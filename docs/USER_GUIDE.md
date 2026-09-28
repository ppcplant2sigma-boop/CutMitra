# CutMitra — Operator Guide

*Developed by Er. Durgesh Pandey and Er. Arun Shukla.*

## 1. Getting started

- **With Python**: `pip install -r requirements.txt`, then
  `python src/cutlist_optimizer.py`.
- **Without Python**: run `BUILD_EXE.bat` once, then open
  `dist/CutMitra.exe`. No internet needed afterwards.

## 2. STOCK table (sheets you hold)

Double-click the green **`+ type here…`** row and type directly in the cell.
`Tab` jumps to the next cell, `Enter` saves, `Esc` cancels, `Del` deletes a row.

| Column   | Meaning                              | Example        |
|----------|--------------------------------------|----------------|
| Length   | Sheet size, horizontal (mm)          | 1250           |
| Width    | Sheet size, vertical (mm)            | 2500           |
| Qty      | How many sheets of this size you have| 200            |
| Mat      | Material code (must match DEMAND)    | MS / SS / blank|
| Price    | Cost per sheet (₹) for cost tracking | 5000           |

Leave **Mat** blank on both sides to allow any-to-any nesting.

## 3. DEMAND table (parts to cut)

| Column | Meaning                                              |
|--------|------------------------------------------------------|
| Length / Width / Qty | Part size in mm and quantity needed     |
| Rot    | **Click to toggle.** Y = part may rotate 90° to fit  |
| Grain  | **Click to toggle.** Y = grain direction fixed → rotation forced OFF |
| Mat    | Must equal the STOCK material you want it cut from   |
| Label  | Printed on the diagram and report (e.g. `SHELF-A`)   |

**Rule of thumb:** keep Rot = Y unless grain truly matters — rotation is the
single biggest scrap saver.

## 4. Top bar settings

- **Kerf saw (mm)** — width the blade eats per cut. Measure 2–3 real cuts and
  enter the value (typically 2–4 mm). Fake 0 looks better on screen but parts
  come out short on the shop floor.
- **Trim edge (mm)** — damaged/uneven border removed from all four sides.
- **Zoom slider** — enlarge the cutting diagram.

## 5. Running the nesting (▶ Start)

1. Press **▶ Start**.
2. A **summary pop-up** appears: total sheets, RM m², pieces, utilization %,
   waste %, cost — separated **per material with the exact sheet sizes used**.
3. Browse sheets with **◀ Prev / Next** or the sheet dropdown.
4. Open **Statistics: 2D** (last item in the dropdown) for the material-wise
   RM report and every sheet's utilization.

## 6. Reading the cutting diagram

- Each coloured box = one part; the number on top = placed width, on the
  side = placed height (mm).
- **Hatched areas** = real waste (offcuts).
- Red-bordered box = first cut of that sheet.
- `Quantity = N` on the right = how many sheets share this exact layout.
- Ticks: *Show size of the pieces / wastes / piece label / index of cutting*.
- The table under the diagram lists every piece with its **X/Y position** —
  measured in mm from the sheet's top-left corner (after trim).

## 7. Importing sizes automatically

**File → Read DXF drawing → DEMAND** — closed outlines and circles become
parts; connected line loops are detected; layers containing SHEET, BORDER,
DIM, TEXT, HATCH are ignored (so title blocks and dimensions don't become
parts).

**File → Read PDF drawing → DEMAND** — vector rectangles are extracted and
merged. In the dialog set:

- **Scale** — drawing-unit → mm (`1.0` for mm CAD exports, `0.3528` for
  point-based PDFs).
- **Ignore parts smaller than** — drops arrows, text boxes, hatch fragments
  (default 10 mm).
- **Material / Rotation** applied to all imported parts.

Always verify imported sizes in the table before pressing Start. Scanned or
photo PDFs contain no vectors — use DXF for those.

**File → Import DEMAND/ STOCK csv** — headers
`Length,Width,Quantity,Rotation,Grain,Material,Label` (demand) and
`Length,Width,Quantity,Material,Label,Price` (stock).

## 8. Outputs for the shop floor

- **🖨 Print report** (`.txt`) — totals, material-wise RM with sheet sizes,
  every sheet with each part's X/Y and rotation flag. Print as-is.
- **DXF** — all sheets + parts as lines, ready for CAD/CAM.
- **File → Save JSON** — reload the whole job later.

## 9. Tips for minimum scrap

1. Rotation ON, Grain OFF unless required.
2. Enter the REAL kerf.
3. List every stock size you actually hold — the optimizer picks the smallest
   sheet each part fits.
4. Use one Material code per grade/thickness so grades never mix.
5. Compare runs: toggle one rotation setting and re-run; keep the lower-waste
   report.
