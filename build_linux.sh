#!/bin/bash
# Linux build script for IHP PDK (ihp_pdk)
# Compiles the PDK as a Nuitka binary package (.so) for distribution.
# Produces platform-versioned zip artifacts ready for the PDK registry.

set -euo pipefail

PdkName="ihp_pdk"
PdkSrc="$(cd "$(dirname "$0")" && pwd)"

VenvBase="${POETRY_VENV_BASE:-$HOME/.poetryenvs}"
OutputBase="${IHP_PDK_OUTPUT:-$HOME/dist/ihp_pdk}"

# Data directories that must be copied verbatim (not compiled)
DataDirs=(stipples drc lvs models va_modules sg13g2_pr docs)
# Data files at the package root that must be included
DataFiles=(config.json sg13g2_tech.json modelLibSettings.json)

# Discover installed Poetry virtualenvs with Python version suffixes
shopt -s nullglob
VenvDirs=("$VenvBase"/*py[0-9].[0-9]*)
shopt -u nullglob

if [ ${#VenvDirs[@]} -eq 0 ]; then
    echo "Error: No Poetry virtual environments found in $VenvBase" >&2
    exit 1
fi

for VenvDir in "${VenvDirs[@]}"; do
    [ -d "$VenvDir" ] || continue

    VenvName=$(basename "$VenvDir")
    if [[ ! "$VenvName" =~ py([0-9]+\.[0-9]+)$ ]]; then
        continue
    fi
    PyVer="${BASH_REMATCH[1]}"
    PyTag="${PyVer//.}"

    ArtifactName="linux-x86_64-py${PyTag}"
    echo "========================================"
    echo "Building IHP PDK binary for Linux - Python $PyVer"
    echo "========================================"

    PythonPath="$VenvDir/bin/python"
    if [ ! -x "$PythonPath" ]; then
        echo "Warning: python not found in $VenvDir -- skipping"
        continue
    fi

    echo "Using Python: $PythonPath"

    # Ensure build dependencies are present
    echo "Installing/upgrading build dependencies..."
    "$PythonPath" -m pip install --upgrade pip >/dev/null
    "$PythonPath" -m pip install --upgrade nuitka >/dev/null

    # Output directory per Python version
    OutputDir="$OutputBase/$ArtifactName"
    if [ -d "$OutputDir" ]; then
        echo "Cleaning previous build..."
        rm -rf "$OutputDir"
    fi
    mkdir -p "$OutputDir"

    # Build PDK as a compiled package
    echo "Compiling IHP PDK with Nuitka (this may take several minutes)..."
    "$PythonPath" -m nuitka \
        --mode=package \
        --include-package="$PdkName" \
        --include-package="${PdkName}.pcells" \
        --include-package="${PdkName}.lvs" \
        --include-package="${PdkName}.drc" \
        --output-dir="$OutputDir" \
        --assume-yes-for-downloads \
        --no-pyi-file \
        --jobs=2 \
        --lto=no \
        "$PdkSrc"

    # Locate compiled output
    PdkBuildFolder="$OutputDir/${PdkName}.build"
    PackageDir="$OutputDir/$PdkName"

    shopt -s nullglob
    PdkSoFiles=("$OutputDir/${PdkName}.cpython-"*.so)
    shopt -u nullglob

    if [ ! -e "${PdkSoFiles[0]}" ]; then
        echo "Error: Cannot locate Nuitka output for IHP PDK" >&2
        exit 1
    fi

    SoFile="${PdkSoFiles[0]}"
    SoName=$(basename "$SoFile")

    # Create the data directory for this binary package
    mkdir -p "$PackageDir"

    # Copy data directories that Nuitka does not compile
    echo "Copying data directories..."
    for dir in "${DataDirs[@]}"; do
        SrcDir="$PdkSrc/$dir"
        DstDir="$PackageDir/$dir"
        if [ -d "$SrcDir" ]; then
            rm -rf "$DstDir"
            cp -r "$SrcDir" "$DstDir"
            echo "  Copied: $dir"
        fi
    done

    # Copy data files at package root
    echo "Copying data files..."
    for file in "${DataFiles[@]}"; do
        SrcFile="$PdkSrc/$file"
        DstFile="$PackageDir/$file"
        if [ -f "$SrcFile" ]; then
            cp "$SrcFile" "$DstFile"
            echo "  Copied: $file"
        fi
    done

    # Update config.json to mark as binary build
    ConfigPath="$PackageDir/config.json"
    if [ -f "$ConfigPath" ]; then
        "$PythonPath" - <<PY
import json
with open('${ConfigPath}', 'r+', encoding='utf-8') as f:
    cfg = json.load(f)
    cfg['binary'] = 1
    f.seek(0)
    json.dump(cfg, f, indent=2)
    f.truncate()
PY
        echo "  Updated config.json: binary=1"
    fi

    # Clean up build artifacts
    echo "Cleaning up build artifacts..."
    if [ -d "$PdkBuildFolder" ]; then
        rm -rf "$PdkBuildFolder"
    fi

    # Create zip artifact (.so at top, ihp_pdk/ data dir beside it)
    echo "Creating zip artifact..."
    ZipName="$OutputBase/${ArtifactName}.zip"
    rm -f "$ZipName"
    (cd "$OutputDir" && zip -r "$ZipName" "$SoName" "$PdkName" >/dev/null)

    echo "Build completed! Artifact: $ZipName"
    echo ""
done

# Create source distribution (matches ihp_pdk.zip)
echo "Creating source distribution..."
SourceZip="$OutputBase/${PdkName}.zip"
rm -f "$SourceZip"
( cd "$(dirname "$PdkSrc")" && zip -r "$SourceZip" "$PdkName" \
    -x "*/__pycache__/*" -x "*.pyc" -x "*.pyo" -x "*/.git/*" >/dev/null )

echo "Source distribution: $SourceZip"

echo "All IHP PDK builds completed."
echo ""
echo "Release artifacts:"
ls -1 "$OutputBase"/*.zip 2>/dev/null || true
