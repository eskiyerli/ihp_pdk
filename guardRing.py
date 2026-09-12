########################################################################
#
# Copyright 2025 Revolution Semiconductor
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
########################################################################

"""Guard ring generator for the IHP SG13G2 PDK.

``Edit -> Guard Ring -> Substrate Tap (p+)`` lets the user drag a rectangle
in the layout view and places a parametric ``guardRing`` PCell around it.
The ring is generated as a multi-part path: parallel ``layoutPath`` segments
on Activ, pSD and Metal1 share the same rectangular centreline, with a Cont
array connecting Metal1 to the diffusion.  Like the ``subtap`` PCell, it
carries no Substrate marker or 'sub!' TEXT, so LVS keeps it in the substrate
net.  Place a Metal1.text label over the ring metal to name the net.
"""

from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGraphicsRectItem,
)

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule

fabproc = importPDKModule('process')
sg13_tech = importPDKModule('sg13_tech')

_dbu = fabproc.dbu if fabproc else 1000  # scene units per um
_tp = sg13_tech.SG13_Tech().techParams if sg13_tech else {}

_contSize = _tp.get("Cnt_a", 0) * _dbu
_contDist = _tp.get("Cnt_b", 0) * _dbu
_contDiffOver = _tp.get("Cnt_c", 0) * _dbu
_contMetalEndcap = _tp.get("M1_c1", 0) * _dbu
# Minimum ring width: one contact plus the larger of the Activ or Metal1
# enclosure on each side.
_minRingWidth = _contSize + 2 * max(_contDiffOver, _contMetalEndcap)


def _findPdkLibraryName(editorWindow, cellName: str = "guardRing") -> str:
    """Return the loaded PDK library name that contains ``cellName/pcell.json``."""
    for libName, libPath in editorWindow.libraryDict.items():
        if (libPath / cellName / "pcell.json").exists():
            return libName
    return ""


class _guardRingDialog(QDialog):
    """Ring width and gap parameters, in um."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Substrate Guard Ring")
        formLayout = QFormLayout(self)

        self.widthSpinBox = QDoubleSpinBox(self)
        self.widthSpinBox.setRange(_minRingWidth / _dbu, 100.0)
        self.widthSpinBox.setValue(0.6)
        self.widthSpinBox.setSingleStep(0.05)
        self.widthSpinBox.setSuffix(" um")

        self.gapSpinBox = QDoubleSpinBox(self)
        self.gapSpinBox.setRange(0.0, 100.0)
        self.gapSpinBox.setValue(0.5)
        self.gapSpinBox.setSingleStep(0.1)
        self.gapSpinBox.setSuffix(" um")

        formLayout.addRow("Ring width:", self.widthSpinBox)
        formLayout.addRow("Gap from rectangle:", self.gapSpinBox)

        buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        formLayout.addRow(buttonBox)


class _ringRectGrabber(QObject):
    """One-shot rubber-band rectangle capture on the layout view.

    Installed as an event filter on the view's viewport so mouse events are
    consumed before the scene's active mode sees them. Left-drag defines the
    guide rectangle; right-click or Esc cancels.
    """

    def __init__(self, editorWindow, onDone):
        super().__init__(editorWindow)
        self._editorWindow = editorWindow
        self._view = editorWindow.centralW.view
        self._scene = editorWindow.centralW.scene
        self._onDone = onDone
        self._start = None
        self._rubber = None

    def start(self):
        self._view.viewport().installEventFilter(self)
        self._view.installEventFilter(self)
        self._editorWindow.messageLine.setText(
            "Guard ring: drag a rectangle (right-click or Esc to cancel)")

    def _finish(self, rect=None):
        self._view.viewport().removeEventFilter(self)
        self._view.removeEventFilter(self)
        if self._rubber is not None:
            self._scene.removeItem(self._rubber)
            self._rubber = None
        self._editorWindow.messageLine.setText("")
        self._editorWindow._guardRingGrabber = None
        if rect is not None:
            self._onDone(rect)

    def _snapPos(self, event):
        return self._scene.snapToGrid(
            self._view.mapToScene(event.pos()).toPoint())

    def eventFilter(self, obj, event):
        etype = event.type()
        if etype == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.RightButton:
                self._finish()
                return True
            if event.button() == Qt.MouseButton.LeftButton \
                    and self._start is None:
                self._start = self._snapPos(event)
                pen = QPen(QColor(255, 160, 0), 0, Qt.PenStyle.DashLine)
                pen.setCosmetic(True)
                self._rubber = QGraphicsRectItem()
                self._rubber.setPen(pen)
                self._rubber.setZValue(1e9)
                self._rubber.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                self._scene.addItem(self._rubber)
                return True
        elif etype == QEvent.Type.MouseMove and self._start is not None:
            self._rubber.setRect(QRectF(
                QPointF(self._start),
                QPointF(self._snapPos(event))).normalized())
            return True
        elif etype == QEvent.Type.MouseButtonRelease \
                and event.button() == Qt.MouseButton.LeftButton \
                and self._start is not None:
            rect = QRectF(
                QPointF(self._start),
                QPointF(self._snapPos(event))).normalized()
            self._start = None
            self._finish(
                rect if rect.width() > 0 and rect.height() > 0 else None)
            return True
        elif etype == QEvent.Type.KeyPress \
                and event.key() == Qt.Key.Key_Escape:
            self._finish()
            return True
        return False


def _commitRing(scene, rect, widthUm, gapUm):
    """Create a guardRing PCell instance around ``rect``."""
    libName = _findPdkLibraryName(scene.editorWindow)
    if not libName:
        scene.editorWindow.messageLine.setText(
            "Guard ring: PDK library not found.")
        return

    from .pcells.guardRing import guardRing

    w_um = rect.width() / _dbu
    h_um = rect.height() / _dbu

    pcell = guardRing()
    pcell(f"{w_um}u", f"{h_um}u", f"{widthUm}u", f"{gapUm}u")

    pcell.libraryName = libName
    pcell.cellName = "guardRing"
    pcell.viewName = "pcell"
    scene.itemCounter += 1
    pcell.counter = scene.itemCounter
    pcell.instanceName = f"I{pcell.counter}"
    pcell.setPos(rect.topLeft())

    scene.addUndoStack(pcell)
    scene.editorWindow.messageLine.setText(
        f"Guard ring pcell created ({len(pcell.shapes)} shapes). "
        "Label the ring metal on Metal1.text to name the substrate net.")


def guardRingClick(editorWindow):
    """Edit -> Guard Ring -> Substrate Tap (p+) callback."""
    scene = editorWindow.centralW.scene

    def _onRect(rect):
        dialog = _guardRingDialog(editorWindow)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            _commitRing(
                scene, rect,
                dialog.widthSpinBox.value(), dialog.gapSpinBox.value())

    # A selected rect doubles as the guide, e.g. an NWell or prBoundary
    # rectangle around the block to guard.
    selectedRects = [
        item for item in scene.selectedItems()
        if isinstance(item, lshp.layoutRect)
    ]
    if selectedRects:
        _onRect(selectedRects[0].sceneBoundingRect())
        return

    # Keep a reference on the window or the grabber is garbage collected
    # while it is still installed as an event filter.
    editorWindow._guardRingGrabber = _ringRectGrabber(editorWindow, _onRect)
    editorWindow._guardRingGrabber.start()
