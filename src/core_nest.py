"""CutMitra shared nesting core (desktop + Android). Pure stdlib;
PDF import needs PyMuPython (lazy import, optional)."""


class SheetPacker:
    """MaxRects Best-Short-Side-Fit nesting — far less scrap than shelf packing.
    Tries several sort orders and keeps the fewest-sheet result."""

    @staticmethod
    def orientations(pw, ph, allow_rot):
        o = [(pw, ph, False)]
        if allow_rot and abs(pw - ph) > 1e-9:
            o.append((ph, pw, True))
        return o

    @staticmethod
    def _prune(free):
        # remove zero-area + contained rects: (x, y, w, h)
        fr = [r for r in free if r[2] > 1e-9 and r[3] > 1e-9]
        out = []
        for i, a in enumerate(fr):
            contained = False
            for j, b in enumerate(fr):
                if i != j and (b[0] <= a[0] + 1e-9 and b[1] <= a[1] + 1e-9 and
                               b[0] + b[2] >= a[0] + a[2] - 1e-9 and
                               b[1] + b[3] >= a[1] + a[3] - 1e-9 and
                               (b[2] * b[3] > a[2] * a[3] + 1e-9)):
                    contained = True
                    break
            if not contained:
                out.append(a)
        return out

    @classmethod
    def _find_best(cls, free, pw, ph, allow):
        """BSSF: min short-side leftover, then long-side, then area waste."""
        best = None  # (short, long, waste, fx, fy, ow, oh, rot, fi)
        for fi, (fx, fy, fw, fh) in enumerate(free):
            for ow, oh, rot in cls.orientations(pw, ph, allow):
                if ow <= fw + 1e-9 and oh <= fh + 1e-9:
                    left_h, left_v = fw - ow, fh - oh
                    short, long = (left_h, left_v) if left_h <= left_v else (left_v, left_h)
                    waste = fw * fh - ow * oh
                    cand = (short, long, waste, fx, fy, ow, oh, rot, fi)
                    if best is None or cand < best:
                        best = cand
        return best

    @classmethod
    def _split(cls, free, px, py, ow, oh, kerf, uw, uh):
        """Split free rects around occupied (px,py,ow+kerf,oh+kerf) clipped to usable."""
        ox2 = min(px + ow + kerf, uw)
        oy2 = min(py + oh + kerf, uh)
        res = []
        for (fx, fy, fw, fh) in free:
            fx2, fy2 = fx + fw, fy + fh
            if ox2 <= fx + 1e-9 or px >= fx2 - 1e-9 or oy2 <= fy + 1e-9 or py >= fy2 - 1e-9:
                res.append((fx, fy, fw, fh))  # no overlap
                continue
            # left
            if px > fx + 1e-9:
                res.append((fx, fy, px - fx, fh))
            # right
            if ox2 < fx2 - 1e-9:
                res.append((ox2, fy, fx2 - ox2, fh))
            # bottom
            if py > fy + 1e-9:
                res.append((fx, fy, fw, py - fy))
            # top
            if oy2 < fy2 - 1e-9:
                res.append((fx, oy2, fw, fy2 - oy2))
        return cls._prune(res)

    @classmethod
    def _pack_once(cls, pieces, demands, stocks, kerf, trim):
        def mat_match(dm, sm):
            dm = (dm or "").strip().lower()
            sm = (sm or "").strip().lower()
            if not dm or not sm:
                return True
            return dm == sm

        def usable(s):
            return float(s["L"]) - 2 * trim, float(s["W"]) - 2 * trim

        def fits_stock(s, pw, ph, allow):
            uw, uh = usable(s)
            if uw <= 0 or uh <= 0:
                return False
            return any(ow <= uw + 1e-9 and oh <= uh + 1e-9
                       for ow, oh, _ in cls.orientations(pw, ph, allow))

        stock_used = [0] * len(stocks)
        sheets = []
        for pc in pieces:
            d = demands[pc["di"]]
            # best global placement across open sheets (least waste)
            best_sh, best_spot = None, None
            for sh in sheets:
                s = stocks[sh["stock_idx"]]
                if not mat_match(d.get("material", ""), s.get("material", "")):
                    continue
                uw, uh = usable(s)
                spot = cls._find_best(sh["free"], pc["L"], pc["W"], pc["rot"])
                if spot and (best_spot is None or spot < best_spot):
                    best_spot, best_sh = spot, sh
            if best_sh is not None:
                (_, _, _, fx, fy, ow, oh, rot, _fi) = best_spot
                s = stocks[best_sh["stock_idx"]]
                uw, uh = usable(s)
                best_sh["free"] = cls._split(best_sh["free"], fx, fy, ow, oh, kerf, uw, uh)
                best_sh["places"].append((fx + trim, fy + trim, ow, oh, rot, pc["di"]))
                continue
            # open new sheet — smallest fitting stock with qty + material
            best_i, best_area = -1, None
            for i, s in enumerate(stocks):
                if s["qty"] > 0 and stock_used[i] >= s["qty"]:
                    continue
                if not mat_match(d.get("material", ""), s.get("material", "")):
                    continue
                if not fits_stock(s, pc["L"], pc["W"], pc["rot"]):
                    continue
                area = float(s["L"]) * float(s["W"])
                if best_area is None or area < best_area:
                    best_area, best_i = area, i
            if best_i < 0:
                return None, (f"Cannot place {d['L']:g}x{d['W']:g} (mat='{d.get('material','')}'). "
                              f"No stock left / mismatch / too big for trim={trim:g}+kerf={kerf:g}.")
            stock_used[best_i] += 1
            s = stocks[best_i]
            uw, uh = usable(s)
            sh = {"stock_idx": best_i, "sw": float(s["L"]), "sh": float(s["W"]),
                  "free": [(0.0, 0.0, uw, uh)], "places": []}
            sheets.append(sh)
            spot = cls._find_best(sh["free"], pc["L"], pc["W"], pc["rot"])
            if spot is None:
                return None, "Packing error on fresh sheet."
            (_, _, _, fx, fy, ow, oh, rot, _fi) = spot
            sh["free"] = cls._split(sh["free"], fx, fy, ow, oh, kerf, uw, uh)
            sh["places"].append((fx + trim, fy + trim, ow, oh, rot, pc["di"]))
        return sheets, {"stock_used": stock_used}

    @classmethod
    def optimize(cls, demands, stocks, kerf=0.0, trim=0.0):
        base = []
        for di, d in enumerate(demands):
            allow = bool(d.get("rot", True)) and not bool(d.get("grain", False))
            for _ in range(int(d["qty"])):
                base.append({"L": float(d["L"]), "W": float(d["W"]),
                             "rot": allow, "di": di})
        if not base:
            return [], {"stock_used": [0] * len(stocks)}
        orders = [
            ("area", lambda a: a["L"] * a["W"]),
            ("maxside", lambda a: max(a["L"], a["W"])),
            ("height", lambda a: a["W"]),
            ("width", lambda a: a["L"]),
        ]
        if len(base) > 1200:  # keep UI fast on huge jobs: single best order
            orders = orders[:1]
        best, best_info, best_key = None, None, None
        for _name, key in orders:
            pieces = sorted(base, key=key, reverse=True)
            res, info = cls._pack_once(pieces, demands, stocks, kerf, trim)
            if res is None:
                continue
            used_area = sum(d["L"] * d["W"] * d["qty"] for d in demands)
            sheet_area = sum(sh["sw"] * sh["sh"] for sh in res)
            k = (len(res), -(used_area / sheet_area if sheet_area else 0))
            if best_key is None or k < best_key:
                best, best_info, best_key = res, info, k
        if best is None:
            # return first error for message
            pieces = sorted(base, key=lambda a: a["L"] * a["W"], reverse=True)
            return cls._pack_once(pieces, demands, stocks, kerf, trim)
        return best, best_info


def write_dxf(path, sheets, demands):
    """Minimal R12 DXF with sheet outline + parts as closed polylines. No deps."""
    with open(path, "w", encoding="utf-8") as f:
        f.write("0\nSECTION\n2\nENTITIES\n")
        dy = 0.0
        for sh in sheets:
            sw, shh = sh["sw"], sh["sh"]
            # sheet outline
            for (x1, y1, x2, y2) in [(0, dy, sw, dy), (sw, dy, sw, dy + shh),
                                     (sw, dy + shh, 0, dy + shh), (0, dy + shh, 0, dy)]:
                f.write(f"0\nLINE\n8\nSHEET\n10\n{x1:.2f}\n20\n{y1:.2f}\n11\n{x2:.2f}\n21\n{y2:.2f}\n")
            for (x, y, w, h, _rot, _ref) in sh["places"]:
                pts = [(x, dy + y), (x + w, dy + y), (x + w, dy + y + h), (x, dy + y + h), (x, dy + y)]
                for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                    f.write(f"0\nLINE\n8\nPARTS\n10\n{x1:.2f}\n20\n{y1:.2f}\n11\n{x2:.2f}\n21\n{y2:.2f}\n")
            dy += shh + max(sw, shh) * 0.1 + 100
        f.write("0\nENDSEC\n0\nEOF\n")


SKIP_LAYERS = ("SHEET", "BORDER", "TITLE", "DIM", "TEXT", "HATCH",
               "DEFPOINTS", "VIEWPORT", "FRAME", "ANNOT")


def _merge_sizes(sizes, tol=0.5):
    """Merge near-identical sizes into (L, W, qty). Normalizes L >= W."""
    out = []
    for L, W in sizes:
        try:
            L, W = round(float(L), 2), round(float(W), 2)
        except Exception:
            continue
        if L <= 0 or W <= 0:
            continue
        a, b = (L, W) if L >= W else (W, L)
        for o in out:
            if abs(o[0] - a) <= tol and abs(o[1] - b) <= tol:
                o[2] += 1
                break
        else:
            out.append([a, b, 1])
    return out


def _layer_ok(name):
    u = (name or "").upper()
    return not any(k in u for k in SKIP_LAYERS)


def parse_dxf_parts(path, scale=1.0, min_dim=10.0, tol=1.0):
    """Read a DXF file and return [(L, W, qty)] part sizes.

    Closed polylines / circles become parts directly; LINE soup is
    clustered by shared endpoints (sheet outlines on SHEET-type layers
    and DIM/TEXT/HATCH layers are ignored). Pure stdlib, offline.
    """
    with open(path, encoding="utf-8", errors="ignore") as f:
        raw = f.read().splitlines()
    pairs = [(raw[k].strip(), raw[k + 1] if k + 1 < len(raw) else "")
             for k in range(0, len(raw) - 1, 2)]
    parts, soup = [], []
    i, n = 0, len(pairs)
    while i < n:
        code, val = pairs[i]
        if code != "0":
            i += 1
            continue
        typ = val.strip().upper()
        if typ == "LINE":
            ent = {}
            i += 1
            while i < n and pairs[i][0] != "0":
                ent[pairs[i][0]] = pairs[i][1]
                i += 1
            if _layer_ok(ent.get("8", "")):
                try:
                    soup.append((float(ent["10"]) * scale, float(ent["20"]) * scale,
                                 float(ent["11"]) * scale, float(ent["21"]) * scale))
                except Exception:
                    pass
            continue
        if typ == "LWPOLYLINE":
            layer, verts, closed, vx = "", [], False, None
            i += 1
            while i < n and pairs[i][0] != "0":
                c, v = pairs[i]
                if c == "8":
                    layer = v
                elif c == "70":
                    try:
                        closed = bool(int(float(v)) & 1)
                    except Exception:
                        pass
                elif c == "10":
                    try:
                        vx = float(v) * scale
                    except Exception:
                        vx = None
                elif c == "20" and vx is not None:
                    try:
                        verts.append((vx, float(v) * scale))
                    except Exception:
                        pass
                    vx = None
                i += 1
            if _layer_ok(layer):
                if closed and len(verts) >= 3:
                    xs = [p[0] for p in verts]
                    ys = [p[1] for p in verts]
                    parts.append((max(xs) - min(xs), max(ys) - min(ys)))
                else:
                    soup += [(a[0], a[1], b[0], b[1]) for a, b in zip(verts, verts[1:])]
            continue
        if typ == "POLYLINE":
            layer, closed = "", False
            i += 1
            while i < n and pairs[i][0] != "0":
                if pairs[i][0] == "8":
                    layer = pairs[i][1]
                elif pairs[i][0] == "70":
                    try:
                        closed = bool(int(float(pairs[i][1])) & 1)
                    except Exception:
                        pass
                i += 1
            verts = []
            while i < n:
                c2, v2 = pairs[i]
                if c2 == "0" and v2.strip().upper() == "VERTEX":
                    vx = vy = None
                    i += 1
                    while i < n and pairs[i][0] != "0":
                        if pairs[i][0] == "10":
                            try:
                                vx = float(pairs[i][1]) * scale
                            except Exception:
                                pass
                        elif pairs[i][0] == "20":
                            try:
                                vy = float(pairs[i][1]) * scale
                            except Exception:
                                pass
                        i += 1
                    if vx is not None and vy is not None:
                        verts.append((vx, vy))
                    continue
                break
            if _layer_ok(layer):
                if closed and len(verts) >= 3:
                    xs = [p[0] for p in verts]
                    ys = [p[1] for p in verts]
                    parts.append((max(xs) - min(xs), max(ys) - min(ys)))
                else:
                    soup += [(a[0], a[1], b[0], b[1]) for a, b in zip(verts, verts[1:])]
            continue
        if typ == "CIRCLE":
            ent = {}
            i += 1
            while i < n and pairs[i][0] != "0":
                ent[pairs[i][0]] = pairs[i][1]
                i += 1
            if _layer_ok(ent.get("8", "")):
                try:
                    r = float(ent.get("40", 0)) * scale
                    if r > 0:
                        parts.append((2 * r, 2 * r))
                except Exception:
                    pass
            continue
        i += 1
    # cluster LINE soup by shared endpoints -> one bbox part per loop
    pts = []

    def pid(x, y):
        for j, (px, py) in enumerate(pts):
            if abs(px - x) <= tol and abs(py - y) <= tol:
                return j
        pts.append((x, y))
        return len(pts) - 1

    parent = {}

    def find(a):
        while parent.get(a, a) != a:
            a = parent[a]
        return a

    for (x1, y1, x2, y2) in soup:
        a, b = pid(x1, y1), pid(x2, y2)
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    comps = {}
    for (x1, y1, x2, y2) in soup:
        comps.setdefault(find(pid(x1, y1)), []).append((x1, y1, x2, y2))
    for segs in comps.values():
        xs, ys = [], []
        for x1, y1, x2, y2 in segs:
            xs += [x1, x2]
            ys += [y1, y2]
        parts.append((max(xs) - min(xs), max(ys) - min(ys)))
    parts = [p for p in parts if p[0] >= min_dim and p[1] >= min_dim]
    return _merge_sizes(parts)


def parse_pdf_parts(path, scale=1.0, min_dim=10.0, tol=1.0):
    """Read vector rectangles from a PDF (CAD export) and return [(L, W, qty)].

    Uses PyMuPDF drawings; overlapping/touching rects (part outline +
    its inner lines) are merged into one bbox. Scanned/image PDFs have
    no vectors — use DXF for those.
    """
    try:
        import pymupdf as fitz  # PyMuPDF, offline
    except ImportError:
        import fitz  # older PyMuPDF alias
    doc = fitz.open(path)
    rects = []
    for page in doc:
        try:
            draws = page.get_drawings()
        except Exception:
            draws = []
        for d in draws:
            try:
                r = d["rect"]
            except Exception:
                continue
            w, h = r.width * scale, r.height * scale
            if w >= min_dim and h >= min_dim:
                rects.append((r.x0 * scale, r.y0 * scale, r.x1 * scale, r.y1 * scale))
    doc.close()
    parent = list(range(len(rects)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def touch(a, b):
        return not (a[2] < b[0] - tol or b[2] < a[0] - tol or
                    a[3] < b[1] - tol or b[3] < a[1] - tol)

    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            if touch(rects[i], rects[j]):
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[rj] = ri
    groups = {}
    for i, r in enumerate(rects):
        groups.setdefault(find(i), []).append(r)
    parts = []
    for rs in groups.values():
        parts.append((max(r[2] for r in rs) - min(r[0] for r in rs),
                      max(r[3] for r in rs) - min(r[1] for r in rs)))
    return _merge_sizes(parts)


def summarize_nesting(sheets, demands, stocks, stock_used=None):
    """Pure helper shared by desktop + mobile. Returns (total, blocks) where
    blocks are per-material sections with stock sizes used."""
    groups = {}
    for sh in sheets:
        s = stocks[sh["stock_idx"]]
        key = (s.get("material", "") or "").strip() or "— Unspecified —"
        g = groups.setdefault(key, {"sheets": 0, "sheet_area": 0.0,
                                    "part_area": 0.0, "cost": 0.0, "pcs": 0})
        g["sheets"] += 1
        g["sheet_area"] += sh["sw"] * sh["sh"]
        g["part_area"] += sum(w * h for (_, _, w, h, _, _) in sh["places"])
        g["pcs"] += len(sh["places"])
        try:
            g["cost"] += float(s.get("price", 0) or 0)
        except Exception:
            pass
    used = list(stock_used or [0] * len(stocks))
    blocks = []
    for mat in sorted(groups):
        g = groups[mat]
        u = g["part_area"] / g["sheet_area"] * 100 if g["sheet_area"] else 0
        sizes = []
        for i, s in enumerate(stocks):
            sm = (s.get("material", "") or "").strip() or "— Unspecified —"
            n = used[i] if i < len(used) else 0
            if n > 0 and sm == mat:
                sizes.append({"size": f"{s['L']:g} x {s['W']:g}", "qty": n,
                              "sqm": s["L"] * s["W"] * n / 1e6})
        blocks.append({"material": mat, "sheets": g["sheets"],
                       "rm_sqm": g["sheet_area"] / 1e6, "pcs": g["pcs"],
                       "util": u, "waste": 100 - u, "cost": g["cost"], "sizes": sizes})
    tot_area = sum(sh["sw"] * sh["sh"] for sh in sheets)
    tot_part = sum(d["L"] * d["W"] * d["qty"] for d in demands)
    tu = tot_part / tot_area * 100 if tot_area else 0
    total = {"sheets": len(sheets), "rm_sqm": tot_area / 1e6,
             "pcs": sum(d["qty"] for d in demands),
             "util": tu, "waste": 100 - tu,
             "cost": sum(b["cost"] for b in blocks)}
    return total, blocks
