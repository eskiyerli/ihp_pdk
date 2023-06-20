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
# Layout Layers
from PySide6.QtCore import (Qt)
from PySide6.QtGui import (QColor, QPen, QBrush)

import revedaEditor.backend.dataDefinitions as ddef


odLayer = ddef.edLayer(name="od", purpose="drawing", pcolor=QColor("white"), pwidth=1,
                       pstyle=Qt.SolidLine,
                       bcolor=QColor("red"), bstyle=Qt.Dense1Pattern, z=2, visible=True,
                       selectable=True, gdsLayer=0)

activeLayer = ddef.edLayer(name="active", purpose="drawing", pcolor=QColor("blue"), pwidth=1,
                           pstyle=Qt.SolidLine,
                           bcolor=QColor("blue"), bstyle=Qt.Dense2Pattern, z=1, visible=True,
                           selectable=True, gdsLayer=1)
contactLayer = ddef.edLayer(name="contact", purpose="drawing", pcolor=QColor("green"), pwidth=1,
                            pstyle=Qt.SolidLine,
                            bcolor=QColor("green"), bstyle=Qt.Dense3Pattern, z=3, visible=True,
                            selectable=True, gdsLayer=2)
m1Layer = ddef.edLayer(name="m1", purpose="drawing", pcolor=QColor("yellow"), pwidth=1,
                       pstyle=Qt.SolidLine, bcolor=QColor("yellow"), bstyle=Qt.Dense4Pattern,
                       z=4, visible=True, selectable=True, gdsLayer=3)

pdkLayoutLayers = [odLayer, activeLayer, contactLayer, m1Layer]


