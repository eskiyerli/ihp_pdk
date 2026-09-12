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
Configurable multi-layer via stack parametric cell for IHP SG13G2 PDK.

Generates a via stack between two metal layers with configurable via
array dimensions per via type (standard vias, TopVia1, TopVia2).
"""

from functools import lru_cache

from PySide6.QtCore import QPointF
from quantiphy import Quantity

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule
from .base import baseCell

laylyr = importPDKModule('layoutLayers')


# Layer stack definition: ordered list of (metal_layer, via_layer_above)
# via_layer_above is the via connecting this metal to the next one up.
_LAYER_STACK = [
    {'name': 'Activ', 'metal': laylyr.Activ_drawing, 'via_above': laylyr.Cont_drawing},
    {'name': 'GatPoly', 'metal': laylyr.GatPoly_drawing, 'via_above': laylyr.Cont_drawing},
    {'name': 'Metal1', 'metal': laylyr.Metal1_drawing, 'via_above': laylyr.Via1_drawing},
    {'name': 'Metal2', 'metal': laylyr.Metal2_drawing, 'via_above': laylyr.Via2_drawing},
    {'name': 'Metal3', 'metal': laylyr.Metal3_drawing, 'via_above': laylyr.Via3_drawing},
    {'name': 'Metal4', 'metal': laylyr.Metal4_drawing, 'via_above': laylyr.Via4_drawing},
    {'name': 'Metal5', 'metal': laylyr.Metal5_drawing, 'via_above': laylyr.TopVia1_drawing},
    {'name': 'TopMetal1', 'metal': laylyr.TopMetal1_drawing, 'via_above': laylyr.TopVia2_drawing},
    {'name': 'TopMetal2', 'metal': laylyr.TopMetal2_drawing, 'via_above': None},
]

# Map name -> index in _LAYER_STACK
_LAYER_INDEX = {entry['name']: i for i, entry in enumerate(_LAYER_STACK)}

# Via design rules per via type
# Key is via layer name, value is (size, spacing, metal_enclosure)
_VIA_RULES = {
    'Cont': ('Cnt_a', 'Cnt_b', 'M1_c'),
    'Via1': ('Vn_a', 'Vn_b', 'Vn_d'),
    'Via2': ('Vn_a', 'Vn_b', 'Vn_d'),
    'Via3': ('Vn_a', 'Vn_b', 'Vn_d'),
    'Via4': ('Vn_a', 'Vn_b', 'Vn_d'),
    'TopVia1': ('TV1_a', 'TV1_b', 'TV1_d'),
    'TopVia2': ('TV2_a', 'TV2_b', 'TV2_d'),
}


class via_stack(baseCell):
    """
    Configurable multi-layer via stack.

    Generates a via stack connecting any two layers in the SG13G2 metal stack,
    with configurable via array dimensions (rows x columns) for each via type.

    Parameters:
        b_layer: Bottom layer name (default "Metal1")
        t_layer: Top layer name (default "Metal2")
        vn_columns: Number of columns for standard vias (default "2")
        vn_rows: Number of rows for standard vias (default "2")
        vt1_columns: Number of columns for TopVia1 (default "1")
        vt1_rows: Number of rows for TopVia1 (default "1")
        vt2_columns: Number of columns for TopVia2 (default "1")
        vt2_rows: Number of rows for TopVia2 (default "1")
    """

    textLayer = laylyr.TEXT_drawing

    def __init__(self, b_layer: str = "Metal1", t_layer: str = "Metal2",
                 vn_columns: str = "2", vn_rows: str = "2",
                 vt1_columns: str = "1", vt1_rows: str = "1",
                 vt2_columns: str = "1", vt2_rows: str = "1"):
        self.b_layer = b_layer
        self.t_layer = t_layer
        self.vn_columns = vn_columns
        self.vn_rows = vn_rows
        self.vt1_columns = vt1_columns
        self.vt1_rows = vt1_rows
        self.vt2_columns = vt2_columns
        self.vt2_rows = vt2_rows
        super().__init__([])

    @lru_cache
    def __call__(self, b_layer: str, t_layer: str,
                 vn_columns: str, vn_rows: str,
                 vt1_columns: str, vt1_rows: str,
                 vt2_columns: str, vt2_rows: str):
        """
        Generate the via stack layout.

        Args:
            b_layer: Bottom layer name (e.g. "Metal1", "Activ", "GatPoly")
            t_layer: Top layer name (e.g. "Metal2", "TopMetal1", "TopMetal2")
            vn_columns: Standard via columns
            vn_rows: Standard via rows
            vt1_columns: TopVia1 columns
            vt1_rows: TopVia1 rows
            vt2_columns: TopVia2 columns
            vt2_rows: TopVia2 rows
        """
        self.b_layer = b_layer
        self.t_layer = t_layer
        self.vn_columns = vn_columns
        self.vn_rows = vn_rows
        self.vt1_columns = vt1_columns
        self.vt1_rows = vt1_rows
        self.vt2_columns = vt2_columns
        self.vt2_rows = vt2_rows

        vn_cols = int(float(vn_columns))
        vn_rws = int(float(vn_rows))
        vt1_cols = int(float(vt1_columns))
        vt1_rws = int(float(vt1_rows))
        vt2_cols = int(float(vt2_columns))
        vt2_rws = int(float(vt2_rows))

        tp = baseCell._techParams

        # Resolve layer indices
        b_idx = _LAYER_INDEX.get(b_layer)
        t_idx = _LAYER_INDEX.get(t_layer)

        if b_idx is None or t_idx is None:
            print(f"via_stack: invalid layer name b_layer={b_layer} t_layer={t_layer}")
            self.shapes = []
            return

        # Device layers (Activ, GatPoly) are mutually exclusive
        device_layers = {'Activ', 'GatPoly'}
        if b_layer in device_layers and t_layer in device_layers:
            t_layer = 'Metal1'
            t_idx = _LAYER_INDEX['Metal1']

        if t_idx <= b_idx:
            t_layer = 'Metal1' if b_idx == 0 else _LAYER_STACK[b_idx + 1]['name']
            t_idx = _LAYER_INDEX[t_layer]

        tempShapes = []

        # Build list of vias to traverse from b_layer to t_layer
        # Via at index i connects layer i to layer i+1
        via_list = []
        for i in range(b_idx, t_idx):
            entry = _LAYER_STACK[i]
            via_layer = entry['via_above']
            via_name = entry['via_above'].name if via_layer else None
            if via_name is None:
                break
            via_list.append({
                'index': i,
                'via_layer': via_layer,
                'via_name': via_name,
                'bottom_metal': entry['metal'],
                'top_metal': _LAYER_STACK[i + 1]['metal'],
            })

        if not via_list:
            self.shapes = []
            return

        # For each via level, compute array geometry and accumulate
        # Track the running bounding box for metal sizing
        prev_metal_box = None

        for vi, via_info in enumerate(via_list):
            via_name = via_info['via_name']

            # Determine nx, ny for this via type
            if via_name == 'TopVia1':
                nx, ny = vt1_cols, vt1_rws
            elif via_name == 'TopVia2':
                nx, ny = vt2_cols, vt2_rws
            else:
                nx, ny = vn_cols, vn_rws

            # Get design rules for this via
            rule_key = via_name
            if rule_key not in _VIA_RULES:
                rule_key = 'Via1'  # fallback

            size_key, spacing_key, enc_key = _VIA_RULES[rule_key]
            via_size = tp[size_key]
            via_spacing = tp[spacing_key]
            metal_enc = tp[enc_key]

            # Compute via array dimensions
            array_w = nx * via_size + (nx - 1) * via_spacing
            array_h = ny * via_size + (ny - 1) * via_spacing

            # Metal box enclosing via array
            metal_w = array_w + 2 * metal_enc
            metal_h = array_h + 2 * metal_enc

            # Place via array starting at (metal_enc, metal_enc) relative to (0,0)
            x_start = metal_enc
            y_start = metal_enc

            # Draw via rectangles
            for row in range(ny):
                for col in range(nx):
                    cx = x_start + col * (via_size + via_spacing)
                    cy = y_start + row * (via_size + via_spacing)
                    p1 = self.toSceneCoord(QPointF(cx, cy))
                    p2 = self.toSceneCoord(QPointF(cx + via_size, cy + via_size))
                    tempShapes.append(lshp.layoutRect(p1, p2, via_info['via_layer']))

            # Draw bottom metal for this via (use larger of prev_metal_box or current)
            current_box = (0, 0, metal_w, metal_h)

            if vi == 0:
                # First via: draw bottom metal
                p1 = self.toSceneCoord(QPointF(0, 0))
                p2 = self.toSceneCoord(QPointF(metal_w, metal_h))
                tempShapes.append(
                    lshp.layoutRect(p1, p2, via_info['bottom_metal']))
                prev_metal_box = current_box
            else:
                # Use union of previous and current for bottom metal
                # (bottom metal of this via is top metal of previous)
                ux1 = min(prev_metal_box[0], current_box[0])
                uy1 = min(prev_metal_box[1], current_box[1])
                ux2 = max(prev_metal_box[2], current_box[2])
                uy2 = max(prev_metal_box[3], current_box[3])
                p1 = self.toSceneCoord(QPointF(ux1, uy1))
                p2 = self.toSceneCoord(QPointF(ux2, uy2))
                tempShapes.append(
                    lshp.layoutRect(p1, p2, via_info['bottom_metal']))
                prev_metal_box = (ux1, uy1, ux2, uy2)

        # Draw top metal for the last via
        if via_list:
            last_via = via_list[-1]
            via_name = last_via['via_name']
            rule_key = via_name if via_name in _VIA_RULES else 'Via1'
            size_key, spacing_key, enc_key = _VIA_RULES[rule_key]
            via_size = tp[size_key]
            via_spacing = tp[spacing_key]
            metal_enc = tp[enc_key]

            if via_name == 'TopVia1':
                nx, ny = vt1_cols, vt1_rws
            elif via_name == 'TopVia2':
                nx, ny = vt2_cols, vt2_rws
            else:
                nx, ny = vn_cols, vn_rws

            array_w = nx * via_size + (nx - 1) * via_spacing
            array_h = ny * via_size + (ny - 1) * via_spacing
            metal_w = array_w + 2 * metal_enc
            metal_h = array_h + 2 * metal_enc

            top_box = (0, 0, metal_w, metal_h)
            if prev_metal_box:
                ux1 = min(prev_metal_box[0], top_box[0])
                uy1 = min(prev_metal_box[1], top_box[1])
                ux2 = max(prev_metal_box[2], top_box[2])
                uy2 = max(prev_metal_box[3], top_box[3])
            else:
                ux1, uy1, ux2, uy2 = top_box

            p1 = self.toSceneCoord(QPointF(ux1, uy1))
            p2 = self.toSceneCoord(QPointF(ux2, uy2))
            tempShapes.append(
                lshp.layoutRect(p1, p2, last_via['top_metal']))

        self.shapes = tempShapes
