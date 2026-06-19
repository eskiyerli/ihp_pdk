# IHP PDK PCell Implementation Status

This document summarizes the parametric cell (pcell) implementations in the ihp_pdk/pcells module for the IHP SG13G2 process.

## Summary

**Total PCells Implemented: 20**

All pcells registered in the module's `__init__.py` are fully implemented with layout generation logic.

## PCell Details

| Category | PCell Name | File | Description | Parameters | Status |
|----------|------------|------|-------------|------------|--------|
| **Base Classes** | baseCell | base.py | Base class for all layout pcells (grid fixing, coordinate conversion, contact arrays) | N/A | ✅ Implemented |
| | baseMosfet | base.py | Base class for MOSFET devices (common gate/diffusion/contact logic) | N/A | ✅ Implemented |
| | baseRfMosfet | base.py | Base class for RF MOSFET devices (guard rings, gate rings) | N/A | ✅ Implemented |
| **Resistors** | rsil | passive.py | Silicide polysilicon resistor with bends | length, width, b (bends), ps (poly space) | ✅ Implemented |
| | rhigh | passive_res_variants.py | High-ohmic resistor (extends rsil with SalBlock, pSD/nSD implants) | length, width, b, ps | ✅ Implemented |
| | rppd | passive_res_variants.py | P-poly diffusion resistor (extends rsil with pSD implant) | length, width, b, ps | ✅ Implemented |
| **Capacitors** | cmim | passive.py | Metal-insulator-metal capacitor | width, length | ✅ Implemented |
| **Standard MOSFETs** | nmos | mosfet.py | N-channel MOSFET | width, length, ng (number of gates) | ✅ Implemented |
| | pmos | mosfet.py | P-channel MOSFET (with NWell, pSD) | width, length, ng | ✅ Implemented |
| **High-Voltage MOSFETs** | nmosHV | mosfet_hv.py | High-voltage N-channel MOSFET (with ThickGateOx) | width, length, ng | ✅ Implemented |
| | pmosHV | mosfet_hv.py | High-voltage P-channel MOSFET (with ThickGateOx, NWell) | width, length, ng | ✅ Implemented |
| **RF MOSFETs** | rfnmos | rf_mosfet.py | RF N-channel MOSFET (with guard ring, gate ring options) | width, length, ng, cnt_rows, Met2Cont, gat_ring, guard_ring | ✅ Implemented |
| | rfpmos | rf_mosfet.py | RF P-channel MOSFET (with guard ring, gate ring, NWell) | width, length, ng, cnt_rows, Met2Cont, gat_ring, guard_ring | ✅ Implemented |
| **BJTs** | npn13G2 | bjt.py | Standard NPN BJT (1-10 emitter fingers) | Nx (fingers), le (emitter length), we (emitter width) | ✅ Implemented |
| | npn13G2V | bjt.py | High-voltage NPN variant (wider emitter, 1-8 fingers) | Nx, le, we | ✅ Implemented |
| | npn13G2L | bjt.py | Low-noise NPN variant (narrower emitter, 1-4 fingers) | Nx, le, we | ✅ Implemented |
| | pnpMPA | bjt.py | Lateral PNP transistor (concentric ring structure) | width, length | ✅ Implemented |
| **Diodes** | dantenna | diodes.py | N-type ESD protection diode (N+/P-substrate) | width, length | ✅ Implemented |
| | dpantenna | diodes.py | P-type ESD protection diode (P+/N-well in isolated well) | width, length | ✅ Implemented |
| | schottky | schottky.py | N+/Metal Schottky diode with guard rings and thermal vias | w, l, Nx, Ny (array), m (multiplier) | ✅ Implemented |
| **Tap Contacts** | ntap1 | tap_contacts.py | N-type substrate tap contact (N-well with nBuLay) | width, length | ✅ Implemented |
| | ptap1 | tap_contacts.py | P-type substrate tap contact (P+ diffusion) | width, length | ✅ Implemented |
| **Utility** | NoFillerStack | nofiller_stack.py | DRC filler exclusion marker (per-layer nofill rectangles) | w, l, noAct, noGP, noM1-5, noTM1-2 | ✅ Implemented |

## Implementation Notes

### Architecture
- All pcells inherit from `baseCell` which provides:
  - Grid fixing (`GridFix()`) for layout coordinate alignment
  - Scene/layout coordinate conversion (`toSceneCoord()`, `toLayoutCoord()`)
  - Contact array generation (`contactArray()`)
  - Thermal layer addition (`ihpAddThermalLayer()`)
  - Technology parameter access via `baseCell._techParams`

### MOSFET Hierarchy
- `baseMosfet` provides common MOSFET geometry (gate poly, diffusion, contacts)
- Standard MOSFETs (`nmos`, `pmos`) extend `baseMosfet`
- High-voltage variants (`nmosHV`, `pmosHV`) extend standard MOSFETs with ThickGateOx layer
- RF variants (`rfnmos`, `rfpmos`) use `baseRfMosfet` with guard ring and gate ring options

### Resistor Hierarchy
- `rsil` is the base silicide resistor with bend support
- `rhigh` extends `rsil` with SalBlock protection and pSD/nSD implant layers
- `rppd` extends `rsil` with SalBlock and pSD implant only

### BJT Implementations
- All BJT pcells are faithful ports of the original KLayout geometry
- Use hard-coded coordinate offsets matching the original design
- NPN variants support multi-finger arrays (Nx parameter)
- `pnpMPA` uses concentric ring polygons (replaces XOR operations from original)

### Diode Implementations
- `dantenna` and `dpantenna` replicate the original `DrawContArray` logic
- Include large-array spacing rules for contact grids
- `schottky` features dual Via1 for current distribution and four-sided pSD guard rings

### Parameter Handling
- All pcells use `quantiphy.Quantity` for parameter parsing (e.g., "4u" → 4e-6 meters)
- Minimum dimension enforcement with clamping and warning messages
- `@lru_cache` decorators for parameter caching where applicable

## Module Structure

```
ihp_pdk/pcells/
├── __init__.py              # Pcell registry (pcells dict)
├── base.py                  # Base classes (baseCell, baseMosfet, baseRfMosfet)
├── mosfet.py                # Standard MOSFETs (nmos, pmos)
├── mosfet_hv.py             # High-voltage MOSFETs (nmosHV, pmosHV)
├── rf_mosfet.py             # RF MOSFETs (rfnmos, rfpmos)
├── passive.py               # Resistors and capacitors (rsil, cmim)
├── passive_res_variants.py  # Resistor variants (rhigh, rppd)
├── bjt.py                   # Bipolar transistors (npn13G2, npn13G2V, npn13G2L, pnpMPA)
├── diodes.py                # ESD diodes (dantenna, dpantenna)
├── schottky.py              # Schottky diode
├── tap_contacts.py          # Substrate taps (ntap1, ptap1)
└── nofiller_stack.py        # Filler exclusion marker
```

## Technology Parameters

All pcells reference technology parameters from `sg13_tech.SG13_Tech().techParams`, including:
- Contact dimensions (`Cnt_a`, `Cnt_b`, `Cnt_c`, etc.)
- Metal overhang rules (`M1_c`, `M1_c1`, etc.)
- Gate oxide rules (`Gat_c`, `Gat_d`, etc.)
- Well enclosure rules (`NW_c`, `pSD_c`, etc.)
- Device-specific minimums and defaults (e.g., `nmos_minW`, `pmos_defL`)

## Licensing

All pcell implementations are licensed under the Apache License 2.0, per the IHP PDK license requirements.
