#!/bin/bash
# Linux build script for IHP PDK (ihp_pdk)
# Compiles the PDK as a Nuitka binary package (.so) for distribution.
# Produces platform-versioned zip artifacts ready for the PDK registry.
#
# Usage: ./build_linux.sh
#   PYTHON_VERSIONS="3.13" ./build_linux.sh   (override versions)
#   IHP_PDK_PYTHON=/path/python ./build_linux.sh  (use this interpreter; version derived)
#   IHP_PDK_SOURCE_ONLY=1 ./build_linux.sh    (only the source zip, no compile)
#   IHP_PDK_SKIP_SOURCE=1 ./build_linux.sh    (skip the source zip)
#   IHP_PDK_OUTPUT=/path ./build_linux.sh     (override artifact output)
#   IHP_PDK_BUILD_DIR=/path ./build_linux.sh  (override build scratch dir)
#   POETRY_VENV_BASE=/path ./build_linux.sh   (override venv search dir)

set -euo pipefail

PdkName="ihp_pdk"
PdkSrc="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VenvBase="${POETRY_VENV_BASE:-$HOME/.poetryenvs}"
OutputBase="${IHP_PDK_OUTPUT:-$HOME/dist/ihp_pdk}"
BuildBase="${IHP_PDK_BUILD_DIR:-$HOME/.reveda_builds}"
PYTHON_VERSIONS="${PYTHON_VERSIONS:-"3.12 3.13 3.14"}"

# A pinned interpreter (CI) overrides venv discovery; the version is derived
# from it so artifacts are never mislabeled.
if [ -n "${IHP_PDK_PYTHON:-}" ]; then
    PYTHON_VERSIONS=$("$IHP_PDK_PYTHON" -c \
        'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
fi

mkdir -p "$OutputBase" "$BuildBase"

# Data directories copied verbatim next to the compiled extension
DataDirs=(stipples drc lvs models sg13g2_pr docs pex)
RequiredDataFiles=(config.json sg13g2_tech.json modelLibSettings.json pcellParameterMap.json)

PASS=()
FAIL=()

# ---------------------------------------------------------------------------
# resolve_pythons VERSION — list pythonX.Y under *-pyX.Y/bin/ dirs in VenvBase
# ---------------------------------------------------------------------------
resolve_pythons() {
    local ver="$1"
    find "$VenvBase" -maxdepth 3 -name "python${ver}" \
         -path "*-py${ver}/bin/python${ver}" 2>/dev/null
}

if [ "$(uname -m)" != "x86_64" ]; then
    echo "ERROR: This script only supports x86_64 builds." >&2
    exit 1
fi

for tool in zip unzip; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: $tool is required but not installed." >&2
        exit 1
    fi
done

echo "============================================"
echo " IHP PDK Binary Builder (Linux)"
echo " Versions : $PYTHON_VERSIONS"
echo " Venvs    : $VenvBase"
echo " Output   : $OutputBase"
echo " BuildDir : $BuildBase"
echo "============================================"

if [ "${IHP_PDK_SOURCE_ONLY:-0}" != "1" ]; then
for PyVer in $PYTHON_VERSIONS; do
    LABEL="ihp_pdk/py$PyVer"
    if [ -n "${IHP_PDK_PYTHON:-}" ]; then
        Candidates=("$IHP_PDK_PYTHON")
    else
        mapfile -t Candidates < <(resolve_pythons "$PyVer")
    fi
    if [ ${#Candidates[@]} -eq 0 ]; then
        echo "FAIL [$LABEL] No python$PyVer under $VenvBase" >&2
        FAIL+=("$LABEL (no env)")
        continue
    fi
    PythonPath=""
    for candidate in "${Candidates[@]}"; do
        if "$candidate" -m nuitka --version >/dev/null 2>&1; then
            PythonPath="$candidate"
            break
        fi
    done
    if [ -z "$PythonPath" ]; then
        echo "FAIL [$LABEL] nuitka not available (checked: ${Candidates[*]})" >&2
        FAIL+=("$LABEL (no nuitka)")
        continue
    fi

    BuildDir="$BuildBase/ihp_pdk_py$PyVer"
    rm -rf "$BuildDir"
    mkdir -p "$BuildDir"

    echo "--------------------------------------------"
    echo "Building : $LABEL"
    echo "Python   : $PythonPath  ($("$PythonPath" --version))"
    echo "--------------------------------------------"

    # Compile only the ihp_pdk package; host/runtime deps stay external.
    if ! "$PythonPath" -m nuitka \
        --mode=package \
        --include-package="$PdkName" \
        --nofollow-import-to=PySide6 \
        --nofollow-import-to=revedaEditor \
        --nofollow-import-to=quantiphy \
        --nofollow-import-to=klayout \
        --output-dir="$BuildDir" \
        --jobs=1 \
        --low-memory \
        --lto=no \
        --assume-yes-for-downloads \
        --no-pyi-file \
        "$PdkSrc"; then
        echo "FAIL [$LABEL] Nuitka build failed" >&2
        FAIL+=("$LABEL (nuitka)")
        rm -rf "$BuildDir"
        continue
    fi

    shopt -s nullglob
    SoFiles=("$BuildDir/${PdkName}.cpython-"*.so)
    shopt -u nullglob
    if [ ${#SoFiles[@]} -lt 1 ]; then
        echo "FAIL [$LABEL] Nuitka produced no ${PdkName}.cpython-*.so in $BuildDir" >&2
        FAIL+=("$LABEL (no extension)")
        rm -rf "$BuildDir"
        continue
    fi
    SoName=$(basename "${SoFiles[0]}")

    PackageDir="$BuildDir/$PdkName"
    mkdir -p "$PackageDir"

    for dir in "${DataDirs[@]}"; do
        [ -d "$PdkSrc/$dir" ] && cp -r "$PdkSrc/$dir" "$PackageDir/$dir"
    done

    for file in "${RequiredDataFiles[@]}"; do
        if [ ! -f "$PdkSrc/$file" ]; then
            echo "FAIL [$LABEL] required data file missing: $PdkSrc/$file" >&2
            FAIL+=("$LABEL (missing $file)")
            rm -rf "$BuildDir"
            continue 2
        fi
        cp "$PdkSrc/$file" "$PackageDir/$file"
    done
    [ -f "$PdkSrc/README.md" ] && cp "$PdkSrc/README.md" "$PackageDir/README.md"

    # Bootstrap __init__.py: makes the staged dir a package for discovery,
    # keeps __file__-rooted resource paths, and loads the sibling extension.
    cat > "$PackageDir/__init__.py" <<'EOF'
"""Bootstrap for the compiled ihp_pdk extension shipped beside this package."""

import sys
from importlib.machinery import EXTENSION_SUFFIXES
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_package_dir = Path(__file__).resolve().parent

# Prefer artifacts matching this interpreter's ABI tag; stale extensions left
# behind by installs for other Python versions are never picked. Fall back to
# trying every compiled sibling so unexpected tag spellings still work.
_candidates = [
    candidate
    for suffix in EXTENSION_SUFFIXES
    if (candidate := _package_dir.parent / f"{__name__}{suffix}").exists()
]
if not _candidates:
    _candidates = sorted(
        p for p in _package_dir.parent.glob(f"{__name__}.*")
        if p.suffix in {".so", ".pyd"}
    )

_errors = []
for _extension in _candidates:
    _spec = spec_from_file_location(
        __name__, _extension, submodule_search_locations=[str(_package_dir)]
    )
    if _spec is None or _spec.loader is None:
        continue
    _previous = sys.modules.get(__name__)
    try:
        _module = module_from_spec(_spec)
        sys.modules[__name__] = _module
        _spec.loader.exec_module(_module)
    except Exception as exc:
        if _previous is not None:
            sys.modules[__name__] = _previous
        else:
            sys.modules.pop(__name__, None)
        _errors.append(exc)
        continue
    break
else:
    _detail = f": {_errors[-1]}" if _errors else ""
    raise ImportError(f"Unable to load compiled module for {__name__!r}{_detail}")
EOF

    # Mark the staged config as a binary distribution (source stays binary=0)
    "$PythonPath" - "$PackageDir/config.json" <<'PYEOF'
import json
import sys

path = sys.argv[1]
with open(path, "r+", encoding="utf-8") as f:
    cfg = json.load(f)
    cfg["binary"] = 1
    f.seek(0)
    json.dump(cfg, f, indent=2)
    f.truncate()
PYEOF

    # Remove bytecode caches and Nuitka scratch before zipping
    find "$PackageDir" -type d -name "__pycache__" -prune -exec rm -rf {} +
    find "$PackageDir" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete
    rm -rf "$BuildDir/${PdkName}.build" "$BuildDir/${PdkName}.dist"
    rm -f  "$BuildDir/${PdkName}.pyi"

    ZipTmp="$BuildDir/ihp_pdk-linux-x86_64-py${PyVer}.zip"
    (cd "$BuildDir" && zip -qr "$ZipTmp" "$SoName" "$PdkName")
    if ! unzip -t "$ZipTmp" >/dev/null; then
        echo "FAIL [$LABEL] zip integrity check failed" >&2
        FAIL+=("$LABEL (bad zip)")
        rm -rf "$BuildDir"
        continue
    fi
    mv "$ZipTmp" "$OutputBase/"
    rm -rf "$BuildDir"
    echo "OK  [$LABEL] -> $OutputBase/ihp_pdk-linux-x86_64-py${PyVer}.zip"
    PASS+=("$LABEL")
done

echo ""
echo "============================================"
echo " Build Summary"
echo "============================================"
for entry in "${PASS[@]}"; do echo "  PASS : $entry"; done
for entry in "${FAIL[@]}"; do echo "  FAIL : $entry"; done
echo "============================================"
if [ ${#FAIL[@]} -gt 0 ]; then
    exit 1
fi
fi  # IHP_PDK_SOURCE_ONLY

if [ "${IHP_PDK_SKIP_SOURCE:-0}" = "1" ]; then
    exit 0
fi

# Source distribution (after binary builds succeed)
echo "Creating source distribution..."
SourceZip="$OutputBase/${PdkName}-source.zip"
rm -f "$SourceZip"
( cd "$(dirname "$PdkSrc")" && zip -qr "$SourceZip" "$PdkName" \
    -x "$PdkName/.git/*" \
    -x "$PdkName/.github/*" \
    -x "*/__pycache__/*" \
    -x "*.pyc" -x "*.pyo" \
    -x "*/.pytest_cache/*" \
    -x "*/.hypothesis/*" \
    -x "*/.vscode/*" \
    -x "*/.VSCodeCounter/*" \
    -x "*/dist/*" \
    -x "$PdkName/*.build/*" -x "$PdkName/*.dist/*" )
unzip -t "$SourceZip" >/dev/null
echo "Source distribution: $SourceZip"
