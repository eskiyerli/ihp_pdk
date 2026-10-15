# Windows build script for IHP PDK (ihp_pdk)
# Compiles the PDK as a Nuitka binary package (.pyd) for distribution.
# Produces platform-versioned zip artifacts ready for the PDK registry.

$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
$PdkName = "ihp_pdk"
$PdkSrc = $ScriptDir  # This script lives inside the ihp_pdk folder

$VenvBase = if ($env:POETRY_VENV_BASE) { $env:POETRY_VENV_BASE } else { "C:\Users\eskiye50\poetryenvs" }
$OutputBase = if ($env:IHP_PDK_OUTPUT) { $env:IHP_PDK_OUTPUT } else { "C:\Users\eskiye50\dist\ihp_pdk" }

# Data directories that must be copied verbatim (not compiled)
$DataDirs = @("stipples", "drc", "lvs", "models", "sg13g2_pr", "docs", "pex")
# Data files at the package root that must be included
$DataFiles = @("config.json", "sg13g2_tech.json", "modelLibSettings.json", "pcellParameterMap.json", "README.md")

# A pinned interpreter via IHP_PDK_PYTHON (CI) overrides Poetry venv discovery;
# the version is derived from it so artifacts are never mislabeled.
if ($env:IHP_PDK_PYTHON) {
    $PyVersions = @(& $env:IHP_PDK_PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
} else {
    $PyVersions = @("3.12", "3.13", "3.14")
}

foreach ($PyVer in $PyVersions) {
    $ArtifactName = "windows-amd64-py${PyVer}"
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Building IHP PDK binary for Windows - Python $PyVer" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    if ($env:IHP_PDK_PYTHON) {
        $PythonPath = $env:IHP_PDK_PYTHON
    } else {
        # Find Poetry virtual environment
        $Pattern = Join-Path $VenvBase "*py$PyVer"
        $MatchedDirs = Get-ChildItem -Directory -Path $Pattern -ErrorAction SilentlyContinue

        if (-not $MatchedDirs) {
            Write-Warning "Poetry env for Python $PyVer not found in $VenvBase -- skipping"
            continue
        }

        $PythonPath = Join-Path $MatchedDirs[0].FullName "Scripts\python.exe"
        if (-not (Test-Path $PythonPath)) {
            Write-Warning "python.exe not found in $($MatchedDirs[0].FullName) -- skipping"
            continue
        }
    }

    Write-Host "Using Python: $PythonPath"

    # Ensure nuitka is installed
    Write-Host "Installing/upgrading build dependencies..."
    & $PythonPath -m pip install --upgrade pip | Out-Null
    & $PythonPath -m pip install --upgrade nuitka | Out-Null

    # Output directory per Python version
    $OutputDir = Join-Path $OutputBase $ArtifactName
    if (Test-Path $OutputDir) {
        Write-Host "Cleaning previous build..."
        Remove-Item -Recurse -Force $OutputDir
    }
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

    # Build PDK as a compiled package
    Write-Host "Compiling IHP PDK with Nuitka (this may take several minutes)..."
    & $PythonPath -m nuitka `
        --mode=package `
        --msvc=latest `
        --include-package=$PdkName `
        --nofollow-import-to=PySide6 `
        --nofollow-import-to=revedaEditor `
        --nofollow-import-to=quantiphy `
        --nofollow-import-to=klayout `
        --output-dir=$OutputDir `
        --assume-yes-for-downloads `
        --no-pyi-file `
        --jobs=2 `
        --lto=no `
        $PdkSrc

    if ($LASTEXITCODE -ne 0) {
        throw "Nuitka build failed for IHP PDK (Python $PyVer)"
    }

    # Locate compiled output. Package mode emits either a <name>.dist folder
    # (compiled __init__ inside the package dir) or a bare <name>.cp*.pyd
    # sibling extension; both are staged into a loadable package layout.
    $PdkDistFolder = Join-Path $OutputDir "${PdkName}.dist"
    $PdkBuildFolder = Join-Path $OutputDir "${PdkName}.build"
    $FinalFolder = Join-Path $OutputDir $PdkName
    $PydFile = Get-ChildItem -Path $OutputDir -Filter "${PdkName}.cp*.pyd" -File -ErrorAction SilentlyContinue | Select-Object -First 1
    $SiblingLayout = $false

    if (Test-Path $PdkDistFolder) {
        Rename-Item -Path $PdkDistFolder -NewName $PdkName
    } elseif ($PydFile) {
        $SiblingLayout = $true
        New-Item -ItemType Directory -Force -Path $FinalFolder | Out-Null
    } elseif (-not (Test-Path $FinalFolder)) {
        throw "Cannot locate Nuitka output for IHP PDK"
    }

    # Copy data directories that Nuitka does not compile
    Write-Host "Copying data directories..."
    foreach ($dir in $DataDirs) {
        $SrcDir = Join-Path $PdkSrc $dir
        $DstDir = Join-Path $FinalFolder $dir
        if (Test-Path $SrcDir) {
            if (Test-Path $DstDir) { Remove-Item -Recurse -Force $DstDir }
            Copy-Item -Path $SrcDir -Destination $DstDir -Recurse -Force
            Write-Host "  Copied: $dir" -ForegroundColor DarkGreen
        }
    }

    # Copy data files at package root
    Write-Host "Copying data files..."
    foreach ($file in $DataFiles) {
        $SrcFile = Join-Path $PdkSrc $file
        $DstFile = Join-Path $FinalFolder $file
        if (Test-Path $SrcFile) {
            Copy-Item -Path $SrcFile -Destination $DstFile -Force
            Write-Host "  Copied: $file" -ForegroundColor DarkGreen
        }
    }

    # Update config.json to mark as binary build
    $ConfigPath = Join-Path $FinalFolder "config.json"
    if (Test-Path $ConfigPath) {
        $config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
        $config.binary = 1
        $config | ConvertTo-Json -Depth 10 | Set-Content $ConfigPath -Encoding UTF8
        Write-Host "  Updated config.json: binary=1" -ForegroundColor DarkGreen
    }

    # Sibling-extension layout needs a bootstrap __init__.py in the staged
    # package dir that loads the .pyd sitting next to it (same logic as the
    # Linux build script).
    if ($SiblingLayout) {
        $Bootstrap = @'
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
'@
        [System.IO.File]::WriteAllText((Join-Path $FinalFolder "__init__.py"), $Bootstrap)
    }

    # Clean up build artifacts
    Write-Host "Cleaning up build artifacts..."
    if (Test-Path $PdkBuildFolder) { Remove-Item -Recurse -Force $PdkBuildFolder }

    # Create zip artifact. Sibling layout ships the extension beside ihp_pdk/,
    # matching what the registry installer and bootstrap expect.
    Write-Host "Creating zip artifact..."
    $ZipName = Join-Path $OutputBase "${PdkName}-${ArtifactName}.zip"
    if (Test-Path $ZipName) { Remove-Item -Force $ZipName }
    $ZipInputs = @($FinalFolder)
    if ($SiblingLayout -and $PydFile) { $ZipInputs += $PydFile.FullName }
    Compress-Archive -Path $ZipInputs -DestinationPath $ZipName -Force

    Write-Host "Build completed! Artifact: $ZipName" -ForegroundColor Green
    Write-Host ""
}

Write-Host "All IHP PDK builds completed." -ForegroundColor Green
Write-Host ""
Write-Host "Release artifacts:" -ForegroundColor Yellow
Get-ChildItem -Path $OutputBase -Filter "*.zip" | ForEach-Object {
    Write-Host "  $($_.FullName)" -ForegroundColor Yellow
}
