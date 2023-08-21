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
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#
import pdk.layoutLayers as laylyr
import pdk.process as fabproc
import revedaEditor.common.layoutShapes as lshp
import pdk.layoutLayers as laylyr

from PySide6.QtCore import (QPoint, )


class nmos(lshp.pcell):
    cut = int(0.17 * fabproc.dbu)
    poly_to_cut = int(0.055 * fabproc.dbu)
    diff_ovlp_cut = int(0.06 * fabproc.dbu)
    poly_ovlp_diff = int(0.13 * fabproc.dbu)
    nsdm_ovlp_diff = int(0.12 * fabproc.dbu)
    li_ovlp_cut = int(0.06 * fabproc.dbu)
    sa = poly_to_cut + cut + diff_ovlp_cut
    sd = 2 * (max(poly_to_cut, diff_ovlp_cut)) + cut

    def __init__(self, gridTuple: tuple[int, int], width: int = 4, length: int = 0.13,
                 nf: int = 1):
        self._gridTuple = gridTuple
        self._width =  int(float(width) * fabproc.dbu)
        self._length = int(float(length)*fabproc.dbu)
        self._nf = int(float(nf))
        self._widthPerFinger = int(self._width / self._nf)
        self.activeRect = lshp.layoutRect(QPoint(0, 0), QPoint(self._widthPerFinger,
                                                               int(self._nf * length + 2 * nmos.sa + (self._nf - 1) * nmos.sd)),
                                          laylyr.odLayer, self._gridTuple)

        super().__init__([self.activeRect], self._gridTuple)


    def __call__(self, width: int, length: int, nf: int = 1):
        self._width = int(float(width)*fabproc.dbu)
        self._length = int(float(length)*fabproc.dbu)
        self._nf = int(float(nf))
        self._widthPerFinger = int(self._width / self._nf)
        # start = self.activeRect.start
        self.activeRect.end = QPoint(self._widthPerFinger,
                        int(self._nf * self._length + 2 * nmos.sa + (self._nf - 1) * nmos.sd))


    @property
    def width(self):
        return (self._width/fabproc.dbu)


    @width.setter
    def width(self, value: str):
        self._width = int(float(value)*fabproc.dbu)


    @property
    def length(self):
        return (self._length/fabproc.dbu)


    @length.setter
    def length(self, value: str):
        self._length = int(float(value)*fabproc.dbu)

    @property
    def nf(self):
        return self._nf

    @nf.setter
    def nf(self, value: str):
        self._nf = int(float(value))


class pmos(lshp.pcell):
    pass
