#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
#
# IHP PDK for Revolution EDA
# Copyright (c) 2024-2026 Revolution Semiconductor

# Publish an IHP PDK release: upload built zips to a GitHub Release in the
# central registry repo and update pdks.json there.
#
# Usage: ./release.sh
#   IHP_PDK_OUTPUT=/path/to/zips ./release.sh   (zip dir, default ~/dist/ihp_pdk)
#   REGISTRY_REPO=owner/repo ./release.sh       (override registry repo)
#
# Run build_linux.sh / build_windows.ps1 first; this script uploads whatever
# *.zip files are in the dist dir. If the release already exists the zips are
# added/replaced (--clobber), so binaries built on another machine can be
# added afterwards. pdks.json is always regenerated from the release's actual
# asset list on GitHub — local zips are not required for the registry update,
# so re-running with an empty dist dir also works (e.g. after uploading
# Windows zips from a Windows machine via 'gh release upload').
#
# Requires: gh (authenticated against the registry repo), git, python3/python.

set -euo pipefail

PdkName="ihp_pdk"
PdkSrc="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RegistryRepo="${REGISTRY_REPO:-eskiyerli/revolutionEDA_pdks}"
DistDir="${IHP_PDK_OUTPUT:-$HOME/dist/ihp_pdk}"

for tool in gh git; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: $tool is required but not installed." >&2
        exit 1
    fi
done
PYTHON="$(command -v python3 || command -v python || true)"
if [ -z "$PYTHON" ]; then
    echo "ERROR: python3/python is required but not installed." >&2
    exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
    echo "ERROR: not logged in to GitHub — run 'gh auth login' first." >&2
    exit 1
fi

Version=$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["pdk_version"])' \
          "$PdkSrc/config.json")
ReleaseTag="${PdkName}-v${Version}"

shopt -s nullglob
Zips=("$DistDir"/*.zip)
Partials=("$DistDir"/*.zip.*)
shopt -u nullglob
if [ ${#Partials[@]} -gt 0 ]; then
    echo "WARNING: incomplete files in $DistDir are ignored (sync in progress?):" >&2
    printf '   %s\n' "${Partials[@]##*/}" >&2
fi

ReleaseExists=0
if gh release view "$ReleaseTag" --repo "$RegistryRepo" >/dev/null 2>&1; then
    ReleaseExists=1
fi
if [ "$ReleaseExists" -eq 0 ] && [ ${#Zips[@]} -eq 0 ]; then
    echo "ERROR: no release $ReleaseTag in $RegistryRepo and no zips in $DistDir" >&2
    echo "       — run build_linux.sh (or set IHP_PDK_OUTPUT) first." >&2
    exit 1
fi

echo "============================================"
echo " IHP PDK Release"
echo " Version  : $Version  (tag $ReleaseTag)"
echo " Registry : $RegistryRepo"
echo " Zips     : $DistDir  (${#Zips[@]} local)"
printf '   %s\n' "${Zips[@]##*/}"
echo "============================================"

WorkDir=$(mktemp -d)
trap 'rm -rf "$WorkDir"' EXIT

if [ "$ReleaseExists" -eq 0 ]; then
    cat > "$WorkDir/notes.md" <<EOF
## IHP SG13G2 PDK Release ${Version}

### Installation
Use **Tools -> PDK -> Setup PDK** in Revolution EDA to install automatically.

### Packages
- **Source**: \`ihp_pdk-source.zip\` — full Python source, works on all platforms
- **Binary**: precompiled \`.pyd\`/\`.so\` modules per platform/Python version
EOF
    gh release create "$ReleaseTag" --repo "$RegistryRepo" --target main \
        --title "IHP PDK v${Version}" \
        --notes-file "$WorkDir/notes.md" \
        "${Zips[@]}"
elif [ ${#Zips[@]} -gt 0 ]; then
    echo "Release $ReleaseTag exists — uploading/replacing assets."
    gh release upload "$ReleaseTag" --repo "$RegistryRepo" \
        --clobber "${Zips[@]}"
fi

# --- Update pdks.json in the registry repo --------------------------------

# Registry URLs are derived from the release's real asset list, not the local
# zip dir, so partial/multi-machine uploads still produce a complete index.
mapfile -t Assets < <(
    gh release view "$ReleaseTag" --repo "$RegistryRepo" \
        --json assets --jq '.assets[].name'
)
if [ ${#Assets[@]} -eq 0 ]; then
    echo "ERROR: release $ReleaseTag has no assets — nothing to index." >&2
    exit 1
fi

# gh acts as the credential helper so no token lands in URLs or .git/config;
# the helper is persisted for the git push below.
gh repo clone "$RegistryRepo" "$WorkDir/registry" -- \
    --config credential.helper='!gh auth git-credential'

if ! git -C "$WorkDir/registry" config user.name >/dev/null 2>&1; then
    GhUser=$(gh api user --jq .login)
    git -C "$WorkDir/registry" config user.name "$GhUser"
    git -C "$WorkDir/registry" config user.email "${GhUser}@users.noreply.github.com"
fi

export PDK_NAME="$PdkName" RELEASE_TAG="$ReleaseTag" VERSION="$Version"
export REGISTRY_REPO="$RegistryRepo"
export ASSETS="$(printf '%s\n' "${Assets[@]}")"
"$PYTHON" - "$WorkDir/registry/pdks.json" <<'PYEOF'
import json
import os
import pathlib
import re
import sys

pdks_path = pathlib.Path(sys.argv[1])
pdk = os.environ["PDK_NAME"]
tag = os.environ["RELEASE_TAG"]
version = os.environ["VERSION"]
base = f"https://github.com/{os.environ['REGISTRY_REPO']}/releases/download/{tag}"

binary_urls = {}
per_platform = {}
source_url = None
for name in os.environ["ASSETS"].splitlines():
    m = re.fullmatch(rf"{re.escape(pdk)}-(.+)-py(\d+)\.(\d+)\.zip", name)
    if m:
        plat, major, minor = m.groups()
        binary_urls[f"{plat}-py{major}{minor}"] = f"{base}/{name}"
        per_platform.setdefault(plat, []).append((int(major), int(minor), name))
    elif name == f"{pdk}-source.zip":
        source_url = f"{base}/{name}"
# platform-level fallback key points at the newest Python build
for plat, builds in per_platform.items():
    binary_urls[plat] = f"{base}/{max(builds)[2]}"

data = json.loads(pdks_path.read_text(encoding="utf-8"))
entries = data["pdks"] if isinstance(data, dict) else data
updated = 0
for entry in entries:
    if entry.get("name") != pdk:
        continue
    # the registry dialog reads "version"; the installer compares "pdk_version"
    entry["version"] = version
    entry["pdk_version"] = version
    if entry.get("type") == "source" and source_url:
        entry["url"] = source_url
        updated += 1
    elif entry.get("type") == "binary" and binary_urls:
        entry["binary_urls"] = binary_urls
        updated += 1
if updated == 0:
    sys.exit(f"No registry entry named {pdk!r} found in {pdks_path}")
pdks_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(f"Updated {updated} registry entr{'y' if updated == 1 else 'ies'}")
PYEOF

if git -C "$WorkDir/registry" diff --quiet; then
    echo "pdks.json unchanged — nothing to commit"
else
    git -C "$WorkDir/registry" add pdks.json
    git -C "$WorkDir/registry" commit \
        -m "Update ${PdkName} registry entry for ${ReleaseTag}"
    git -C "$WorkDir/registry" push
fi

echo ""
echo "Release published: https://github.com/${RegistryRepo}/releases/tag/${ReleaseTag}"
