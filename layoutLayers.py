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
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

import revedaEditor.backend.dataDefinitions as ddef

odLayer_drw = ddef.layLayer(
    name="od",
    purpose="drawing",
    pcolor=QColor(255, 0, 0, 127),
    pwidth=1,
    pstyle=Qt.SolidLine,
    bcolor=QColor(255, 0, 0, 127),
    btexture="pdk/stipple1.png",
    z=1,
    visible=True,
    selectable=True,
    gdsLayer=0,
)

odLayer_pin = ddef.layLayer(
    name="od",
    purpose="pin",
    pcolor=QColor(255, 0, 0, 180),
    pwidth=1,
    pstyle=Qt.SolidLine,
    bcolor=QColor(139, 0, 0, 180),
    btexture="pdk/stipple1.png",
    z=1,
    visible=True,
    selectable=True,
    gdsLayer=0,
)
odLayer_txt = ddef.layLayer(
    name="od",
    purpose="text",
    pcolor=QColor(255, 0, 0, 255),
    pwidth=1,
    pstyle=Qt.SolidLine,
    bcolor=QColor(139, 0, 0, 255),
    btexture="pdk/stipple1.png",
    z=1,
    visible=True,
    selectable=True,
    gdsLayer=0,
)
activeLayer_drw = ddef.layLayer(
    name="active",
    purpose="drawing",
    pcolor=QColor(0, 0, 255, 127),
    pwidth=1,
    pstyle=Qt.SolidLine,
    bcolor=QColor(0, 0, 255, 180),
    btexture="pdk/stipple2.png",
    z=2,
    visible=True,
    selectable=True,
    gdsLayer=1,
)
activeLayer_pin = ddef.layLayer(
    name="active",
    purpose="pin",
    pcolor=QColor(0, 0, 255, 180),
    pwidth=1,
    pstyle=Qt.SolidLine,
    bcolor=QColor(0, 0, 139, 180),
    btexture="pdk/stipple2.png",
    z=2,
    visible=True,
    selectable=True,
    gdsLayer=1,
)
activeLayer_txt = ddef.layLayer(
    name="active",
    purpose="text",
    pcolor=QColor(0, 0, 255, 255),
    pwidth=1,
    pstyle=Qt.SolidLine,
    bcolor=QColor(0, 0, 255, 255),
    btexture="pdk/stipple2.png",
    z=2,
    visible=True,
    selectable=True,
    gdsLayer=1,
)
contactLayer_drw = ddef.layLayer(
    name="contact",
    purpose="drawing",
    pcolor=QColor(0, 255, 0, 127),
    pwidth=1,
    pstyle=Qt.SolidLine,
    bcolor=QColor("green"),
    btexture="pdk/stipple3.png",
    z=3,
    visible=True,
    selectable=True,
    gdsLayer=2,
)
contactLayer_pin = ddef.layLayer(
    name="contact",
    purpose="pin",
    pcolor=QColor(0, 0, 255, 180),
    pwidth=3,
    pstyle=Qt.SolidLine,
    bcolor=QColor("darkGreen"),
    btexture="pdk/stipple3.png",
    z=3,
    visible=True,
    selectable=True,
    gdsLayer=2,
)
contactLayer_txt = ddef.layLayer(
    name="contact",
    purpose="text",
    pcolor=QColor(50, 0, 255, 255),
    pwidth=1,
    pstyle=Qt.SolidLine,
    bcolor=QColor(50, 0, 255, 255),
    btexture="pdk/stipple3.png",
    z=3,
    visible=True,
    selectable=True,
    gdsLayer=2,
)
m1Layer_drw = ddef.layLayer(
    name="m1",
    purpose="drawing",
    pcolor=QColor(255, 255, 0, 127),
    pwidth=1,
    pstyle=Qt.SolidLine,
    bcolor=QColor(255, 255, 0, 127),
    btexture="pdk/stipple4.png",
    z=4,
    visible=True,
    selectable=True,
    gdsLayer=3,
)
m1layer_pin = ddef.layLayer(
    name="m1",
    purpose="pin",
    pcolor=QColor(246, 190, 0, 180),
    pwidth=1,
    pstyle=Qt.SolidLine,
    bcolor=QColor(246, 190, 0, 180),
    btexture="pdk/stipple4.png",
    z=4,
    visible=True,
    selectable=True,
    gdsLayer=3,
)
m1layer_txt = ddef.layLayer(
    name="m1",
    purpose="text",
    pcolor=QColor(246, 190, 0, 255),
    pwidth=1,
    pstyle=Qt.SolidLine,
    bcolor=QColor(246, 190, 0, 255),
    btexture="pdk/stipple4.png",
    z=4,
    visible=True,
    selectable=True,
    gdsLayer=3,
)
m2Layer_drw = ddef.layLayer(
    name="m2",
    purpose="drawing",
    pcolor=QColor(255, 0, 255, 127),
    pwidth=1,
    pstyle=Qt.SolidLine,
    bcolor=QColor(255, 0, 255, 127),
    btexture="pdk/stipple5.png",
    z=5,
    visible=True,
    selectable=True,
    gdsLayer=4,
)
m2Layer_pin = ddef.layLayer(
    name="m2",
    purpose="pin",
    pcolor=QColor(255, 0, 255, 180),
    pwidth=1,
    pstyle=Qt.SolidLine,
    bcolor=QColor(255, 0, 255, 180),
    btexture="pdk/stipple5.png",
    z=5,
    visible=True,
    selectable=True,
    gdsLayer=4,
)
m2Layer_txt = ddef.layLayer(
    name="m2",
    purpose="text",
    pcolor=QColor(255, 0, 255, 255),
    pwidth=1,
    pstyle=Qt.SolidLine,
    bcolor=QColor(255, 0, 255, 255),
    btexture="pdk/stipple5.png",
    z=5,
    visible=True,
    selectable=True,
    gdsLayer=4,
)
via1Layer_drw = ddef.layLayer(
    name="via1",
    purpose="drawing",
    pcolor=QColor(180, 0, 180, 127),
    pwidth=2,
    pstyle=Qt.SolidLine,
    bcolor=QColor(180, 0, 180, 127),
    btexture="pdk/stipple6.png",
    z=6,
    visible=True,
    selectable=True,
    gdsLayer=5,
)
via1Layer_pin = ddef.layLayer(
    name="via1",
    purpose="pin",
    pcolor=QColor(180, 0, 180, 180),
    pwidth=3,
    pstyle=Qt.SolidLine,
    bcolor=QColor(180, 0, 180, 180),
    btexture="pdk/stipple6.png",
    z=6,
    visible=True,
    selectable=True,
    gdsLayer=5,
)
via1Layer_txt = ddef.layLayer(
    name="via1",
    purpose="text",
    pcolor=QColor(180, 0, 180, 255),
    pwidth=1,
    pstyle=Qt.SolidLine,
    bcolor=QColor(180, 0, 180, 255),
    btexture="pdk/stipple6.png",
    z=6,
    visible=True,
    selectable=True,
    gdsLayer=5,
)
pdkLayoutLayers = [
    odLayer_drw,
    activeLayer_drw,
    contactLayer_drw,
    m1Layer_drw,
    m2Layer_drw,
]
pdkPinLayers = [
    odLayer_pin,
    activeLayer_pin,
    contactLayer_pin,
    m1layer_pin,
    m2Layer_pin,
]
pdkViaLayers = [
    contactLayer_drw,
    via1Layer_drw,
]
pdkTextLayers = [
    odLayer_txt,
    activeLayer_txt,
    contactLayer_txt,
    m1layer_txt,
    m2Layer_txt,
]
pdkAllLayers = pdkLayoutLayers + pdkPinLayers + pdkTextLayers + pdkViaLayers
