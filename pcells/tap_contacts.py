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

from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF
from quantiphy import Quantity

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule
from .base import baseCell

laylyr = importPDKModule('layoutLayers')


def _drawTap(cell, w, l, implantLayer, implantOver):
    """Build a plain tap's shapes: Cont array, Metal1, Activ and implant.

    ``w``, ``l`` and ``implantOver`` are in um.  ``implantLayer`` is pSD for
    a p+ tap or NWell for an n+ tap; ``implantOver`` is its required
    enclosure of the diffusion (pSD_c1 / NW_e).  No pins or marker layers
    are drawn, so LVS keeps the tap as plain connectivity.
    """
    tp = baseCell._techParams
    shapesCont = cell._draw_contact_array(
        w, l, tp["Cnt_a"], tp["Cnt_b"], tp["Cnt_c"])
    shapes = list(shapesCont)

    # Metal1 covers the contact array extended by the metal overhang.
    if shapesCont:
        firstRect = shapesCont[0]
        min_x = firstRect.start.x()
        min_y = firstRect.start.y()
        max_x = firstRect.end.x()
        max_y = firstRect.end.y()

        for rect in shapesCont[1:]:
            min_x = min(min_x, rect.start.x())
            min_y = min(min_y, rect.start.y())
            max_x = max(max_x, rect.end.x())
            max_y = max(max_y, rect.end.y())

        point1 = QPointF(min_x - cell.toSceneDimension(tp["M1_c"]),
                         min_y - cell.toSceneDimension(tp["M1_c1"]))
        point2 = QPointF(max_x + cell.toSceneDimension(tp["M1_c"]),
                         max_y + cell.toSceneDimension(tp["M1_c1"]))
    else:
        # Fallback: use original dimensions
        point1 = cell.toSceneCoord(QPointF(0, 0))
        point2 = cell.toSceneCoord(QPointF(w, l))

    shapes.append(lshp.layoutRect(point1, point2, laylyr.Metal1_drawing))
    shapes.append(lshp.layoutRect(cell.toSceneCoord(QPointF(0, 0)),
                                  cell.toSceneCoord(QPointF(w, l)),
                                  laylyr.Activ_drawing))
    shapes.append(lshp.layoutRect(
        cell.toSceneCoord(QPointF(-implantOver, -implantOver)),
        cell.toSceneCoord(QPointF(w + implantOver, l + implantOver)),
        implantLayer))
    return shapes


class ptap1(baseCell):
    """P-type substrate tap contact cell."""

    metal1_layer = laylyr.Metal1_drawing
    metal1_layer_pin = laylyr.Metal1_pin
    pdiff_layer = laylyr.Activ_drawing
    pdiffx_layer = laylyr.pSD_drawing
    cont_layer = laylyr.Cont_drawing
    text_layer = laylyr.TEXT_drawing

    def __init__(self, width: str = "2u", length: str = "2u"):
        self.width = width
        self.length = length
        super().__init__([])

    @lru_cache(maxsize=16)
    def __call__(self, width: str, length: str):
        self.width = Quantity(width).real if width else Quantity("2u").real
        self.length = Quantity(length).real if length else Quantity("2u").real

        tempShapesList = []
        tp = baseCell._techParams

        # Design rule definitions
        cont_size = tp["Cnt_a"]
        cont_dist = tp["Cnt_b"]
        cont_diff_over = tp["Cnt_c"]
        cont_metal_over = tp["M1_c"]
        cont_metal_endcap = tp["M1_c1"]
        pdiffx_over = tp["pSD_c1"]  # pSD enclosure of p+Activ in pWell

        wmin = Quantity(tp["ptap1_minLW"]).real * 1e6
        lmin = Quantity(tp["ptap1_minLW"]).real * 1e6

        w = self.width * 1e6
        l = self.length * 1e6

        # Check for minimum width/length
        if w < wmin - self._epsilon:
            w = wmin
            print(f"Width < {wmin}")

        if l < lmin - self._epsilon:
            l = lmin
            print(f"Length < {lmin}")

        # Draw contact array
        shapes_cont = self._draw_contact_array(
            w, l, cont_size, cont_dist, cont_diff_over
        )
        tempShapesList.extend(shapes_cont)

        # Calculate bounding box from contact array
        # Find min/max coordinates from contact array
        if shapes_cont:
            first_rect = shapes_cont[0]
            min_x = first_rect.start.x()
            min_y = first_rect.start.y()
            max_x = first_rect.end.x()
            max_y = first_rect.end.y()

            for rect in shapes_cont[1:]:
                min_x = min(min_x, rect.start.x())
                min_y = min(min_y, rect.start.y())
                max_x = max(max_x, rect.end.x())
                max_y = max(max_y, rect.end.y())

            # Expand by metal overhang
            meta_min_x = min_x - self.toSceneDimension(cont_metal_over)
            meta_min_y = min_y - self.toSceneDimension(cont_metal_endcap)
            meta_max_x = max_x + self.toSceneDimension(cont_metal_over)
            meta_max_y = max_y + self.toSceneDimension(cont_metal_endcap)

            point1 = QPointF(meta_min_x, meta_min_y)
            point2 = QPointF(meta_max_x, meta_max_y)
        else:
            # Fallback: use original dimensions
            point1 = self.toSceneCoord(QPointF(0, 0))
            point2 = self.toSceneCoord(QPointF(w, l))

        # Draw Metal1
        tempShapesList.append(lshp.layoutRect(point1, point2, self.metal1_layer))

        # Draw Metal1 pin
        tempShapesList.append(
            lshp.layoutPin(
                point1,
                point2,
                "TIE",
                lshp.layoutPin.pinDirs[2],
                lshp.layoutPin.pinTypes[0],
                self.metal1_layer_pin,
            )
        )

        # Draw p+ diffusion
        diff_point1 = self.toSceneCoord(QPointF(0, 0))
        diff_point2 = self.toSceneCoord(QPointF(w, l))
        tempShapesList.append(
            lshp.layoutRect(diff_point1, diff_point2, self.pdiff_layer)
        )

        # Draw pSD layer (p+ implant)
        psd_point1 = self.toSceneCoord(
            QPointF(-pdiffx_over, -pdiffx_over)
        )
        psd_point2 = self.toSceneCoord(
            QPointF(w + pdiffx_over, l + pdiffx_over)
        )
        tempShapesList.append(
            lshp.layoutRect(psd_point1, psd_point2, self.pdiffx_layer)
        )

        # Draw substrate pin (SUB)
        tempShapesList.append(
            lshp.layoutPin(
                diff_point1,
                diff_point2,
                "SUB",
                lshp.layoutPin.pinDirs[2],
                lshp.layoutPin.pinTypes[0],
                laylyr.Substrate_drawing,
            )
        )

        # Add text label
        center = QRectF(diff_point1, diff_point2).center()
        tempShapesList.append(
            lshp.layoutLabel(
                center,
                "sub!",
                *self._labelFontTuple,
                lshp.layoutLabel.LABEL_ALIGNMENTS[0],
                lshp.layoutLabel.LABEL_ORIENTS[0],
                self.text_layer,
            )
        )
        tempShapesList.append(
            lshp.layoutLabel(
                center,
                "sub!",
                *self._labelFontTuple,
                lshp.layoutLabel.LABEL_ALIGNMENTS[0],
                lshp.layoutLabel.LABEL_ORIENTS[0],
                laylyr.Substrate_drawing,
            )
        )

        self.shapes = tempShapesList


class subtap(baseCell):
    """Plain p+ substrate tap.

    Pure connectivity geometry: no Substrate marker and no 'sub!' TEXT, so
    LVS keeps it as plain ptap (pwell -> ptap -> cont -> metal1) and no
    device is extracted. Place a Metal1.text label over the tap to name the
    substrate net (e.g. 'VSS').
    """

    metal1_layer = laylyr.Metal1_drawing
    pdiff_layer = laylyr.Activ_drawing
    pdiffx_layer = laylyr.pSD_drawing
    cont_layer = laylyr.Cont_drawing

    def __init__(self, width: str = "2u", length: str = "2u"):
        self.width = width
        self.length = length
        super().__init__([])

    @lru_cache(maxsize=16)
    def __call__(self, width: str, length: str):
        self.width = Quantity(width).real if width else Quantity("2u").real
        self.length = Quantity(length).real if length else Quantity("2u").real

        tp = baseCell._techParams
        pdiffx_over = tp["pSD_c1"]  # pSD enclosure of p+Activ in pWell

        w = self.width * 1e6
        l = self.length * 1e6

        # Minimum size: one contact plus Activ overlap on each side
        wmin = lmin = tp["Cnt_a"] + 2 * tp["Cnt_c"]

        # Check for minimum width/length
        if w < wmin - self._epsilon:
            w = wmin
            print(f"Width < {wmin}")

        if l < lmin - self._epsilon:
            l = lmin
            print(f"Length < {lmin}")

        self.shapes = _drawTap(self, w, l, self.pdiffx_layer, pdiffx_over)


class psubtap(baseCell):
    """p+ substrate tap line.

    A minimum-width p+ tap strip (one Cont column plus Activ overlap on
    each side) of length ``length``.  Pure connectivity geometry like
    ``subtap``: place a Metal1.text label over the line to name the
    substrate net.
    """

    metal1_layer = laylyr.Metal1_drawing
    pdiff_layer = laylyr.Activ_drawing
    pdiffx_layer = laylyr.pSD_drawing
    cont_layer = laylyr.Cont_drawing

    def __init__(self, length: str = "5u"):
        self.length = length
        super().__init__([])

    @lru_cache(maxsize=16)
    def __call__(self, length: str):
        self.length = \
            Quantity(length).real if length else Quantity("5u").real

        tp = baseCell._techParams

        # Fixed strip width: one contact plus Activ overlap on each side.
        w = tp["Cnt_a"] + 2 * tp["Cnt_c"]
        l = self.length * 1e6

        if l < w - self._epsilon:
            l = w
            print(f"Length < {w}")

        self.shapes = _drawTap(self, w, l, self.pdiffx_layer, tp["pSD_c1"])


class ntap1(baseCell):
    """N-type substrate tap contact cell."""

    metal1_layer = laylyr.Metal1_drawing
    metal1_layer_pin = laylyr.Metal1_pin
    ndiff_layer = laylyr.Activ_drawing
    nwell_layer = laylyr.NWell_drawing
    nwell_layer_pin = laylyr.NWell_pin
    nbulay_layer = laylyr.nBuLay_drawing
    cont_layer = laylyr.Cont_drawing
    text_layer = laylyr.TEXT_drawing

    def __init__(self, width: str = "2u", length: str = "2u"):
        self.width = width
        self.length = length
        super().__init__([])

    @lru_cache(maxsize=16)
    def __call__(self, width: str, length: str):
        self.width = Quantity(width).real if width else Quantity("2u").real
        self.length = Quantity(length).real if length else Quantity("2u").real

        tempShapesList = []
        tp = baseCell._techParams

        # Design rule definitions
        cont_size = tp["Cnt_a"]
        cont_dist = tp["Cnt_b"]
        cont_diff_over = tp["Cnt_c"]
        cont_metal_over = tp["M1_c"]
        cont_metal_endcap = tp["M1_c1"]
        ndiff_over = tp["NW_e"]  # Minimum NWell enclosure

        wmin = Quantity(tp["ntap1_minLW"]).real * 1e6
        lmin = Quantity(tp["ntap1_minLW"]).real * 1e6

        w = self.width * 1e6
        l = self.length * 1e6

        # Check for minimum width/length
        if w < wmin - self._epsilon:
            w = wmin
            print(f"Width < {wmin}")

        if l < lmin - self._epsilon:
            l = lmin
            print(f"Length < {lmin}")

        # Draw contact array
        shapes_cont = self._draw_contact_array(
            w, l, cont_size, cont_dist, cont_diff_over
        )
        tempShapesList.extend(shapes_cont)

        # Calculate bounding box from contact array
        if shapes_cont:
            first_rect = shapes_cont[0]
            min_x = first_rect.start.x()
            min_y = first_rect.start.y()
            max_x = first_rect.end.x()
            max_y = first_rect.end.y()

            for rect in shapes_cont[1:]:
                min_x = min(min_x, rect.start.x())
                min_y = min(min_y, rect.start.y())
                max_x = max(max_x, rect.end.x())
                max_y = max(max_y, rect.end.y())

            # Expand by metal overhang
            meta_min_x = min_x - self.toSceneDimension(cont_metal_over)
            meta_min_y = min_y - self.toSceneDimension(cont_metal_endcap)
            meta_max_x = max_x + self.toSceneDimension(cont_metal_over)
            meta_max_y = max_y + self.toSceneDimension(cont_metal_endcap)

            point1 = QPointF(meta_min_x, meta_min_y)
            point2 = QPointF(meta_max_x, meta_max_y)
        else:
            # Fallback: use original dimensions
            point1 = self.toSceneCoord(QPointF(0, 0))
            point2 = self.toSceneCoord(QPointF(w, l))

        # Draw Metal1
        tempShapesList.append(lshp.layoutRect(point1, point2, self.metal1_layer))

        # Draw Metal1 pin
        tempShapesList.append(
            lshp.layoutPin(
                point1,
                point2,
                "TIE",
                lshp.layoutPin.pinDirs[2],
                lshp.layoutPin.pinTypes[0],
                self.metal1_layer_pin,
            )
        )

        # Draw n+ diffusion
        diff_point1 = self.toSceneCoord(QPointF(0, 0))
        diff_point2 = self.toSceneCoord(QPointF(w, l))
        tempShapesList.append(
            lshp.layoutRect(diff_point1, diff_point2, self.ndiff_layer)
        )

        # Draw NWell pin layer (pin marking)
        tempShapesList.append(
            lshp.layoutRect(diff_point1, diff_point2, self.nwell_layer_pin)
        )

        # Draw NWell layer (actual well)
        nwell_point1 = self.toSceneCoord(QPointF(-ndiff_over, -ndiff_over))
        nwell_point2 = self.toSceneCoord(
            QPointF(w + ndiff_over, l + ndiff_over)
        )
        tempShapesList.append(
            lshp.layoutRect(nwell_point1, nwell_point2, self.nwell_layer)
        )

        # Draw nBuLay (bulk layer)
        tempShapesList.append(
            lshp.layoutRect(nwell_point1, nwell_point2, self.nbulay_layer)
        )

        # Draw well pin (WELL)
        tempShapesList.append(
            lshp.layoutPin(
                diff_point1,
                diff_point2,
                "WELL",
                lshp.layoutPin.pinDirs[2],
                lshp.layoutPin.pinTypes[0],
                self.nwell_layer,
            )
        )

        # Add text label
        center = QRectF(diff_point1, diff_point2).center()
        tempShapesList.append(
            lshp.layoutLabel(
                center,
                "well",
                *self._labelFontTuple,
                lshp.layoutLabel.LABEL_ALIGNMENTS[0],
                lshp.layoutLabel.LABEL_ORIENTS[0],
                self.text_layer,
            )
        )
        tempShapesList.append(
            lshp.layoutLabel(
                center,
                "well",
                *self._labelFontTuple,
                lshp.layoutLabel.LABEL_ALIGNMENTS[0],
                lshp.layoutLabel.LABEL_ORIENTS[0],
                self.nwell_layer,
            )
        )

        self.shapes = tempShapesList


class nwtap(baseCell):
    """Plain n+ n-well tap.

    Pure connectivity geometry: no nBuLay marker, no NWell pin and no 'well'
    TEXT, so LVS keeps it as a plain ntap (nwell -> ntap -> cont -> metal1)
    and no device is extracted. Place a Metal1.text label over the tap to
    name the well net (e.g. 'VDD'). nSD is not drawn: it is a derived layer
    and may only be drawn inside Rhigh resistors.
    """

    metal1_layer = laylyr.Metal1_drawing
    ndiff_layer = laylyr.Activ_drawing
    nwell_layer = laylyr.NWell_drawing
    cont_layer = laylyr.Cont_drawing

    def __init__(self, width: str = "2u", length: str = "2u"):
        self.width = width
        self.length = length
        super().__init__([])

    @lru_cache(maxsize=16)
    def __call__(self, width: str, length: str):
        self.width = Quantity(width).real if width else Quantity("2u").real
        self.length = Quantity(length).real if length else Quantity("2u").real

        tp = baseCell._techParams
        ndiff_over = tp["NW_e"]  # NWell enclosure of n+Activ

        w = self.width * 1e6
        l = self.length * 1e6

        # Minimum size: one contact plus Activ overlap on each side.  The
        # enclosing NWell (Activ + 2*NW_e) then always meets NW_a.
        wmin = lmin = tp["Cnt_a"] + 2 * tp["Cnt_c"]

        # Check for minimum width/length
        if w < wmin - self._epsilon:
            w = wmin
            print(f"Width < {wmin}")

        if l < lmin - self._epsilon:
            l = lmin
            print(f"Length < {lmin}")

        self.shapes = _drawTap(self, w, l, self.nwell_layer, ndiff_over)


class nwelltap(baseCell):
    """n+ n-well tap line.

    A minimum-width n+ tap strip (one Cont column plus Activ overlap on
    each side) of length ``length``, enclosed by NWell at NW_e.  Pure
    connectivity geometry like ``nwtap``: place a Metal1.text label over
    the line to name the well net.
    """

    metal1_layer = laylyr.Metal1_drawing
    ndiff_layer = laylyr.Activ_drawing
    nwell_layer = laylyr.NWell_drawing
    cont_layer = laylyr.Cont_drawing

    def __init__(self, length: str = "5u"):
        self.length = length
        super().__init__([])

    @lru_cache(maxsize=16)
    def __call__(self, length: str):
        self.length = \
            Quantity(length).real if length else Quantity("5u").real

        tp = baseCell._techParams

        # Fixed strip width: one contact plus Activ overlap on each side.
        w = tp["Cnt_a"] + 2 * tp["Cnt_c"]
        l = self.length * 1e6

        if l < w - self._epsilon:
            l = w
            print(f"Length < {w}")

        self.shapes = _drawTap(self, w, l, self.nwell_layer, tp["NW_e"])
