# Buildozer spec for CutMitra Android app.
# Build on Linux/WSL:  bash package_apk.sh   (or: buildozer android debug)
[app]
title = CutMitra
package.name = cutmitra
package.domain = org.link.cutmitra
source.dir = .
source.include_exts = py,png
version = 1.0.3
requirements = python3,kivy
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/icon.png
android.archs = arm64-v8a
android.api = 34
android.minapi = 24
android.accept_sdk_license = True
android.release_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1
