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
import revedaEditor.common.shape as shp
import pdk.layoutLayers as laylyr
from PySide6.QtCore import (QPoint,)


class nmos(shp.layoutCell):
    def __init__(self, gridTuple:tuple[int,int], width:int = 20, length:int
    =20):
        self._gridTuple = gridTuple
        self.activeRect = shp.layRect(QPoint(0,0), QPoint(width, length),
                                 laylyr.odLayer, self._gridTuple)
        super().__init__([self.activeRect],self._gridTuple)

    @property
    def width(self):
        return self._width

    @property
    def length(self):
        return self._length
class pmos(shp.shape):
    pass