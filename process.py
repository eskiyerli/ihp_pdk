# 
# Revolution EDA
# 
# Copyright (c) 2026 Revolution Semiconductor
#
# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
##
import revedaEditor.backend.dataDefinitions as ddef
from quantiphy import Quantity
from revedaEditor.backend.pdkLoader import importPDKModule

laylyr = importPDKModule("layoutLayers")
techParams = importPDKModule("sg13_tech").SG13_Tech().techParams

# common process parameters
dbu = 1000  # distance between two points on the screen, 1um/1000=1n
layoutScaler = 1e6 * dbu
snapGrid = 50  # 50nm
majorGrid = 100  # 100nm
gdsUnit = Quantity("1 nm")
gdsPrecision = Quantity("1 nm")

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
    ddef.viaDefTuple(
        "contBar", laylyr.Cont_drawing, "", 0.34, 0.34, 0.16, 0.16, 0.18, 10.0
    ),
    ddef.viaDefTuple(
        "cont", laylyr.Cont_drawing, "", 0.16, 0.16, 0.16, 0.16, 0.18, 10.0
    ),
    ddef.viaDefTuple(
        "viamim",
        laylyr.Vmim_drawing,
        "",
        techParams["TV1_a"],
        10,
        techParams["TV1_a"],
        10,
        0.84,
        10,
    ),
    ddef.viaDefTuple(
        "via1", laylyr.Via1_drawing, "", 0.19, 0.19, 0.19, 0.19, 0.22, 10.0
    ),
    ddef.viaDefTuple(
        "via2", laylyr.Via2_drawing, "", 0.19, 0.19, 0.19, 0.19, 0.22, 10.0
    ),
    ddef.viaDefTuple(
        "via3", laylyr.Via3_drawing, "", 0.19, 0.19, 0.19, 0.19, 0.22, 10.0
    ),
    ddef.viaDefTuple(
        "via4", laylyr.Via4_drawing, "", 0.19, 0.19, 0.19, 0.19, 0.22, 10.0
    ),
    ddef.viaDefTuple(
        "topVia1", laylyr.TopVia1_drawing, "", 0.42, 0.42, 0.42, 0.42, 0.42, 10.0
    ),
    ddef.viaDefTuple(
        "topVia2", laylyr.TopVia2_drawing, "", 0.90, 0.90, 0.90, 0.90, 1.06, 10.0
    ),
]

processViaNames = [via.name for via in processVias]

processPaths = [
    ddef.layoutPathDefTuple(
        "nwell", laylyr.NWell_drawing, "", 0.62, 1000.0, 0.62, 10000.0, 0.62, 10000.0
    ),
    ddef.layoutPathDefTuple(
        "gatPoly", laylyr.GatPoly_drawing, "", 0.13, 100.0, 0.13, 1000.0, 0.18, 1000.0
    ),
    ddef.layoutPathDefTuple(
        "metal1", laylyr.Metal1_drawing, "", 0.16, 100.0, 0.6, 1000.0, 0.18, 1000.0
    ),
    ddef.layoutPathDefTuple(
        "metal2", laylyr.Metal2_drawing, "", 0.20, 100.0, 0.6, 1000.0, 0.21, 1000.0
    ),
    ddef.layoutPathDefTuple(
        "metal3", laylyr.Metal3_drawing, "", 0.20, 100.0, 0.6, 1000.0, 0.21, 1000.0
    ),
    ddef.layoutPathDefTuple(
        "metal4", laylyr.Metal4_drawing, "", 0.20, 100.0, 0.6, 1000.0, 0.21, 1000.0
    ),
    ddef.layoutPathDefTuple(
        "metal5", laylyr.Metal5_drawing, "", 0.20, 100.0, 0.6, 1000.0, 0.21, 1000.0
    ),
    ddef.layoutPathDefTuple(
        "topMetal1", laylyr.TopMetal1_drawing, "", 1.64, 100.0, 1, 1000.0, 1.64, 1000.0
    ),
    ddef.layoutPathDefTuple(
        "topMetal2", laylyr.TopMetal1_drawing, "", 2.0, 100.0, 1, 1000.0, 2.0, 1000.0
    ),
]
processPathNames = [path.name for path in processPaths]
