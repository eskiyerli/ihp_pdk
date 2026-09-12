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

"""RC Extraction (PEX) callback for IHP SG13G2 PDK.

This module provides the menu callback for launching RC parasitic extraction
from the layout editor's Check menu. It is wired via config.json:

    {
      "menu": "Check",
      "action": "RCExtraction",
      "text": "RC Extraction (PEX)...",
      "module": "pexExtraction",
      "callback": "pexExtractionClick",
      "apply": ["layoutEditor"]
    }

The extraction flow requires:
1. A successful LVS run that produced a .rcx.json (via 'Export for PEX')
2. The IHP SG13G2 technology file (pex/ihp_sg13g2.json in this PDK)
3. The RC extraction module (revedaEditor.rcextraction), which ships with
   Revolution EDA
"""

import logging
import pathlib

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

logger = logging.getLogger("reveda")


def pexExtractionClick(layoutEditor):
    """Menu callback for Check → RC Extraction (PEX).

    Opens the PEX dialog which allows the user to configure and run
    parasitic extraction on the current layout cell.
    """
    dlg = pexExtractionDialogue(layoutEditor)
    dlg.show()


class pexExtractionDialogue(QDialog):
    """Dialog for configuring and running parasitic RC extraction."""

    def __init__(self, layoutEditor):
        super().__init__(layoutEditor)
        self.layoutEditor = layoutEditor
        self.setWindowTitle("RC Extraction (PEX) — IHP SG13G2")
        self.setMinimumWidth(550)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window)

        # Determine paths from the current cell
        self._cellName = layoutEditor.cellName
        self._libName = layoutEditor.libName
        self._layoutFile = layoutEditor.file  # Path to layout.json
        self._cellDir = self._layoutFile.parent

        # Locate the tech file from this PDK
        self._pdkDir = pathlib.Path(__file__).parent
        self._defaultTechFile = self._pdkDir / "pex" / "ihp_sg13g2.json"

        mainLayout = QVBoxLayout()

        # --- Input section ---
        inputGroup = QGroupBox("Input")
        inputLayout = QFormLayout()

        self.cellLabel = QLabel(f"{self._libName} / {self._cellName}")
        inputLayout.addRow("Cell:", self.cellLabel)

        # RCX database path. LVS writes <cell>.rcx.json into the LVS run
        # directory (the same default location the LVS dialog uses), not the
        # cell directory, so the library browser never sees it as a cellview.
        self._lvsRunDir = getattr(layoutEditor, "gdsExportDirObj", self._cellDir)
        self.rcxPathEdit = QLineEdit()
        rcxDefault = self._lvsRunDir / f"{self._cellName}.rcx.json"
        self.rcxPathEdit.setText(str(rcxDefault))
        rcxBrowseBtn = QPushButton("Browse...")
        rcxBrowseBtn.clicked.connect(self._browseRcxFile)
        rcxRow = QHBoxLayout()
        rcxRow.addWidget(self.rcxPathEdit)
        rcxRow.addWidget(rcxBrowseBtn)
        inputLayout.addRow("RCX Database:", rcxRow)

        # Tech file path (pre-filled from PDK)
        self.techPathEdit = QLineEdit()
        if self._defaultTechFile.exists():
            self.techPathEdit.setText(str(self._defaultTechFile))
        else:
            self.techPathEdit.setPlaceholderText("Path to technology JSON file")
        techBrowseBtn = QPushButton("Browse...")
        techBrowseBtn.clicked.connect(self._browseTechFile)
        techRow = QHBoxLayout()
        techRow.addWidget(self.techPathEdit)
        techRow.addWidget(techBrowseBtn)
        inputLayout.addRow("Tech File:", techRow)

        inputGroup.setLayout(inputLayout)
        mainLayout.addWidget(inputGroup)

        # --- Options section ---
        optionsGroup = QGroupBox("Extraction Options")
        optionsLayout = QFormLayout()

        self.cornerCombo = QComboBox()
        self.cornerCombo.addItems(["nom", "hrhc", "lrhc", "hrlc", "lrlc"])
        self.cornerCombo.setToolTip(
            "nom = Nominal\n"
            "hrhc = High Resistance, High Capacitance\n"
            "lrhc = Low Resistance, High Capacitance\n"
            "hrlc = High Resistance, Low Capacitance\n"
            "lrlc = Low Resistance, Low Capacitance"
        )
        optionsLayout.addRow("Process Corner:", self.cornerCombo)

        self.formatCombo = QComboBox()
        self.formatCombo.addItems(["spice", "vacask", "spef", "spectre"])
        optionsLayout.addRow("Output Format:", self.formatCombo)

        self.couplingCheck = QCheckBox("Extract inter-net coupling capacitance")
        self.couplingCheck.setChecked(True)
        optionsLayout.addRow("", self.couplingCheck)

        optionsGroup.setLayout(optionsLayout)
        mainLayout.addWidget(optionsGroup)

        # --- Output section ---
        outputGroup = QGroupBox("Output")
        outputLayout = QFormLayout()

        self.outputPathEdit = QLineEdit()
        outputDefault = self._cellDir / f"{self._cellName}.pex.spice"
        self.outputPathEdit.setText(str(outputDefault))
        outputBrowseBtn = QPushButton("Browse...")
        outputBrowseBtn.clicked.connect(self._browseOutputFile)
        outputRow = QHBoxLayout()
        outputRow.addWidget(self.outputPathEdit)
        outputRow.addWidget(outputBrowseBtn)
        outputLayout.addRow("Output File:", outputRow)

        outputGroup.setLayout(outputLayout)
        mainLayout.addWidget(outputGroup)

        # --- Status ---
        self.statusLabel = QLabel("")
        mainLayout.addWidget(self.statusLabel)

        # --- Buttons ---
        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox.accepted.connect(self._runExtraction)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText("Extract")
        mainLayout.addWidget(self.buttonBox)

        self.setLayout(mainLayout)

        # Update output path when format changes
        self.formatCombo.currentTextChanged.connect(self._updateOutputPath)

    def _browseRcxFile(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select RCX Database", str(self._cellDir),
            "RCX Files (*.rcx.json);;All Files (*)"
        )
        if path:
            self.rcxPathEdit.setText(path)

    def _browseTechFile(self):
        startDir = str(self._pdkDir / "pex") if self._pdkDir.exists() else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Technology File", startDir,
            "Tech Files (*.json);;All Files (*)"
        )
        if path:
            self.techPathEdit.setText(path)

    def _browseOutputFile(self):
        extMap = {"spice": "SPICE (*.spice)", "spef": "SPEF (*.spef)",
                  "spectre": "Spectre (*.scs)", "vacask": "VACASK (*.cir)"}
        fmt = self.formatCombo.currentText()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Extracted Netlist", str(self._cellDir),
            f"{extMap.get(fmt, 'All Files (*)')}"
        )
        if path:
            self.outputPathEdit.setText(path)

    def _updateOutputPath(self, fmt: str):
        extMap = {"spice": ".pex.spice", "spef": ".pex.spef", "spectre": ".pex.scs",
                  "vacask": ".pex.cir"}
        ext = extMap.get(fmt, ".pex.spice")
        self.outputPathEdit.setText(str(self._cellDir / f"{self._cellName}{ext}"))

    def _runExtraction(self):
        """Validate inputs and run the extraction."""
        rcxPath = pathlib.Path(self.rcxPathEdit.text().strip())
        techPath = pathlib.Path(self.techPathEdit.text().strip())
        outputPath = pathlib.Path(self.outputPathEdit.text().strip())

        # Validate RCX file
        if not rcxPath.exists():
            QMessageBox.critical(
                self, "RCX Database Not Found",
                f"Cannot find: {rcxPath}\n\n"
                f"You must run LVS with 'Export for PEX' enabled first.\n"
                f"Use: Check → LVS with KLayout (enable PEX export)"
            )
            return

        # Validate tech file
        if not techPath.exists():
            QMessageBox.critical(
                self, "Tech File Not Found",
                f"Cannot find: {techPath}\n\n"
                f"Please specify a valid technology JSON file."
            )
            return

        # Run extraction
        corner = self.cornerCombo.currentText()
        fmt = self.formatCombo.currentText()
        coupling = self.couplingCheck.isChecked()

        self.statusLabel.setText("Running extraction...")
        self.buttonBox.setEnabled(False)

        try:
            from revedaEditor.rcextraction.extractor import extract
            from revedaEditor.rcextraction.netlist import get_writer
            from revedaEditor.rcextraction.rcx_schema import load_rcx_database
            from revedaEditor.rcextraction.tech import load_tech_file

            # Load inputs
            techData = load_tech_file(techPath, corner=corner)
            rcxDb = load_rcx_database(rcxPath)

            if not rcxDb.lvs_equivalent:
                logger.warning(f"LVS did NOT pass for cell '{rcxDb.cell_name}'.")

            # Run extraction
            result = extract(rcxDb, techData, coupling=coupling)

            # Write output
            writer = get_writer(fmt)
            writer.write(result, outputPath)

            # Create cellview in the schematic cell for config view access
            self._createPexCellview(fmt, outputPath)

            self.statusLabel.setText(
                f"Done: {result.total_r} R, {result.total_c} C, "
                f"{len(result.devices)} devices → {outputPath.name}"
            )
            QMessageBox.information(
                self, "Extraction Complete",
                f"Parasitic extraction completed successfully.\n\n"
                f"Cell: {result.cell_name}\n"
                f"Devices: {len(result.devices)}\n"
                f"Resistors: {result.total_r}\n"
                f"Capacitors: {result.total_c}\n"
                f"Corner: {corner}\n\n"
                f"Output: {outputPath}\n"
                f"Cellview: pex_{fmt}"
            )
            self.accept()

        except ImportError as e:
            self.statusLabel.setText("Error: RC extraction module unavailable")
            QMessageBox.critical(
                self, "RC Extraction Module Unavailable",
                f"The RC extraction module (revedaEditor.rcextraction) could "
                f"not be imported.\n\n"
                f"This module ships with Revolution EDA, so this usually points "
                f"to a broken or incomplete installation.\n\n"
                f"Error: {e}"
            )
        except Exception as e:
            self.statusLabel.setText(f"Error: {e}")
            QMessageBox.critical(
                self, "Extraction Failed",
                f"RC extraction failed:\n\n{e}"
            )
        finally:
            self.buttonBox.setEnabled(True)

    def _createPexCellview(self, fmt: str, outputPath: pathlib.Path):
        """Create a cellview in the schematic cell so it appears in config view.

        The view uses the two-file convention:
        - A JSON stub (pex_<fmt>.json) with viewType pointing to the netlist file
        - The actual netlist file (already written by the extractor)

        The netlist file is copied/referenced in the schematic cell directory,
        making it available for simulation via switchViewList in config views.
        """
        import json
        import shutil
        import revedaEditor.backend.libBackEnd as libb

        # Map format to view name and file extension
        viewNameMap = {
            "spice": ("pex_spice", ".pex.spice"),
            "vacask": ("pex_vacask", ".pex.cir"),
            "spectre": ("pex_spectre", ".pex.scs"),
            "spef": ("pex_spef", ".pex.spef"),
        }

        viewName, ext = viewNameMap.get(fmt, (f"pex_{fmt}", f".pex.{fmt}"))

        # Find the schematic cell in the library model
        # The layout cell and schematic cell share the same cellItem parent
        cellItem = self.layoutEditor.cellItem
        cellDir = cellItem.cellPath

        # Copy the netlist into the cell directory if it's not already there
        targetNetlistPath = cellDir / f"{self._cellName}{ext}"
        if outputPath.resolve() != targetNetlistPath.resolve():
            shutil.copy2(outputPath, targetNetlistPath)

        # Create the JSON stub for this view
        viewStubPath = cellDir / f"{viewName}.json"
        stubContent = [
            {"viewType": viewName},
            {"filePath": f"{self._cellName}{ext}"},
        ]
        with viewStubPath.open("w", encoding="utf-8") as f:
            json.dump(stubContent, f, indent=2)

        # Add to the library model if not already present
        existingView = None
        for row in range(cellItem.rowCount()):
            child = cellItem.child(row)
            if child and child.viewName == viewName:
                existingView = child
                break

        if existingView is None:
            newViewItem = libb.viewItem(viewStubPath)
            cellItem.appendRow(newViewItem)
            logger.info(f"Created cellview: {self._libName}/{self._cellName}/{viewName}")
        else:
            logger.info(f"Updated cellview: {self._libName}/{self._cellName}/{viewName}")
