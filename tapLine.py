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

"""Tap line generator for the IHP SG13G2 PDK.

``Create -> Substrate Tap -> P+ Tap Line`` / ``N-Well Tap Line`` lets the
user click a polyline in the layout view and places a parametric
``psubtap``/``nwelltap`` PCell strip along every segment, mirroring the
Draw Path interaction: the first left-click anchors the strip and each
further click commits the in-flight segment and starts the next one.  The
live preview is the pcell itself, so all layers are visible while
drawing.  A press-drag-release also works, since vertices are placed at
the release position.  The dominant axis of a segment sets its direction;
horizontal segments rotate the pcell -90 degrees so its length axis lies
along x.  Like a drawn path, every segment overlaps its end points by
half a strip width, so consecutive strips share one coincident contact
at each vertex and the corner square stays covered on every layer.
Right-click or Esc ends the line, dropping a trailing zero-length
segment.  Like the ``subtap`` PCell the strip carries no
marker layers or pins, so LVS keeps it in the substrate/well net.  Place
a Metal1.text label over the line to name the net.
"""

from PySide6.QtCore import QEvent, QObject, QPointF, Qt

from revedaEditor.backend.pdkLoader import importPDKModule
from .guardRing import _findPdkLibraryName

fabproc = importPDKModule('process')
sg13_tech = importPDKModule('sg13_tech')

_dbu = fabproc.dbu if fabproc else 1000  # scene units per um
_tp = sg13_tech.SG13_Tech().techParams if sg13_tech else {}
# Minimum strip length in scene units: one contact plus Activ overlap on
# each side, matching the clamp inside the psubtap/nwelltap pcells.
# Requesting anything shorter only makes the pcell warn and clamp, so the
# draft is built at this floor directly.
_minTapDbu = (_tp.get("Cnt_a", 0) + 2 * _tp.get("Cnt_c", 0)) * _dbu
# Segments shorter than half the strip width cannot produce a real
# strip, so clicks below this extent are ignored as click slop.
_minSegDbu = max(_minTapDbu / 2, 1)


class _tapLineGrabber(QObject):
    """Click-to-click tap line capture on the layout view.

    Installed as an event filter on the view's viewport so mouse events
    are consumed before the scene's active mode sees them.  Each
    in-progress segment is a real pcell instance already pushed on the
    undo stack, so committed segments survive Esc and Ctrl+Z removes them
    one at a time, exactly like Draw Path.
    """

    def __init__(self, editorWindow, cellName, pcellClass, libName):
        super().__init__(editorWindow)
        self._editorWindow = editorWindow
        self._view = editorWindow.centralW.view
        self._scene = editorWindow.centralW.scene
        self._cellName = cellName
        self._pcellClass = pcellClass
        self._libName = libName
        self._start = None        # anchor of the in-progress segment
        self._draft = None        # in-progress pcell segment
        self._segLength = 0       # current segment extent in scene units
        self._draftLength = 0     # length in scene units last built
        self._draftCentreX = 0.0  # x-centre of the draft's shapes
        self._segments = 0

    def start(self):
        self._view.viewport().installEventFilter(self)
        self._view.installEventFilter(self)
        self._editorWindow.messageLine.setText(
            f"{self._cellName} line: click the first point, click again "
            "for each vertex (right-click or Esc to finish)")

    def _snapPos(self, event):
        return self._scene.snapToGrid(
            self._view.mapToScene(event.pos()).toPoint())

    def _makeDraft(self, point):
        """Push a new, still empty, segment pcell anchored at ``point``."""
        pcell = self._pcellClass()
        pcell.libraryName = self._libName
        pcell.cellName = self._cellName
        pcell.viewName = "pcell"
        self._scene.itemCounter += 1
        pcell.counter = self._scene.itemCounter
        pcell.instanceName = f"I{pcell.counter}"
        pcell.setPos(point)
        self._scene.addUndoStack(pcell)
        self._draft = pcell
        self._segLength = 0
        self._draftLength = 0
        self._draftCentreX = 0.0

    def _updateDraft(self, point):
        """Stretch the in-progress pcell from ``_start`` to ``point``.

        The strip follows the dominant axis: vertical segments place the
        cell unrotated, horizontal ones rotate it -90 degrees (local +y
        -> +x) so the diffusion centreline stays pinned on the line
        through the anchor point.  Like a drawn path, every segment
        overlaps its end points by half a strip width: consecutive
        strips share one coincident contact at the vertex and the corner
        square stays covered on every layer.  The pcell is only rebuilt
        when the snapped length changes.
        """
        draft = self._draft
        dx = point.x() - self._start.x()
        dy = point.y() - self._start.y()
        horizontal = abs(dx) > abs(dy)
        length = abs(dx) if horizontal else abs(dy)
        self._segLength = length
        if length < _minSegDbu:
            # Too short to form a strip: nothing to show yet.
            draft.setVisible(False)
            return
        draft.setVisible(True)
        # Extend past both end points by half the strip width.
        back = _minTapDbu / 2
        buildLength = length + 2 * back
        if buildLength != self._draftLength:
            draft(f"{buildLength / _dbu}u")
            self._draftLength = buildLength
            self._draftCentreX = draft.childrenBoundingRect().center().x()
        if horizontal:
            # Rotate about the local origin: (x, y) -> (y, -x), so the
            # strip extends +x and its centreline lands centreX above
            # the position.
            draft.angle = -90
            pos = QPointF(
                min(self._start.x(), point.x()) - back,
                self._start.y() + self._draftCentreX)
        else:
            draft.angle = 0
            pos = QPointF(
                self._start.x() - self._draftCentreX,
                min(self._start.y(), point.y()) - back)
        draft.setPos(self._scene.snapToGrid(pos.toPoint()))

    def _finish(self):
        self._view.viewport().removeEventFilter(self)
        self._view.removeEventFilter(self)
        if self._draft is not None and self._draft.scene() is not None:
            if self._segLength < _minSegDbu:
                # Drop the too-short trailing segment; its add command
                # is the newest undo entry, like Draw Path's cleanup.
                self._scene.undoStack.removeLastCommand()
            else:
                self._segments += 1
        self._draft = None
        self._start = None
        if self._segments:
            self._editorWindow.messageLine.setText(
                f"{self._cellName}: {self._segments} tap segment(s) "
                "placed. Label the line metal on Metal1.text to name "
                "the net.")
        else:
            self._editorWindow.messageLine.setText("")
        self._editorWindow._tapLineGrabber = None

    def eventFilter(self, obj, event):
        etype = event.type()
        if etype == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.RightButton:
                self._finish()
                return True
            if event.button() == Qt.MouseButton.LeftButton:
                if self._start is None:
                    self._start = self._snapPos(event)
                    self._makeDraft(self._start)
                # Swallow every left press during the capture so the
                # scene never starts a selection or a move.
                return True
        elif etype == QEvent.Type.MouseMove:
            if self._start is None:
                return False
            if self._draft is None or self._draft.scene() is None:
                # In-progress segment was removed while drawing
                # (e.g. undo); the next click re-anchors a new line.
                self._draft = None
                self._start = None
                return True
            self._updateDraft(self._snapPos(event))
            return True
        elif etype == QEvent.Type.MouseButtonRelease \
                and event.button() == Qt.MouseButton.LeftButton:
            if self._start is None:
                return True
            point = self._snapPos(event)
            segLen = max(abs(point.x() - self._start.x()),
                         abs(point.y() - self._start.y()))
            if segLen < _minSegDbu:
                # Click slop: keep the segment open for a real end
                # point.
                return True
            if self._draft is None or self._draft.scene() is None:
                self._start = point
                self._makeDraft(point)
                return True
            self._updateDraft(point)
            self._segments += 1
            self._start = point
            self._makeDraft(point)
            return True
        elif etype == QEvent.Type.MouseButtonRelease \
                and event.button() == Qt.MouseButton.RightButton:
            # Context menus fire on release on Windows; keep one from
            # popping up while the line is being drawn.
            return True
        elif etype == QEvent.Type.KeyPress \
                and event.key() == Qt.Key.Key_Escape:
            self._finish()
            return True
        elif etype == QEvent.Type.MouseButtonDblClick:
            # A double-click reaching the scene could open an item
            # dialogue while the line is still being drawn.
            return True
        return False


def _startTapLine(editorWindow, cellName, pcellClass):
    libName = _findPdkLibraryName(editorWindow, cellName)
    if not libName:
        editorWindow.messageLine.setText(
            f"Tap line: {cellName} PDK library not found.")
        return
    # A previous grabber may still be installed if the menu was invoked
    # twice in a row.
    if getattr(editorWindow, "_tapLineGrabber", None) is not None:
        editorWindow._tapLineGrabber._finish()
    # Keep a reference on the window or the grabber is garbage collected
    # while it is still installed as an event filter.
    editorWindow._tapLineGrabber = _tapLineGrabber(
        editorWindow, cellName, pcellClass, libName)
    editorWindow._tapLineGrabber.start()


def psubTapClick(editorWindow):
    """Create -> Substrate Tap -> P+ Tap Line callback."""
    from .pcells.tap_contacts import psubtap
    _startTapLine(editorWindow, "psubtap", psubtap)


def nwellTapClick(editorWindow):
    """Create -> Substrate Tap -> N-Well Tap Line callback."""
    from .pcells.tap_contacts import nwelltap
    _startTapLine(editorWindow, "nwelltap", nwelltap)
