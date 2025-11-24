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
#    consideration (including without limitation fees for hosting) a product or service whose value
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
import revedaEditor.backend.dataDefinitions as ddef
from revedaEditor.backend.pdkPaths import importPDKModule
from quantiphy import Quantity


laylyr = importPDKModule('layoutLayers')
techParams = importPDKModule('sg13_tech').SG13_Tech().techParams

# common process parameters
dbu = 1000  # distance between two points, 1um/1000=1n
snapGrid = 50 # 50nm
majorGrid = 100 # 100nm
gdsUnit = Quantity("1 um")
gdsPrecision = Quantity("1 num")

# via definitions, all distances are in um.
# class viaDefTuple(NamedTuple):
#     name: str
#     layer: layLayer
#     type: str
#     minWidth: float
#     maxWidth: float
#     minHeight: float
#     maxHeight: float
#     minSpacing: float
#     maxSpacing: float
processVias = [
    ddef.viaDefTuple("contBar", laylyr.Cont_drawing, "", 0.34, 0.34, 0.16, 0.16,
                     0.18, 10.0),
    ddef.viaDefTuple("cont", laylyr.Cont_drawing, "", 0.16, 0.16, 0.16, 0.16, 0.18, 10.0),
    ddef.viaDefTuple('viamim', laylyr.Vmim_drawing, "", techParams['TV1_a'], 10,
                     techParams['TV1_a'], 10, 0.84, 10),
    ddef.viaDefTuple("via1", laylyr.Via1_drawing, "", 0.19, 0.19, 0.19, 0.19,
                     0.22, 10.0),
    ddef.viaDefTuple("via2", laylyr.Via2_drawing, "", 0.19, 0.19, 0.19, 0.19,
                     0.22, 10.0),
    ddef.viaDefTuple("via3", laylyr.Via3_drawing, "", 0.19, 0.19, 0.19, 0.19,
                     0.22, 10.0),
    ddef.viaDefTuple("via4", laylyr.Via4_drawing, "", 0.19, 0.19, 0.19, 0.19,
                     0.22, 10.0),
    ddef.viaDefTuple("topVia1", laylyr.TopVia1_drawing, "", 0.42, 0.42, 0.42,
                     0.42, 0.42, 10.0),
    ddef.viaDefTuple("topVia2", laylyr.TopVia2_drawing, "", 0.90, 0.90, 0.90,
                     0.90, 1.06, 10.0)
]

processViaNames = [via.name for via in processVias]