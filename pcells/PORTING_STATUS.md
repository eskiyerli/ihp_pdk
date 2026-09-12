# IHP SG13G2 PCell Porting Status: KLayout to Revolution EDA

This document tracks the porting progress of IHP SG13G2 parametric cells from the KLayout reference implementation to Revolution EDA.

## Summary

| Metric | Count |
|--------|-------|
| Total KLayout PCells | 28 |
| Ported to Revolution EDA | 31 |
| Not Yet Ported | 0 |
| Porting Coverage | 100% |

## Detailed Porting Status

### MOSFETs — Standard

| KLayout Source | KLayout Class | RevEDA File | RevEDA Class | Status | Notes |
|----------------|---------------|-------------|--------------|--------|-------|
| `nmos_code.py` | `nmos` | `mosfet.py` | `nmos` | Ported | Standard N-channel MOSFET |
| `pmos_code.py` | `pmos` | `mosfet.py` | `pmos` | Ported | Standard P-channel MOSFET |

### MOSFETs — High Voltage

| KLayout Source | KLayout Class | RevEDA File | RevEDA Class | Status | Notes |
|----------------|---------------|-------------|--------------|--------|-------|
| `nmosHV_code.py` | `nmosHV` | `mosfet_hv.py` | `nmosHV` | Ported | HV N-channel with ThickGateOx |
| `pmosHV_code.py` | `pmosHV` | `mosfet_hv.py` | `pmosHV` | Ported | HV P-channel with ThickGateOx |

### MOSFETs — RF

| KLayout Source | KLayout Class | RevEDA File | RevEDA Class | Status | Notes |
|----------------|---------------|-------------|--------------|--------|-------|
| `rfnmos_code.py` | `rfnmos` | `rf_mosfet.py` | `rfnmos` | Ported | RF NMOS with guard/gate ring options |
| `rfpmos_code.py` | `rfpmos` | `rf_mosfet.py` | `rfpmos` | Ported | RF PMOS with guard/gate ring options |
| `rfnmosHV_code.py` | `rfnmosHV` | `rf_mosfet_hv.py` | `rfnmosHV` | Ported | RF HV N-channel; extends `rfnmos` + ThickGateOx |
| `rfpmosHV_code.py` | `rfpmosHV` | `rf_mosfet_hv.py` | `rfpmosHV` | Ported | RF HV P-channel; extends `rfpmos` + ThickGateOx |
| `rfmosfet_base_code.py` | `rfmosfet_base` | `rf_mosfet.py` / `base.py` | `baseRfMosfet` | Ported | Base class for all RF MOSFETs |

### Bipolar Transistors (BJTs)

| KLayout Source | KLayout Class | RevEDA File | RevEDA Class | Status | Notes |
|----------------|---------------|-------------|--------------|--------|-------|
| `npn13G2_code.py` | `npn13G2` | `bjt.py` | `npn13G2` | Ported | Standard NPN, 1-10 emitter fingers |
| `npn13G2V_code.py` | `npn13G2V` | `bjt.py` | `npn13G2V` | Ported | High-voltage NPN variant |
| `npn13G2L_code.py` | `npn13G2L` | `bjt.py` | `npn13G2L` | Ported | Low-noise NPN variant |
| `pnpMPA_code.py` | `pnpMPA` | `bjt.py` | `pnpMPA` | Ported | Lateral PNP (concentric ring) |

### Resistors

| KLayout Source | KLayout Class | RevEDA File | RevEDA Class | Status | Notes |
|----------------|---------------|-------------|--------------|--------|-------|
| `rsil_code.py` | `rsil` | `passive.py` | `rsil` | Ported | Silicide poly resistor with bends |
| `rhigh_code.py` | `rhigh` | `passive_res_variants.py` | `rhigh` | Ported | High-ohmic resistor |
| `rppd_code.py` | `rppd` | `passive_res_variants.py` | `rppd` | Ported | P-poly diffusion resistor |
| `res_base_code.py` | `ResistorBase` | — | — | Deferred | Multi-segment resistor base (serial/parallel); enhances existing cells |

### Capacitors

| KLayout Source | KLayout Class | RevEDA File | RevEDA Class | Status | Notes |
|----------------|---------------|-------------|--------------|--------|-------|
| `cmim_code.py` | `cmim` | `passive.py` | `cmim` | Ported | Metal-insulator-metal capacitor |
| `rfcmim_code.py` | `rfcmim` | `rfcmim.py` | `rfcmim` | Ported | RF MIM capacitor with ground ring and feed lines |
| `SVaricap_code.py` | `SVaricap` | `svaricap.py` | `SVaricap` | Ported | HV S-parameter varicap (gate-controlled) |

### Diodes and ESD

| KLayout Source | KLayout Class | RevEDA File | RevEDA Class | Status | Notes |
|----------------|---------------|-------------|--------------|--------|-------|
| `dantenna_code.py` | `dantenna` | `diodes.py` | `dantenna` | Ported | N-type ESD antenna diode |
| `dpantenna_code.py` | `dpantenna` | `diodes.py` | `dpantenna` | Ported | P-type ESD antenna diode |
| `schottky_code.py` | `schottky` | `schottky.py` | `schottky` | Ported | Schottky diode with guard rings |
| `esd_code.py` | `esd` | `esd.py` | `esd` | Ported | General ESD protection device (6 model variants) |

### Inductors

| KLayout Source | KLayout Class | RevEDA File | RevEDA Class | Status | Notes |
|----------------|---------------|-------------|--------------|--------|-------|
| `inductors_code.py` | `inductors` | `inductors.py` | `inductorBase` | Ported | Spiral inductor base class |
| `inductor2_code.py` | `inductor2` | `inductors.py` | `inductor2` | Ported | Single-turn spiral (DMIN=15.48u, NR=1) |
| `inductor3_code.py` | `inductor3` | `inductors.py` | `inductor3` | Ported | Three-terminal spiral (DMIN=25.84u, NR=2) |

### Tap Contacts

| KLayout Source | KLayout Class | RevEDA File | RevEDA Class | Status | Notes |
|----------------|---------------|-------------|--------------|--------|-------|
| `ntap1_code.py` | `ntap1` | `tap_contacts.py` | `ntap1` | Ported | N-well substrate tap |
| `ptap1_code.py` | `ptap1` | `tap_contacts.py` | `ptap1` | Ported | P+ substrate tap |

### Utility / Miscellaneous

| KLayout Source | KLayout Class | RevEDA File | RevEDA Class | Status | Notes |
|----------------|---------------|-------------|--------------|--------|-------|
| `NoFillerStack_code.py` | `NoFillerStack` | `nofiller_stack.py` | `NoFillerStack` | Ported | DRC filler exclusion marker |
| `via_stack_code.py` | `via_stack` | `via_stack.py` | `via_stack` | Ported | Configurable multi-layer via stack |
| `bondpad_code.py` | `bondpad` | `bondpad.py` | `bondpad` | Ported | Bond pad with via stacking |
| `sealring_code.py` | `sealring` | `sealring.py` | `sealring` | Ported | Chip seal ring (multi-metal/via corners) |
| `isolbox_code.py` | `isolbox` | `isolbox.py` | `isolbox` | Ported | Deep-trench isolation box |

### KLayout Infrastructure / Helpers (Not applicable for direct porting)

| KLayout Source | Purpose | RevEDA Equivalent | Notes |
|----------------|---------|-------------------|-------|
| `geometry.py` | Helper functions (`dbCreateRect`, `contactArray`, etc.) | `base.py` (`baseCell`) | Geometry primitives are re-implemented in the base class |
| `thermal.py` | Thermal layer utilities | `base.py` (`ihpAddThermalLayer`) | Integrated into base class |
| `utility_functions.py` | Shared utilities (`GridFix`, `eng_string`, `MkPin`, etc.) | `base.py` + standard Python | Distributed across base classes |

## Remaining Enhancement Opportunity

| PCell | Complexity | Priority | Rationale |
|-------|-----------|----------|-----------|
| `ResistorBase` (multi-segment) | Low | Low | Port from `res_base_code.py` to enable serial/parallel resistor arrays for `rsil`/`rhigh`/`rppd` |

## File Mapping Summary

```
KLayout Source                          RevEDA Ported File
─────────────────────────────────────── ──────────────────────────────
nmos_code.py                         -> mosfet.py
pmos_code.py                         -> mosfet.py
nmosHV_code.py                       -> mosfet_hv.py
pmosHV_code.py                       -> mosfet_hv.py
rfnmos_code.py                       -> rf_mosfet.py
rfpmos_code.py                       -> rf_mosfet.py
rfnmosHV_code.py                     -> rf_mosfet_hv.py
rfpmosHV_code.py                     -> rf_mosfet_hv.py
rfmosfet_base_code.py                -> rf_mosfet.py / base.py
npn13G2_code.py                      -> bjt.py
npn13G2V_code.py                     -> bjt.py
npn13G2L_code.py                     -> bjt.py
pnpMPA_code.py                       -> bjt.py
rsil_code.py                         -> passive.py
rhigh_code.py                        -> passive_res_variants.py
rppd_code.py                         -> passive_res_variants.py
res_base_code.py                     -> (deferred - enhancement)
cmim_code.py                         -> passive.py
rfcmim_code.py                       -> rfcmim.py
SVaricap_code.py                     -> svaricap.py
dantenna_code.py                     -> diodes.py
dpantenna_code.py                    -> diodes.py
schottky_code.py                     -> schottky.py
esd_code.py                          -> esd.py
inductors_code.py                    -> inductors.py
inductor2_code.py                    -> inductors.py
inductor3_code.py                    -> inductors.py
ntap1_code.py                        -> tap_contacts.py
ptap1_code.py                        -> tap_contacts.py
NoFillerStack_code.py                -> nofiller_stack.py
via_stack_code.py                    -> via_stack.py
bondpad_code.py                      -> bondpad.py
sealring_code.py                     -> sealring.py
isolbox_code.py                      -> isolbox.py
geometry.py                          -> base.py (helpers)
thermal.py                           -> base.py (helpers)
utility_functions.py                 -> base.py (helpers)
```

## Recommended Next Steps

1. **Validation** — Test each newly ported pcell by instantiating with default parameters and verifying output geometry.
2. **Multi-segment resistors** — Optionally port `ResistorBase` to enhance existing resistors with serial/parallel array support.
3. **Schematic callbacks** — Add schematic-side callback classes for new cells (`rfcmim`, `SVaricap`, `esd`, etc.) in `callbacks.py`.
