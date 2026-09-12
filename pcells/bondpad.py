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
Bond pad parametric cell for IHP SG13G2 PDK.

Supports octagon, square, and circle shapes with optional metal stacking,
via filling, filler exclusion, and passivation opening.
"""

import math
from functools import lru_cache

from PySide6.QtCore import QPointF
from quantiphy import Quantity

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule
from .base import baseCell

laylyr = importPDKModule('layoutLayers')


# Metal and via layer lists for SG13G2 (7 metals + TM1 + TM2)
_METAL_LAYERS = [
    laylyr.Metal1_drawing,
    laylyr.Metal2_drawing,
    laylyr.Metal3_drawing,
    laylyr.Metal4_drawing,
    laylyr.Metal5_drawing,
    laylyr.TopMetal1_drawing,
    laylyr.TopMetal2_drawing,
]

_VIA_LAYERS = [
    laylyr.Via1_drawing,
    laylyr.Via2_drawing,
    laylyr.Via3_drawing,
    laylyr.Via4_drawing,
    laylyr.TopVia1_drawing,
    laylyr.TopVia2_drawing,
]

_NOFILL_LAYERS = [
    laylyr.Activ_nofill,
    laylyr.GatPoly_nofill,
    laylyr.Metal1_nofill,
    laylyr.Metal2_nofill,
    laylyr.Metal3_nofill,
    laylyr.Metal4_nofill,
    laylyr.Metal5_nofill,
    laylyr.TopMetal1_nofill,
    laylyr.TopMetal2_nofill,
]


class bondpad(baseCell):
    """
    Bond pad with configurable shape, metal stacking, and via filling.

    Generates a bond pad on the top metal with optional:
    - Metal stacking down to a specified bottom metal
    - Via rings and/or via fill between stacked metals
    - Filler exclusion zones around the pad
    - Passivation opening

    Parameters:
        padShape: Pad shape ("octagon", "square", or "circle"; default "octagon")
        diameter: Pad diameter (default "60u")
        topMetal: Top metal layer ("TM1" or "TM2"; default "TM2")
        bottomMetal: Bottom metal layer ("1"-"5" or "TM1"; default "1")
        stack: Stack metals ("1" = yes, "0" = no; default "1")
        fill: Fill metals with vias ("1" = yes, "0" = no; default "0")
        addFillerEx: Add filler exclusion ("1" = yes, "0" = no; default "1")
    """

    passivLayer = laylyr.Passiv_drawing
    dfpadLayer = laylyr.dfpad_drawing
    textLayer = laylyr.TEXT_drawing

    def __init__(self, padShape: str = "octagon", diameter: str = "60u",
                 topMetal: str = "TM2", bottomMetal: str = "1",
                 stack: str = "1", fill: str = "0", addFillerEx: str = "1"):
        self._padShape = padShape
        self.diameter = diameter
        self.topMetal = topMetal
        self.bottomMetal = bottomMetal
        self.stack = stack
        self.fill = fill
        self.addFillerEx = addFillerEx
        super().__init__([])

    @property
    def padShape(self) -> str:
        return self._padShape

    @padShape.setter
    def padShape(self, value: str):
        self._padShape = value

    def _mkRect(self, shapes, x1, y1, x2, y2, layer):
        """Create a layoutRect from micron coordinates."""
        p1 = self.toSceneCoord(QPointF(x1, y1))
        p2 = self.toSceneCoord(QPointF(x2, y2))
        shapes.append(lshp.layoutRect(p1, p2, layer))

    def _mkPolygon(self, shapes, points, layer):
        """Create a layoutPolygon from (x, y) tuples in microns."""
        scene_points = [self.toSceneCoord(QPointF(x, y)) for x, y in points]
        shapes.append(lshp.layoutPolygon(scene_points, layer))

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

    @staticmethod
    def _octagonPoints(radx, rady, offset):
        """Generate octagon vertices centered at origin."""
        return [
            (-radx + offset, -rady),
            (radx - offset, -rady),
            (radx, -rady + offset),
            (radx, rady - offset),
            (radx - offset, rady),
            (-radx + offset, rady),
            (-radx, rady - offset),
            (-radx, -rady + offset),
        ]

    def _resolveMetalIndex(self, name):
        """Resolve metal layer name to 0-based index in _METAL_LAYERS."""
        if name == 'TM2':
            return 6
        elif name == 'TM1':
            return 5
        else:
            idx = int(name) - 1
            return max(0, min(idx, 6))

    @lru_cache
    def __call__(self, padShape: str, diameter: str, topMetal: str,
                 bottomMetal: str, stack: str, fill: str, addFillerEx: str):
        """
        Generate bond pad layout.

        Args:
            padShape: "octagon", "square", or "circle"
            diameter: Pad diameter (e.g. "60u")
            topMetal: "TM1" or "TM2"
            bottomMetal: "1"-"5" or "TM1"
            stack: "1" for metal stacking, "0" for top only
            fill: "1" for via fill, "0" for via ring only
            addFillerEx: "1" to add filler exclusion
        """
        self._padShape = padShape
        self.diameter = diameter
        self.topMetal = topMetal
        self.bottomMetal = bottomMetal
        self.stack = stack
        self.fill = fill
        self.addFillerEx = addFillerEx

        tp = baseCell._techParams
        grid = tp["grid"]

        # Parse parameters
        rad = self.GridFix(Quantity(diameter).real * 5e5)
        radx = rad
        rady = rad
        doStack = stack == '1'
        doFill = fill == '1'
        doFillerEx = addFillerEx == '1'

        topIdx = self._resolveMetalIndex(topMetal)
        botIdx = self._resolveMetalIndex(bottomMetal)
        if botIdx >= topIdx:
            botIdx = topIdx - 1

        # Via design rules
        Vn_size = tp["Vn_a"]
        Vn_dist = tp["Vn_b"]
        TV1_size = tp["TV1_a"]
        TV1_dist = tp["TV1_b"]
        TV2_size = tp["TV2_a"]
        TV2_dist = tp["TV2_b"]
        met_over = tp["TV1_d"]
        met_over2 = tp.get("Pad_gR", met_over)
        met_over_pass = tp.get("Pas_c", 2.1)
        noFillerEnc = 10.0

        if met_over2 > met_over:
            met_over = met_over2

        # Stripe width for via ring
        stripeWidth = self.GridFix(met_over + math.sqrt(2) * TV2_size * 0.5) * 2

        tempShapes = []

        # ==================================================
        # 1. Filler exclusion (if enabled)
        # ==================================================
        if doFillerEx:
            oradx = radx + noFillerEnc
            orady = rady + noFillerEnc
            if padShape == 'octagon':
                ooff = self.GridFix(min(oradx, orady) * (1 - 1 / (math.sqrt(2) + 1)))
                pts = self._octagonPoints(oradx, orady, ooff)
                for nfLayer in _NOFILL_LAYERS:
                    self._mkPolygon(tempShapes, pts, nfLayer)
            else:
                for nfLayer in _NOFILL_LAYERS:
                    self._mkRect(tempShapes, -oradx, -orady, oradx, orady, nfLayer)

        # ==================================================
        # 2. Top metal pad
        # ==================================================
        topLayer = _METAL_LAYERS[topIdx]
        if padShape == 'octagon':
            offset = self.GridFix(min(radx, rady) * (1 - 1 / (math.sqrt(2) + 1)))
            pts = self._octagonPoints(radx, rady, offset)
            self._mkPolygon(tempShapes, pts, topLayer)
            # dfpad layer (bond pad recognition)
            self._mkPolygon(tempShapes, pts, self.dfpadLayer)
        else:
            self._mkRect(tempShapes, -radx, -rady, radx, rady, topLayer)
            self._mkRect(tempShapes, -radx, -rady, radx, rady, self.dfpadLayer)

        # ==================================================
        # 3. Passivation opening
        # ==================================================
        oradx = radx - met_over_pass
        orady = rady - met_over_pass
        if padShape == 'octagon':
            ooff = self.GridFix(min(oradx, orady) * (1 - 1 / (math.sqrt(2) + 1)))
            pts = self._octagonPoints(oradx, orady, ooff)
            self._mkPolygon(tempShapes, pts, self.passivLayer)
        else:
            self._mkRect(tempShapes, -oradx, -orady, oradx, orady, self.passivLayer)

        # ==================================================
        # 4. Metal stacking with via rings
        # ==================================================
        if doStack:
            for metalIdx in range(botIdx, topIdx):
                metalLayer = _METAL_LAYERS[metalIdx]
                viaLayer = _VIA_LAYERS[metalIdx]

                # Determine via size/spacing for this level
                if metalIdx == 4:  # Metal5 -> TopMetal1
                    vs = TV1_size
                    vd = TV1_dist
                elif metalIdx == 5:  # TopMetal1 -> TopMetal2
                    vs = TV2_size
                    vd = TV2_dist
                else:
                    vs = Vn_size
                    vd = Vn_dist

                # Draw metal layer (ring or filled)
                if doFill:
                    if padShape == 'octagon':
                        self._mkPolygon(tempShapes, self._octagonPoints(radx, rady, offset),
                                        metalLayer)
                    else:
                        self._mkRect(tempShapes, -radx, -rady, radx, rady, metalLayer)
                else:
                    # Ring only (stripe width around perimeter)
                    if padShape == 'square':
                        # Top/bottom strips
                        self._mkRect(tempShapes, -radx, rady - stripeWidth,
                                     radx, rady, metalLayer)
                        self._mkRect(tempShapes, -radx, -rady,
                                     radx, -rady + stripeWidth, metalLayer)
                        # Left/right strips
                        self._mkRect(tempShapes, -radx, -rady + stripeWidth,
                                     -radx + stripeWidth, rady - stripeWidth, metalLayer)
                        self._mkRect(tempShapes, radx - stripeWidth, -rady + stripeWidth,
                                     radx, rady - stripeWidth, metalLayer)
                    else:
                        # For octagon, draw full shape (ring would require polygon subtraction)
                        self._mkPolygon(tempShapes, self._octagonPoints(radx, rady, offset),
                                        metalLayer)

                # Via ring (4 sides)
                viaofs = self.GridFix((stripeWidth - vs) / 2)
                # Top
                tempShapes.extend(
                    self.contactArray(0, viaLayer,
                                      -radx, rady - stripeWidth,
                                      radx, rady,
                                      viaofs, viaofs, vs, vd))
                # Bottom
                tempShapes.extend(
                    self.contactArray(0, viaLayer,
                                      -radx, -rady,
                                      radx, -rady + stripeWidth,
                                      viaofs, viaofs, vs, vd))
                # Left
                tempShapes.extend(
                    self.contactArray(0, viaLayer,
                                      -radx, -rady + stripeWidth,
                                      -radx + stripeWidth, rady - stripeWidth,
                                      viaofs, viaofs, vs, vd))
                # Right
                tempShapes.extend(
                    self.contactArray(0, viaLayer,
                                      radx - stripeWidth, -rady + stripeWidth,
                                      radx, rady - stripeWidth,
                                      viaofs, viaofs, vs, vd))

                # Via fill (center area)
                if doFill:
                    fillEnc = stripeWidth + 4
                    tempShapes.extend(
                        self.contactArray(0, viaLayer,
                                          -radx + fillEnc, -rady + fillEnc,
                                          radx - fillEnc, rady - fillEnc,
                                          0, 0, vs, vd * 4))

        # ==================================================
        # 5. Label
        # ==================================================
        self._mkLabel(tempShapes, 0, 0, 'PAD', self.textLayer)

        self.shapes = tempShapes
