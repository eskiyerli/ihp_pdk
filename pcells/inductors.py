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
Spiral inductor parametric cells for IHP SG13G2 PDK.

Includes inductor2 (2-terminal) and inductor3 (3-terminal) octagonal
spiral inductors for RF applications.
"""

import math
from functools import lru_cache

from PySide6.QtCore import QPointF
from quantiphy import Quantity

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule
import revedaEditor.backend.dataDefinitions as ddef
from .base import baseCell

laylyr = importPDKModule('layoutLayers')


def _inductorMinD(w, s, nr, grid):
    """
    Calculate minimum inner diameter for an octagonal spiral inductor.

    Args:
        w: trace width in microns
        s: trace spacing in microns
        nr: number of turns
        grid: layout grid in microns

    Returns:
        Minimum inner diameter in microns.
    """
    sqrt2 = math.sqrt(2)
    epsilon = 1e-6

    def _gridFix(x):
        return int(math.floor(x / grid + epsilon)) * grid

    if nr == 1:
        dmin = _gridFix((s + w + w) * (1 + sqrt2) / 2 + grid * 2) * 2
    elif nr == 2:
        dmin = _gridFix(
            (_gridFix(w / sqrt2 + s / 2) + _gridFix(s * 0.4143) + 0.02 + w)
            * 2 * (1 + sqrt2) + 0.01
        )
    else:
        dmin = _gridFix(
            ((_gridFix(w / sqrt2 + s / 2) + _gridFix(s * 0.4143)) * 2
             + 2 * s + 4 * w) * (1 + sqrt2)
        )
    return dmin


class inductorBase(baseCell):
    """
    Base class for octagonal spiral inductors (inductor2 and inductor3).

    Generates geometry on TopMetal2/TopMetal1 with TopVia2 crossovers,
    octagonal filler-block exclusion zones, and IND recognition layer.
    """

    # Layer definitions
    TM2:ddef.layLayer = laylyr.TopMetal2_drawing
    TM1 = laylyr.TopMetal1_drawing
    TM2p = laylyr.TopMetal2_pin
    TM1p = laylyr.TopMetal1_pin
    TV2 = laylyr.TopVia2_drawing
    IND = laylyr.IND_drawing
    INDp = laylyr.IND_pin
    PWellBlock = laylyr.PWell_block
    NoActFiller = laylyr.Activ_nofill
    NoGatFiller = laylyr.GatPoly_nofill
    NoMet1Filler = laylyr.Metal1_nofill
    NoMet2Filler = laylyr.Metal2_nofill
    NoMet3Filler = laylyr.Metal3_nofill
    NoMet4Filler = laylyr.Metal4_nofill
    NoMet5Filler = laylyr.Metal5_nofill
    NoTMet1Filler = laylyr.TopMetal1_nofill
    NoTMet2Filler = laylyr.TopMetal2_nofill
    NoRCX = laylyr.NoRCX_drawing
    substrateE = laylyr.LBE_drawing
    textLayer = laylyr.TEXT_drawing

    # Subclass overrides
    _cellName = "inductor2"
    _isType2 = True
    _isType3 = False

    def __init__(self, w: str = "2u", s: str = "2.1u",
                 d: str = "15.48u", nr_r: str = "1",
                 blockqrc: str = "True", subE: str = "False"):
        self.w = w
        self.s = s
        self.d = d
        self.nr_r = nr_r
        self.blockqrc = blockqrc
        self.subE = subE
        super().__init__([])

    @staticmethod
    def _evenp(value):
        return not (bool(int(value) & 1))

    @staticmethod
    def _oddp(value):
        return bool(int(value) & 1)

    def _mkPolygon(self, shapes, points_um, layer):
        """Create a layoutPolygon from a list of (x, y) tuples in microns."""
        scene_points = [self.toSceneCoord(QPointF(x, y)) for x, y in points_um]
        shapes.append(lshp.layoutPolygon(scene_points, layer))

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

    @lru_cache
    def __call__(self, w: str, s: str, d: str, nr_r: str,
                 blockqrc: str, subE: str):
        """
        Generate the inductor layout.

        Args:
            w: Trace width (e.g. "2u")
            s: Trace spacing (e.g. "2.1u")
            d: Inner diameter (e.g. "15.48u")
            nr_r: Number of turns (e.g. "1")
            blockqrc: Block QRC layer ("True"/"False")
            subE: Substrate etching ("True"/"False")
        """
        # Parse parameters
        w = self.GridFix(Quantity(w).real * 5e5) * 2
        s = self.GridFix(Quantity(s).real * 1e6)
        d = self.GridFix(Quantity(d).real * 5e5) * 2
        d1 = d
        nr_r = int(Quantity(nr_r).real)
        blockqrc = str(blockqrc).lower() in ('true', '1', 't')
        subE = str(subE).lower() in ('true', '1', 't')

        type2 = self._isType2
        type3 = self._isType3
        grid = 0.01

        nr_vias = round((w + 0.06) / 1.96 - 0.5)

        var = 1 + math.sqrt(2)
        d_min = _inductorMinD(w, s, nr_r, grid)
        if d < d_min:
            d = d_min

        lat_sm = self.GridFix(d / (2 * var)) * 2
        lat_big = self.GridFix((d + 2 * w) / var)
        cateta_sm = (d - lat_sm) / 2
        cateta_big = self.GridFix((d + 2 * w) / (var * math.sqrt(2)))

        tempShapes = []

        # ============================================================
        # Center tap path for inductor3 (type3 only)
        # ============================================================
        if type3:
            # Vertical path as rectangle: center tap
            self._mkRect(tempShapes, -w / 2, -0.01, w / 2, 30, self.TM2)
            self._mkLabel(tempShapes, 0, 0, 'LC', laylyr.IND_text
                          if hasattr(laylyr, 'IND_text') else self.textLayer)
            self._mkPin(tempShapes, -w / 2, -0.01, w / 2, 0.01, 'LC', self.TM2p)
            self._mkPin(tempShapes, -w / 2, -0.01, w / 2, 0.01, 'LC', self.INDp)

        # ============================================================
        # Compute initial positions
        # ============================================================
        x1 = self.GridFix(lat_sm / 2) - w
        y1 = 30 - w / 2
        x2 = self.GridFix(lat_big / 2)
        x = x1 + (x2 - x1) / 2
        y2 = nr_r * w + (nr_r - 1) * s + 30 - w
        x_cross = self.GridFix(w / math.sqrt(2) + s / 2)
        d_via_cross = self.GridFix(s * 0.4143) + grid
        d1_via_cross = self.GridFix(w * 0.4143) + grid
        x_via = x_cross + d_via_cross + grid

        if type3 or (not self._oddp(nr_r)):
            self._mkRect(tempShapes, -x_via, 30, x_via, w + 30, self.TM2)

        lat_big2 = d1_via_cross + grid

        # ============================================================
        # Via position calculation
        # ============================================================
        if (nr_r == 2) or (nr_r == 1):
            if type3:
                x1_via = (s + w / 2 + 0.5
                          + (w - nr_vias * 0.9 - (nr_vias - 1) * 1.06 - 1) / 2)
            else:
                x1_via = (s / 2 + 0.5
                          + (w - nr_vias * 0.9 - (nr_vias - 1) * 1.06 - 1) / 2)
        else:
            x1_via = (x_via + s + w + 0.5
                      + (w - nr_vias * 0.9 - (nr_vias - 1) * 1.06 - 1) / 2)

        y1_via = y2 + 0.5 + (w - nr_vias * 0.9 - (nr_vias - 1) * 1.06 - 1) / 2

        # ============================================================
        # Draw initial via array (connecting leads to spiral)
        # ============================================================
        if nr_r != 1:
            x1v = x1_via
            for pcIndex1 in range(int(nr_vias)):
                x1v_inner = x1_via
                for pcIndex2 in range(int(nr_vias)):
                    self._mkRect(tempShapes,
                                 x1v_inner, y1_via,
                                 x1v_inner + 0.9, y1_via + 0.9, self.TV2)
                    self._mkRect(tempShapes,
                                 -x1v_inner, y1_via,
                                 -(x1v_inner + 0.9), y1_via + 0.9, self.TV2)
                    x1v_inner += 1.96
                y1_via += 1.96
            # Reset y1_via for later use
            y1_via = y2 + 0.5 + (w - nr_vias * 0.9 - (nr_vias - 1) * 1.06 - 1) / 2

        # ============================================================
        # Main loop: Draw octagonal turns
        # ============================================================
        for pcIndexX in range(nr_r):
            # Build polygon points for this turn segment
            if pcIndexX == 0:
                if (nr_r == 2) or (nr_r == 1):
                    if type3:
                        pp1 = [
                            (s + w / 2, y2), (s + w / 2, y2 + w),
                            (lat_sm / 2, y2 + w),
                            (d / 2, y2 + w + cateta_sm),
                            (d / 2, y2 + w + cateta_sm + lat_sm),
                            (lat_sm / 2, y2 + w + d),
                            (x_via, y2 + w + d), (x_via, y2 + w * 2 + d),
                            (lat_sm / 2 + d1_via_cross, y2 + d + 2 * w),
                            ((d + 2 * w) / 2, y2 + w + cateta_sm + lat_sm + d1_via_cross),
                            ((d + 2 * w) / 2, y2 + w + cateta_sm - d1_via_cross),
                            (lat_sm / 2 + d1_via_cross, y2),
                        ]
                        pp2 = [(-x, y) for x, y in pp1]
                    else:
                        pp1 = [
                            (s / 2, y2), (s / 2, y2 + w),
                            (lat_sm / 2, y2 + w),
                            (d / 2, y2 + w + cateta_sm),
                            (d / 2, y2 + w + cateta_sm + lat_sm),
                            (lat_sm / 2, y2 + w + d),
                            (x_via, y2 + w + d), (x_via, y2 + w * 2 + d),
                            (lat_sm / 2 + d1_via_cross, y2 + d + 2 * w),
                            ((d + 2 * w) / 2, y2 + w + cateta_sm + lat_sm + d1_via_cross),
                            ((d + 2 * w) / 2, y2 + w + cateta_sm - d1_via_cross),
                            (lat_sm / 2 + d1_via_cross, y2),
                        ]
                        pp2 = [(-x, y) for x, y in pp1]
                else:
                    pp1 = [
                        (x_via + s + w, y2), (x_via + s + w, y2 + w),
                        (lat_sm / 2, y2 + w),
                        (d / 2, y2 + w + cateta_sm),
                        (d / 2, y2 + w + cateta_sm + lat_sm),
                        (lat_sm / 2, y2 + w + d),
                        (x_via, y2 + w + d), (x_via, y2 + w * 2 + d),
                        (lat_sm / 2 + d1_via_cross, y2 + d + 2 * w),
                        ((d + 2 * w) / 2, y2 + w + cateta_sm + lat_sm + d1_via_cross),
                        ((d + 2 * w) / 2, y2 + w + cateta_sm - d1_via_cross),
                        (lat_sm / 2 + d1_via_cross, y2),
                    ]
                    pp2 = [(-x, y) for x, y in pp1]
            else:
                pp1 = [
                    (x1, y2), (x1, y2 + w),
                    (lat_sm / 2, y2 + w),
                    (d / 2, y2 + w + cateta_sm),
                    (d / 2, y2 + w + cateta_sm + lat_sm),
                    (lat_sm / 2, y2 + w + d),
                    (x_via, y2 + w + d), (x_via, y2 + w * 2 + d),
                    (lat_sm / 2 + d1_via_cross, y2 + d + 2 * w),
                    ((d + 2 * w) / 2, y2 + w + cateta_sm + lat_sm + d1_via_cross),
                    ((d + 2 * w) / 2, y2 + w + cateta_sm - d1_via_cross),
                    (lat_sm / 2 + d1_via_cross, y2),
                ]
                pp2 = [(-x, y) for x, y in pp1]

            self._mkPolygon(tempShapes, pp1, self.TM2)
            self._mkPolygon(tempShapes, pp2, self.TM2)

            # ========================================================
            # Even-indexed turn: crossover geometry
            # ========================================================
            if self._evenp(pcIndexX):
                if type2 and (self._oddp(nr_r) and (pcIndexX == nr_r - 1)):
                    # Final turn for odd-turn inductor2: simple bridge
                    pp4 = [
                        (x_via, y2 + w + d), (x_via, y2 + w * 2 + d),
                        (-x_via, y2 + w * 2 + d), (-x_via, y2 + w + d),
                    ]
                    self._mkPolygon(tempShapes, pp4, self.TM2)
                else:
                    # Crossover on TM1 (right side)
                    pp3_tm1 = [
                        (x_via + w, y2 + w + d),
                        (x_via + w, y2 + w * 2 + d),
                        (x_cross, y2 + w * 2 + d),
                        (x_cross - (w + s + 2 * grid), y2 + w * 3 + s + d + 2 * grid),
                        (-x_via - w, y2 + w * 3 + s + d + 2 * grid),
                        (-x_via - w, y2 + w * 2 + s + d + 2 * grid),
                        (-x_cross, y2 + w * 2 + s + d + 2 * grid),
                        (w + s + 2 * grid - x_cross, y2 + w + d),
                    ]
                    self._mkPolygon(tempShapes, pp3_tm1, self.TM1)

                    # Crossover on TM2 (left side)
                    pp3_tm2 = [
                        (-x_via, y2 + w + d),
                        (-x_via, y2 + w * 2 + d),
                        (-x_cross, y2 + w * 2 + d),
                        (w + s + 2 * grid - x_cross, y2 + w * 3 + s + d + 2 * grid),
                        (x_via, y2 + w * 3 + s + d + 2 * grid),
                        (x_via, y2 + w * 2 + s + d + 2 * grid),
                        (x_cross + 3 * grid, y2 + w * 2 + s + d + 2 * grid),
                        (x_cross - (w + s - grid), y2 + w + d),
                    ]
                    self._mkPolygon(tempShapes, pp3_tm2, self.TM2)

                    # Vias at the upper crossover
                    xv = x_via + 0.5 + (w - nr_vias * 0.9 - (nr_vias - 1) * 1.06 - 1) / 2
                    yv = y2 + w + d + 0.5 + (w - nr_vias * 0.9 - (nr_vias - 1) * 1.06 - 1) / 2
                    for _ in range(int(nr_vias)):
                        xvi = xv
                        for _ in range(int(nr_vias)):
                            self._mkRect(tempShapes, xvi, yv, xvi + 0.9, yv + 0.9, self.TV2)
                            self._mkRect(tempShapes, -xvi, yv + s + w,
                                         -(xvi + 0.9), yv + 0.9 + s + w, self.TV2)
                            xvi += 1.96
                        yv += 1.96

                # Lower crossover (connects inner turns, pcIndexX != 0)
                if pcIndexX != 0:
                    pp3_tm2_lower = [
                        (x_via, y2), (x_via, y2 + w),
                        (x_cross + grid, y2 + w),
                        (x_cross - (w + s) + grid, y2 + w * 2 + s),
                        (-x_via, y2 + w * 2 + s),
                        (-x_via, y2 + w + s),
                        (-x_cross, y2 + w + s),
                        (-x_cross + w + s, y2),
                    ]
                    self._mkPolygon(tempShapes, pp3_tm2_lower, self.TM2)

                    pp3_tm1_lower = [
                        (-x_via - w, y2), (-x_via - w, y2 + w),
                        (-x_cross - grid, y2 + w),
                        (-x_cross + w + s - grid, y2 + w * 2 + s),
                        (x_via + w + grid, y2 + w * 2 + s),
                        (x_via + w + grid, y2 + w + s),
                        (x_cross, y2 + w + s),
                        (x_cross - (w + s), y2),
                    ]
                    self._mkPolygon(tempShapes, pp3_tm1_lower, self.TM1)

                    # Vias at lower crossover
                    xv = (x_via + grid + 0.5
                          + (w - nr_vias * 0.9 - (nr_vias - 1) * 1.06 - 1) / 2)
                    yv = (y2 + w + s + 0.5
                          + (w - nr_vias * 0.9 - (nr_vias - 1) * 1.06 - 1) / 2)
                    for _ in range(int(nr_vias)):
                        xvi = xv
                        for _ in range(int(nr_vias)):
                            self._mkRect(tempShapes, xvi, yv,
                                         xvi + 0.9, yv + 0.9, self.TV2)
                            self._mkRect(tempShapes, -xvi + grid, yv - s - w,
                                         -(xvi - grid + 0.9), yv + 0.9 - s - w,
                                         self.TV2)
                            xvi += 1.96
                        yv += 1.96

            # ========================================================
            # Update geometry for next turn
            # ========================================================
            y2 = y2 - w - s
            x1 = x_via
            d = d + 2 * (s + w + grid)
            lat_sm = self.GridFix(d / (2 * var)) * 2
            lat_big = self.GridFix((d + 2 * w) / var)
            cateta_sm = (d - lat_sm) / 2
            cateta_big = self.GridFix((d + 2 * w) / (var * math.sqrt(2)))

        # ============================================================
        # Draw lead-in paths (vertical TM1 or TM2 rectangles)
        # ============================================================
        if type2:
            if (nr_r == 2) or (nr_r == 1):
                x1 = (w + s) / 2
            else:
                x1 = x1 + w / 2 + s + w
        else:
            if nr_r == 2:
                x1 = w + s
            else:
                x1 = x1 + w / 2 + s + w

        # Lead height
        lead_top = nr_r * w + (nr_r - 1) * s + 30
        lead_bottom = -0.01

        if type2 and (nr_r == 1):
            # Single-turn inductor2: leads on TM2
            self._mkRect(tempShapes, x1 - w / 2, lead_bottom,
                         x1 + w / 2, lead_top, self.TM2)
            self._mkRect(tempShapes, -x1 - w / 2, lead_bottom,
                         -x1 + w / 2, lead_top, self.TM2)
            # Pins on TM2
            self._mkPin(tempShapes, x1 - w / 2, -0.01, x1 + w / 2, 0.01,
                        'LB', self.TM2p)
            self._mkPin(tempShapes, -x1 - w / 2, -0.01, -x1 + w / 2, 0.01,
                        'LA', self.TM2p)
            # IND pins
            self._mkPin(tempShapes, x1 - w / 2, -0.01, x1 + w / 2, 0.01,
                        'LB', self.INDp)
            self._mkPin(tempShapes, -x1 - w / 2, -0.01, -x1 + w / 2, 0.01,
                        'LA', self.INDp)
        else:
            # Multi-turn or inductor3: leads on TM1
            self._mkRect(tempShapes, x1 - w / 2, lead_bottom,
                         x1 + w / 2, lead_top, self.TM1)
            self._mkRect(tempShapes, -x1 - w / 2, lead_bottom,
                         -x1 + w / 2, lead_top, self.TM1)
            # Pins on TM1
            self._mkPin(tempShapes, x1 - w / 2, -0.01, x1 + w / 2, 0.01,
                        'LB', self.TM1p)
            self._mkPin(tempShapes, -x1 - w / 2, -0.01, -x1 + w / 2, 0.01,
                        'LA', self.TM1p)
            # IND pins
            self._mkPin(tempShapes, x1 - w / 2, -0.01, x1 + w / 2, 0.01,
                        'LB', self.INDp)
            self._mkPin(tempShapes, -x1 - w / 2, -0.01, -x1 + w / 2, 0.01,
                        'LA', self.INDp)

        # Pin labels
        self._mkLabel(tempShapes, x1, 0, 'LB', self.textLayer)
        self._mkLabel(tempShapes, -x1, 0, 'LA', self.textLayer)

        # Cell name label
        self._mkLabel(tempShapes, 0, y2 + cateta_sm / 2 + lat_sm,
                      self._cellName, self.textLayer)

        # ============================================================
        # Draw octagonal exclusion zone (filler block, IND, etc.)
        # ============================================================
        # Reset d and recalculate for the outer octagon
        y2_oct = 0
        d_oct = d - 2 * s + 2 * 30
        lat_sm_oct = self.GridFix(d_oct / (2 * var)) * 2
        cateta_sm_oct = (d_oct - lat_sm_oct) / 2

        octagon_pts = [
            (lat_sm_oct / 2, y2_oct),
            (d_oct / 2, y2_oct + cateta_sm_oct),
            (d_oct / 2, y2_oct + cateta_sm_oct + lat_sm_oct),
            (lat_sm_oct / 2, y2_oct + d_oct),
            (-lat_sm_oct / 2, y2_oct + d_oct),
            (-d_oct / 2, y2_oct + cateta_sm_oct + lat_sm_oct),
            (-d_oct / 2, y2_oct + cateta_sm_oct),
            (-lat_sm_oct / 2, y2_oct),
        ]

        filler_layers = [
            self.PWellBlock, self.NoActFiller, self.NoGatFiller,
            self.NoMet1Filler, self.NoMet2Filler, self.NoMet3Filler,
            self.NoMet4Filler, self.NoMet5Filler,
            self.NoTMet1Filler, self.NoTMet2Filler,
        ]

        for layer in filler_layers:
            self._mkPolygon(tempShapes, octagon_pts, layer)

        # IND recognition layer
        self._mkPolygon(tempShapes, octagon_pts, self.IND)

        # Optional NoRCX layer
        if blockqrc:
            self._mkPolygon(tempShapes, octagon_pts, self.NoRCX)

        # Optional substrate etching layer
        if subE:
            self._mkPolygon(tempShapes, octagon_pts, self.substrateE)

        # ============================================================
        # LVS parameter label
        # ============================================================
        xs = [pt[0] for pt in octagon_pts]
        x_left_edge = min(xs)
        y2_label = 2 * nr_r * w + 2 * (nr_r - 1) * s
        pcLabelText = (f"  width={w:.1f}\n  space={s:.1f}\n"
                       f"  diameter={d1:.2f}\n  turns={nr_r:d}")
        self._mkLabel(tempShapes, x_left_edge,
                      y2_label + (d1 - lat_sm_oct) / 4 + lat_sm_oct,
                      pcLabelText, self.textLayer)

        self.shapes = tempShapes


class inductor2(inductorBase):
    """
    2-terminal octagonal spiral inductor.

    Parameters:
        w: Trace width (default "2u")
        s: Trace spacing (default "2.1u")
        d: Inner diameter (default "15.48u")
        nr_r: Number of turns (default "1")
        blockqrc: Block QRC layer (default "True")
        subE: Substrate etching (default "False")
    """
    _cellName = "inductor2"
    _isType2 = True
    _isType3 = False

    def __init__(self, w: str = "2u", s: str = "2.1u",
                 d: str = "15.48u", nr_r: str = "1",
                 blockqrc: str = "True", subE: str = "False"):
        super().__init__(w, s, d, nr_r, blockqrc, subE)
