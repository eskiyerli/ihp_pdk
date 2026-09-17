########################################################################
#
# Copyright 2024 IHP PDK Authors
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

"""
Chip seal ring parametric cell for IHP SG13G2 PDK.

Generates a multi-metal, multi-via seal ring around the chip perimeter
with corners, straight sections, and slit option. The seal ring provides
mechanical and moisture protection for the die edge.
"""

import math
from functools import lru_cache

from PySide6.QtCore import QPointF
from quantiphy import Quantity

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule
from .base import baseCell

laylyr = importPDKModule('layoutLayers')


class sealring(baseCell):
    """
    Chip seal ring for die edge protection.

    Generates a continuous frame of stacked metals and vias around
    the chip perimeter. Includes Passiv layer, all metal layers
    (Metal1-Metal5, TopMetal1, TopMetal2), and all via layers
    (Cont, Via1-Via4, TopVia1, TopVia2) in a multi-corner structure.

    Parameters:
        l: Length in X direction (default "500u")
        w: Width in Y direction (default "500u")
        addLabel: Add sub! label ("1" or "0"; default "0")
        addSlit: Add slit in ring ("1" or "0"; default "0")
    """

    # Layer definitions
    passivLayer = laylyr.Passiv_drawing
    edgeSealLayer = laylyr.EdgeSeal_drawing
    edgeSealBoundary = laylyr.EdgeSeal_boundary
    textLayer = laylyr.TEXT_drawing
    psdLayer = laylyr.pSD_drawing
    activLayer = laylyr.Activ_drawing

    # Metal layers (ordered)
    _metalLayers = [
        laylyr.Activ_drawing,
        laylyr.pSD_drawing,
        laylyr.EdgeSeal_drawing,
        laylyr.Metal1_drawing,
        laylyr.Metal2_drawing,
        laylyr.Metal3_drawing,
        laylyr.Metal4_drawing,
        laylyr.Metal5_drawing,
        laylyr.TopMetal1_drawing,
        laylyr.TopMetal2_drawing,
    ]

    # Via layers (ordered)
    _viaLayers = [
        laylyr.Cont_drawing,
        laylyr.Via1_drawing,
        laylyr.Via2_drawing,
        laylyr.Via3_drawing,
        laylyr.Via4_drawing,
        laylyr.TopVia1_drawing,
        laylyr.TopVia2_drawing,
    ]

    def __init__(self, l: str = "500u", w: str = "500u",
                 addLabel: str = "0", addSlit: str = "0"):
        self.l = l
        self.w = w
        self.addLabel = addLabel
        self.addSlit = addSlit
        super().__init__([])

    def _mkRect(self, shapes, x1, y1, x2, y2, layer):
        """Create a layoutRect from micron coordinates."""
        p1 = self.toSceneCoord(QPointF(x1, y1))
        p2 = self.toSceneCoord(QPointF(x2, y2))
        shapes.append(lshp.layoutRect(p1, p2, layer))

    def _mkLabel(self, shapes, x, y, text, layer):
        """Create a layoutLabel from micron coordinates."""
        pt = self.toSceneCoord(QPointF(x, y))
        shapes.append(lshp.layoutLabel(
            pt, text,
            *self._labelFontTuple,
            lshp.layoutLabel.LABEL_ALIGNMENTS[0],
            lshp.layoutLabel.LABEL_ORIENTS[0],
            layer
        ))

    @lru_cache(maxsize=16)
    def __call__(self, l: str, w: str, addLabel: str, addSlit: str):
        """
        Generate seal ring layout.

        Args:
            l: Length in X (e.g. "500u")
            w: Width in Y (e.g. "500u")
            addLabel: "1" to add sub! label
            addSlit: "1" to add slit in ring
        """
        self.l = l
        self.w = w
        self.addLabel = addLabel
        self.addSlit = addSlit

        tp = baseCell._techParams

        # Parse dimensions
        edgeBox = Quantity(tp.get("sealring_complete_edgeBox", "0")).real * 1e6
        lu = Quantity(l).real * 1e6 + edgeBox * 2
        wu = Quantity(w).real * 1e6 + edgeBox * 2

        # Design parameters from KLayout source
        cont_size = tp["Cnt_a"]
        vn_size = tp["Vn_a"]
        TV1_size = tp["TV1_a"]
        TV2_size = tp["TV2_a"]

        cornerWidth = 4.2
        cornerLength = cornerWidth * 2
        metalOffset = 3 + cornerWidth + edgeBox
        viaOffset = 5.1 + cornerWidth + edgeBox
        cornerEnd = 28.2 + edgeBox

        tempShapes = []

        # ==================================================
        # 1. Straight sections (4 sides of the frame)
        # ==================================================
        # For each layer, draw 4 rectangles forming the straight portions
        # between corners (top, bottom, left, right).

        # Passiv layer straight sections
        self._mkRect(tempShapes, edgeBox, cornerEnd,
                     cornerWidth + edgeBox, wu - cornerEnd, self.passivLayer)
        self._mkRect(tempShapes, cornerEnd, edgeBox,
                     lu - cornerEnd, cornerWidth + edgeBox, self.passivLayer)
        self._mkRect(tempShapes, lu - edgeBox, cornerEnd,
                     lu - cornerWidth - edgeBox, wu - cornerEnd, self.passivLayer)
        self._mkRect(tempShapes, cornerEnd, wu - edgeBox,
                     lu - cornerEnd, wu - cornerWidth - edgeBox, self.passivLayer)

        # Metal layers straight sections
        metalLayers = [
            laylyr.Activ_drawing, laylyr.pSD_drawing, laylyr.EdgeSeal_drawing,
            laylyr.Metal1_drawing, laylyr.Metal2_drawing, laylyr.Metal3_drawing,
            laylyr.Metal4_drawing, laylyr.Metal5_drawing,
            laylyr.TopMetal1_drawing, laylyr.TopMetal2_drawing,
        ]
        for layer in metalLayers:
            # Left
            self._mkRect(tempShapes, metalOffset, cornerEnd,
                         metalOffset + cornerWidth, wu - cornerEnd, layer)
            # Bottom
            self._mkRect(tempShapes, cornerEnd, metalOffset,
                         lu - cornerEnd, metalOffset + cornerWidth, layer)
            # Right
            self._mkRect(tempShapes, lu - metalOffset, cornerEnd,
                         lu - cornerWidth - metalOffset, wu - cornerEnd, layer)
            # Top
            self._mkRect(tempShapes, cornerEnd, wu - metalOffset,
                         lu - cornerEnd, wu - cornerWidth - metalOffset, layer)

        # Via layers straight sections
        for viaLayer in self._viaLayers:
            if viaLayer == laylyr.TopVia1_drawing:
                viaWidth = TV1_size
            elif viaLayer == laylyr.TopVia2_drawing:
                viaWidth = TV2_size
            elif viaLayer == laylyr.Cont_drawing:
                viaWidth = cont_size
            else:
                viaWidth = vn_size

            viaLength = 4.2

            # Left
            self._mkRect(tempShapes, viaOffset - 0.1, cornerEnd,
                         viaOffset + viaWidth - 0.1, wu - cornerEnd, viaLayer)
            # Bottom
            self._mkRect(tempShapes, cornerEnd, viaOffset - 0.1,
                         lu - cornerEnd, viaOffset + viaWidth - 0.1, viaLayer)
            # Right
            self._mkRect(tempShapes, lu - viaOffset + 0.1, cornerEnd,
                         lu - viaWidth - viaOffset + 0.1, wu - cornerEnd, viaLayer)
            # Top
            self._mkRect(tempShapes, cornerEnd, wu - viaOffset + 0.1,
                         lu - cornerEnd, wu - viaWidth - viaOffset + 0.1, viaLayer)

        # ==================================================
        # 2. Corner regions (simplified as filled rectangles)
        # ==================================================
        # Bottom-left corner
        self._drawCornerRegion(tempShapes, 0, 0, cornerEnd, cornerEnd,
                               metalOffset, cornerWidth, metalLayers)
        # Bottom-right corner
        self._drawCornerRegion(tempShapes, lu - cornerEnd, 0, lu, cornerEnd,
                               metalOffset, cornerWidth, metalLayers)
        # Top-left corner
        self._drawCornerRegion(tempShapes, 0, wu - cornerEnd, cornerEnd, wu,
                               metalOffset, cornerWidth, metalLayers)
        # Top-right corner
        self._drawCornerRegion(tempShapes, lu - cornerEnd, wu - cornerEnd, lu, wu,
                               metalOffset, cornerWidth, metalLayers)

        # ==================================================
        # 3. EdgeSeal boundary box
        # ==================================================
        self._mkRect(tempShapes, 0, 0, lu, wu, self.edgeSealBoundary)

        # ==================================================
        # 4. Labels
        # ==================================================
        areaText = f"sealring {lu:.0f}x{wu:.0f} um"
        self._mkLabel(tempShapes, 5.0, 5.0, areaText, self.textLayer)

        if addLabel == '1':
            self._mkLabel(tempShapes, lu / 2, wu / 2, 'sub!', self.textLayer)

        self.shapes = tempShapes

    def _drawCornerRegion(self, shapes, x1, y1, x2, y2, metalOffset, cornerWidth,
                          metalLayers):
        """Draw simplified corner region with L-shaped metal fills."""
        # Passiv corner
        self._mkRect(shapes, x1, y1, x2, y1 + cornerWidth, self.passivLayer)
        self._mkRect(shapes, x1, y1, x1 + cornerWidth, y2, self.passivLayer)

        # Metal corners (L-shaped approximation)
        mx1 = x1 + metalOffset if x1 == 0 else x1
        my1 = y1 + metalOffset if y1 == 0 else y1
        mx2 = x2 - metalOffset if x2 > (x2 - x1) / 2 + x1 else x2
        my2 = y2 - metalOffset if y2 > (y2 - y1) / 2 + y1 else y2

        for layer in metalLayers:
            # Horizontal bar of L
            self._mkRect(shapes, x1 + metalOffset, y1 + metalOffset,
                         x2 - metalOffset + cornerWidth, y1 + metalOffset + cornerWidth,
                         layer)
            # Vertical bar of L
            self._mkRect(shapes, x1 + metalOffset, y1 + metalOffset,
                         x1 + metalOffset + cornerWidth, y2 - metalOffset + cornerWidth,
                         layer)
