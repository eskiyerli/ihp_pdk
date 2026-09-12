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
RF High-Voltage MOSFET parametric cells for IHP SG13G2 PDK.

Extends rfnmos/rfpmos with ThickGateOx layer for high-voltage operation.
"""

from functools import lru_cache

from PySide6.QtCore import QPointF
from quantiphy import Quantity

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule
from .base import baseRfMosfet, baseCell
from .rf_mosfet import rfnmos, rfpmos

laylyr = importPDKModule('layoutLayers')


class rfnmosHV(rfnmos):
    """RF High-Voltage NMOS transistor - extends rfnmos with ThickGateOx layer."""

    tgo_layer = laylyr.ThickGateOx_drawing

    @staticmethod
    @lru_cache(maxsize=1)
    def _get_rfnmosHV_params():
        """Cache for RF NMOSHV technology parameters."""
        tp = baseCell._techParams
        return {
            "defL": Quantity(tp["rfnmosHV_defL"]).real,
            "defW": Quantity(tp["rfnmosHV_defW"]).real,
            "defNG": Quantity(tp["rfnmosHV_defNG"]).real,
            "minL": Quantity(tp["rfnmosHV_minL"]).real,
            "minW": Quantity(tp["rfnmosHV_minW"]).real,
        }

    def __init__(self, width: str = "1u", length: str = "0.72u", ng: str = "1",
                 cnt_rows: str = "1", Met2Cont: str = "1", gat_ring: str = "1",
                 guard_ring: str = "1"):

        params = self._get_rfnmosHV_params()
        self.width = Quantity(width).real if width else params["defW"]
        self.length = Quantity(length).real if length else params["defL"]
        self.ng = int(float(ng)) if ng else params["defNG"]
        self.cnt_rows = int(float(cnt_rows)) if cnt_rows else 1
        self.Met2Cont = Met2Cont
        self.gat_ring = gat_ring
        self.guard_ring = guard_ring
        # Skip rfnmos.__init__ and go directly to baseRfMosfet
        baseRfMosfet.__init__(self, [])

    @lru_cache
    def __call__(self, width: str, length: str, ng: str, cnt_rows: str,
                 Met2Cont: str, gat_ring: str, guard_ring: str):
        tempShapesList = []
        device_params = self._get_rfnmosHV_params()

        self.width = Quantity(width).real if width else device_params["defW"]
        self.length = Quantity(length).real if length else device_params["defL"]
        self.ng = int(float(ng)) if ng else device_params["defNG"]
        self.cnt_rows = int(float(cnt_rows)) if cnt_rows else 1
        self.Met2Cont = Met2Cont
        self.gat_ring = gat_ring
        self.guard_ring = guard_ring

        W = self.width * 1e6 / self.ng
        L = self.length * 1e6
        useMet2 = self.Met2Cont == '1'

        # Get common RF parameters
        rf_params = self._get_rf_common_params(W, L, self.ng, self.cnt_rows)
        rf_params.update({'L': L, 'cnt_rows': self.cnt_rows})

        # Active height
        hact = rf_params['ec'] + rf_params['ec'] + (self.ng - 1) * rf_params[
            'dc'] + self.ng * L

        # Draw active area and gates
        u = self._draw_rf_active_and_gates(tempShapesList, W, hact, self.ng,
                                           rf_params)

        # Draw source/drain contacts
        self._draw_rf_source_drain_contacts(tempShapesList, W, self.ng, rf_params,
                                            useMet2)

        # Draw pins
        self._draw_rf_pins(tempShapesList, W, rf_params)

        # Draw gate ring and contacts
        gat_ring = self.gat_ring == '1'
        self._draw_rf_gate_ring_and_contacts(tempShapesList, W, hact, rf_params,
                                             gat_ring, u)

        # Draw guard ring
        guard_ring = self.guard_ring == '1'
        xl, yb, xr, yt = self._draw_rf_guard_ring(tempShapesList, W, hact,
                                                   rf_params, guard_ring)

        # Inscription
        tempShapesList.append(lshp.layoutLabel(self.toSceneCoord(
            QPointF((xl + xr) / 2, yt - rf_params['wguard'] / 2)),
            self.__class__.__name__,
            *self._labelFontTuple,
            lshp.layoutLabel.LABEL_ALIGNMENTS[0],
            lshp.layoutLabel.LABEL_ORIENTS[0],
            self.text_layer))

        # pSD for rfnmosHV guard ring
        wpsd = 0.38
        d = (wpsd - rf_params['wguard']) / 2
        xl_psd, xr_psd = xl - d, xr + d
        yb_psd, yt_psd = yb - d, yt + d
        tempShapesList.append(
            lshp.layoutRect(self.toSceneCoord(QPointF(xl_psd, yb_psd)),
                            self.toSceneCoord(QPointF(xr_psd, yb_psd + wpsd)),
                            self.psd_layer))
        tempShapesList.append(
            lshp.layoutRect(self.toSceneCoord(QPointF(xl_psd, yt_psd - wpsd)),
                            self.toSceneCoord(QPointF(xr_psd, yt_psd)),
                            self.psd_layer))
        tempShapesList.append(
            lshp.layoutRect(self.toSceneCoord(QPointF(xl_psd, yb_psd + wpsd)),
                            self.toSceneCoord(
                                QPointF(xl_psd + wpsd, yt_psd - wpsd)),
                            self.psd_layer))
        tempShapesList.append(lshp.layoutRect(
            self.toSceneCoord(QPointF(xr_psd - wpsd, yb_psd + wpsd)),
            self.toSceneCoord(QPointF(xr_psd, yt_psd - wpsd)), self.psd_layer))

        # ThickGateOx layer for HV operation
        tp = baseCell._techParams
        tgo_over = tp["TGO_a"]  # ThickGateOx enclosure over active
        tgo_point1 = self.toSceneCoord(QPointF(-tgo_over, -tgo_over))
        tgo_point2 = self.toSceneCoord(QPointF(W + tgo_over, hact + tgo_over))
        tempShapesList.append(
            lshp.layoutRect(tgo_point1, tgo_point2, self.tgo_layer))

        # Move to origin
        move_point = self.toSceneCoord(QPointF(-xl, -yb))
        for shape in tempShapesList:
            if isinstance(shape,
                          (lshp.layoutRect, lshp.layoutPin, lshp.layoutLabel)):
                shape.moveBy(move_point.x(), move_point.y())

        self.shapes = tempShapesList


class rfpmosHV(rfpmos):
    """RF High-Voltage PMOS transistor - extends rfpmos with ThickGateOx layer."""

    tgo_layer = laylyr.ThickGateOx_drawing

    @staticmethod
    @lru_cache(maxsize=1)
    def _get_rfpmosHV_params():
        """Cache for RF PMOSHV technology parameters."""
        tp = baseCell._techParams
        return {
            "defL": Quantity(tp["rfpmosHV_defL"]).real,
            "defW": Quantity(tp["rfpmosHV_defW"]).real,
            "defNG": Quantity(tp["rfpmosHV_defNG"]).real,
            "minL": Quantity(tp["rfpmosHV_minL"]).real,
            "minW": Quantity(tp["rfpmosHV_minW"]).real,
        }

    def __init__(self, width: str = "1u", length: str = "0.72u", ng: str = "1",
                 cnt_rows: str = "1", Met2Cont: str = "1", gat_ring: str = "1",
                 guard_ring: str = "1"):

        params = self._get_rfpmosHV_params()
        self.width = Quantity(width).real if width else params["defW"]
        self.length = Quantity(length).real if length else params["defL"]
        self.ng = int(float(ng)) if ng else params["defNG"]
        self.cnt_rows = int(float(cnt_rows)) if cnt_rows else 1
        self.Met2Cont = Met2Cont
        self.gat_ring = gat_ring
        self.guard_ring = guard_ring
        # Skip rfpmos.__init__ and go directly to baseRfMosfet
        baseRfMosfet.__init__(self, [])

    @lru_cache
    def __call__(self, width: str, length: str, ng: str, cnt_rows: str,
                 Met2Cont: str, gat_ring: str, guard_ring: str):
        tempShapesList = []
        device_params = self._get_rfpmosHV_params()

        self.width = Quantity(width).real if width else device_params["defW"]
        self.length = Quantity(length).real if length else device_params["defL"]
        self.ng = int(float(ng)) if ng else device_params["defNG"]
        self.cnt_rows = int(float(cnt_rows)) if cnt_rows else 1
        self.Met2Cont = Met2Cont
        self.gat_ring = gat_ring
        self.guard_ring = guard_ring

        W = self.width * 1e6 / self.ng
        L = self.length * 1e6
        useMet2 = self.Met2Cont == '1'

        # Get common RF parameters
        rf_params = self._get_rf_common_params(W, L, self.ng, self.cnt_rows)
        rf_params.update({'L': L, 'cnt_rows': self.cnt_rows})

        # Active height
        hact = rf_params['ec'] + rf_params['ec'] + (self.ng - 1) * rf_params[
            'dc'] + self.ng * L

        # Draw active area and gates
        u = self._draw_rf_active_and_gates(tempShapesList, W, hact, self.ng,
                                           rf_params)

        # Draw source/drain contacts
        self._draw_rf_source_drain_contacts(tempShapesList, W, self.ng, rf_params,
                                            useMet2)

        # Draw pins
        self._draw_rf_pins(tempShapesList, W, rf_params)

        # Draw gate ring and contacts
        gat_ring = self.gat_ring == '1'
        self._draw_rf_gate_ring_and_contacts(tempShapesList, W, hact, rf_params,
                                             gat_ring, u)

        # Draw guard ring
        guard_ring = self.guard_ring == '1'
        xl, yb, xr, yt = self._draw_rf_guard_ring(tempShapesList, W, hact,
                                                   rf_params, guard_ring)

        # nSD for rfpmosHV guard ring
        wnsd = 0.38
        d = (wnsd - rf_params['wguard']) / 2
        xl_nsd, xr_nsd = xl - d, xr + d
        yb_nsd, yt_nsd = yb - d, yt + d
        tempShapesList.append(
            lshp.layoutRect(self.toSceneCoord(QPointF(xl_nsd, yb_nsd)),
                            self.toSceneCoord(QPointF(xr_nsd, yb_nsd + wnsd)),
                            self.nsd_layer))
        tempShapesList.append(
            lshp.layoutRect(self.toSceneCoord(QPointF(xl_nsd, yt_nsd - wnsd)),
                            self.toSceneCoord(QPointF(xr_nsd, yt_nsd)),
                            self.nsd_layer))
        tempShapesList.append(
            lshp.layoutRect(self.toSceneCoord(QPointF(xl_nsd, yb_nsd + wnsd)),
                            self.toSceneCoord(
                                QPointF(xl_nsd + wnsd, yt_nsd - wnsd)),
                            self.nsd_layer))
        tempShapesList.append(lshp.layoutRect(
            self.toSceneCoord(QPointF(xr_nsd - wnsd, yb_nsd + wnsd)),
            self.toSceneCoord(QPointF(xr_nsd, yt_nsd - wnsd)), self.nsd_layer))

        # NWell for rfpmosHV
        dnw = 0.38
        xl_nw = -rf_params['dgatx'] - rf_params['wgat'] - dnw
        xr_nw = W + rf_params['dgatx'] + rf_params['wgat'] + dnw
        yb_nw = -rf_params['dgaty'] - rf_params['wgat'] - dnw
        yt_nw = hact + rf_params['dgaty'] + rf_params['wgat'] + dnw
        tempShapesList.append(
            lshp.layoutRect(self.toSceneCoord(QPointF(xl_nw, yb_nw)),
                            self.toSceneCoord(QPointF(xr_nw, yt_nw)),
                            self.nwell_layer))

        # ThickGateOx layer for HV operation
        tp = baseCell._techParams
        tgo_over = tp["TGO_a"]  # ThickGateOx enclosure over active
        tgo_point1 = self.toSceneCoord(QPointF(-tgo_over, -tgo_over))
        tgo_point2 = self.toSceneCoord(QPointF(W + tgo_over, hact + tgo_over))
        tempShapesList.append(
            lshp.layoutRect(tgo_point1, tgo_point2, self.tgo_layer))

        # Inscription
        tempShapesList.append(lshp.layoutLabel(self.toSceneCoord(
            QPointF((xl + xr) / 2, yt - rf_params['wguard'] / 2)),
            self.__class__.__name__,
            *self._labelFontTuple,
            lshp.layoutLabel.LABEL_ALIGNMENTS[0],
            lshp.layoutLabel.LABEL_ORIENTS[0],
            self.text_layer))

        # Move to origin
        move_point = self.toSceneCoord(QPointF(-xl, -yb))
        for shape in tempShapesList:
            if isinstance(shape,
                          (lshp.layoutRect, lshp.layoutPin, lshp.layoutLabel)):
                shape.moveBy(move_point.x(), move_point.y())

        self.shapes = tempShapesList
