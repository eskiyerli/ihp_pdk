#    "Commons Clause" License Condition v1.0
#   #
#    The Software is provided to you by the Licensor under the License, as defined
#    below, subject to the following condition.
#
#    Without limiting other conditions in the License, the grant of rights under the
#    License will not include, and the License does not grant to you, the right to
#    Sell the Software.
#
#    For purposes of the foregoing, "Sell" means practicing any or all of the rights
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

import math
from quantiphy import Quantity


class baseInst:
    def __init__(self, labels_dict: dict):
        self._labelsDict = labels_dict

    def __repr__(self):
        return f"{self.__class__.__name__}({self._labelsDict})"


class annotate_bip_params(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)


class annotate_fet_params(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)


class bondpad(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)


class cap_cmim(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.W = Quantity(self._labelsDict["@w"].labelValue)
        self.L = Quantity(self._labelsDict["@l"].labelValue)
        self.MF = Quantity(self._labelsDict["@mf"].labelValue)

    def C_parm(self):
        return self.MF * (self.W * self.L * 1.5e-3 + 2 * (self.W + self.L) * 40e-12)


class cap_cpara(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.C = Quantity(self._labelsDict["@C"].labelValue)


class cap_rfcmim(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.W = Quantity(self._labelsDict["@w"].labelValue)
        self.L = Quantity(self._labelsDict["@l"].labelValue)
        self.wfeed = Quantity(self._labelsDict["@wfeed"].labelValue)

    def C_parm(self):
        return self.W * self.L * 1.5e-3 + 2 * (self.W + self.L) * 40e-12


class dantenna(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.l = Quantity(self._labelsDict["@l"].labelValue)
        self.w = Quantity(self._labelsDict["@w"].labelValue)


class diodevdd_2kv(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.m = Quantity(self._labelsDict["@m"].labelValue)


class diodevdd_4kv(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.m = Quantity(self._labelsDict["@m"].labelValue)


class diodevss_2kv(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.m = Quantity(self._labelsDict["@m"].labelValue)


class diodevss_4kv(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.m = Quantity(self._labelsDict["@m"].labelValue)


class dpantenna(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.l = Quantity(self._labelsDict["@l"].labelValue)
        self.w = Quantity(self._labelsDict["@w"].labelValue)


class idiodevdd_2kv(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.m = Quantity(self._labelsDict["@m"].labelValue)


class idiodevdd_4kv(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.m = Quantity(self._labelsDict["@m"].labelValue)


class idiodevss_2kv(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.m = Quantity(self._labelsDict["@m"].labelValue)


class idiodevss_4kv(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.m = Quantity(self._labelsDict["@m"].labelValue)


class inductorBase(baseInst):
    """
    Base callback class for SG13G2 inductors.
    Evaluates inductance (L_parm), resistance (R_parm), quality factor (Q_parm),
    and self-resonance frequency (SRF_parm) from instance labels
    (@w, @s, @d, @nr_r; optional @subE for substrate-etched variants).
    """
    default_d = "15.48u"
    default_nr = "1"

    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.w = Quantity(self._getLabelVal(["@w", "@W"], "2u"))
        self.s = Quantity(self._getLabelVal(["@s", "@S"], "2.1u"))
        self.d = Quantity(self._getLabelVal(["@d", "@D"], getattr(self, "default_d", "15.48u")))
        self.nr_r = Quantity(self._getLabelVal(["@nr_r", "@nr", "@N"], getattr(self, "default_nr", "1")))
        self.subE = self._getLabelVal(["@subE", "@sube"], "False")

    def _getLabelVal(self, keys: list, default: str):
        for k in keys:
            if k in self._labelsDict:
                val = getattr(self._labelsDict[k], "labelValue", self._labelsDict[k])
                if val not in (None, "", "?"):
                    return str(val)
        return default

    def L_parm(self):
        """Estimate series inductance (H) using Modified Wheeler formula for octagons."""
        d_in = self.d.real
        w = self.w.real
        s = self.s.real
        n = float(self.nr_r.real)

        d_out = d_in + 2 * n * w + 2 * (n - 1) * s
        d_avg = 0.5 * (d_in + d_out)
        fill_factor = (d_out - d_in) / (d_out + d_in) if (d_out + d_in) > 0 else 0.0

        k1, k2 = 2.25, 3.55
        mu_0 = 4 * math.pi * 1e-7
        return k1 * mu_0 * (n ** 2) * d_avg / (1 + k2 * fill_factor) if (1 + k2 * fill_factor) > 0 else 0.0

    def R_parm(self):
        """Estimate series resistance (Ohm) including skin effect on TM2 at 5 GHz."""
        d_in = self.d.real
        w = self.w.real
        s = self.s.real
        n = float(self.nr_r.real)
        freq_hz = 5.0e9

        d_out = d_in + 2 * n * w + 2 * (n - 1) * s
        d_avg = 0.5 * (d_in + d_out)
        l_total = 4 * n * d_avg

        rho_tm2 = 0.007 * 3.0e-6
        mu_0 = 4 * math.pi * 1e-7
        delta = math.sqrt(rho_tm2 / (math.pi * freq_hz * mu_0))
        t_eff = 3.0e-6 * (1 - math.exp(-3.0e-6 / delta))

        return (rho_tm2 * l_total) / (w * t_eff) if (w * t_eff) > 0 else 0.0

    def Q_parm(self):
        """Estimate quality factor at 5 GHz."""
        w_rad = 2 * math.pi * 5.0e9
        r_val = self.R_parm()
        return (w_rad * self.L_parm()) / r_val if r_val > 0 else 0.0

    def _parasiticCap(self):
        """Estimate total winding parasitic capacitance (F).

        Sum of the winding-to-substrate oxide capacitance through the IMD
        stack and the lateral capacitance between adjacent turns. When the
        substrate is etched below the inductor (subE), the oxide term is
        dropped.
        """
        eps_ox = 8.854e-12 * 4.1   # SiO2 IMD permittivity
        t_ox = 10.0e-6             # effective IMD height, TopMetal2 to substrate
        t_m = 3.0e-6               # TopMetal2 thickness

        w = self.w.real
        s = self.s.real
        n = float(self.nr_r.real)
        d_in = self.d.real

        d_out = d_in + 2 * n * w + 2 * (n - 1) * s
        d_avg = 0.5 * (d_in + d_out)
        l_total = 4 * n * d_avg

        subEtched = str(self.subE).strip().lower() in ("true", "1", "yes")
        # 1/2 factor: winding voltage distributes evenly along the spiral
        c_ox = 0.0 if subEtched else eps_ox * w * l_total / (2 * t_ox)
        l_side = l_total / n if n > 0 else 0.0
        c_lat = eps_ox * t_m * l_side * (n - 1) / s if s > 0 else 0.0
        return c_ox + c_lat

    def SRF_parm(self):
        """Estimate self-resonance frequency (Hz) = 1 / (2*pi*sqrt(L*C))."""
        c_total = self._parasiticCap()
        l_val = self.L_parm()
        if c_total <= 0 or l_val <= 0:
            return 0.0
        return 1.0 / (2 * math.pi * math.sqrt(l_val * c_total))


class inductor2(inductorBase):
    """Callback class for 2-terminal octagonal inductor."""
    default_d = "15.48u"
    default_nr = "1"


class inductor3(inductorBase):
    """Callback class for 3-terminal center-tapped octagonal inductor."""
    default_d = "25.84u"
    default_nr = "2"


class inductor(inductorBase):
    """Generic inductor alias."""
    pass


class nmoscl_2(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.m = Quantity(self._labelsDict["@m"].labelValue)


class nmoscl_4(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.m = Quantity(self._labelsDict["@m"].labelValue)


class npn13G2(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.Nx = Quantity(self._labelsDict["@Nx"].labelValue)


class npn13G2_5t(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.Nx = Quantity(self._labelsDict["@Nx"].labelValue)


class npn13G2l(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.Nx = Quantity(self._labelsDict["@Nx"].labelValue)
        self.El = Quantity(self._labelsDict["@El"].labelValue)


class npn13G2l_5t(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.Nx = Quantity(self._labelsDict["@Nx"].labelValue)
        self.El = Quantity(self._labelsDict["@El"].labelValue)


class npn13G2v(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.Nx = Quantity(self._labelsDict["@Nx"].labelValue)
        self.El = Quantity(self._labelsDict["@El"].labelValue)


class npn13G2v_5t(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.Nx = Quantity(self._labelsDict["@Nx"].labelValue)
        self.El = Quantity(self._labelsDict["@El"].labelValue)


class ntap1(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.w = Quantity(self._labelsDict["@w"].labelValue)
        self.l = Quantity(self._labelsDict["@l"].labelValue)

    def R_parm(self):
        area_term = 9.8e-10 / (self.w * self.l)
        perimeter_term = 9.8e-4 / (2.0 * (self.w + self.l))
        return 1.0 / (1.0 / area_term + 1.0 / perimeter_term)


class pnpMPA(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.w = Quantity(self._labelsDict["@w"].labelValue)
        self.l = Quantity(self._labelsDict["@l"].labelValue)

    def a_parm(self):
        return self.w * self.l

    def p_parm(self):
        return 2 * (self.w + self.l)


class ptap1(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)

        self.w = Quantity(self._labelsDict["@w"].labelValue)
        self.l = Quantity(self._labelsDict["@l"].labelValue)

    def R_parm(self):
        area_term = 9.8e-10 / (self.w * self.l)
        perimeter_term = 9.8e-4 / (2.0 * (self.w + self.l))
        return 1.0 / (1.0 / area_term + 1.0 / perimeter_term)


class rhigh(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.W = Quantity(self._labelsDict["@w"].labelValue)
        self.L = Quantity(self._labelsDict["@l"].labelValue)
        self.b = Quantity(self._labelsDict["@b"].labelValue)
        self.m = Quantity(self._labelsDict["@m"].labelValue)

    def R_parm(self):
        return (
                1.6e-4 / self.W
                + 1360.0
                * ((self.b + 1) * self.L + (1.081 * (self.W - 0.04e-6) + 0.18e-6) * self.b)
                / (self.W - 0.04e-6)
        ) / self.m


class rppd(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.W = Quantity(self._labelsDict["@w"].labelValue)
        self.L = Quantity(self._labelsDict["@l"].labelValue)
        self.b = Quantity(self._labelsDict["@b"].labelValue)
        self.m = Quantity(self._labelsDict["@m"].labelValue)

    def R_parm(self):
        return (
                70.0e-6 / self.W
                + 260.0
                * ((self.b + 1) * self.L + (1.081 * (self.W + 6.0e-9) + 0.18e-6) * self.b)
                / (self.W + 6.0e-9)
        ) / self.m


class rsil(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.w = Quantity(self._labelsDict["@w"].labelValue)
        self.l = Quantity(self._labelsDict["@l"].labelValue)
        self.b = Quantity(self._labelsDict["@b"].labelValue)
        self.m = Quantity(self._labelsDict["@m"].labelValue)

    def R_parm(self):
        return (
                9.0e-6 / self.w
                + 7.0
                * ((self.b + 1) * self.l + (1.081 * (self.w + 1.0e-8) + 0.18e-6) * self.b)
                / (self.w + 1.0e-8)
        ) / self.m


class sg13_hv_nmos(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.L = Quantity(self._labelsDict["@l"].labelValue)
        self.W = Quantity(self._labelsDict["@w"].labelValue)
        self.ng = Quantity(self._labelsDict["@ng"].labelValue)
        self.m = Quantity(self._labelsDict["@m"].labelValue)


class sg13_hv_pmos(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.L = Quantity(self._labelsDict["@l"].labelValue)
        self.W = Quantity(self._labelsDict["@w"].labelValue)
        self.ng = Quantity(self._labelsDict["@ng"].labelValue)
        self.m = Quantity(self._labelsDict["@m"].labelValue)


class sg13_hv_rf_nmos(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.L = Quantity(self._labelsDict["@l"].labelValue)
        self.W = Quantity(self._labelsDict["@w"].labelValue)
        self.ng = Quantity(self._labelsDict["@ng"].labelValue)
        self.m = Quantity(self._labelsDict["@m"].labelValue)
        self.rfmode = Quantity(self._labelsDict["@rfmode"].labelValue)


class sg13_hv_rf_pmos(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.L = Quantity(self._labelsDict["@l"].labelValue)
        self.W = Quantity(self._labelsDict["@w"].labelValue)
        self.ng = Quantity(self._labelsDict["@ng"].labelValue)
        self.m = Quantity(self._labelsDict["@m"].labelValue)
        self.rfmode = Quantity(self._labelsDict["@rfmode"].labelValue)


class sg13_lv_nmos(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.L = Quantity(self._labelsDict["@l"].labelValue)
        self.W = Quantity(self._labelsDict["@w"].labelValue)
        self.ng = Quantity(self._labelsDict["@ng"].labelValue)
        self.m = Quantity(self._labelsDict["@m"].labelValue)


class sg13_lv_pmos(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.L = Quantity(self._labelsDict["@l"].labelValue)
        self.W = Quantity(self._labelsDict["@w"].labelValue)
        self.ng = Quantity(self._labelsDict["@ng"].labelValue)
        self.m = Quantity(self._labelsDict["@m"].labelValue)


class sg13_lv_rf_nmos(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.L = Quantity(self._labelsDict["@l"].labelValue)
        self.W = Quantity(self._labelsDict["@w"].labelValue)
        self.ng = Quantity(self._labelsDict["@ng"].labelValue)
        self.m = Quantity(self._labelsDict["@m"].labelValue)
        self.rfmode = Quantity(self._labelsDict["@rfmode"].labelValue)


class sg13_lv_rf_pmos(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.L = Quantity(self._labelsDict["@l"].labelValue)
        self.W = Quantity(self._labelsDict["@w"].labelValue)
        self.ng = Quantity(self._labelsDict["@ng"].labelValue)
        self.m = Quantity(self._labelsDict["@m"].labelValue)
        self.rfmode = Quantity(self._labelsDict["@rfmode"].labelValue)


class sg13_svaricap(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.l = Quantity(self._labelsDict["@l"].labelValue)
        self.w = Quantity(self._labelsDict["@w"].labelValue)
        self.Nx = Quantity(self._labelsDict["@Nx"].labelValue)


class sub(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
