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
RF MIM capacitor parametric cell for IHP SG13G2 PDK.

Features a MIM capacitor with TopMetal1 top plate, Metal5 bottom plate,
Vmim vias, pSD guard ring with Metal1/contacts, and feed lines.
"""

from functools import lru_cache

from PySide6.QtCore import QPointF
from quantiphy import Quantity

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule
from .base import baseCell

laylyr = importPDKModule('layoutLayers')


class rfcmim(baseCell):
    """
    RF MIM capacitor with ground ring and feed lines.

    Generates a MIM capacitor with:
    - MIM dielectric layer between Metal5 (bottom) and TopMetal1 (top)
    - Vmim via array connecting top plate to TopMetal1
    - pSD guard ring with Metal1 contacts for substrate connection
    - PWell block layer
    - Feed lines on TopMetal1 for PLUS, Metal5 for MINUS pins

    Parameters:
        w: Capacitor width (default "4.76u")
        l: Capacitor length (default "4.76u")
        wfeed: Feed line width (default "3u")
    """

    # Layer definitions
    textLayer = laylyr.TEXT_drawing
    tm1Layer = laylyr.TopMetal1_drawing
    tm1Pin = laylyr.TopMetal1_pin
    m5Layer = laylyr.Metal5_drawing
    m5Pin = laylyr.Metal5_pin
    mimLayer = laylyr.MIM_drawing
    vmimLayer = laylyr.Vmim_drawing
    pwellBlock = laylyr.PWell_block
    contLayer = laylyr.Cont_drawing
    activLayer = laylyr.Activ_drawing
    psdLayer = laylyr.pSD_drawing
    m1Layer = laylyr.Metal1_drawing
    m1Pin = laylyr.Metal1_pin

    def __init__(self, w: str = "4.76u", l: str = "4.76u", wfeed: str = "3u"):
        self.w = w
        self.l = l
        self.wfeed = wfeed
        super().__init__([])

    @lru_cache
    def __call__(self, w: str, l: str, wfeed: str):
        """
        Generate rfcmim layout.

        Args:
            w: Capacitor width (e.g. "4.76u")
            l: Capacitor length (e.g. "4.76u")
            wfeed: Feed line width (e.g. "3u")
        """
        self.w = w
        self.l = l
        self.wfeed = wfeed

        wu = Quantity(w).real * 1e6
        lu = Quantity(l).real * 1e6
        wf = Quantity(wfeed).real * 1e6

        # Enforce minimum: rfcmim_minLW
        tp = baseCell._techParams
        minLW = Quantity(tp["rfcmim_minLW"]).real * 1e6
        if wu < minLW - self._epsilon:
            wu = minLW
        if lu < minLW - self._epsilon:
            lu = minLW

        # Grid-fix dimensions
        lu = self.GridFix(lu)
        wu = self.GridFix(wu)
        wf = self.GridFix(wf)

        # Design rules
        via_size = tp["TV1_a"]
        via_dist = tp["TV1_b"]
        cont_size = tp["Cnt_a"]
        cont_dist = tp["Cnt_b"]
        tm_over = tp["TV1_d"]
        mim_over = tp["Mim_c"]
        via_over = tp["Mim_d"]

        tempShapes = []

        # ==================================================
        # 1. MIM capacitor body
        # ==================================================
        # Vmim via array over the MIM area
        via_enc = via_over + tm_over
        tempShapes.extend(
            self.contactArray(0, self.vmimLayer, 0, 0, lu, wu,
                              via_enc, via_enc, via_size, via_dist))

        # MIM dielectric layer
        self._mkRect(tempShapes, 0, 0, lu, wu, self.mimLayer)

        # TopMetal1 top plate (inset by via_over)
        self._mkRect(tempShapes, via_over, via_over, lu - via_over, wu - via_over,
                     self.tm1Layer)

        # Metal5 bottom plate (extended by mim_over)
        self._mkRect(tempShapes, -mim_over, -mim_over, lu + mim_over, wu + mim_over,
                     self.m5Layer)

        # PWell block
        self._mkRect(tempShapes, -3, -3, lu + 3, wu + 3, self.pwellBlock)

        # ==================================================
        # 2. Feed lines
        # ==================================================
        feedox = self.GridFix((lu - wf) / 2)
        feedoy = self.GridFix((wu - wf) / 2)

        # TopMetal1 feed (PLUS) - left side
        self._mkRect(tempShapes, -5.6, feedoy, via_over, feedoy + wf, self.tm1Layer)

        # PLUS pin
        self._mkPin(tempShapes, -5.6, feedoy, -3.6, feedoy + wf, 'PLUS', self.tm1Pin)
        self._mkLabel(tempShapes, -4.6, feedoy + wf / 2, 'PLUS', self.textLayer)

        # Metal5 feed (MINUS) - right side
        self._mkRect(tempShapes, lu + 0.6, feedoy, lu + 5.6, feedoy + wf, self.m5Layer)

        # MINUS pin
        self._mkPin(tempShapes, lu + 3.6, feedoy, lu + 5.6, feedoy + wf, 'MINUS', self.m5Pin)
        self._mkLabel(tempShapes, lu + 4.6, feedoy + wf / 2, 'MINUS', self.textLayer)

        # ==================================================
        # 3. Guard ring (Activ + pSD + Metal1 + Contacts)
        # ==================================================
        # Inner edge of guard ring at +/-3.6, outer at +/-5.6
        ring_inner = 3.6
        ring_outer = 5.6

        # Activ ring (as 4 rectangles forming a frame)
        self._mkRect(tempShapes, -ring_outer, -ring_outer,
                     lu + ring_outer, -ring_inner, self.activLayer)
        self._mkRect(tempShapes, -ring_outer, wu + ring_inner,
                     lu + ring_outer, wu + ring_outer, self.activLayer)
        self._mkRect(tempShapes, -ring_outer, -ring_inner,
                     -ring_inner, wu + ring_inner, self.activLayer)
        self._mkRect(tempShapes, lu + ring_inner, -ring_inner,
                     lu + ring_outer, wu + ring_inner, self.activLayer)

        # pSD ring (slightly larger than activ)
        psd_inner = 3.57
        psd_outer = 5.63
        self._mkRect(tempShapes, -psd_outer, -psd_outer,
                     lu + psd_outer, -psd_inner, self.psdLayer)
        self._mkRect(tempShapes, -psd_outer, wu + psd_inner,
                     lu + psd_outer, wu + psd_outer, self.psdLayer)
        self._mkRect(tempShapes, -psd_outer, -psd_inner,
                     -psd_inner, wu + psd_inner, self.psdLayer)
        self._mkRect(tempShapes, lu + psd_inner, -psd_inner,
                     lu + psd_outer, wu + psd_inner, self.psdLayer)

        # Metal1 ring (same as activ ring dimensions)
        self._mkRect(tempShapes, -ring_outer, -ring_outer,
                     lu + ring_outer, -ring_inner, self.m1Layer)
        self._mkRect(tempShapes, -ring_outer, wu + ring_inner,
                     lu + ring_outer, wu + ring_outer, self.m1Layer)
        self._mkRect(tempShapes, -ring_outer, -ring_inner,
                     -ring_inner, wu + ring_inner, self.m1Layer)
        self._mkRect(tempShapes, lu + ring_inner, -ring_inner,
                     lu + ring_outer, wu + ring_inner, self.m1Layer)

        # Ring contacts
        cont_enc = 0.36
        # Right side (split for MINUS feed gap)
        tempShapes.extend(
            self.contactArray(0, self.contLayer,
                              lu + ring_inner, -ring_inner,
                              lu + ring_outer, feedoy,
                              cont_enc, cont_enc, cont_size, cont_dist))
        tempShapes.extend(
            self.contactArray(0, self.contLayer,
                              lu + ring_inner, feedoy + wf,
                              lu + ring_outer, wu + ring_inner,
                              cont_enc, cont_enc, cont_size, cont_dist))
        # Left side
        tempShapes.extend(
            self.contactArray(0, self.contLayer,
                              -ring_outer, -ring_inner,
                              -ring_inner, wu + ring_inner,
                              cont_enc, cont_enc, cont_size, cont_dist))
        # Top
        tempShapes.extend(
            self.contactArray(0, self.contLayer,
                              -ring_outer, wu + ring_inner,
                              lu + ring_outer, wu + ring_outer,
                              cont_enc, cont_enc, cont_size, cont_dist))
        # Bottom
        tempShapes.extend(
            self.contactArray(0, self.contLayer,
                              -ring_outer, -ring_outer,
                              lu + ring_outer, -ring_inner,
                              cont_enc, cont_enc, cont_size, cont_dist))

        # ==================================================
        # 4. TIE pin on bottom Metal1
        # ==================================================
        p1 = self.toSceneCoord(QPointF(-ring_outer, -ring_outer))
        p2 = self.toSceneCoord(QPointF(lu + ring_outer, -ring_inner))
        tempShapes.append(lshp.layoutPin(
            p1, p2, 'TIE',
            lshp.layoutPin.pinDirs[2],
            lshp.layoutPin.pinTypes[0],
            self.m1Pin))
        self._mkLabel(tempShapes, lu / 2, -4.6, 'TIE', self.textLayer)

        # ==================================================
        # 5. Cell label
        # ==================================================
        self._mkLabel(tempShapes, lu / 2, wu + 2, 'rfcmim', self.textLayer)

        self.shapes = tempShapes

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
