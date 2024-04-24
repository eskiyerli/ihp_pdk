#    “Commons Clause” License Condition v1.0
#   #
#    The Software is provided to you by the Licensor under the License, as defined
#    below, subject to the following condition.
#
#    Without limiting other conditions in the License, the grant of rights under the
#    License will not include, and the License does not grant to you, the right to
#    Sell the Software.
#
#    For purposes of the foregoing, “Sell” means practicing any or all of the rights
#    granted to you under the License to provide to third parties, for a fee or other
#    consideration (including without limitation fees for hosting or consulting/
#    support services related to the Software), a product or service whose value
#    derives, entirely or substantially, from the functionality of the Software. Any
#    license notice or attribution required by the License must also include this
#    Commons Clause License Condition notice.
#
#   Add-ons and extensions developed for this software may be distributed
#   under their own separate licenses.
#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#
# import pdk.layoutLayers as laylyr
from PySide6.QtCore import (
    QPoint,
)

import pdk.layoutLayers as laylyr
import pdk.process as fabproc
# import pdk.utilityFunctions as uf
import revedaEditor.common.layoutShapes as lshp
from pdk.sg13_tech import SG13_Tech as sg13
from quantiphy import Quantity

class baseCell(lshp.layoutPcell):

    """
    Base class for all layout parametric cells.
    """
    scale = fabproc.dbu
    def __init__(self, shapes = list):
        super().__init__(shapes)
        techClass = sg13()
        self._techParams = techClass.techParams

    @staticmethod
    def zerop(value):
        if value == 0:
            return 1
        else:
            return 0
#
class nmos(baseCell):
    cut = int(0.17 * fabproc.dbu)
    poly_to_cut = int(0.055 * fabproc.dbu)
    diff_ovlp_cut = int(0.06 * fabproc.dbu)
    poly_ovlp_diff = int(0.13 * fabproc.dbu)
    nsdm_ovlp_diff = int(0.12 * fabproc.dbu)
    li_ovlp_cut = int(0.06 * fabproc.dbu)
    sa = poly_to_cut + cut + diff_ovlp_cut
    sd = 2 * (max(poly_to_cut, diff_ovlp_cut)) + cut

    # when initialized it has no shapes.
    def __init__(
        self,
        width: str = "4.0",
        length: str = "0.13",
        nf: str = "1",
    ):
        """
        Initialize a new instance of the nmos pcell.

        Args:
            width (str, optional): total gate width. Defaults to 4.0.
            length (str, optional): gate length. Defaults to 0.13.
            nf (str, optional): number of fingers. Defaults to 1.
        """
        self._shapes = []
        # define the device parameters here but set them to zero
        self._deviceWidth = float(width)  # device width
        self._drawnWidth: int = int(
            fabproc.dbu * self._deviceWidth
        )  # width in grid points
        self._deviceLength = float(length)  # gate length
        self._drawnLength: int = int(fabproc.dbu * self._deviceLength)
        self._nf = int(float(nf))  # number of fingers.
        self._widthPerFinger = int(self._drawnWidth / self._nf)
        super().__init__(self._shapes)

    def __call__(self, width: str, length: str, nf: str):
        """
        When pcell instance is called, it removes all the shapes and recreates them
        and adds them as child items to pcell.

        Args:
            width (float): total gate width
            length (float): gate length
            nf (int): number of fingers

        Returns:
            list[layoutShape]: list of shapes in the pcell
        """
        self._deviceWidth = float(width)  # total gate width
        self._drawnWidth = int(
            self._deviceWidth * fabproc.dbu
        )  # drawn gate width in grid points
        self._deviceLength = float(length)  # gate length
        self._drawnLength = int(
            self._deviceLength * fabproc.dbu
        )  # drawn gate length in grid points
        self._nf = int(float(nf))  # number of fingers
        self._widthPerFinger = self._drawnWidth / self._nf
        self.shapes = self.createGeometry() # check shapes property of layoutInstance class

    def createGeometry(self) -> list[lshp.layoutShape]:
        """
        This function creates the geometry of the nmos pcell.
        It consists of an active region and poly fingers.
        Args:
            self (nmos): instance of the nmos pcell
        Returns:
            list[layoutShape]: list of shapes in the pcell
        """
        activeRect = lshp.layoutRect(
            QPoint(0, 0),
            QPoint(
                self._widthPerFinger,
                int(
                    self._nf * self._drawnLength
                    + 2 * nmos.sa
                    + (self._nf - 1) * nmos.sd
                ),
            ),
            laylyr.Activ_drw,
        )
        polyFingers = [
            lshp.layoutRect(
                QPoint(
                    -nmos.poly_ovlp_diff,
                    nmos.sa + finger * (self._drawnLength + nmos.sd),
                ),
                QPoint(
                    self._widthPerFinger + nmos.poly_ovlp_diff,
                    nmos.sa
                    + finger * (self._drawnLength + nmos.sd)
                    + self._drawnLength,
                ),
                laylyr.GatPoly_drw,
            )
            for finger in range(self._nf)
        ]
        # contacts = [lshp.layoutRect(

        # )]
        return [activeRect, *polyFingers]

    @property
    def width(self):
        return self._deviceWidth

    @width.setter
    def width(self, value: float):
        self._deviceWidth = value

    @property
    def length(self):
        return self._deviceLength

    @length.setter
    def length(self, value: float):
        self._deviceLength = value

    @property
    def nf(self):
        return self._nf

    @nf.setter
    def nf(self, value: int):
        self._nf = value

class nmos_ihp(baseCell):
    def __init__(self, w: str = '4u', l:str = '0.13u', ng: str = '1'):

        self.w= Quantity(w).real
        self.l = Quantity(l).real
        self.ng = int(float(ng))
        self._shapes = []
        super().__init__(self._shapes)

    def __call__(self, w: str, l:str, ng: str):
        tempShapesList = []
        self.w= Quantity(w).real
        self.l = Quantity(l).real
        self.ng = int(float(ng))
        defL       = Quantity(self._techParams['nmos_defL']).real
        defW       = Quantity(self._techParams['nmos_defW']).real
        defNG      = Quantity(self._techParams['nmos_defNG']).real
        minL       = Quantity(self._techParams['nmos_minL']).real
        minW       = Quantity(self._techParams['nmos_minW']).real
        # layers
        metall_layer = laylyr.Metal1_drw
        metall_layer_pin = laylyr.Metal1_pin
        ndiff_layer = laylyr.Activ_drw
        poly_layer = laylyr.GatPoly_drw
        poly_layer_pin = laylyr.GatPoly_pin
        locint_layer = laylyr.Cont_drw

        #
        epsilon = Quantity(self._techParams['epsilon1']).real
        endcap = self._techParams['M1_c1']
        cont_size = self._techParams['Cnt_a']
        cont_dist = self._techParams['Cnt_b']
        cont_Activ_overRec = self._techParams['Cnt_c']
        cont_metall_over = self._techParams['M1_c']
        gatpoly_Activ_over = self._techParams['Gat_c']
        gatpoly_cont_dist = self._techParams['Cnt_f']
        smallw_gatpoly_cont_dist = cont_Activ_overRec+self._techParams['Gat_d']
        contActMin = 2*cont_Activ_overRec+cont_size

        wf = self.w/self.ng
        if endcap < cont_metall_over :
            endcap = cont_metall_over
        if wf < contActMin-epsilon :   #  adjust size of Gate to S/D contact region due to
            # corner
            gatpoly_cont_dist = smallw_gatpoly_cont_dist

        xdiff_beg = 0
        ydiff_beg = 0
        ydiff_end = wf
        if wf < contActMin :
            xoffset = 0
            diffoffset = (contActMin-wf)/2
        else:
            diffoffset = 0 # Need to check

        # get the number of contacts
        lcon = wf-2*cont_Activ_overRec
        distc = cont_size+cont_dist
        ncont = (wf-2*cont_Activ_overRec+cont_dist)/(cont_size+cont_dist)+epsilon
        if self.zerop(ncont) :
            ncont = 1
        diff_cont_offset = (wf - 2 * cont_Activ_overRec - ncont * cont_size - (ncont - 1) *
                            cont_dist) / 2
        # draw the cont row
        xcont_beg = xdiff_beg + cont_Activ_overRec
        ycont_beg = ydiff_beg + cont_Activ_overRec
        ycont_cnt = ycont_beg + diffoffset + diff_cont_offset
        xcont_end = xcont_beg + cont_size
        # draw Metal rect
        # calculate bot and top cont position
        yMet1 = ycont_cnt-endcap
        yMet2 = ycont_cnt+cont_size+(ncont-1)*distc+endcap
        # is metal1 overlapping Activ?
        yMet1 = min(yMet1, ydiff_beg+diffoffset)
        yMet2 = max(yMet2, ydiff_end+diffoffset)
        point1 = QPoint(baseCell.scale*(xcont_beg - cont_metall_over), baseCell.scale*yMet1)
        point2 = QPoint(baseCell.scale*(xcont_end + cont_metall_over), baseCell.scale*yMet2)

        tempShapesList.append(lshp.layoutRect(
            point1, point2,
            metall_layer
        ))
        self.shapes = tempShapesList

