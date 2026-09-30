# Changelog

## v1.0.3 — 2026-09-28

- **Running metre (perimeter) of the demand**: `2 x (L + W) x qty` per size, in
  the mobile RESULT tab as a KPI + per-size table (size / pcs / m-per-pc /
  running m) and in the desktop RM report and Statistics view
- **RESULT diagram redrawn**: every demand panel gets an outline (the first cut
  stays red, as on desktop), the scrap area is hatched 45° and the sheet got
  ~2x bigger; piece sizes are printed where they fit
- **UI rebuilt**: app bar with version, white cards on a soft background,
  captioned panels, KPI tiles, consistent type scale, proper ASCII button labels
  (Kivy drops ▶ ◀ on some Android fonts) and no clipped text — `android/ui_audit.py`
  fails the build if any label or button does not fit its box
- **Fix — Android app opened to a black screen**: `CutMitraApp.start_nesting`
  was defined as `run()`, shadowing Kivy's `App.run()`, so the app built no
  window and died on `self.kerf_in` (no such attribute). Renamed to
  `start_nesting()`; added `android/smoke_test.py` (22 UI checks) so the whole
  app is exercised without a phone
- Crashes are no longer silent on Android: traceback popup + `cutmitra_error.log`
  in the app's private folder
- **New Android app** (`android/`, Kivy) with the same MaxRects engine as the
  desktop: DEMAND / STOCK entry, Rotation + Grain, Material, Price, kerf/trim,
  material-wise summary, per-sheet diagram + X/Y cut list, ABOUT tab with
  credits. Launcher icon reuses `assets/logo.png`. Build via
  `android/package_apk.sh` (Linux / WSL) → `bin/cutmitra-1.0.3-arm64-v8a-debug.apk`
- Engine extracted to `src/core_nest.py` so Windows and Android provably share
  one nesting implementation (same input → same 29-sheet / 80.09% result)
- Developer credits: **Er. Durgesh Pandey**, **Er. Arun Shukla** — new
  Help → About dialog in the app, credit footer on printed reports,
  Credits section in README / User Guide, and an ABOUT tab in the Android app

## v1.0.2 — 2026-09-28

- Renamed app **Link Cutlist Optimizer → CutMitra** everywhere (window title,
  exe name, metadata, docs); logo redrawn as a "C" sheet mark
- Product = CutMitra 1.0.0 in exe properties

## v1.0.1 — 2026-09-28

- New logo (`assets/logo.png`/`.ico`, generator in `tools/make_logo.py`) —
  shown in the window title bar, taskbar, and embedded as the exe icon
- Exe now carries version metadata (`version_info.txt`): Company = Link,
  Product = Link Cutlist Optimizer 1.0.0 — no more "unknown program" look in
  Properties / SmartScreen dialog

## v1.0.0 — 2026-09-28 (initial release)

- Pro-style DEMAND / STOCK tables with direct in-cell editing, Tab navigation,
  green `+` add-row, Del-key delete
- Per-row Rotation toggle, Grain lock, Material matching, piece Labels
- Kerf + trim-edge aware nesting
- MaxRects Best-Short-Side-Fit engine with 4-pass sort-order search
- Per-sheet cutting diagram: sizes with backing labels, hatched true-waste
  areas, cut index, Quantity grouping, zoom slider
- Auto RM-summary pop-up after nesting + material-wise report in
  Statistics: 2D (sheets used per material with stock sizes)
- CSV / DXF / PDF-drawing import that auto-fills DEMAND
- TXT cutting report with X/Y positions, DXF export, JSON save/load
- Stock price → total + per-material cost tracking
- Professional navy/steel theme, alternating table rows
