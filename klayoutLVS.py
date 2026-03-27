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


import json
import logging
import pathlib
import time
from contextlib import contextmanager

from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QPushButton,
    QRadioButton, QVBoxLayout,
)
from quantiphy import Quantity

import revedaEditor.backend.editFunctions as edf
import revedaEditor.backend.libraryMethods as libm
from revedaEditor.backend.pdkLoader import importPDKModule
from revedaEditor.gui.schematicEditor import schematicEditor, xyceNetlist

process = importPDKModule('process')
logger = logging.getLogger('reveda')

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
    lvs = importPDKModule('lvs')
    if lvs is None:
        logger.error("LVS module not found. Please ensure the LVS module is available and try again.")
        return

    def saveRunSet(dlg):
        settings = dlg.collectSettings()
        lvsRunPathObj = pathlib.Path(settings['lvsRunPath'])
        lvsRunPathObj.mkdir(parents=True, exist_ok=True)
        settingsPathObj = lvsRunPathObj / 'lvsSettings.json'
        with settingsPathObj.open('w') as f:
            json.dump(settings, f, indent=4)
        logger.info(f"LVS settings saved to {settingsPathObj}")

    def LVSProcessFinished(filePath: pathlib.Path):
        logger.info(f"LVS process finished. Report: {filePath}")

    def runKlayoutLVS(dlg):
        settings = dlg.collectSettings()
        klayoutPath = settings['klayoutPath']
        schematicCellName = settings['schematicCellName']
        schematicViewName = settings['schematicViewName']
        layoutCellName = settings['layoutCellName']
        lvsRunLimit = settings['lvsRunLimit']
        lvsRunPath = settings['lvsRunPath']
        gdsExport = settings['gdsExport']
        lvsSwitches = settings['lvsSwitches']
        createNetlist = settings['createNetlist']
        netOnly = not createNetlist
        gdsUnit = settings['gdsUnit']
        gdsPrecision = settings['gdsPrecision']
        implicitNets = settings['implicitNets']
        runMode = settings['runMode']
        lvsRunPathObj = pathlib.Path(lvsRunPath)
        lvsRunPathObj.mkdir(parents=True, exist_ok=True)

        lvsPath = pathlib.Path(lvs.__file__).parent.resolve()
        lvsRulePath = lvsPath / 'sg13g2.lvs'
        schematicNetlistPathObj = lvsRunPathObj / f"{schematicCellName}_{schematicViewName}.cir"

        if gdsExport:
            layoutEditor.centralW.scene.exportCellGDS(lvsRunPathObj, gdsUnit, gdsPrecision, process.dbu)

        if createNetlist:
            createSchematicNetlist(dlg, lvsRunPathObj)
        else:
            logger.info("Schematic netlist generation is disabled; running in NET_ONLY mode.")

        if not netOnly and not schematicNetlistPathObj.exists():
            logger.error(
                f"Schematic netlist file not found at {schematicNetlistPathObj}. "
                f"Please check the netlist creation settings and try again."
            )
            return

        gdsPath = lvsRunPathObj / f'{layoutCellName}.gds'
        if not gdsPath.exists():
            logger.error(f"GDS file not found at {gdsPath}. Please check the GDS export settings and try again.")
            return

        lvsReportFilePath = lvsRunPathObj / f'{layoutCellName}.lvsdb'
        argumentsList = [
            '-b', '-r', str(lvsRulePath),
            '-rd', f'input={gdsPath}',
            '-rd', f'topcell={layoutCellName}',
            '-rd', f'report={lvsReportFilePath}',
            '-rd', f'net_only={'true' if netOnly else 'false'}',
            '-rd', f'run_mode={runMode}',
        ]
        if not netOnly:
            argumentsList.extend(['-rd', f'schematic={schematicNetlistPathObj}'])

        for switchName, enabled in lvsSwitches.items():
            argumentsList.extend(['-rd', f'{switchName}={'true' if enabled else 'false'}'])

        if implicitNets:
            argumentsList.extend(['-rd', f'implicit_nets={implicitNets}'])

        layoutEditor.processManager.maxProcesses = int(lvsRunLimit)
        lvsProcess = layoutEditor.processManager.add_process(klayoutPath, argumentsList)
        lvsProcess.process.finished.connect(lambda: LVSProcessFinished(lvsReportFilePath))

    def createSchematicNetlist(dlg, lvsRunPathObj):
        settings = dlg.collectSettings()
        schematicLibName:str = settings['schematicLibName']
        schematicCellName:str = settings['schematicCellName']
        schematicViewName:str = settings['schematicViewName']
        libItem = libm.getLibItem(dlg.model, schematicLibName)
        cellItem = libm.getCellItem(libItem, schematicCellName)
        viewItem = libm.getViewItem(cellItem, schematicViewName)
        schematicE:schematicEditor  = schematicEditor(viewItem, dlg.model.libraryDict, dlg.layoutEditor.libraryView)
        schematicE.loadSchematic()
        schematicNetlistPathObj:pathlib.Path = lvsRunPathObj / f"{schematicCellName}_{schematicViewName}.cir"
        netlistObj = xyceNetlist(schematicE, schematicNetlistPathObj, False, True)
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
        self.setMinimumSize(600, 900)
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
        self.schematicLibItem = libm.getLibItem(self.model, self.schematicLibListCB.currentText())
        schematicLayout.addRow("Library:", self.schematicLibListCB)

        self.schematicCellListCB = QComboBox()
        schematicCellList = sorted(
            [self.schematicLibItem.child(i).cellName for i in range(self.schematicLibItem.rowCount())])
        self.schematicCellListCB.addItems(schematicCellList)
        self.schematicCellListCB.setEditable(True)
        self.schematicCellListCB.currentTextChanged.connect(self.changeSchematicCellViews)
        self.schematicCellItem = libm.getCellItem(self.schematicLibItem, self.schematicCellListCB.currentText())
        schematicLayout.addRow("Cell:", self.schematicCellListCB)

        self.schematicCellViewListCB = QComboBox()
        self.schematicCellViewListCB.setEditable(True)
        self.schematicCellViewListCB.addItems(sorted([self.schematicCellItem.child(i).text() for i in range(self.schematicCellItem.rowCount()) if self.schematicCellItem.child(i).viewType == 'schematic']))
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
        self.exportGDSLayout.addRow(edf.boldLabel("Export GDS:"),
                                    self.gdsExportBox)
        self.unitEdit = edf.shortLineEdit()
        self.unitEdit.setToolTip("The unit of the GDS file.")
        self.exportGDSLayout.addRow(edf.boldLabel("Unit:"), self.unitEdit)
        self.precisionEdit = edf.shortLineEdit()
        self.precisionEdit.setToolTip("The precision of the GDS file.")
        self.exportGDSLayout.addRow(edf.boldLabel("Precision:"),
                                    self.precisionEdit)
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
        self.mainLayout.addWidget(netlistGroupBox)

        lvsOptionsGroup = QGroupBox("LVS Options")
        lvsOptionsLayout = QVBoxLayout()
        lvsOptionsLayout.setSpacing(10)
        klayoutPathDialogueLayout = QHBoxLayout()
        klayoutPathDialogueLayout.addWidget(
            edf.boldLabel("KLayout Executable Path:"), 1)
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
            ("no_net_names",               "No Net Names"),
            ("spice_comments",             "Spice Comments"),
            ("top_lvl_pins",             "Top Level Pins"),
            ("ignore_top_ports_mismatch",  "Ignore Top Ports Mismatch"),
            ("no_simplify",               "No Simplify"),
            ("no_series_res",        "No Series Resistors"),
            ("no_parallel_res",      "No Parallel Resistors"),
            ("combine_devices",            "Combine Devices"),
            ("purge",    "Remove Floating Devices"),
            ("purge_nets",       "Remove Floating Nets"),
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
        self.setLayout(self.mainLayout)
        self.show()

    def changeSchematicCells(self):
        self.schematicLibItem = libm.getLibItem(self.model, self.schematicLibListCB.currentText())
        if self.schematicLibItem is None:
            return
        schematicCellList = sorted([self.schematicLibItem.child(i).cellName for i in range(self.schematicLibItem.rowCount())])
        self.schematicCellListCB.blockSignals(True)
        self.schematicCellListCB.clear()
        self.schematicCellListCB.addItems(schematicCellList)
        self.schematicCellListCB.blockSignals(False)
        self.changeSchematicCellViews()

    def changeSchematicCellViews(self):
        self.schematicCellItem = libm.getCellItem(self.schematicLibItem, self.schematicCellListCB.currentText())
        if self.schematicCellItem is None:
            self.schematicCellViewListCB.clear()
            return
        schematicCellViewList = sorted([self.schematicCellItem.child(i).text() for i in range(self.schematicCellItem.rowCount()) if self.schematicCellItem.child(i).viewType == 'schematic'])
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
            QFileDialog.getOpenFileName(self,
                                        caption="Select KLayout Executable")[0])

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
        lvsSwitches = {attr: grp.checkedButton().text() == "True"
                       for attr, grp in self.lvsSwitchGroups.items()}
        unitText = self.unitEdit.text().strip()
        precisionText = self.precisionEdit.text().strip()
        return {
            'klayoutPath': self.klayoutPathEdit.text().strip(),
            'schematicLibName': self.schematicLibListCB.currentText().strip(),
            'schematicCellName': self.schematicCellListCB.currentText().strip(),
            'schematicViewName': self.schematicCellViewListCB.currentText().strip(),
            'layoutLibName': self.layoutEditor.libName,
            'layoutCellName': self.layoutEditor.cellName,
            'layoutViewName': self.layoutEditor.viewName,
            'lvsRunLimit': self.LVSRunLimitEdit.text().strip(),
            'lvsRunPath': self.LVSRunPathEdit.text().strip(),
            'gdsExport': 1 if self.gdsExportBox.isChecked() else 0,
            'createNetlist': self.netlistBox.isChecked(),
            'gdsUnit': Quantity(unitText).real if unitText else 0,
            'gdsPrecision': Quantity(precisionText).real if precisionText else 0,
            'implicitNets': self.implicitNetsEdit.text().strip(),
            'lvsSwitches': lvsSwitches,
            'runMode': self.runModeGroup.checkedButton().text().lower(),
        }

    def applySettings(self, settings: dict) -> None:
        if 'klayoutPath' in settings:
            self.klayoutPathEdit.setText(settings['klayoutPath'])
        if 'lvsRunPath' in settings:
            self.LVSRunPathEdit.setText(settings['lvsRunPath'])
        if 'lvsRunLimit' in settings:
            self.LVSRunLimitEdit.setText(str(settings['lvsRunLimit']))
        if 'gdsExport' in settings:
            self.gdsExportBox.setChecked(bool(settings['gdsExport']))
        if 'createNetlist' in settings:
            self.netlistBox.setChecked(bool(settings['createNetlist']))
        if 'gdsUnit' in settings and settings['gdsUnit']:
            self.unitEdit.setText(str(settings['gdsUnit']))
        if 'gdsPrecision' in settings and settings['gdsPrecision']:
            self.precisionEdit.setText(str(settings['gdsPrecision']))
        if 'implicitNets' in settings:
            self.implicitNetsEdit.setText(settings['implicitNets'])
        elif 'implicit_nets' in settings:
            self.implicitNetsEdit.setText(settings['implicit_nets'])
        if 'schematicLibName' in settings:
            self.schematicLibListCB.setCurrentText(settings['schematicLibName'])
        if 'schematicCellName' in settings:
            self.schematicCellListCB.setCurrentText(settings['schematicCellName'])
        if 'schematicViewName' in settings:
            self.schematicCellViewListCB.setCurrentText(settings['schematicViewName'])
        if 'lvsSwitches' in settings:
            for attr, value in settings['lvsSwitches'].items():
                if attr in self.lvsSwitchGroups:
                    for btn in self.lvsSwitchGroups[attr].buttons():
                        if (btn.text() == "True") == value:
                            btn.setChecked(True)
                            break
        if 'runMode' in settings:
            runMode = settings['runMode'].lower()
            if runMode == 'deep':
                self.deepBtn.setChecked(True)
            elif runMode == 'flat':
                self.flatBtn.setChecked(True)
        self._lockLayoutSelection()
