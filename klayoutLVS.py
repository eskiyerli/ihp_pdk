#     "Commons Clause" License Condition v1.0
#    #
#     The Software is provided to you by the Licensor under the License, as defined
#     below, subject to the following condition.
#  #
#     Without limiting other conditions in the License, the grant of rights under the
#     License will not include, and the License does not grant to you, the right to
#     Sell the Software.
#  #
#     For purposes of the foregoing, "Sell" means practicing any or all of the rights
#     granted to you under the License to provide to third parties, for a fee or other
#     consideration (including without limitation fees for hosting) a product or service whose value
#     derives, entirely or substantially, from the functionality of the Software. Any
#     license notice or attribution required by the License must also include this
#     Commons Clause License Condition notice.
#  #
#    Add-ons and extensions developed for this software may be distributed
#    under their own separate licenses.
#  #
#     Software: Revolution EDA
#     License: Mozilla Public License 2.0
#     Licensor: Revolution Semiconductor (Registered in the Netherlands)

from contextlib import contextmanager
from functools import lru_cache
import json
import logging
import pathlib
import time

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QIcon, QStandardItemModel
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from quantiphy import Quantity

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.editFunctions as edf
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.gui.lvsResults as lvsr
from revedaEditor.backend.pdkLoader import importPDKModule
from revedaEditor.fileio.extractedSchematic import klayoutSchematicGenerator
from revedaEditor.fileio.spiceNetlist import parse_extracted_netlist

from revedaEditor.gui.schematicEditor import schematicEditor, xyceNetlist

process = importPDKModule("process")


logger = logging.getLogger("reveda")

SYMBOL_PIN_DISTANCE = 80
SYMBOL_STUB_LENGHT = 20

# The IHP rule deck's PREFIX_MAP misses a few extracted device classes:
# the two-port inductor extractor registers its devices as 'inductor'
# (not 'inductor2'), and the npn13G2l/npn13G2v extractors use lower-case
# names while PREFIX_MAP spells them npn13G2L/npn13G2V. KLayout's custom
# writer then falls back to the numeric device id as the SPICE prefix
# (e.g. "1$1 ..."), producing device lines the netlist parser cannot
# read. The .lvs files are vendor code, so the proper prefix is restored
# here when the extracted netlist is consumed.
_EXTRACTED_DEVICE_PREFIXES = {
    "inductor": "L",
    "npn13g2l": "Q",
    "npn13g2v": "Q",
}


def fixupExtractedDevicePrefixes(netlistPath: pathlib.Path) -> None:
    """Rewrite digit-prefixed device lines in an extracted SPICE netlist.

    Lines inside a subcircuit that start with a digit come from device
    classes missing from the deck's PREFIX_MAP (see
    _EXTRACTED_DEVICE_PREFIXES). The model token (last bare token before
    the key=value parameters) identifies the class; the line's first
    token is rewritten as ``<prefix><expanded_name>``. Edits the file in
    place; unmapped or unparseable lines are left untouched.
    """
    try:
        lines = netlistPath.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    insideSubckt = False
    changed = False
    for index, line in enumerate(lines):
        upperLine = line.strip().upper()
        if upperLine.startswith(".SUBCKT"):
            insideSubckt = True
            continue
        if upperLine.startswith(".ENDS"):
            insideSubckt = False
            continue
        if not insideSubckt or not line[:1].isdigit():
            continue
        tokens = line.split()
        modelIndex = next(
            (i for i in range(len(tokens) - 1, 0, -1) if "=" not in tokens[i]),
            None,
        )
        if modelIndex is None:
            continue
        prefix = _EXTRACTED_DEVICE_PREFIXES.get(tokens[modelIndex].casefold())
        if prefix is None:
            continue
        tokens[0] = prefix + tokens[0].lstrip("0123456789")
        lines[index] = " ".join(tokens)
        changed = True
    if changed:
        netlistPath.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info(f"Restored device prefixes in {netlistPath}")


def collectSceneConnectivityHints(scene, extractedNetlist, dbu):
    """Extract naming/connectivity hints from a layout scene.

    Returns ``(devicePinAnchors, portFootprints, pcellBridges)``:
      * devicePinAnchors: list of (net_id, LayRect) built by matching each
        device (Pcell) terminal pin to the extracted-netlist device it belongs
        to. The net_id is that terminal's net -- exactly what the device lines
        reference -- so a routing group landing on the pin is named that net
        and the parasitics connect to the correct transistor terminal.
      * portFootprints: (netName, LayRect) from top-level pins (ports).
      * pcellBridges: per-instance PcellBridge(pin_name, LayRect) so routing
        that lands on the same device terminal is tied into one net.

    Matching scene instances to extracted devices: the extracted netlist may
    split a multi-finger device into several devices, each carrying a layout
    position (in microns). We match each device *pin* to the nearest extracted
    device (by pin-centre vs device position) and read that device's terminal
    -> net map, so per-finger nets resolve correctly.

    Uses ``sceneBoundingRect`` so nested/rotated pin footprints are already in
    scene (dbu) coordinates, matching the layout.json geometry.
    """
    import revedaEditor.common.layoutShapes as lshp
    from revedaEditor.rcextraction.layoutGeometry import LayRect, PcellBridge

    def _layRect(item):
        r = item.sceneBoundingRect()
        return LayRect(r.left(), r.top(), r.right(), r.bottom())

    devicePinAnchors = []
    portFootprints = []
    pcellBridges = []
    if scene is None:
        return devicePinAnchors, portFootprints, pcellBridges

    # Extracted devices with a layout position (microns -> dbu) and their
    # terminal -> net map, for pin->net resolution by proximity.
    extractedDevices = []
    if extractedNetlist:
        for dev in extractedNetlist.get("devices", []):
            pos = dev.get("position")
            terminals = dev.get("terminals", {})
            if isinstance(pos, dict) and terminals:
                extractedDevices.append((
                    float(pos.get("x", 0.0)) * dbu,
                    float(pos.get("y", 0.0)) * dbu,
                    terminals,
                ))

    def _netForPin(pinName, cx, cy):
        """Net id for a pin: the nearest extracted device that has this pin."""
        best = None
        bestDist = float("inf")
        pinUpper = pinName.upper()
        for dx, dy, terminals in extractedDevices:
            matchedNet = None
            for tName, netId in terminals.items():
                if tName.upper() == pinUpper:
                    matchedNet = netId
                    break
            if matchedNet is None:
                continue
            dist = (dx - cx) ** 2 + (dy - cy) ** 2
            if dist < bestDist:
                bestDist = dist
                best = matchedNet
        return best

    for item in scene.items():
        # Top-level pins define ports (parentItem is None => not inside an
        # instance).
        if isinstance(item, lshp.layoutPin) and item.parentItem() is None:
            name = (item.pinName or "").strip()
            if name:
                portFootprints.append((name, _layRect(item)))
            continue

        # Instances/Pcells contribute their child pins as device-terminal
        # anchors (for naming) and bridges (for connectivity).
        if isinstance(item, (lshp.layoutInstance, lshp.layoutPcell)):
            bridges = []
            for child in item.childItems():
                if isinstance(child, lshp.layoutPin):
                    pinName = (child.pinName or "").strip()
                    if not pinName:
                        continue
                    rect = _layRect(child)
                    cx = 0.5 * (rect.x1 + rect.x2)
                    cy = 0.5 * (rect.y1 + rect.y2)
                    pinUpper = pinName.upper()
                    layerName = getattr(getattr(child, "layer", None), "name", "Metal1")
                    bridges.append(PcellBridge(pinName, rect, layerName))
                    netId = _netForPin(pinName, cx, cy)
                    if netId is not None:
                        devicePinAnchors.append((str(netId), rect, layerName))
                    if extractedNetlist:
                        bestDev = None
                        bestDevDist = float("inf")
                        for dev in extractedNetlist.get("devices", []):
                            pos = dev.get("position")
                            if isinstance(pos, dict):
                                dx = float(pos.get("x", 0.0)) * dbu
                                dy = float(pos.get("y", 0.0)) * dbu
                                dist = (dx - cx) ** 2 + (dy - cy) ** 2
                                if dist < bestDevDist:
                                    bestDevDist = dist
                                    bestDev = dev
                        if bestDev is not None:
                            bestDev.setdefault("terminal_locations", {})[pinUpper] = {
                                "x": cx, "y": cy, "layer": layerName
                            }
            if bridges:
                pcellBridges.append(bridges)

    return devicePinAnchors, portFootprints, pcellBridges


@contextmanager
def _measureDuration():
    start_time = time.perf_counter()
    try:
        yield
    finally:
        end_time = time.perf_counter()
        logger.info(
            f"Total processing time: {(end_time - start_time) * 1000:.3f} milliseconds"
        )


def klayoutLVSClick(layoutEditor):
    from revedaEditor.fileio.importlvsdb import LVSDBParser 

    @lru_cache(maxsize=16)
    def findSymbolViewNameTuple(extractedCellName: str, libraryModel: QStandardItemModel):
        """Find (libName, cellName, viewName) tuple for a cell type."""

        root = libraryModel.invisibleRootItem()

        def symbolViewTuple(libItem, cellItem):
            # Look for symbol view among the cell's views (level 2)
            for viewRow in range(cellItem.rowCount()):
                viewItem = cellItem.child(viewRow)  # viewItem
                if viewItem.viewName == "symbol":
                    return ddef.viewNameTuple(
                        libItem.libraryName, cellItem.cellName, "symbol"
                    )
            return None

        def symbolLvsModel(cellItem) -> str | None:
            """Return the symbol's ``lvs_model`` attribute, if defined."""
            for viewRow in range(cellItem.rowCount()):
                viewItem = cellItem.child(viewRow)
                if viewItem.viewName != "symbol":
                    continue
                try:
                    with viewItem.viewPath.open("r", encoding="utf-8") as symbolFile:
                        symbolData = json.load(symbolFile)
                except (OSError, json.JSONDecodeError):
                    return None
                for item in symbolData:
                    if (
                        isinstance(item, dict)
                        and item.get("type") == "attr"
                        and str(item.get("nam", "")).casefold() == "lvs_model"
                    ):
                        return item.get("def")
                return None
            return None

        # Iterate through libraries (level 0)
        for libRow in range(root.rowCount()):
            libItem = root.child(libRow)  # libraryItem

            # Iterate through cells in this library (level 1)
            for cellRow in range(libItem.rowCount()):
                cellItem = libItem.child(cellRow)  # cellItem
                if cellItem.cellName == extractedCellName or str(cellItem.cellName).casefold() == str(extractedCellName).casefold():
                    viewTuple = symbolViewTuple(libItem, cellItem)
                    if viewTuple is not None:
                        return viewTuple

        # The extracted device class may differ from the library cell name
        # (e.g. LVS device "rfcmim" vs cell "cap_rfcmim"). Fall back to the
        # symbol's "lvs_model" attribute, which is what the schematic-side
        # LVS netlist emits as the device model.
        targetName = str(extractedCellName).casefold()
        for libRow in range(root.rowCount()):
            libItem = root.child(libRow)
            for cellRow in range(libItem.rowCount()):
                cellItem = libItem.child(cellRow)
                lvsModel = symbolLvsModel(cellItem)
                if lvsModel is not None and str(lvsModel).casefold() == targetName:
                    return symbolViewTuple(libItem, cellItem)

        return None

    def saveRunSet(dlg):
        settings = dlg.collectSettings()
        lvsRunPathObj = pathlib.Path(settings["lvsRunPath"])
        lvsRunPathObj.mkdir(parents=True, exist_ok=True)
        settingsPathObj = lvsRunPathObj / "lvsSettings.json"
        with settingsPathObj.open("w") as f:
            json.dump(settings, f, indent=4)
        logger.info(f"LVS settings saved to {settingsPathObj}")

    def LVSProcessFinished(
        filePath: pathlib.Path,
        extractedNetlistPath: pathlib.Path,
        dlg: "klayoutLVSDialogue",
        schematic_editor=None,
        referenceNetlistPath: pathlib.Path | None = None,
    ):
        logger.info(f"LVS process finished. Report: {filePath}")
        dlg.console.appendPlainText(f"\n--- LVS Finished. Report: {filePath} ---")
        if extractedNetlistPath.exists():
            dlg.console.appendPlainText(
                f"--- Extracted layout netlist: {extractedNetlistPath} ---"
            )
        else:
            dlg.console.appendPlainText(
                "--- Extracted layout netlist was not generated. ---"
            )

        layoutLayers = importPDKModule("layoutLayers")
        parser = LVSDBParser(filePath, layoutLayers)
        parser.load()
        logger.info(f"Parsed LVSDB: {parser.filepath}")

        # Use extracted netlist as single source of truth for lvs_schematic
        fixupExtractedDevicePrefixes(extractedNetlistPath)
        extracted = parse_extracted_netlist(extractedNetlistPath, layoutEditor.cellName)


        # Gather cross-reference and schematic-side data for the results dialog
        crossrefs = parser.get_all_crossrefs_formatted()
        schem_cell_name = layoutEditor.cellName
        xref = parser.get_crossref(layoutEditor.cellName)
        if xref and xref.get("schematic_name"):
            schem_cell_name = xref["schematic_name"]
        schem_nets = parser.get_schematic_nets(schem_cell_name)
        schem_devices = parser.get_schematic_devices(schem_cell_name)

        # Export the RCX database for RC extraction (PEX) when requested.
        # It is written into the LVS run directory (alongside the other LVS
        # artifacts) rather than the cell directory: the cell directory is
        # scanned by the library browser, which would misinterpret a stray
        # .rcx.json as an (unopenable) cellview. The PEX dialog defaults its
        # RCX input to this same location.
        pexSettings = dlg.collectSettings()
        if pexSettings.get("exportPex"):
            try:
                import orjson
                from revedaEditor.rcextraction.rcxExport import exportRcxDatabase

                layoutLayersModule = importPDKModule("layoutLayers")
                # Real routing geometry comes from the layout.json cellview,
                # not the LVSDB (whose per-net shapes are on internal layers
                # with no physical dimensions).
                with layoutEditor.file.open("rb") as layoutFile:
                    layoutElements = orjson.loads(layoutFile.read())

                # Device-terminal anchors, port footprints and Pcell bridges
                # come from the live layout scene, where pins are already
                # instantiated in scene coordinates. Device pins carry the net
                # ids the extracted-netlist device lines reference, so net
                # naming connects parasitics to the right terminals.
                devicePinAnchors, portFootprints, pcellBridges = (
                    collectSceneConnectivityHints(
                        layoutEditor.centralW.scene, extracted, process.dbu
                    )
                )

                lvsEquivalent = bool(xref.get("equivalent")) if xref else False
                rcxOutputPath = (
                    pathlib.Path(pexSettings["lvsRunPath"])
                    / f"{layoutEditor.cellName}.rcx.json"
                )
                exportRcxDatabase(
                    layoutEditor.cellName,
                    layoutElements,
                    extracted,
                    layoutLayersModule,
                    process,
                    rcxOutputPath,
                    process.dbu,
                    lvsEquivalent,
                    devicePinAnchors=devicePinAnchors,
                    portFootprints=portFootprints,
                    pcellBridges=pcellBridges,
                )
                dlg.console.appendPlainText(
                    f"--- Exported RCX database for PEX: {rcxOutputPath} ---"
                )
            except Exception as rcxError:
                logger.error(f"Failed to export RCX database: {rcxError}")
                dlg.console.appendPlainText(
                    f"--- ERROR: RCX export failed: {rcxError} ---"
                )

        # Compute source reference netlist path for hierarchy tree. In netlist
        # mode this is the user-supplied file; in schematic mode it is the
        # generated <cell>_<view>.cir.
        lvsSettings = dlg.collectSettings()
        if referenceNetlistPath is not None:
            sourceNetlistPath = pathlib.Path(referenceNetlistPath)
        elif lvsSettings.get("lvsSourceMode") == "netlist" and lvsSettings.get(
            "netlistFilePath"
        ):
            sourceNetlistPath = pathlib.Path(lvsSettings["netlistFilePath"])
        else:
            sourceNetlistPath = pathlib.Path(lvsSettings["lvsRunPath"]) / (
                f"{lvsSettings['schematicCellName']}_{lvsSettings['schematicViewName']}.cir"
            )

        # Create LVS results dialog with the schematic editor from the dialogue settings
        lvsNetsDlg = lvsr.lvsResultsDialogue(
            layoutEditor,
            parser.get_nets(layoutEditor.cellName),
            parser.get_layout_devices(layoutEditor.cellName),
            parser.get_layout_cells_with_bbox(),
            parser=parser,
            crossrefs=crossrefs,
            schem_nets=schem_nets,
            schem_devices=schem_devices,
            schematic_editor=schematic_editor,
            source_netlist_path=sourceNetlistPath,
            extracted_netlist_path=extractedNetlistPath,
        )

        schematicNetlistPath = None
        if extracted:
            schematicNetlistPath = sourceNetlistPath
            revedaMain = QApplication.instance().appMainW
            gen = klayoutSchematicGenerator(
                parser,
                layoutEditor,
                revedaMain,
                findSymbolViewNameTuple,
                logger,
                highlight_callback=lvsNetsDlg.register_schematic_view,
            )
            lvs_schematic_editor = gen.generateSchematic(extracted, schematicNetlistPath)
            if lvs_schematic_editor is not None:
                lvs_schematic_editor.show()
                lvs_schematic_editor.raise_()
                lvs_schematic_editor.activateWindow()

        lvsNetsDlg.show()

    def runKlayoutLVS(dlg):
        settings = dlg.collectSettings()
        klayoutPath = settings["klayoutPath"]
        sourceMode = settings.get("lvsSourceMode", "schematic")
        netlistMode = sourceMode == "netlist"
        netlistFilePath = settings.get("netlistFilePath", "")
        schematicCellName = settings["schematicCellName"]
        schematicViewName = settings["schematicViewName"]
        layoutCellName = settings["layoutCellName"]
        lvsRunLimit = settings["lvsRunLimit"]
        lvsRunPath = settings["lvsRunPath"]
        gdsExport = settings["gdsExport"]
        lvsSwitches = settings["lvsSwitches"]
        createNetlist = settings["createNetlist"]
        netOnly = not createNetlist
        gdsUnit = settings["gdsUnit"]
        gdsPrecision = settings["gdsPrecision"]
        implicitNets = settings["implicitNets"]
        runMode = settings["runMode"]
        lvsRunPathObj = pathlib.Path(lvsRunPath)
        lvsRunPathObj.mkdir(parents=True, exist_ok=True)
        lvsModule = importPDKModule("lvs")
        lvsPath = pathlib.Path(lvsModule.__file__).parent.resolve()
        lvsRulePath = lvsPath / "sg13g2.lvs"

        # The reference netlist compared against the layout. In schematic mode
        # it is generated from the chosen schematic cellview; in netlist mode
        # the user supplies an existing netlist file, so no schematic editor is
        # opened or netlisted.
        schematic_editor = None
        if netlistMode:
            if not netlistFilePath:
                logger.error(
                    "Netlist mode selected but no netlist file was specified."
                )
                dlg.console.appendPlainText(
                    "ERROR: No netlist file specified for netlist-mode LVS."
                )
                return
            schematicNetlistPathObj = pathlib.Path(netlistFilePath)
            if not schematicNetlistPathObj.exists():
                logger.error(
                    f"Netlist file not found at {schematicNetlistPathObj}."
                )
                dlg.console.appendPlainText(
                    f"ERROR: Netlist file not found: {schematicNetlistPathObj}"
                )
                return
            # net_only comparison is meaningless without a reference netlist;
            # force a full compare against the supplied netlist.
            netOnly = False
        else:
            schematicNetlistPathObj = (
                lvsRunPathObj / f"{schematicCellName}_{schematicViewName}.cir"
            )
            # Get the schematic editor for the selected schematic cellview
            schematic_lib_name = settings["schematicLibName"]
            schematic_cell_name = settings["schematicCellName"]
            schematic_view_name = settings["schematicViewName"]

            # Try to find or open the schematic editor for the selected cellview
            revedaMain = QApplication.instance().appMainW
            if revedaMain:
                from revedaEditor.backend.dataDefinitions import viewNameTuple
                view_key = viewNameTuple(schematic_lib_name, schematic_cell_name, schematic_view_name)
                schematic_editor = revedaMain.openViews.get(view_key)
                # If not already open, open it via the library view infrastructure
                if schematic_editor is None:
                    try:
                        libItem = libm.getLibItem(dlg.model, schematic_lib_name)
                        cellItem = libm.getCellItem(libItem, schematic_cell_name)
                        viewItem = libm.getViewItem(cellItem, schematic_view_name)
                        if viewItem:
                            viewItemT = ddef.viewItemTuple(libItem, cellItem, viewItem)
                            layoutEditor.libraryView.openCellView(viewItemT)
                            schematic_editor = revedaMain.openViews.get(view_key)

                    except Exception as e:
                        logger.warning(f"Failed to open schematic editor for {schematic_lib_name}:{schematic_cell_name}:{schematic_view_name}: {e}")

                # Ensure the schematic scene is loaded so nets/devices can be extracted.
                # Only load if the scene is empty — calling loadSchematic() on an
                # already-loaded editor duplicates all items because loadDesign()
                # does not clear the scene first.
                if schematic_editor is not None:
                    try:
                        if not hasattr(schematic_editor, 'centralW') or schematic_editor.centralW is None:
                            schematic_editor.init_UI()
                        if schematic_editor.centralW.scene is not None and \
                                len(schematic_editor.centralW.scene.items()) == 0:
                            schematic_editor.loadSchematic()
                    except Exception as e:
                        logger.warning(f"Failed to load schematic for {schematic_cell_name}: {e}")

        if gdsExport:
            layoutEditor.centralW.scene.exportCellGDS(
                lvsRunPathObj, gdsUnit, gdsPrecision, process.dbu
            )

        if not netlistMode and createNetlist:
            createSchematicNetlist(dlg, lvsRunPathObj, schematic_editor)
        elif not netlistMode:
            logger.info(
                "Schematic netlist generation is disabled; running in NET_ONLY mode."
            )

        if not netOnly and not schematicNetlistPathObj.exists():
            logger.error(
                f"Reference netlist file not found at {schematicNetlistPathObj}. "
                f"Please check the netlist settings and try again."
            )
            return

        gdsPath = lvsRunPathObj / f"{layoutCellName}.gds"
        if not gdsPath.exists():
            logger.error(
                f"GDS file not found at {gdsPath}. Please check the GDS export settings and try again."
            )
            return

        lvsReportFilePath = lvsRunPathObj / f"{layoutCellName}.lvsdb"
        lvsExtractedNetlistPath = lvsRunPathObj / f"{layoutCellName}_extracted.cir"
        argumentsList = [
            "-b",
            "-r",
            str(lvsRulePath),
            "-rd",
            f"input={gdsPath}",
            "-rd",
            f"topcell={layoutCellName}",
            "-rd",
            f"report={lvsReportFilePath}",
            "-rd",
            f"target_netlist={lvsExtractedNetlistPath}",
            "-rd",
            f"net_only={'true' if netOnly else 'false'}",
            "-rd",
            f"run_mode={runMode}",
        ]
        if not netOnly:
            argumentsList.extend(["-rd", f"schematic={schematicNetlistPathObj}"])

        for switchName, enabled in lvsSwitches.items():
            argumentsList.extend(["-rd", f"{switchName}={'true' if enabled else 'false'}"])

        if implicitNets:
            argumentsList.extend(["-rd", f"implicit_nets={implicitNets}"])

        layoutEditor.processManager.maxProcesses = int(lvsRunLimit)
        dlg.console.appendPlainText("--- LVS Started ---")
        lvsProcess = layoutEditor.processManager.add_process(klayoutPath, argumentsList)

        if lvsProcess.process is None:
            dlg.console.appendPlainText("ERROR: Failed to start KLayout process")
            logger.error("Failed to start KLayout process")
            return

        # Redirect process output to dialog console instead of main logger
        try:
            lvsProcess.process.readyReadStandardOutput.disconnect()
        except RuntimeError:
            pass
        lvsProcess.process.readyReadStandardOutput.connect(
            lambda: dlg.appendLVSOutput(lvsProcess.process)
        )
        lvsProcess.process.readyReadStandardError.connect(
            lambda: dlg.appendLVSError(lvsProcess.process)
        )
        # Connect LVS-specific callback alongside the ProcessManager's own
        # finished slot (process_finished), which removes the process from
        # running_processes and frees the slot.  Do NOT disconnect the
        # ProcessManager slot — otherwise the process is never cleaned up and
        # consecutive runs exhaust the max-processes limit.
        lvsProcess.process.finished.connect(
            lambda: LVSProcessFinished(
                lvsReportFilePath,
                lvsExtractedNetlistPath,
                dlg,
                schematic_editor,
                referenceNetlistPath=schematicNetlistPathObj,
            )
        )

    def createSchematicNetlist(dlg, lvsRunPathObj, schematic_editor=None):
        settings = dlg.collectSettings()
        schematicLibName: str = settings["schematicLibName"]
        schematicCellName: str = settings["schematicCellName"]
        schematicViewName: str = settings["schematicViewName"]
        schematicNetlistPathObj: pathlib.Path = (
            lvsRunPathObj / f"{schematicCellName}_{schematicViewName}.cir"
        )
        # Reuse the already-open schematic editor if available; otherwise
        # create a temporary one for netlisting.  Creating a new
        # schematicEditor and calling loadSchematic() would register it in
        # openViews, overwriting the user's actual open editor.
        if schematic_editor is not None:
            schematicE = schematic_editor
        else:
            libItem = libm.getLibItem(dlg.model, schematicLibName)
            cellItem = libm.getCellItem(libItem, schematicCellName)
            viewItem = libm.getViewItem(cellItem, schematicViewName)
            schematicE: schematicEditor = schematicEditor(
                viewItem, dlg.model.libraryDict, dlg.layoutEditor.libraryView
            )
            schematicE.loadSchematic()
        netlistObj = xyceNetlist(schematicE, schematicNetlistPathObj, False, True, True)
        if netlistObj:
            with _measureDuration():
                netlistObj.writeNetlist()

    def loadRunSet(dlg):
        filePath, _ = QFileDialog.getOpenFileName(
            dlg, caption="Load LVS Settings", filter="JSON Files (*.json)"
        )
        if not filePath:
            return
        try:
            with open(filePath) as f:
                settings = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error(f"Failed to load LVS settings from {filePath}: {exc}")
            return
        dlg.applySettings(settings)
        logger.info(f"LVS settings loaded from {filePath}")

    dlg = klayoutLVSDialogue(layoutEditor)
    dlg.unitEdit.setText(str(process.gdsUnit))
    dlg.precisionEdit.setText(str(process.gdsPrecision))
    dlg.gdsExportBox.setChecked(True)
    dlg.LVSRunPathEdit.setText(str(layoutEditor.gdsExportDirObj))
    dlg.runLVSAction.triggered.connect(lambda: runKlayoutLVS(dlg))
    dlg.show()


class klayoutLVSDialogue(QMainWindow):
    def __init__(self, parentEditor):
        super().__init__(parentEditor)
        self.layoutEditor = parentEditor
        self.model = parentEditor.libraryView.libraryModel
        self.setWindowTitle("KLayout LVS")
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumSize(1200, 900)
        self._settings = QSettings("Revolution Semiconductor", "Revolution EDA")
        self._recentSettingsKey = "ihpKlayoutLVS/recentSettings"
        self._createMenuBar()
        self.mainLayout = QVBoxLayout()

        # Source mode selector: compare the layout against a schematic cellview
        # (netlisted on the fly) or against an existing netlist file directly.
        # The latter lets designs that only have a netlist (no schematic) run
        # LVS.
        sourceModeGroupBox = QGroupBox("Reference Source")
        sourceModeLayout = QHBoxLayout()
        self.sourceModeGroup = QButtonGroup(self)
        self.schematicModeBtn = QRadioButton("Schematic")
        self.netlistModeBtn = QRadioButton("Netlist")
        self.schematicModeBtn.setChecked(True)
        self.sourceModeGroup.addButton(self.schematicModeBtn)
        self.sourceModeGroup.addButton(self.netlistModeBtn)
        self.schematicModeBtn.toggled.connect(self._onSourceModeChanged)
        sourceModeLayout.addWidget(self.schematicModeBtn)
        sourceModeLayout.addWidget(self.netlistModeBtn)
        sourceModeLayout.addStretch()
        sourceModeGroupBox.setLayout(sourceModeLayout)
        self.mainLayout.addWidget(sourceModeGroupBox)

        hLayout = QHBoxLayout()
        self.mainLayout.addLayout(hLayout)
        schematicGroupBox = QGroupBox("Schematic")
        self.schematicGroupBox = schematicGroupBox
        schematicLayout = QFormLayout()
        schematicGroupBox.setLayout(schematicLayout)
        self.schematicLibListCB = QComboBox()
        self.schematicLibListCB.setModel(self.model)
        self.schematicLibListCB.setModelColumn(0)
        self.schematicLibListCB.setCurrentText(self.layoutEditor.libName)
        self.schematicLibItem = libm.getLibItem(
            self.model, self.layoutEditor.libName
        )
        schematicLayout.addRow("Library:", self.schematicLibListCB)

        self.schematicCellListCB = QComboBox()
        schematicCellList = sorted(
            [
                self.schematicLibItem.child(i).cellName
                for i in range(self.schematicLibItem.rowCount())
            ]
        )
        self.schematicCellListCB.addItems(schematicCellList)
        self.schematicCellListCB.setEditable(True)
        self.schematicCellListCB.setCurrentText(self.layoutEditor.cellName)
        self.schematicCellItem = libm.getCellItem(
            self.schematicLibItem, self.layoutEditor.cellName
        )
        schematicLayout.addRow("Cell:", self.schematicCellListCB)

        self.schematicCellViewListCB = QComboBox()
        self.schematicCellViewListCB.setEditable(True)
        self.schematicCellViewListCB.addItems(
            sorted(
                [
                    self.schematicCellItem.child(i).text()
                    for i in range(self.schematicCellItem.rowCount())
                    if self.schematicCellItem.child(i).viewType == "schematic"
                ]
            )
        )
        schematicLayout.addRow("View:", self.schematicCellViewListCB)

        self.schematicLibListCB.currentTextChanged.connect(self.changeSchematicCells)
        self.schematicCellListCB.currentTextChanged.connect(
            self.changeSchematicCellViews
        )

        hLayout.addWidget(schematicGroupBox)

        layoutGroupBox = QGroupBox("Layout")
        layoutLayout = QFormLayout()
        layoutGroupBox.setLayout(layoutLayout)
        self.layoutLibListCB = QComboBox()
        self.layoutLibListCB.setEditable(False)
        self.layoutLibListCB.addItem(self.layoutEditor.libName)
        layoutLayout.addRow("Library:", self.layoutLibListCB)

        self.layoutCellListCB = QComboBox()
        self.layoutCellListCB.setEditable(False)
        self.layoutCellListCB.addItem(self.layoutEditor.cellName)
        layoutLayout.addRow(edf.boldLabel("Cell:"), self.layoutCellListCB)

        self.layoutCellViewListCB = QComboBox()
        self.layoutCellViewListCB.setEditable(False)
        self.layoutCellViewListCB.addItem(self.layoutEditor.viewName)
        layoutLayout.addRow(edf.boldLabel("View:"), self.layoutCellViewListCB)
        self._lockLayoutSelection()

        hLayout.addWidget(layoutGroupBox)

        # Existing-netlist source: used when "Netlist" mode is selected.
        # Hidden by default; the schematic group is shown instead.
        self.netlistGroupBox = QGroupBox("Netlist File")
        netlistFileLayout = QFormLayout()
        self.netlistGroupBox.setLayout(netlistFileLayout)
        netlistPathRow = QHBoxLayout()
        self.netlistFilePathEdit = edf.longLineEdit()
        self.netlistFilePathEdit.setToolTip(
            "SPICE netlist to compare the layout against. Must define the "
            "top cell as a subcircuit matching the layout top cell name."
        )
        self.netlistBrowseBtn = QPushButton("Browse...")
        self.netlistBrowseBtn.clicked.connect(self.onNetlistFileButtonClicked)
        netlistPathRow.addWidget(self.netlistFilePathEdit, 5)
        netlistPathRow.addWidget(self.netlistBrowseBtn, 1)
        netlistFileLayout.addRow(edf.boldLabel("Netlist Path:"), netlistPathRow)
        self.netlistGroupBox.setVisible(False)
        hLayout.addWidget(self.netlistGroupBox)

        exportGroupBox = QGroupBox("GDS Export Options")
        self.exportGDSLayout = QFormLayout()
        self.exportGDSLayout.setSpacing(10)
        self.gdsExportBox = QCheckBox()
        self.gdsExportBox.checkStateChanged.connect(self.exportGDSRows)
        self.exportGDSLayout.addRow(edf.boldLabel("Export GDS:"), self.gdsExportBox)
        self.unitEdit = edf.shortLineEdit()
        self.unitEdit.setToolTip("The unit of the GDS file.")
        self.exportGDSLayout.addRow(edf.boldLabel("Unit:"), self.unitEdit)
        self.precisionEdit = edf.shortLineEdit()
        self.precisionEdit.setToolTip("The precision of the GDS file.")
        self.exportGDSLayout.addRow(edf.boldLabel("Precision:"), self.precisionEdit)
        self.exportGDSLayout.setRowVisible(1, False)
        self.exportGDSLayout.setRowVisible(2, False)
        exportGroupBox.setLayout(self.exportGDSLayout)
        self.mainLayout.addWidget(exportGroupBox)
        self.mainLayout.addSpacing(20)

        netlistGroupBox = QGroupBox("Netlist Options")
        netlistLayout = QFormLayout()
        netlistGroupBox.setLayout(netlistLayout)
        self.netlistBox = QCheckBox()
        self.netlistBox.setChecked(True)
        netlistLayout.addRow(edf.boldLabel("Create Schematic Netlist:"), self.netlistBox)
        self.exportPexBox = QCheckBox()
        self.exportPexBox.setToolTip(
            "Write a <cell>.rcx.json extraction database into the LVS run "
            "directory so RC Extraction (PEX) can run directly on the LVS "
            "result."
        )
        netlistLayout.addRow(edf.boldLabel("Export for PEX:"), self.exportPexBox)
        self.mainLayout.addWidget(netlistGroupBox)

        lvsOptionsGroup = QGroupBox("LVS Options")
        lvsOptionsLayout = QVBoxLayout()
        lvsOptionsLayout.setSpacing(10)
        klayoutPathDialogueLayout = QHBoxLayout()
        klayoutPathDialogueLayout.addWidget(edf.boldLabel("KLayout Executable Path:"), 1)
        self.klayoutPathEdit = edf.longLineEdit()
        klayoutPathDialogueLayout.addWidget(self.klayoutPathEdit, 5)
        lvsOptionsLayout.addLayout(klayoutPathDialogueLayout)

        lvsRunPathLayout = QHBoxLayout()
        lvsRunPathLayout.addWidget(edf.boldLabel("LVS Run Path:"), 1)
        self.LVSRunPathEdit = edf.longLineEdit()
        lvsRunPathLayout.addWidget(self.LVSRunPathEdit, 5)
        lvsOptionsLayout.addLayout(lvsRunPathLayout)

        lvsRunLimitDialogueLayout = QHBoxLayout()
        lvsRunLimitDialogueLayout.addWidget(edf.boldLabel("LVS Run Limit:"), 2)
        self.LVSRunLimitEdit = edf.longLineEdit()
        lvsRunLimitDialogueLayout.addWidget(self.LVSRunLimitEdit)
        lvsOptionsLayout.addLayout(lvsRunLimitDialogueLayout)
        self.LVSRunLimitEdit.setText("2")

        implicitNetsLayout = QHBoxLayout()
        implicitNetsLayout.addWidget(edf.boldLabel("Implicit Nets:"), 2)
        self.implicitNetsEdit = edf.longLineEdit()
        self.implicitNetsEdit.setPlaceholderText("VDD,VSS or *")
        self.implicitNetsEdit.setToolTip(
            "Comma-separated net names or patterns for implicit connections."
        )
        implicitNetsLayout.addWidget(self.implicitNetsEdit, 5)
        lvsOptionsLayout.addLayout(implicitNetsLayout)

        self.mainLayout.addSpacing(20)
        # LVS switches – exclusive True/False radio buttons per option
        _lvsSwitchDefs = [
            ("no_net_names", "No Net Names"),
            ("spice_comments", "Spice Comments"),
            ("top_lvl_pins", "Top Level Pins"),
            ("ignore_top_ports_mismatch", "Ignore Top Ports Mismatch"),
            ("no_simplify", "No Simplify"),
            ("no_series_res", "No Series Resistors"),
            ("no_parallel_res", "No Parallel Resistors"),
            ("combine_devices", "Combine Devices"),
            ("disable_tap_extraction", "Disable Tap Extraction"),
            ("purge", "Remove Floating Devices"),
            ("purge_nets", "Remove Floating Nets"),
            ("purge_devices", "Remove Unused Devices"),
        ]
        self.lvsSwitchGroups: dict[str, QButtonGroup] = {}
        lvsSwitchesLayout = QFormLayout()
        lvsSwitchesLayout.setSpacing(6)
        for attr, labelText in _lvsSwitchDefs:
            btnGroup = QButtonGroup(self)
            trueBtn = QRadioButton("True")
            falseBtn = QRadioButton("False")
            trueBtn.setChecked(True)
            btnGroup.addButton(trueBtn)
            btnGroup.addButton(falseBtn)
            btnRowLayout = QHBoxLayout()
            btnRowLayout.setSpacing(16)
            btnRowLayout.addWidget(trueBtn)
            btnRowLayout.addWidget(falseBtn)
            btnRowLayout.addStretch()
            lvsSwitchesLayout.addRow(labelText + ":", btnRowLayout)
            self.lvsSwitchGroups[attr] = btnGroup
        self.mainLayout.addSpacing(10)
        # Run mode – exclusive Deep/Flat radio buttons (in same QFormLayout for alignment)
        self.runModeGroup = QButtonGroup(self)
        self.deepBtn = QRadioButton("Deep")
        self.flatBtn = QRadioButton("Flat")
        self.deepBtn.setChecked(True)
        self.runModeGroup.addButton(self.deepBtn)
        self.runModeGroup.addButton(self.flatBtn)
        runModeRowLayout = QHBoxLayout()
        runModeRowLayout.setSpacing(14)
        runModeRowLayout.addWidget(self.deepBtn)
        runModeRowLayout.addWidget(self.flatBtn)
        runModeRowLayout.addStretch()
        lvsSwitchesLayout.addRow("Run Mode:", runModeRowLayout)

        lvsOptionsLayout.addLayout(lvsSwitchesLayout)

        lvsOptionsGroup.setLayout(lvsOptionsLayout)
        self.mainLayout.addWidget(lvsOptionsGroup)

        # Wrap the form in a scroll area (left panel of splitter)
        formWidget = QWidget()
        formWidget.setLayout(self.mainLayout)
        scrollArea = QScrollArea()
        scrollArea.setWidget(formWidget)
        scrollArea.setWidgetResizable(True)
        scrollArea.setMinimumWidth(620)

        # Console panel (right panel of splitter)
        consoleWidget = QWidget()
        consoleLayout = QVBoxLayout(consoleWidget)
        consoleLayout.addWidget(QLabel("LVS Output:"))
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMinimumWidth(400)
        consoleLayout.addWidget(self.console)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(scrollArea)
        splitter.addWidget(consoleWidget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        outerLayout = QHBoxLayout()
        outerLayout.addWidget(splitter)
        centralWidget = QWidget()
        centralWidget.setLayout(outerLayout)
        self.setCentralWidget(centralWidget)
        self.show()

    def _createMenuBar(self):
        menuBar = self.menuBar()
        menuBar.setNativeMenuBar(False)
        fileMenu = menuBar.addMenu("&File")
        self.loadSettingsAction = QAction(
            QIcon(":/icons/document-import.png"), "Load LVS Settings...", self
        )
        self.loadSettingsAction.triggered.connect(lambda: self._load_settings_from_file())
        fileMenu.addAction(self.loadSettingsAction)
        self.saveSettingsAction = QAction(
            QIcon(":/icons/disk.png"), "Save LVS Settings...", self
        )
        self.saveSettingsAction.triggered.connect(lambda: self._save_settings_to_file())
        fileMenu.addAction(self.saveSettingsAction)
        fileMenu.addSeparator()
        self.recentSettingsMenu = fileMenu.addMenu("Recent LVS Settings")
        self._updateRecentSettingsMenu()
        fileMenu.addSeparator()
        self.closeAction = QAction(QIcon(":/icons/external.png"), "Close", self)
        self.closeAction.triggered.connect(self.close)
        fileMenu.addAction(self.closeAction)

        self.runLVSAction = QAction(
            QIcon(":/icons/application-run.png"), "Run LVS", self
        )
        self.runLVSAction.setShortcut("F5")
        runMenu = menuBar.addMenu("&Run")
        runMenu.addAction(self.runLVSAction)

        toolsMenu = menuBar.addMenu("&Tools")
        self.selectKlayoutAction = QAction(
            QIcon(":/icons/external.png"), "Select KLayout Executable...", self
        )
        self.selectKlayoutAction.triggered.connect(self.onkfilePathButtonClicked)
        toolsMenu.addAction(self.selectKlayoutAction)
        self.selectRunPathAction = QAction(
            QIcon(":/icons/document.png"), "Select LVS Run Path...", self
        )
        self.selectRunPathAction.triggered.connect(self.onLVSRunPathButtonClicked)
        toolsMenu.addAction(self.selectRunPathAction)
        toolsMenu.addSeparator()
        self.clearConsoleAction = QAction(
            QIcon(":/icons/eraser.png"), "Clear LVS Output", self
        )
        self.clearConsoleAction.triggered.connect(lambda: self.console.clear())
        toolsMenu.addAction(self.clearConsoleAction)

        self.lvsToolBar = self.addToolBar("LVS")
        self.lvsToolBar.setObjectName("lvsToolBar")
        self.lvsToolBar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.lvsToolBar.addAction(self.runLVSAction)
        self.lvsToolBar.addSeparator()
        self.lvsToolBar.addAction(self.loadSettingsAction)
        self.lvsToolBar.addAction(self.saveSettingsAction)
        self.lvsToolBar.addSeparator()
        self.lvsToolBar.addAction(self.selectKlayoutAction)
        self.lvsToolBar.addAction(self.selectRunPathAction)
        self.lvsToolBar.addAction(self.clearConsoleAction)
        self.lvsToolBar.addSeparator()
        self.lvsToolBar.addAction(self.closeAction)

    def _recent_settings(self) -> list[str]:
        values = self._settings.value(self._recentSettingsKey, [])
        if isinstance(values, str):
            values = [values]
        return [str(path) for path in values if path]

    def _updateRecentSettingsMenu(self):
        self.recentSettingsMenu.clear()
        recentPaths = self._recent_settings()
        if not recentPaths:
            action = self.recentSettingsMenu.addAction("No recent settings")
            action.setEnabled(False)
            return
        for path in recentPaths:
            settingsPath = pathlib.Path(path)
            displayName = self._recent_settings_display_name(settingsPath)
            action = self.recentSettingsMenu.addAction(displayName)
            action.setToolTip(path)
            if settingsPath.exists():
                action.triggered.connect(
                    lambda checked=False, path=path: self._load_settings_from_file(path)
                )
            else:
                action.setEnabled(False)

    @staticmethod
    def _recent_settings_display_name(settingsPath: pathlib.Path) -> str:
        try:
            with settingsPath.open("r", encoding="utf-8") as settingsFile:
                settings = json.load(settingsFile)
        except (OSError, json.JSONDecodeError):
            return "Unknown LVS Cell"

        layoutCell = str(settings.get("layoutCellName", "")).strip()
        schematicCell = str(settings.get("schematicCellName", "")).strip()
        if layoutCell and schematicCell and layoutCell != schematicCell:
            return f"{layoutCell} (schematic: {schematicCell})"
        return layoutCell or schematicCell or "Unknown LVS Cell"

    def _add_recent_settings(self, filepath: str):
        paths = [filepath] + [path for path in self._recent_settings() if path != filepath]
        self._settings.setValue(self._recentSettingsKey, paths[:5])
        self._updateRecentSettingsMenu()

    def changeSchematicCells(self):
        self.schematicLibItem = libm.getLibItem(
            self.model, self.schematicLibListCB.currentText()
        )
        if self.schematicLibItem is None:
            return
        schematicCellList = sorted(
            [
                self.schematicLibItem.child(i).cellName
                for i in range(self.schematicLibItem.rowCount())
            ]
        )
        self.schematicCellListCB.blockSignals(True)
        self.schematicCellListCB.clear()
        self.schematicCellListCB.addItems(schematicCellList)
        self.schematicCellListCB.blockSignals(False)
        self.changeSchematicCellViews()

    def changeSchematicCellViews(self):
        self.schematicCellItem = libm.getCellItem(
            self.schematicLibItem, self.schematicCellListCB.currentText()
        )
        if self.schematicCellItem is None:
            self.schematicCellViewListCB.clear()
            return
        schematicCellViewList = sorted(
            [
                self.schematicCellItem.child(i).text()
                for i in range(self.schematicCellItem.rowCount())
                if self.schematicCellItem.child(i).viewType == "schematic"
            ]
        )
        self.schematicCellViewListCB.clear()
        self.schematicCellViewListCB.addItems(schematicCellViewList)

    def _onSourceModeChanged(self, *args):
        """Toggle schematic vs netlist reference widgets based on source mode."""
        schematicMode = self.schematicModeBtn.isChecked()
        self.schematicGroupBox.setVisible(schematicMode)
        self.netlistGroupBox.setVisible(not schematicMode)
        # Schematic netlist generation only applies when a schematic is the
        # reference; an existing netlist file is used as-is.
        self.netlistBox.setEnabled(schematicMode)
        if not schematicMode:
            self.netlistBox.setChecked(False)

    def onNetlistFileButtonClicked(self):
        filePath, _ = QFileDialog.getOpenFileName(
            self,
            caption="Select Netlist File",
            filter="Netlist Files (*.cir *.sp *.spice *.net *.cdl);;All Files (*)",
        )
        if filePath:
            self.netlistFilePathEdit.setText(filePath)

    def exportGDSRows(self):
        if self.gdsExportBox.isChecked():
            self.exportGDSLayout.setRowVisible(1, True)
            self.exportGDSLayout.setRowVisible(2, True)
        else:
            self.exportGDSLayout.setRowVisible(1, False)
            self.exportGDSLayout.setRowVisible(2, False)

    def onkfilePathButtonClicked(self):
        self.klayoutPathEdit.setText(
            QFileDialog.getOpenFileName(self, caption="Select KLayout Executable")[0]
        )

    def onLVSRunPathButtonClicked(self):
        self.LVSRunPathEdit.setText(
            QFileDialog.getExistingDirectory(self, caption="Select LVS Run Path")
        )

    def _lockLayoutSelection(self):
        self.layoutLibListCB.clear()
        self.layoutLibListCB.addItem(self.layoutEditor.libName)
        self.layoutCellListCB.clear()
        self.layoutCellListCB.addItem(self.layoutEditor.cellName)
        self.layoutCellViewListCB.clear()
        self.layoutCellViewListCB.addItem(self.layoutEditor.viewName)
        self.layoutLibListCB.setEnabled(False)
        self.layoutCellListCB.setEnabled(False)
        self.layoutCellViewListCB.setEnabled(False)

    def collectSettings(self) -> dict:
        lvsSwitches = {
            attr: grp.checkedButton().text() == "True"
            for attr, grp in self.lvsSwitchGroups.items()
        }
        unitText = self.unitEdit.text().strip()
        precisionText = self.precisionEdit.text().strip()
        return {
            "klayoutPath": self.klayoutPathEdit.text().strip(),
            "lvsSourceMode": "netlist" if self.netlistModeBtn.isChecked() else "schematic",
            "netlistFilePath": self.netlistFilePathEdit.text().strip(),
            "schematicLibName": self.schematicLibListCB.currentText().strip(),
            "schematicCellName": self.schematicCellListCB.currentText().strip(),
            "schematicViewName": self.schematicCellViewListCB.currentText().strip(),
            "layoutLibName": self.layoutEditor.libName,
            "layoutCellName": self.layoutEditor.cellName,
            "layoutViewName": self.layoutEditor.viewName,
            "lvsRunLimit": self.LVSRunLimitEdit.text().strip(),
            "lvsRunPath": self.LVSRunPathEdit.text().strip(),
            "gdsExport": 1 if self.gdsExportBox.isChecked() else 0,
            "createNetlist": self.netlistBox.isChecked(),
            "exportPex": self.exportPexBox.isChecked(),
            "gdsUnit": Quantity(unitText).real if unitText else 0,
            "gdsPrecision": Quantity(precisionText).real if precisionText else 0,
            "implicitNets": self.implicitNetsEdit.text().strip(),
            "lvsSwitches": lvsSwitches,
            "runMode": self.runModeGroup.checkedButton().text().lower(),
        }

    def applySettings(self, settings: dict) -> None:
        """Apply settings dict to dialog fields.

        Maps JSON keys to the corresponding dialog widgets. Missing keys are
        silently skipped so that partial settings files work correctly.
        Validates filesystem paths (klayoutPath, lvsRunPath) after applying
        and logs warnings for paths that do not exist.

        Validates: Requirements 11.4, 11.6
        """
        if "klayoutPath" in settings:
            self.klayoutPathEdit.setText(settings["klayoutPath"])
        if "netlistFilePath" in settings:
            self.netlistFilePathEdit.setText(settings["netlistFilePath"])
        if "lvsSourceMode" in settings:
            if str(settings["lvsSourceMode"]).lower() == "netlist":
                self.netlistModeBtn.setChecked(True)
            else:
                self.schematicModeBtn.setChecked(True)
            self._onSourceModeChanged()
        if "lvsRunPath" in settings:
            self.LVSRunPathEdit.setText(settings["lvsRunPath"])
        if "lvsRunLimit" in settings:
            self.LVSRunLimitEdit.setText(str(settings["lvsRunLimit"]))
        if "gdsExport" in settings:
            self.gdsExportBox.setChecked(bool(settings["gdsExport"]))
        if "createNetlist" in settings:
            self.netlistBox.setChecked(bool(settings["createNetlist"]))
        if "exportPex" in settings:
            self.exportPexBox.setChecked(bool(settings["exportPex"]))
        if "gdsUnit" in settings and settings["gdsUnit"]:
            self.unitEdit.setText(str(settings["gdsUnit"]))
        if "gdsPrecision" in settings and settings["gdsPrecision"]:
            self.precisionEdit.setText(str(settings["gdsPrecision"]))
        if "implicitNets" in settings:
            self.implicitNetsEdit.setText(settings["implicitNets"])
        elif "implicit_nets" in settings:
            self.implicitNetsEdit.setText(settings["implicit_nets"])
        if "schematicLibName" in settings:
            self.schematicLibListCB.setCurrentText(settings["schematicLibName"])
        if "schematicCellName" in settings:
            self.schematicCellListCB.setCurrentText(settings["schematicCellName"])
        if "schematicViewName" in settings:
            self.schematicCellViewListCB.setCurrentText(settings["schematicViewName"])
        if "lvsSwitches" in settings:
            for attr, value in settings["lvsSwitches"].items():
                if attr in self.lvsSwitchGroups:
                    for btn in self.lvsSwitchGroups[attr].buttons():
                        if (btn.text() == "True") == value:
                            btn.setChecked(True)
                            break
        if "runMode" in settings:
            runMode = settings["runMode"].lower()
            if runMode == "deep":
                self.deepBtn.setChecked(True)
            elif runMode == "flat":
                self.flatBtn.setChecked(True)
        self._lockLayoutSelection()

        # Req 11.4: Validate filesystem paths and warn for missing ones
        path_warnings = []
        if "klayoutPath" in settings and settings["klayoutPath"]:
            if not pathlib.Path(settings["klayoutPath"]).exists():
                path_warnings.append(
                    f"KLayout path does not exist: {settings['klayoutPath']}"
                )
        if "lvsRunPath" in settings and settings["lvsRunPath"]:
            if not pathlib.Path(settings["lvsRunPath"]).exists():
                path_warnings.append(
                    f"LVS run path does not exist: {settings['lvsRunPath']}"
                )
        if path_warnings:
            for w in path_warnings:
                logger.warning(w)

    def _save_settings_to_file(self):
        """Prompt for file path and save current settings as JSON.

        Uses QFileDialog with JSON filter. 4-space indent.
        Validates: Requirements 11.1, 11.3
        """
        defaultPath = pathlib.Path(self.layoutEditor.gdsExportDirObj) / "lvsSettings.json"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save LVS Settings",
            str(defaultPath),
            "JSON Files (*.json);;All Files (*)",
        )
        if not filepath:
            return  # User cancelled

        settings = self.collectSettings()

        try:
            with open(filepath, "w") as f:
                json.dump(settings, f, indent=4)
            self._add_recent_settings(filepath)
            logger.info(f"LVS settings saved to {filepath}")
        except OSError as e:
            logger.error(f"Failed to save LVS settings to {filepath}: {e}")

    def _load_settings_from_file(self, filepath: str | None = None):
        """Prompt for file path and load settings from JSON.

        Shows warning for invalid filesystem paths.
        Logs errors for parse failures and retains current values.
        Validates: Requirements 11.2, 11.4, 11.5, 11.6
        """
        if filepath is None:
            filepath, _ = QFileDialog.getOpenFileName(
                self,
                "Load LVS Settings",
                "",
                "JSON Files (*.json);;All Files (*)",
            )
        if not filepath:
            return  # User cancelled

        # Try to parse the JSON file
        try:
            with open(filepath, "r") as f:
                settings = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            # Req 11.5: Log error, retain current values
            logger.error(f"Failed to load LVS settings from {filepath}: {e}")
            return

        # Req 11.4: Validate filesystem paths and warn for missing
        warnings = []
        if "klayoutPath" in settings:
            p = pathlib.Path(settings["klayoutPath"])
            if not p.exists():
                warnings.append(
                    f"KLayout path does not exist: {settings['klayoutPath']}"
                )

        if "lvsRunPath" in settings:
            p = pathlib.Path(settings["lvsRunPath"])
            if not p.exists():
                warnings.append(
                    f"LVS run path does not exist: {settings['lvsRunPath']}"
                )

        if warnings:
            QMessageBox.warning(
                self,
                "Path Validation Warning",
                "The following paths do not exist:\n\n"
                + "\n".join(warnings)
                + "\n\nRemaining settings will still be applied.",
            )

        # Req 11.6: Apply only keys present in file
        self.applySettings(settings)
        self._add_recent_settings(filepath)
        logger.info(f"LVS settings loaded from {filepath}")

    def appendLVSOutput(self, process) -> None:
        output = process.readAllStandardOutput().data().decode("utf-8")
        if output.strip():
            self.console.appendPlainText(output.rstrip())

    def appendLVSError(self, process) -> None:
        error = process.readAllStandardError().data().decode("utf-8")
        if error.strip():
            self.console.appendPlainText(f"[STDERR] {error.rstrip()}")
