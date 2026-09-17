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
snapGrid = 0.05  # 0.05um (50nm)
majorGrid = 0.1  # 0.1um (100nm)
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
# bottomLayer / topLayer are the two conductor layers a via stitches together,
# and bottom/topEnclosure (in um) are how far each metal must extend past the
# cut on every side. Enclosure values come from the SG13G2 tech params:
#   Cnt_c   -> Metal1 enclosure of Cont
#   Vn_c    -> Metal enclosure of Via1..Via4
#   TV1_c/d -> Metal5 / TopMetal1 enclosure of TopVia1
#   TV2_c/d -> TopMetal1 / TopMetal2 enclosure of TopVia2
#   Mim_d/c -> MIM / TopMetal1 enclosure of Vmim
# Note: contacts physically land on Activ/GatPoly at the bottom and Metal1 at
# the top, so GatPoly is used as the bottom layer and Metal1 as the top layer.
_cntEnc = techParams["Cnt_c"]  # 0.07
_viaEnc = techParams["Vn_c"]  # 0.05
processVias = [
    ddef.viaDefTuple(
        "contBar",
        laylyr.Cont_drawing,
        "",
        0.34,
        0.34,
        0.16,
        0.16,
        0.28,
        10.0,
        bottomLayer=laylyr.GatPoly_drawing,
        topLayer=laylyr.Metal1_drawing,
        bottomEnclosure=_cntEnc,
        topEnclosure=_cntEnc,
    ),
    ddef.viaDefTuple(
        "cont",
        laylyr.Cont_drawing,
        "",
        0.16,
        0.16,
        0.16,
        0.16,
        0.28,
        10.0,
        bottomLayer=laylyr.GatPoly_drawing,
        topLayer=laylyr.Metal1_drawing,
        bottomEnclosure=_cntEnc,
        topEnclosure=_cntEnc,
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
        bottomLayer=laylyr.MIM_drawing,
        topLayer=laylyr.TopMetal1_drawing,
        bottomEnclosure=techParams["Mim_d"],
        topEnclosure=techParams["Mim_c"],
    ),
    ddef.viaDefTuple(
        "via1",
        laylyr.Via1_drawing,
        "",
        0.19,
        0.19,
        0.19,
        0.19,
        0.22,
        10.0,
        bottomLayer=laylyr.Metal1_drawing,
        topLayer=laylyr.Metal2_drawing,
        bottomEnclosure=_viaEnc,
        topEnclosure=_viaEnc,
    ),
    ddef.viaDefTuple(
        "via2",
        laylyr.Via2_drawing,
        "",
        0.19,
        0.19,
        0.19,
        0.19,
        0.22,
        10.0,
        bottomLayer=laylyr.Metal2_drawing,
        topLayer=laylyr.Metal3_drawing,
        bottomEnclosure=_viaEnc,
        topEnclosure=_viaEnc,
    ),
    ddef.viaDefTuple(
        "via3",
        laylyr.Via3_drawing,
        "",
        0.19,
        0.19,
        0.19,
        0.19,
        0.22,
        10.0,
        bottomLayer=laylyr.Metal3_drawing,
        topLayer=laylyr.Metal4_drawing,
        bottomEnclosure=_viaEnc,
        topEnclosure=_viaEnc,
    ),
    ddef.viaDefTuple(
        "via4",
        laylyr.Via4_drawing,
        "",
        0.19,
        0.19,
        0.19,
        0.19,
        0.22,
        10.0,
        bottomLayer=laylyr.Metal4_drawing,
        topLayer=laylyr.Metal5_drawing,
        bottomEnclosure=_viaEnc,
        topEnclosure=_viaEnc,
    ),
    ddef.viaDefTuple(
        "topVia1",
        laylyr.TopVia1_drawing,
        "",
        0.42,
        0.42,
        0.42,
        0.42,
        0.42,
        10.0,
        bottomLayer=laylyr.Metal5_drawing,
        topLayer=laylyr.TopMetal1_drawing,
        bottomEnclosure=techParams["TV1_c"],
        topEnclosure=techParams["TV1_d"],
    ),
    ddef.viaDefTuple(
        "topVia2",
        laylyr.TopVia2_drawing,
        "",
        0.90,
        0.90,
        0.90,
        0.90,
        1.06,
        10.0,
        bottomLayer=laylyr.TopMetal1_drawing,
        topLayer=laylyr.TopMetal2_drawing,
        bottomEnclosure=techParams["TV2_c"],
        topEnclosure=techParams["TV2_d"],
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
        "topMetal2", laylyr.TopMetal2_drawing, "", 2.0, 100.0, 1, 1000.0, 2.0, 1000.0
    ),
]
processPathNames = [path.name for path in processPaths]
