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
$DataDirs = @("stipples", "drc", "lvs", "models", "va_modules", "sg13g2_pr", "docs")
# Data files at the package root that must be included
$DataFiles = @("config.json", "sg13g2_tech.json", "modelLibSettings.json")

foreach ($PyVer in @("3.13")) {
    $ArtifactName = "windows-amd64-py${PyVer}"
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Building IHP PDK binary for Windows - Python $PyVer" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

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
        --include-package=${PdkName}.pcells `
        --include-package=${PdkName}.lvs `
        --include-package=${PdkName}.drc `
        --output-dir=$OutputDir `
        --assume-yes-for-downloads `
        --no-pyi-file `
        --jobs=2 `
        --lto=no `
        $PdkSrc

    if ($LASTEXITCODE -ne 0) {
        throw "Nuitka build failed for IHP PDK (Python $PyVer)"
    }

    # Locate compiled output
    $PdkDistFolder = Join-Path $OutputDir "${PdkName}.dist"
    $PdkBuildFolder = Join-Path $OutputDir "${PdkName}.build"
    $FinalFolder = Join-Path $OutputDir $PdkName

    if (Test-Path $PdkDistFolder) {
        Rename-Item -Path $PdkDistFolder -NewName $PdkName
    } elseif (-not (Test-Path $FinalFolder)) {
        # Nuitka may output directly without .dist suffix
        Write-Warning "Expected dist folder not found, checking alternative locations..."
        $AltFolder = Join-Path $OutputDir $PdkName
        if (-not (Test-Path $AltFolder)) {
            throw "Cannot locate Nuitka output for IHP PDK"
        }
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

    # Clean up build artifacts
    Write-Host "Cleaning up build artifacts..."
    if (Test-Path $PdkBuildFolder) { Remove-Item -Recurse -Force $PdkBuildFolder }

    # Create zip artifact (the zip root should be ihp_pdk/ so extraction places it correctly)
    Write-Host "Creating zip artifact..."
    $ZipName = Join-Path $OutputBase "${PdkName}-${ArtifactName}.zip"
    if (Test-Path $ZipName) { Remove-Item -Force $ZipName }
    Compress-Archive -Path $FinalFolder -DestinationPath $ZipName -Force

    Write-Host "Build completed! Artifact: $ZipName" -ForegroundColor Green
    Write-Host ""
}

Write-Host "All IHP PDK builds completed." -ForegroundColor Green
Write-Host ""
Write-Host "Release artifacts:" -ForegroundColor Yellow
Get-ChildItem -Path $OutputBase -Filter "*.zip" | ForEach-Object {
    Write-Host "  $($_.FullName)" -ForegroundColor Yellow
}
