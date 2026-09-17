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
#
# For a complete summary of implemented pcells, see PCELL_STATUS.md

from .base import baseCell, baseMosfet, baseRfMosfet
from .mosfet import nmos, pmos
from .mosfet_hv import nmosHV, pmosHV
from .passive import rsil, cmim
from .passive_res_variants import rhigh, rppd
from .rf_mosfet import rfnmos, rfpmos
from .rf_mosfet_hv import rfnmosHV, rfpmosHV
from .tap_contacts import (ntap1, nwelltap, nwtap, psubtap, ptap1, subtap)
from .inductors import inductor2, inductor3
from .bjt import npn13G2, npn13G2V, npn13G2L, pnpMPA
from .diodes import dantenna, dpantenna
from .nofiller_stack import NoFillerStack
from .schottky import schottky
from .via_stack import via_stack
from .esd import (
    esd,
    diodevdd_2kv,
    diodevss_2kv,
    diodevdd_4kv,
    diodevss_4kv,
    nmoscl_2,
    nmoscl_4,
)
from .rfcmim import rfcmim
from .svaricap import SVaricap
from .bondpad import bondpad
from .sealring import sealring
from .isolbox import isolbox
from .guardRing import guardRing

pcells = {
    'rsil': rsil,
    'rhigh': rhigh,
    'rppd': rppd,
    'cmim': cmim,
    'nmos': nmos,
    'pmos': pmos,
    'nmosHV': nmosHV,
    'pmosHV': pmosHV,
    'rfnmos': rfnmos,
    'rfpmos': rfpmos,
    'rfnmosHV': rfnmosHV,
    'rfpmosHV': rfpmosHV,
    'ntap1': ntap1,
    'ptap1': ptap1,
    'subtap': subtap,
    'nwtap': nwtap,
    'psubtap': psubtap,
    'nwelltap': nwelltap,
    'inductor2': inductor2,
    'inductor3': inductor3,
    'npn13G2': npn13G2,
    'npn13G2V': npn13G2V,
    'npn13G2L': npn13G2L,
    'pnpMPA': pnpMPA,
    'dantenna': dantenna,
    'dpantenna': dpantenna,
    'NoFillerStack': NoFillerStack,
    'schottky': schottky,
    'via_stack': via_stack,
    'esd': esd,
    'diodevdd_2kv': diodevdd_2kv,
    'diodevss_2kv': diodevss_2kv,
    'diodevdd_4kv': diodevdd_4kv,
    'diodevss_4kv': diodevss_4kv,
    'nmoscl_2': nmoscl_2,
    'nmoscl_4': nmoscl_4,
    'rfcmim': rfcmim,
    'SVaricap': SVaricap,
    'bondpad': bondpad,
    'sealring': sealring,
    'isolbox': isolbox,
    'guardRing': guardRing,
}
