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
ESD protection device parametric cells for IHP SG13G2 PDK.

Fixed-geometry ESD cells with model selection. Supported models:
- diodevdd_2kv: VDD-side 2kV diode ESD clamp
- diodevss_2kv: VSS-side 2kV diode ESD clamp
- diodevdd_4kv: VDD-side 4kV diode ESD clamp
- diodevss_4kv: VSS-side 4kV diode ESD clamp
- nmoscl_2: 2-finger NMOS clamp
- nmoscl_4: 4-finger NMOS clamp
"""

from functools import lru_cache

from PySide6.QtCore import QPointF
from quantiphy import Quantity

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule
from .base import baseCell

laylyr = importPDKModule('layoutLayers')


class esd(baseCell):
    """
    ESD protection device with fixed geometry per model variant.

    This is a fixed-geometry cell: the layout is entirely determined
    by the model parameter. Contact/via arrays use technology parameters
    for sizing, but polygon shapes are hard-coded per KLayout original.

    Parameters:
        model: ESD variant (default "diodevdd_2kv")
    """

    # Layer definitions
    metal1_layer = laylyr.Metal1_drawing
    metal1_pin = laylyr.Metal1_pin
    metal2_layer = laylyr.Metal2_drawing
    metal2_pin = laylyr.Metal2_pin
    metal3_layer = laylyr.Metal3_drawing
    metal3_pin = laylyr.Metal3_pin
    via1_layer = laylyr.Via1_drawing
    via2_layer = laylyr.Via2_drawing
    activ_layer = laylyr.Activ_drawing
    gatpoly_layer = laylyr.GatPoly_drawing
    salblock_layer = laylyr.SalBlock_drawing
    thickgateox_layer = laylyr.ThickGateOx_drawing
    psd_layer = laylyr.pSD_drawing
    nwell_layer = laylyr.NWell_drawing
    cont_layer = laylyr.Cont_drawing
    recog_esd_layer = laylyr.Recog_esd
    recog_layer = laylyr.Recog_drawing
    text_layer = laylyr.TEXT_drawing

    _VALID_MODELS = [
        'diodevdd_2kv', 'diodevss_2kv',
        'diodevdd_4kv', 'diodevss_4kv',
        'nmoscl_2', 'nmoscl_4',
    ]

    def __init__(self, model: str = "diodevdd_2kv"):
        self.model = model
        super().__init__([])

    def _mkRect(self, shapes, x1, y1, x2, y2, layer):
        """Create a layoutRect from micron coordinates."""
        p1 = self.toSceneCoord(QPointF(x1, y1))
        p2 = self.toSceneCoord(QPointF(x2, y2))
        shapes.append(lshp.layoutRect(p1, p2, layer))

    def _mkPolygon(self, shapes, points, layer):
        """Create a layoutPolygon from a list of (x, y) tuples in microns."""
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

    def _mkRectArray(self, shapes, x0, y0, n_rows, n_cols, size, offset, layer):
        """
        Create an n_rows x n_cols array of square contacts/vias.

        Args:
            x0, y0: Lower-left corner of first element
            n_rows: Number of rows
            n_cols: Number of columns
            size: Square size of each element
            offset: Spacing between elements
            layer: Target layer
        """
        for i in range(n_rows):
            for j in range(n_cols):
                x = x0 + j * (size + offset)
                y = y0 + i * (size + offset)
                self._mkRect(shapes, x, y, x + size, y + size, layer)

    @lru_cache(maxsize=16)
    def __call__(self, model: str = "diodevdd_2kv"):
        """
        Generate ESD device layout for the specified model.

        Args:
            model: ESD variant name
        """
        if model is None:
            model = self.model
        self.model = model

        if model not in self._VALID_MODELS:
            print(f"esd: unknown model '{model}', valid: {self._VALID_MODELS}")
            self.shapes = []
            return

        tp = baseCell._techParams
        cont_size = tp["Cnt_a"]
        cont_dist = tp["Cnt_b"]
        via1_size = tp["Vn_a"]
        via1_sep = tp["Vn_b1"]
        cont_sep = 0.2

        tempShapes = []

        if model == 'diodevdd_2kv':
            self._gen_diodevdd_2kv(tempShapes, cont_size, cont_sep, via1_size,
                                   via1_sep)
        elif model == 'diodevss_2kv':
            self._gen_diodevss_2kv(tempShapes, cont_size, cont_sep, via1_size,
                                   via1_sep)
        elif model == 'diodevdd_4kv':
            self._gen_diodevdd_4kv(tempShapes, cont_size, cont_sep, via1_size,
                                   via1_sep)
        elif model == 'diodevss_4kv':
            self._gen_diodevss_4kv(tempShapes, cont_size, cont_sep, via1_size,
                                   via1_sep)
        elif model == 'nmoscl_2':
            self._gen_nmoscl_2(tempShapes, cont_size, cont_sep, via1_size,
                               via1_sep)
        elif model == 'nmoscl_4':
            self._gen_nmoscl_4(tempShapes, cont_size, cont_sep, via1_size,
                               via1_sep)

        self.shapes = tempShapes

    # ------------------------------------------------------------------
    # diodevdd_2kv: VDD-side 2kV diode ESD clamp (9.72 x 37.05 um)
    # ------------------------------------------------------------------
    def _gen_diodevdd_2kv(self, shapes, cont_size, cont_sep, via1_size, via1_sep):
        # Recognition layer
        self._mkRect(shapes, 0, 0, 9.72, 37.05, self.recog_esd_layer)

        # Labels
        self._mkLabel(shapes, -0.32, 18.535, 'PAD', self.text_layer)
        self._mkLabel(shapes, 9.15, 18.99, 'VDD', self.text_layer)
        self._mkLabel(shapes, 4.86, 0.675, 'VSS', self.text_layer)

        # Contact arrays
        self._mkRectArray(shapes, 0.64, 0.61, 1, 24, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 0.64, 36.28, 1, 24, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 0.58, 1.145, 97, 1, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 8.98, 1.145, 97, 1, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 4.44, 4.89, 77, 3, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 2.165, 3.405, 85, 3, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 6.695, 3.405, 85, 3, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 2.055, 2.19, 3, 16, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 2.055, 34.02, 3, 16, cont_size, cont_sep, self.cont_layer)

        # Via1 arrays
        self._mkRectArray(shapes, 1.99, 3.74, 6, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 1.99, 12.74, 6, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 1.99, 21.74, 6, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 1.99, 30.74, 6, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 6.55, 3.74, 6, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 6.55, 12.74, 6, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 6.55, 21.74, 6, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 6.55, 30.74, 6, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 4.305, 7.76, 8, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 4.305, 16.76, 8, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 4.305, 25.76, 8, 3, via1_size, via1_sep, self.via1_layer)

        # Activ polygons
        self._mkPolygon(shapes, [(4.23, 4.73), (4.23, 32.51), (5.49, 32.51), (5.49, 4.73)],
                        self.activ_layer)
        self._mkPolygon(shapes, [
            (1.98, 1.98), (1.98, 3.24), (6.51, 3.24), (6.51, 33.81),
            (3.24, 33.81), (3.24, 3.24), (1.98, 3.24), (1.98, 35.07),
            (7.77, 35.07), (7.77, 1.98)], self.activ_layer)
        self._mkPolygon(shapes, [
            (0.42, 0.45), (0.42, 0.93), (8.82, 0.93), (8.82, 36.12),
            (0.90, 36.12), (0.90, 0.93), (0.42, 0.93), (0.42, 36.60),
            (9.30, 36.60), (9.30, 0.45)], self.activ_layer)

        # pSD polygons
        self._mkPolygon(shapes, [
            (0.0, 0.0), (0.0, 1.35), (8.40, 1.35), (8.40, 35.70),
            (1.35, 35.70), (1.35, 1.35), (0.0, 1.35), (0.0, 37.05),
            (9.72, 37.05), (9.72, 0.0)], self.psd_layer)
        self._mkPolygon(shapes, [(3.81, 4.07), (3.81, 33.14), (5.91, 33.14), (5.91, 4.07)],
                        self.psd_layer)

        # NWell
        self._mkPolygon(shapes, [(1.56, 1.56), (1.56, 35.49), (8.19, 35.49), (8.19, 1.56)],
                        self.nwell_layer)

        # Metal1 polygons
        self._mkPolygon(shapes, [
            (1.83, 1.89), (1.83, 3.30), (6.36, 3.30), (6.36, 33.75),
            (3.36, 33.75), (3.36, 3.30), (1.83, 3.30), (1.83, 35.16),
            (7.92, 35.16), (7.92, 1.89)], self.metal1_layer)
        self._mkPolygon(shapes, [
            (0.0, 0.0), (0.0, 1.35), (8.40, 1.35), (8.40, 35.70),
            (1.35, 35.70), (1.35, 1.35), (0.0, 1.35), (0.0, 37.05),
            (9.72, 37.05), (9.72, 0.0)], self.metal1_layer)
        self._mkPolygon(shapes, [(3.96, 4.43), (3.96, 32.78), (5.76, 32.78), (5.76, 4.43)],
                        self.metal1_layer)

        # Metal1 pin
        self._mkPolygon(shapes, [(0.0, 0.0), (0.0, 1.35), (9.72, 1.35), (9.72, 0.0)],
                        self.metal1_pin)

        # Metal2 polygons
        self._mkPolygon(shapes, [
            (1.94, 3.735), (1.94, 6.335), (7.34, 6.335), (7.34, 12.735),
            (1.94, 12.735), (1.94, 15.335), (7.34, 15.335), (7.34, 21.735),
            (1.94, 21.735), (1.94, 24.335), (7.34, 24.335), (7.34, 30.735),
            (1.94, 30.735), (1.94, 33.335), (10.94, 33.335), (10.94, 3.735)],
            self.metal2_layer)
        self._mkPolygon(shapes, [
            (-2.12, 7.755), (-2.12, 29.315), (5.505, 29.315), (5.505, 25.755),
            (1.48, 25.755), (1.48, 20.315), (5.505, 20.315), (5.505, 16.755),
            (1.48, 16.755), (1.48, 11.315), (5.505, 11.315), (5.505, 7.755)],
            self.metal2_layer)

        # Metal2 pins
        self._mkPolygon(shapes, [(-2.12, 7.755), (-2.12, 29.315), (1.48, 29.315), (1.48, 7.755)],
                        self.metal2_pin)
        self._mkPolygon(shapes, [(7.34, 3.735), (7.34, 33.335), (10.94, 33.335), (10.94, 3.735)],
                        self.metal2_pin)

    # ------------------------------------------------------------------
    # diodevss_2kv: VSS-side 2kV diode ESD clamp (9.72 x 37.05 um)
    # ------------------------------------------------------------------
    def _gen_diodevss_2kv(self, shapes, cont_size, cont_sep, via1_size, via1_sep):
        # Recognition layer
        self._mkRect(shapes, 0, 0, 9.72, 37.05, self.recog_esd_layer)

        # Labels
        self._mkLabel(shapes, -0.2, 18.535, 'PAD', self.text_layer)
        self._mkLabel(shapes, 9.15, 18.99, 'VSS', self.text_layer)
        self._mkLabel(shapes, 4.86, 36.375, 'VDD', self.text_layer)

        # Contact arrays (same as diodevdd_2kv)
        self._mkRectArray(shapes, 0.64, 0.61, 1, 24, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 0.64, 36.28, 1, 24, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 0.58, 1.145, 97, 1, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 8.98, 1.145, 97, 1, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 4.44, 4.89, 77, 3, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 2.165, 3.405, 85, 3, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 6.695, 3.405, 85, 3, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 2.055, 2.19, 3, 16, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 2.055, 34.02, 3, 16, cont_size, cont_sep, self.cont_layer)

        # Via1 arrays
        self._mkRectArray(shapes, 2.03, 3.73, 6, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 2.03, 12.73, 6, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 2.03, 21.73, 6, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 2.03, 30.73, 6, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 6.59, 3.73, 6, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 6.59, 12.73, 6, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 6.59, 21.73, 6, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 6.59, 30.73, 6, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 4.285, 7.745, 8, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 4.285, 16.745, 8, 3, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 4.285, 25.745, 8, 3, via1_size, via1_sep, self.via1_layer)

        # Activ polygons (same as diodevdd_2kv)
        self._mkPolygon(shapes, [(4.23, 4.73), (4.23, 32.51), (5.49, 32.51), (5.49, 4.73)],
                        self.activ_layer)
        self._mkPolygon(shapes, [
            (1.98, 1.98), (1.98, 3.24), (6.51, 3.24), (6.51, 33.81),
            (3.24, 33.81), (3.24, 3.24), (1.98, 3.24), (1.98, 35.07),
            (7.77, 35.07), (7.77, 1.98)], self.activ_layer)
        self._mkPolygon(shapes, [
            (0.42, 0.45), (0.42, 0.93), (8.82, 0.93), (8.82, 36.12),
            (0.90, 36.12), (0.90, 0.93), (0.42, 0.93), (0.42, 36.60),
            (9.30, 36.60), (9.30, 0.45)], self.activ_layer)

        # pSD (mirrored: inner well is at different position for VSS)
        self._mkPolygon(shapes, [
            (1.56, 1.56), (1.56, 3.66), (6.09, 3.66), (6.09, 33.39),
            (3.66, 33.39), (3.66, 3.66), (1.56, 3.66), (1.56, 35.49),
            (8.19, 35.49), (8.19, 1.56)], self.psd_layer)

        # NWell (outer ring for VSS variant)
        self._mkPolygon(shapes, [
            (0.0, 0.0), (0.0, 1.35), (8.40, 1.35), (8.40, 35.70),
            (1.35, 35.70), (1.35, 1.35), (0.0, 1.35), (0.0, 37.05),
            (9.72, 37.05), (9.72, 0.0)], self.nwell_layer)

        # Metal1
        self._mkPolygon(shapes, [
            (1.83, 1.89), (1.83, 3.30), (6.36, 3.30), (6.36, 33.75),
            (3.36, 33.75), (3.36, 3.30), (1.83, 3.30), (1.83, 35.16),
            (7.92, 35.16), (7.92, 1.89)], self.metal1_layer)
        self._mkPolygon(shapes, [
            (0.0, 0.0), (0.0, 1.35), (8.40, 1.35), (8.40, 35.70),
            (1.35, 35.70), (1.35, 1.35), (0.0, 1.35), (0.0, 37.05),
            (9.72, 37.05), (9.72, 0.0)], self.metal1_layer)
        self._mkPolygon(shapes, [(4.11, 4.43), (4.11, 32.78), (5.64, 32.78), (5.64, 4.43)],
                        self.metal1_layer)

        # Metal1 pin (top strip for VSS)
        self._mkPolygon(shapes, [(0.0, 35.70), (0.0, 37.05), (9.72, 37.05), (9.72, 35.70)],
                        self.metal1_pin)

        # Metal2 polygons
        self._mkPolygon(shapes, [
            (1.98, 3.725), (1.98, 6.325), (7.38, 6.325), (7.38, 12.725),
            (1.98, 12.725), (1.98, 15.325), (7.38, 15.325), (7.38, 21.725),
            (1.98, 21.725), (1.98, 24.325), (7.38, 24.325), (7.38, 30.725),
            (1.98, 30.725), (1.98, 33.325), (10.98, 33.325), (10.98, 3.725)],
            self.metal2_layer)
        self._mkPolygon(shapes, [
            (-2.08, 7.755), (-2.08, 29.305), (5.30, 29.305), (5.30, 25.755),
            (1.52, 25.755), (1.52, 20.305), (5.30, 20.305), (5.30, 16.755),
            (1.52, 16.755), (1.52, 11.305), (5.30, 11.305), (5.30, 7.755)],
            self.metal2_layer)

        # Metal2 pins
        self._mkPolygon(shapes, [(-2.08, 7.745), (-2.08, 29.305), (1.52, 29.305), (1.52, 7.745)],
                        self.metal2_pin)
        self._mkPolygon(shapes, [(7.38, 3.725), (7.38, 33.325), (10.98, 33.325), (10.98, 3.725)],
                        self.metal2_pin)

    # ------------------------------------------------------------------
    # diodevdd_4kv: VDD-side 4kV diode ESD clamp (14.32 x 37.05 um)
    # ------------------------------------------------------------------
    def _gen_diodevdd_4kv(self, shapes, cont_size, cont_sep, via1_size, via1_sep):
        # Recognition layer
        self._mkRect(shapes, 0, 0, 14.32, 37.05, self.recog_esd_layer)

        # Labels
        self._mkLabel(shapes, -0.51, 18.442, 'PAD', self.text_layer)
        self._mkLabel(shapes, 13.64, 18.525, 'VDD', self.text_layer)
        self._mkLabel(shapes, 7.16, 0.675, 'VSS', self.text_layer)

        # Contact arrays
        self._mkRectArray(shapes, 0.62, 0.61, 1, 37, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 0.62, 36.28, 1, 37, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 0.58, 1.105, 97, 1, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 13.54, 1.105, 97, 1, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 4.44, 4.81, 77, 3, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 8.97, 4.81, 77, 3, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 2.165, 3.405, 85, 3, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 6.725, 3.405, 85, 3, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 11.285, 3.405, 85, 3, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 2.235, 2.19, 3, 28, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 2.235, 34.02, 3, 28, cont_size, cont_sep, self.cont_layer)

        # Via1 arrays
        for xoff in [2.005, 6.565, 11.125]:
            for yoff in [3.72, 12.72, 21.72, 30.72]:
                self._mkRectArray(shapes, xoff, yoff, 6, 3, via1_size, via1_sep,
                                  self.via1_layer)
        for xoff in [4.305, 8.835]:
            for yoff in [7.68, 16.68, 25.68]:
                self._mkRectArray(shapes, xoff, yoff, 8, 3, via1_size, via1_sep,
                                  self.via1_layer)

        # Activ polygons
        self._mkPolygon(shapes, [(4.23, 4.65), (4.23, 32.43), (5.49, 32.43), (5.49, 4.65)],
                        self.activ_layer)
        self._mkPolygon(shapes, [(8.76, 4.65), (8.76, 32.43), (10.02, 32.43), (10.02, 4.65)],
                        self.activ_layer)
        self._mkPolygon(shapes, [
            (1.98, 1.98), (1.98, 3.24), (11.05, 3.24), (11.05, 33.81),
            (7.77, 33.81), (7.77, 3.24), (6.51, 3.24), (6.51, 33.81),
            (3.24, 33.81), (3.24, 3.24), (1.98, 3.24), (1.98, 35.07),
            (12.31, 35.07), (12.31, 1.98)], self.activ_layer)
        self._mkPolygon(shapes, [
            (0.42, 0.45), (0.42, 0.93), (13.42, 0.93), (13.42, 36.12),
            (0.90, 36.12), (0.90, 0.93), (0.42, 0.93), (0.42, 36.60),
            (13.90, 36.60), (13.90, 0.45)], self.activ_layer)

        # pSD polygons
        self._mkPolygon(shapes, [
            (0.0, 0.0), (0.0, 1.35), (13.0, 1.35), (13.0, 35.70),
            (1.35, 35.70), (1.35, 1.35), (0.0, 1.35), (0.0, 37.05),
            (14.32, 37.05), (14.32, 0.0)], self.psd_layer)
        self._mkPolygon(shapes, [(3.81, 3.99), (3.81, 33.06), (5.91, 33.06), (5.91, 3.99)],
                        self.psd_layer)
        self._mkPolygon(shapes, [(8.34, 3.99), (8.34, 33.06), (10.44, 33.06), (10.44, 3.99)],
                        self.psd_layer)

        # NWell
        self._mkPolygon(shapes, [(1.56, 1.56), (1.56, 35.49), (12.79, 35.49), (12.79, 1.56)],
                        self.nwell_layer)

        # Metal1 polygons
        self._mkPolygon(shapes, [
            (1.83, 1.89), (1.83, 3.30), (10.90, 3.30), (10.90, 33.75),
            (7.92, 33.75), (7.92, 3.30), (6.36, 3.30), (6.36, 33.75),
            (3.36, 33.75), (3.36, 3.30), (1.83, 3.30), (1.83, 35.16),
            (12.46, 35.16), (12.46, 1.89)], self.metal1_layer)
        self._mkPolygon(shapes, [
            (0.0, 0.0), (0.0, 1.35), (13.0, 1.35), (13.0, 35.70),
            (1.35, 35.70), (1.35, 1.35), (0.0, 1.35), (0.0, 37.05),
            (14.32, 37.05), (14.32, 0.0)], self.metal1_layer)
        self._mkPolygon(shapes, [(3.96, 4.35), (3.96, 32.70), (5.76, 32.70), (5.76, 4.35)],
                        self.metal1_layer)
        self._mkPolygon(shapes, [(8.49, 4.35), (8.49, 32.70), (10.29, 32.70), (10.29, 4.35)],
                        self.metal1_layer)

        # Metal1 pin
        self._mkPolygon(shapes, [(0.0, 0.0), (0.0, 1.35), (14.32, 1.35), (14.32, 0.0)],
                        self.metal1_pin)

        # Metal2 polygons
        self._mkPolygon(shapes, [
            (1.955, 3.715), (1.955, 6.315), (11.86, 6.315), (11.86, 12.715),
            (1.955, 12.715), (1.955, 15.315), (11.86, 15.315), (11.86, 21.715),
            (1.955, 21.715), (1.955, 24.315), (11.86, 24.315), (11.86, 30.715),
            (1.955, 30.715), (1.955, 33.315), (15.505, 33.315), (15.505, 3.715)],
            self.metal2_layer)
        self._mkPolygon(shapes, [
            (-2.30, 7.735), (-2.30, 29.295), (10.015, 29.295), (10.015, 25.735),
            (1.295, 25.735), (1.295, 20.295), (10.015, 20.295), (10.015, 16.735),
            (1.295, 16.735), (1.295, 11.295), (10.015, 11.295), (10.015, 7.735)],
            self.metal2_layer)

        # Metal2 pins
        self._mkPolygon(shapes, [(-2.30, 7.735), (-2.30, 29.295), (1.295, 29.295), (1.295, 7.735)],
                        self.metal2_pin)
        self._mkPolygon(shapes, [(11.86, 3.715), (11.86, 33.315), (15.505, 33.315), (15.505, 3.715)],
                        self.metal2_pin)

    # ------------------------------------------------------------------
    # diodevss_4kv: VSS-side 4kV diode ESD clamp (14.32 x 37.05 um)
    # ------------------------------------------------------------------
    def _gen_diodevss_4kv(self, shapes, cont_size, cont_sep, via1_size, via1_sep):
        # Recognition layer
        self._mkRect(shapes, 0, 0, 14.32, 37.05, self.recog_esd_layer)

        # Labels
        self._mkLabel(shapes, -0.51, 18.442, 'PAD', self.text_layer)
        self._mkLabel(shapes, 13.64, 18.525, 'VSS', self.text_layer)
        self._mkLabel(shapes, 7.16, 36.375, 'VDD', self.text_layer)

        # Contact arrays (same positions as diodevdd_4kv)
        self._mkRectArray(shapes, 0.62, 0.61, 1, 37, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 0.62, 36.28, 1, 37, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 0.58, 1.105, 97, 1, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 13.54, 1.105, 97, 1, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 4.44, 4.81, 77, 3, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 8.97, 4.81, 77, 3, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 2.165, 3.405, 85, 3, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 6.725, 3.405, 85, 3, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 11.285, 3.405, 85, 3, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 2.235, 2.19, 3, 28, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 2.235, 34.02, 3, 28, cont_size, cont_sep, self.cont_layer)

        # Via1 arrays
        for xoff in [2.01, 6.57, 11.13]:
            for yoff in [3.73, 12.73, 21.73, 30.73]:
                self._mkRectArray(shapes, xoff, yoff, 6, 3, via1_size, via1_sep,
                                  self.via1_layer)
        for xoff in [4.285, 8.815]:
            for yoff in [7.665, 16.665, 25.665]:
                self._mkRectArray(shapes, xoff, yoff, 8, 3, via1_size, via1_sep,
                                  self.via1_layer)

        # Activ polygons
        self._mkPolygon(shapes, [(4.23, 4.65), (4.23, 32.43), (5.49, 32.43), (5.49, 4.65)],
                        self.activ_layer)
        self._mkPolygon(shapes, [(8.76, 4.65), (8.76, 32.43), (10.02, 32.43), (10.02, 4.65)],
                        self.activ_layer)
        self._mkPolygon(shapes, [
            (1.98, 1.98), (1.98, 3.24), (11.05, 3.24), (11.05, 33.81),
            (7.77, 33.81), (7.77, 3.24), (6.51, 3.24), (6.51, 33.81),
            (3.24, 33.81), (3.24, 3.24), (1.98, 3.24), (1.98, 35.07),
            (12.31, 35.07), (12.31, 1.98)], self.activ_layer)
        self._mkPolygon(shapes, [
            (0.42, 0.45), (0.42, 0.93), (13.42, 0.93), (13.42, 36.12),
            (0.90, 36.12), (0.90, 0.93), (0.42, 0.93), (0.42, 36.60),
            (13.90, 36.60), (13.90, 0.45)], self.activ_layer)

        # pSD (VSS variant: inner well + outer pSD ring swapped)
        self._mkPolygon(shapes, [
            (1.56, 1.56), (1.56, 3.66), (10.63, 3.66), (10.63, 33.39),
            (8.19, 33.39), (8.19, 3.66), (6.09, 3.66), (6.09, 33.39),
            (3.66, 33.39), (3.66, 3.66), (1.56, 3.66), (1.56, 35.49),
            (12.73, 35.49), (12.73, 1.56)], self.psd_layer)

        # NWell (outer ring for VSS)
        self._mkPolygon(shapes, [
            (0.0, 0.0), (0.0, 1.35), (13.0, 1.35), (13.0, 35.70),
            (1.35, 35.70), (1.35, 1.35), (0.0, 1.35), (0.0, 37.05),
            (14.32, 37.05), (14.32, 0.0)], self.nwell_layer)

        # Metal1
        self._mkPolygon(shapes, [
            (1.83, 1.89), (1.83, 3.30), (10.90, 3.30), (10.90, 33.75),
            (7.92, 33.75), (7.92, 3.30), (6.36, 3.30), (6.36, 33.75),
            (3.36, 33.75), (3.36, 3.30), (1.83, 3.30), (1.83, 35.16),
            (12.46, 35.16), (12.46, 1.89)], self.metal1_layer)
        self._mkPolygon(shapes, [
            (0.0, 0.0), (0.0, 1.35), (13.0, 1.35), (13.0, 35.70),
            (1.35, 35.70), (1.35, 1.35), (0.0, 1.35), (0.0, 37.05),
            (14.32, 37.05), (14.32, 0.0)], self.metal1_layer)
        self._mkPolygon(shapes, [(4.11, 4.35), (4.11, 32.70), (5.64, 32.70), (5.64, 4.35)],
                        self.metal1_layer)
        self._mkPolygon(shapes, [(8.64, 4.35), (8.64, 32.70), (10.17, 32.70), (10.17, 4.35)],
                        self.metal1_layer)

        # Metal1 pin (top strip for VSS)
        self._mkPolygon(shapes, [(0.0, 35.70), (0.0, 37.05), (14.32, 37.05), (14.32, 35.70)],
                        self.metal1_pin)

        # Metal2 polygons
        self._mkPolygon(shapes, [
            (1.96, 3.725), (1.96, 6.325), (11.82, 6.325), (11.82, 12.725),
            (1.96, 12.725), (1.96, 15.325), (11.82, 15.325), (11.82, 21.725),
            (1.96, 21.725), (1.96, 24.325), (11.82, 24.325), (11.82, 30.725),
            (1.96, 30.725), (1.96, 33.325), (15.46, 33.325), (15.46, 3.725)],
            self.metal2_layer)
        self._mkPolygon(shapes, [
            (-2.31, 7.66), (-2.31, 29.22), (10.015, 29.22), (10.015, 25.66),
            (1.295, 25.66), (1.295, 20.22), (10.015, 20.22), (10.015, 16.66),
            (1.295, 16.66), (1.295, 11.22), (10.015, 11.22), (10.015, 7.66)],
            self.metal2_layer)

        # Metal2 pins
        self._mkPolygon(shapes, [(-2.31, 7.66), (-2.31, 29.22), (1.295, 29.22), (1.295, 7.66)],
                        self.metal2_pin)
        self._mkPolygon(shapes, [(11.82, 3.72), (11.82, 33.33), (15.46, 33.33), (15.46, 3.72)],
                        self.metal2_pin)

    # ------------------------------------------------------------------
    # nmoscl_2: 2-finger NMOS clamp (placeholder - large fixed geometry)
    # ------------------------------------------------------------------
    def _gen_nmoscl_2(self, shapes, cont_size, cont_sep, via1_size, via1_sep):
        # Recognition layers
        self._mkRect(shapes, -2.25, -1.95, 34.96, 19.62, self.recog_esd_layer)
        self._mkRect(shapes, -2.25, -1.95, 34.96, 19.62, self.recog_layer)

        # Labels
        self._mkLabel(shapes, 1.811, -1.245, 'VSS', self.text_layer)
        self._mkLabel(shapes, 1.592, 19.26, 'VDD', self.text_layer)
        self._mkLabel(shapes, 20.45, 10.01, 'nmoscl_2', self.text_layer)

        # Contact arrays
        self._mkRectArray(shapes, -0.71, -1.315, 1, 91, cont_size, 0.22, self.cont_layer)
        self._mkRectArray(shapes, 0.47, 16.945, 1, 89, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, -0.71, 18.785, 1, 91, cont_size, 0.22, self.cont_layer)
        self._mkRectArray(shapes, -1.59, -1.35, 57, 1, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 34.17, -1.35, 57, 1, cont_size, cont_sep, self.cont_layer)

        # Via1 arrays
        self._mkRectArray(shapes, -1.175, -1.325, 1, 73, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, -1.175, 18.775, 1, 73, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, -1.605, -1.045, 42, 1, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 34.155, -1.045, 42, 1, via1_size, via1_sep, self.via1_layer)

        # Repeated gate/source/drain contacts (13 fingers)
        for i in range(13):
            x_base = 0.065 + i * 2.66
            self._mkRectArray(shapes, x_base, 1.28, 39, 1, cont_size, cont_sep, self.cont_layer)
            self._mkRectArray(shapes, x_base + 0.36, 1.28, 39, 1, cont_size, cont_sep,
                              self.cont_layer)
            self._mkRectArray(shapes, x_base - 0.085, 1.125, 30, 2, via1_size, via1_sep,
                              self.via1_layer)
            self._mkRectArray(shapes, x_base - 0.085, 1.125, 30, 2, via1_size, via1_sep,
                              self.via2_layer)

        # Activ polygons
        self._mkPolygon(shapes, [
            (-1.83, -1.53), (-1.83, -0.90), (33.91, -0.90), (33.91, 18.57),
            (-1.20, 18.57), (-1.20, -0.90), (-1.83, -0.90), (-1.83, 19.20),
            (34.54, 19.20), (34.54, -1.53)], self.activ_layer)
        self._mkPolygon(shapes, [
            (0.0, 1.20), (0.0, 15.21), (32.57, 15.21), (32.57, 1.20)],
            self.activ_layer)
        self._mkPolygon(shapes, [(0.0, 16.71), (0.0, 17.34), (32.71, 17.34), (32.71, 16.71)],
                        self.activ_layer)

        # pSD
        self._mkPolygon(shapes, [(-0.33, 16.35), (-0.33, 17.67), (33.04, 17.67), (33.04, 16.35)],
                        self.psd_layer)

        # ThickGateOx
        self._mkPolygon(shapes, [(-0.515, 0.86), (-0.515, 15.845), (33.095, 15.845), (33.095, 0.86)],
                        self.thickgateox_layer)

        # NWell (outer ring)
        self._mkPolygon(shapes, [
            (-2.25, -1.95), (-2.25, -0.54), (33.58, -0.54), (33.58, 18.21),
            (-0.87, 18.21), (-0.87, -0.54), (-2.25, -0.54), (-2.25, 19.62),
            (34.96, 19.62), (34.96, -1.95)], self.nwell_layer)

        # Metal1 outer ring
        self._mkPolygon(shapes, [
            (-2.25, -1.95), (-2.25, -0.54), (33.58, -0.54), (33.58, 17.88),
            (-0.87, 17.88), (-0.87, -0.54), (-2.25, -0.54), (-2.25, 19.29),
            (34.96, 19.29), (34.96, -1.95)], self.metal1_layer)

    # ------------------------------------------------------------------
    # nmoscl_4: 4-finger NMOS clamp (placeholder - large fixed geometry)
    # ------------------------------------------------------------------
    def _gen_nmoscl_4(self, shapes, cont_size, cont_sep, via1_size, via1_sep):
        # This is the wider variant of nmoscl_2 with double the finger count.
        # Recognition layers
        self._mkRect(shapes, -2.25, -1.95, 67.66, 19.62, self.recog_esd_layer)
        self._mkRect(shapes, -2.25, -1.95, 67.66, 19.62, self.recog_layer)

        # Labels
        self._mkLabel(shapes, 1.811, -1.245, 'VSS', self.text_layer)
        self._mkLabel(shapes, 1.592, 19.26, 'VDD', self.text_layer)
        self._mkLabel(shapes, 33.0, 10.01, 'nmoscl_4', self.text_layer)

        # Contact arrays (doubled width)
        self._mkRectArray(shapes, -0.71, -1.315, 1, 182, cont_size, 0.22, self.cont_layer)
        self._mkRectArray(shapes, 0.47, 16.945, 1, 178, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, -0.71, 18.785, 1, 182, cont_size, 0.22, self.cont_layer)
        self._mkRectArray(shapes, -1.59, -1.35, 57, 1, cont_size, cont_sep, self.cont_layer)
        self._mkRectArray(shapes, 66.87, -1.35, 57, 1, cont_size, cont_sep, self.cont_layer)

        # Via1 arrays
        self._mkRectArray(shapes, -1.175, -1.325, 1, 140, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, -1.175, 18.775, 1, 140, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, -1.605, -1.045, 42, 1, via1_size, via1_sep, self.via1_layer)
        self._mkRectArray(shapes, 66.855, -1.045, 42, 1, via1_size, via1_sep, self.via1_layer)

        # Repeated gate/source/drain contacts (26 fingers)
        for i in range(26):
            x_base = 0.065 + i * 2.66
            self._mkRectArray(shapes, x_base, 1.28, 39, 1, cont_size, cont_sep, self.cont_layer)
            self._mkRectArray(shapes, x_base + 0.36, 1.28, 39, 1, cont_size, cont_sep,
                              self.cont_layer)
            self._mkRectArray(shapes, x_base - 0.085, 1.125, 30, 2, via1_size, via1_sep,
                              self.via1_layer)
            self._mkRectArray(shapes, x_base - 0.085, 1.125, 30, 2, via1_size, via1_sep,
                              self.via2_layer)

        # Activ polygons (scaled for 4-finger)
        self._mkPolygon(shapes, [
            (-1.83, -1.53), (-1.83, -0.90), (66.61, -0.90), (66.61, 18.57),
            (-1.20, 18.57), (-1.20, -0.90), (-1.83, -0.90), (-1.83, 19.20),
            (67.24, 19.20), (67.24, -1.53)], self.activ_layer)
        self._mkPolygon(shapes, [
            (0.0, 1.20), (0.0, 15.21), (65.27, 15.21), (65.27, 1.20)],
            self.activ_layer)
        self._mkPolygon(shapes, [(0.0, 16.71), (0.0, 17.34), (65.41, 17.34), (65.41, 16.71)],
                        self.activ_layer)

        # pSD
        self._mkPolygon(shapes, [(-0.33, 16.35), (-0.33, 17.67), (65.74, 17.67), (65.74, 16.35)],
                        self.psd_layer)

        # ThickGateOx
        self._mkPolygon(shapes, [(-0.515, 0.86), (-0.515, 15.845), (65.795, 15.845), (65.795, 0.86)],
                        self.thickgateox_layer)

        # NWell
        self._mkPolygon(shapes, [
            (-2.25, -1.95), (-2.25, -0.54), (66.28, -0.54), (66.28, 18.21),
            (-0.87, 18.21), (-0.87, -0.54), (-2.25, -0.54), (-2.25, 19.62),
            (67.66, 19.62), (67.66, -1.95)], self.nwell_layer)

        # Metal1 outer ring
        self._mkPolygon(shapes, [
            (-2.25, -1.95), (-2.25, -0.54), (66.28, -0.54), (66.28, 17.88),
            (-0.87, 17.88), (-0.87, -0.54), (-2.25, -0.54), (-2.25, 19.29),
            (67.66, 19.29), (67.66, -1.95)], self.metal1_layer)


class diodevdd_2kv(esd):
    def __init__(self, model: str = "diodevdd_2kv"):
        super().__init__(model="diodevdd_2kv")


class diodevss_2kv(esd):
    def __init__(self, model: str = "diodevss_2kv"):
        super().__init__(model="diodevss_2kv")


class diodevdd_4kv(esd):
    def __init__(self, model: str = "diodevdd_4kv"):
        super().__init__(model="diodevdd_4kv")


class diodevss_4kv(esd):
    def __init__(self, model: str = "diodevss_4kv"):
        super().__init__(model="diodevss_4kv")


class nmoscl_2(esd):
    def __init__(self, model: str = "nmoscl_2"):
        super().__init__(model="nmoscl_2")


class nmoscl_4(esd):
    def __init__(self, model: str = "nmoscl_4"):
        super().__init__(model="nmoscl_4")
