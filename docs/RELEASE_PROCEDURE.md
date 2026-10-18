# IHP PDK Release Procedure

How to publish a source + binary release of the IHP SG13G2 PDK. Releases are
built and published locally — no CI involved.

## Prerequisites

- `gh` CLI authenticated (`gh auth login`) with write access to
  `eskiyerli/revolutionEDA_pdks`
- Python 3.12–3.14 with Nuitka (`pip install nuitka`) in each build env
- Linux x86_64 machine for Linux binaries and the source zip
- Windows machine with the MSVC toolchain for Windows binaries
- `zip` and `unzip` (Linux)

## What a release produces

| Artifact | Description |
|----------|-------------|
| `ihp_pdk-source.zip` | Full Python source, works on all platforms |
| `ihp_pdk-windows-amd64-py3.X.zip` | Compiled `.pyd` modules, per Python version |
| `ihp_pdk-linux-x86_64-py3.X.zip` | Compiled `.so` modules, per Python version |

Users install these via **Tools -> PDK -> Setup PDK** in Revolution EDA.

## Steps

### 1. Bump and tag

Update `pdk_version` in `config.json`, then commit and tag:

```bash
git commit -am "Release v0.3.0"
git tag -a v0.3.0 -m "IHP SG13G2 PDK v0.3.0"
git push origin main --tags
```

### 2. Build the zips

```bash
./build_linux.sh        # linux-x86_64 zips + ihp_pdk-source.zip → ~/dist/ihp_pdk
```

On a Windows machine:

```powershell
.\build_windows.ps1     # windows-amd64 zips → %USERPROFILE%\dist\ihp_pdk
```

To get the Windows zips onto the release, either:

- **Copy them into the Linux dist dir** (`~/dist/ihp_pdk`) and re-run
  `./release.sh` there, or
- **Upload straight from Windows** (Git Bash or PowerShell, with `gh`
  authenticated):

  ```powershell
  gh release upload ihp_pdk-v0.3.0 "$env:USERPROFILE\dist\ihp_pdk\*.zip" `
      --repo eskiyerli/revolutionEDA_pdks --clobber
  ```

  then re-run `./release.sh` anywhere (it also runs under Git Bash). With no
  local zips it just rewrites `pdks.json` from the release's asset list.

### 3. Publish

```bash
./release.sh
```

This reads `pdk_version` from `config.json`, creates release
`ihp_pdk-v<version>` in `revolutionEDA_pdks` (on `main`), uploads every
`*.zip` in the dist dir, then rewrites `pdks.json` from the release's actual
asset list and pushes the registry update.

If the release already exists it uploads/replaces the assets instead.
`pdks.json` is regenerated from the assets on GitHub, not the local dir, so
re-running is always safe — even from a machine that only has a subset of
the zips (or none, when just fixing the registry).

Environment variables:
- `IHP_PDK_OUTPUT` — zip directory (default `~/dist/ihp_pdk`, same as
  `build_linux.sh`)
- `REGISTRY_REPO` — registry repo (default `eskiyerli/revolutionEDA_pdks`)

### 4. Verify

1. Open Revolution EDA → **Tools -> PDK -> Setup PDK** → **Refresh**
2. The new version should appear with an upgrade indicator
3. Install both source and binary variants on test machines
4. Verify DRC/LVS menu items appear in the layout editor
5. Verify pcells instantiate correctly

---

## Reference

### How binary PDKs work

- Nuitka compiles the `ihp_pdk` package into a single `.so`/`.pyd` extension
  placed *beside* an `ihp_pdk/` data directory containing a bootstrap
  `__init__.py` that loads the compiled sibling.
- `"binary": 1` is set in the staged `config.json`; the source tree keeps `0`.
- `pdkLoader.py` adds the PDK parent directory to `sys.path` and imports by
  package name — no special handling needed for binary vs source.

### Data files

These are NOT compiled and are copied verbatim into the binary distribution:

| Path | Purpose |
|------|---------|
| `stipples/` | Layer fill patterns (PNG + TXT) |
| `drc/` | KLayout DRC rule decks |
| `lvs/` | KLayout LVS rule decks |
| `models/` | Xyce/VACASK device models |
| `sg13g2_pr/` | Primitive cell library (JSON cell views) |
| `pex/` | RC extraction technology file |
| `docs/` | Documentation |
| `config.json` | PDK metadata and menu configuration |
| `sg13g2_tech.json` | Technology parameters |
| `modelLibSettings.json` | Model library paths |
| `pcellParameterMap.json` | Schematic↔pcell parameter mapping |

### Registry key format

The `binary_urls` dictionary uses keys in the format `{system}-{arch}-{pyver}`:
- `system` = `platform.system().lower()` (windows, linux)
- `arch` = `platform.machine().lower()` (amd64, x86_64)
- `pyver` = `py{major}{minor}` (py313, py312)

The Setup PDK dialog tries the most specific key first, then falls back to
less specific ones.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Nuitka build fails | Check Python version compatibility and disk space; the log in the build dir has details |
| Binary PDK won't import | Ensure Python version matches the build (e.g. py3.13 binary needs Python 3.13) |
| Missing menu items after install | Verify `config.json` is present in the installed PDK directory |
| DRC/LVS rules not found | Verify `drc/` and `lvs/` directories were included in the zip |
| `release.sh` can't find zips | Set `IHP_PDK_OUTPUT` to the directory containing them |
| "No URL for your platform" | Add the missing platform key to `binary_urls` in `pdks.json` |
| Version not showing as update | Ensure `pdk_version` in registry `pdks.json` and local `config.json` follow semver |
| gh auth/push fails | Run `gh auth login` with an account that can write to the registry repo |
