########################################################################
#
# Copyright 2023 IHP PDK Authors
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
HV S-parameter varicap (gate-controlled) parametric cell for IHP SG13G2 PDK.

MOS varactor with ThickGateOx, NWell/nBuLay isolation, and interdigitated
gate fingers for RF tuning applications.
"""

from functools import lru_cache

from PySide6.QtCore import QPointF
from quantiphy import Quantity

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule
from .base import baseCell

laylyr = importPDKModule('layoutLayers')


class SVaricap(baseCell):
    """
    HV S-parameter varicap (gate-controlled MOS varactor).

    Generates interdigitated gate structure with NWell/nBuLay isolation
    for use as an RF-tunable capacitor.

    Parameters:
        w: Width (default "3.74u", choices: "3.74u" or "9.74u")
        l: Length (default "0.3u", choices: "0.3u" or "0.8u")
        Nx: Number of columns (default "1", range 1-10)
    """

    # Layer definitions
    activLayer = laylyr.Activ_drawing
    gateLayer = laylyr.GatPoly_drawing
    contLayer = laylyr.Cont_drawing
    met1Layer = laylyr.Metal1_drawing
    met1Pin = laylyr.Metal1_pin
    psdLayer = laylyr.pSD_drawing
    nwellLayer = laylyr.NWell_drawing
    nbulayLayer = laylyr.nBuLay_drawing
    gateOxLayer = laylyr.ThickGateOx_drawing
    textLayer = laylyr.TEXT_drawing

    def __init__(self, w: str = "3.74u", l: str = "0.3u", Nx: str = "1"):
        self.w = w
        self.l = l
        self.Nx = Nx
        super().__init__([])

    def _mkRect(self, shapes, x1, y1, x2, y2, layer):
        """Create a layoutRect from micron coordinates."""
        p1 = self.toSceneCoord(QPointF(x1, y1))
        p2 = self.toSceneCoord(QPointF(x2, y2))
        shapes.append(lshp.layoutRect(p1, p2, layer))

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
        """
        Draw a metal strip with contacts along its length.
        Simplified version of the KLayout MetalCont helper.
        """
        # Determine orientation (vertical vs horizontal)
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)

        if dy >= dx:
            # Vertical strip
            self._mkRect(shapes, x1 - metW / 2, y1, x1 + metW / 2, y2, self.met1Layer)
            # Place contacts along the strip
            y = y1 + 0.08
            while y + contW <= y2:
                self._mkRect(shapes, x1 - contW / 2, y, x1 + contW / 2, y + contW,
                             self.contLayer)
                y += contW + contS
        else:
            # Horizontal strip
            self._mkRect(shapes, x1, y1 - metW / 2, x2, y1 + metW / 2, self.met1Layer)
            x = x1 + 0.08
            while x + contW <= x2:
                self._mkRect(shapes, x, y1 - contW / 2, x + contW, y1 + contW / 2,
                             self.contLayer)
                x += contW + contS

    @lru_cache
    def __call__(self, w: str, l: str, Nx: str):
        """
        Generate SVaricap layout.

        Args:
            w: Width ("3.74u" or "9.74u")
            l: Length ("0.3u" or "0.8u")
            Nx: Number of columns (1-10)
        """
        self.w = w
        self.l = l
        self.Nx = Nx

        wu = Quantity(w).real * 1e6
        lu = Quantity(l).real * 1e6
        NX = int(float(Nx))

        # Clamp NX to valid range
        if NX < 1:
            NX = 1
        if NX > 10:
            NX = 10

        # Design parameters from KLayout source
        contW = 0.16
        contS = 0.18
        metW = contW + 2 * 0.05
        nwellOgate = 0.57
        nbulayOgate = 0.33
        gateOactiv = 0.35

        if wu == 3.74:
            gateOnwell = 0.11
            gateOnbulay = 0.35
        else:
            gateOnwell = -0.145
            gateOnbulay = 0.1

        x1 = 0.73
        gateS = 0.25
        y1 = 0.39 + gateS
        pcStepX = (gateS + lu) * 2

        tempShapes = []

        # ==================================================
        # 1. Gate fingers and source/drain contacts
        # ==================================================
        for pcIndexX in range(NX):
            # Two gate fingers per column
            gx1 = x1 + pcIndexX * pcStepX
            self._mkRect(tempShapes, gx1, y1, gx1 + lu, y1 + wu, self.gateLayer)
            gx2 = x1 + lu + gateS + pcIndexX * pcStepX
            self._mkRect(tempShapes, gx2, y1 - gateS, gx2 + lu, y1 - gateS + wu,
                         self.gateLayer)

            # Metal1 + contacts for source/drain (vertical strips)
            cx1 = self.GridFix(x1 + lu / 2) + pcIndexX * pcStepX
            self._metalCont(tempShapes, cx1, y1 + 0.08, cx1, y1 + wu - 0.01,
                            metW, contW, contS)
            cx2 = x1 - gateS - self.GridFix(lu / 2) + (pcIndexX + 1) * pcStepX
            self._metalCont(tempShapes, cx2, y1 - gateS + 0.01, cx2,
                            y1 - gateS + wu - 0.08, metW, contW, contS)

        # ==================================================
        # 2. Top and bottom gate bus bars
        # ==================================================
        bus_x1 = x1
        bus_x2 = x1 - gateS + NX * pcStepX
        self._mkRect(tempShapes, bus_x1, y1 + wu, bus_x2, y1 + wu + 0.5, self.gateLayer)
        self._mkRect(tempShapes, bus_x1, y1 - gateS - 0.5, bus_x2, y1 - gateS,
                     self.gateLayer)

        # Metal1 + contacts on top and bottom gate bus
        self._metalCont(tempShapes, bus_x1 + 0.02, y1 - gateS - 0.25,
                        bus_x2 - 0.02, y1 - gateS - 0.25, metW, contW, contS)
        self._metalCont(tempShapes, bus_x1 + 0.02, y1 + wu + 0.25,
                        bus_x2 - 0.02, y1 + wu + 0.25, metW, contW, contS)

        # Left-side well contact
        self._metalCont(tempShapes, x1 - 0.34, y1 + (wu - gateS) / 2 - 0.48,
                        x1 - 0.34, y1 + (wu - gateS) / 2 + 0.48,
                        contW + 2 * 0.02, contW, contS)

        # ==================================================
        # 3. Pins
        # ==================================================
        # G1 pin (bottom gate bus)
        self._mkPin(tempShapes, bus_x1 + 0.02, y1 - gateS - 0.12,
                    bus_x2 - 0.02, y1 - gateS - 0.38, 'G1', self.met1Pin)
        # G2 pin (top gate bus)
        self._mkPin(tempShapes, bus_x1 + 0.02, y1 + wu + 0.12,
                    bus_x2 - 0.02, y1 + wu + 0.38, 'G2', self.met1Pin)
        # W pin (left well contact)
        self._mkPin(tempShapes, x1 - 0.44,
                    y1 + self.GridFix((wu - gateS) / 2) - 0.47,
                    x1 - 0.24,
                    y1 + self.GridFix((wu - gateS) / 2) + 0.47, 'W', self.met1Pin)

        # ==================================================
        # 4. Active, NWell, nBuLay regions
        # ==================================================
        self._mkRect(tempShapes,
                     x1 - 0.49, y1 - gateS - 0.5 + gateOactiv,
                     bus_x2 + 0.33, y1 + wu + 0.5 - gateOactiv,
                     self.activLayer)
        self._mkRect(tempShapes,
                     x1 - 0.73, y1 - gateS - 0.5 + gateOnwell,
                     bus_x2 + 0.57, y1 + wu + 0.5 - gateOnwell,
                     self.nwellLayer)
        self._mkRect(tempShapes,
                     x1 - 0.49, y1 - gateS - 0.5 + gateOnbulay,
                     bus_x2 + 0.33, y1 + wu + 0.5 - gateOnbulay,
                     self.nbulayLayer)

        # ==================================================
        # 5. pSD guard dots (anti-latchup)
        # ==================================================
        nr_psd = round((2 * NX * lu + (2 * NX - 1) * gateS - 0.24) / 10 + 0.5)
        if nr_psd > 1:
            x_psd = self.GridFix(
                (2 * NX * lu + (2 * NX - 1) * gateS - (nr_psd - 1) * 10) / 2 + 0.61)
            if x_psd < x1 + self.GridFix((2 * lu + gateS - 0.24) / 2):
                nr_psd -= 1
                x_psd = self.GridFix(
                    (2 * NX * lu + (2 * NX - 1) * gateS - (nr_psd - 1) * 10) / 2 + 0.61)
        else:
            x_psd = x1 + self.GridFix((2 * lu + gateS - 0.24) / 2)

        for pcIndexX in range(int(nr_psd)):
            xp = x_psd + pcIndexX * 10
            # Top pSD dots
            self._mkRect(tempShapes, xp, y1 + wu + 0.5 - gateOactiv,
                         xp + 0.24, y1 + wu + 0.5 - gateOactiv + 0.76,
                         self.activLayer)
            self._mkRect(tempShapes, xp - 0.1, y1 + wu + 0.6 - gateOactiv,
                         xp + 0.34, y1 + wu + 0.6 - gateOactiv + 0.76,
                         self.psdLayer)
            # Bottom pSD dots
            self._mkRect(tempShapes, xp, y1 - gateS - 0.5 + gateOactiv - 0.76,
                         xp + 0.24, y1 - gateS - 0.5 + gateOactiv,
                         self.activLayer)
            self._mkRect(tempShapes, xp - 0.1, y1 - gateS - 0.6 + gateOactiv - 0.76,
                         xp + 0.34, y1 - gateS - 0.6 + gateOactiv,
                         self.psdLayer)

        # ==================================================
        # 6. Cell label
        # ==================================================
        self._mkLabel(tempShapes, x1 - 0.49,
                      y1 - gateS - 0.5 + gateOnbulay + gateOactiv,
                      'SVaricap', self.textLayer)

        self.shapes = tempShapes
