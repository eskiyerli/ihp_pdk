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
from .base import baseMosfet, baseCell
from .mosfet import nmos, pmos

laylyr = importPDKModule('layoutLayers')


class nmosHV(nmos):
    """High-voltage NMOS transistor - extends standard NMOS with ThickGateOx layer."""

    tgo_layer = laylyr.ThickGateOx_drawing

    @staticmethod
    @lru_cache(maxsize=1)
    def _get_nmosHV_params():
        """Cache for NMOSHV technology parameters."""
        tp = baseCell._techParams
        return {
            "defL": Quantity(tp["nmosHV_defL"]).real,
            "defW": Quantity(tp["nmosHV_defW"]).real,
            "defNG": Quantity(tp["nmosHV_defNG"]).real,
            "minL": Quantity(tp["nmosHV_minL"]).real,
            "minW": Quantity(tp["nmosHV_minW"]).real,
        }

    def __init__(self, width: str = "4u", length: str = "0.72u", ng: str = "1"):
        params = self._get_nmosHV_params()
        self.width = Quantity(width).real if width else params["defW"]
        self.length = Quantity(length).real if length else params["defL"]
        self.ng = int(float(ng)) if ng else params["defNG"]
        super(nmos, self).__init__([])

    @lru_cache
    def __call__(self, width: str, length: str, ng: str):
        tempShapesList = []
        device_params = self._get_nmosHV_params()
        common_params = self._get_common_params()

        self.width = Quantity(width).real if width else device_params["defW"]
        self.length = Quantity(length).real if length else device_params["defL"]
        self.ng = int(float(ng)) if ng else device_params["defNG"]

        wf = self.width * 1e6 / self.ng
        l = self.length * 1e6

        # Calculate contact parameters
        contActMin, ncont, diff_cont_offset, diffoffset = self._calculate_contact_params(wf,
                                                                                         common_params)

        # Adjust gate-contact distance for small widths
        gatpoly_cont_dist = common_params["gatpoly_cont_dist"]
        if wf < contActMin - common_params["epsilon"]:
            gatpoly_cont_dist = common_params["smallw_gatpoly_cont_dist"]

        # Basic dimensions
        xdiff_beg, ydiff_beg, ydiff_end = 0, 0, wf
        xcont_beg = xdiff_beg + common_params["cont_Activ_overRec"]
        ycont_beg = ydiff_beg + common_params["cont_Activ_overRec"]
        xcont_end = xcont_beg + common_params["cont_size"]

        # Metal coverage
        endcap = max(common_params["endcap"], common_params["cont_metall_over"])
        distc = common_params["cont_size"] + common_params["cont_dist"]
        ycont_cnt = ycont_beg + diffoffset + diff_cont_offset
        yMet1 = min(ycont_cnt - endcap, ydiff_beg + diffoffset)
        yMet2 = max(ycont_cnt + common_params["cont_size"] + (ncont - 1) * distc + endcap,
                    ydiff_end + diffoffset)

        # Draw source contact and diffusion
        self._draw_metal_and_contacts(tempShapesList, xcont_beg, xcont_end, yMet1, yMet2,
                                      ydiff_beg, ydiff_end, diffoffset, "S", common_params)
        self._draw_diffusion_rect(tempShapesList, xcont_beg, ycont_beg, xcont_end,
                                  common_params["cont_size"],
                                  common_params["cont_Activ_overRec"], self.ndiff_layer)

        # Draw gates and drain contacts
        for i in range(1, self.ng + 1):
            # Gate poly
            xpoly_beg = xcont_end + gatpoly_cont_dist
            ypoly_beg = ydiff_beg - common_params["gatpoly_Activ_over"]
            xpoly_end = xpoly_beg + l
            ypoly_end = ydiff_end + common_params["gatpoly_Activ_over"]

            self._draw_gate_poly(tempShapesList, xpoly_beg, ypoly_beg, xpoly_end, ypoly_end,
                                 diffoffset, i == 1)

            # Drain contact
            xcont_beg = xpoly_end + gatpoly_cont_dist
            xcont_end = xcont_beg + common_params["cont_size"]

            self._draw_metal_and_contacts(tempShapesList, xcont_beg, xcont_end, yMet1,
                                          yMet2,
                                          ydiff_beg, ydiff_end, diffoffset,
                                          "D" if i == 1 else "", common_params)
            self._draw_diffusion_rect(tempShapesList, xcont_beg, ycont_beg, xcont_end,
                                      common_params["cont_size"],
                                      common_params["cont_Activ_overRec"], self.ndiff_layer)

        # Final diffusion layer
        xdiff_end = xcont_end + common_params["cont_Activ_overRec"]
        point1 = self.toSceneCoord(QPointF(xdiff_beg, ydiff_beg + diffoffset))
        point2 = self.toSceneCoord(QPointF(xdiff_end, ydiff_end + diffoffset))
        tempShapesList.append(lshp.layoutRect(point1, point2, self.ndiff_layer))

        # Add ThickGateOx layer (original: no diffoffset applied to TGO)
        tp = baseCell._techParams
        tgo_gate_over = tp["TGO_c"]  # ThickGateOx over GatPoly
        tgo_activ_over = tp["TGO_a"]  # ThickGateOx over Active

        tgo_point1 = self.toSceneCoord(QPointF(
            xdiff_beg - tgo_activ_over,
            ydiff_beg - common_params["gatpoly_Activ_over"] - tgo_gate_over))
        tgo_point2 = self.toSceneCoord(QPointF(
            xdiff_end + tgo_activ_over,
            ydiff_end + common_params["gatpoly_Activ_over"] + tgo_gate_over))
        tempShapesList.append(lshp.layoutRect(tgo_point1, tgo_point2, self.tgo_layer))

        self.shapes = tempShapesList


class pmosHV(pmos):
    """High-voltage PMOS transistor - extends standard PMOS with ThickGateOx layer."""

    tgo_layer = laylyr.ThickGateOx_drawing

    @staticmethod
    @lru_cache(maxsize=1)
    def _get_pmosHV_params():
        """Cache for PMOSHV technology parameters."""
        tp = baseCell._techParams
        return {
            "defL": Quantity(tp["pmosHV_defL"]).real,
            "defW": Quantity(tp["pmosHV_defW"]).real,
            "defNG": Quantity(tp["pmosHV_defNG"]).real,
            "minL": Quantity(tp["pmosHV_minL"]).real,
            "minW": Quantity(tp["pmosHV_minW"]).real,
            "psd_pActiv_over": tp["pSD_c"],
            "nwell_pActiv_over": tp["NW_c"],
            "smallw_gatpoly_cont_dist": tp["Cnt_c"] + tp["Gat_d"],
            "psd_PFET_over": tp["pSD_i"],
        }

    def __init__(self, width: str = "4u", length: str = "0.72u", ng: str = "1"):
        params = self._get_pmosHV_params()
        self.width = Quantity(width).real if width else params["defW"]
        self.length = Quantity(length).real if length else params["defL"]
        self.ng = int(float(ng)) if ng else params["defNG"]
        super(pmos, self).__init__([])

    @lru_cache
    def __call__(self, width: str, length: str, ng: str):
        tempShapesList = []
        device_params = self._get_pmosHV_params()
        common_params = self._get_common_params()

        self.width = Quantity(width).real if width else device_params["defW"]
        self.length = Quantity(length).real if length else device_params["defL"]
        self.ng = int(float(ng)) if ng else device_params["defNG"]

        wf = self.width * 1e6 / self.ng
        l = self.length * 1e6

        # Calculate contact parameters
        contActMin, ncont, diff_cont_offset, diffoffset = self._calculate_contact_params(wf,
                                                                                         common_params)

        # Adjust gate-contact distance for small widths
        gatpoly_cont_dist = common_params["gatpoly_cont_dist"]
        if wf < contActMin - common_params["epsilon"]:
            gatpoly_cont_dist = device_params["smallw_gatpoly_cont_dist"]

        # Basic dimensions
        xdiff_beg, ydiff_beg, ydiff_end = 0, 0, wf
        xcont_beg = xdiff_beg + common_params["cont_Activ_overRec"]
        ycont_beg = ydiff_beg + common_params["cont_Activ_overRec"]
        xcont_end = xcont_beg + common_params["cont_size"]

        # Metal coverage
        endcap = max(common_params["endcap"], common_params["cont_metall_over"])
        distc = common_params["cont_size"] + common_params["cont_dist"]
        ycont_cnt = ycont_beg + diffoffset + diff_cont_offset
        yMet1 = min(ycont_cnt - endcap, ydiff_beg + diffoffset)
        yMet2 = max(ycont_cnt + common_params["cont_size"] + (ncont - 1) * distc + endcap,
                    ydiff_end + diffoffset)

        # Draw source contact and diffusion
        self._draw_metal_and_contacts(tempShapesList, xcont_beg, xcont_end, yMet1, yMet2,
                                      ydiff_beg, ydiff_end, diffoffset, "S", common_params)
        self._draw_diffusion_rect(tempShapesList, xcont_beg, ycont_beg, xcont_end,
                                  common_params["cont_size"],
                                  common_params["cont_Activ_overRec"], self.pdiff_layer)

        # Draw gates and drain contacts
        for i in range(1, self.ng + 1):
            # Gate poly
            xpoly_beg = xcont_end + gatpoly_cont_dist
            ypoly_beg = ydiff_beg - common_params["gatpoly_Activ_over"]
            xpoly_end = xpoly_beg + l
            ypoly_end = ydiff_end + common_params["gatpoly_Activ_over"]

            point1 = self.toSceneCoord(QPointF(xpoly_beg, ypoly_beg + diffoffset))
            point2 = self.toSceneCoord(QPointF(xpoly_end, ypoly_end + diffoffset))
            tempShapesList.append(lshp.layoutRect(point1, point2, self.gatpoly_layer))
            tempShapesList.extend(
                self.ihpAddThermalMosLayer(point1, point2, True, self.__class__.__name__))

            if i == 1:
                center = QRectF(point1, point2).center()
                tempShapesList.append(
                    lshp.layoutPin(point1, point2, "G", lshp.layoutPin.pinDirs[2],
                                   lshp.layoutPin.pinTypes[0], self.poly_layer_pin))
                tempShapesList.append(lshp.layoutLabel(center, "G", *self._labelFontTuple,
                                                       lshp.layoutLabel.LABEL_ALIGNMENTS[0],
                                                       lshp.layoutLabel.LABEL_ORIENTS[0],
                                                       self.text_layer))

            # Drain contact
            xcont_beg = xpoly_end + gatpoly_cont_dist
            xcont_end = xcont_beg + common_params["cont_size"]

            self._draw_metal_and_contacts(tempShapesList, xcont_beg, xcont_end, yMet1,
                                          yMet2,
                                          ydiff_beg, ydiff_end, diffoffset,
                                          "D" if i == 1 else "", common_params)
            self._draw_diffusion_rect(tempShapesList, xcont_beg, ycont_beg, xcont_end,
                                      common_params["cont_size"],
                                      common_params["cont_Activ_overRec"], self.pdiff_layer)

        # Final layers
        xdiff_end = xcont_end + common_params["cont_Activ_overRec"]

        # Main diffusion
        point1 = self.toSceneCoord(QPointF(xdiff_beg, ydiff_beg + diffoffset))
        point2 = self.toSceneCoord(QPointF(xdiff_end, ydiff_end + diffoffset))
        tempShapesList.append(lshp.layoutRect(point1, point2, self.pdiff_layer))

        # pSD layer
        point1 = self.toSceneCoord(QPointF(xdiff_beg - device_params["psd_pActiv_over"],
                                           ydiff_beg - common_params["gatpoly_Activ_over"] -
                                           device_params["psd_PFET_over"] + diffoffset))
        point2 = self.toSceneCoord(QPointF(xdiff_end + device_params["psd_pActiv_over"],
                                           ydiff_end + common_params["gatpoly_Activ_over"] +
                                           device_params["psd_PFET_over"] + diffoffset))
        tempShapesList.append(lshp.layoutRect(point1, point2, self.pdiffx_layer))

        # NWell layer
        nwell_offset = max(0, self.GridFix((contActMin - wf) / 2 + self._sg13grid / 2))
        point1 = self.toSceneCoord(QPointF(xdiff_beg - device_params["nwell_pActiv_over"],
                                           ydiff_beg - device_params[
                                               "nwell_pActiv_over"] + diffoffset - nwell_offset))
        point2 = self.toSceneCoord(QPointF(xdiff_end + device_params["nwell_pActiv_over"],
                                           ydiff_end + device_params[
                                               "nwell_pActiv_over"] + diffoffset + nwell_offset))
        tempShapesList.append(lshp.layoutRect(point1, point2, self.well_layer))

        # Add ThickGateOx layer
        tp = baseCell._techParams
        tgo_gate_over = tp["TGO_c"]  # Overlay over GatPoly
        tgo_activ_over = tp["TGO_a"]  # Overlay over Active

        # ThickGateOx extents determined by active + nwell enclosure
        tgo_x1 = xdiff_beg - tgo_activ_over
        tgo_x2 = xdiff_end + tgo_activ_over
        tgo_y1 = ydiff_beg - common_params["gatpoly_Activ_over"] - tgo_gate_over
        tgo_y2 = ydiff_end + common_params["gatpoly_Activ_over"] + tgo_gate_over

        # Original: if NWell extends further than TGO, use NWell extents
        nwell_pActiv_over = device_params["nwell_pActiv_over"]
        if nwell_pActiv_over > tgo_activ_over:
            tgo_x1 = xdiff_beg - nwell_pActiv_over
            tgo_x2 = xdiff_end + nwell_pActiv_over
        if (nwell_pActiv_over + diffoffset - nwell_offset) > (common_params["gatpoly_Activ_over"] - tgo_gate_over):
            tgo_y1 = ydiff_beg - nwell_pActiv_over + diffoffset - nwell_offset
            tgo_y2 = ydiff_end + nwell_pActiv_over + diffoffset + nwell_offset

        tgo_point1 = self.toSceneCoord(QPointF(tgo_x1, tgo_y1))
        tgo_point2 = self.toSceneCoord(QPointF(tgo_x2, tgo_y2))
        tempShapesList.append(lshp.layoutRect(tgo_point1, tgo_point2, self.tgo_layer))

        self.shapes = tempShapesList
