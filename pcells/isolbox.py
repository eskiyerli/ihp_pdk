########################################################################
#
# Copyright 2025 IHP PDK Authors
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
Deep-trench isolation box parametric cell for IHP SG13G2 PDK.

Generates an NWell/nBuLay isolation structure with optional diode
recognition layer, PWellBlock, and contact ring.
"""

from functools import lru_cache

from PySide6.QtCore import QPointF
from quantiphy import Quantity

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule
from .base import baseCell

laylyr = importPDKModule('layoutLayers')


class isolbox(baseCell):
    """
    Deep-trench isolation box.

    Generates an NWell ring with nBuLay, Active ring, optional diode
    recognition layer, optional PWell block, and optional contact ring.

    Parameters:
        l: Length (default "3.6u")
        w: Width (default "3.6u")
        wellwidth: NWell width ("1.05u" or "1.5u"; default "1.05u")
        diode_layer: Add diode recognition layer ("1" or "0"; default "1")
        cont_ring: Add contact ring ("O"=full, "U"=three sides, "0"=none; default "0")
        pwell_w: PWellBlock width in um (default "0")
    """

    # Layer definitions
    dwellLayer = laylyr.nBuLay_drawing
    wellLayer = laylyr.NWell_drawing
    activLayer = laylyr.Activ_drawing
    activPin = laylyr.Activ_pin
    diodeLayer = laylyr.Recog_diode
    metal1Layer = laylyr.Metal1_drawing
    contLayer = laylyr.Cont_drawing
    pwellBlock = laylyr.PWell_block
    textLayer = laylyr.TEXT_drawing

    def __init__(self, l: str = "3.6u", w: str = "3.6u",
                 wellwidth: str = "1.05u", diode_layer: str = "1",
                 cont_ring: str = "0", pwell_w: str = "0"):
        self.l = l
        self.w = w
        self.wellwidth = wellwidth
        self.diode_layer = diode_layer
        self.cont_ring = cont_ring
        self.pwell_w = pwell_w
        super().__init__([])

    def _mkRect(self, shapes, x1, y1, x2, y2, layer):
        """Create a layoutRect from micron coordinates."""
        p1 = self.toSceneCoord(QPointF(x1, y1))
        p2 = self.toSceneCoord(QPointF(x2, y2))
        shapes.append(lshp.layoutRect(p1, p2, layer))

    def _mkPolygon(self, shapes, points, layer):
        """Create a layoutPolygon from (x, y) tuples in microns."""
        scene_points = [self.toSceneCoord(QPointF(x, y)) for x, y in points]
        shapes.append(lshp.layoutPolygon(scene_points, layer))

    def _mkPin(self, shapes, x1, y1, x2, y2, name, layer):
        """Create a layoutPin from micron coordinates."""
        p1 = self.toSceneCoord(QPointF(x1, y1))
        p2 = self.toSceneCoord(QPointF(x2, y2))
        shapes.append(lshp.layoutPin(
            p1, p2, name,
            lshp.layoutPin.pinDirs[2],
            lshp.layoutPin.pinTypes[0],
            layer
        ))

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

    def _metalCont(self, shapes, x1, y1, x2, y2, metW, contW, contS):
        """Draw a metal strip with contacts (horizontal or vertical)."""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)

        if dy >= dx:
            # Vertical
            xc = (x1 + x2) / 2
            self._mkRect(shapes, xc - metW / 2, min(y1, y2),
                         xc + metW / 2, max(y1, y2), self.metal1Layer)
            y = min(y1, y2) + contW / 2
            while y + contW <= max(y1, y2):
                self._mkRect(shapes, xc - contW / 2, y, xc + contW / 2, y + contW,
                             self.contLayer)
                y += contW + contS
        else:
            # Horizontal
            yc = (y1 + y2) / 2
            self._mkRect(shapes, min(x1, x2), yc - metW / 2,
                         max(x1, x2), yc + metW / 2, self.metal1Layer)
            x = min(x1, x2) + contW / 2
            while x + contW <= max(x1, x2):
                self._mkRect(shapes, x, yc - contW / 2, x + contW, yc + contW / 2,
                             self.contLayer)
                x += contW + contS

    @lru_cache(maxsize=16)
    def __call__(self, l: str, w: str, wellwidth: str,
                 diode_layer: str, cont_ring: str, pwell_w: str):
        """
        Generate isolbox layout.

        Args:
            l: Length (e.g. "3.6u")
            w: Width (e.g. "3.6u")
            wellwidth: NWell width ("1.05u" or "1.5u")
            diode_layer: "1" to add diode layer
            cont_ring: "O" (full ring), "U" (3-sided), "0" (none)
            pwell_w: PWellBlock width in um string (e.g. "0" or "1.5u")
        """
        self.l = l
        self.w = w
        self.wellwidth = wellwidth
        self.diode_layer = diode_layer
        self.cont_ring = cont_ring
        self.pwell_w = pwell_w

        lu = Quantity(l).real * 1e6
        wu = Quantity(w).real * 1e6
        nw_a = Quantity(wellwidth).real * 1e6
        pw_width = Quantity(pwell_w).real * 1e6 if pwell_w != '0' else 0
        doDiode = diode_layer == '1'
        doContRing = cont_ring in ('O', 'U')

        # Design rules from KLayout source
        nbl_nw = 0.62
        nwOact = 0.24
        nwOact2 = 0.32 if wellwidth == '0.85u' else nwOact
        contW = 0.16
        contS = 0.18

        if wellwidth == '1.05u':
            dd = 0.4
        else:
            dd = nw_a - nbl_nw

        tempShapes = []

        # ==================================================
        # 1. nBuLay (deep well)
        # ==================================================
        self._mkRect(tempShapes,
                     -nw_a + dd, -nw_a + dd,
                     lu - nw_a - dd, wu - nw_a - dd,
                     self.dwellLayer)

        # ==================================================
        # 2. NWell ring (as polygon with hole)
        # ==================================================
        # Outer ring of NWell
        nw_pts = [
            (0, 0), (lu - 2 * nw_a, 0),
            (lu - 2 * nw_a, wu - 2 * nw_a), (0, wu - 2 * nw_a),
            (0, 0), (-nw_a, 0),
            (-nw_a, wu - nw_a), (lu - nw_a, wu - nw_a),
            (lu - nw_a, -nw_a), (-nw_a, -nw_a), (-nw_a, 0),
        ]
        self._mkPolygon(tempShapes, nw_pts, self.wellLayer)

        # ==================================================
        # 3. Diode recognition layer (same shape as NWell)
        # ==================================================
        if doDiode:
            self._mkPolygon(tempShapes, nw_pts, self.diodeLayer)

        # ==================================================
        # 4. PWellBlock (if pwell_w > 0)
        # ==================================================
        if pw_width > 0:
            pwb_pts = [
                (-nw_a - pw_width, -nw_a), (lu - nw_a, -nw_a),
                (lu - nw_a, wu - nw_a), (-nw_a, wu - nw_a),
                (-nw_a, -nw_a), (-nw_a - pw_width, -nw_a),
                (-nw_a - pw_width, wu - nw_a + pw_width),
                (lu - nw_a + pw_width, wu - nw_a + pw_width),
                (lu - nw_a + pw_width, -nw_a - pw_width),
                (-nw_a - pw_width, -nw_a - pw_width),
            ]
            self._mkPolygon(tempShapes, pwb_pts, self.pwellBlock)

        # ==================================================
        # 5. Active ring
        # ==================================================
        act_pts = [
            (-(nw_a - nwOact2), -(nw_a - nwOact2)),
            (lu - nw_a - nwOact2, -(nw_a - nwOact2)),
            (lu - nw_a - nwOact2, wu - nw_a - nwOact2),
            (-(nw_a - nwOact2), wu - nw_a - nwOact2),
            (-(nw_a - nwOact2), -nwOact),
            (-nwOact, -nwOact),
            (-nwOact, wu - 2 * nw_a + nwOact),
            (lu - 2 * nw_a + nwOact, wu - 2 * nw_a + nwOact),
            (lu - 2 * nw_a + nwOact, -nwOact),
            (-(nw_a - nwOact2), -nwOact),
        ]
        self._mkPolygon(tempShapes, act_pts, self.activLayer)

        # ==================================================
        # 6. Pin on left side of active ring
        # ==================================================
        self._mkPin(tempShapes,
                    -(nw_a - nwOact2), -(nw_a - nwOact2),
                    -nwOact, wu - nw_a - nwOact2,
                    'I', self.activPin)

        # ==================================================
        # 7. Contact ring (if enabled)
        # ==================================================
        if doContRing:
            venc = 0.06
            xm = nw_a / 2 + 0.015
            wm = contW + venc * 2

            if wellwidth == '0.85u':
                xm = xm - 0.05
                wm = wm - 0.02

            # Bottom
            self._metalCont(tempShapes,
                            -xm + wm / 2, -xm,
                            lu - 2 * nw_a + xm - wm / 2, -xm,
                            wm, contW, contS)
            # Left
            self._metalCont(tempShapes,
                            -xm, -xm - wm / 2,
                            -xm, wu - 2 * nw_a + xm + wm / 2,
                            wm, contW, contS)
            # Right
            self._metalCont(tempShapes,
                            lu - 2 * nw_a + xm, -xm - wm / 2,
                            lu - 2 * nw_a + xm, wu - 2 * nw_a + xm + wm / 2,
                            wm, contW, contS)
            # Top (only for 'O' ring)
            if cont_ring == 'O':
                self._metalCont(tempShapes,
                                -xm + wm / 2, wu - 2 * nw_a + xm,
                                lu - 2 * nw_a + xm - wm / 2, wu - 2 * nw_a + xm,
                                wm, contW, contS)

        # ==================================================
        # 8. Label
        # ==================================================
        self._mkLabel(tempShapes, 0, -nw_a / 2, 'isolbox', self.textLayer)

        self.shapes = tempShapes
