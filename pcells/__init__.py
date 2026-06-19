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
from .tap_contacts import ntap1, ptap1
from .bjt import npn13G2, npn13G2V, npn13G2L, pnpMPA
from .diodes import dantenna, dpantenna
from .nofiller_stack import NoFillerStack
from .schottky import schottky

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
    'ntap1': ntap1,
    'ptap1': ptap1,
    'npn13G2': npn13G2,
    'npn13G2V': npn13G2V,
    'npn13G2L': npn13G2L,
    'pnpMPA': pnpMPA,
    'dantenna': dantenna,
    'dpantenna': dpantenna,
    'NoFillerStack': NoFillerStack,
    'schottky': schottky
}
