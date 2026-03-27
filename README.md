# IHP SG13G2 Process Design Kit (PDK) for Revolution EDA

A comprehensive Python-based Process Design Kit (PDK) for the **IHP SG13G2 130nm BiCMOS technology** integrated with the **Revolution EDA** open-source IC design environment.

## Overview

This PDK provides complete design automation support for IHP's SG13G2 process node, including:

- **Parametric layout cells (pcells)** for automated device and passive component generation
- **Instance parameter callbacks** for electrical parameter computation
- **Schematic and symbol layer definitions** for front-end design
- **Layout layer definitions** with GDS layer/datatype mappings
- **Design Rule Checking (DRC)** integration via KLayout
- **SPICE simulation models** and Verilog-A modules for transient and AC analysis

**Technology Details:**
- **Process Node:** SG13G2 (IHP 130nm BiCMOS)
- **PDK Version:** 0.2.0
- **License:** Apache 2.0 

---

## What's Implemented

### 1. Parametric Cells (PCell Library)

The PDK includes 6 parametric layout cells enabling automated, scalable device generation:

#### Active Devices

| Cell | Description | Parameters |
|------|-------------|------------|
| **nmos** | NMOS transistor with configurable fingers | `width`, `length`, `ng` (number of gates) |
| **pmos** | PMOS transistor with configurable fingers | `width`, `length`, `ng` (number of gates) |
| **rfnmos** | RF-optimized NMOS with guard rings | `width`, `length`, `ng`, `cnt_rows`, `Met2Cont`, `gat_ring`, `guard_ring` |
| **rfpmos** | RF-optimized PMOS with guard rings | `width`, `length`, `ng`, `cnt_rows`, `Met2Cont`, `gat_ring`, `guard_ring` |

#### Passive Components

| Cell | Description | Parameters |
|------|-------------|------------|
| **rsil** | Polysilicon resistor (meander pattern) | `length`, `width`, `b` (bends), `ps` (poly spacing) |
| **cmim** | Metal-insulator-metal capacitor | `w`, `l`, `mf` (multiplier factor) |

**Key Features:**
- All pcells support parameterized layout generation at instantiation time
- Automatic contact array placement with correct spacing and alignment
- Technology-aware grid snapping and design rule compliance
- Support for multi-finger and multi-unit configurations
- RF variants include guard rings and shielding for low-noise applications

### 2. Instance Callbacks

The `callbacks.py` module provides automatic electrical parameter computation for 50+ device variants:

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

### 3. Layer Definitions

#### Schematic/Symbol Layers (schLayers.py)

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

Complete layout layer set for GDS II file I/O:

**Metallization Layers:**
- Metal1–Metal4 (drawing + pin layers)
- Via1–Via4 (contact/via layers)
- Contact layers (Cont_drawing)

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

### 4. Design Rule Checking (DRC)

**KLayout DRC Integration:**
- Headless KLayout DRC execution with IHP rule decks
- DRC result parsing and error visualization in Revolution EDA
- Menu integration: `Check → DRC with KLayout` (Ctrl+Shift+D)

**Included Rule Files:**
- `sg13g2_maximal.lydrc` - Full rule checking (all design rules)
- `sg13g2_minimal.lydrc` - Essential rules only (faster runs)

DRC violations are parsed and displayed as a table with:
- Error classification (layer/rule pair)
- Error location coordinates
- Interactive error highlighting on layout

### 5. SPICE Simulation Models

Complete model library for analog circuit design:

**Compact Models (`.lib` files):**
- `sg13g2_moslv_stat.lib` - Low-voltage MOSFET models (statistical)
- `sg13g2_moshv_stat.lib` - High-voltage MOSFET models (statistical)
- `sg13g2_hbt_stat.lib` - HBT transistor models
- Device-specific models: capacitors, diodes, resistors, ESD structures

**Parametric Models:**
- Temperature variation (`*_mod.lib`)
- Process corners (`corner*.lib`)

**Verilog-A Modules:**
- PSP103 MOSFET model (libXyce_Plugin_PSP103_VA.so)
- Enables advanced RF/analog simulation with Xyce

### 6. Process Technology Parameters

The `sg13_tech.py` and `process.py` modules define:

- **Distance unit (DBU):** 1 nm precision
- **Snap grid:** 50 nm
- **Major grid:** 100 nm
- **GDS unit:** 1 nm with 1 nm precision

**Via Definitions:**
- Via types: Contact (cont), Via1–Via4, MIM via, barrier contact (contBar)
- Each via has min/max width, height, and spacing constraints
- Example: `cont` via is 0.16 µm square with 0.18 µm minimum spacing

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
   - Select device from `ihp_pdk` library
4. **Configure device parameters:**
   - Double-click instance → Edit properties
   - Parameters use Quantiphy format: `"4u"` = 4 micrometers, `"180n"` = 180 nanometers

### Creating Layout Designs

1. **Open Layout Editor** in Revolution EDA
2. **Insert parametric cells:**
   - Create instance → Select from pcells: `nmos`, `pmos`, `rsil`, `cmim`, `rfnmos`, `rfpmos`
   - Specify parameters (width, length, number of gates, etc.)
3. **Layout is auto-generated** with all contacts, vias, and pins correctly placed
4. **Run DRC:** `Check → DRC with KLayout` (Ctrl+Shift+D)
5. **Review violations** in error table; click to highlight on layout

### Running Simulations

1. **Generate netlist** from schematic
2. **Configure simulation:**
   - Select analysis type (DC, AC, transient, etc.)
   - Choose Xyce simulator backend
3. **Apply IHP models:**
   - Simulation engine auto-links `sg13g2_moslv_stat.lib` and other `.lib` files
   - Verilog-A modules loaded for RF simulation
4. **Run simulation** via `aiTerminal` or command-line interface

### Example Netlist

When you create a MOSFET instance with width=10µm, length=0.13µm, fingers=2:

```spice
* Auto-generated from Revolution EDA schematic
.include ihp_pdk/models/sg13g2_moslv_stat.lib

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
├── callbacks.py                       # Instance parameter callbacks (358 lines)
├── process.py                         # Technology parameters & vias
├── sg13_tech.py                       # Technology class with grid/precision
├── sg13g2_tech.json                   # JSON technology node definition
├── schLayers.py                       # Schematic layer definitions (167 lines)
├── symLayers.py                       # Symbol layer definitions
├── layoutLayers.py                    # Layout layer/GDS mappings
├── klayoutDRC.py                      # DRC integration with KLayout
│
├── pcells/                            # Parametric layout cells
│   ├── __init__.py                    # Exports all pcells
│   ├── base.py                        # Base classes (baseCell, baseMosfet, baseRfMosfet)
│   ├── mosfet.py                      # nmos, pmos classes
│   ├── passive.py                     # rsil, cmim resistor/capacitor cells
│   └── rf_mosfet.py                   # rfnmos, rfpmos RF transistors
│
├── models/                            # SPICE simulation models
│   ├── sg13g2_moslv_stat.lib          # Low-voltage MOSFET models
│   ├── sg13g2_moshv_stat.lib          # High-voltage MOSFET models
│   ├── sg13g2_hbt_stat.lib            # HBT transistor models
│   ├── capacitors_stat.lib
│   ├── resistors_stat.lib
│   ├── diodes.lib
│   └── ... (25+ model files)
│
├── va_modules/                        # Verilog-A behavioral models
│   └── libXyce_Plugin_PSP103_VA.so    # PSP103 MOSFET model plugin
│
├── drc/                               # Design Rule Check decks
│   ├── sg13g2_maximal.lydrc           # Full DRC rules
│   ├── sg13g2_minimal.lydrc           # Essential DRC rules
│   └── ... (DRC documentation)
│
├── sg13g2_pr/                         # IHP-supplied PDK reference
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
- Resistor supports bend count and poly spacing customization
- Capacitors support multiplier factors for parallel plate arrays

### RF Device Support

- Dedicated RF MOSFET families (`rfnmos`, `rfpmos`)
- Integrated guard rings and shielding
- Configurable contact row arrangements for matching

### Device Model Accuracy

- Statistical corner models (process variation)
- Temperature-dependent models (worst-case corners)
- Verilog-A PSP103 for advanced analog/RF simulation

### Design Rule Integration

- Built-in KLayout DRC execution
- Fast rule checking with maximal/minimal deck options
- Error visualization and clickable error navigation

---

## Usage Examples

### Example 1: Create a Simple NMOS Transistor

**In Schematic Editor:**
1. Add Instance → `nmos_3p3` (3.3V NMOS)
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

### Example 3: Run DRC Check

1. Complete layout design
2. Press **Ctrl+Shift+D** or `Check → DRC with KLayout`
3. KLayout runs `sg13g2_maximal.lydrc` headless
4. Violations appear in error table with layer pair and coordinates
5. Click error to highlight on layout canvas

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

1. Extend `sg13g2_maximal.lydrc` with new rules
2. Use KLayout DRC rule syntax
3. Test with `klayoutDRC.py` module

---

## Migration from Other PDKs

If migrating from OpenPDK or other formats:

- **Device names:** Cross-reference with IHP's naming convention in callbacks
- **Layer definitions:** Verify GDS layer/datatype pairs in `layoutLayers.py`
- **Simulation models:** Update `.include` paths in netlists to point to `models/`
- **Layout rules:** Use `sg13g2_minimal.lydrc` for basic compatibility, then `maximal` for full compliance

---

## Performance Considerations

- **PCell generation:** Typically <100ms for standard devices
- **DRC checking:** 30s–2min depending on layout size and rule deck (use minimal deck for large designs)
- **Simulation:** Xyce model convergence depends on device count and analysis type

---

## Dependencies

Revolution EDA integration requires:

- **Python 3.12+** with PySide6 ≥6.10.0
- **quantiphy** - Unit/quantity parsing
- **gdstk** ≥0.9.60 - GDS II file I/O
- **KLayout** (optional but required for DRC) - `klayout` command-line tool
- **Xyce** (recommended for simulation backend)

All dependencies are auto-fulfilled by the Revolution EDA environment.

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

**Last Updated:** February 2026  
**Version:** 0.2.0
