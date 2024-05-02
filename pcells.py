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

# This file contains the implementation of the IHP PDK in Revolution EDA.
# Therefore, it complies with the license assigned by the IHP.

import math
import os

from PySide6.QtCore import (QPoint, QPointF, QRectF)
from PySide6.QtGui import (QFontDatabase, QFont,)
from dotenv import load_dotenv

load_dotenv()

if os.environ.get("REVEDA_PDK_PATH"):
    import pdk.layoutLayers as laylyr
    import pdk.process as fabproc
else:
    import defaultPdk.layoutLayers as laylyr
    import defaultPdk.process as fabproc

import revedaEditor.common.layoutShapes as lshp
import revedaEditor.backend.dataDefinitions as ddef
from pdk.sg13_tech import SG13_Tech as sg13
from quantiphy import Quantity


class baseCell(lshp.layoutPcell):
    """
    Base class for all layout parametric cells.
    """


    def __init__(self, shapes=list):
        super().__init__(shapes)
        techClass = sg13()
        self._techParams = techClass.techParams
        self._sg13grid = Quantity(self._techParams['grid']).real
        self._epsilon = self._techParams["epsilon1"]
        fontFamilies = QFontDatabase().families()
        fontFamily = [font for font in fontFamilies if QFontDatabase().isFixedPitch(
            font)][0]
        self._fixedFont = QFont(fontFamily, 16)
        self._labelFontStyle = self._fixedFont.styleName()
        self._labelFontFamily = self._fixedFont.family()
        self._labelFontSize = self._fixedFont.pointSize()
        self._labelFontTuple = (self._labelFontFamily, self._labelFontStyle, self._labelFontSize)

    @staticmethod
    def fix(value):
        if type(value) == float:
            return int(math.floor(value))
        else:
            return value

    @staticmethod
    def oddp(value):
        '''
        Returns True if value is odd, False if value is even.
        '''
        return bool(value & 1)

    def GridFix(self,x):

        return self.fix(x / self._sg13grid + self._epsilon) * self._sg13grid

    def calcViaArray(self,via: lshp.layoutVia, rect: QRectF, xs: float, ys: float) -> (
            lshp.layoutViaArray):
        '''
        Find the xnum and ynum for layout Via array and return an layoutViaArray.
        '''
        print(f'rect width: {rect.width()}, via width: {via.width}')
        if rect.width() < via.width:
            xnum = 0
        else:
            xnum = math.floor((rect.width() - via.width )/(via.width+xs)) + 1

        if rect.height() < via.height:
            ynum = 0
        else:
            ynum = math.floor((rect.height() - via.height )/(via.height+ys)) + 1
        print(f'xnum: {xnum}, ynum: {ynum}')
        viaRectWidth = xnum * via.width + (xnum-1) * xs
        viaRectHeight = ynum * via.height + (ynum-1) * ys
        start = QPointF(rect.left()+(rect.width()-viaRectWidth)*0.5,
                                        rect.top()+(rect.height()-viaRectHeight)*0.5)
        return lshp.layoutViaArray(start, via, xs, ys, xnum, ynum)



    @staticmethod
    def toLayoutCoord(point: [QPoint]) -> QPointF:
        """
        Converts a point in scene coordinates to layout coordinates by dividing it to
        fabproc.dbu.
        """
        point /= fabproc.dbu
        return point.toPointF()

    @staticmethod
    def toSceneCoord(point: [QPointF]) -> QPoint:
        """
        Converts a point in layout coordinates to scene coordinates by multiplying it with
        fabproc.dbu.
        """
        point *= fabproc.dbu
        return point.toPoint()

    @staticmethod
    def toSceneDimension(value: float) -> float:
        return value*fabproc.dbu

    @staticmethod
    def toSceneDimension(value: float) -> int:
        return int(value*fabproc.dbu)

    def toLayoutDimension(self, value: int) -> float:
        return value/fabproc.dbu


class rsil(baseCell):
    def __init__(
        self,
        length: str = '4u' ,
        width: str = '1u',
        b: str = '1', # bends
        ps: str = '0.18u', # poly space
    ):
        self._shapes = []
        self.length = length
        self.width = width
        self.b = b
        self.ps = ps

        super().__init__(self._shapes)

    def __call__(self, length: str, width: str, b: str, ps: str):
        self.length = Quantity(length).real
        self.width = Quantity(width).real
        self.b = Quantity(b).real
        self.ps = Quantity(ps).real

        tempShapeList = []
        contpolylayer = laylyr.GatPoly_drw
        bodypolylayer = laylyr.PolyRes_drw
        reslayer = laylyr.RES_drw
        extBlocklayer = laylyr.EXTBlock_drw
        locintlayer = laylyr.Cont_drw
        metlayer = laylyr.Metal1_drw
        metlayer_pin = laylyr.Metal1_pin
        metlayer_lbl = laylyr.Metal1_lbl
        textlayer = laylyr.TEXT_drw
        Cell = self.__class__.__name__
        metover = self._techParams[Cell + '_met_over_cont']
        consize = self._techParams['Cnt_a']  # min and max size of Cont
        conspace = self._techParams['Cnt_b']  # min ContSpace
        polyover = self._techParams['Cnt_d']  # min GatPoly enclosure of Cont
        li_poly_over = self._techParams['Rsil_b']  # min RES Spacing to Cont
        ext_over = self._techParams['Rsil_e']  # min EXTBlock enclosure of RES
        endcap = self._techParams['M1_c1']
        poly_cont_len = li_poly_over + consize + polyover  # end of RES to end of poly
        contbar_poly_over = self._techParams['CntB_d']  # min length of LI-Bar
        contbar_min_len = self._techParams['CntB_a1']  # min length of LI-Bar

        wmin = Quantity(self._techParams[Cell + '_minW']).real * 1e6  # min Width
        lmin = Quantity(self._techParams[Cell + '_minL']).real * 1e6  # Min Length
        psmin = Quantity(self._techParams[Cell + '_minPS']).real * 1e6  # min PolySpace
        grid = self._sg13grid
        gridnumber = 0.0
        contoverlay = 0.0

        #dbReplaceProp(pcCV, 'pin#', 'int', 3)
        l = self.length*1e6
        w = self.width*1e6
        b = self.fix(self.b + self._epsilon)
        ps = self.ps*1e6
        wcontact = w
        drawbar = False
        internalCode = False

        if internalCode == True :
            if wcontact-2*contbar_poly_over + self._epsilon >= contbar_min_len :
                drawbar = True

        if metover < endcap :
            metover = endcap

        contoverlay = wcontact - w
        if contoverlay > 0:
            contoverlay = contoverlay / 2
            gridnumber = contoverlay / grid
            gridnumber = round(gridnumber + self._epsilon)
            if (gridnumber * grid * 100) < contoverlay:
                gridnumber += 1

            contoverlay = gridnumber*grid
            wcontact = w+2*contoverlay

        # insertion point is at (0,0) - contoverlay
        xpos1 = 0 - contoverlay
        ypos1 = 0
        xpos2 = xpos1 + wcontact
        ypos2 = 0
        Dir = -1
        stripes = b + 1
        if w < wmin - self._epsilon:
            w = wmin
            print('Width < ' + str(wmin))

        if l < lmin - self._epsilon:
            l = lmin
            print('Length < ' + str(lmin))

        if ps < psmin - self._epsilon:
            ps = psmin
            print('poly space < ' + str(psmin))

        # **************************************************************
        # draw res contact  #1 (bottom)
        # **************************************************************

        # set xpos1/xpos2 to left for contacts
        xpos1 = xpos1 - contoverlay
        xpos2 = xpos2 - contoverlay
        # Gat PolyPart of bottom ContactArea
        point1 = self.toSceneCoord(QPointF(xpos1, ypos1))
        point2 = self.toSceneCoord(QPointF(xpos2, ypos2 + poly_cont_len * Dir))
        tempShapeList.append(lshp.layoutRect(point1, point2, contpolylayer))
#        dbCreateRect(self, contpolylayer, Box(xpos1, ypos1, xpos2, ypos2 + poly_cont_len *
#        Dir))
        # number parallel conts: ncont, distance: distc:
        wcon = wcontact - 2.0 * polyover
        distc = consize + conspace
        ncont = self.fix((wcon + conspace) / distc + self._epsilon)
        if ncont < 1:
            ncont = 1

        distr = self.GridFix((wcon - ncont * distc + conspace) * 0.5)
        # **************************************************************
        # draw Cont squares or bars of bottom ContactArea
        # LI and Metal
        # always dot contacts, autogenerated LI
        if drawbar == True:
            point1 = self.toSceneCoord(QPointF(xpos1 + contbar_poly_over, ypos2 +
                                               li_poly_over * Dir))
            point2 = self.toSceneCoord(QPointF(xpos2 - contbar_poly_over, ypos2 +
                                               (consize + li_poly_over) * Dir))
            tempShapeList.append(lshp.layoutRect(point1, point2, locintlayer))
            # dbCreateRect(self, locintlayer,
            #              Box(xpos1 + contbar_poly_over, ypos2 + li_poly_over * Dir,
            #                  xpos2 - contbar_poly_over, ypos2 + (consize + li_poly_over) * Dir))
        else:
            for i in range(ncont):
                point1 = self.toSceneCoord(QPointF(xpos1 + polyover + distr + i * distc,
                                                    ypos2 + li_poly_over * Dir))
                point2 = self.toSceneCoord(QPointF(xpos1 + polyover + distr + i * distc + consize,
                                                    ypos2 + (consize + li_poly_over) * Dir))
                tempShapeList.append(lshp.layoutRect(point1, point2, locintlayer))
                # dbCreateRect(self, locintlayer, Box(xpos1 + polyover + distr + i * distc,
                #                                     ypos2 + li_poly_over * Dir,
                #                                     xpos1 + polyover + distr + i * distc + consize,
                #                                     ypos2 + (consize + li_poly_over) * Dir))
        # **************************************************************
        # draw MetalRect and Pin of bottom Contact Area
        ypos1 = ypos2 + (li_poly_over - metover) * Dir
        ypos2 = ypos2 + (consize + li_poly_over + metover) * Dir
        point1 = self.toSceneCoord(QPointF(xpos1 + contbar_poly_over - endcap, ypos1))
        point2 = self.toSceneCoord(QPointF(xpos2 - contbar_poly_over + endcap, ypos2))
        # dbCreateRect(self, metlayer, Box(xpos1 + contbar_poly_over - endcap, ypos1,
        #                                  xpos2 - contbar_poly_over + endcap, ypos2))
        tempShapeList.append(lshp.layoutRect(point1, point2, metlayer))
        # MkPin(self, 'PLUS', 1,
        #       Box(xpos1 + contbar_poly_over - endcap, ypos1, xpos2 - contbar_poly_over + endcap,
        #           ypos2), metlayer)
        centre = QRectF(point1,point2).center()
        tempShapeList.append(lshp.layoutPin(point1,point2, 'PLUS', lshp.layoutPin.pinDirs[2],
                                           lshp.layoutPin.pinTypes[0], metlayer_pin))
        tempShapeList.append(lshp.layoutLabel(centre, 'PLUS',
                                             *self._labelFontTuple,
                                             lshp.layoutLabel.labelAlignments[0],
                                             lshp.layoutLabel.labelOrients[0],
                                             metlayer_lbl))
        # **************************************************************
        # Resistorbody
        # **************************************************************
        Dir = 1
        # set xpos1 & xpos2 correct with contoverlay
        xpos1 = xpos1+contoverlay
        ypos1 = 0
        xpos2 = xpos1+w-contoverlay
        ypos2 = ypos1+l*Dir

        # **************************************************************
        # GatPoly and PolyRes
        # major structures ahead -> here: not applicable
        for i in range(1, int(stripes) + 1):
            xpos2 = xpos1 + w
            ypos2 = ypos1 + l * Dir
            # draw long res line
            # when dogbone and bends>0 shift long res line to inner contactline
            if stripes > 1:
                if i == 1:
                    # fist stripe move to right
                    xpos1 = xpos1 + contoverlay
                    xpos2 = xpos2 + contoverlay

            # all vertical ResPoly and GatPoly Parts
            point1 = self.toSceneCoord(QPointF(xpos1, ypos1))
            point2 = self.toSceneCoord(QPointF(xpos2, ypos2))
            tempShapeList.append(lshp.layoutRect(point1, point2, bodypolylayer))
            tempShapeList.append(lshp.layoutRect(point1, point2, reslayer))
            # dbCreateRect(self, bodypolylayer, Box(xpos1, ypos1, xpos2, ypos2))
            # dbCreateRect(self, reslayer, Box(xpos1, ypos1, xpos2, ypos2))
            # not yet implemented
            # ihpAddThermalResLayer(self, Box(xpos1, ypos1, xpos2, ypos2), True, Cell)
            # **************************************************************
            # EXTBlock
            if i == 1:
                point1 = self.toSceneCoord(QPointF(xpos1 - ext_over, ypos1))
                point2 = self.toSceneCoord(QPointF(xpos2 + ext_over, ypos2))
                tempShapeList.append(lshp.layoutRect(point1, point2, extBlocklayer))
                # dbCreateRect(self, extBlocklayer,
                #              Box(xpos1 - ext_over, ypos1, xpos2 + ext_over, ypos2))
            else:
                point1 = self.toSceneCoord(QPointF(xpos1 - ext_over, ypos1))
                point2 = self.toSceneCoord(QPointF(xpos2 + ext_over, ypos2))
                tempShapeList.append(lshp.layoutRect(point1, point2, extBlocklayer))
                # dbCreateRect(self, extBlocklayer,
                #              Box(xpos1 - ext_over, ypos1, xpos2 + ext_over, ypos2))

            # **************************************************************
            # hor connection parts
            if i < stripes : # Connections parts
                ypos1 = ypos2+w*Dir
                xpos2 = xpos1+2*w+ps
                ypos2 = ypos1-w*Dir
                Dir *= -1
                # draw res bend
                point1 = self.toSceneCoord(QPointF(xpos1,ypos1))
                point2 = self.toSceneCoord(QPointF(xpos2,ypos2))
                tempShapeList.append(lshp.layoutRect(point1, point2, bodypolylayer))
                tempShapeList.append(lshp.layoutRect(point1, point2, reslayer))
                # dbCreateRect(self, bodypolylayer, Box(xpos1, ypos1, xpos2, ypos2))
                # dbCreateRect(self, reslayer, Box(xpos1, ypos1, xpos2, ypos2))
                # decide in which direction the part is drawn
                if self.oddp(i):
                    point1 = self.toSceneCoord(QPointF(xpos1 - ext_over, ypos1 + ext_over))
                    point2 = self.toSceneCoord(QPointF(xpos2 + ext_over, ypos2 - ext_over))
                    tempShapeList.append(lshp.layoutRect(point1,point2,extBlocklayer))

                    # dbCreateRect(self, extBlocklayer,
                    #              Box(xpos1 - ext_over, ypos1 + ext_over, xpos2 + ext_over,
                    #                  ypos2 - ext_over))
                else:
                    point1 = self.toSceneCoord(QPointF(xpos1 - ext_over, ypos1 - ext_over))
                    point2 = self.toSceneCoord(QPointF(xpos2 + ext_over, ypos2 + ext_over))
                    tempShapeList.append(lshp.layoutRect(point1,point2,extBlocklayer))
                    # dbCreateRect(self, extBlocklayer,
                    #              Box(xpos1 - ext_over, ypos1 - ext_over, xpos2 + ext_over,
                    #                  ypos2 + ext_over))

                xpos1 = xpos1 + w + ps
                ypos1 = ypos2
        # x1,y1,x2,y2,dir are updated, use code from first contact, only pin is different
        # **************************************************************
        # draw res contact (Top)
        # **************************************************************
        # set x1 x2 to dogbone,:
        if stripes >  1 :
            xpos1 = xpos1
            xpos2 = xpos2+contoverlay+contoverlay
        else :
            xpos1 = xpos1-contoverlay
            xpos2 = xpos2+contoverlay
        # **************************************************************
        #  GatPoly Part
        point1 = self.toSceneCoord(QPointF(xpos1, ypos2))
        point2 = self.toSceneCoord(QPointF(xpos2, ypos2 + poly_cont_len * Dir))
        tempShapeList.append(lshp.layoutRect(point1, point2, contpolylayer))
        # dbCreateRect(self, contpolylayer, Box(xpos1, ypos2, xpos2, ypos2 + poly_cont_len * Dir))

        # draw contacts
        # LI and Metal
        # always dot contacts with auto-generated LI

        # **************************************************************
        # EXTBlock
        # draw ExtBlock for bottom Cont Area
        point1 = self.toSceneCoord(QPointF(xpos1 - ext_over, ypos1))
        point2 = self.toSceneCoord(QPointF(xpos2 + ext_over, ypos2 + ext_over * Dir +
                                           poly_cont_len * Dir))
        tempShapeList.append(lshp.layoutRect(point1, point2, extBlocklayer))

        # dbCreateRect(self, extBlocklayer, Box(xpos1 - ext_over, ypos1, xpos2 + ext_over,
        #                                       ypos2 + ext_over * Dir + poly_cont_len * Dir))
        # **************************************************************
        #  ExtBlock Part
        # added internal code
        if drawbar == True:
            # can only be in internal PCell
            point1 = self.toSceneCoord(QPointF(xpos1 + contbar_poly_over, ypos2 +
                                               li_poly_over * Dir))
            point2 = self.toSceneCoord(QPointF(xpos2 - contbar_poly_over, ypos2 + (consize +
                                                                                   li_poly_over) * Dir))
            tempShapeList.append(lshp.layoutRect(point1, point2, locintlayer))
            # dbCreateRect(self, locintlayer,
            #              Box(xpos1 + contbar_poly_over, ypos2 + li_poly_over * Dir,
            #                  xpos2 - contbar_poly_over, ypos2 + (consize + li_poly_over) * Dir))
        else:
            for i in range(ncont):
                point1 = self.toSceneCoord(QPointF(xpos1 + polyover + distr + i * distc,
                                                    ypos2 + li_poly_over * Dir))
                point2 = self.toSceneCoord(QPointF(xpos1 + polyover + distr + i * distc + consize,
                                                    ypos2 + (consize + li_poly_over) * Dir))
                tempShapeList.append(lshp.layoutRect(point1, point2, locintlayer))
                # dbCreateRect(self, locintlayer, Box(xpos1 + polyover + distr + i * distc,
                #                                     ypos2 + li_poly_over * Dir,
                #                                     xpos1 + polyover + distr + i * distc + consize,
                #                                     ypos2 + (consize + li_poly_over) * Dir))
        # **************************************************************
        #  Metal ans Pin Part
        # new metal block
        ypos1 = ypos2+(li_poly_over-metover)*Dir
        ypos2 = ypos2+(consize+li_poly_over+metover)*Dir
        point1 = self.toSceneCoord(QPointF(xpos1+contbar_poly_over-endcap, ypos1))
        point2 = self.toSceneCoord(QPointF(xpos2-contbar_poly_over+endcap, ypos2))
        tempShapeList.append(lshp.layoutRect(point1, point2, metlayer))
        # dbCreateRect(self, metlayer, Box(xpos1+contbar_poly_over-endcap, ypos1, xpos2-contbar_poly_over+endcap, ypos2))
        centre = QRectF(point1,point2).center()
        tempShapeList.append(lshp.layoutPin(point1,point2, 'MINUS', lshp.layoutPin.pinDirs[2],
                                           lshp.layoutPin.pinTypes[0], metlayer_pin))
        tempShapeList.append(lshp.layoutLabel(centre, 'MINUS', *self._labelFontTuple,
                                             lshp.layoutLabel.labelAlignments[0],
                                             lshp.layoutLabel.labelOrients[0],
                                             metlayer_lbl))
        # MkPin(self, 'MINUS', 2, Box(xpos1+contbar_poly_over-endcap, ypos1, xpos2-contbar_poly_over+endcap, ypos2), metlayer)
        resistance = self.CbResCalc('R', 0, l * 1e-6, w * 1e-6, b, ps * 1e-6, Cell)
        labeltext = '{0} r={1:.3f}'.format(Cell, resistance)
        labelpos = self.toSceneCoord(QPointF(w / 2, l / 2))
        rlabeltuple = (self._labelFontTuple[0], self._labelFontTuple[1],
                        4*self._labelFontTuple[2])

        # lbl
        tempShapeList.append(lshp.layoutLabel(labelpos,labeltext,*rlabeltuple,
                                             lshp.layoutLabel.labelAlignments[0],
                                             lshp.layoutLabel.labelOrients[0], textlayer))
        # lbl = dbCreateLabel(self, Layer(textlayer, 'drawing'), labelpos, labeltext,
        #                     'centerCenter', rot, Font.EURO_STYLE, labelheight)
        self.shapes = tempShapeList
    # ****************************************************************************************************
    # CbResCalc
    # ****************************************************************************************************

    def CbResCalc(self, calc, r, l, w, b, ps, cell):

        suffix = "G2"
        rspec = Quantity(
            self._techParams[cell + suffix + '_rspec']).real  # specific body res. per sq. (
        # float)
        rkspec = Quantity(self._techParams[cell + '_rkspec']).real  # res. per single contact (float)
        rzspec = Quantity(self._techParams[
                             cell + '_rzspec']).real * 1e6  # transition res. per um width
        # between contact area and body (float)
        lwd = Quantity(self._techParams[
                          cell + suffix + '_lwd']).real * 1e6  # line width delta [um] (both
        # edges, positiv value adds to w)
        kappa = 1.85
        if cell + '_kappa' in self._techParams:
            kappa = Quantity(self._techParams[cell + '_kappa']).real
        poly_over_cont = self._techParams['Cnt_d']  # strcat(cell '_poly_over_cont'))
        cont_size = self._techParams[
            'Cnt_a']  # techGetSpacingRule(tfId 'minWidth' 'Cont')     # size of contact array [um]
        cont_space = self._techParams['Cnt_b']  # techGetSpacingRule(tfId 'minSpacing' 'Cont')
        cont_dist = cont_space + cont_size
        minW = Quantity(self._techParams[cell + '_minW']).real

        # must check for string arguments and convert to float
        if type(r) == str:
            r = Quantity(r).real
        if type(l) == str:
            l = Quantity(l).real
        if type(w) == str:
            w = Quantity(w).real
        if type(b) == str:
            b = Quantity(b).real
        if type(ps) == str:
            ps = Quantity(ps).real

        if w >= (minW-Quantity('1u').real*self._epsilon):
        # if LeQp3(w, minW, '1u', self._techParams[
        #     'epsilon1']):  # 6.8.03 GG: wmin -> minW,HS: Function'LeQp' 28.9.2004
            w = minW  # avoid divide by zero errors in case of problems ; 21.7.03 GG: eps -> minW

        w = w * 1e6  # um (needed for contact calculation);HS 4.10.2004
        l = l * 1e6
        ps = ps * 1e6

        # here: all dimensions given in [um]!
        result = 0

        if calc == 'R':
            weff = w + lwd
            # result = l/weff*(b+1)*rspec+(2.0/kappa*weff+ps)*b/weff*rspec+2.0/weff*rzspec+2.0*(rkspec/ncont)
            result = l / weff * (b + 1) * rspec + (
                        2.0 / kappa * weff + ps) * b / weff * rspec + 2.0 / w * rzspec
        elif calc == 'l':
            weff = w + lwd
            # result = (weff*(r-2.0*rkspec/ncont)-b*(2.0/kappa*weff+ps)*rspec-2.0*rzspec)/(rspec*(b+1))*1.0e-6 ; in [m]
            result = (weff * r - b * (
                        2.0 / kappa * weff + ps) * rspec - 2.0 * weff / w * rzspec) / (
                                 rspec * (b + 1)) * 1.0e-6  # in [m]
        elif calc == 'w':
            tmp = r - 2 * b * rspec / kappa
            p = (r * lwd - l * (b + 1) * rspec - (
                        2 * lwd / kappa + ps) * b * rspec - 2 * rzspec) / tmp
            q = -2 * lwd * rzspec / tmp
            w = -p / 2 + math.sqrt(p * p / 4 - q)
            result = self.GridFix(w) * 1e-6  # -> [m]

        return result

#
# class nmos_ihp(baseCell):
#     def __init__(self, width: str = "4u", length: str = "0.13u", ng: str = "1"):
#
#         self.width = Quantity(width).real
#         self.length = Quantity(length).real
#         self.ng = int(float(ng))
#
#         tempShapeList = []
#         super().__init__(tempShapeList)
#
#     def __call__(self, width: str, length: str, ng: str):
#         tempShapesList = []
#         self.width = Quantity(width).real
#         self.length = Quantity(length).real
#         self.ng = int(float(ng))
#
#         Cell = self.__class__.__name__
#         typ = 'N'
#         hv = False
#
#         defL = Quantity(self._techParams["nmos_defL"]).real
#         defW = Quantity(self._techParams["nmos_defW"]).real
#         defNG = Quantity(self._techParams["nmos_defNG"]).real
#         minL = Quantity(self._techParams["nmos_minL"]).real
#         minW = Quantity(self._techParams["nmos_minW"]).real
#         # layers
#         metall_layer = laylyr.Metal1_drw
#         metall_layer_pin = laylyr.Metal1_pin
#         metal1_layer_label = laylyr.Metal1_txt
#         ndiff_layer = laylyr.Activ_drw
#         pdiff_layer = laylyr.Activ_drw
#         pdiffx_layer = laylyr.pSD_drw
#         poly_layer = laylyr.GatPoly_drw
#         poly_layer_pin = laylyr.GatPoly_pin
#         well_layer = laylyr.NWell_drw
#         well2_layer = laylyr.nBuLay_drw
#         textlayer = laylyr.TEXT_drw
#         locint_layer = laylyr.Cont_drw
#         tgo_layer = laylyr.ThickGateOx_drw
#         #* Generic Design Rule Definitions
#         #
#         epsilon = self._techParams["epsilon1"]
#         endcap = self._techParams["M1_c1"]
#         cont_size = self._techParams["Cnt_a"]
#         cont_dist = self._techParams["Cnt_b"]
#         cont_Activ_overRec = self._techParams['Cnt_c']
#         cont_metall_over = self._techParams['M1_c']
#         psd_pActiv_over = self._techParams['pSD_c']
#         nwell_pActiv_over = self._techParams['NW_c']
#         #minNwellForNBuLay = self._techParams['NW_g']
#         well2_over = self._techParams['NW_NBL']
#         gatpoly_Activ_over = self._techParams["Gat_c"]
#         gatpoly_cont_dist = self._techParams["Cnt_f"]
#         smallw_gatpoly_cont_dist =self._techParams['Cnt_c']
#         psd_PFET_over = self._techParams['pSD_i']
#         pdiffx_poly_over_orth = 0.48
#
#         wmin = Quantity(self._techParams['nmos_minW']).real
#         lmin = Quantity(self._techParams['nmos_minL']).real
#         # all calculations should be rounded to 3 digits. 1nm = QPoint(1, 0)
#         contActMin = self.GridFix(2*cont_Activ_overRec+cont_size)
#         thGateOxGat = self._techParams['TGO_c']
#         thGateOxAct = self._techParams['TGO_a']
#
#         ng = math.floor(self.ng+epsilon)
#         wf = self.GridFix(self.width/ng)
#         l = self.GridFix(self.length)
#
#         if endcap < cont_metall_over :
#             endcap = cont_metall_over
#
#         if hv :
#             labelhv = 'HV'
#         else :
#             labelhv = ''
#
#         if wf < contActMin-epsilon :  # adjust size of Gate to S/D contact region due to corner
#             gatpoly_cont_dist = smallw_gatpoly_cont_dist
#
#         xdiff_beg = 0
#         ydiff_beg = 0
#         ydiff_end = wf
#
#         if wf < wmin - epsilon:
#             print('Width < ' + str(wmin))
#             w = wmin
#
#         if l < lmin - epsilon:
#             print('Length < ' + str(lmin))
#             l = lmin
#
#         if ng < 1:
#             print('Minimum one finger')
#             ng = 1
#
#         xanz = self.fix(wf-2*cont_Activ_overRec+cont_dist/(cont_size+cont_dist)+epsilon)
#         w1 = self.GridFix(xanz*(cont_size+cont_dist)-cont_dist+cont_Activ_overRec
#                           +cont_Activ_overRec)
#         xoffset = self.GridFix((wf-w1)/2)
#         diffoffset = 0
#
#         if wf < contActMin:
#             xoffset = 0
#             diffoffset = self.GridFix((contActMin - wf) / 2)
#
#
#         # get the number of contacts
#         lcon = wf - 2 * cont_Activ_overRec
#         distc = cont_size + cont_dist
#         ncont = self.fix((wf - 2 * cont_Activ_overRec + cont_dist) / (
#                 cont_size + cont_dist) + epsilon)
#         # if self.zerop(ncont):
#         #     ncont = 1
#         if ncont == 0:
#             ncont = 1
#         diff_cont_offset = self.GridFix(wf - 2 * cont_Activ_overRec - ncont * cont_size - (
#                 ncont - 1) * cont_dist / 2)
#         # draw the cont row
#         xcont_beg = xdiff_beg + cont_Activ_overRec
#         ycont_beg = ydiff_beg + cont_Activ_overRec
#         ycont_cnt = ycont_beg + diffoffset + diff_cont_offset
#         xcont_end = xcont_beg + cont_size
#         # draw Metal rect
#         # calculate bot and top cont position
#         yMet1 = ycont_cnt - endcap
#         yMet2 = ycont_cnt + cont_size + (ncont - 1) * distc + endcap
#         # is metal1 overlapping Activ?
#         yMet1 = min(yMet1, ydiff_beg + diffoffset)
#         yMet2 = max(yMet2, ydiff_end + diffoffset)
#         point1 = QPointF(xcont_beg - cont_metall_over, yMet1)
#         point2 = QPointF(xcont_end + cont_metall_over, yMet2)
#         # tempShapesList.append(
#         #     lshp.layoutRect(
#         #         self.toSceneCoord(point1), self.toSceneCoord(point2), metall_layer
#         #     )
#         # )
#         center = QRectF(point1, point2).center()
#         tempShapesList.append(
#             lshp.layoutPin(self.toSceneCoord(point1), self.toSceneCoord(point2), "S",
#                            lshp.layoutPin.pinDirs[2], lshp.layoutPin.pinTypes[0],
#                            metall_layer_pin))
#
#
#         point1 = QPointF(xcont_beg - cont_Activ_overRec, ycont_beg - cont_Activ_overRec)
#         point2 = QPointF(
#             xcont_end + cont_Activ_overRec, ycont_beg + cont_size + cont_Activ_overRec
#         )
#
#         tempShapesList.append(
#             lshp.layoutRect(
#                 self.toSceneCoord(point1), self.toSceneCoord(point2), ndiff_layer
#             )
#         )
#         # draw contacts
#         # LI and Metall
#         subCont = lshp.layoutVia(QPoint(0,0), fabproc.cont, self.toSceneDimension(cont_size),
#                                  self.toSceneDimension(cont_size))
#         point1 = self.toSceneCoord(QPointF(xcont_beg, ydiff_beg))
#         point2 = self.toSceneCoord(QPointF(xcont_end, ydiff_end+diffoffset*2))
#         rect = QRectF(point1, point2)
#
#         print(f'rect: {rect}')
#         layoutViaArray = self.calcViaArray(subCont, rect, self.toSceneDimension(cont_dist),
#                                            self.toSceneDimension(cont_dist))
#         tempShapesList.append(layoutViaArray)
#         # for i in range(ng):
#         #     # draw the poly line
#         #     xpoly_beg = xcont_end+gatpoly_cont_dist
#         #     ypoly_beg = ydiff_beg-gatpoly_Activ_over
#         #     xpoly_end = xpoly_beg+l
#         #     ypoly_end = ydiff_end+gatpoly_Activ_over
#         #     point1 = QPointF(xpoly_beg, ypoly_beg+diffoffset)
#         #     point2 = QPointF( xpoly_end, ypoly_end+diffoffset)
#         #     tempShapesList.append(lshp.layoutRect(self.toSceneCoord(point1),
#         #                                           self.toSceneCoord(point2), metall_layer))
#
#         self.shapes = tempShapesList
