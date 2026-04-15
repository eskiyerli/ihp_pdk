# LVSDBParser Module Documentation

Parser for KLayout .lvsdb files into Python structures for Revolution EDA.

## Class: `LVSDBParser`

Parses KLayout .lvsdb files into Python structures for Revolution EDA.
Handles the S-expression format and extracts Layers, Nets, Devices,
Schematic views, and Cross-reference mappings.

When pdk_module is provided, resolves GDS layers to PDK layer names
using the PDK's layer definitions (e.g., layoutLayers.py).

---

## Methods

### `__init__(self, filepath: str, pdk_module=None)`

Initialize the LVSDB parser.

**Args:**
- `filepath`: Path to the .lvsdb file to parse.
- `pdk_module`: Optional PDK module with layer definitions (e.g., layoutLayers).
  When provided, enables resolution of GDS layer numbers to PDK layer names.

**Attributes:**
- `layer_map`: Mapping from LVSDB internal layer IDs to GDS strings (layer/datatype).
- `gds_to_pdk`: Mapping from (gdsLayer, datatype) tuples to PDK layer names.
- `data`: Raw parsed S-expression data from the file.
- `layout_cells`: Cache of parsed layout cell data.
- `schematic_cells`: Cache of parsed schematic cell data.
- `crossrefs`: Cross-reference mappings between layout and schematic cells.

---

### `tokenize(self, text: str) -> Iterator[str]`

Tokenize the Lisp-like S-expression format.

Splits the input text into tokens including parentheses, quoted strings,
and unquoted atoms. Handles both single and double quotes.

**Args:**
- `text`: The S-expression text to tokenize.

**Yields:**
- Individual tokens as strings (e.g., '(', ')', 'cell_name', '"quoted string"').

---

### `parse_expression(self, tokens)`

Recursively build a tree from tokens.

Parses a parenthesized S-expression into a nested list structure.
Handles nested expressions by recursively parsing content within parentheses.

**Args:**
- `tokens`: Iterator of tokens from tokenize().

**Returns:**
- Nested list representing the parsed S-expression tree.

---

### `load(self)`

Load and parse the LVSDB file.

Reads the file, strips the header, tokenizes the S-expression content,
and builds the parse tree. After loading, processes layer mappings
and cross-reference sections.

**Returns:**
- The parsed data structure (list of S-expressions).

**Raises:**
- `FileNotFoundError`: If the filepath does not exist.
- `IOError`: If the file cannot be read.

---

### `_process_crossrefs(self)`

Extract cross-reference mappings from the Z section.

The Z section contains equivalence information between layout and schematic
cells, including net, pin, and device mappings. Populates self.crossrefs
with mappings for each cell.

Cross-reference format: X(cell_name schematic_name equiv mapping...)
where mapping contains net, pin, and device correspondences.

---

### `_parse_crossref_mapping(self, mapping_items: List) -> Dict`

Parse the Z section mapping block with tag-pair format.

Extracts net, pin, and device mappings from the cross-reference section.
The mapping uses a tag-pair format where tags (N, P, D) are followed by
content lists describing the correspondence.

**Args:**
- `mapping_items`: List of tag-content pairs from the Z section.

**Returns:**
- Dictionary with keys 'nets', 'pins', 'devices', each containing
  a list of mapping dictionaries with layout/schematic correspondences
  and status information.

---

### `get_all_layout_cells(self) -> List[str]`

Return list of all layout cell names.

Scans the J (layout) section of the parsed data to extract all
cell names defined in the layout view.

**Returns:**
- List of layout cell name strings.

---

### `get_all_schematic_cells(self) -> List[str]`

Return list of all schematic cell names.

Scans the H (schematic/circuit) section of the parsed data to extract
all cell names defined in the schematic view.

**Returns:**
- List of schematic cell name strings.

---

### `_safe_get(self, lst: List, idx: int, default: Any = None) -> Any`

Safely get an item from a list with bounds checking.

Helper method to safely access list elements without raising IndexError.
Also handles cases where the input is not a list.

**Args:**
- `lst`: The list to access.
- `idx`: The index to retrieve.
- `default`: Value to return if index is out of bounds or lst is not a list.

**Returns:**
- The item at index idx, or default if out of bounds.

---

### `_build_gds_lookup(self)`

Build reverse lookup from (gdsLayer, datatype) to PDK layer name.

Scans the PDK module for layLayer objects (objects with gdsLayer and
datatype attributes) and builds a lookup dictionary. This enables
resolution of GDS layer numbers to human-readable PDK layer names.

Populates self.gds_to_pdk with (gdsLayer, datatype) -> pdk_name mappings.

---

### `_get_layer_name(self, lvsdb_layer_id: str) -> Optional[str]`

Get PDK layer name from LVSDB internal layer ID.

**Resolution order:**
1. Look up lvsdb_id in layer_map -> get GDS string 'layer/datatype'
2. Parse GDS string to (layer, datatype)
3. Look up (layer, datatype) in PDK gds_to_pdk -> get PDK name
4. If no PDK mapping, return GDS string; if no GDS mapping, return lvsdb_id

---

### `_process_layers(self)`

Extract L(id 'GDS') mappings from the J section into a usable dict.

The J section contains layer definitions with L tags that map internal
LVSDB layer IDs to GDS strings in the format 'layer/datatype'.

Populates self.layer_map with lvsdb_id -> gds_string mappings.

---

### `get_nets(self, cell_name: str) -> List[Dict]`

Return all geometry associated with nets in a specific layout cell.

Retrieves the parsed net data for a layout cell, including net names
and associated geometric shapes (rectangles, polygons, labels).

**Args:**
- `cell_name`: Name of the layout cell to query.

**Returns:**
- List of net dictionaries, each containing 'net_id', 'name',
  and 'shapes' (list of geometry dictionaries).

---

### `get_devices(self, cell_name: str) -> List[Dict]`

Return all devices in a specific layout cell.

Retrieves the device data extracted from the LVSDB for a layout cell,
including device IDs, types, positions, parameters, and terminal mappings.

**Args:**
- `cell_name`: Name of the layout cell to query.

**Returns:**
- List of device dictionaries with keys: 'id', 'type', 'position',
  'params', 'terminals', 'subdevices'.

---

### `get_schematic_devices(self, cell_name: str) -> List[Dict]`

Return all devices from the schematic view of a cell.

Retrieves device data from the schematic/circuit representation,
including device names, types, parameters, and terminal net connections.

**Args:**
- `cell_name`: Name of the schematic cell to query.

**Returns:**
- List of schematic device dictionaries with keys: 'id', 'type',
  'name', 'params', 'terminals'.

---

### `get_schematic_nets(self, cell_name: str) -> List[Dict]`

Return all nets from the schematic view of a cell.

Retrieves net data from the schematic/circuit representation,
including net IDs and names.

**Args:**
- `cell_name`: Name of the schematic cell to query.

**Returns:**
- List of schematic net dictionaries with keys: 'net_id', 'name'.

---

### `get_extracted_schematic(self, layout_cell_name: str) -> Optional[Dict]`

Returns extracted schematic with resolved net names for creating a schematic view.

**Returns dict with:**
- `'name'`: schematic cell name
- `'nets'`: list of {id, name, layout_net_id}  # schematic nets with names resolved
- `'devices'`: list of {id, name, type, params, terminals}  # devices with terminal net names
- `'equivalent'`: True/False/None  # LVS equivalence status

---

### `get_crossref(self, cell_name: str) -> Optional[Dict]`

Return cross-reference mapping between layout and schematic.

Retrieves the pre-parsed cross-reference data for a cell, which includes
the schematic cell name, equivalence status, and net/pin/device mappings.

**Args:**
- `cell_name`: Name of the layout cell to query.

**Returns:**
- Dictionary with keys 'schematic_name', 'equivalent', 'mapping',
  or None if no cross-reference exists for this cell.

---

### `get_connectivity(self, layout_cell_name: str) -> Optional[Dict]`

Return bidirectional connectivity information.

Builds both device-centric and net-centric views of connectivity:
- Device-centric: which nets connect to each device terminal
- Net-centric: which device terminals connect to each net

**Args:**
- `layout_cell_name`: Name of the layout cell to extract connectivity from.

**Returns:**
- Dictionary with keys:
  - 'devices': Dict mapping device names to {terminal: net_name} dicts
  - 'nets': Dict mapping net names to [(dev_name, terminal), ...] lists
  - 'netlist': List of (dev_name, type, {terminal: net_name, ...}) tuples
  
  Returns None if the cell cannot be found or has no extracted schematic.

---

### `_get_layout_cell(self, cell_name: str) -> Optional[Dict]`

Get parsed layout cell data, processing if not cached.

Looks up the cell in the layout cell cache first. If not found,
searches the J section of the parsed data, parses the cell definition,
and caches the result.

**Args:**
- `cell_name`: Name of the layout cell to retrieve.

**Returns:**
- Dictionary with parsed cell data ('name', 'bbox', 'nets', 'pins', 'devices'),
  or None if the cell is not found.

---

### `_get_schematic_cell(self, cell_name: str) -> Optional[Dict]`

Get parsed schematic cell data, processing if not cached.

Looks up the cell in the schematic cell cache first. If not found,
searches the H section of the parsed data, parses the cell definition,
and caches the result.

**Args:**
- `cell_name`: Name of the schematic cell to retrieve.

**Returns:**
- Dictionary with parsed cell data ('name', 'nets', 'pins', 'devices'),
  or None if the cell is not found.

---

### `_parse_layout_cell(self, cell_list: List) -> Dict`

Parse an X(cell_name ...) layout cell definition from the J section.

Layout cells contain a bounding box, nets with geometry, pins, and devices.
The content is in tag-pair format: R (bbox), N (net), P (pin), D (device).

**Args:**
- `cell_list`: List containing the cell definition starting with cell name.

**Returns:**
- Dictionary with keys: 'name', 'bbox', 'nets', 'pins', 'devices'.

---

### `_parse_schematic_cell(self, cell_list: List) -> Dict`

Parse an X(cell_name ...) schematic cell definition from the H section.

Schematic cells contain nets, pins, and devices in tag-pair format:
N (net), P (pin), D (device). Unlike layout cells, schematic cells
do not have geometric bounding boxes.

**Args:**
- `cell_list`: List containing the cell definition starting with cell name.

**Returns:**
- Dictionary with keys: 'name', 'nets', 'pins', 'devices'.

---

### `_parse_bbox(self, min_pt: List, max_pt: List) -> Optional[List[List[float]]]`

Parse bounding box from two coordinate lists.

Converts string or numeric coordinates to float and formats as
a 2x2 bounding box matrix.

**Args:**
- `min_pt`: List of [x, y] coordinates for the minimum corner.
- `max_pt`: List of [x, y] coordinates for the maximum corner.

**Returns:**
- Bounding box as [[xmin, ymin], [xmax, ymax]], or None if parsing fails.

---

### `_parse_pin(self, pin_list: List) -> Optional[Dict]`

Parse a P(pin_id I(name)) pin definition.

Pins are defined in tag-pair format with an ID and optional name.

**Args:**
- `pin_list`: List containing pin data: [tag, pin_id, [I, (name)]].

**Returns:**
- Dictionary with 'pin_id' and 'name', or None if parsing fails.

---

### `_parse_schematic_net(self, net_list: List) -> Optional[Dict]`

Parse a schematic net with tag-pair format: N id I(name).

Schematic nets contain a net ID and optionally a name in I tag format.

**Args:**
- `net_list`: List containing net data: [N, net_id, I, (name), ...].

**Returns:**
- Dictionary with 'net_id' and 'name', or None if parsing fails.

---

### `_parse_schematic_device(self, dev_list: List) -> Optional[Dict]`

Parse a schematic device with tag-pair format.

**Device format:** D id type I(name) E(name val) T(term net) ...
- I tag: Instance name
- E tag: Parameters (name-value pairs)
- T tag: Terminal connections (terminal name -> net ID)

**Args:**
- `dev_list`: List containing device data starting with tag, id, type.

**Returns:**
- Dictionary with keys: 'id', 'type', 'name', 'params', 'terminals',
  or None if parsing fails.

---

### `_parse_net(self, net_list: List) -> Optional[Dict]`

Parse a layout net with tag-pair format.

**Net format:** [N, id, I(name), R(layer origin size), Q(layer points...), J(layer text pos)...]
- I tag: Net name
- R tag: Rectangle geometry (layer, origin [x,y], size [w,h])
- Q tag: Polygon geometry (layer, list of [x,y] points)
- J tag: Text label (layer, text string, position [x,y])

**Args:**
- `net_list`: List containing net data starting with tag and net_id.

**Returns:**
- Dictionary with 'net_id', 'name', and 'shapes' (list of geometry dicts),
  or None if parsing fails.

---

### `_parse_device(self, dev_list: List) -> Optional[Dict]`

Parse a layout device with tag-pair format.

**Device format:** D id type Y(x y) E(name val) T(term net) D(subdevice) C(conn)...
- id: Device identifier
- type: Device type (e.g., 'MOS', 'RES', 'CAP')
- Y tag: Position coordinates [x, y]
- E tag: Parameters (name-value pairs, value converted to float if possible)
- T tag: Terminal connections (terminal name -> net ID)
- D tag: Sub-devices (for hierarchical devices)
- C tag: Connections between terminals

**Args:**
- `dev_list`: List containing device data starting with tag, id, type.

**Returns:**
- Dictionary with keys: 'id', 'type', 'position', 'params', 'terminals', 'subdevices',
  or None if parsing fails.

---

### `_parse_subdevice(self, subdev_list: List) -> Optional[Dict]`

Parse a sub-device reference.

**Sub-device format:** D(name Y(x y))
Represents a child device within a hierarchical device structure.

**Args:**
- `subdev_list`: List containing sub-device data: [D, name, Y, (x, y)].

**Returns:**
- Dictionary with 'name' and 'transform' (position [x, y]),
  or None if parsing fails.

---

## Usage Example

```python
from ihp_pdk.lvs.lvsdb_parser import LVSDBParser
import ihp_pdk.layoutLayers as ly

# Parse with PDK for layer name resolution
parser = LVSDBParser('opamp.lvsdb', ly)
parser.load()

# Get all layout cells
print(parser.get_all_layout_cells())

# Get nets and devices for a specific cell
nets = parser.get_nets('opamp')
devices = parser.get_devices('opamp')

# Get cross-reference information
xref = parser.get_crossref('opamp')
print(f"Equivalent: {xref['equivalent']}")

# Get extracted schematic with resolved net names
extracted = parser.get_extracted_schematic('opamp')

# Get bidirectional connectivity
conn = parser.get_connectivity('opamp')
print(conn['devices'])   # device -> terminals -> nets
print(conn['nets'])      # net -> (device, terminal) list
```
