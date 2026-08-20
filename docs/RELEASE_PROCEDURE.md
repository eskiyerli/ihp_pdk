# IHP PDK Release Procedure

This document describes how to release the IHP SG13G2 PDK as both source code and precompiled binary packages.

## Prerequisites

- Git repository with push access and tag permissions
- GitHub Personal Access Token (`REVEDA_PAT`) configured as a repository secret (needed to clone `revolution-eda` during CI builds)
- For local builds: Poetry virtual environment with Python 3.12 or 3.13, Nuitka installed

## Release Overview

Each release produces:

| Artifact | Description |
|----------|-------------|
| `ihp_pdk-source.zip` | Full Python source, works on all platforms |
| `ihp_pdk-windows-amd64-py3.13.zip` | Compiled `.pyd` modules for Windows x64, Python 3.13 |
| `ihp_pdk-windows-amd64-py3.12.zip` | Compiled `.pyd` modules for Windows x64, Python 3.12 |
| `ihp_pdk-linux-x86_64-py3.13.zip` | Compiled `.so` modules for Linux x86_64, Python 3.13 |
| `ihp_pdk-linux-x86_64-py3.12.zip` | Compiled `.so` modules for Linux x86_64, Python 3.12 |

Users install these via **Tools -> PDK -> Setup PDK** in Revolution EDA.

---

## Step 1: Prepare the Release

1. Update `config.json` with the new version:

```json
{
  "pdk_name": "IHP SG13G2",
  "pdk_version": "0.3.0",
  ...
}
```

2. Commit all changes:

```bash
git add -A
git commit -m "Release v0.3.0"
```

3. Verify nothing is broken by running Revolution EDA with the source PDK locally.

## Step 2: Tag and Push

Create an annotated tag matching the version:

```bash
git tag -a v0.3.0 -m "IHP SG13G2 PDK v0.3.0"
git push origin main --tags
```

This triggers the GitHub Actions workflow (`.github/workflows/build-pdk.yml`).

## Step 3: CI Build (Automatic)

The workflow runs automatically on tag push:

1. Checks out `ihp_pdk` and `revolution-eda` (build dependency)
2. Installs Python, Nuitka, PySide6, quantiphy, numpy
3. Compiles the PDK package with Nuitka for each platform/Python combination
4. Copies data directories (stipples, drc, lvs, models, va_modules, sg13g2_pr, docs)
5. Copies data files (config.json, sg13g2_tech.json, modelLibSettings.json)
6. Sets `"binary": 1` in the compiled artifact's config.json
7. Creates a source archive (excludes .git, __pycache__, build artifacts)
8. Attaches all zip artifacts to a GitHub Release

Monitor progress at: `https://github.com/eskiyerli/ihp_pdk/actions`

## Step 4: Update the PDK Registry

After the release is published, update `pdks.json` in the `revolutionEDA_pdks` registry repository:

```json
{
  "pdks": [
    {
      "name": "ihp_pdk",
      "pdk_name": "IHP SG13G2",
      "type": "source",
      "process": "SG13G2 130nm BiCMOS",
      "version": "0.3.0",
      "pdk_version": "0.3.0",
      "license": "Apache 2.0",
      "description": "IHP SG13G2 130nm SiGe BiCMOS PDK (source)...",
      "url": "https://github.com/eskiyerli/revolutionEDA_pdks/releases/download/v0.3.0/ihp_pdk-source.zip"
    },
    {
      "name": "ihp_pdk",
      "pdk_name": "IHP SG13G2 (Binary)",
      "type": "binary",
      "process": "SG13G2 130nm BiCMOS",
      "version": "0.3.0",
      "pdk_version": "0.3.0",
      "license": "Apache 2.0",
      "description": "IHP SG13G2 130nm SiGe BiCMOS PDK (precompiled binary)...",
      "binary_urls": {
        "windows-amd64-py313": "https://github.com/eskiyerli/revolutionEDA_pdks/releases/download/v0.3.0/ihp_pdk-windows-amd64-py3.13.zip",
        "windows-amd64-py312": "https://github.com/eskiyerli/revolutionEDA_pdks/releases/download/v0.3.0/ihp_pdk-windows-amd64-py3.12.zip",
        "linux-x86_64-py313": "https://github.com/eskiyerli/revolutionEDA_pdks/releases/download/v0.3.0/ihp_pdk-linux-x86_64-py3.13.zip",
        "linux-x86_64-py312": "https://github.com/eskiyerli/revolutionEDA_pdks/releases/download/v0.3.0/ihp_pdk-linux-x86_64-py3.12.zip",
        "windows-amd64": "https://github.com/eskiyerli/revolutionEDA_pdks/releases/download/v0.3.0/ihp_pdk-windows-amd64-py3.13.zip",
        "linux-x86_64": "https://github.com/eskiyerli/revolutionEDA_pdks/releases/download/v0.3.0/ihp_pdk-linux-x86_64-py3.13.zip"
      }
    }
  ]
}
```

Commit and push to `main` in the registry repo:

```bash
cd revolutionEDA_pdks
# edit pdks.json with new version URLs
git add pdks.json
git commit -m "Update IHP PDK to v0.3.0"
git push origin main
```

## Step 5: Verify

1. Open Revolution EDA
2. Go to **Tools -> PDK -> Setup PDK**
3. Click **Refresh** — the new version should appear with an upgrade indicator
4. Install both source and binary variants on test machines
5. Verify that DRC/LVS menu items appear in the layout editor
6. Verify that pcells instantiate correctly

---

## Local Build (Manual)

For local testing or when CI is unavailable, use `build_windows.ps1`:

```powershell
cd ihp_pdk
.\build_windows.ps1
```

Environment variables:
- `POETRY_VENV_BASE` — directory containing Poetry virtualenvs (default: `C:\Users\eskiye50\poetryenvs`)
- `IHP_PDK_OUTPUT` — output directory for artifacts (default: `C:\Users\eskiye50\dist\ihp_pdk`)

The script requires:
- Poetry virtualenv with PySide6, quantiphy, numpy, revedaEditor installed
- Nuitka (`pip install nuitka`)
- MSVC toolchain (Visual Studio Build Tools)

---

## Architecture Notes

### How Binary PDKs Work

- The Nuitka compiler produces `.pyd` (Windows) or `.so` (Linux) files from each `.py` module
- Python's `importlib.import_module()` transparently handles both source and compiled modules
- `pdkLoader.py` adds the PDK parent directory to `sys.path` and imports by package name — no special handling needed for binary vs source
- The `"binary": 1` flag in `config.json` is informational (shown in the Setup PDK dialog)

### Data Files

These are NOT compiled and must be copied verbatim into the binary distribution:

| Path | Purpose |
|------|---------|
| `stipples/` | Layer fill patterns (PNG + TXT) |
| `drc/` | KLayout DRC rule decks (`.lydrc`) |
| `lvs/` | KLayout LVS rule decks (`.lvs`) |
| `models/` | SPICE/Xyce device models |
| `va_modules/` | Verilog-A compiled plugins |
| `sg13g2_pr/` | Primitive cell library (JSON cell views) |
| `docs/` | Documentation |
| `config.json` | PDK metadata and menu configuration |
| `sg13g2_tech.json` | Technology parameters |
| `modelLibSettings.json` | Model library paths |

### Registry Key Format

The `binary_urls` dictionary uses keys in the format `{system}-{arch}-{pyver}`:
- `system` = `platform.system().lower()` (windows, linux)
- `arch` = `platform.machine().lower()` (amd64, x86_64)
- `pyver` = `py{major}{minor}` (py313, py312)

The Setup PDK dialog tries the most specific key first, then falls back to less specific ones.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CI fails at Nuitka compilation | Check that `revolution-eda` is importable (REVEDA_PAT secret must be set) |
| Binary PDK won't import | Ensure Python version matches the build (e.g. py3.13 binary needs Python 3.13) |
| Missing menu items after install | Verify `config.json` is present in the installed PDK directory |
| DRC/LVS rules not found | Verify `drc/` and `lvs/` directories were included in the zip |
| "No URL for your platform" | Add the missing platform key to `binary_urls` in `pdks.json` |
| Version not showing as update | Ensure `pdk_version` in both registry `pdks.json` and local `config.json` follow semver |
