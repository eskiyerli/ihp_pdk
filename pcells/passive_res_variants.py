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
Resistor variant cells for IHP SG13G2 PDK.
Extends the base rsil (silicide) resistor with different protection and implant layers.
"""

from functools import lru_cache
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QGraphicsItem
import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule
from .passive import rsil
from .base import baseCell, fabproc

laylyr = importPDKModule('layoutLayers')


class rhigh(rsil):
    """
    High-ohmic polysilicon resistor variant (rhigh).
    
    Extends rsil with:
    - SalBlock protection layer (replaces EXTBlock)
    - pSD and nSD implant layers for device isolation
    - Dedicated tech parameter keys (rhigh_minW, rhigh_minL, etc.)
    
    Parameters:
        length: Resistor length (default "4u")
        width: Resistor width (default "1u")
        b: Number of bends/stripes (default "1")
        ps: Poly-to-poly spacing (default "0.18u")
    """

    # Override layer definitions for rhigh variant
    contpolylayer = laylyr.GatPoly_drawing
    bodypolylayer = laylyr.PolyRes_drawing
    reslayer = laylyr.RES_drawing
    sallayer = laylyr.SalBlock_drawing  # Primary protection layer
    extBlocklayer = laylyr.EXTBlock_drawing  # Secondary protection layer (also drawn)
    psdlayer = laylyr.pSD_drawing  # P-type source/drain implant
    nsdlayer = laylyr.nSD_drawing  # N-type source/drain implant
    locintlayer = laylyr.Cont_drawing
    metlayer = laylyr.Metal1_drawing
    metlayer_pin = laylyr.Metal1_pin
    metlayer_label = laylyr.Metal1_label
    textlayer = laylyr.TEXT_drawing

    def __init__(
            self,
            length: str = "4u",
            width: str = "1u",
            b: str = "0",
            ps: str = "0.18u",
    ):
        """Initialize rhigh resistor with specified dimensions."""
        self.length = length
        self.width = width
        self.b = b
        self.ps = ps
        baseCell.__init__(self, [])

    @lru_cache
    def __call__(self, length: str, width: str, b: str, ps: str):
        """
        Generate rhigh resistor layout.
        
        Calls parent rsil layout generation, then adds pSD/nSD implant layers
        to provide proper device isolation for high-ohmic resistors.
        
        Args:
            length: Resistor length
            width: Resistor width
            b: Number of bends/stripes
            ps: Poly-to-poly spacing
        """
        # Call parent to generate base rsil layout
        super().__call__(length, width, b, ps)

        # Extract tech parameters for implant layer sizing
        tp = baseCell._techParams
        implant_enclosure = tp.get("Rhi_c", 0.18)  # pSD/nSD enclosure over PolyRes/GatPoly (Rhi_c)

        # Add SalBlock, pSD and nSD implant layers.
        # SalBlock must cover only the resistor body (PolyRes) to block silicidation
        # there while leaving the contact polysilicon (GatPoly) unblocked.
        # KLayout: Box(xpos1-salover, ypos1, xpos2+salover, ypos2) — x-only enclosure.
        # pSD/nSD must cover the full cell (body + both contacts) to ensure
        # correct doping throughout.
        enc = implant_enclosure * fabproc.dbu
        sal_over = tp.get("Sal_c", 0.2) * fabproc.dbu

        # SalBlock bbox: PolyRes only (resistor body + bends, not contacts)
        sal_min_x = sal_min_y = float('inf')
        sal_max_x = sal_max_y = float('-inf')
        # pSD/nSD bbox: EXTBlock + GatPoly (full cell including both contacts)
        imp_min_x = imp_min_y = float('inf')
        imp_max_x = imp_max_y = float('-inf')

        for shape in list(self.shapes):
            if isinstance(shape, lshp.layoutRect):
                x1, y1 = shape.start.x(), shape.start.y()
                x2, y2 = shape.end.x(), shape.end.y()
                lx, rx = min(x1, x2), max(x1, x2)
                ly, ry = min(y1, y2), max(y1, y2)
                if shape.layer == rhigh.bodypolylayer:
                    sal_min_x = min(sal_min_x, lx)
                    sal_min_y = min(sal_min_y, ly)
                    sal_max_x = max(sal_max_x, rx)
                    sal_max_y = max(sal_max_y, ry)
                if shape.layer in (rhigh.bodypolylayer, rhigh.contpolylayer):
                    imp_min_x = min(imp_min_x, lx)
                    imp_min_y = min(imp_min_y, ly)
                    imp_max_x = max(imp_max_x, rx)
                    imp_max_y = max(imp_max_y, ry)

        def _add(shape):
            shape.setFlags(QGraphicsItem.ItemStacksBehindParent)
            shape.setFlag(QGraphicsItem.ItemIsSelectable, False)
            self.addShape(shape)

        if sal_min_x != float('inf'):
            _add(lshp.layoutRect(
                QPointF(sal_min_x - sal_over, sal_min_y),
                QPointF(sal_max_x + sal_over, sal_max_y),
                rhigh.sallayer,
            ))

        if imp_min_x != float('inf'):
            _add(lshp.layoutRect(
                QPointF(imp_min_x - enc, imp_min_y - enc),
                QPointF(imp_max_x + enc, imp_max_y + enc),
                rhigh.psdlayer,
            ))
            _add(lshp.layoutRect(
                QPointF(imp_min_x - enc, imp_min_y - enc),
                QPointF(imp_max_x + enc, imp_max_y + enc),
                rhigh.nsdlayer,
            ))


class rppd(rsil):
    """
    P-poly diffusion resistor variant (rppd).
    
    Extends rsil with:
    - SalBlock protection layer
    - pSD implant layer (p-type source/drain)
    - Dedicated tech parameter keys (rppd_minW, rppd_minL, etc.)
    - Optional pSD notch filling for tight poly spacing
    
    Parameters:
        length: Resistor length (default "4u")
        width: Resistor width (default "1u")
        b: Number of bends/stripes (default "1")
        ps: Poly-to-poly spacing (default "0.18u")
    """

    # Override layer definitions for rppd variant
    contpolylayer = laylyr.GatPoly_drawing
    bodypolylayer = laylyr.PolyRes_drawing
    reslayer = laylyr.RES_drawing
    sallayer = laylyr.SalBlock_drawing  # Primary protection layer
    extBlocklayer = laylyr.EXTBlock_drawing  # Secondary protection layer
    psdlayer = laylyr.pSD_drawing  # P-type source/drain implant (primary implant)
    locintlayer = laylyr.Cont_drawing
    metlayer = laylyr.Metal1_drawing
    metlayer_pin = laylyr.Metal1_pin
    metlayer_label = laylyr.Metal1_label
    textlayer = laylyr.TEXT_drawing

    def __init__(
            self,
            length: str = "4u",
            width: str = "1u",
            b: str = "0",
            ps: str = "0.18u",
    ):
        """Initialize rppd resistor with specified dimensions."""
        self.length = length
        self.width = width
        self.b = b
        self.ps = ps
        baseCell.__init__(self, [])

    @lru_cache
    def __call__(self, length: str, width: str, b: str, ps: str):
        """
        Generate rppd resistor layout.
        
        Calls parent rsil layout generation, then adds pSD implant layer
        for p-poly diffusion resistor variant.
        
        Args:
            length: Resistor length
            width: Resistor width
            b: Number of bends/stripes
            ps: Poly-to-poly spacing
        """
        # Call parent to generate base rsil layout
        super().__call__(length, width, b, ps)

        # Extract tech parameters for implant layer sizing
        tp = baseCell._techParams
        implant_enclosure = tp.get("Rppd_b", 0.18)  # pSD enclosure over PolyRes/GatPoly (Rppd_b)

        # Add pSD implant layer as a single bounding-box rectangle covering the
        # full cell (body + both contacts), matching the KLayout reference approach.
        enc = implant_enclosure * fabproc.dbu

        bbox_min_x = bbox_min_y = float('inf')
        bbox_max_x = bbox_max_y = float('-inf')

        for shape in list(self.shapes):
            if isinstance(shape, lshp.layoutRect):
                x1, y1 = shape.start.x(), shape.start.y()
                x2, y2 = shape.end.x(), shape.end.y()
                lx, rx = min(x1, x2), max(x1, x2)
                ly, ry = min(y1, y2), max(y1, y2)
                if shape.layer in (rppd.bodypolylayer, rppd.contpolylayer):
                    bbox_min_x = min(bbox_min_x, lx)
                    bbox_min_y = min(bbox_min_y, ly)
                    bbox_max_x = max(bbox_max_x, rx)
                    bbox_max_y = max(bbox_max_y, ry)

        def _add(shape):
            shape.setFlags(QGraphicsItem.ItemStacksBehindParent)
            shape.setFlag(QGraphicsItem.ItemIsSelectable, False)
            self.addShape(shape)

        if bbox_min_x != float('inf'):
            _add(lshp.layoutRect(
                QPointF(bbox_min_x - enc, bbox_min_y - enc),
                QPointF(bbox_max_x + enc, bbox_max_y + enc),
                rppd.psdlayer,
            ))
