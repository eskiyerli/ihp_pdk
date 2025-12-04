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

import pathlib
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QGroupBox, QHBoxLayout,
                               QFileDialog, QComboBox,
                               QDialogButtonBox, QPushButton, QFormLayout,
                               QCheckBox)

import revedaEditor.backend.editFunctions as edf
from revedaEditor.backend.pdkLoader import importPDKModule
process = importPDKModule('process')


def klayoutDRCClick(editorwindow):
    klayoutDRCModule = importPDKModule("klayoutDRC")
    if klayoutDRCModule is None:
        editorwindow.logger.error('PDK does not allow DRC verification with KLayout.')
        return

    def saveRunSet(dlg):
        klayoutPath = dlg.klayoutPathEdit.text().strip()
        cellName = dlg.cellNameEdit.text().strip()
        drcRunSetName = dlg.DRCRunSetCB.currentText().strip()
        drcRunLimit = dlg.DRCRunLimitEdit.text().strip()
        drcRunPath = dlg.DRCRunPathEdit.text().strip()
        gdsExport = 1 if dlg.gdsExportBox.isChecked() else 0
        gdsUnit = Quantity(dlg.unitEdit.text().strip()).real
        gdsPrecision = Quantity(dlg.precisionEdit.text().strip()).real
        drcRunPathObj = pathlib.Path(drcRunPath)
        drcRunPathObj.mkdir(parents=True, exist_ok=True)
        settingsPathObj = drcRunPathObj / 'drcSettings.json'
        with settingsPathObj.open('w') as f:
            json.dump({'klayoutPath': klayoutPath, 'cellName': cellName,
                        'drcRunSetName': drcRunSetName, 'drcRunLimit':
                            drcRunLimit, 'drcRunPath': drcRunPath,
                        'gdsExport': gdsExport, 'gdsUnit': gdsUnit,
                        'gdsPrecision': gdsPrecision}, f, indent=4)

    def DRCProcessFinished(filePath: pathlib.Path):
        dlg = ldlg.drcErrorsDialogue(editorwindow, filePath.resolve())
        dlg.drcTable.polygonSelected.connect(editorwindow.handlePolygonSelection)
        dlg.show()

    def runKlayoutDRC(dlg):
        klayoutPath = dlg.klayoutPathEdit.text().strip()
        cellName = dlg.cellNameEdit.text().strip()
        drcRunSetName = dlg.DRCRunSetCB.currentText().strip()
        drcRunLimit = dlg.DRCRunLimitEdit.text().strip()
        drcRunPath = dlg.DRCRunPathEdit.text().strip()
        gdsExport = 1 if dlg.gdsExportBox.isChecked() else 0
        gdsUnit = Quantity(dlg.unitEdit.text().strip()).real
        gdsPrecision = Quantity(dlg.precisionEdit.text().strip()).real
        drcRunPathObj = pathlib.Path(drcRunPath)
        drcRunPathObj.mkdir(parents=True, exist_ok=True)
        if gdsExport:
            editorwindow.centralW.scene.exportCellGDS(drcRunPathObj, gdsUnit,
                                                gdsPrecision, process.dbu)
        if (drcRunPathObj / f'{cellName}.gds').exists():
            gdsPath = drcRunPathObj.joinpath(f'{cellName}.gds')
            drcPath = pathlib.Path(drc.__file__).parent.resolve()
            drcRuleFilePath = drcPath.joinpath(f'{drcRunSetName}.lydrc')
            drcReportFilePath = drcRunPathObj.joinpath(f'{cellName}.lyrdb')
            argumentsList = ['-b', '-r',
                                f'{drcRuleFilePath}',
                                '-rd',
                                f'in_gds={gdsPath}',
                                '-rd',
                                f'report_file={drcReportFilePath}']
            editorwindow.processManager.maxProcesses = int(drcRunLimit)
            drcProcess = editorwindow.processManager.add_process(klayoutPath,
                                                            argumentsList)
            drcProcess.process.finished.connect(
                lambda: DRCProcessFinished(drcReportFilePath))
        else:
            editorwindow.logger.error('GDS file can not be found')

    dlg = klayoutDRCModule.drcKLayoutDialogue(editorwindow)
    drc = importPDKModule("drc")
    if drc is None:
        editorwindow.logger.error('PDK does not have DRC module.')
        return
    drcPath = pathlib.Path(drc.__file__).parent.resolve()
    rulesFiles = [pathItem.stem for pathItem in list(drcPath.glob("*.lydrc"))]
    dlg.DRCRunSetCB.addItems(rulesFiles)
    dlg.saveButton.clicked.connect(lambda: saveRunSet(dlg))
    dlg.runButton.clicked.connect(lambda: runKlayoutDRC(dlg))
    settingsPathObj = (editorwindow.gdsExportDirObj / 'drcSettings.json')
    if settingsPathObj.exists():
        try:
            with settingsPathObj.open('r') as f:
                settings = json.load(f)
                dlg.klayoutPathEdit.setText(settings['klayoutPath'])
                dlg.cellNameEdit.setText(settings['cellName'])
                dlg.DRCRunSetCB.setCurrentText(settings['drcRunSetName'])
                dlg.DRCRunLimitEdit.setText(settings['drcRunLimit'])
                dlg.DRCRunPathEdit.setText(settings['drcRunPath'])
                dlg.gdsExportBox.setChecked(bool(settings['gdsExport']))
                dlg.unitEdit.setText(str(settings['gdsUnit']))
                dlg.precisionEdit.setText(str(settings['gdsPrecision']))
        except Exception as e:
            editorwindow.logger.error(e)
    else:
        dlg.gdsExportBox.setChecked(False)
        dlg.cellNameEdit.setText(editorwindow.cellName)
        dlg.DRCRunSetCB.setCurrentIndex(0)
        dlg.DRCRunLimitEdit.setText('2')
        dlg.DRCRunPathEdit.setText(str(editorwindow.gdsExportDirObj))
        if hasattr(process, "gdsUnit"):
            dlg.unitEdit.setText(process.gdsUnit.render())
        if hasattr(process, "gdsPrecision"):
            dlg.precisionEdit.setText(process.gdsPrecision.render())

    dlg.show()


class drcKLayoutDialogue(QDialog):
    def __init__(self, parent=None):
        self.parent = parent
        super().__init__(parent)
        self.setMinimumSize(500, 500)
        self.setWindowTitle("Revolution EDA Options")
        mainLayout = QVBoxLayout()
        mainLayout.setSpacing(20)

        filePathsGroup = QGroupBox("DRC Options")
        filePathsLayout = QVBoxLayout()
        filePathsLayout.setSpacing(10)
        klayoutPathDialogueLayout = QHBoxLayout()
        klayoutPathDialogueLayout.addWidget(
            edf.boldLabel("KLayout Executable Path:"), 1)
        self.klayoutPathEdit = edf.longLineEdit()
        klayoutPathDialogueLayout.addWidget(self.klayoutPathEdit, 5)
        self.rootPathButton = QPushButton("...")
        self.rootPathButton.clicked.connect(self.onkfilePathButtonClicked)
        klayoutPathDialogueLayout.addWidget(self.rootPathButton, 1)
        filePathsLayout.addLayout(klayoutPathDialogueLayout)
        cellNameLayout = QHBoxLayout()
        cellNameLayout.addWidget(edf.boldLabel("Cell Name:"), 1)
        self.cellNameEdit = edf.longLineEdit()
        cellNameLayout.addWidget(self.cellNameEdit)
        filePathsLayout.addLayout(cellNameLayout)

        drcRunSetDialogueLayout = QHBoxLayout()
        drcRunSetDialogueLayout.addWidget(edf.boldLabel("DRC Run Set:"), 2)
        self.DRCRunSetCB = QComboBox()
        self.DRCRunSetCB.currentIndexChanged.connect(self.onDRCRunSetChanged)
        drcRunSetDialogueLayout.addWidget(self.DRCRunSetCB, 5)
        filePathsLayout.addLayout(drcRunSetDialogueLayout)
        DRCOptionsGroupBox = QGroupBox("DRC Options")

        drcRunLimitDialogueLayout = QHBoxLayout()
        drcRunLimitDialogueLayout.addWidget(edf.boldLabel("DRC Run Limit:"), 2)
        self.DRCRunLimitEdit = edf.longLineEdit()
        drcRunLimitDialogueLayout.addWidget(self.DRCRunLimitEdit)
        filePathsLayout.addLayout(drcRunLimitDialogueLayout)

        drcRunPathLayout = QHBoxLayout()
        drcRunPathLayout.addWidget(edf.boldLabel("DRC Run Path:"), 1)
        self.DRCRunPathEdit = edf.longLineEdit()
        drcRunPathLayout.addWidget(self.DRCRunPathEdit, 5)
        self.drcRunPathButton = QPushButton("...")
        self.drcRunPathButton.clicked.connect(self.onDRCRunPathButtonClicked)
        drcRunPathLayout.addWidget(self.drcRunPathButton, 1)
        filePathsLayout.addLayout(drcRunPathLayout)
        filePathsGroup.setLayout(filePathsLayout)
        mainLayout.addWidget(filePathsGroup)

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
        mainLayout.addWidget(exportGroupBox)
        mainLayout.addSpacing(20)

        self.runButton = QPushButton("Run DRC")
        self.saveButton = QPushButton("Save DRC Config")
        self.closeButton = QPushButton("Close")
        self.buttonBox = QDialogButtonBox()
        # self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel)
        self.buttonBox.addButton(self.saveButton, QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(self.runButton, QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(self.closeButton, QDialogButtonBox.RejectRole)
        self.buttonBox.rejected.connect(self.reject)

        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)
        self.show()

    def onkfilePathButtonClicked(self):
        self.klayoutPathEdit.setText(
            QFileDialog.getOpenFileName(self,
                                        caption="Select KLayout Executable")[0]
        )

    def onDRCRunPathButtonClicked(self):
        self.DRCRunPathEdit.setText(
            QFileDialog.getExistingDirectory(self, caption="Select DRC Run Path")
        )

    def exportGDSRows(self):
        if self.gdsExportBox.isChecked():
            self.exportGDSLayout.setRowVisible(1, True)
            self.exportGDSLayout.setRowVisible(2, True)
        else:
            self.exportGDSLayout.setRowVisible(1, False)
            self.exportGDSLayout.setRowVisible(2, False)

    def onDRCRunSetChanged(self, index: int):
        print(index)
