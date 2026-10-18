# Windows build script for IHP PDK (ihp_pdk)
# Compiles the PDK as a Nuitka binary package (.pyd) for distribution.
# Produces platform-versioned zip artifacts ready for the PDK registry.
#
# Usage: .\build_windows.ps1
#   $env:PYTHON_VERSIONS="3.13"; .\build_windows.ps1   (override versions)
#   $env:IHP_PDK_PYTHON="C:\path\python.exe"           (use this interpreter; version derived)
#   $env:IHP_PDK_OUTPUT="D:\dist"                      (override artifact output)
#   $env:IHP_PDK_BUILD_DIR="D:\build"                  (override build scratch dir)
#   $env:POETRY_VENV_BASE="C:\path"                    (override venv search dir)

$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
$PdkName = "ihp_pdk"
$PdkSrc = $ScriptDir  # This script lives inside the ihp_pdk folder

$VenvBase = if ($env:POETRY_VENV_BASE) { $env:POETRY_VENV_BASE } else { "C:\Users\eskiye50\poetryenvs" }
$OutputBase = if ($env:IHP_PDK_OUTPUT) { $env:IHP_PDK_OUTPUT } else { "C:\Users\eskiye50\dist\ihp_pdk" }
$BuildBase = if ($env:IHP_PDK_BUILD_DIR) { $env:IHP_PDK_BUILD_DIR } else { "$env:USERPROFILE\.reveda_builds" }

# A pinned interpreter (IHP_PDK_PYTHON) overrides venv discovery; the version
# is derived from it so artifacts are never mislabeled.
if ($env:IHP_PDK_PYTHON) {
    $PyVersions = @(& $env:IHP_PDK_PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
} elseif ($env:PYTHON_VERSIONS) {
    $PyVersions = @($env:PYTHON_VERSIONS -split '\s+' | Where-Object { $_ })
} else {
    $PyVersions = @("3.12", "3.13", "3.14")
}

# Data directories copied verbatim next to the compiled extension
$DataDirs = @("stipples", "drc", "lvs", "models", "sg13g2_pr", "docs", "pex")
$RequiredDataFiles = @("config.json", "sg13g2_tech.json", "modelLibSettings.json", "pcellParameterMap.json")

$Pass = @()
$Fail = @()

if ([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture -ne 'X64') {
    Write-Error "This script only supports x64 builds."
    exit 1
}

New-Item -ItemType Directory -Force -Path $OutputBase, $BuildBase | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " IHP PDK Binary Builder (Windows)" -ForegroundColor Cyan
Write-Host " Versions : $($PyVersions -join ' ')" -ForegroundColor Cyan
Write-Host " Venvs    : $VenvBase" -ForegroundColor Cyan
Write-Host " Output   : $OutputBase" -ForegroundColor Cyan
Write-Host " BuildDir : $BuildBase" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

foreach ($PyVer in $PyVersions) {
    $Label = "ihp_pdk/py$PyVer"
    $ArtifactName = "windows-amd64-py${PyVer}"

    if ($env:IHP_PDK_PYTHON) {
        $Candidates = @($env:IHP_PDK_PYTHON)
    } else {
        $Candidates = @(
            Get-ChildItem -Directory -Path (Join-Path $VenvBase "*-py$PyVer") -ErrorAction SilentlyContinue |
            ForEach-Object { Join-Path $_.FullName "Scripts\python.exe" } |
            Where-Object { Test-Path $_ }
        )
    }
    if (-not $Candidates) {
        Write-Host "FAIL [$Label] No python$PyVer under $VenvBase" -ForegroundColor Red
        $Fail += "$Label (no env)"
        continue
    }

    $PythonPath = $null
    $NuitkaErr = ""
    foreach ($candidate in $Candidates) {
        if (-not (Test-Path $candidate)) {
            $NuitkaErr = "not found: $candidate"
            continue
        }
        try {
            $check = & $candidate -m nuitka --version 2>&1 | Out-String
        } catch {
            $check = "$_"
            $LASTEXITCODE = 1
        }
        if ($LASTEXITCODE -eq 0) {
            $PythonPath = $candidate
            break
        }
        $NuitkaErr = (($check -split "`r?`n") | Where-Object { $_ } | Select-Object -First 1)
    }
    if (-not $PythonPath) {
        Write-Host "FAIL [$Label] nuitka unusable (checked: $($Candidates -join ', '))" -ForegroundColor Red
        if ($NuitkaErr) { Write-Host "       $NuitkaErr" -ForegroundColor Red }
        $Fail += "$Label (no nuitka)"
        continue
    }

    $BuildDir = Join-Path $BuildBase "ihp_pdk_py$PyVer"
    if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
    New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

    Write-Host "--------------------------------------------" -ForegroundColor Cyan
    Write-Host "Building : $Label" -ForegroundColor Cyan
    Write-Host "Python   : $PythonPath  ($(& $PythonPath --version))" -ForegroundColor Cyan
    Write-Host "--------------------------------------------" -ForegroundColor Cyan

    # Compile only the ihp_pdk package; host/runtime deps stay external.
    & $PythonPath -m nuitka `
        --mode=package `
        --msvc=latest `
        --include-package=$PdkName `
        --nofollow-import-to=PySide6 `
        --nofollow-import-to=revedaEditor `
        --nofollow-import-to=quantiphy `
        --nofollow-import-to=klayout `
        --output-dir=$BuildDir `
        --assume-yes-for-downloads `
        --no-pyi-file `
        --jobs=2 `
        --lto=no `
        $PdkSrc

    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL [$Label] Nuitka build failed" -ForegroundColor Red
        $Fail += "$Label (nuitka)"
        Remove-Item -Recurse -Force $BuildDir
        continue
    }

    # Locate compiled output. Package mode emits either a <name>.dist folder
    # (compiled __init__ inside the package dir) or a bare <name>.cp*.pyd
    # sibling extension; both are staged into a loadable package layout.
    $PdkDistFolder = Join-Path $BuildDir "${PdkName}.dist"
    $PdkBuildFolder = Join-Path $BuildDir "${PdkName}.build"
    $FinalFolder = Join-Path $BuildDir $PdkName
    $PydFile = Get-ChildItem -Path $BuildDir -Filter "${PdkName}.cp*.pyd" -File -ErrorAction SilentlyContinue | Select-Object -First 1
    $SiblingLayout = $false

    if (Test-Path $PdkDistFolder) {
        Rename-Item -Path $PdkDistFolder -NewName $PdkName
    } elseif ($PydFile) {
        $SiblingLayout = $true
        New-Item -ItemType Directory -Force -Path $FinalFolder | Out-Null
    } elseif (-not (Test-Path $FinalFolder)) {
        Write-Host "FAIL [$Label] cannot locate Nuitka output in $BuildDir" -ForegroundColor Red
        $Fail += "$Label (no extension)"
        Remove-Item -Recurse -Force $BuildDir
        continue
    }

    foreach ($dir in $DataDirs) {
        $SrcDir = Join-Path $PdkSrc $dir
        if (Test-Path $SrcDir) {
            Copy-Item -Path $SrcDir -Destination (Join-Path $FinalFolder $dir) -Recurse -Force
        }
    }

    $MissingFile = $null
    foreach ($file in $RequiredDataFiles) {
        $SrcFile = Join-Path $PdkSrc $file
        if (-not (Test-Path $SrcFile)) {
            $MissingFile = $file
            break
        }
        Copy-Item -Path $SrcFile -Destination (Join-Path $FinalFolder $file) -Force
    }
    if ($MissingFile) {
        Write-Host "FAIL [$Label] required data file missing: $SrcFile" -ForegroundColor Red
        $Fail += "$Label (missing $MissingFile)"
        Remove-Item -Recurse -Force $BuildDir
        continue
    }
    $Readme = Join-Path $PdkSrc "README.md"
    if (Test-Path $Readme) { Copy-Item -Path $Readme -Destination (Join-Path $FinalFolder "README.md") -Force }

    # Mark the staged config as a binary distribution (source stays binary=0)
    $ConfigPath = Join-Path $FinalFolder "config.json"
    $config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
    $config.binary = 1
    $config | ConvertTo-Json -Depth 10 | Set-Content $ConfigPath -Encoding UTF8

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

    # Remove bytecode caches and Nuitka scratch before zipping
    Get-ChildItem -Path $FinalFolder -Recurse -Directory -Filter "__pycache__" |
        Remove-Item -Recurse -Force
    Get-ChildItem -Path $FinalFolder -Recurse -Include "*.pyc", "*.pyo" -File |
        Remove-Item -Force
    if (Test-Path $PdkBuildFolder) { Remove-Item -Recurse -Force $PdkBuildFolder }
    $PdkPyi = Join-Path $BuildDir "${PdkName}.pyi"
    if (Test-Path $PdkPyi) { Remove-Item -Force $PdkPyi }

    # Create zip artifact. Sibling layout ships the extension beside ihp_pdk/,
    # matching what the registry installer and bootstrap expect.
    $ZipTmp = Join-Path $BuildDir "${PdkName}-${ArtifactName}.zip"
    if (Test-Path $ZipTmp) { Remove-Item -Force $ZipTmp }
    $ZipInputs = @($FinalFolder)
    if ($SiblingLayout -and $PydFile) { $ZipInputs += $PydFile.FullName }
    Compress-Archive -Path $ZipInputs -DestinationPath $ZipTmp -Force

    # Integrity check: fully decompress every entry (like `unzip -t`)
    $zip = [System.IO.Compression.ZipFile]::OpenRead($ZipTmp)
    try {
        foreach ($entry in $zip.Entries) {
            $stream = $entry.Open()
            $stream.CopyTo([System.IO.Stream]::Null)
            $stream.Close()
        }
    } catch {
        Write-Host "FAIL [$Label] zip integrity check failed: $_" -ForegroundColor Red
        $Fail += "$Label (bad zip)"
        $zip.Dispose()
        Remove-Item -Recurse -Force $BuildDir
        continue
    }
    $zip.Dispose()

    $ZipFinal = Join-Path $OutputBase "${PdkName}-${ArtifactName}.zip"
    Move-Item -Path $ZipTmp -Destination $ZipFinal -Force
    Remove-Item -Recurse -Force $BuildDir
    Write-Host "OK  [$Label] -> $ZipFinal" -ForegroundColor Green
    $Pass += $Label
    Write-Host ""
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Build Summary" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
foreach ($entry in $Pass) { Write-Host "  PASS : $entry" -ForegroundColor Green }
foreach ($entry in $Fail) { Write-Host "  FAIL : $entry" -ForegroundColor Red }
Write-Host "============================================" -ForegroundColor Cyan
if ($Fail.Count -gt 0) { exit 1 }
