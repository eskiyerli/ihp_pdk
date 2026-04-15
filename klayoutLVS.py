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

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
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
from revedaEditor.backend.pdkLoader import importPDKModule
import revedaEditor.common.net as snet
# import revedaEditor.common.shapes as shp
from revedaEditor.gui.schematicEditor import schematicEditor, xyceNetlist

process = importPDKModule("process")
logger = logging.getLogger("reveda")

SYMBOL_PIN_DISTANCE = 80
SYMBOL_STUB_LENGHT = 20



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


    # def createSchematicSymbol(device:dict, fixedFont: QFont, libraryDict: dict):
    #     cellType = device['type']
    #     instanceName = device['name']

    #     # Try to find the real symbol in libraries
    #     symbolBox = _loadLibrarySymbol(cellType, instanceName, libraryDict)
    #     if symbolBox:
    #         return symbolBox

    #     # Fallback: create generic symbol
    #     terminalNames = list(device['terminals'].keys())
    #     numTerminals = len(terminalNames)
    #     pinsPerSide = max(1, (numTerminals + 3) // 4)
    #     symbolSideLength = pinsPerSide * SYMBOL_PIN_DISTANCE

    #     rectItem = shp.symbolRectangle(QPoint(0, 0), QPoint(symbolSideLength, symbolSideLength))
    #     textItem = shp.text(
    #         rectItem.start,
    #         f'{instanceName}',
    #         fixedFont.family(),
    #         fixedFont.styleName(),
    #         str(fixedFont.pointSize()),
    #         shp.text.textAlignments[0],
    #         shp.text.textOrients[0],
    #     )
    #     instNameLabel = shp.symbolLabel(
    #         QPoint(symbolSideLength // 2, symbolSideLength // 2 - 15),
    #         "[@instName]",
    #         "NLPLabel",
    #         12,
    #         "Center",
    #         "R0",
    #         "Normal",
    #     )
    #     instNameLabel.labelVisible = True

    #     instCellLabel = shp.symbolLabel(
    #         QPoint(symbolSideLength // 2 - 15, symbolSideLength // 2 + 15),
    #         "[@cellName]",
    #         "NLPLabel",
    #         12,
    #         "Center",
    #         "R0",
    #         "Normal",
    #     )
    #     instCellLabel.labelVisible = True

    #     pinItems = []
    #     sides = ['left', 'top', 'right', 'bottom']
    #     sideIndex = 0
    #     pinIndexOnSide = 0

    #     for i, termName in enumerate(terminalNames):
    #         side = sides[sideIndex]
    #         if side == 'left':
    #             x = -SYMBOL_STUB_LENGHT // 2
    #             y = (pinIndexOnSide + 0.5) * SYMBOL_PIN_DISTANCE
    #         elif side == 'top':
    #             x = (pinIndexOnSide + 0.5) * SYMBOL_PIN_DISTANCE
    #             y = -SYMBOL_STUB_LENGHT // 2
    #         elif side == 'right':
    #             x = symbolSideLength + SYMBOL_STUB_LENGHT // 2
    #             y = (pinIndexOnSide + 0.5) * SYMBOL_PIN_DISTANCE
    #         else:
    #             x = int((pinIndexOnSide + 0.5) * SYMBOL_PIN_DISTANCE)
    #             y = int(symbolSideLength + SYMBOL_STUB_LENGHT // 2)

    #         pinItem = shp.symbolPin(QPoint(x, y), termName, 'Inout', 'Signal')
    #         pinItems.append(pinItem)

    #         pinIndexOnSide += 1
    #         if pinIndexOnSide >= pinsPerSide:
    #             pinIndexOnSide = 0
    #             sideIndex = (sideIndex + 1) % 4

    #     attrs = {'pinOrder': ', '.join(terminalNames)}
    #     symbolBox = shp.schematicSymbol([rectItem, textItem, instNameLabel, instCellLabel] + pinItems, attrs)
    #     symbolBox.instanceName = instanceName
    #     symbolBox.cellName = cellType
    #     instNameLabel.labelDefs()
    #     instNameLabel.setOpacity(1)
    #     instCellLabel.labelDefs()
    #     instCellLabel.setOpacity(1)
    #     return symbolBox

    @lru_cache(maxsize=16)
    def findSymbolViewNameTuple(extractedCellName: str, libraryModel: QStandardItemModel):
        """Find (libName, cellName, viewName) tuple for a cell type."""
        print(extractedCellName)
        
        root = libraryModel.invisibleRootItem()
        
        # Iterate through libraries (level 0)
        for libRow in range(root.rowCount()):
            libItem = root.child(libRow)  # libraryItem
            libName = libItem.libraryName
            
            # Iterate through cells in this library (level 1)
            for cellRow in range(libItem.rowCount()):
                cellItem = libItem.child(cellRow)  # cellItem
                if cellItem.cellName == extractedCellName:
                    # Found the cell, now look for symbol view (level 2)
                    for viewRow in range(cellItem.rowCount()):
                        viewItem = cellItem.child(viewRow)  # viewItem
                        if viewItem.viewName == "symbol":
                            return ddef.viewNameTuple(libName, extractedCellName, "symbol")
                            
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
        from lvs.lvsdb_parser import LVSDBParser
        layoutLayers = importPDKModule('layoutLayers')
        parser = LVSDBParser(filePath, layoutLayers)
        parser.load()
        logger.info(f"Parsed LVSDB: {parser.filepath}")
        extracted = parser.get_extracted_schematic(layoutEditor.cellName)
        if extracted:
            from revedaEditor.gui.schematicEditor import schematicEditor
            import revedaEditor.backend.libBackEnd as libb
            # schLayers: ModuleType | None = importPDKModule('schLayers')

            revedaMain = QApplication.instance().appMainW

            # Create temporary filepath
            tempViewFilePath = layoutEditor.cellItem.cellPath.joinpath(
                "lvs_schematic.json"
            )
            tempViewItem = libb.viewItem(tempViewFilePath)
            layoutEditor.cellItem.appendRow(tempViewItem)
            tempSchematicEditor = schematicEditor(
                tempViewItem, revedaMain.libraryDict, revedaMain.libraryBrowser
            )
            snapToGrid = tempSchematicEditor.centralW.scene.snapToGrid
            devices = extracted["devices"]

            # Get layout device positions and cross-reference mapping
            layout_devices = parser.get_devices(layoutEditor.cellName)
            xref = parser.get_crossref(layoutEditor.cellName)

            # Build mapping: schematic device name -> layout position
            schem_to_layout_pos = {}
            if xref and layout_devices:
                # Build layout device ID -> position lookup
                layout_pos_by_id = {d['id']: d.get('position') for d in layout_devices}
                # Map schematic devices to layout positions via cross-reference
                for mapping in xref.get('mapping', {}).get('devices', []):
                    layout_dev = mapping.get('layout_dev')
                    schem_dev = mapping.get('schem_dev')
                    if layout_dev in layout_pos_by_id:
                        schem_to_layout_pos[schem_dev] = layout_pos_by_id[layout_dev]

            for device in devices:
                symbolViewNameTuple = findSymbolViewNameTuple(device['type'], revedaMain.libraryModel)
                if symbolViewNameTuple is None:
                    logger.warning(f"Could not find symbol for device: {device}")
                    continue
                # Use layout position if available, otherwise fallback to device index
                schem_dev_id = device.get('id')
                layout_pos = schem_to_layout_pos.get(schem_dev_id)

                if layout_pos:
                    # Scale layout coordinates to schematic units (e.g., divide by 10)
                    snappedPos = snapToGrid(QPoint(layout_pos[0] / 5, layout_pos[1] / 5))
                    symbolItem = tempSchematicEditor.centralW.scene.instSymbol(symbolViewNameTuple, snappedPos)
                    symbolItem.setPos(snappedPos)
                else:
                    symbolItem = tempSchematicEditor.centralW.scene.instSymbol(symbolViewNameTuple, QPoint(0, 0))
                symbolItem.instanceName = device['name']
                symbolItem.labels['@instName'].labelDefs()
                tempSchematicEditor.centralW.scene.addItem(symbolItem)
                br = symbolItem.boundingRect()
                center = br.center()

                for pinName, pinItem in symbolItem.pins.items():
                    localPos = pinItem.start
                    pinScenePos = pinItem.mapToScene(localPos)
                    dx = localPos.x() - center.x()
                    dy = localPos.y() - center.y()
                    
                    if abs(dx) > abs(dy):
                        side = "left" if dx < 0 else "right"
                    else:
                        side = "top" if dy < 0 else "bottom"
                

                    # Determine side based on local position relative to rectangle
                    if side == "left":
                        pinNetItem = snet.schematicNet(pinScenePos, pinScenePos-QPoint(30,0), 1, 0)
                        name =  device['terminals'].get(pinName)
                        if name:
                            pinNetItem.name = name

                    elif side == "right":
                        pinNetItem = snet.schematicNet(pinScenePos, pinScenePos+QPoint(30,0), 1, 0)
                        name =  device['terminals'].get(pinName)
                        if name:
                            pinNetItem.name = name
                    elif side == "top":
                        pinNetItem = snet.schematicNet(pinScenePos, pinScenePos-QPoint(0,30), 1, 0)
                        name =  device['terminals'].get(pinName)   
                        if name:
                            pinNetItem.name = name                 
                    else:
                        pinNetItem = snet.schematicNet(pinScenePos, pinScenePos+QPoint(0,30), 1, 0)
                        name =  device['terminals'].get(pinName)    
                    if name:
                            pinNetItem.name = name
                    tempSchematicEditor.centralW.scene.addItem(pinNetItem)
            tempSchematicEditor.show()
        # now starting parsing layout data



    def runKlayoutLVS(dlg):
        settings = dlg.collectSettings()
        klayoutPath = settings["klayoutPath"]
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
        schematicNetlistPathObj = (
            lvsRunPathObj / f"{schematicCellName}_{schematicViewName}.cir"
        )

        if gdsExport:
            layoutEditor.centralW.scene.exportCellGDS(
                lvsRunPathObj, gdsUnit, gdsPrecision, process.dbu
            )

        if createNetlist:
            createSchematicNetlist(dlg, lvsRunPathObj)
        else:
            logger.info(
                "Schematic netlist generation is disabled; running in NET_ONLY mode."
            )

        if not netOnly and not schematicNetlistPathObj.exists():
            logger.error(
                f"Schematic netlist file not found at {schematicNetlistPathObj}. "
                f"Please check the netlist creation settings and try again."
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
            argumentsList.extend(
                ["-rd", f"{switchName}={'true' if enabled else 'false'}"]
            )

        if implicitNets:
            argumentsList.extend(["-rd", f"implicit_nets={implicitNets}"])

        layoutEditor.processManager.maxProcesses = int(lvsRunLimit)
        dlg.console.appendPlainText("--- LVS Started ---")
        lvsProcess = layoutEditor.processManager.add_process(klayoutPath, argumentsList)
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
        lvsProcess.process.finished.connect(
            lambda: LVSProcessFinished(lvsReportFilePath, lvsExtractedNetlistPath, dlg)
        )

    def createSchematicNetlist(dlg, lvsRunPathObj):
        settings = dlg.collectSettings()
        schematicLibName: str = settings["schematicLibName"]
        schematicCellName: str = settings["schematicCellName"]
        schematicViewName: str = settings["schematicViewName"]
        libItem = libm.getLibItem(dlg.model, schematicLibName)
        cellItem = libm.getCellItem(libItem, schematicCellName)
        viewItem = libm.getViewItem(cellItem, schematicViewName)
        schematicE: schematicEditor = schematicEditor(
            viewItem, dlg.model.libraryDict, dlg.layoutEditor.libraryView
        )
        schematicE.loadSchematic()
        schematicNetlistPathObj: pathlib.Path = (
            lvsRunPathObj / f"{schematicCellName}_{schematicViewName}.cir"
        )
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
    dlg.runButton.clicked.connect(lambda: runKlayoutLVS(dlg))
    dlg.saveButton.clicked.connect(lambda: saveRunSet(dlg))
    dlg.loadButton.clicked.connect(lambda: loadRunSet(dlg))
    dlg.show()


class klayoutLVSDialogue(QDialog):
    def __init__(self, parentEditor):
        super().__init__(parentEditor)
        self.layoutEditor = parentEditor
        self.model = parentEditor.libraryView.libraryModel
        self.setWindowTitle("KLayout LVS")
        self.setMinimumSize(1100, 700)
        self.mainLayout = QVBoxLayout()
        hLayout = QHBoxLayout()
        self.mainLayout.addLayout(hLayout)
        schematicGroupBox = QGroupBox("Schematic")
        schematicLayout = QFormLayout()
        schematicGroupBox.setLayout(schematicLayout)
        self.schematicLibListCB = QComboBox()
        self.schematicLibListCB.setModel(self.model)
        self.schematicLibListCB.setModelColumn(0)
        self.schematicLibListCB.currentTextChanged.connect(self.changeSchematicCells)
        self.schematicLibItem = libm.getLibItem(
            self.model, self.schematicLibListCB.currentText()
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
        self.schematicCellListCB.currentTextChanged.connect(
            self.changeSchematicCellViews
        )
        self.schematicCellItem = libm.getCellItem(
            self.schematicLibItem, self.schematicCellListCB.currentText()
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
        netlistLayout.addRow(
            edf.boldLabel("Create Schematic Netlist:"), self.netlistBox
        )
        self.mainLayout.addWidget(netlistGroupBox)

        lvsOptionsGroup = QGroupBox("LVS Options")
        lvsOptionsLayout = QVBoxLayout()
        lvsOptionsLayout.setSpacing(10)
        klayoutPathDialogueLayout = QHBoxLayout()
        klayoutPathDialogueLayout.addWidget(
            edf.boldLabel("KLayout Executable Path:"), 1
        )
        self.klayoutPathEdit = edf.longLineEdit()
        klayoutPathDialogueLayout.addWidget(self.klayoutPathEdit, 5)
        self.rootPathButton = QPushButton("...")
        self.rootPathButton.clicked.connect(self.onkfilePathButtonClicked)
        klayoutPathDialogueLayout.addWidget(self.rootPathButton, 1)
        lvsOptionsLayout.addLayout(klayoutPathDialogueLayout)

        lvsRunPathLayout = QHBoxLayout()
        lvsRunPathLayout.addWidget(edf.boldLabel("LVS Run Path:"), 1)
        self.LVSRunPathEdit = edf.longLineEdit()
        lvsRunPathLayout.addWidget(self.LVSRunPathEdit, 5)
        self.lvsRunPathButton = QPushButton("...")
        self.lvsRunPathButton.clicked.connect(self.onLVSRunPathButtonClicked)
        lvsRunPathLayout.addWidget(self.lvsRunPathButton, 1)
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
            ("purge", "Remove Floating Devices"),
            ("purge_nets", "Remove Floating Nets"),
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

        self.runButton = QPushButton("Run LVS")
        self.saveButton = QPushButton("Save LVS Config")
        self.loadButton = QPushButton("Load LVS Config")
        self.closeButton = QPushButton("Close")
        self.buttonBox = QDialogButtonBox()
        self.buttonBox.addButton(self.loadButton, QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(self.saveButton, QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(self.runButton, QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(self.closeButton, QDialogButtonBox.RejectRole)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)

        # Wrap the form in a scroll area (left panel of splitter)
        formWidget = QWidget()
        formWidget.setLayout(self.mainLayout)
        scrollArea = QScrollArea()
        scrollArea.setWidget(formWidget)
        scrollArea.setWidgetResizable(True)
        scrollArea.setMinimumWidth(580)

        # Console panel (right panel of splitter)
        consoleWidget = QWidget()
        consoleLayout = QVBoxLayout(consoleWidget)
        consoleLayout.addWidget(QLabel("LVS Output:"))
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMinimumWidth(400)
        clearConsoleButton = QPushButton("Clear Console")
        clearConsoleButton.clicked.connect(self.console.clear)
        consoleLayout.addWidget(self.console)
        consoleLayout.addWidget(clearConsoleButton)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(scrollArea)
        splitter.addWidget(consoleWidget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        outerLayout = QHBoxLayout()
        outerLayout.addWidget(splitter)
        self.setLayout(outerLayout)
        self.show()

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
            "gdsUnit": Quantity(unitText).real if unitText else 0,
            "gdsPrecision": Quantity(precisionText).real if precisionText else 0,
            "implicitNets": self.implicitNetsEdit.text().strip(),
            "lvsSwitches": lvsSwitches,
            "runMode": self.runModeGroup.checkedButton().text().lower(),
        }

    def applySettings(self, settings: dict) -> None:
        if "klayoutPath" in settings:
            self.klayoutPathEdit.setText(settings["klayoutPath"])
        if "lvsRunPath" in settings:
            self.LVSRunPathEdit.setText(settings["lvsRunPath"])
        if "lvsRunLimit" in settings:
            self.LVSRunLimitEdit.setText(str(settings["lvsRunLimit"]))
        if "gdsExport" in settings:
            self.gdsExportBox.setChecked(bool(settings["gdsExport"]))
        if "createNetlist" in settings:
            self.netlistBox.setChecked(bool(settings["createNetlist"]))
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

    def appendLVSOutput(self, process) -> None:
        output = process.readAllStandardOutput().data().decode("utf-8")
        if output.strip():
            self.console.appendPlainText(output.rstrip())

    def appendLVSError(self, process) -> None:
        error = process.readAllStandardError().data().decode("utf-8")
        if error.strip():
            self.console.appendPlainText(f"[STDERR] {error.rstrip()}")
