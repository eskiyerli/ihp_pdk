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
# distributed under laughable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
########################################################################

from functools import lru_cache

from PySide6.QtCore import QPointF
from quantiphy import Quantity

import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule
from .base import baseRfMosfet

laylyr = importPDKModule('layoutLayers')


class rfnmos(baseRfMosfet):
    @staticmethod
    @lru_cache(maxsize=1)
    def _get_rfnmos_params():
        """Cache for RFNMOS technology parameters."""
        tp = baseRfMosfet._techParams
        return {"defL": Quantity(tp["rfnmos_defL"]).real,
                "defW": Quantity(tp["rfnmos_defW"]).real,
                "defNG": Quantity(tp["rfnmos_defNG"]).real,
                "minL": Quantity(tp["rfnmos_minL"]).real,
                "minW": Quantity(tp["rfnmos_minW"]).real, }

    # RFNMOS-specific layers
    psd_layer = laylyr.pSD_drawing

    def __init__(self, width: str = "1u", length: str = "0.72u", ng: str = "1",
                 cnt_rows: str = "1", Met2Cont: str = "1", gat_ring: str = "1",
                 guard_ring: str = "1"):

        params = self._get_rfnmos_params()
        self.width = Quantity(width).real if width else params["defW"]
        self.length = Quantity(length).real if length else params["defL"]
        self.ng = int(float(ng)) if ng else params["defNG"]
        self.cnt_rows = int(float(cnt_rows)) if cnt_rows else 1
        self.Met2Cont = Met2Cont
        self.gat_ring = gat_ring
        self.guard_ring = guard_ring
        super().__init__([])

    def __call__(self, width: str, length: str, ng: str, cnt_rows: str,
                 Met2Cont: str, gat_ring: str, guard_ring: str):
        tempShapesList = []
        device_params = self._get_rfnmos_params()

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
            lshp.layoutLabel.LABEL_ALIGNMENTS[
                0],
            lshp.layoutLabel.LABEL_ORIENTS[0],
            self.text_layer))

        # pSD for rfnmos
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

        # Move to origin
        move_point = self.toSceneCoord(QPointF(-xl, -yb))
        for shape in tempShapesList:
            if isinstance(shape,
                          (lshp.layoutRect, lshp.layoutPin, lshp.layoutLabel)):
                shape.moveBy(move_point.x(), move_point.y())

        self.shapes = tempShapesList


class rfpmos(baseRfMosfet):
    @staticmethod
    @lru_cache(maxsize=1)
    def _get_rfpmos_params():
        """Cache for RFPMOS technology parameters."""
        tp = baseRfMosfet._techParams
        return {"defL": Quantity(tp["rfpmos_defL"]).real,
                "defW": Quantity(tp["rfpmos_defW"]).real,
                "defNG": Quantity(tp["rfpmos_defNG"]).real,
                "minL": Quantity(tp["rfpmos_minL"]).real,
                "minW": Quantity(tp["rfpmos_minW"]).real, }

    # RFPMOS-specific layers
    nsd_layer = laylyr.nSD_drawing
    nwell_layer = laylyr.NWell_drawing

    def __init__(self, width: str = "1u", length: str = "0.72u", ng: str = "1",
                 cnt_rows: str = "1", Met2Cont: str = "1", gat_ring: str = "1",
                 guard_ring: str = "1"):

        params = self._get_rfpmos_params()
        self.width = Quantity(width).real if width else params["defW"]
        self.length = Quantity(length).real if length else params["defL"]
        self.ng = int(float(ng)) if ng else params["defNG"]
        self.cnt_rows = int(float(cnt_rows)) if cnt_rows else 1
        self.Met2Cont = Met2Cont
        self.gat_ring = gat_ring
        self.guard_ring = guard_ring
        super().__init__([])

    @lru_cache
    def __call__(self, width: str, length: str, ng: str, cnt_rows: str,
                 Met2Cont: str, gat_ring: str, guard_ring: str):
        tempShapesList = []
        device_params = self._get_rfpmos_params()

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

        # nSD for rfpmos guardring
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

        # NWell for rfpmos
        dnw = 0.38
        xl_nw, xr_nw = -rf_params['dgatx'] - rf_params['wgat'] - dnw, W + \
                       rf_params['dgatx'] + rf_params['wgat'] + dnw
        yb_nw, yt_nw = -rf_params['dgaty'] - rf_params['wgat'] - dnw, hact + \
                       rf_params['dgaty'] + rf_params['wgat'] + dnw
        tempShapesList.append(
            lshp.layoutRect(self.toSceneCoord(QPointF(xl_nw, yb_nw)),
                            self.toSceneCoord(QPointF(xr_nw, yt_nw)),
                            self.nwell_layer))

        # Inscription
        tempShapesList.append(lshp.layoutLabel(self.toSceneCoord(
            QPointF((xl + xr) / 2, yt - rf_params['wguard'] / 2)),
            self.__class__.__name__,
            *self._labelFontTuple,
            lshp.layoutLabel.LABEL_ALIGNMENTS[
                0],
            lshp.layoutLabel.LABEL_ORIENTS[0],
            self.text_layer))

        # Move to origin
        move_point = self.toSceneCoord(QPointF(-xl, -yb))
        for shape in tempShapesList:
            if isinstance(shape,
                          (lshp.layoutRect, lshp.layoutPin, lshp.layoutLabel)):
                shape.moveBy(move_point.x(), move_point.y())

        self.shapes = tempShapesList
