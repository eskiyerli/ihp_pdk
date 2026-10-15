# IHP SG13G2 Process Design Kit (PDK) for Revolution EDA

A comprehensive Python-based Process Design Kit (PDK) for the **IHP SG13G2 130nm BiCMOS technology** integrated with the **Revolution EDA** open-source IC design environment.

## Overview

This PDK provides complete design automation support for IHP's SG13G2 process node, including:

- **Parametric layout cells (pcells)** for automated device and passive component generation
- **A complete device library** (`sg13g2_pr`) pairing schematic symbols with pcell layout views
- **Instance parameter callbacks** for electrical parameter computation
- **Schematic and symbol layer definitions** for front-end design
- **Layout layer definitions** with GDS layer/datatype mappings
- **Design Rule Checking (DRC)** and **Layout vs. Schematic (LVS)** integration via KLayout
- **RC parasitic extraction (PEX)** with process-corner technology data
- **Xyce and VACASK simulation models**, including compiled Verilog-A/OSDI modules

**Technology Details:**
- **Process Node:** SG13G2 (IHP 130nm SiGe BiCMOS)
- **PDK Version:** 0.3.0
- **License:** Apache 2.0 

---

## What's Implemented

### 1. Parametric Cells (PCell Library)

The PDK ports the complete IHP KLayout pcell set to Revolution EDA — **42 registered pcells** covering every device family (see `pcells/PCELL_STATUS.md` and `pcells/PORTING_STATUS.md` for details):

#### MOSFETs

| Cell | Description | Parameters |
|------|-------------|------------|
| **nmos / pmos** | Standard MOSFETs with configurable fingers | `width`, `length`, `ng` (number of gates) |
| **nmosHV / pmosHV** | High-voltage MOSFETs with ThickGateOx | `width`, `length`, `ng` |
| **rfnmos / rfpmos** | RF MOSFETs with guard/gate ring options | `width`, `length`, `ng`, `cnt_rows`, `Met2Cont`, `gat_ring`, `guard_ring` |
| **rfnmosHV / rfpmosHV** | RF high-voltage MOSFETs | same as RF variants plus ThickGateOx |

#### Passive Components

| Cell | Description | Parameters |
|------|-------------|------------|
| **rsil** | Silicide polysilicon resistor (meander pattern) | `length`, `width`, `b` (bends), `ps` (poly spacing) |
| **rhigh** | High-ohmic resistor (SalBlock + implants) | `length`, `width`, `b`, `ps` |
| **rppd** | P-poly diffusion resistor | `length`, `width`, `b`, `ps` |
| **cmim** | Metal-insulator-metal capacitor | `w`, `l`, `mf` (multiplier factor) |
| **rfcmim** | RF MIM capacitor with ground ring and feed lines | geometry + ring options |
| **SVaricap** | HV S-parameter varicap (gate-controlled) | `w`, `l`, array parameters |
| **inductor2 / inductor3** | Spiral inductors (two- and three-terminal) | `DMIN`, `NR` (turns), geometry |

#### Bipolar, Diodes, and ESD

| Cell | Description |
|------|-------------|
| **npn13G2 / npn13G2V / npn13G2L** | NPN HBTs (standard, high-voltage, low-noise) with 1–10 emitter fingers |
| **pnpMPA** | Lateral PNP transistor (concentric ring structure) |
| **dantenna / dpantenna** | N-type and P-type ESD protection diodes |
| **schottky** | N+/Metal Schottky diode with guard rings and thermal vias |
| **esd, diodevdd/vss_2kv, diodevdd/vss_4kv, nmoscl_2, nmoscl_4** | ESD protection device family |

#### Taps, Rings, and Utilities

| Cell | Description |
|------|-------------|
| **ntap1 / ptap1** | N-well and P+ substrate tap contacts |
| **subtap / nwtap / psubtap / nwelltap** | Connectivity and minimum-width tap lines |
| **guardRing** | Parametric multi-part guard ring (p+ substrate or n+ n-well) |
| **via_stack** | Configurable multi-layer via stack |
| **bondpad / sealring / isolbox** | Bond pad, chip seal ring, deep-trench isolation box |
| **NoFillerStack** | DRC filler exclusion marker (per-layer nofill rectangles) |

**Key Features:**
- All pcells generate layout at instantiation time with technology-aware grid snapping
- Automatic contact array placement with correct spacing and alignment
- Multi-finger and multi-unit device configurations
- RF variants include guard rings, gate rings, and shielding for low-noise applications
- 100% coverage of the IHP KLayout pcell reference set

### 2. Device Symbol Library

The `sg13g2_pr` library ships **45 device cells** — schematic symbols with matching pcell layout views for most devices — covering LV/HV/RF MOSFETs, BJTs (including five-terminal variants), resistors, capacitors, inductors, diodes, ESD devices, substrate taps, and bond pads.

### 3. Instance Callbacks

The `callbacks.py` module provides automatic electrical parameter computation for 45 device classes:

**Capacitor Classes:**
- `cap_cmim` - Metal-insulator-metal capacitor with calculated capacitance
- `cap_cpara` - Parameterized capacitor
- `cap_rfcmim` - RF-optimized MIM capacitor

**MOSFETs:**
- NMOS/PMOS variants (low-voltage, high-voltage, thick-oxide gate)
- Multiple drive strengths

**Passive Devices:**
- Resistors (silicon, polysilicon, high-resistance)
- Diodes (various junction types and configurations)

**Other Devices:**
- HBT (Heterojunction Bipolar Transistor) models
- ESD protection structures
- Bond pads and antenna structures

**Example:** When you instantiate a `cap_cmim` device with width and length parameters, the callback automatically calculates its capacitance using the formula:
```python
C = MF × (W × L × 1.5e-3 + 2 × (W + L) × 40e-12)
```

### 4. Layer Definitions

#### Schematic/Symbol Layers (schLayers.py / symLayers.py)

The PDK defines comprehensive schematic drawing layers:

- **Wire layers:** Standard signal wires, error indication, selection highlighting
- **Bus layers:** Multi-signal buses with distinctive appearance
- **Component layers:** Pin labels, port connections, annotation text
- **Structural layers:** Symbolic representation of devices (rectangles, circles, polygons)

Each layer is a PySide6 Qt graphics-enabled dataclass with configurable:
- Colors, line styles, line widths
- Fill patterns and brush styles
- Z-order (rendering depth)
- Visibility and selectability toggles

#### Layout Layers (layoutLayers.py)

Complete layout layer set for GDS II file I/O covering the full SG13G2 stack:

**Metallization Layers:**
- Metal1–Metal5 (drawing + pin layers)
- TopMetal1–TopMetal2 thick top metals
- Via1–Via4, TopVia1–TopVia2, and contact layers

**Active Device Layers:**
- Active region (Activ_drawing)
- N-well, P-well (NWell_drawing, pBuLay_drawing)
- Gate poly (GatPoly_drawing, GatPoly_pin)

**Mask Definition Layers:**
- Thick gate oxide (ThickGateOx_drawing)
- Implant layers (pSD_drawing, nBuLay_drawing)
- High-voltage layers for 3.3V/6V devices

**Special Layers:**
- Polysilicon resistor mask (PolyRes_drawing)
- MIM capacitor (MIM_drawing, Vmim_drawing)
- Externally defined blocks (EXTBlock_drawing)
- Heat transfer annotation (HeatTrans_drawing)

Each layout layer is mapped to specific GDS layer/datatype pairs per IHP specifications.

### 5. Design Rule Checking (DRC)

**KLayout DRC Integration:**
- Headless KLayout execution against the SG13G2 rule decks in `drc/rule_decks/`
- Full deck suite: `sg13g2_maximal.drc` plus FEOL, BEOL, geometry, pin, density, antenna, and forbidden-layer rule tables
- Menu integration: `Check → DRC with KLayout...` (Ctrl+Shift+D)
- Flat or deep run modes, per-table selection, and optional density/antenna subsets
- Rule categories: verified PreCheck set, full Main rule set, and an optional unverified Extra set

DRC violations are parsed and displayed as a table with:
- Error classification (layer/rule pair)
- Error location coordinates
- Interactive error highlighting on layout

### 6. Layout vs. Schematic (LVS)

**KLayout LVS Integration:**
- Menu integration: `Check → LVS with KLayout...` (Ctrl+Shift+L)
- Full extraction and comparison decks in `lvs/rule_decks/`: MOS, RF MOS, BJT, resistor, capacitor, diode, ESD, inductor, and tap extraction/derivation/connection decks, plus custom device extractors
- Flat or deep hierarchical run modes
- Series/parallel resistor combination and device merging controls
- Netlist-only extraction and schematic-vs-schematic (SVS) comparison flows
- Implicit-net support for bottom-up block-level verification
- Results surface in Revolution EDA's LVS mismatch tables, with the extracted `.cir` netlist and `.lvsdb` database available for inspection

### 7. RC Parasitic Extraction (PEX)

**RC extraction integration:**
- Menu integration: `Check → RC Extraction (PEX)...` (Ctrl+Shift+X)
- Runs on a successful LVS "Export for PEX" pass
- Uses the `pex/ihp_sg13g2.json` technology file derived from the IHP extract deck
- Per-layer sheet resistance, via resistance per cut, and area/fringe/sidewall capacitance across process corners (nominal, minimum, maximum)
- RC and C-only extraction modes for fast parasitic views

### 8. Layout Creation Tools

PDK-specific menu commands wired through `config.json`:

- `Create → Guard Ring → Substrate Tap (p+)...` / `N-Well Tap (n+)...` — parametric guard-ring placement
- `Create → Substrate Tap → P+ Tap Line` / `N-Well Tap Line` — minimum-width tap lines

### 9. Simulation Models

Model libraries ship preconfigured through `modelLibSettings.json` (using `${PDK_ROOT}`-relative paths) for **Xyce** and **VACASK**:

**Xyce (`models/xyce/`):**
- Statistical and corner `.lib` decks for LV/HV MOSFETs, HBTs, resistors, capacitors, diodes, ESD devices, and bond pads
- Compiled Verilog-A modules (`PSP103`, `mosvar`) for advanced RF/analog simulation

**VACASK (`models/vacask/`):**
- Matching corner/statistical model set (MOS LV/HV, HBT, RES, CAP, DIO)
- Precompiled OSDI modules for Linux and Windows
- Verilog-A sources for PSP103, R3_CMC, and MOSVAR

### 10. Process Technology Parameters

The `sg13_tech.py` and `process.py` modules define:

- **Distance unit (DBU):** 1 nm precision
- **Snap grid:** 50 nm
- **Major grid:** 100 nm
- **GDS unit:** 1 nm with 1 nm precision

**Via Definitions (9 types):**
- `cont`, `contBar` (barrier contact), `viamim`, `via1`–`via4`, `topVia1`–`topVia2`
- Each via defines min/max width, height, spacing, and bottom/top layer enclosures
- Example: `cont` via is 0.16 µm square with 0.28 µm minimum spacing

**Path Definitions (9 types):**
- `nwell`, `gatPoly`, `metal1`–`metal5`, `topMetal1`–`topMetal2`
- Per-layer width, spacing, and enclosure defaults for wiring

---

## How to Use with Revolution EDA

### Installation

1. **Clone the IHP PDK repository** into your Revolution EDA workspace:
   ```bash
   cd /path/to/revolution-eda
   git clone <ihp_pdk_repo> ihp_pdk
   ```

2. **Configure PDK path** in Revolution EDA:
   - Set `REVEDA_PDK_PATH` environment variable or
   - Set `REVEDA_PDK_PATH` in `.env` file (relative or absolute path)

3. **Restart Revolution EDA** for changes to take effect

### Creating Schematic Designs

1. **Launch Revolution EDA** schematic editor
2. **Select IHP SG13G2 PDK** from PDK selector
3. **Add devices** from the component library:
   - Right-click → `Add Instance`
   - Select device from the `sg13g2_pr` library
4. **Configure device parameters:**
   - Double-click instance → Edit properties
   - Parameters use Quantiphy format: `"4u"` = 4 micrometers, `"180n"` = 180 nanometers

### Creating Layout Designs

1. **Open Layout Editor** in Revolution EDA
2. **Insert parametric cells:**
   - Create instance → Select from the 42 registered pcells (`nmos`, `pmos`, `rsil`, `cmim`, `rfnmos`, `npn13G2`, `inductor2`, ...)
   - Specify parameters (width, length, number of gates, etc.)
3. **Layout is auto-generated** with all contacts, vias, and pins correctly placed
4. **Run DRC:** `Check → DRC with KLayout...` (Ctrl+Shift+D)
5. **Run LVS:** `Check → LVS with KLayout...` (Ctrl+Shift+L)
6. **Run PEX:** `Check → RC Extraction (PEX)...` (Ctrl+Shift+X) after an LVS pass
7. **Review violations** in error/mismatch tables; click to highlight on layout

### Running Simulations

1. **Generate netlist** from schematic
2. **Configure simulation:**
   - Select analysis type (DC, AC, transient, etc.)
   - Choose the Xyce or VACASK simulator backend
3. **Apply IHP models:**
   - `modelLibSettings.json` pre-selects the corner decks; adjust sections as needed
   - Verilog-A/OSDI modules load for RF-capable device models
4. **Run simulation** via RevedaSim or the command line

### Example Netlist

When you create a MOSFET instance with width=10µm, length=0.13µm, fingers=2:

```spice
* Auto-generated from Revolution EDA schematic
.include ihp_pdk/models/xyce/sg13g2_moslv_stat.lib

M1 d g s b sg13_lv_nmos W=10u L=0.13u NF=2

.control
ac dec 100 1 10g
run
.endc
```

---

## Project Structure

```
ihp_pdk/
├── README.md                          # This file
├── __init__.py                        # Package initialization
├── config.json                        # PDK metadata and menu items
├── callbacks.py                       # Instance parameter callbacks
├── process.py                         # Technology parameters, vias, paths
├── sg13_tech.py                       # Technology class with grid/precision
├── sg13g2_tech.json                   # JSON technology node definition
├── schLayers.py                       # Schematic layer definitions
├── symLayers.py                       # Symbol layer definitions
├── layoutLayers.py                    # Layout layer/GDS mappings
├── klayoutDRC.py                      # DRC integration with KLayout
├── klayoutLVS.py                      # LVS integration with KLayout
├── pexExtraction.py                   # RC parasitic extraction callback
├── guardRing.py                       # Guard-ring menu actions
├── tapLine.py                         # Tap-line menu actions
├── modelLibSettings.json              # Preconfigured simulator model decks
├── pcellParameterMap.json             # Schematic↔pcell parameter mapping
├── build_linux.sh                     # Binary build script (Linux)
├── build_windows.ps1                  # Binary build script (Windows)
│
├── pcells/                            # Parametric layout cells (42 registered)
│   ├── __init__.py                    # Exports all pcells
│   ├── base.py                        # Base classes (baseCell, baseMosfet, baseRfMosfet)
│   ├── mosfet.py / mosfet_hv.py       # Standard and HV MOSFETs
│   ├── rf_mosfet.py / rf_mosfet_hv.py # RF and RF-HV MOSFETs
│   ├── passive.py / passive_res_variants.py  # rsil, cmim, rhigh, rppd
│   ├── rfcmim.py / svaricap.py        # RF MIM cap, varicap
│   ├── inductors.py                   # Spiral inductors
│   ├── bjt.py                         # NPN/PNP HBTs
│   ├── diodes.py / schottky.py        # ESD and Schottky diodes
│   ├── esd.py                         # ESD clamp family
│   ├── tap_contacts.py / guardRing.py # Substrate taps, guard ring
│   ├── via_stack.py                   # Multi-layer via stack
│   ├── bondpad.py / sealring.py / isolbox.py  # Pad, seal ring, isolation
│   ├── nofiller_stack.py              # Filler exclusion marker
│   ├── PCELL_STATUS.md                # Per-cell implementation status
│   └── PORTING_STATUS.md              # KLayout→RevEDA porting coverage
│
├── sg13g2_pr/                         # Device symbol + pcell library (45 cells)
│
├── models/                            # Simulation models
│   ├── xyce/                          # Xyce .lib decks + compiled VA modules
│   └── vacask/                        # VACASK decks, OSDI binaries, VA sources
│
├── drc/                               # KLayout DRC rule decks + runner
│   ├── rule_decks/                    # maximal deck + category rule tables
│   ├── run_drc.py                     # CLI runner
│   └── README.md                      # Deck usage documentation
│
├── lvs/                               # KLayout LVS rule decks + runner
│   ├── rule_decks/                    # extraction/derivation/connection decks
│   ├── sg13g2.lvs                     # Main LVS runset
│   ├── run_lvs.py                     # CLI runner
│   └── README.md                      # Deck usage documentation
│
├── pex/                               # RC extraction technology file
│   └── ihp_sg13g2.json                # Resistance/capacitance per corner
│
├── docs/                              # LVS DB parser, VACASK, release notes
└── stipples/                          # Fill patterns for layout rendering
```

---

## Key Features & Capabilities

### Tech-Aware Parametric Layout

- Automatic calculation of contact arrays with correct spacing
- Grid-aligned geometry using technology DBU
- epsilon-corrected dimension calculations to prevent floating-point errors
- Support for small-width device special cases

### Multi-Finger & Multi-Unit Cells

- MOSFET cells support variable number of gate fingers (`ng` parameter)
- BJT cells support 1–10 emitter fingers (`Nx` parameter)
- Resistor supports bend count and poly spacing customization
- Capacitors support multiplier factors for parallel plate arrays

### RF Device Support

- Dedicated RF MOSFET families (`rfnmos`, `rfpmos`, plus HV variants)
- Integrated guard rings and shielding
- Configurable contact row arrangements for matching
- RF MIM capacitor and spiral inductor cells

### Full Verification Flow

- KLayout DRC with per-table and density/antenna subsets
- KLayout LVS with device extractors for every PDK device family
- RC/C-only parasitic extraction using foundry corner data
- Guard-ring and tap-line helpers to keep layouts LVS-clean

### Device Model Accuracy

- Statistical corner models (process variation)
- Temperature-dependent models (worst-case corners)
- Verilog-A/OSDI PSP103, R3_CMC, and MOSVAR models for advanced analog/RF simulation
- Xyce and VACASK backends with preconfigured library settings

---

## Usage Examples

### Example 1: Create a Simple NMOS Transistor

**In Schematic Editor:**
1. Add Instance → `sg13_lv_nmos` (LV NMOS)
2. Set parameters: `W=10u`, `L=0.13u`
3. Connect D, G, S, B pins to your circuit

**In Layout Editor:**
1. Insert parametric cell → `nmos`
2. Set parameters: `width=10u`, `length=0.13u`, `ng=2`
3. Layout is automatically generated with correct contacts and vias

### Example 2: Design an MIM Capacitor

1. **Schematic:** Add `cap_cmim` device, specify `W=100u`, `L=100u`, `MF=4`
2. **Callback calculates:** 
   - C = 4 × (100×100×1.5e-3 + 2×(100+100)×40e-12) = 6.016 pF
3. **Layout:** Insert `cmim` pcell with matching parameters
4. **Simulation:** Models auto-linked via `capacitors_stat.lib`

### Example 3: Run DRC and LVS

1. Complete layout design
2. Press **Ctrl+Shift+D** or `Check → DRC with KLayout...`
3. KLayout runs the SG13G2 rule decks headless
4. Violations appear in error table with layer pair and coordinates
5. Click error to highlight on layout canvas
6. Press **Ctrl+Shift+L** for LVS; mismatches appear in the LVS tables

---

## Development & Extension

### Adding a New Parametric Cell

1. Define cell class in `pcells/` inheriting from `baseCell` or `baseMosfet`
2. Implement `__init__()` with parameter defaults
3. Implement `__call__()` to generate layout shapes
4. Register in `pcells/__init__.py` - add to `pcells` dict
5. Verify layer/tech parameter references in `base.py`

### Adding Instance Parameters

1. Create callback class in `callbacks.py` inheriting from `baseInst`
2. Parse label values in `__init__()` using `Quantity()`
3. Implement parameter computation methods (e.g., `C_parm()`)
4. Reference in schematic instance properties

### Custom DRC Rules

1. Extend the rule tables under `drc/rule_decks/` with new rules
2. Use KLayout DRC rule syntax
3. Test with `klayoutDRC.py` or `drc/run_drc.py`

---

## Migration from Other PDKs

If migrating from OpenPDK or other formats:

- **Device names:** Cross-reference with IHP's naming convention in callbacks
- **Layer definitions:** Verify GDS layer/datatype pairs in `layoutLayers.py`
- **Simulation models:** Update `.include` paths in netlists to point to `models/xyce/` or `models/vacask/`
- **Layout rules:** Start with a subset of rule tables, then enable the full `sg13g2_maximal.drc` set for compliance

---

## Performance Considerations

- **PCell generation:** Typically <100ms for standard devices
- **DRC checking:** 30s–2min depending on layout size and selected rule tables
- **LVS checking:** Deep mode is slower but scales to larger hierarchies; use flat mode for blocks
- **Simulation:** Model convergence depends on device count and analysis type

---

## Dependencies

Revolution EDA integration requires:

- **Python 3.12+** with PySide6 ≥6.10.0
- **quantiphy** - Unit/quantity parsing
- **gdstk** ≥0.9.60 - GDS II file I/O
- **KLayout** (required for DRC/LVS) - `klayout` command-line tool
- **Xyce or VACASK** (for simulation)

---

## Support & Issues

For questions or bug reports:

- Check [Revolution EDA Documentation](https://github.com/revedaEditor)
- Consult [IHP SG13G2 Technology Documentation](https://www.ihp-microelectronics.com)
- File issues on the IHP PDK GitHub repository

---

## License

- **Apache License 2.0** - Core PDK code and layout definitions
- **Commons Clause** - Commercial use restrictions for Revolution Semiconductor components
- **IHP License** - Reference to IHP's original process design information

See LICENSE files in the repository root for details.

---

## Acknowledgments

IHP PDK for Revolution EDA is maintained in collaboration with:
- **IHP Microelectronics** - Original SG13G2 Process Technology
- **Revolution Semiconductor** - Revolution EDA Platform
- Open-source contributors to SPICE models and design rule decks

---

**Last Updated:** October 2026  
**Version:** 0.3.0
