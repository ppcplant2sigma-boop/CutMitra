#!/bin/bash
# Build the CutMitra APK (run inside WSL Ubuntu / Linux).
# First-time only setup:
#   sudo apt update && sudo apt install -y git zip unzip openjdk-21-jdk \
#     python3-pip python3-venv autoconf libtool pkg-config \
#     zlib1g-dev libncurses-dev libffi-dev libssl-dev libsqlite3-dev
#   python3 -m venv ~/bvenv && source ~/bvenv/bin/activate && pip install buildozer
# Then:  bash package_apk.sh
#
# Slow disk? Copy the android/ + src/core_nest.py + assets/logo.png into a
# Linux-native dir (e.g. ~/cutmitra-android) and run this script there.
set -e
cd "$(dirname "$0")"

# Buildozer writes ~2 GB of .buildozer/ next to this script; keep it out of git.

# Single source of truth for the engine and the logo lives in the repo root.
cp ../src/core_nest.py ./core_nest.py
cp ../assets/logo.png ./icon.png

# Pillow is only needed to rasterise the launcher icon into mipmaps.
python -c "import PIL" 2>/dev/null || pip install --quiet Pillow

# python-for-android rebuilds its helper venv with ensurepip on every run; if a
# previous run upgraded pip inside it, the leftover files make the next run die
# with "cannot import name 'BuildDependencyInstallError'". Drop the venv first.
rm -rf .buildozer/android/platform/build-*/build/venv

buildozer android debug
ls -la bin/*.apk
