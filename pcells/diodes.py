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
ESD Protection Diode (Antenna) cells for IHP SG13G2 PDK.

Includes N-type (dantenna) and P-type (dpantenna) antenna diodes
for electrostatic discharge protection in signal paths.
"""

from functools import lru_cache
from PySide6.QtCore import QPointF
from quantiphy import Quantity

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule
from .base import baseCell

laylyr = importPDKModule('layoutLayers')


class dantenna(baseCell):
    """
    N-type ESD protection diode (antenna diode).

    Simple junction diode: N+ diffusion over p-substrate.
    Used for protection on signal paths.

    Features:
    - N+/P-substrate junction
    - Parametric width and length
    - Contact array with grid-fixed positions
    - Metal1 pad covering contact array bounding box
    - Recognition layer for LVS

    Parameters:
        width: Device width (default "0.78u")
        length: Device length (default "0.78u")
    """

    # Layer definitions
    activlayer = laylyr.Activ_drawing
    contactlayer = laylyr.Cont_drawing
    metal1layer = laylyr.Metal1_drawing
    metal1layer_pin = laylyr.Metal1_pin
    textlayer = laylyr.TEXT_drawing
    recoglayer = laylyr.Recog_diode

    def __init__(self, width: str = "0.78u", length: str = "0.78u"):
        """Initialize dantenna with specified dimensions."""
        self.width = width
        self.length = length
        super().__init__([])

    @lru_cache
    def __call__(self, width: str, length: str):
        """
        Generate dantenna N-type ESD diode layout.

        Creates a simple N+/P-substrate junction with contacts
        distributed in a grid pattern matching the original KLayout
        DrawContArray behavior.

        Args:
            width: Device width (e.g., "0.78u")
            length: Device length (e.g., "0.78u")
        """
        # Parse parameters
        w_um = Quantity(width).real * 1e6
        l_um = Quantity(length).real * 1e6

        # Get technology parameters
        tp = baseCell._techParams
        cont_size = tp["Cnt_a"]
        cont_spacing = tp["Cnt_b"]
        cont_enclosure = tp["Cnt_c"]
        # Large-array spacing rule
        cont_spacing_big = tp["Cnt_b1"]
        cont_spacing_big_nr = tp["Cnt_b1_nr"]

        # Min dimensions
        wmin = Quantity(tp["dantenna_minW"]).real * 1e6
        lmin = Quantity(tp["dantenna_minL"]).real * 1e6

        # Recognition layer overshoot
        diods_over = Quantity(tp["dantenna_dov"]).real * 1e6

        # Enforce minimum width/length
        if w_um < wmin - self._epsilon:
            w_um = wmin
            print(f"dantenna: W clamped to minimum {wmin}")

        if l_um < lmin - self._epsilon:
            l_um = lmin
            print(f"dantenna: L clamped to minimum {lmin}")

        tempShapes = []

        # ==================================================
        # 1. Device name label at center on TEXT layer
        # ==================================================
        center_pt = self.toSceneCoord(QPointF(w_um / 2, l_um / 2))
        tempShapes.append(
            lshp.layoutLabel(
                center_pt, "dant",
                *self._labelFontTuple,
                lshp.layoutLabel.LABEL_ALIGNMENTS[0],
                lshp.layoutLabel.LABEL_ORIENTS[0],
                dantenna.textlayer
            )
        )

        # ==================================================
        # 2. Draw contact array (replicating DrawContArray)
        # ==================================================
        cont_bbox = self._draw_cont_array(
            tempShapes, 0, 0, w_um, l_um,
            cont_size, cont_spacing, cont_enclosure,
            cont_spacing_big, cont_spacing_big_nr,
            dantenna.contactlayer
        )

        # ==================================================
        # 3. Draw Metal1 pad covering contact array bbox
        # ==================================================
        metal_p1 = self.toSceneCoord(QPointF(cont_bbox[0], cont_bbox[1]))
        metal_p2 = self.toSceneCoord(QPointF(cont_bbox[2], cont_bbox[3]))
        tempShapes.append(lshp.layoutRect(metal_p1, metal_p2, dantenna.metal1layer))

        # ==================================================
        # 4. Create MINUS pin on Metal1 bbox
        # ==================================================
        tempShapes.append(
            lshp.layoutPin(
                metal_p1, metal_p2, "MINUS",
                lshp.layoutPin.pinDirs[2],
                lshp.layoutPin.pinTypes[0],
                dantenna.metal1layer_pin
            )
        )

        # ==================================================
        # 5. Draw Active (N-diffusion) region: Box(0, 0, w, l)
        # ==================================================
        p1 = self.toSceneCoord(QPointF(0, 0))
        p2 = self.toSceneCoord(QPointF(w_um, l_um))
        tempShapes.append(lshp.layoutRect(p1, p2, dantenna.activlayer))

        # ==================================================
        # 6. Draw Recognition layer for LVS
        # ==================================================
        recog_p1 = self.toSceneCoord(
            QPointF(-diods_over, -diods_over)
        )
        recog_p2 = self.toSceneCoord(
            QPointF(w_um + diods_over, l_um + diods_over)
        )
        tempShapes.append(
            lshp.layoutRect(recog_p1, recog_p2, dantenna.recoglayer)
        )

        self.shapes = tempShapes

    def _draw_cont_array(self, shapes, x1, y1, x2, y2,
                         cont_size, cont_spacing, cont_enclosure,
                         cont_spacing_big, cont_spacing_big_nr,
                         cont_layer):
        """
        Replicate the original DrawContArray logic.

        Computes contact grid count, applies large-array spacing rule,
        centers the grid within the bounding box with grid-fixed offsets,
        and returns the contact array bounding box (x1, y1, x2, y2).
        """
        w = x2 - x1
        h = y2 - y1

        # Calculate number of contacts in each direction
        xanz = self.fix(
            (w - 2 * cont_enclosure + cont_spacing + self._epsilon)
            / (cont_size + cont_spacing)
        )
        yanz = self.fix(
            (h - 2 * cont_enclosure + cont_spacing + self._epsilon)
            / (cont_size + cont_spacing)
        )

        if xanz <= 0:
            xanz = 1
        if yanz <= 0:
            yanz = 1

        # Large-array spacing rule: if >= Cnt_b1_nr contacts in both
        # directions, increase spacing to Cnt_b1
        if xanz >= cont_spacing_big_nr and yanz >= cont_spacing_big_nr:
            cont_spacing = cont_spacing_big
            xanz = self.fix(
                (w - 2 * cont_enclosure + cont_spacing + self._epsilon)
                / (cont_size + cont_spacing)
            )
            yanz = self.fix(
                (h - 2 * cont_enclosure + cont_spacing + self._epsilon)
                / (cont_size + cont_spacing)
            )
            if xanz <= 0:
                xanz = 1
            if yanz <= 0:
                yanz = 1

        # Compute the minimum space needed by the contact grid
        xmin = xanz * (cont_size + cont_spacing) - cont_spacing + 2 * cont_enclosure
        ymin = yanz * (cont_size + cont_spacing) - cont_spacing + 2 * cont_enclosure

        # Center the grid within the device (grid-fixed offset)
        xoff = self.GridFix((w - xmin) / 2)
        yoff = self.GridFix((h - ymin) / 2)

        # Place contacts
        for j in range(int(yanz)):
            for i in range(int(xanz)):
                cx = x1 + xoff + cont_enclosure + (cont_size + cont_spacing) * i
                cy = y1 + yoff + cont_enclosure + (cont_size + cont_spacing) * j
                p1 = self.toSceneCoord(QPointF(cx, cy))
                p2 = self.toSceneCoord(QPointF(cx + cont_size, cy + cont_size))
                shapes.append(lshp.layoutRect(p1, p2, cont_layer))

        # Return bounding box of the contact array
        bbox_x1 = x1 + xoff + cont_enclosure
        bbox_y1 = y1 + yoff + cont_enclosure
        bbox_x2 = bbox_x1 + xanz * cont_size + (xanz - 1) * cont_spacing
        bbox_y2 = bbox_y1 + yanz * cont_size + (yanz - 1) * cont_spacing

        return (bbox_x1, bbox_y1, bbox_x2, bbox_y2)


class dpantenna(baseCell):
    """
    P-type ESD protection diode (antenna diode) in isolated well.

    Junction diode: P+ diffusion in N-well over p-substrate.
    Provides isolated ESD protection in high-impedance circuits.

    Features:
    - P+/N-well junction with substrate isolation
    - Parametric width and length
    - Contact array with grid-fixed positions
    - pSD implant and NWell sized from active area
    - Metal1 pad covering contact array bounding box
    - Recognition layer for LVS

    Parameters:
        width: Device width (default "0.78u")
        length: Device length (default "0.78u")
    """

    # Layer definitions
    activlayer = laylyr.Activ_drawing
    psdlayer = laylyr.pSD_drawing
    nwelllayer = laylyr.NWell_drawing
    contactlayer = laylyr.Cont_drawing
    metal1layer = laylyr.Metal1_drawing
    metal1layer_pin = laylyr.Metal1_pin
    textlayer = laylyr.TEXT_drawing
    recoglayer = laylyr.Recog_diode

    def __init__(self, width: str = "0.78u", length: str = "0.78u"):
        """Initialize dpantenna with specified dimensions."""
        self.width = width
        self.length = length
        super().__init__([])

    @lru_cache
    def __call__(self, width: str, length: str):
        """
        Generate dpantenna P-type ESD diode layout in isolated well.

        Creates a P+/N-well junction with NWell sized from the active
        region (matching original dbLayerSize behavior).

        Args:
            width: Device width (e.g., "0.78u")
            length: Device length (e.g., "0.78u")
        """
        # Parse parameters
        w_um = Quantity(width).real * 1e6
        l_um = Quantity(length).real * 1e6

        # Get technology parameters
        tp = baseCell._techParams
        cont_size = tp["Cnt_a"]
        cont_spacing = tp["Cnt_b"]
        cont_enclosure = tp["Cnt_c"]
        cont_spacing_big = tp["Cnt_b1"]
        cont_spacing_big_nr = tp["Cnt_b1_nr"]
        psd_enclosure = tp["pSD_c"]
        nwell_enclosure = tp["NW_c"]  # NWell sized from Activ

        # Min dimensions
        wmin = Quantity(tp["dpantenna_minW"]).real * 1e6
        lmin = Quantity(tp["dpantenna_minL"]).real * 1e6

        # Recognition layer overshoot
        diods_over = Quantity(tp["dpantenna_dov"]).real * 1e6

        # Enforce minimum width/length
        if w_um < wmin - self._epsilon:
            w_um = wmin
            print(f"dpantenna: W clamped to minimum {wmin}")

        if l_um < lmin - self._epsilon:
            l_um = lmin
            print(f"dpantenna: L clamped to minimum {lmin}")

        tempShapes = []

        # ==================================================
        # 1. Device name label at center on TEXT layer
        # ==================================================
        center_pt = self.toSceneCoord(QPointF(w_um / 2, l_um / 2))
        tempShapes.append(
            lshp.layoutLabel(
                center_pt, "dpant",
                *self._labelFontTuple,
                lshp.layoutLabel.LABEL_ALIGNMENTS[0],
                lshp.layoutLabel.LABEL_ORIENTS[0],
                dpantenna.textlayer
            )
        )

        # ==================================================
        # 2. Draw contact array (replicating DrawContArray)
        # ==================================================
        cont_bbox = self._draw_cont_array(
            tempShapes, 0, 0, w_um, l_um,
            cont_size, cont_spacing, cont_enclosure,
            cont_spacing_big, cont_spacing_big_nr,
            dpantenna.contactlayer
        )

        # ==================================================
        # 3. Draw Metal1 pad covering contact array bbox
        # ==================================================
        metal_p1 = self.toSceneCoord(QPointF(cont_bbox[0], cont_bbox[1]))
        metal_p2 = self.toSceneCoord(QPointF(cont_bbox[2], cont_bbox[3]))
        tempShapes.append(lshp.layoutRect(metal_p1, metal_p2, dpantenna.metal1layer))

        # ==================================================
        # 4. Create MINUS pin on Metal1 bbox
        # ==================================================
        tempShapes.append(
            lshp.layoutPin(
                metal_p1, metal_p2, "MINUS",
                lshp.layoutPin.pinDirs[2],
                lshp.layoutPin.pinTypes[0],
                dpantenna.metal1layer_pin
            )
        )

        # ==================================================
        # 5. Draw P-diffusion (Activ) region: Box(0, 0, w, l)
        # ==================================================
        p1 = self.toSceneCoord(QPointF(0, 0))
        p2 = self.toSceneCoord(QPointF(w_um, l_um))
        tempShapes.append(lshp.layoutRect(p1, p2, dpantenna.activlayer))

        # ==================================================
        # 6. Draw pSD implant layer (P+ implant)
        # ==================================================
        psd_p1 = self.toSceneCoord(
            QPointF(-psd_enclosure, -psd_enclosure)
        )
        psd_p2 = self.toSceneCoord(
            QPointF(w_um + psd_enclosure, l_um + psd_enclosure)
        )
        tempShapes.append(lshp.layoutRect(psd_p1, psd_p2, dpantenna.psdlayer))

        # ==================================================
        # 7. Draw Recognition layer for LVS
        # ==================================================
        recog_p1 = self.toSceneCoord(
            QPointF(-diods_over, -diods_over)
        )
        recog_p2 = self.toSceneCoord(
            QPointF(w_um + diods_over, l_um + diods_over)
        )
        tempShapes.append(
            lshp.layoutRect(recog_p1, recog_p2, dpantenna.recoglayer)
        )

        # ==================================================
        # 8. Draw NWell sized from Active
        #    Original: dbLayerSize(nwell_layer, [pdiffRect], NW_c)
        # ==================================================
        nwell_p1 = self.toSceneCoord(
            QPointF(-nwell_enclosure, -nwell_enclosure)
        )
        nwell_p2 = self.toSceneCoord(
            QPointF(w_um + nwell_enclosure, l_um + nwell_enclosure)
        )
        tempShapes.append(lshp.layoutRect(nwell_p1, nwell_p2, dpantenna.nwelllayer))

        self.shapes = tempShapes

    def _draw_cont_array(self, shapes, x1, y1, x2, y2,
                         cont_size, cont_spacing, cont_enclosure,
                         cont_spacing_big, cont_spacing_big_nr,
                         cont_layer):
        """
        Replicate the original DrawContArray logic.

        Computes contact grid count, applies large-array spacing rule,
        centers the grid within the bounding box with grid-fixed offsets,
        and returns the contact array bounding box (x1, y1, x2, y2).
        """
        w = x2 - x1
        h = y2 - y1

        # Calculate number of contacts in each direction
        xanz = self.fix(
            (w - 2 * cont_enclosure + cont_spacing + self._epsilon)
            / (cont_size + cont_spacing)
        )
        yanz = self.fix(
            (h - 2 * cont_enclosure + cont_spacing + self._epsilon)
            / (cont_size + cont_spacing)
        )

        if xanz <= 0:
            xanz = 1
        if yanz <= 0:
            yanz = 1

        # Large-array spacing rule: if >= Cnt_b1_nr contacts in both
        # directions, increase spacing to Cnt_b1
        if xanz >= cont_spacing_big_nr and yanz >= cont_spacing_big_nr:
            cont_spacing = cont_spacing_big
            xanz = self.fix(
                (w - 2 * cont_enclosure + cont_spacing + self._epsilon)
                / (cont_size + cont_spacing)
            )
            yanz = self.fix(
                (h - 2 * cont_enclosure + cont_spacing + self._epsilon)
                / (cont_size + cont_spacing)
            )
            if xanz <= 0:
                xanz = 1
            if yanz <= 0:
                yanz = 1

        # Compute the minimum space needed by the contact grid
        xmin = xanz * (cont_size + cont_spacing) - cont_spacing + 2 * cont_enclosure
        ymin = yanz * (cont_size + cont_spacing) - cont_spacing + 2 * cont_enclosure

        # Center the grid within the device (grid-fixed offset)
        xoff = self.GridFix((w - xmin) / 2)
        yoff = self.GridFix((h - ymin) / 2)

        # Place contacts
        for j in range(int(yanz)):
            for i in range(int(xanz)):
                cx = x1 + xoff + cont_enclosure + (cont_size + cont_spacing) * i
                cy = y1 + yoff + cont_enclosure + (cont_size + cont_spacing) * j
                p1 = self.toSceneCoord(QPointF(cx, cy))
                p2 = self.toSceneCoord(QPointF(cx + cont_size, cy + cont_size))
                shapes.append(lshp.layoutRect(p1, p2, cont_layer))

        # Return bounding box of the contact array
        bbox_x1 = x1 + xoff + cont_enclosure
        bbox_y1 = y1 + yoff + cont_enclosure
        bbox_x2 = bbox_x1 + xanz * cont_size + (xanz - 1) * cont_spacing
        bbox_y2 = bbox_y1 + yanz * cont_size + (yanz - 1) * cont_spacing

        return (bbox_x1, bbox_y1, bbox_x2, bbox_y2)
