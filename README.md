# CutMitra

![logo](assets/logo.png)

Offline 2D sheet-cutting (nesting) optimizer for **Windows and Android** — in
the style of Cutting Optimization Pro. Enter the sheets you hold in **STOCK**
and the parts you need in **DEMAND**, press **▶ Start**, and get per-sheet
cutting diagrams with minimum scrap. **100% offline**, no internet or licence
needed. Both builds share one nesting engine (`src/core_nest.py`), so a phone
and a PC give the same layout.

## Features

- **DEMAND / STOCK tables** with direct in-cell editing (double-click, `Tab`
  moves to the next cell, green `+` row adds, `Del` deletes)
- **Per-row Rotation toggle** + **Grain lock** (grain forces no-rotation)
- **Material matching** — demand rows only nest onto same-material stock
- **Kerf (saw-blade width)** and **trim-edge** accounted for in every layout
- **MaxRects Best-Short-Side-Fit nesting engine** — tries 4 sort orders and
  keeps the fewest-sheet result (mixed sizes nest far tighter than row packing)
- **Visual cutting plan** per sheet: piece sizes, hatched waste areas, piece
  labels, cut order index, `Quantity = N` for identical sheets
- **Auto pop-up RM summary** after nesting: total sheets / m² / pcs /
  utilization / waste / cost, separated **material-wise with sheet sizes used**
- **Statistics: 2D tab**: material-wise RM report + per-sheet utilization
- **Imports that auto-fill DEMAND**
  - CSV (`Length,Width,Quantity,Rotation,Grain,Material,Label`)
  - DXF drawings (closed outlines, circles; SHEET/DIM/TEXT/HATCH layers ignored)
  - PDF CAD drawings via PyMuPDF (vector rects merged; scale adjustable)
- **Exports**: printable `.txt` cutting report with X/Y positions, `.dxf` of
  all sheets, project save/load (`.json`)
- **Cost tracking**: price per stock sheet → total + per-material cost

## Quick start

**Option A — run from source** (any OS with Python 3.10+):

```bash
pip install -r requirements.txt   # only pymupdf; skip if you don't need PDF import
python src/cutlist_optimizer.py
```

**Option B — Windows exe** (no Python needed): run `BUILD_EXE.bat`, then launch
`dist/CutMitra.exe`.

**Option C — Android APK**: prebuilt APKs are attached to the
[GitHub releases](https://github.com/ppcplant2sigma-boop/CutMitra/releases);
copy the `.apk` to the phone → tap it → allow *Install unknown apps*. To build
it yourself (Linux or WSL), see [`android/README_ANDROID.md`](android/README_ANDROID.md).

## Typical workflow

1. **STOCK** — double-click the green `+` row, type sheet Length, Width, Qty
   (e.g. `1250 x 2500 x 200`), optional Material + Price.
2. **DEMAND** — type part Length, Width, Qty (e.g. `380 x 955 x 200`).
   Click **Rot** to allow 90° rotation, **Grain** to lock it off.
3. Set **Kerf** (measure 2–3 real cuts) and **Trim edge** in the top bar.
4. Press **▶ Start** → RM summary pop-up → browse each sheet diagram →
   **🖨 Print report** / **DXF** for the shop floor.

See [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) for the full operator guide.

## Project structure

```
link-cutlist-optimizer/
├── src/
│   ├── core_nest.py            # shared MaxRects engine (Windows + Android)
│   └── cutlist_optimizer.py    # Windows app (tkinter, stdlib + pymupdf)
├── android/
│   ├── main.py                 # Kivy app (mobile UI)
│   ├── buildozer.spec          # APK packaging config
│   ├── package_apk.sh          # builds bin/*.apk (Linux / WSL)
│   └── README_ANDROID.md       # APK build + install guide
├── assets/
│   ├── logo.png / logo.ico    # app + exe + Android launcher icon
├── tools/
│   └── make_logo.py           # regenerates the logo (pip install pillow)
├── docs/
│   └── USER_GUIDE.md          # shop-floor operator guide
├── requirements.txt
├── version_info.txt           # exe identity (Company/Product/version)
├── BUILD_EXE.bat              # builds dist/CutMitra.exe
├── CHANGELOG.md
└── README.md
```

## "Windows protected your PC" warning on a new PC

This is normal for **any unsigned** `.exe` (SmartScreen shows it because no
paid code-signing certificate vouches for the publisher — not because the file
is harmful). Our exe carries proper identity metadata (right-click →
Properties → Details shows *Link / CutMitra / 1.0.0*).

- **One-time unblock**: right-click the `.exe` → Properties → tick
  **Unblock** → OK. Or on the blue screen click *More info → Run anyway*.
- **Distribute smartly**: send the exe as a **ZIP** (removes the
  internet "Mark of the Web"), or share via pen drive / LAN.
- **Full removal** of the warning needs a code-signing certificate
  (paid, ~₹8–20k/year from Sectigo/DigiCert) — worth it only if you ship to
  many customers.

## How the nesting works

Parts are sorted large-first and placed with a **MaxRects** free-rectangle
manager using the **Best-Short-Side-Fit** rule (each piece goes where it leaves
the smallest leftover strip, checking every open sheet). The run is repeated
for 4 sort orders (area / max-side / height / width) and the fewest-sheet
result wins. Kerf is reserved as a gap around every placed part; trim shrinks
the usable sheet area on all four sides.

## Notes

- All dimensions are in **millimetres**; areas shown in m² where large.
- `build/`, `dist/`, the PyInstaller `.spec` file, `.buildozer/`, `bin/*.apk`,
  `android/core_nest.py` and `android/icon.png` are build artefacts and are
  **not** committed — rebuild locally or attach the `.exe` / `.apk` to a
  GitHub Release. `android/core_nest.py` and `android/icon.png` are copied from
  `src/core_nest.py` and `assets/logo.png` by `android/package_apk.sh`, so the
  engine has exactly one source in git.
- PDF import needs vector CAD PDFs; scanned/image PDFs have no vectors —
  use DXF for those.

## Credits

Developed by **Er. Durgesh Pandey** and **Er. Arun Shukla**.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
