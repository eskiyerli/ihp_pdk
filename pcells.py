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
import revedaEditor.common.layoutShapes as lshp

class nmos(lshp.layoutPcell):
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
            gridTuple: tuple[int, int],
            width: float = 4.0,
            length: float = 0.13,
            nf: int = 1,
    ):
        self._shapes = []
        self._gridTuple = gridTuple
        # define the device parameters here but set them to zero
        self._deviceWidth = width # device width
        self._drawnWidth: int = int(fabproc.dbu * self._deviceWidth) # width in grid points
        self._deviceLength = length
        self._drawnLength: int = int(fabproc.dbu * self._deviceLength)
        self._nf = int(nf) # number of fingers.
        self._widthPerFinger = int(self._drawnWidth / self._nf)
        super().__init__(self._shapes, self._gridTuple)
    #

    def __call__(self, width:float, length:float, nf:int):
        '''
        When pcell instance is called, it removes all the shapes and recreates them and adds them as child items to pcell.
        '''
        self._deviceWidth = width
        self._drawnWidth = int(self._deviceWidth * fabproc.dbu)
        self._deviceLength = length
        self._drawnLength = int(self._deviceLength * fabproc.dbu)
        self._nf = int(nf)
        self._widthPerFinger = self._drawnWidth / self._nf
        for shape in self._shapes:
            self.scene().removeItem(shape)
            del shape
        self._shapes = self.createGeometry()
        [shape.setParentItem(self) for shape in self._shapes]

    def createGeometry(self) -> list[lshp.layoutShape]:
        activeRect = lshp.layoutRect(
            QPoint(0, 0),
            QPoint(
                self._widthPerFinger,
                int(self._nf * self._drawnLength + 2 * nmos.sa + (self._nf - 1) * nmos.sd),
            ),
            laylyr.odLayer_drw,
            self._gridTuple,
        )
        polyFingers = [lshp.layoutRect(
            QPoint(-nmos.poly_ovlp_diff,
            nmos.sa + finger * (self._drawnLength + nmos.sd)),
            QPoint(self._widthPerFinger + nmos.poly_ovlp_diff,
            nmos.sa + finger * (self._drawnLength + nmos.sd) + self._drawnLength), laylyr.poLayer_drw,
            self._gridTuple
        ) for finger in range(self._nf)]
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

class pmos(lshp.layoutPcell):
    pass
