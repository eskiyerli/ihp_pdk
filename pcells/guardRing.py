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

"""Parametric guard ring PCell for the IHP SG13G2 PDK.

The guard ring is generated as a multi-part path: parallel ``layoutPath``
segments on ``Activ``, ``pSD`` and ``Metal1`` share the same rectangular
centreline, and a ``Cont`` array fills the ring.  The resulting PCell can be
re-parameterised after placement.
"""

import math
from functools import lru_cache

from PySide6.QtCore import QLineF, QPointF
from quantiphy import Quantity

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule
from .base import baseCell

laylyr = importPDKModule('layoutLayers')
fabproc = importPDKModule('process')


class guardRing(baseCell):
    """p+ substrate guard ring around a guide rectangle.

    Parameters:
        w: Guide rectangle width (e.g. "10u").
        h: Guide rectangle height (e.g. "10u").
        ringWidth: Width of the Activ/Metal1 ring (e.g. "0.6u").
        gap: Distance from the guide rectangle to the ring inner edge
            (e.g. "0.5u").

    The PCell origin is the lower-left corner of the guide rectangle.  The
    ring is built outside this rectangle at the requested gap.
    """

    activLayer = laylyr.Activ_drawing
    psdLayer = laylyr.pSD_drawing
    metal1Layer = laylyr.Metal1_drawing
    contLayer = laylyr.Cont_drawing

    def __init__(self, w: str = "10u", h: str = "10u",
                 ringWidth: str = "0.6u", gap: str = "0.5u"):
        self.w = w
        self.h = h
        self.ringWidth = ringWidth
        self.gap = gap
        super().__init__([])

    @lru_cache
    def __call__(self, w: str, h: str, ringWidth: str, gap: str):
        self.w = w
        self.h = h
        self.ringWidth = ringWidth
        self.gap = gap

        grid_um = baseCell._sg13grid  # 0.005 um for SG13G2
        two_grid_um = 2 * grid_um
        grid_dbu = self.toSceneDimension(grid_um)

        w_um = Quantity(w).real * 1e6 if w else 10.0
        h_um = Quantity(h).real * 1e6 if h else 10.0
        rw_um = Quantity(ringWidth).real * 1e6 if ringWidth else 0.6
        gap_um = Quantity(gap).real * 1e6 if gap else 0.5

        # Snap dimensions to the process grid.  Ring width must be an even
        # multiple of the grid so path edges (centreline +/- width/2) stay
        # on-grid and corner overlaps remain clean.
        w_um = baseCell.GridFix(w_um)
        h_um = baseCell.GridFix(h_um)
        gap_um = baseCell.GridFix(gap_um)

        tp = baseCell._techParams
        cont_size = tp["Cnt_a"]
        cont_dist = tp["Cnt_b"]
        cont_diff_over = tp["Cnt_c"]
        cont_metal_endcap = tp["M1_c1"]
        psd_over = baseCell.GridFix(tp["pSD_c1"])

        min_rw = cont_size + 2 * max(cont_diff_over, cont_metal_endcap)
        min_rw = round(baseCell.GridFix(min_rw) / two_grid_um) * two_grid_um

        rw_um = baseCell.GridFix(rw_um)
        if rw_um < min_rw:
            rw_um = min_rw
        rw_um = round(rw_um / two_grid_um) * two_grid_um
        if rw_um < two_grid_um:
            rw_um = two_grid_um

        w_dbu = self.toSceneDimension(w_um)
        h_dbu = self.toSceneDimension(h_um)
        rw_dbu = self.toSceneDimension(rw_um)
        gap_dbu = self.toSceneDimension(gap_um)
        psd_over_dbu = self.toSceneDimension(psd_over)

        # Inner/outer edges of the ring relative to the guide rectangle origin.
        inner_off = gap_dbu
        outer_off = gap_dbu + rw_dbu

        activ_strips = self._frameStrips(0, 0, w_dbu, h_dbu, inner_off, outer_off)
        psd_strips = self._frameStrips(
            0, 0, w_dbu, h_dbu, inner_off - psd_over_dbu,
            outer_off + psd_over_dbu)
        csize_dbu = int(round(cont_size * fabproc.dbu / grid_dbu)) * grid_dbu
        cont_rects = self._contRects(activ_strips, cont_size, cont_dist,
                                     cont_diff_over)

        shapes = []
        for strip in psd_strips:
            shapes.append(self._stripToPath(strip, self.psdLayer,
                                            rw_dbu + 2 * psd_over_dbu))
        for strip in activ_strips:
            shapes.append(self._stripToPath(strip, self.activLayer, rw_dbu))
        for strip in activ_strips:
            shapes.append(self._stripToPath(strip, self.metal1Layer, rw_dbu))
        for rect in cont_rects:
            # Snap contact lower-left to the grid and keep exact contact size.
            x1 = round(rect[0] / grid_dbu) * grid_dbu
            y1 = round(rect[1] / grid_dbu) * grid_dbu
            shapes.append(lshp.layoutRect(
                QPointF(x1, y1), QPointF(x1 + csize_dbu, y1 + csize_dbu),
                self.contLayer))

        self.shapes = shapes

    @staticmethod
    def _frameStrips(x1, y1, x2, y2, innerOff, outerOff):
        """Four non-overlapping strips forming a rectangular frame."""
        ox1, oy1 = x1 - outerOff, y1 - outerOff
        ox2, oy2 = x2 + outerOff, y2 + outerOff
        ix1, iy1 = x1 - innerOff, y1 - innerOff
        ix2, iy2 = x2 + innerOff, y2 + innerOff
        return [
            (ox1, iy2, ox2, oy2),   # +y side
            (ox1, oy1, ox2, iy1),   # -y side
            (ox1, iy1, ix1, iy2),   # -x side
            (ix2, iy1, ox2, iy2),   # +x side
        ]

    @staticmethod
    def _contRects(strips, cont_size, cont_dist, cont_diff_over):
        """Contact rects filling each frame strip along its long axis."""
        rects = []
        dbu = fabproc.dbu
        csize = cont_size * dbu
        cdist = cont_dist * dbu
        cover = cont_diff_over * dbu
        pitch = csize + cdist
        for sx1, sy1, sx2, sy2 in strips:
            w, h = sx2 - sx1, sy2 - sy1
            length = max(w, h)
            n = int(math.floor(
                (length - 2 * cover + cdist) / pitch + 1e-6))
            if n < 1:
                continue
            if n == 1:
                first = (length - csize) / 2.0
                step = 0.0
            else:
                first = cover
                step = csize + (
                    (length - 2 * cover - n * csize) / (n - 1))
            across = (min(w, h) - csize) / 2.0
            pos = first
            for _ in range(n):
                if w >= h:
                    rects.append(
                        (sx1 + pos, sy1 + across,
                         sx1 + pos + csize, sy1 + across + csize))
                else:
                    rects.append(
                        (sx1 + across, sy1 + pos,
                         sx1 + across + csize, sy1 + pos + csize))
                pos += step
        return rects

    @staticmethod
    def _stripToPath(strip, layer, width):
        """Convert an axis-aligned strip into a layoutPath.

        ``strip`` is ``(x1, y1, x2, y2)`` with ``x1 < x2`` and ``y1 < y2``.
        The returned path follows the strip centreline.
        """
        x1, y1, x2, y2 = strip
        if (x2 - x1) >= (y2 - y1):  # horizontal or square
            return lshp.layoutPath(
                QLineF(QPointF(x1, (y1 + y2) / 2.0),
                       QPointF(x2, (y1 + y2) / 2.0)),
                layer, width)
        else:  # vertical
            return lshp.layoutPath(
                QLineF(QPointF((x1 + x2) / 2.0, y1),
                       QPointF((x1 + x2) / 2.0, y2)),
                layer, width)
