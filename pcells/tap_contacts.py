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

import math
from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF
from quantiphy import Quantity

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule
from .base import baseCell

laylyr = importPDKModule('layoutLayers')


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

    @lru_cache
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
            min_x = first_rect.topLeft.x()
            min_y = first_rect.topLeft.y()
            max_x = first_rect.bottomRight.x()
            max_y = first_rect.bottomRight.y()

            for rect in shapes_cont[1:]:
                min_x = min(min_x, rect.topLeft.x())
                min_y = min(min_y, rect.topLeft.y())
                max_x = max(max_x, rect.bottomRight.x())
                max_y = max(max_y, rect.bottomRight.y())

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
        pin_point1 = self.toSceneCoord(QPointF(0, 0))
        pin_point2 = self.toSceneCoord(QPointF(w, l))
        tempShapesList.append(
            lshp.layoutPin(
                pin_point1,
                pin_point2,
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

        self.shapes = tempShapesList

    def _draw_contact_array(
        self, w, l, cont_size, cont_dist, cont_diff_over
    ):
        """Draw contact array for tap."""
        shapes = []

        # Calculate number of contacts
        distc = cont_size + cont_dist
        ncont_x = self.fix((w - 2 * cont_diff_over + cont_dist) / distc + self._epsilon)
        ncont_y = self.fix((l - 2 * cont_diff_over + cont_dist) / distc + self._epsilon)

        if ncont_x <= 0 or ncont_y <= 0:
            return shapes

        # Calculate spacing
        dsx = 0 if ncont_x == 1 else (w - 2 * cont_diff_over - ncont_x * cont_size) / (ncont_x - 1)
        dsy = 0 if ncont_y == 1 else (l - 2 * cont_diff_over - ncont_y * cont_size) / (ncont_y - 1)

        x_start = (w - cont_size) / 2 if ncont_x == 1 else cont_diff_over
        y_start = (l - cont_size) / 2 if ncont_y == 1 else cont_diff_over

        # Generate contact array
        x = x_start
        for i in range(ncont_x):
            y = y_start
            for j in range(ncont_y):
                x_fixed = self.GridFix(x)
                y_fixed = self.GridFix(y)
                point1 = self.toSceneCoord(QPointF(x_fixed, y_fixed))
                point2 = self.toSceneCoord(
                    QPointF(x_fixed + cont_size, y_fixed + cont_size)
                )
                shapes.append(lshp.layoutRect(point1, point2, self.cont_layer))
                y += cont_size + dsy
            x += cont_size + dsx

        return shapes


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

    @lru_cache
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
            min_x = first_rect.topLeft.x()
            min_y = first_rect.topLeft.y()
            max_x = first_rect.bottomRight.x()
            max_y = first_rect.bottomRight.y()

            for rect in shapes_cont[1:]:
                min_x = min(min_x, rect.topLeft.x())
                min_y = min(min_y, rect.topLeft.y())
                max_x = max(max_x, rect.bottomRight.x())
                max_y = max(max_y, rect.bottomRight.y())

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
        pin_point1 = self.toSceneCoord(QPointF(0, 0))
        pin_point2 = self.toSceneCoord(QPointF(w, l))
        tempShapesList.append(
            lshp.layoutPin(
                pin_point1,
                pin_point2,
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

        self.shapes = tempShapesList

    def _draw_contact_array(
        self, w, l, cont_size, cont_dist, cont_diff_over
    ):
        """Draw contact array for tap."""
        shapes = []

        # Calculate number of contacts
        distc = cont_size + cont_dist
        ncont_x = self.fix((w - 2 * cont_diff_over + cont_dist) / distc + self._epsilon)
        ncont_y = self.fix((l - 2 * cont_diff_over + cont_dist) / distc + self._epsilon)

        if ncont_x <= 0 or ncont_y <= 0:
            return shapes

        # Calculate spacing
        dsx = 0 if ncont_x == 1 else (w - 2 * cont_diff_over - ncont_x * cont_size) / (ncont_x - 1)
        dsy = 0 if ncont_y == 1 else (l - 2 * cont_diff_over - ncont_y * cont_size) / (ncont_y - 1)

        x_start = (w - cont_size) / 2 if ncont_x == 1 else cont_diff_over
        y_start = (l - cont_size) / 2 if ncont_y == 1 else cont_diff_over

        # Generate contact array
        x = x_start
        for i in range(ncont_x):
            y = y_start
            for j in range(ncont_y):
                x_fixed = self.GridFix(x)
                y_fixed = self.GridFix(y)
                point1 = self.toSceneCoord(QPointF(x_fixed, y_fixed))
                point2 = self.toSceneCoord(
                    QPointF(x_fixed + cont_size, y_fixed + cont_size)
                )
                shapes.append(lshp.layoutRect(point1, point2, self.cont_layer))
                y += cont_size + dsy
            x += cont_size + dsx

        return shapes
