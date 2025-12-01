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


from ast import main
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QGroupBox, QHBoxLayout, QFileDialog, QComboBox,
                               QDialogButtonBox, QPushButton, QFormLayout, QCheckBox)

from revedaEditor.backend.pdkPaths import importPDKModule

import revedaEditor.backend.editFunctions as edf

from pathlib import Path


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
        klayoutPathDialogueLayout.addWidget(edf.boldLabel("KLayout Executable Path:"), 1)
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
        drcRunSetDialogueLayout.addWidget(self.DRCRunSetCB, 5)
        filePathsLayout.addLayout(drcRunSetDialogueLayout)
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
        mainLayout.addWidget(exportGroupBox)
        mainLayout.addSpacing(20)

        self.runButton = QPushButton("Run DRC")
        self.saveButton = QPushButton("Save DRC Config.")
        self.buttonBox = QDialogButtonBox()
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel)
        self.buttonBox.addButton(self.saveButton, QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(self.runButton, QDialogButtonBox.ActionRole)
        self.buttonBox.rejected.connect(self.reject)

        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)
        self.show()

    def onkfilePathButtonClicked(self):
        self.klayoutPathEdit.setText(
            QFileDialog.getOpenFileName(self, caption="Select KLayout Executable")[0]
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
