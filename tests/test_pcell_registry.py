# SPDX-License-Identifier: Apache-2.0
#
# IHP PDK for Revolution EDA
# Copyright (c) 2024-2026 Revolution Semiconductor

"""Regression tests for the ihp_pdk pcell registry.

Each test body runs in a subprocess so the pcell module import and the
REVEDA_PDK_PATH environment stay isolated from the pytest process and from
other tests that may load a different PDK.

Note: pytest imports the ``ihp_pdk`` package itself while collecting tests
inside it, so the parent pytest process also needs REVEDA_PDK_PATH (this
directory) and PYTHONPATH (the pdks dir and revolution-eda core) set.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

PDK_ROOT = Path(__file__).resolve().parents[1]
PDK_PARENT = PDK_ROOT.parent

# revolution-eda is a sibling of the pdks directory in the normal workspace
# layout; PYTHONPATH is honored as a fallback for other layouts.
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
    assert result.returncode == 0, (
        f"subprocess exited {result.returncode}\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
    return result


_REGISTRY_SCRIPT = """
import importlib
import inspect
import sys

sys.path.insert(0, {pdk_parent!r})
if {core_root!r}:
    sys.path.insert(0, {core_root!r})

from PySide6.QtWidgets import QApplication

app = QApplication([])

module = importlib.import_module("ihp_pdk.pcells")

# The offscreen Qt platform has no fonts; baseCell picks the first fixed-pitch
# family, so give QFontDatabase a deterministic stand-in for this headless run.
import ihp_pdk.pcells.base as pcell_base


class _FixedFontDB:
    def families(self):
        return ["Courier New"]

    @staticmethod
    def isFixedPitch(family):
        return True


pcell_base.QFontDatabase = _FixedFontDB

registry = module.pcells

for name in ("nmos", "nwtap", "subtap"):
    assert name in registry, f"missing pcell: {{name}}"
for name in ("NoFillerStack", "schottky"):
    assert name not in registry, f"stub pcell registered: {{name}}"

# Instantiate each registered pcell used by the failing layout records and
# regenerate shapes with its declared default parameters.
for name in ("nmos", "nwtap", "subtap"):
    cls = registry[name]
    instance = cls()
    defaults = {{
        pname: p.default
        for pname, p in inspect.signature(type(instance).__init__).parameters.items()
        if p.default is not inspect.Parameter.empty
    }}
    instance(**defaults)
    assert instance.shapes, f"{{name}} produced no shapes"
    bounds = instance.boundingRect()
    assert not bounds.isNull() and bounds.isValid(), (
        f"{{name}} produced empty boundingRect: {{bounds}}")
    print(name, "shapes:", len(instance.shapes), "bbox:", bounds)
"""


_LOADER_SCRIPT = """
import logging
import sys
from types import SimpleNamespace

sys.path.insert(0, {pdk_parent!r})
if {core_root!r}:
    sys.path.insert(0, {core_root!r})

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

app = QApplication([])

from revedaEditor.fileio import loadJSON

# The offscreen Qt platform has no fonts; baseCell picks the first fixed-pitch
# family, so give QFontDatabase a deterministic stand-in for this headless run.
import ihp_pdk.pcells.base as pcell_base


class _FixedFontDB:
    def families(self):
        return ["Courier New"]

    @staticmethod
    def isFixedPitch(family):
        return True


pcell_base.QFontDatabase = _FixedFontDB

scene = SimpleNamespace(
    libraryDict={{"sg13g2_pr": {sg13g2_pr!r}}},
    rulerFont=QFont(),
    snapTuple=(5, 5),
    rulerWidth=1,
    logger=logging.getLogger("test_pcell_registry"),
)
factory = loadJSON.layoutItems(scene)

CASES = {{
    "nwtap": {{"width": "2u", "length": "2u"}},
    "subtap": {{"width": "2u", "length": "2u"}},
    "sg13_lv_nmos": {{"width": "4u", "length": "0.13u", "ng": "1"}},
}}

for cell, params in CASES.items():
    item = {{
        "type": "Pcell",
        "lib": "sg13g2_pr",
        "cell": cell,
        "view": "pcell",
        "nam": f"{{cell}}_i0",
        "ic": 0,
        "loc": [0, 0],
        "params": params,
    }}
    instance = factory.createPcellInstance(item)
    assert instance is not None, f"createPcellInstance returned None for {{cell}}"
    assert instance.instanceName == item["nam"], (
        f"{{cell}}: instanceName {{instance.instanceName!r}} != {{item['nam']!r}}")
    assert instance.shapes, f"{{cell}} instance has no shapes"
    print(cell, "ok: shapes", len(instance.shapes))
"""


def test_pcell_registry_imports_and_generates_layout():
    _run(
        _REGISTRY_SCRIPT.format(
            pdk_parent=str(PDK_PARENT),
            core_root=str(CORE_ROOT) if CORE_ROOT else "",
        )
    )


def test_layout_loader_creates_pcell_instances():
    _run(
        _LOADER_SCRIPT.format(
            pdk_parent=str(PDK_PARENT),
            core_root=str(CORE_ROOT) if CORE_ROOT else "",
            sg13g2_pr=str(PDK_ROOT / "sg13g2_pr"),
        )
    )
