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

from PySide6.QtCore import QPoint, QPointF, QRectF
from PySide6.QtGui import (QFont, QFontDatabase)
from quantiphy import Quantity

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.common.layoutShapes as lshp
from revedaEditor.backend.pdkLoader import importPDKModule

sg13_tech = importPDKModule('sg13_tech')
laylyr = importPDKModule('layoutLayers')
fabproc = importPDKModule('process')


class baseCell(lshp.layoutPcell):
    """
    Base class for all layout parametric cells.
    """

    techClass = sg13_tech.SG13_Tech()
    _techParams = techClass.techParams
    _sg13grid = Quantity(_techParams["grid"]).real
    _epsilon = _techParams["epsilon1"]
    heatTransLayer = laylyr.HeatTrans_drawing

    @classmethod
    def GridFix(cls, x):
        return cls.fix(x / cls._sg13grid + cls._epsilon) * cls._sg13grid

    @staticmethod
    def fix(value):
        if isinstance(value, float):
            return int(math.floor(value))
        else:
            return value

    def __init__(self, shapes=list):
        super().__init__(shapes)
        fontFamilies = QFontDatabase().families()
        fontFamily = \
            [font for font in fontFamilies if QFontDatabase().isFixedPitch(font)][0]
        self._fixedFont = QFont(fontFamily, 16)
        self._labelFontStyle = self._fixedFont.styleName()
        self._labelFontFamily = self._fixedFont.family()
        self._labelFontSize = self._fixedFont.pointSize()
        self._labelFontTuple = (self._labelFontFamily, self._labelFontStyle,
                                self._labelFontSize,)

    @staticmethod
    def oddp(value):
        """
        Returns True if value is odd, False if value is even.
        """
        return bool(value & 1)

    # ***********************************************************************************************************************
    # contactArray
    # ***********************************************************************************************************************
    def contactArray(self, pathLayer: ddef.layLayer | int,
                     contLayer: ddef.layLayer, xl, yl, xh, yh, ox, oy, ws, ds, ):
        w, h = xh - xl, yh - yl
        mlist = []

        nx = int(math.floor((w - ox * 2 + ds) / (ws + ds) + self._epsilon))
        ny = int(math.floor((h - oy * 2 + ds) / (ws + ds) + self._epsilon))

        if nx <= 0 or ny <= 0:
            return mlist

        # Calculate spacing and starting positions
        dsx = 0 if nx == 1 else (w - ox * 2 - ws * nx) / (nx - 1)
        dsy = 0 if ny == 1 else (h - oy * 2 - ws * ny) / (ny - 1)
        x_start = (w - ws) / 2 if nx == 1 else ox
        y_start = (h - ws) / 2 if ny == 1 else oy

        # Add path layer once if needed
        if pathLayer:
            point1 = self.toSceneCoord(QPointF(xl, yl))
            point2 = self.toSceneCoord(QPointF(xh, yh))
            mlist.append(lshp.layoutRect(point1, point2, pathLayer))

        # Generate contact array
        x = x_start
        for i in range(nx):
            y = y_start
            for j in range(ny):
                x_fixed, y_fixed = self.GridFix(x), self.GridFix(y)
                point1 = self.toSceneCoord(QPointF(xl + x_fixed, yl + y_fixed))
                point2 = self.toSceneCoord(
                    QPointF(xl + x_fixed + ws, yl + y_fixed + ws))
                mlist.append(lshp.layoutRect(point1, point2, contLayer))
                y += ws + dsy
            x += ws + dsx

        return mlist

    def ihpAddThermalLayer(self, heatLayer: ddef.layLayer, point1: QPoint,
                           point2: QPoint, addThermalText: bool, labelText: str):
        shapes = [lshp.layoutRect(point1, point2, heatLayer)]
        if addThermalText:
            shapes.append(
                lshp.layoutLabel(QRectF(point1, point2).center(), labelText,
                                 *self._labelFontTuple,
                                 lshp.layoutLabel.LABEL_ALIGNMENTS[0],
                                 lshp.layoutLabel.LABEL_ORIENTS[0], heatLayer, ))
        return shapes

    def ihpAddThermalMosLayer(self, point1, point2, addThermalText, label):
        return (self.ihpAddThermalLayer(baseCell.heatTransLayer, point1, point2,
                                        addThermalText, label))

    @staticmethod
    def toLayoutCoord(point: QPoint) -> QPointF:
        """
        Converts a point in scene coordinates to layout coordinates by dividing it to
        fabproc.dbu.
        """
        point /= fabproc.dbu
        return point.toPointF()

    @staticmethod
    def toSceneCoord(point: QPointF) -> QPoint:
        """
        Converts a point in layout coordinates to scene coordinates by multiplying it with
        fabproc.dbu.
        """
        point *= fabproc.dbu
        return point.toPoint()

    @staticmethod
    def toSceneDimension(value: float) -> int:
        """
        Converts a floating-point value to an integer scene dimension.

        This method takes a floating-point value representing a physical dimension
        and converts it to an integer value suitable for use in the layout design
        or rendering process. The conversion is performed by scaling the input value
        by the database unit (dbu) resolution used in the semiconductor fabrication
        process.

        Args:
            value (float): The floating-point value to be converted.

        Returns:
            int: The converted integer scene dimension.
        """
        return int(value * fabproc.dbu)

    @staticmethod
    def toLayoutDimension(value: int) -> float:
        return value / fabproc.dbu


class baseMosfet(baseCell):
    """Base class for all MOSFET devices to eliminate code duplication."""

    # Common layers - to be overridden by subclasses
    metal1_layer = laylyr.Metal1_drawing
    metal1_layer_pin = laylyr.Metal1_pin
    metal1_layer_label = laylyr.Metal1_text
    activ_layer = laylyr.Activ_drawing
    gatpoly_layer = laylyr.GatPoly_drawing
    cont_layer = laylyr.Cont_drawing
    text_layer = laylyr.TEXT_drawing
    locint_layer = laylyr.Cont_drawing

    def _get_common_params(self):
        """Get common MOSFET parameters."""
        tp = baseCell._techParams
        return {"epsilon": tp["epsilon1"], "endcap": tp["M1_c1"],
                "cont_size": tp["Cnt_a"], "cont_dist": tp["Cnt_b"],
                "cont_Activ_overRec": tp["Cnt_c"], "cont_metall_over": tp["M1_c"],
                "gatpoly_Activ_over": tp["Gat_c"], "gatpoly_cont_dist": tp["Cnt_f"],
                "smallw_gatpoly_cont_dist": tp["Cnt_c"], }

    def _calculate_contact_params(self, wf, params):
        """Calculate contact-related parameters."""
        epsilon = params["epsilon"]
        cont_size = params["cont_size"]
        cont_dist = params["cont_dist"]
        cont_Activ_overRec = params["cont_Activ_overRec"]

        contActMin = self.GridFix(2 * cont_Activ_overRec + cont_size)

        # Calculate number of contacts
        distc = cont_size + cont_dist
        ncont = self.fix(
            (wf - 2 * cont_Activ_overRec + cont_dist) / distc + epsilon)
        if ncont == 0:
            ncont = 1

        diff_cont_offset = self.GridFix((
                                                wf - 2 * cont_Activ_overRec - ncont * cont_size - (
                                                ncont - 1) * cont_dist) / 2)

        diffoffset = 0
        if wf < contActMin:
            diffoffset = self.GridFix((contActMin - wf) / 2)

        return contActMin, ncont, diff_cont_offset, diffoffset

    def _draw_metal_and_contacts(self, shapes_list, xcont_beg, xcont_end, yMet1,
                                 yMet2, ydiff_beg, ydiff_end, diffoffset,
                                 pin_name, params):
        """Draw metal rectangle and contacts."""
        cont_metall_over = params["cont_metall_over"]
        cont_Activ_overRec = params["cont_Activ_overRec"]
        cont_size = params["cont_size"]
        cont_dist = params["cont_dist"]

        # Metal rectangle
        point1 = self.toSceneCoord(QPointF(xcont_beg - cont_metall_over, yMet1))
        point2 = self.toSceneCoord(QPointF(xcont_end + cont_metall_over, yMet2))
        shapes_list.append(lshp.layoutRect(point1, point2, self.metal1_layer))

        # Contacts
        shapes_list.extend(
            self.contactArray(0, self.locint_layer, xcont_beg, ydiff_beg,
                              xcont_end, ydiff_end + diffoffset * 2, 0,
                              cont_Activ_overRec, cont_size, cont_dist))

        # Pin and label
        center = QRectF(point1, point2).center()
        shapes_list.append(
            lshp.layoutPin(point1, point2, pin_name, lshp.layoutPin.pinDirs[2],
                           lshp.layoutPin.pinTypes[0], self.metal1_layer_pin))
        shapes_list.append(
            lshp.layoutLabel(center, pin_name, *self._labelFontTuple,
                             lshp.layoutLabel.LABEL_ALIGNMENTS[0],
                             lshp.layoutLabel.LABEL_ORIENTS[0],
                             self.metal1_layer_label))

    def _draw_gate_poly(self, shapes_list, xpoly_beg, ypoly_beg, xpoly_end,
                        ypoly_end, diffoffset, is_first_gate=False):
        """Draw gate polysilicon."""
        point1 = self.toSceneCoord(QPointF(xpoly_beg, ypoly_beg + diffoffset))
        point2 = self.toSceneCoord(QPointF(xpoly_end, ypoly_end + diffoffset))
        shapes_list.append(lshp.layoutRect(point1, point2, self.gatpoly_layer))
        shapes_list.extend(self.ihpAddThermalMosLayer(point1, point2, True,
                                                      self.__class__.__name__))

        if is_first_gate:
            center = QRectF(point1, point2).center()
            shapes_list.append(
                lshp.layoutPin(point1, point2, "G", lshp.layoutPin.pinDirs[2],
                               lshp.layoutPin.pinTypes[0], self.metal1_layer_pin))
            shapes_list.append(
                lshp.layoutLabel(center.toPoint(), "G", *self._labelFontTuple,
                                 lshp.layoutLabel.LABEL_ALIGNMENTS[0],
                                 lshp.layoutLabel.LABEL_ORIENTS[0],
                                 self.metal1_layer_label))

    def _draw_diffusion_rect(self, shapes_list, xcont_beg, ycont_beg, xcont_end,
                             cont_size, cont_Activ_overRec, layer):
        """Draw diffusion rectangle."""
        point1 = self.toSceneCoord(QPointF(xcont_beg - cont_Activ_overRec,
                                           ycont_beg - cont_Activ_overRec))
        point2 = self.toSceneCoord(QPointF(xcont_end + cont_Activ_overRec,
                                           ycont_beg + cont_size + cont_Activ_overRec))
        shapes_list.append(lshp.layoutRect(point1, point2, layer))


class baseRfMosfet(baseCell):
    """Base class for RF MOSFET devices to eliminate code duplication."""

    # Common layers - to be overridden by subclasses
    activ_layer = laylyr.Activ_drawing
    gatpoly_layer = laylyr.GatPoly_drawing
    cont_layer = laylyr.Cont_drawing
    metal1_layer = laylyr.Metal1_drawing
    metal2_layer = laylyr.Metal2_drawing
    via1_layer = laylyr.Via1_drawing
    text_layer = laylyr.TEXT_drawing
    metal1_pin = laylyr.Metal1_pin

    def _get_rf_common_params(self, W, L, ng, cnt_rows):
        """Get common RF MOSFET parameters."""
        tp = baseCell._techParams
        return {'wc': tp['Cnt_a'], 'sc': tp['Cnt_b'], 'ec': tp['Cnt_c'],
                'dc': tp['Cnt_f'], 'wvia1': tp['TV1_a'], 'svia1': tp['TV1_b'],
                'dvia1': tp['TV1_d'], 'wgat': tp['Gat_a'], 'dgatx': tp['Gat_d'],
                'dgaty': tp['Gat_c'], 'wguard': tp['pSD_a'], 'dguard': tp['pSD_b'],
                'wcont': W,
                'hcont': (tp['Cnt_a'] * cnt_rows) + (tp['Cnt_b'] * (cnt_rows - 1)), }

    def _draw_rf_active_and_gates(self, shapes_list, W, hact, ng, params):
        """Draw RF active area and gates."""
        # Active area
        point1 = self.toSceneCoord(QPointF(0, 0))
        point2 = self.toSceneCoord(QPointF(W, hact))
        shapes_list.append(lshp.layoutRect(point1, point2, self.activ_layer))
        y = 0
        # Gates
        for i in range(ng):
            y = params['ec'] + i * (params['L'] + params['dc'])
            point1 = self.toSceneCoord(QPointF(0, y))
            point2 = self.toSceneCoord(QPointF(W, y + params['L']))
            shapes_list.append(
                lshp.layoutRect(point1, point2, self.gatpoly_layer))
        return y + params['L']

    def _draw_rf_source_drain_contacts(self, shapes_list, W, ng, params, useMet2):
        """Draw RF source/drain contacts."""
        for i in range(ng + 1):
            y = i * (params['L'] + params['dc'])
            h = params['ec'] if (i == 0 or i == ng) else params['dc']

            # Metal1
            point1 = self.toSceneCoord(QPointF(0, y))
            point2 = self.toSceneCoord(QPointF(W, y + h))
            shapes_list.append(lshp.layoutRect(point1, point2, self.metal1_layer))

            # Contacts
            shapes_list.extend(
                self.contactArray(0, self.cont_layer, 0, y, W, y + h,
                                  params['ec'], params['ec'], params['wc'],
                                  params['sc']))

            # Vias and Metal2 if enabled
            if useMet2:
                shapes_list.append(
                    lshp.layoutRect(point1, point2, self.metal2_layer))
                shapes_list.extend(
                    self.contactArray(0, self.via1_layer, 0, y, W, y + h,
                                      params['dvia1'], params['dvia1'],
                                      params['wvia1'], params['svia1']))

    def _draw_rf_pins(self, shapes_list, W, params):
        """Draw RF pins."""
        # Source pin
        point1_s = self.toSceneCoord(QPointF(0, 0))
        point2_s = self.toSceneCoord(QPointF(W, params['ec']))
        shapes_list.append(
            lshp.layoutPin(point1_s, point2_s, "S", lshp.layoutPin.pinDirs[2],
                           lshp.layoutPin.pinTypes[0], self.metal1_pin))

        # Drain pin
        y_d = params['ec'] + params['L']
        point1_d = self.toSceneCoord(QPointF(0, y_d))
        point2_d = self.toSceneCoord(QPointF(W, y_d + params['dc']))
        shapes_list.append(
            lshp.layoutPin(point1_d, point2_d, "D", lshp.layoutPin.pinDirs[2],
                           lshp.layoutPin.pinTypes[0], self.metal1_pin))

    def _draw_rf_gate_ring_and_contacts(self, shapes_list, W, hact, params,
                                        gat_ring: bool, u):
        """Draw RF gate ring and contacts."""
        if not gat_ring:
            return

        xl, xr = -params['dgatx'] - params['wgat'], W + params['dgatx']
        yb, yt = -params['dgaty'] - params['wgat'], hact + params['dgaty']

        # Gate ring
        shapes_list.append(lshp.layoutRect(self.toSceneCoord(QPointF(xl, yb)),
                                           self.toSceneCoord(
                                               QPointF(xr + params['wgat'],
                                                       yb + params['wgat'])),
                                           self.gatpoly_layer))
        shapes_list.append(lshp.layoutRect(self.toSceneCoord(QPointF(xl, yt)),
                                           self.toSceneCoord(
                                               QPointF(xr + params['wgat'],
                                                       yt + params['wgat'])),
                                           self.gatpoly_layer))
        shapes_list.append(lshp.layoutRect(self.toSceneCoord(QPointF(xl, yb)),
                                           self.toSceneCoord(
                                               QPointF(xl + params['wgat'],
                                                       yt + params['wgat'])),
                                           self.gatpoly_layer))
        shapes_list.append(lshp.layoutRect(self.toSceneCoord(QPointF(xr, yb)),
                                           self.toSceneCoord(
                                               QPointF(xr + params['wgat'],
                                                       yt + params['wgat'])),
                                           self.gatpoly_layer))

        # Gate contacts
        x = (xl + xr + params['wgat']) / 2 - params['wc'] / 2
        y = yb - params['ec'] - params['wc']
        shapes_list.extend(
            self.contactArray(self.metal1_layer, self.cont_layer, x, y,
                              x + params['wc'], y + params['wc'], params['ec'],
                              params['ec'], params['wc'], params['sc']))

        # Gate pin
        point1_g = self.toSceneCoord(QPointF(x, y))
        point2_g = self.toSceneCoord(QPointF(x + params['wc'], y + params['wc']))
        shapes_list.append(
            lshp.layoutPin(point1_g, point2_g, "G", lshp.layoutPin.pinDirs[2],
                           lshp.layoutPin.pinTypes[0], self.metal1_pin))

    def _draw_rf_guard_ring(self, shapes_list, W, hact, params, guard_ring: bool):
        """Draw RF guard ring."""
        if not guard_ring:
            return 0, 0, 0, 0

        xl = -params['dgatx'] - params['wgat'] - params['dguard'] - params[
            'wguard']
        xr = W + params['dgatx'] + params['wgat'] + params['dguard'] + params[
            'wguard']
        yb = -params['dgaty'] - params['wgat'] - params['dguard'] - params[
            'wguard']
        yt = hact + params['dgaty'] + params['wgat'] + params['dguard'] + params[
            'wguard']

        # Guard ring active
        shapes_list.append(lshp.layoutRect(self.toSceneCoord(QPointF(xl, yb)),
                                           self.toSceneCoord(QPointF(xr,
                                                                     yb + params[
                                                                         'wguard'])),
                                           self.activ_layer))
        shapes_list.append(
            lshp.layoutRect(self.toSceneCoord(QPointF(xl, yt - params['wguard'])),
                            self.toSceneCoord(QPointF(xr, yt)), self.activ_layer))
        shapes_list.append(
            lshp.layoutRect(self.toSceneCoord(QPointF(xl, yb + params['wguard'])),
                            self.toSceneCoord(QPointF(xl + params['wguard'],
                                                      yt - params['wguard'])),
                            self.activ_layer))
        shapes_list.append(lshp.layoutRect(self.toSceneCoord(
            QPointF(xr - params['wguard'], yb + params['wguard'])),
            self.toSceneCoord(QPointF(xr,
                                      yt - params[
                                          'wguard'])),
            self.activ_layer))

        # Guard ring contacts
        shapes_list.extend(
            self.contactArray(self.metal1_layer, self.cont_layer, xl, yb, xr, yt,
                              params['ec'], params['ec'], params['wc'],
                              params['sc']))

        # Bulk pin
        point1_b = self.toSceneCoord(QPointF(xl, yb))
        point2_b = self.toSceneCoord(QPointF(xr, yt))
        shapes_list.append(
            lshp.layoutPin(point1_b, point2_b, "B", lshp.layoutPin.pinDirs[2],
                           lshp.layoutPin.pinTypes[0], self.metal1_pin))

        return xl, yb, xr, yt
