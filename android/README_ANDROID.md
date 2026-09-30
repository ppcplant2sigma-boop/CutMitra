# CutMitra — Android app

Kivy-based mobile build of CutMitra. **Same MaxRects nesting engine** as the
desktop app (`core_nest.py` is copied from `../src/` at package time, so the
engine stays identical). 100% offline.

## Mobile v1 scope

- DEMAND / STOCK entry with Add / Edit / Delete, Rotation + Grain switches,
  Material, Price
- Kerf + Trim settings, ▶ START nesting
- Summary + **material-wise sheets used**, per-sheet diagram preview,
  X/Y cut list with sheet browser
- ABOUT tab with version and developer credits
- Not in mobile v1 (desktop has them): PDF / DXF / CSV import, TXT / DXF
  export, project save/load, zoom slider

## Test the UI without a phone

```bash
pip install kivy
python android/smoke_test.py    # drives all 5 tabs, 34 checks
python android/ui_audit.py     # fails if any label or button is clipped
```

`smoke_test.py` boots the real Kivy app on the desktop (a window flashes for
~1 s), then drives every screen: nesting, KPI tiles, running-metre table, sheet
browser, cut list, ABOUT tab, the add/edit popups and both error paths. It is
also the fastest way to catch a broken APK — e.g. a method that shadows
`App.run()` kills the app before any window opens, which is exactly the bug that
shipped in the first `v1.0.3` upload.

`ui_audit.py` re-walks every tab at 360 × 700 and measures each widget: a
`Button` whose text is wider than the button, a `Label` whose texture is taller
than its box, or a widget left with no room all fail the run. This is the
regression guard for the UI complaints ("button label is not proper", "text is
cut off") — keep it green.

## When the app misbehaves on a phone

Android hides `stderr`, so every crash is (a) shown in a popup with the
traceback and (b) appended to `cutmitra_error.log` in the app's private folder.
Screenshot the popup, or pull the log with
`adb shell run-as org.link.cutmitra cat files/cutmitra_error.log`.

## Build the APK (WSL Ubuntu)

```bash
# one-time setup
sudo apt update && sudo apt install -y git zip unzip openjdk-21-jdk \
  python3-pip python3-venv autoconf libtool pkg-config \
  zlib1g-dev libncurses-dev libffi-dev libssl-dev libsqlite3-dev
python3 -m venv ~/bvenv && source ~/bvenv/bin/activate && pip install buildozer

# build (first run downloads SDK+NDK + compiles CPython, ~30-60 min;
# later runs reuse the cache and take ~1-2 min)
bash package_apk.sh
```

`package_apk.sh` copies `../src/core_nest.py` → `./core_nest.py` and
`../assets/logo.png` → `./icon.png`, installs Pillow (launcher icon), drops the
stale helper venv, then runs `buildozer android debug`.

APK lands in `bin/` (e.g. `cutmitra-1.0.3-arm64-v8a-debug.apk` — `arm64-v8a`
covers nearly all modern phones). Building on `/mnt/c`/`/mnt/e` is very slow
(≈2 GB of `.buildozer/` through the 9p filesystem) — for repeat builds copy
`android/`, `src/core_nest.py` and `assets/logo.png` into a Linux-native
directory (e.g. `~/cutmitra-android`) and build there.

## Install on phone

Copy the APK to the phone (USB / WhatsApp / Drive) → tap it → allow
*Install unknown apps* → Install. No internet or account needed afterwards.

Debug builds are signed with the auto-generated debug key. For distribution,
switch to a release build with your own keystore
(`buildozer android release --ks <keystore> --ks-key-alias <alias>`) and keep
the keystore safe — Android refuses updates signed with a different key.

## Known python-for-android issues hit on this setup

1. **`charset_normalizer ... is not a supported wheel on this platform`** —
   p4a resolves pure-Python deps with `--platform` tags and writes the resolved
   wheel URLs into `requirements.txt`, but then runs the final cross-install
   `pip install --target … -r requirements.txt` *without* those tags, so pip
   rejects the pinned `*_android_24_arm64_v8a.whl`. Fixed by patching
   `.buildozer/android/platform/python-for-android/pythonforandroid/build.py`
   (`run_pymodules_install`) to pass
   `--platform=android_<api>_arm64_v8a --platform=android_<api>_aarch64
   --python-version <ver>`. Re-apply after any `buildozer --clean` or p4a
   update; the unpatched file is kept as `build.py.orig`.
2. **`ImportError: cannot import name 'BuildDependencyInstallError'`** —
   p4a re-runs `python -m venv venv` over an existing venv, whose ensurepip
   reinstall mixes old and new pip files. `package_apk.sh` removes
   `.buildozer/android/platform/build-*/build/venv` before each build.
