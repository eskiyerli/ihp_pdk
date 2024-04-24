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
import math
from pdk.sg13_tech import SG13_Tech as sg13

techClass = sg13()
self._techParams = techClass.techParams

#***********************************************************************************************************************
# fix
#***********************************************************************************************************************
def fix(value):
    if type(value) == float:
        return int(math.floor(value))
    else :
        return value


#***********************************************************************************************************************
# GridFix
#***********************************************************************************************************************
def GridFix(x):
    return fix(x*SG13_IGRID+SG13_EPSILON)*SG13_GRID         # always use "nice" numbers, as 1/grid may be irrational
