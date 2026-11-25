# SPDX-License-Identifier: Apache-2.0
#
# IHP PDK for Revolution EDA
# Copyright (c) 2024-2026 Revolution Semiconductor

"""layoutPilot technology snapshot for the IHP SG13G2 PDK.

Pure JSON-serializable description of everything the layoutPilot
plugin needs from this PDK: process constants, supported devices
with their parameter/pin maps, the merged DRC rule values, the
semantic role->IHP rule-key map, verification deck locations and
honest capability flags.  All PDK/revedaEditor imports happen inside
``get_layout_pilot_technology`` so importing this module is cheap
and side-effect free.
"""

import hashlib
import json
from pathlib import Path

_FORMAT = "layoutPilotTech-v1"
_VERSION = 2

_PKG = Path(__file__).resolve().parent

# Semantic role -> IHP rule key for every rule layoutPilot reads.
_ROLES = {
    "metal1_width": "M1_a",
    "metal1_space": "M1_b",
    "metal1_enclosure_via": "M1_e",
    "metal1_enclosure_via_wide": "M1_e_w",
    "metal1_enclosure_via_corner": "M1_e_cr",
    "metaln_width": "Mn_a",
    "metaln_space": "Mn_b",
    "metaln_enclosure_via": "Mn_e",
    "metaln_enclosure_via_corner": "Mn_e_cr",
    "via_size": "Vn_a",
    "via_space": "Vn_b",
    "via_enclosure": "Vn_c1",
    "nwell_device_enclosure": "NW_c",
    "nwell_to_psd_space": "NW_d",
    "nwell_ring_enclosure": "NW_e",
    "psd_ring_overhang": "pSD_c1",
    "active_space": "Act_b",
    "contact_size": "Cnt_a",
    "contact_space": "Cnt_b",
    "contact_enclosure": "Cnt_c",
}

_MOS_TERMINALS = ["D", "G", "S", "B"]

#: Physical conductor/cut stack bottom-to-top with cut connectivity
#: (layoutPilotTech v2).  ``rule_role`` is the rule-deck prefix the
#: plugin uses for cut size/spacing/enclosure lookups — the values
#: mirror what the plugin historically hardcoded as CUT_MAP.
_STACK_CONDUCTORS = ["Activ", "GatPoly", "Metal1", "Metal2", "Metal3",
                     "Metal4", "Metal5", "TopMetal1", "TopMetal2"]
_STACK_CUTS = {
    "Cont": {"rule_role": "cont", "below": "GatPoly", "above": "Metal1"},
    "Via1": {"rule_role": "via1", "below": "Metal1", "above": "Metal2"},
    "Via2": {"rule_role": "via2", "below": "Metal2", "above": "Metal3"},
    "Via3": {"rule_role": "via3", "below": "Metal3", "above": "Metal4"},
    "Via4": {"rule_role": "via4", "below": "Metal4", "above": "Metal5"},
    "TopVia1": {"rule_role": "topVia1", "below": "Metal5",
                "above": "TopMetal1"},
    "TopVia2": {"rule_role": "topVia2", "below": "TopMetal1",
                "above": "TopMetal2"},
}

#: Semantic layer roles (layoutPilotTech v2) — stage code must ask
#: for these, never write the literal names.
_LAYER_ROLES = {
    "gate": "GatPoly",
    "active": "Activ",
    "contact": "Cont",
    "well_n": "NWell",
    "implant_n": "nSD",
    "implant_p": "pSD",
}

#: Per-device tile class and pin truth (layoutPilotTech v2).
#: tile_class: row_shareable — interdigitated shared-diffusion row
#: device; passive_unit — fixed master placed in/near rows.
_DEVICE_EXTRAS = {
    "sg13_lv_nmos": {"tile_class": "row_shareable",
                     "pin_layers": {"D": "Metal1", "G": "Metal1",
                                    "S": "Metal1", "B": "Metal1"}},
    "sg13_lv_pmos": {"tile_class": "row_shareable",
                     "pin_layers": {"D": "Metal1", "G": "Metal1",
                                    "S": "Metal1", "B": "Metal1"}},
    "cap_cmim": {"tile_class": "passive_unit",
                 "pin_layers": {"PLUS": "TopMetal1",
                                "MINUS": "Metal5"}},
    "rsil": {"tile_class": "passive_unit",
             "pin_layers": {"PLUS": "Metal1", "MINUS": "Metal1"}},
    "rhigh": {"tile_class": "passive_unit",
              "pin_layers": {"PLUS": "Metal1", "MINUS": "Metal1"}},
    "rppd": {"tile_class": "passive_unit",
             "pin_layers": {"PLUS": "Metal1", "MINUS": "Metal1"}},
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require(path: Path) -> Path:
    if not path.is_file():
        raise FileNotFoundError(
            f"layoutPilotTech: required PDK file missing: {path}")
    return path


def _read_json(path: Path) -> dict:
    return json.loads(_require(path).read_text(encoding="utf-8"))


def _device(cell: str, kind: str, domain, terminals, param_map,
            pins=None) -> dict:
    dev = {"kind": kind, "domain": domain,
           "library": "sg13g2_pr", "terminals": terminals,
           "param_map": dict(param_map or {})}
    if pins:
        dev["pins"] = dict(pins)
    return dev


def _mfg_grid_um() -> float:
    layout_json = _PKG / "designPilotLayout.json"
    if layout_json.is_file():
        try:
            return float(json.loads(
                layout_json.read_text(
                    encoding="utf-8"))["grid"]["manufacturing_um"])
        except (KeyError, ValueError, json.JSONDecodeError):
            pass
    return 0.005


def get_layout_pilot_technology() -> dict:
    """Return the ``layoutPilotTech-v1`` snapshot for this PDK.

    Raises FileNotFoundError/KeyError on a missing required PDK
    file — the snapshot is never returned partial."""
    from revedaEditor.backend.pdkLoader import importPDKModule
    process = importPDKModule("process")

    pmap = _read_json(_PKG / "pcellParameterMap.json")
    mappings = pmap.get("mappings", {})
    pins = pmap.get("pinMappings", {})

    devices = {
        "sg13_lv_nmos": _device(
            "sg13_lv_nmos", "nmos", "n", _MOS_TERMINALS,
            mappings.get("sg13_lv_nmos")),
        "sg13_lv_pmos": _device(
            "sg13_lv_pmos", "pmos", "p", _MOS_TERMINALS,
            mappings.get("sg13_lv_pmos")),
    }
    for cell in ("cap_cmim",):
        devices[cell] = _device(
            cell, "cap", None, list(
                (pins.get(cell) or {"PLUS": None,
                                    "MINUS": None}).keys()),
            mappings.get(cell), pins.get(cell))
    for cell in ("rsil", "rhigh", "rppd"):
        devices[cell] = _device(
            cell, "res", None, list(
                (pins.get(cell) or {"PLUS": None,
                                    "MINUS": None}).keys()),
            mappings.get(cell), pins.get(cell))

    for cell, extra in _DEVICE_EXTRAS.items():
        if cell in devices:
            devices[cell].update(extra)

    rules = dict(
        _read_json(_PKG / "sg13g2_tech.json")["Parameters"])
    for k, v in _read_json(
            _PKG / "drc" / "rule_decks"
            / "sg13g2_tech_default.json")["drc_rules"].items():
        rules.setdefault(k, v)

    try:
        kdrc = importPDKModule("klayoutDRC")
        rule_sets = dict(
            getattr(kdrc, "DRC_RULE_SETS", {}) or {})
        default_json = getattr(
            kdrc, "DRC_DEFAULT_JSON",
            "rule_decks/sg13g2_tech_default.json")
        rule_sets_ok = True
    except Exception:  # noqa: BLE001
        rule_sets, default_json = {}, ""
        rule_sets_ok = False

    verification = {
        "drc": {"module": "klayoutDRC", "dir": "drc",
                "rule_sets": rule_sets,
                "default_json": default_json,
                "main_rule_set": "main",
                "rule_sets_importable": rule_sets_ok},
        "lvs": {"dir": "lvs", "deck": "sg13g2.lvs"},
    }

    capabilities = {
        "recipes": ["mirror_array", "ratioed_mirror",
                    "generic_groups"],
        "supply_rails": True,
        # true VDD/VSS straps (supplyRails.py, Milestone D.1):
        # Metal3 default — wide enough to carry the domain bulk, high
        # enough to clear the M1/M2 join corridor; 0.8um is ~4x the
        # Mn_a minimum-width track, snapped to the mfg grid
        "rail_options": {
            "default_layer": "Metal3",
            "allowed_layers": ["Metal3", "Metal4", "Metal5"],
            "default_width_um": 0.8,
            "allowed_sides": ["top", "bottom"]},
        # free-device multi-row folding (floorplanPlanner +
        # GroupsPlacement fold_rows, Milestone D.2) — true only while
        # the real DRC/LVS proof stands; revert to False otherwise.
        "multi_row": True,
        "shared_diffusion_rows": True,
        "routing_depth": 7,
        "estimator": False,
        "constraint_checkers": ["avoid_over"],
    }

    files = {
        "layoutPilotTech.py": _sha(_require(
            _PKG / "layoutPilotTech.py")),
        "sg13g2_tech.json": _sha(_require(
            _PKG / "sg13g2_tech.json")),
        "drc/rule_decks/sg13g2_tech_default.json": _sha(_require(
            _PKG / "drc" / "rule_decks"
            / "sg13g2_tech_default.json")),
        "pcellParameterMap.json": _sha(_require(
            _PKG / "pcellParameterMap.json")),
        "process.py": _sha(_require(_PKG / "process.py")),
    }

    snapshot = {
        "format": _FORMAT,
        "version": _VERSION,
        "pdk": {"name": "ihp_pdk", "id": "ihp_sg13g2",
                "version": str(_read_json(
                    _PKG / "config.json").get("pdk_version", ""))},
        "process": {"dbu": int(process.dbu),
                    "snap_grid_um": float(process.snapGrid),
                    "mfg_grid_um": _mfg_grid_um()},
        "devices": devices,
        "layers": {"stack": {"conductors": list(_STACK_CONDUCTORS),
                             "cuts": dict(_STACK_CUTS)},
                   "roles": dict(_LAYER_ROLES)},
        "rules": {"values": rules, "roles": dict(_ROLES)},
        "verification": verification,
        "capabilities": capabilities,
        "files": files,
    }
    digest = hashlib.sha256(
        json.dumps({"files": files, "devices": devices,
                    "layers": snapshot["layers"],
                    "rules": snapshot["rules"],
                    "verification": verification,
                    "capabilities": capabilities},
                   sort_keys=True,
                   separators=(",", ":")).encode("utf-8")).hexdigest()
    snapshot["digest"] = digest
    return snapshot
