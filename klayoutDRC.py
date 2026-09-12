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

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (QVBoxLayout, QGroupBox, QHBoxLayout,
                               QFileDialog, QComboBox, QLabel, QPlainTextEdit,
                               QPushButton, QFormLayout, QScrollArea, QSplitter,
                               QWidget, QCheckBox, QMainWindow)
from quantiphy import Quantity

import revedaEditor.backend.editFunctions as edf
import revedaEditor.gui.layoutDialogues as ldlg
from revedaEditor.backend.pdkLoader import importPDKModule

logger = logging.getLogger("reveda")

process = importPDKModule('process')

# Rule-set registry for the modular IHP-SG13G2 KLayout DRC rundeck.
# Each entry maps a user-visible run-set name to the rule deck file (relative to
# the PDK ``drc`` package directory) and any extra ``-rd name=value`` switches
# that select the intended subset of checks. All decks share the common
# variable contract: ``input`` (GDS), ``report`` (lyrdb), ``log`` (log file),
# ``threads`` and ``run_mode``; those are added at run time.
#
# The main deck (``ihp-sg13g2.drc``) is table driven and pulls its rule decks in
# via KLayout ``# %include`` directives, while ``density``/``antenna``/
# ``maximal`` are standalone decks shipped under ``rule_decks``.
DRC_RULE_SETS = {
    "main": {
        "file": "ihp-sg13g2.drc",
        "switches": {"tables": "main"},
    },
    "precheck": {
        "file": "ihp-sg13g2.drc",
        "switches": {"tables": "main", "precheck_drc": "true"},
    },
    "density": {
        "file": "rule_decks/density.drc",
        "switches": {},
    },
    "antenna": {
        "file": "rule_decks/antenna.drc",
        "switches": {},
    },
    "maximal": {
        "file": "rule_decks/sg13g2_maximal.drc",
        "switches": {},
    },
}

# Shared default DRC rule-values JSON (relative to the PDK ``drc`` package dir).
# The decks default ``$drc_json`` to a process-specific tech JSON that only
# exists in the upstream IHP tree layout; when it is missing they abort. We pin
# ``drc_json`` to this shipped default so the tech-override branch is skipped and
# the run stays self-contained.
DRC_DEFAULT_JSON = "rule_decks/sg13g2_tech_default.json"


def klayoutDRCClick(editorwindow):
    # klayoutDRCModule = importPDKModule("klayoutDRC")
    # if klayoutDRCModule is None:
    #     editorwindow.logger.error('PDK does not allow DRC verification with KLayout.')
    #     return

    def loadRunSet(dlg):
        filePath, _ = QFileDialog.getOpenFileName(
            dlg, caption="Load DRC Settings", filter="JSON Files (*.json)"
        )
        if not filePath:
            return
        try:
            with open(filePath) as f:
                settings = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error(f"Failed to load DRC settings from {filePath}: {exc}")
            return
        dlg.applySettings(settings)
        logger.info(f"DRC settings loaded from {filePath}")

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

    def DRCProcessFinished(filePath: pathlib.Path, dlg: 'drcKLayoutDialogue'):
        dlg.console.appendPlainText(f"\n--- DRC Finished. Report: {filePath} ---")
        errorsDlg = ldlg.drcErrorsDialogue(editorwindow, filePath.resolve())
        errorsDlg.drcTable.polygonSelected.connect(editorwindow.handlePolygonSelection)
        errorsDlg.drcTable.zoomToRect.connect(editorwindow.centralW.scene.zoomToRect)
        errorsDlg.show()

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
            ruleSet = DRC_RULE_SETS.get(drcRunSetName)
            if ruleSet is None:
                editorwindow.logger.error(
                    f'Unknown DRC run set: {drcRunSetName}')
                return
            drcRuleFilePath = drcPath.joinpath(ruleSet["file"])
            if not drcRuleFilePath.exists():
                editorwindow.logger.error(
                    f'DRC rule deck not found: {drcRuleFilePath}')
                return
            drcReportFilePath = drcRunPathObj.joinpath(f'{cellName}.lyrdb')
            drcLogFilePath = drcRunPathObj.joinpath(f'{cellName}_drc.log')
            # Common variable contract shared by every deck in the modular
            # rundeck (see ihp-sg13g2.drc / rule_decks/*.drc file setup).
            drcVariables = {
                "input": str(gdsPath),
                "report": str(drcReportFilePath),
                "log": str(drcLogFilePath),
                "topcell": cellName,
                "run_mode": "deep",
                "threads": str(drcRunLimit),
            }
            # Pin the rule-values JSON to the shipped default so decks that read
            # it (main/precheck/density/antenna) do not abort trying to load the
            # upstream process-specific tech JSON, which is absent here.
            defaultJsonPath = drcPath.joinpath(DRC_DEFAULT_JSON)
            if defaultJsonPath.exists():
                drcVariables["drc_json"] = str(defaultJsonPath)
                drcVariables["drc_json_default"] = str(defaultJsonPath)
            drcVariables.update(ruleSet["switches"])
            argumentsList = ['-b', '-r', f'{drcRuleFilePath}']
            for name, value in drcVariables.items():
                argumentsList.extend(['-rd', f'{name}={value}'])
            editorwindow.processManager.maxProcesses = int(drcRunLimit)
            dlg.console.appendPlainText("--- DRC Started ---")
            drcProcess = editorwindow.processManager.add_process(klayoutPath,
                                                            argumentsList)
            # Redirect process output to dialog console instead of main logger
            try:
                drcProcess.process.readyReadStandardOutput.disconnect()
            except RuntimeError:
                pass
            drcProcess.process.readyReadStandardOutput.connect(
                lambda: dlg.appendDRCOutput(drcProcess.process))
            drcProcess.process.readyReadStandardError.connect(
                lambda: dlg.appendDRCError(drcProcess.process))
            drcProcess.process.finished.connect(
                lambda: DRCProcessFinished(drcReportFilePath, dlg))
        else:
            editorwindow.logger.error('GDS file can not be found')

    dlg = drcKLayoutDialogue(editorwindow)
    drc = importPDKModule("drc")
    if drc is None:
        editorwindow.logger.error('PDK does not have DRC module.')
        return
    drcPath = pathlib.Path(drc.__file__).parent.resolve()
    # Offer only the run sets whose rule deck is actually present in the PDK.
    rulesFiles = [
        name for name, ruleSet in DRC_RULE_SETS.items()
        if drcPath.joinpath(ruleSet["file"]).exists()
    ]
    if not rulesFiles:
        editorwindow.logger.error(
            'No DRC rule decks found in the PDK drc directory.')
        return
    dlg.DRCRunSetCB.addItems(rulesFiles)
    dlg.runDRCAction.triggered.connect(lambda: runKlayoutDRC(dlg))
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


class drcKLayoutDialogue(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parentEditor = parent

        self.setMinimumSize(1000, 500)
        self.setWindowTitle("KLayout DRC")
        self.setWindowModality(Qt.WindowModality.NonModal)
        self._settings = QSettings("Revolution Semiconductor", "Revolution EDA")
        self._recentSettingsKey = "ihpKlayoutDRC/recentSettings"
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
        # DRCOptionsGroupBox = QGroupBox("DRC Options")

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

        mainLayout.addStretch()

        # Wrap the form in a scroll area (left panel of splitter)
        formWidget = QWidget()
        formWidget.setLayout(mainLayout)
        scrollArea = QScrollArea()
        scrollArea.setWidget(formWidget)
        scrollArea.setWidgetResizable(True)
        scrollArea.setMinimumWidth(480)

        # Console panel (right panel of splitter)
        consoleWidget = QWidget()
        consoleLayout = QVBoxLayout(consoleWidget)
        consoleLayout.addWidget(QLabel("DRC Output:"))
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
        centralWidget = QWidget()
        centralWidget.setLayout(outerLayout)
        self.setCentralWidget(centralWidget)
        self._createMenuBar()
        self.show()

    def _createMenuBar(self):
        menuBar = self.menuBar()
        menuBar.setNativeMenuBar(False)
        fileMenu = menuBar.addMenu("&File")
        self.loadSettingsAction = QAction(
            QIcon(":/icons/document-import.png"), "Load DRC Settings...", self
        )
        self.loadSettingsAction.triggered.connect(self._load_settings_from_file)
        fileMenu.addAction(self.loadSettingsAction)
        self.saveSettingsAction = QAction(
            QIcon(":/icons/disk.png"), "Save DRC Settings...", self
        )
        self.saveSettingsAction.triggered.connect(self._save_settings_to_file)
        fileMenu.addAction(self.saveSettingsAction)
        fileMenu.addSeparator()
        self.recentSettingsMenu = fileMenu.addMenu("Recent DRC Settings")
        self._updateRecentSettingsMenu()
        fileMenu.addSeparator()
        self.closeAction = QAction(QIcon(":/icons/external.png"), "Close", self)
        self.closeAction.triggered.connect(self.close)
        fileMenu.addAction(self.closeAction)

        self.runDRCAction = QAction(
            QIcon(":/icons/application-run.png"), "Run DRC", self
        )
        self.runDRCAction.setShortcut("F5")
        menuBar.addMenu("&Run").addAction(self.runDRCAction)

        toolsMenu = menuBar.addMenu("&Tools")
        self.selectKlayoutAction = QAction(
            QIcon(":/icons/external.png"), "Select KLayout Executable...", self
        )
        self.selectKlayoutAction.triggered.connect(self.onkfilePathButtonClicked)
        toolsMenu.addAction(self.selectKlayoutAction)
        self.selectRunPathAction = QAction(
            QIcon(":/icons/document.png"), "Select DRC Run Path...", self
        )
        self.selectRunPathAction.triggered.connect(self.onDRCRunPathButtonClicked)
        toolsMenu.addAction(self.selectRunPathAction)
        self.clearConsoleAction = QAction(
            QIcon(":/icons/eraser.png"), "Clear DRC Output", self
        )
        self.clearConsoleAction.triggered.connect(self.console.clear)
        toolsMenu.addAction(self.clearConsoleAction)

        self.drcToolBar = self.addToolBar("DRC")
        self.drcToolBar.setObjectName("drcToolBar")
        self.drcToolBar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        for action in (
            self.runDRCAction, self.loadSettingsAction, self.saveSettingsAction,
            self.selectKlayoutAction, self.selectRunPathAction,
            self.clearConsoleAction, self.closeAction,
        ):
            self.drcToolBar.addAction(action)

    def _recent_settings(self) -> list[str]:
        values = self._settings.value(self._recentSettingsKey, [])
        if isinstance(values, str):
            values = [values]
        return [str(path) for path in values if path]

    def _updateRecentSettingsMenu(self):
        self.recentSettingsMenu.clear()
        paths = self._recent_settings()
        if not paths:
            action = self.recentSettingsMenu.addAction("No recent settings")
            action.setEnabled(False)
            return
        for path in paths:
            settingsPath = pathlib.Path(path)
            action = self.recentSettingsMenu.addAction(settingsPath.name)
            action.setToolTip(path)
            if settingsPath.exists():
                action.triggered.connect(
                    lambda checked=False, path=path: self._load_settings_from_file(path)
                )
            else:
                action.setEnabled(False)

    def _add_recent_settings(self, filepath: str):
        paths = [filepath] + [path for path in self._recent_settings() if path != filepath]
        self._settings.setValue(self._recentSettingsKey, paths[:5])
        self._updateRecentSettingsMenu()

    def _settings_dict(self) -> dict:
        return {
            "klayoutPath": self.klayoutPathEdit.text().strip(),
            "cellName": self.cellNameEdit.text().strip(),
            "drcRunSetName": self.DRCRunSetCB.currentText().strip(),
            "drcRunLimit": self.DRCRunLimitEdit.text().strip(),
            "drcRunPath": self.DRCRunPathEdit.text().strip(),
            "gdsExport": 1 if self.gdsExportBox.isChecked() else 0,
            "gdsUnit": Quantity(self.unitEdit.text().strip()).real,
            "gdsPrecision": Quantity(self.precisionEdit.text().strip()).real,
        }

    def _save_settings_to_file(self):
        defaultPath = pathlib.Path(self.parentEditor.gdsExportDirObj) / "drcSettings.json"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save DRC Settings", str(defaultPath),
            "JSON Files (*.json);;All Files (*)"
        )
        if not filepath:
            return
        try:
            with open(filepath, "w") as settingsFile:
                json.dump(self._settings_dict(), settingsFile, indent=4)
        except (OSError, ValueError) as exc:
            logger.error(f"Failed to save DRC settings to {filepath}: {exc}")
            return
        self._add_recent_settings(filepath)
        logger.info(f"DRC settings saved to {filepath}")

    def _load_settings_from_file(self, filepath=None):
        if filepath is None:
            filepath, _ = QFileDialog.getOpenFileName(
                self, "Load DRC Settings", "",
                "JSON Files (*.json);;All Files (*)"
            )
        if not filepath:
            return
        try:
            with open(filepath) as settingsFile:
                settings = json.load(settingsFile)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error(f"Failed to load DRC settings from {filepath}: {exc}")
            return
        self.applySettings(settings)
        self._add_recent_settings(filepath)
        logger.info(f"DRC settings loaded from {filepath}")

    def applySettings(self, settings: dict) -> None:
        """Apply settings dict to dialog fields.

        Missing keys are silently skipped so that partial settings files
        work correctly.
        """
        if "klayoutPath" in settings:
            self.klayoutPathEdit.setText(settings["klayoutPath"])
        if "cellName" in settings:
            self.cellNameEdit.setText(settings["cellName"])
        if "drcRunSetName" in settings:
            self.DRCRunSetCB.setCurrentText(settings["drcRunSetName"])
        if "drcRunLimit" in settings:
            self.DRCRunLimitEdit.setText(str(settings["drcRunLimit"]))
        if "drcRunPath" in settings:
            self.DRCRunPathEdit.setText(settings["drcRunPath"])
        if "gdsExport" in settings:
            self.gdsExportBox.setChecked(bool(settings["gdsExport"]))
        if "gdsUnit" in settings and settings["gdsUnit"]:
            self.unitEdit.setText(str(settings["gdsUnit"]))
        if "gdsPrecision" in settings and settings["gdsPrecision"]:
            self.precisionEdit.setText(str(settings["gdsPrecision"]))

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

    def appendDRCOutput(self, process) -> None:
        output = process.readAllStandardOutput().data().decode("utf-8")
        if output.strip():
            self.console.appendPlainText(output.rstrip())

    def appendDRCError(self, process) -> None:
        error = process.readAllStandardError().data().decode("utf-8")
        if error.strip():
            self.console.appendPlainText(f"[STDERR] {error.rstrip()}")
