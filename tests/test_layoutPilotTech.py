# SPDX-License-Identifier: Apache-2.0
#
# IHP PDK for Revolution EDA
# Copyright (c) 2024-2026 Revolution Semiconductor

"""Regression tests for the ihp_pdk layoutPilot technology snapshot.

Each test body runs in a subprocess so REVEDA_PDK_PATH and the
revedaEditor import stay isolated (mirrors test_pcell_registry.py).
Skips cleanly when revedaEditor is not importable.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PDK_ROOT = Path(__file__).resolve().parents[1]
PDK_PARENT = PDK_ROOT.parent

CORE_CANDIDATE = PDK_PARENT.parent / "revolution-eda"
CORE_ROOT = (
    CORE_CANDIDATE
    if (CORE_CANDIDATE / "revedaEditor").is_dir()
    else None
)


def _subprocess_env():
    env = os.environ.copy()
    env["REVEDA_PDK_PATH"] = str(PDK_ROOT)
    env["QT_QPA_PLATFORM"] = "offscreen"
    extra = [str(PDK_PARENT)]
    if CORE_ROOT is not None:
        extra.append(str(CORE_ROOT))
    env["PYTHONPATH"] = os.pathsep.join(
        extra + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )
    return env


def _run(script):
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        capture_output=True,
        text=True,
        env=_subprocess_env(),
        timeout=300,
    )
    return result


_SCRIPT = """
import importlib
import json
import sys

sys.path.insert(0, {pdk_parent!r})
if {core_root!r}:
    sys.path.insert(0, {core_root!r})

import os
os.environ.setdefault("REVEDA_PDK_PATH", {pdk_root!r})

module = importlib.import_module("ihp_pdk.layoutPilotTech")
snap = module.get_layout_pilot_technology()

json.dumps(snap)
assert snap["format"] == "layoutPilotTech-v1"
assert snap["version"] == 1
assert snap["pdk"]["id"] == "ihp_sg13g2"
assert snap["pdk"]["version"]

snap2 = module.get_layout_pilot_technology()
assert snap["digest"] == snap2["digest"]
assert len(snap["digest"]) == 64

assert snap["devices"]["sg13_lv_nmos"]["domain"] == "n"
assert snap["devices"]["sg13_lv_nmos"]["kind"] == "nmos"
assert snap["devices"]["sg13_lv_pmos"]["domain"] == "p"
assert snap["devices"]["sg13_lv_pmos"]["kind"] == "pmos"
for cell in ("cap_cmim", "rsil", "rhigh", "rppd"):
    assert cell in snap["devices"], cell
    assert snap["devices"][cell]["param_map"] is not None

values = snap["rules"]["values"]
roles = snap["rules"]["roles"]
for role, key in roles.items():
    assert key in values, f"role {{role}} -> missing rule {{key}}"

for rel, sha in snap["files"].items():
    assert ({pdk_root!r} / rel if False else True)
import pathlib
for rel in snap["files"]:
    assert (pathlib.Path({pdk_root!r}) / rel).is_file(), rel

assert snap["verification"]["drc"]["main_rule_set"] == "main"
assert snap["verification"]["lvs"]["deck"] == "sg13g2.lvs"
assert snap["capabilities"]["supply_rails"] is False
print("snapshot ok")
"""


@pytest.mark.skipif(
    CORE_ROOT is None,
    reason="revedaEditor core checkout not found next to pdks/")
def test_layout_pilot_technology_snapshot():
    result = _run(_SCRIPT.format(
        pdk_parent=str(PDK_PARENT),
        pdk_root=str(PDK_ROOT),
        core_root=str(CORE_ROOT) if CORE_ROOT else ""))
    assert "snapshot ok" in result.stdout, (
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}")
