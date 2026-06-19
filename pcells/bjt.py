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
BJT (Bipolar Junction Transistor) parametric cells for IHP SG13G2 PDK.

Includes NPN variants (npn13G2, npn13G2V, npn13G2L) and PNP variant (pnpMPA).
Faithful port of the original KLayout pcell geometry.
"""

import math
from functools import lru_cache
from PySide6.QtCore import QPoint, QPointF, QRectF
from quantiphy import Quantity

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule
from .base import baseCell

laylyr = importPDKModule('layoutLayers')


class npn13G2(baseCell):
    """
    Standard NPN BJT (npn13G2) for IHP SG13G2.

    Faithful port of the original KLayout pcell geometry.
    Uses hard-coded coordinate offsets matching the original design.

    Parameters:
        Nx: Number of emitter fingers (1-10)
        le: Emitter length (default "0.9u")
        we: Emitter width (default "0.07u")
    """

    # Layer definitions
    via1layer = laylyr.Via1_drawing
    metal1layer = laylyr.Metal1_drawing
    metal1layer_pin = laylyr.Metal1_pin
    metal2layer = laylyr.Metal2_drawing
    metal2layer_pin = laylyr.Metal2_pin
    contactlayer = laylyr.Cont_drawing
    emwindlayer = laylyr.EmWind_drawing
    activlayer = laylyr.Activ_drawing
    activmasklayer = laylyr.Activ_mask
    nsdlayer = laylyr.nSD_block
    psdlayer = laylyr.pSD_drawing
    translayer = laylyr.TRANS_drawing
    textlayer = laylyr.TEXT_drawing
    heatlayer = laylyr.HeatTrans_drawing

    # Device constants
    stepX = 1.85
    nx_max = 10

    def __init__(self, Nx: str = "1", le: str = "0.9u", we: str = "0.07u"):
        self.Nx = Nx
        self.le = le
        self.we = we
        super().__init__([])

    @lru_cache
    def __call__(self, Nx: str, le: str, we: str):
        """Generate npn13G2 layout matching original KLayout geometry."""
        Nx_int = int(float(Nx))
        # Original swaps le and we
        le_um = Quantity(we).real * 1e6  # le = original we
        we_um = Quantity(le).real * 1e6  # we = original le

        if Nx_int < 1:
            Nx_int = 1
        if Nx_int > self.nx_max:
            Nx_int = self.nx_max

        stepX = self.stepX
        stretchX = stepX * (Nx_int - 1)

        # Offsets (from original, with default params)
        bipwinyoffset = 0.0  # (2*(bipwiny - 0.1) - 0)/2, bipwiny=0.1 default
        empolyyoffset = 0.0  # (2*(empolyy - 0.18))/2, empolyy=0.18 default
        empolyxoffset = 0.0  # (2*(empolyx - 0.15))/2, empolyx=0.15 default
        baspolyxoffset = 0.0  # (2*(baspolyx - 0.3))/2, baspolyx=0.3 default
        STIoffset = 0.0  # (2*(STI - 0.44))/2, STI=0.44 default
        leoffset = 0.0
        nSDBlockShift = 0.43 - le_um

        # CMetY values depend on Nx
        if Nx_int > 1:
            CMetY1 = 1.01 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset
            CMetY2 = 0.57 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset
        else:
            CMetY1 = 0.8 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset
            CMetY2 = 0.56 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset

        tempShapes = []

        # === Per-finger geometry ===
        pcRepeatY = 4
        pcStepY = 0.41
        yOffset = 0.20

        for pcIndexX in range(Nx_int):
            cx = stepX * pcIndexX  # finger center x

            # --- Via1 array (4 rows, 2 vias per row: left + right) ---
            for pcIndexY in range(pcRepeatY):
                # Left via
                vx1 = cx - 0.3
                vy1 = -((-0.3 - yOffset - leoffset - bipwinyoffset - empolyyoffset) + (pcIndexY * pcStepY)) + 0.2
                vx2 = cx - 0.11
                vy2 = -((-0.11 - yOffset - leoffset - bipwinyoffset - empolyyoffset) + (pcIndexY * pcStepY)) + 0.2
                tempShapes.append(self._rect(vx1, vy1, vx2, vy2, self.via1layer))

                # Right via
                vx1 = cx + 0.11
                vx2 = cx + 0.3
                tempShapes.append(self._rect(vx1, vy1, vx2, vy2, self.via1layer))

            # --- Emitter Metal1 ---
            em_y1 = -(-0.32 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset)
            em_y2 = -(0.335 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset)
            tempShapes.append(self._rect(cx - 0.35, em_y1, cx + 0.35, em_y2, self.metal1layer))

            # --- Cont (base contacts) ---
            # Top contacts
            ct_x1 = cx - 0.79 - le_um / 2
            ct_y1 = -(-0.76 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset)
            ct_x2 = cx + 0.79 + le_um / 2
            ct_y2 = -(-0.6 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset)
            tempShapes.append(self._rect(ct_x1, ct_y1, ct_x2, ct_y2, self.contactlayer))

            # Bottom contacts
            cb_x1 = cx - 0.76
            cb_y1 = -(0.77 + we_um / 2 - leoffset - bipwinyoffset - empolyyoffset)
            cb_x2 = cx + 0.76
            cb_y2 = -(0.61 + we_um / 2 - leoffset - bipwinyoffset - empolyyoffset)
            tempShapes.append(self._rect(cb_x1, cb_y1, cb_x2, cb_y2, self.contactlayer))

            # --- EmWind (emitter window) ---
            ew_x1 = cx - le_um / 2
            ew_y1 = -(-we_um / 2 - leoffset)
            ew_x2 = cx + le_um / 2
            ew_y2 = -(we_um / 2 + leoffset)
            tempShapes.append(self._rect(ew_x1, ew_y1, ew_x2, ew_y2, self.emwindlayer))

            # --- HeatTrans layer ---
            ht_x1 = ew_x1 - 0.05
            ht_y1 = (-we_um / 2 - leoffset) - 0.05
            ht_x2 = ew_x2 + 0.05
            ht_y2 = (we_um / 2 + leoffset) + 0.05
            tempShapes.append(self._rect(ht_x1, ht_y1, ht_x2, ht_y2, self.heatlayer))

            # --- Activ/mask polygon (8-point) ---
            xl = cx - 0.06
            xh = xl + 0.12
            yl = -0.24 - leoffset
            yh = -yl
            activ_mask_pts = [
                (xh + 0.865, -yl + 0.74),
                (xl - 0.865, -yl + 0.74),
                (xl - 0.865, -yh - 0.38),
                (xl - 0.385, -yh - 0.38),
                (xl - 0.175, -yh - 0.59),
                (xh + 0.175, -yh - 0.59),
                (xh + 0.385, -yh - 0.38),
                (xh + 0.865, -yh - 0.38),
            ]
            tempShapes.append(self._polygon(activ_mask_pts, self.activmasklayer))

            # --- Activ/drawing rectangle (collector ring piece) ---
            ar_x1 = cx - 0.89 - le_um / 2 - empolyxoffset - baspolyxoffset - STIoffset
            ar_y1 = -(-0.83 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset)
            ar_x2 = cx + 0.89 + le_um / 2 + empolyxoffset + baspolyxoffset + STIoffset
            ar_y2 = -(-0.89 - we_um / 2 + 0.36 - leoffset - bipwinyoffset - empolyyoffset)
            tempShapes.append(self._rect(ar_x1, ar_y1, ar_x2, ar_y2, self.activlayer))

            # --- nSD/block polygon (10-point) ---
            sx = cx
            nsd_pts = [
                (sx + 0.94 + le_um / 2 + empolyxoffset + baspolyxoffset + STIoffset,
                 -(1.98 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset)),
                (sx + 0.94 + le_um / 2 + empolyxoffset + baspolyxoffset + STIoffset,
                 -(0.45 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset)),
                (sx + 0.52 + le_um / 2 + empolyxoffset + baspolyxoffset + STIoffset,
                 -(0.03 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset)),
                (sx + 0.52 + le_um / 2 + empolyxoffset + baspolyxoffset + STIoffset,
                 -(-0.6 - we_um / 2 + leoffset + bipwinyoffset + empolyyoffset + nSDBlockShift)),
                (sx + 0.27 + le_um / 2 + empolyxoffset + baspolyxoffset + STIoffset,
                 -(-0.85 - we_um / 2 + leoffset + bipwinyoffset + empolyyoffset + nSDBlockShift)),
                (sx - 0.27 - le_um / 2 - empolyxoffset - baspolyxoffset - STIoffset,
                 -(-0.85 - we_um / 2 + leoffset + bipwinyoffset + empolyyoffset + nSDBlockShift)),
                (sx - 0.52 - le_um / 2 - empolyxoffset - baspolyxoffset - STIoffset,
                 -(-0.6 - we_um / 2 + leoffset + bipwinyoffset + empolyyoffset + nSDBlockShift)),
                (sx - 0.52 - le_um / 2 - empolyxoffset - baspolyxoffset - STIoffset,
                 -(0.03 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset)),
                (sx - 0.94 - le_um / 2 - empolyxoffset - baspolyxoffset - STIoffset,
                 -(0.45 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset)),
                (sx - 0.94 - le_um / 2 - empolyxoffset - baspolyxoffset - STIoffset,
                 -(1.98 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset)),
            ]
            tempShapes.append(self._polygon(nsd_pts, self.nsdlayer))

        # === Shared geometry (spans all fingers) ===

        # --- Collector Metal1 ---
        tempShapes.append(self._rect(
            -0.89 - le_um / 2, CMetY1,
            stretchX + 0.89 + le_um / 2, CMetY2,
            self.metal1layer))

        # --- Base Metal1 ---
        bm_y1 = -(0.57 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset)
        bm_y2 = -(0.81 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset)
        tempShapes.append(self._rect(
            -0.94 - le_um / 2, bm_y1,
            stretchX + 0.94 + le_um / 2, bm_y2,
            self.metal1layer))

        # --- Emitter Metal2 bus ---
        em2_y1 = -(-0.32 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset)
        em2_y2 = -(0.335 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset)
        tempShapes.append(self._rect(
            -0.89 - le_um / 2, em2_y1,
            stretchX + 0.89 + le_um / 2, em2_y2,
            self.metal2layer))

        # --- TRANS polygon ---
        trans_pts = [
            (stretchX + 2.45, 2.43 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset),
            (-2.45, 2.43 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset),
            (-2.45, -1.98 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset),
            (stretchX + 2.45, -1.98 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset),
        ]
        tempShapes.append(self._polygon(trans_pts, self.translayer))

        # --- pSD polygon (ring-like, 10-point) ---
        psd_pts = [
            (stretchX + 3.35, 3.33 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset),
            (stretchX + 2.45, 3.33 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset),
            (stretchX + 2.45, -1.98 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset),
            (-2.45, -1.98 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset),
            (-2.45, 2.43 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset),
            (stretchX + 2.45, 2.43 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset),
            (stretchX + 2.45, 3.33 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset),
            (-3.35, 3.33 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset),
            (-3.35, -2.88 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset),
            (stretchX + 3.35, -2.88 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset),
        ]
        tempShapes.append(self._polygon(psd_pts, self.psdlayer))

        # --- Activ polygon (ring-like, 10-point) ---
        activ_pts = [
            (stretchX + 3.15, 3.13 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset),
            (stretchX + 2.65, 3.13 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset),
            (stretchX + 2.65, -2.18 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset),
            (-2.65, -2.18 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset),
            (-2.65, 2.63 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset),
            (stretchX + 2.65, 2.63 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset),
            (stretchX + 2.65, 3.13 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset),
            (-3.15, 3.13 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset),
            (-3.15, -2.68 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset),
            (stretchX + 3.15, -2.68 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset),
        ]
        tempShapes.append(self._polygon(activ_pts, self.activlayer))

        # === Pins ===
        # Collector pin (Metal1)
        if Nx_int > 1:
            c_y1 = 0.57 + we_um / 2 - leoffset - bipwinyoffset - empolyyoffset
            c_y2 = 1.01 + we_um / 2 - leoffset - bipwinyoffset - empolyyoffset
        else:
            c_y1 = 0.56 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset
            c_y2 = 0.8 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset
        c_x1 = -0.89 - le_um / 2
        c_x2 = stretchX + 0.89 + le_um / 2
        cp1 = self.toSceneCoord(QPointF(c_x1, c_y1))
        cp2 = self.toSceneCoord(QPointF(c_x2, c_y2))
        tempShapes.append(lshp.layoutPin(
            cp1, cp2, "C", lshp.layoutPin.pinDirs[2],
            lshp.layoutPin.pinTypes[0], self.metal1layer_pin))
        tempShapes.append(lshp.layoutLabel(
            QRectF(cp1, cp2).center(), "C",
            *self._labelFontTuple,
            lshp.layoutLabel.LABEL_ALIGNMENTS[0],
            lshp.layoutLabel.LABEL_ORIENTS[0], self.textlayer))

        # Base pin (Metal1)
        b_x1 = -0.94 - le_um / 2
        b_y1 = -0.81 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset
        b_x2 = stretchX + 0.94 + le_um / 2
        b_y2 = -0.57 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset
        bp1 = self.toSceneCoord(QPointF(b_x1, b_y1))
        bp2 = self.toSceneCoord(QPointF(b_x2, b_y2))
        tempShapes.append(lshp.layoutPin(
            bp1, bp2, "B", lshp.layoutPin.pinDirs[2],
            lshp.layoutPin.pinTypes[0], self.metal1layer_pin))
        tempShapes.append(lshp.layoutLabel(
            QRectF(bp1, bp2).center(), "B",
            *self._labelFontTuple,
            lshp.layoutLabel.LABEL_ALIGNMENTS[0],
            lshp.layoutLabel.LABEL_ORIENTS[0], self.textlayer))

        # Emitter pin (Metal2)
        e_x1 = -0.71 - le_um / 2
        e_y1 = 0.32 + we_um / 2 + leoffset + bipwinyoffset + empolyyoffset
        e_x2 = stretchX + 0.71 + le_um / 2
        e_y2 = -0.335 - we_um / 2 - leoffset - bipwinyoffset - empolyyoffset
        ep1 = self.toSceneCoord(QPointF(e_x1, e_y1))
        ep2 = self.toSceneCoord(QPointF(e_x2, e_y2))
        tempShapes.append(lshp.layoutPin(
            ep1, ep2, "E", lshp.layoutPin.pinDirs[2],
            lshp.layoutPin.pinTypes[0], self.metal2layer_pin))
        tempShapes.append(lshp.layoutLabel(
            QRectF(ep1, ep2).center(), "E",
            *self._labelFontTuple,
            lshp.layoutLabel.LABEL_ALIGNMENTS[0],
            lshp.layoutLabel.LABEL_ORIENTS[0], self.textlayer))

        self.shapes = tempShapes

    # --- Helper methods ---

    def _rect(self, x1, y1, x2, y2, layer):
        """Create a layoutRect from layout coordinates."""
        p1 = self.toSceneCoord(QPointF(x1, y1))
        p2 = self.toSceneCoord(QPointF(x2, y2))
        return lshp.layoutRect(p1, p2, layer)

    def _polygon(self, points_list, layer):
        """Create a layoutPolygon from a list of (x,y) tuples in layout coords."""
        scene_points = [self.toSceneCoord(QPointF(x, y)) for x, y in points_list]
        return lshp.layoutPolygon(scene_points, layer)


class npn13G2V(baseCell):
    """
    High-voltage NPN variant (npn13G2V).

    Has wider emitter (0.12 µm) and different geometry structure
    compared to npn13G2. This is a distinct device, not a simple
    parameter override.

    Parameters:
        Nx: Number of emitter fingers (1-8)
        le: Emitter length (default "1.0u")
        we: Emitter width (default "0.12u")
    """

    # Same layers as npn13G2
    via1layer = laylyr.Via1_drawing
    metal1layer = laylyr.Metal1_drawing
    metal1layer_pin = laylyr.Metal1_pin
    metal2layer = laylyr.Metal2_drawing
    metal2layer_pin = laylyr.Metal2_pin
    contactlayer = laylyr.Cont_drawing
    emwindlayer = laylyr.EmWiHV_drawing
    activlayer = laylyr.Activ_drawing
    activmasklayer = laylyr.Activ_mask
    nsdlayer = laylyr.nSD_block
    psdlayer = laylyr.pSD_drawing
    translayer = laylyr.TRANS_drawing
    textlayer = laylyr.TEXT_drawing
    heatlayer = laylyr.HeatTrans_drawing

    nx_max = 8

    def __init__(self, Nx: str = "1", le: str = "1.0u", we: str = "0.12u"):
        self.Nx = Nx
        self.le = le
        self.we = we
        super().__init__([])

    @lru_cache
    def __call__(self, Nx: str, le: str, we: str):
        """
        Generate npn13G2V layout.

        Args:
            Nx: Number of emitter fingers (1-8)
            le: Emitter length (e.g., "1.0u")
            we: Emitter width (e.g., "0.12u")
        """
        Nx_int = int(float(Nx))
        le_um = Quantity(le).real * 1e6
        we_um = Quantity(we).real * 1e6

        if Nx_int < 1:
            Nx_int = 1
        if Nx_int > self.nx_max:
            Nx_int = self.nx_max

        emWindOrigin_x = 3.81
        emWindOrigin_y = 3.1
        Col_Metal1_distance = 0.79
        Col_Metal1_width = 0.32
        Bas_Metal1_distance = 0.295
        Bas_Metal1_width = 0.17
        Emi_Metal1_enc_vert = 0.28
        Emi_Metal1_enc_hori = 0.07

        tempShapes = []

        for cnt in range(Nx_int):
            dx = cnt * 2.34
            cx = emWindOrigin_x + dx

            tempShapes.append(self._rect(cx, emWindOrigin_y, cx + we_um, emWindOrigin_y + le_um, self.emwindlayer))

            tempShapes.append(self._rect(cx - 0.05, emWindOrigin_y - 0.05, cx + we_um + 0.05, emWindOrigin_y + le_um + 0.05, self.heatlayer))

            tempShapes.append(self._rect(cx - 1.11, emWindOrigin_y - 0.28, cx - 0.705, emWindOrigin_y + le_um + 0.28, self.activlayer))
            tempShapes.append(self._rect(cx - 0.07, emWindOrigin_y - 0.28, cx + we_um + 0.07, emWindOrigin_y + le_um + 0.28, self.activlayer))
            tempShapes.append(self._rect(cx + we_um + 0.705, emWindOrigin_y - 0.28, cx + we_um + 1.11, emWindOrigin_y + le_um + 0.28, self.activlayer))

            tempShapes.append(self._rect(cx - 0.705, emWindOrigin_y - 0.28, cx - 0.07, emWindOrigin_y + le_um + 0.28, self.activmasklayer))
            tempShapes.append(self._rect(cx + we_um + 0.07, emWindOrigin_y - 0.28, cx + we_um + 0.705, emWindOrigin_y + le_um + 0.28, self.activmasklayer))

            via_cnt = int((le_um + 0.46) / (0.19 + 0.22))

            bbx_height = le_um + 2 * Emi_Metal1_enc_vert
            via_column = via_cnt * 0.19 + (via_cnt - 1) * 0.22 + (0.19 + 0.22) + 0.05 + 0.06
            if bbx_height < via_column:
                via_cnt -= 1

            for i in range(via_cnt + 1):
                tempShapes.append(self._rect(3.775 + dx, 2.87 + i * 0.41, 3.965 + dx, 3.06 + i * 0.41, self.via1layer))

            tempShapes.append(self._rect(3.79 + dx, 3.04, 3.95 + dx, 3.16 + le_um, self.contactlayer))

            cont_cnt = self.fix((le_um + 0.21) / (0.16 + 0.18))

            for i in range(cont_cnt + 1):
                tempShapes.append(self._rect(2.8 + dx, 2.89 + i * 0.34, 2.96 + dx, 3.05 + i * 0.34, self.contactlayer))
                tempShapes.append(self._rect(3.35 + dx, 2.89 + i * 0.34, 3.51 + dx, 3.05 + i * 0.34, self.contactlayer))
                tempShapes.append(self._rect(4.23 + dx, 2.89 + i * 0.34, 4.39 + dx, 3.05 + i * 0.34, self.contactlayer))
                tempShapes.append(self._rect(4.78 + dx, 2.89 + i * 0.34, 4.94 + dx, 3.05 + i * 0.34, self.contactlayer))

            tempShapes.append(self._rect(cx - Col_Metal1_distance - Col_Metal1_width, 2.82, cx - Col_Metal1_distance, 4.1 + le_um, self.metal1layer))
            tempShapes.append(self._rect(cx + we_um + Col_Metal1_distance, 2.82, cx + we_um + Col_Metal1_distance + Col_Metal1_width, 4.1 + le_um, self.metal1layer))
            tempShapes.append(self._rect(cx - Col_Metal1_distance - Col_Metal1_width, 4.1 + le_um, cx + we_um + Col_Metal1_distance + Col_Metal1_width, 4.1 + le_um + 0.65, self.metal1layer))

            tempShapes.append(self._rect(cx - Bas_Metal1_distance - Bas_Metal1_width, 2.1, cx - Bas_Metal1_distance, 3.38 + le_um, self.metal1layer))
            tempShapes.append(self._rect(cx + we_um + Bas_Metal1_distance, 2.1, cx + we_um + Bas_Metal1_distance + Bas_Metal1_width, 3.38 + le_um, self.metal1layer))
            tempShapes.append(self._rect(cx - Bas_Metal1_distance - Bas_Metal1_width, 1.45, cx + we_um + Bas_Metal1_distance + Bas_Metal1_width, 2.1, self.metal1layer))

            tempShapes.append(self._rect(cx - Emi_Metal1_enc_hori, emWindOrigin_y - Emi_Metal1_enc_vert, cx + we_um + Emi_Metal1_enc_hori, emWindOrigin_y + le_um + Emi_Metal1_enc_vert, self.metal1layer))

            tempShapes.append(self._rect(cx - Col_Metal1_distance - Col_Metal1_width, 2.82, cx + Col_Metal1_distance + Col_Metal1_width + we_um, 3.38 + le_um, self.metal2layer))

        if Nx_int > 1:
            for cnt in range(1, Nx_int):
                dx = cnt * 2.34
                tempShapes.append(self._rect(4.395 + (cnt - 1) * 2.34, 1.45, 5.685 + (cnt - 1) * 2.34, 2.1, self.metal1layer))

        tempShapes.append(self._rect(0.9, 0.9, 6.84 + (Nx_int - 1) * 2.34, 5.3 + le_um, self.translayer))

        tempShapes.append(self._ring_polygon(0.0, 0.0, 7.74 + (Nx_int - 1) * 2.34, 6.2 + le_um, 0.9, 0.9, 6.84 + (Nx_int - 1) * 2.34, 5.3 + le_um, self.psdlayer))

        tempShapes.append(self._ring_polygon(0.2, 0.2, 7.54 + (Nx_int - 1) * 2.34, 6.0 + le_um, 0.7, 0.7, 7.04 + (Nx_int - 1) * 2.34, 5.5 + le_um, self.activlayer))

        ae_text = f"Ae={Nx_int}*{le_um:.2f}*{we_um:.2f}"
        tempShapes.append(lshp.layoutLabel(
            self.toSceneCoord(QPointF(1.5, 1.0)), ae_text,
            *self._labelFontTuple,
            lshp.layoutLabel.LABEL_ALIGNMENTS[0],
            lshp.layoutLabel.LABEL_ORIENTS[1], self.textlayer))

        tempShapes.append(lshp.layoutLabel(
            self.toSceneCoord(QPointF(1.75, 1.0)), "npn13G2V",
            *self._labelFontTuple,
            lshp.layoutLabel.LABEL_ALIGNMENTS[0],
            lshp.layoutLabel.LABEL_ORIENTS[0], self.textlayer))

        cp1 = self.toSceneCoord(QPointF(emWindOrigin_x - Col_Metal1_distance - Col_Metal1_width, 4.1 + le_um))
        cp2 = self.toSceneCoord(QPointF(emWindOrigin_x + (Nx_int - 1) * 2.34 + we_um + Col_Metal1_distance + Col_Metal1_width, 4.1 + le_um + 0.65))
        tempShapes.append(lshp.layoutPin(cp1, cp2, "C", lshp.layoutPin.pinDirs[2], lshp.layoutPin.pinTypes[0], self.metal1layer_pin))
        tempShapes.append(lshp.layoutLabel(QRectF(cp1, cp2).center(), "C", *self._labelFontTuple, lshp.layoutLabel.LABEL_ALIGNMENTS[0], lshp.layoutLabel.LABEL_ORIENTS[0], self.textlayer))

        bp1 = self.toSceneCoord(QPointF(emWindOrigin_x - Bas_Metal1_distance - Bas_Metal1_width, 1.45))
        bp2 = self.toSceneCoord(QPointF(emWindOrigin_x + (Nx_int - 1) * 2.34 + we_um + Bas_Metal1_distance + Bas_Metal1_width, 2.1))
        tempShapes.append(lshp.layoutPin(bp1, bp2, "B", lshp.layoutPin.pinDirs[2], lshp.layoutPin.pinTypes[0], self.metal1layer_pin))
        tempShapes.append(lshp.layoutLabel(QRectF(bp1, bp2).center(), "B", *self._labelFontTuple, lshp.layoutLabel.LABEL_ALIGNMENTS[0], lshp.layoutLabel.LABEL_ORIENTS[0], self.textlayer))

        ep1 = self.toSceneCoord(QPointF(emWindOrigin_x - Col_Metal1_distance - Col_Metal1_width, 2.82))
        ep2 = self.toSceneCoord(QPointF(emWindOrigin_x + (Nx_int - 1) * 2.34 + we_um + Col_Metal1_distance + Col_Metal1_width, 3.38 + le_um))
        tempShapes.append(lshp.layoutPin(ep1, ep2, "E", lshp.layoutPin.pinDirs[2], lshp.layoutPin.pinTypes[0], self.metal2layer_pin))
        tempShapes.append(lshp.layoutLabel(QRectF(ep1, ep2).center(), "E", *self._labelFontTuple, lshp.layoutLabel.LABEL_ALIGNMENTS[0], lshp.layoutLabel.LABEL_ORIENTS[0], self.textlayer))

        self.shapes = tempShapes

    def _rect(self, x1, y1, x2, y2, layer):
        p1 = self.toSceneCoord(QPointF(x1, y1))
        p2 = self.toSceneCoord(QPointF(x2, y2))
        return lshp.layoutRect(p1, p2, layer)

    def _ring_polygon(self, ox1, oy1, ox2, oy2, ix1, iy1, ix2, iy2, layer):
        ring_pts = [
            (ox1, oy1),
            (ox2, oy1),
            (ox2, oy2),
            (ox1, oy2),
            (ix1, iy2),
            (ix2, iy2),
            (ix2, iy1),
            (ix1, iy1),
            (ix1, iy2),
            (ox1, oy2),
        ]
        scene_points = [self.toSceneCoord(QPointF(x, y)) for x, y in ring_pts]
        return lshp.layoutPolygon(scene_points, layer)


class npn13G2L(baseCell):
    """
    Low-noise NPN variant (npn13G2L).

    Has narrower emitter and different isolation structure.
    This is a distinct device with its own geometry.

    Parameters:
        Nx: Number of emitter fingers (1-4)
        le: Emitter length (default "0.9u")
        we: Emitter width (default "0.07u")
    """

    # Same layers as npn13G2
    via1layer = laylyr.Via1_drawing
    metal1layer = laylyr.Metal1_drawing
    metal1layer_pin = laylyr.Metal1_pin
    metal2layer = laylyr.Metal2_drawing
    metal2layer_pin = laylyr.Metal2_pin
    contactlayer = laylyr.Cont_drawing
    emwindlayer = laylyr.EmWind_drawing
    activlayer = laylyr.Activ_drawing
    activmasklayer = laylyr.Activ_mask
    nsdlayer = laylyr.nSD_block
    psdlayer = laylyr.pSD_drawing
    translayer = laylyr.TRANS_drawing
    textlayer = laylyr.TEXT_drawing
    heatlayer = laylyr.HeatTrans_drawing

    nx_max = 4

    def __init__(self, Nx: str = "1", le: str = "0.9u", we: str = "0.07u"):
        self.Nx = Nx
        self.le = le
        self.we = we
        super().__init__([])

    @lru_cache
    def __call__(self, Nx: str, le: str, we: str):
        """
        Generate npn13G2L layout.

        Args:
            Nx: Number of emitter fingers (1-4)
            le: Emitter length (e.g., "0.9u")
            we: Emitter width (e.g., "0.07u")
        """
        Nx_int = int(float(Nx))
        le_um = Quantity(le).real * 1e6
        we_um = Quantity(we).real * 1e6

        if Nx_int < 1:
            Nx_int = 1
        if Nx_int > self.nx_max:
            Nx_int = self.nx_max

        emWindOrigin_x = 3.865
        emWindOrigin_y = 3.1
        Col_Metal1_distance = 0.975
        Col_Metal1_width = 0.39
        Bas_Metal1_distance = 0.32
        Bas_Metal1_width = 0.16
        Emi_Metal1_enc_vert = 0.2
        Emi_Metal1_enc_hori = 0.095

        tempShapes = []

        for cnt in range(Nx_int):
            dx = cnt * 2.8
            cx = emWindOrigin_x + dx

            tempShapes.append(self._rect(cx, emWindOrigin_y, cx + we_um, emWindOrigin_y + le_um, self.emwindlayer))

            tempShapes.append(self._rect(cx - 0.05, emWindOrigin_y - 0.05, cx + we_um + 0.05, emWindOrigin_y + le_um + 0.05, self.heatlayer))

            tempShapes.append(self._rect(cx - 1.365, emWindOrigin_y - 0.28, cx - 0.705, emWindOrigin_y + le_um + 0.28, self.activlayer))
            tempShapes.append(self._rect(cx - 0.095, emWindOrigin_y - 0.28, cx + we_um + 0.095, emWindOrigin_y + le_um + 0.28, self.activlayer))
            tempShapes.append(self._rect(cx + we_um + 0.705, emWindOrigin_y - 0.28, cx + we_um + 1.365, emWindOrigin_y + le_um + 0.28, self.activlayer))

            tempShapes.append(self._rect(cx - 0.705, emWindOrigin_y - 0.28, cx - 0.095, emWindOrigin_y + le_um + 0.28, self.activmasklayer))
            tempShapes.append(self._rect(cx + we_um + 0.095, emWindOrigin_y - 0.28, cx + we_um + 0.705, emWindOrigin_y + le_um + 0.28, self.activmasklayer))

            tempShapes.append(self._rect(3.805 + dx, 3.0, 3.995 + dx, 3.2 + le_um, self.via1layer))

            tempShapes.append(self._rect(2.68 + dx, 2.95, 2.84 + dx, 3.25 + le_um, self.contactlayer))
            tempShapes.append(self._rect(3.82 + dx, 2.95, 3.98 + dx, 3.25 + le_um, self.contactlayer))
            tempShapes.append(self._rect(4.96 + dx, 2.95, 5.12 + dx, 3.25 + le_um, self.contactlayer))

            cont_cnt = self.fix((le_um + 0.21) / (0.16 + 0.18))

            for i in range(cont_cnt + 1):
                tempShapes.append(self._rect(3.385 + dx, 2.89 + i * 0.34, 3.545 + dx, 3.05 + i * 0.34, self.contactlayer))
                tempShapes.append(self._rect(4.255 + dx, 2.89 + i * 0.34, 4.415 + dx, 3.05 + i * 0.34, self.contactlayer))

            tempShapes.append(self._rect(cx - Col_Metal1_distance - Col_Metal1_width, 2.82, cx - Col_Metal1_distance, 4.1 + le_um, self.metal1layer))
            tempShapes.append(self._rect(cx + we_um + Col_Metal1_distance, 2.82, cx + we_um + Col_Metal1_distance + Col_Metal1_width, 4.1 + le_um, self.metal1layer))
            tempShapes.append(self._rect(cx - Col_Metal1_distance - Col_Metal1_width, 4.1 + le_um, cx + we_um + Col_Metal1_distance + Col_Metal1_width, 4.1 + le_um + 0.65, self.metal1layer))

            tempShapes.append(self._rect(cx - Bas_Metal1_distance - Bas_Metal1_width, 2.1, cx - Bas_Metal1_distance, 3.38 + le_um, self.metal1layer))
            tempShapes.append(self._rect(cx + we_um + Bas_Metal1_distance, 2.1, cx + we_um + Bas_Metal1_distance + Bas_Metal1_width, 3.38 + le_um, self.metal1layer))
            tempShapes.append(self._rect(cx - Bas_Metal1_distance - Bas_Metal1_width, 1.45, cx + we_um + Bas_Metal1_distance + Bas_Metal1_width, 2.1, self.metal1layer))

            tempShapes.append(self._rect(cx - Emi_Metal1_enc_hori, emWindOrigin_y - Emi_Metal1_enc_vert, cx + we_um + Emi_Metal1_enc_hori, emWindOrigin_y + le_um + Emi_Metal1_enc_vert, self.metal1layer))

            tempShapes.append(self._rect(cx - Col_Metal1_distance - Col_Metal1_width, 2.9, cx + Col_Metal1_distance + Col_Metal1_width + we_um, 3.3 + le_um, self.metal2layer))

        if Nx_int > 1:
            for cnt in range(1, Nx_int):
                dx = cnt * 2.8
                tempShapes.append(self._rect(4.415 + (cnt - 1) * 2.8, 1.45, 6.185 + (cnt - 1) * 2.8, 2.1, self.metal1layer))

        tempShapes.append(self._rect(0.9, 0.9, 6.9 + (Nx_int - 1) * 2.8, 5.3 + le_um, self.translayer))

        tempShapes.append(self._ring_polygon(0.0, 0.0, 7.8 + (Nx_int - 1) * 2.8, 6.2 + le_um, 0.9, 0.9, 6.9 + (Nx_int - 1) * 2.8, 5.3 + le_um, self.psdlayer))

        tempShapes.append(self._ring_polygon(0.2, 0.2, 7.6 + (Nx_int - 1) * 2.8, 6.0 + le_um, 0.7, 0.7, 7.1 + (Nx_int - 1) * 2.8, 5.5 + le_um, self.activlayer))

        ae_text = f"Ae={Nx_int}*1*{le_um:.2f}*{we_um:.2f}"
        tempShapes.append(lshp.layoutLabel(
            self.toSceneCoord(QPointF(1.5, 1.0)), ae_text,
            *self._labelFontTuple,
            lshp.layoutLabel.LABEL_ALIGNMENTS[0],
            lshp.layoutLabel.LABEL_ORIENTS[1], self.textlayer))

        tempShapes.append(lshp.layoutLabel(
            self.toSceneCoord(QPointF(1.75, 1.0)), "npn13G2L",
            *self._labelFontTuple,
            lshp.layoutLabel.LABEL_ALIGNMENTS[0],
            lshp.layoutLabel.LABEL_ORIENTS[0], self.textlayer))

        cp1 = self.toSceneCoord(QPointF(emWindOrigin_x - Col_Metal1_distance - Col_Metal1_width, 4.1 + le_um))
        cp2 = self.toSceneCoord(QPointF(emWindOrigin_x + (Nx_int - 1) * 2.8 + we_um + Col_Metal1_distance + Col_Metal1_width, 4.1 + le_um + 0.65))
        tempShapes.append(lshp.layoutPin(cp1, cp2, "C", lshp.layoutPin.pinDirs[2], lshp.layoutPin.pinTypes[0], self.metal1layer_pin))
        tempShapes.append(lshp.layoutLabel(QRectF(cp1, cp2).center(), "C", *self._labelFontTuple, lshp.layoutLabel.LABEL_ALIGNMENTS[0], lshp.layoutLabel.LABEL_ORIENTS[0], self.textlayer))

        bp1 = self.toSceneCoord(QPointF(emWindOrigin_x - Bas_Metal1_distance - Bas_Metal1_width, 1.45))
        bp2 = self.toSceneCoord(QPointF(emWindOrigin_x + (Nx_int - 1) * 2.8 + we_um + Bas_Metal1_distance + Bas_Metal1_width, 2.1))
        tempShapes.append(lshp.layoutPin(bp1, bp2, "B", lshp.layoutPin.pinDirs[2], lshp.layoutPin.pinTypes[0], self.metal1layer_pin))
        tempShapes.append(lshp.layoutLabel(QRectF(bp1, bp2).center(), "B", *self._labelFontTuple, lshp.layoutLabel.LABEL_ALIGNMENTS[0], lshp.layoutLabel.LABEL_ORIENTS[0], self.textlayer))

        ep1 = self.toSceneCoord(QPointF(emWindOrigin_x - Col_Metal1_distance - Col_Metal1_width, 2.9))
        ep2 = self.toSceneCoord(QPointF(emWindOrigin_x + (Nx_int - 1) * 2.8 + we_um + Col_Metal1_distance + Col_Metal1_width, 3.3 + le_um))
        tempShapes.append(lshp.layoutPin(ep1, ep2, "E", lshp.layoutPin.pinDirs[2], lshp.layoutPin.pinTypes[0], self.metal2layer_pin))
        tempShapes.append(lshp.layoutLabel(QRectF(ep1, ep2).center(), "E", *self._labelFontTuple, lshp.layoutLabel.LABEL_ALIGNMENTS[0], lshp.layoutLabel.LABEL_ORIENTS[0], self.textlayer))

        self.shapes = tempShapes

    def _rect(self, x1, y1, x2, y2, layer):
        p1 = self.toSceneCoord(QPointF(x1, y1))
        p2 = self.toSceneCoord(QPointF(x2, y2))
        return lshp.layoutRect(p1, p2, layer)

    def _ring_polygon(self, ox1, oy1, ox2, oy2, ix1, iy1, ix2, iy2, layer):
        ring_pts = [
            (ox1, oy1),
            (ox2, oy1),
            (ox2, oy2),
            (ox1, oy2),
            (ix1, iy2),
            (ix2, iy2),
            (ix2, iy1),
            (ix1, iy1),
            (ix1, iy2),
            (ox1, oy2),
        ]
        scene_points = [self.toSceneCoord(QPointF(x, y)) for x, y in ring_pts]
        return lshp.layoutPolygon(scene_points, layer)


class pnpMPA(baseCell):
    """
    Lateral PNP transistor (pnpMPA) for IHP SG13G2.

    Faithful port of the original KLayout pcell geometry.
    Concentric ring structure with central anode, collector ring,
    and substrate guard ring. XOR operations from the original are
    replaced with explicit ring polygons.

    Parameters:
        width: Device width (default "0.7u")
        length: Device length (default "2u")
    """

    # Layer definitions
    activlayer = laylyr.Activ_drawing
    psdlayer = laylyr.pSD_drawing
    nwelllayer = laylyr.NWell_drawing
    nbulaylayer = laylyr.nBuLay_drawing
    contactlayer = laylyr.Cont_drawing
    metal1layer = laylyr.Metal1_drawing
    metal1layer_pin = laylyr.Metal1_pin
    textlayer = laylyr.TEXT_drawing

    def __init__(self, width: str = "0.7u", length: str = "2u"):
        self.width = width
        self.length = length
        super().__init__([])

    @lru_cache
    def __call__(self, width: str, length: str):
        """
        Generate pnpMPA layout matching original KLayout geometry.

        The original uses XOR operations to create ring shapes.
        Here we draw them as explicit ring polygons (outer boundary
        with inner cutout traced as a single polygon path).

        Args:
            width: Device width (e.g., "0.7u")
            length: Device length (e.g., "2u")
        """
        w_um = Quantity(width).real * 1e6
        l_um = Quantity(length).real * 1e6

        tp = baseCell._techParams
        Cnt_a = tp["Cnt_a"]
        Cnt_b = tp["Cnt_b"]
        Cnt_b1 = tp["Cnt_b1"]
        M1_c1 = tp["M1_c1"]
        pSD_c = tp["pSD_c"]

        # Original uses GridFix(Numeric(l)*5e5) which is GridFix(l_um/2)
        # since Numeric(l) is in meters and *5e5 = *1e6/2
        hact = self.GridFix(l_um / 2)
        wact = self.GridFix(w_um / 2)

        # Derived dimensions (matching original exactly)
        w1m1 = wact - 0.02
        h1m1 = hact - 0.02
        wpsd = wact + 0.21
        hpsd = hact + 0.18
        w2act = wpsd + pSD_c
        h2act = hpsd + pSD_c
        dw2act = max(wact, 0.3)
        dh2act = 0.29
        w2m1 = w2act + 0.02
        h2m1 = h2act + 0.02
        dw2m1 = dw2act - 0.04
        dh2m1 = dh2act - 0.04
        wbulay = w2act + dw2act + 0.05
        hbulay = h2act + dh2act + 0.05
        wnwell = wbulay + 0.26
        hnwell = hbulay + 0.26
        w2psd = wnwell + 0.5
        h2psd = hnwell + 0.5
        d2psd = 0.75
        w3act = w2psd + 0.2
        h3act = h2psd + 0.2
        d3act = 0.35

        tempShapes = []

        # ==================================================
        # 1. Central Activ (PLUS anode)
        # ==================================================
        tempShapes.append(self._rect(-wact, -hact, wact, hact, self.activlayer))

        # ==================================================
        # 2. pSD around central region
        # ==================================================
        tempShapes.append(self._rect(-wpsd, -hpsd, wpsd, hpsd, self.psdlayer))

        # ==================================================
        # 3. Central contacts + Metal1 (PLUS)
        # ==================================================
        _ox = M1_c1
        _oy = M1_c1
        _ws = Cnt_a
        _ds = Cnt_b

        # Check large-array threshold
        vg4 = (Cnt_a + Cnt_b) * 4 + Cnt_a + _ox * 2
        if (w1m1 * 2) >= vg4 and (h1m1 * 2) >= vg4:
            _ds = Cnt_b1

        tempShapes.extend(
            self.contactArray(self.metal1layer, self.contactlayer,
                              -w1m1, -h1m1, w1m1, h1m1, _ox, _oy, _ws, _ds))

        # ==================================================
        # 4. Collector ring: Activ XOR → ring polygon
        #    Original: XOR of Box(-w2act,-h2act,w2act,h2act)
        #              and Box(-w2act-dw2act,-h2act-dh2act,w2act+dw2act,h2act+dh2act)
        # ==================================================
        tempShapes.append(self._ring_polygon(
            -w2act - dw2act, -h2act - dh2act, w2act + dw2act, h2act + dh2act,
            -w2act, -h2act, w2act, h2act,
            self.activlayer))

        # ==================================================
        # 5. Collector Metal1 ring
        #    Original: XOR of Box(-w2m1,-h2m1,w2m1,h2m1)
        #              and Box(-w2m1-dw2m1,-h2m1-dh2m1,w2m1+dw2m1,h2m1+dh2m1)
        # ==================================================
        tempShapes.append(self._ring_polygon(
            -w2m1 - dw2m1, -h2m1 - dh2m1, w2m1 + dw2m1, h2m1 + dh2m1,
            -w2m1, -h2m1, w2m1, h2m1,
            self.metal1layer))

        # ==================================================
        # 6. Collector contacts (left and right sides)
        # ==================================================
        # Reset spacing for collector contacts
        _ds = Cnt_b
        if (dw2m1) >= vg4 and (h2m1 * 2) >= vg4:
            _ds = Cnt_b1

        # Left side contacts
        tempShapes.extend(
            self.contactArray(self.metal1layer, self.contactlayer,
                              -w2m1 - dw2m1, -h2m1, -w2m1, h2m1,
                              _ox, _oy, _ws, _ds))
        # Right side contacts
        tempShapes.extend(
            self.contactArray(self.metal1layer, self.contactlayer,
                              w2m1, -h2m1, w2m1 + dw2m1, h2m1,
                              _ox, _oy, _ws, _ds))

        # ==================================================
        # 7. nBuLay isolation
        # ==================================================
        tempShapes.append(self._rect(-wbulay, -hbulay, wbulay, hbulay, self.nbulaylayer))

        # ==================================================
        # 8. NWell isolation
        # ==================================================
        tempShapes.append(self._rect(-wnwell, -hnwell, wnwell, hnwell, self.nwelllayer))

        # ==================================================
        # 9. Outer pSD ring
        #    Original: XOR of Box(-w2psd,-h2psd,w2psd,h2psd)
        #              and Box(-w2psd-d2psd,-h2psd-d2psd,w2psd+d2psd,h2psd+d2psd)
        # ==================================================
        tempShapes.append(self._ring_polygon(
            -w2psd - d2psd, -h2psd - d2psd, w2psd + d2psd, h2psd + d2psd,
            -w2psd, -h2psd, w2psd, h2psd,
            self.psdlayer))

        # ==================================================
        # 10. Outer Activ ring (guard ring)
        #     Original: XOR of Box(-w3act,-h3act,w3act,h3act)
        #               and Box(-w3act-d3act,-h3act-d3act,w3act+d3act,h3act+d3act)
        # ==================================================
        tempShapes.append(self._ring_polygon(
            -w3act - d3act, -h3act - d3act, w3act + d3act, h3act + d3act,
            -w3act, -h3act, w3act, h3act,
            self.activlayer))

        # ==================================================
        # 11. Guard ring contacts + Metal1 (TIE)
        #     All 4 sides
        # ==================================================
        _ds = Cnt_b
        _ox = 0.095
        _oy = M1_c1

        # Top
        tempShapes.extend(
            self.contactArray(self.metal1layer, self.contactlayer,
                              -w3act - d3act, h3act, w3act + d3act, h3act + d3act,
                              _ox, _oy, _ws, _ds))
        # Bottom
        tempShapes.extend(
            self.contactArray(self.metal1layer, self.contactlayer,
                              -w3act - d3act, -h3act - d3act, w3act + d3act, -h3act,
                              _ox, _oy, _ws, _ds))
        # Left (different _oy)
        _oy = 0.085
        tempShapes.extend(
            self.contactArray(self.metal1layer, self.contactlayer,
                              -w3act - d3act, -h3act, -w3act, h3act,
                              _ox, _oy, _ws, _ds))
        # Right
        tempShapes.extend(
            self.contactArray(self.metal1layer, self.contactlayer,
                              w3act, -h3act, w3act + d3act, h3act,
                              _ox, _oy, _ws, _ds))

        # ==================================================
        # 12. Pins
        # ==================================================
        # PLUS pin (central anode, Metal1)
        pp1 = self.toSceneCoord(QPointF(-w1m1, -h1m1))
        pp2 = self.toSceneCoord(QPointF(w1m1, h1m1))
        tempShapes.append(lshp.layoutPin(
            pp1, pp2, "PLUS", lshp.layoutPin.pinDirs[2],
            lshp.layoutPin.pinTypes[0], self.metal1layer_pin))
        tempShapes.append(lshp.layoutLabel(
            QRectF(pp1, pp2).center(), "PLUS",
            *self._labelFontTuple,
            lshp.layoutLabel.LABEL_ALIGNMENTS[0],
            lshp.layoutLabel.LABEL_ORIENTS[0], self.textlayer))

        # MINUS pin (collector ring, left band Metal1)
        mp1 = self.toSceneCoord(QPointF(-w2m1 - dw2m1, -h2m1))
        mp2 = self.toSceneCoord(QPointF(-w2m1, h2m1))
        tempShapes.append(lshp.layoutPin(
            mp1, mp2, "MINUS", lshp.layoutPin.pinDirs[2],
            lshp.layoutPin.pinTypes[0], self.metal1layer_pin))
        tempShapes.append(lshp.layoutLabel(
            QRectF(mp1, mp2).center(), "MINUS",
            *self._labelFontTuple,
            lshp.layoutLabel.LABEL_ALIGNMENTS[0],
            lshp.layoutLabel.LABEL_ORIENTS[0], self.textlayer))

        # TIE pin (guard ring, top band)
        tp1 = self.toSceneCoord(QPointF(-w3act - d3act, h3act))
        tp2 = self.toSceneCoord(QPointF(w3act + d3act, h3act + d3act))
        tempShapes.append(lshp.layoutPin(
            tp1, tp2, "TIE", lshp.layoutPin.pinDirs[2],
            lshp.layoutPin.pinTypes[0], self.metal1layer_pin))
        tempShapes.append(lshp.layoutLabel(
            QRectF(tp1, tp2).center(), "TIE",
            *self._labelFontTuple,
            lshp.layoutLabel.LABEL_ALIGNMENTS[0],
            lshp.layoutLabel.LABEL_ORIENTS[0], self.textlayer))

        self.shapes = tempShapes

    # --- Helper methods ---

    def _rect(self, x1, y1, x2, y2, layer):
        """Create a layoutRect from layout coordinates."""
        p1 = self.toSceneCoord(QPointF(x1, y1))
        p2 = self.toSceneCoord(QPointF(x2, y2))
        return lshp.layoutRect(p1, p2, layer)

    def _ring_polygon(self, ox1, oy1, ox2, oy2, ix1, iy1, ix2, iy2, layer):
        """
        Create a rectangular ring polygon (outer - inner).

        Traces outer boundary CW, then inner boundary CCW to create
        a ring shape equivalent to XOR of two rectangles.
        """
        # Trace: outer CW from bottom-left, then notch into inner CCW
        points = [
            (ox1, oy1),  # outer bottom-left
            (ox2, oy1),  # outer bottom-right
            (ox2, oy2),  # outer top-right
            (ox1, oy2),  # outer top-left
            (ox1, iy2),  # step to inner top-left height
            (ix1, iy2),  # inner top-left
            (ix1, iy1),  # inner bottom-left
            (ix2, iy1),  # inner bottom-right
            (ix2, iy2),  # inner top-right
            (ox2, iy2),  # step back to outer at inner top-right
            (ox2, oy2),  # back to outer top-right (will close)
        ]
        # Actually for a proper ring we need to trace it differently.
        # Standard approach: outer perimeter, then cut to inner, trace inner
        # reversed, cut back to outer, close.
        points = [
            # Outer perimeter (CW)
            (ox1, oy1),
            (ox2, oy1),
            (ox2, oy2),
            (ox1, oy2),
            # Cut down to inner top-left
            (ox1, iy2),
            (ix1, iy2),
            # Inner perimeter (CCW = reversed CW)
            (ix1, iy1),
            (ix2, iy1),
            (ix2, iy2),
            # Cut back out to outer
            (ox2, iy2),
            (ox2, oy2),
        ]
        # Simplify: use the standard "figure-8" ring polygon with a slit
        # Outer rectangle traced CW, with a slit on left side connecting
        # to inner rectangle traced CCW
        ring_pts = [
            # Start at outer bottom-left, go CW
            (ox1, oy1),
            (ox2, oy1),
            (ox2, oy2),
            (ox1, oy2),
            # Slit: move to inner top-left
            (ix1, iy2),
            # Trace inner CCW (= reversed)
            (ix2, iy2),
            (ix2, iy1),
            (ix1, iy1),
            # Close slit back to outer bottom-left
            (ix1, iy2),
            (ox1, oy2),
        ]
        scene_points = [self.toSceneCoord(QPointF(x, y)) for x, y in ring_pts]
        return lshp.layoutPolygon(scene_points, layer)
