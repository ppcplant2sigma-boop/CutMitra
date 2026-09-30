"""CutMitra Android app (Kivy) — offline 2D sheet nesting.

Same MaxRects engine as the desktop app (core_nest.py, copied next to this
file at package time). 100% offline. Mobile v1: manual size entry +
diagrams + material-wise summary (no file import/export yet).
"""
import math
import os
import sys
import traceback

from kivy.app import App
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Line, Mesh, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.switch import Switch
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

import core_nest

VERSION = "1.0.3"
DEVELOPERS = ("Er. Durgesh Pandey", "Er. Arun Shukla")

# ---------------------------------------------------------------- design system
BG = (0.957, 0.965, 0.976, 1)       # app background, slightly cool grey
CARD = (1, 1, 1, 1)
INK = (0.07, 0.09, 0.13, 1)         # headings
BODY = (0.20, 0.23, 0.29, 1)        # normal text
MUTED = (0.45, 0.49, 0.55, 1)       # captions
BORDER = (0.87, 0.89, 0.92, 1)
NAVY = (0.06, 0.10, 0.20, 1)        # app bar
BLUE = (0.11, 0.33, 0.72, 1)        # primary action
BLUE_D = (0.08, 0.24, 0.55, 1)
GREEN = (0.05, 0.44, 0.26, 1)
RED = (0.66, 0.13, 0.13, 1)
AMBER = (0.72, 0.44, 0.02, 1)
STEEL = (0.85, 0.88, 0.95, 1)
SCRAP = (0.95, 0.95, 0.95, 1)       # sheet background on the diagram
HATCH = (0.60, 0.60, 0.60, 0.85)    # scrap hatch lines
PIECE_EDGE = (0.20, 0.20, 0.20, 1)  # every demand panel gets an outline
CUT_START = (0.69, 0.0, 0.13, 1)    # first cut, same red as the desktop app
PALETTE = [(1, 1, 1, 1), (1, 0.85, 0.85, 1), (0.85, 0.92, 1, 1),
           (0.85, 0.95, 0.85, 1), (1, 0.95, 0.77, 1), (0.91, 0.85, 1, 1),
           (0.88, 0.97, 0.98, 1)]

FS_H1 = 19        # app bar title
FS_H2 = 14.5      # card title
FS_BODY = 13      # normal text, inputs
FS_SMALL = 12     # table rows, hints
FS_CAP = 10.5     # captions, tile labels
FS_TILE = 17      # KPI value


def _num(s, name, allow_zero=False):
    v = float((s or "").strip())
    if (v < 0) or (not allow_zero and v <= 0):
        raise ValueError(f"{name} must be {'>= 0' if allow_zero else '> 0'}")
    return v


def _int(s, name):
    v = int(float((s or "").strip()))
    if v <= 0:
        raise ValueError(f"{name} must be > 0")
    return v


def btn(text, bg=None, fg=(1, 1, 1, 1), fs=14.5, h=dp(44), bold=True, **kw):
    """Button whose label always renders: explicit font size, real newlines
    instead of symbols (Kivy's default font drops ▶ ◀ on some Android builds,
    and long single-line text gets clipped because Button does not wrap)."""
    b = Button(text=text, font_size=dp(fs), bold=bold, size_hint_y=None,
               height=h, color=fg, **kw)
    if bg is not None:
        b.background_color = bg
    return b


def lbl(text, fs=13, color=BODY, **kw):
    return Label(text=text, font_size=dp(fs), color=color, **kw)


class Card(BoxLayout):
    """White panel with a hairline border, rounded corners and a caption
    title. Everything on screen lives inside one of these."""

    def __init__(self, title=None, **kw):
        kw.setdefault("orientation", "vertical")
        kw.setdefault("padding", dp(10))
        kw.setdefault("spacing", dp(6))
        super().__init__(**kw)
        self._border = None
        with self.canvas.before:
            Color(*CARD)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(*BORDER)
            self._border = Line(width=1)
        if title:
            self.add_widget(lbl(title.upper(), fs=FS_CAP, color=MUTED, bold=True,
                                size_hint_y=None, height=dp(16), halign="left",
                                valign="middle"))
        self.bind(pos=self._deco, size=self._deco)

    def _deco(self, *_a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border.rounded_rectangle = (self.x + 0.5, self.y + 0.5,
                                          max(1, self.width - 1),
                                          max(1, self.height - 1), dp(8))


class Tile(Card):
    """Small KPI tile: caption above, big number below."""

    def __init__(self, caption, value="—", color=INK, **kw):
        kw.setdefault("padding", dp(8))
        kw.setdefault("spacing", dp(0))
        super().__init__(**kw)
        self.add_widget(lbl(caption.upper(), fs=FS_CAP, color=MUTED, bold=True,
                            size_hint_y=None, height=dp(14), halign="left",
                            valign="middle"))
        self.value_lbl = lbl(value, fs=FS_TILE, color=color, bold=True,
                             size_hint_y=None, halign="left", valign="middle")
        self.add_widget(self.value_lbl)

    def set(self, value, color=None):
        self.value_lbl.text = value
        if color is not None:
            self.value_lbl.color = color


def err_popup(msg):
    box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
    box.add_widget(lbl(msg, fs=12))
    ok = btn("OK", bg=BLUE, h=dp(44))
    box.add_widget(ok)
    pop = Popup(title="CutMitra", content=box, size_hint=(0.88, 0.42),
                separator_color=BLUE)
    ok.bind(on_release=pop.dismiss)
    pop.open()


def save_error(text):
    """Android hides stderr, so keep a copy of every crash on disk."""
    try:
        path = os.path.join(os.path.expanduser("~"), "cutmitra_error.log")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text + "\n" + "-" * 50 + "\n")
    except Exception:
        pass


def crash_guard(fn):
    """Report a failure on screen instead of dying silently."""
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception:
            tb = traceback.format_exc()
            save_error(tb)
            try:
                err_popup("Something went wrong:\n\n" + tb[-700:])
            except Exception:
                pass
            raise
    wrapper.__name__ = fn.__name__
    return wrapper


SCRAP = (0.95, 0.95, 0.95, 1)          # sheet background on the diagram
HATCH = (0.60, 0.60, 0.60, 0.85)       # scrap hatch lines
PIECE_EDGE = (0.20, 0.20, 0.20, 1)     # every demand panel gets an outline
CUT_START = (0.69, 0.0, 0.13, 1)       # first cut, same red as the desktop app

_TEXT_CACHE = {}


def hatch_segments(x1, y1, x2, y2, step, width):
    """45-degree segments that fill a scrap rectangle (like the desktop plan)."""
    w, h = x2 - x1, y2 - y1
    if w <= 0 or h <= 0:
        return []
    out = []
    off = -h
    while off < w:
        t0 = max(0.0, -off)
        t1 = min(h, w - off)
        if t1 - t0 > 0.5:
            out += [x1 + off + t0, y1 + t0, x1 + off + t1, y1 + t1, width]
        off += step
    return out


def draw_quads(canvas, segs, color):
    """One Mesh of thin quads — far cheaper than a Line per hatch stroke."""
    verts = []
    for i in range(0, len(segs), 5):
        ax, ay, bx, by, wd = segs[i:i + 5]
        dx, dy = bx - ax, by - ay
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln * wd / 2.0, dx / ln * wd / 2.0
        verts += [ax + nx, ay + ny, bx + nx, by + ny,
                  ax - nx, ay - ny, bx - nx, by - ny]
    if verts:
        Color(*color)
        Mesh(vertices=verts, indices=list(range(len(verts))), mode="triangles")


def piece_label(txt, font_px):
    key = (txt, int(font_px))
    tex = _TEXT_CACHE.get(key)
    if tex is None:
        cl = CoreLabel(text=txt, font_size=int(font_px), color=(0.12, 0.12, 0.12, 1))
        cl.refresh()
        tex = cl.texture
        _TEXT_CACHE[key] = tex
    return tex


class RowList(BoxLayout):
    """Scrollable list of demand/stock rows with Edit + Del buttons."""

    def __init__(self, app, kind, **kw):
        super().__init__(orientation="vertical", **kw)
        self.app = app
        self.kind = kind  # "demand" or "stock"
        head = Card(orientation="horizontal", padding=(dp(10), dp(6), dp(8), dp(6)),
                    spacing=dp(6), size_hint_y=None, height=dp(48))
        head.add_widget(lbl(("DEMAND" if kind == "demand" else "STOCK") + " ROWS",
                            fs=FS_CAP, color=MUTED, bold=True,
                            halign="left", valign="middle"))
        add = btn("ADD", bg=GREEN, fs=FS_CAP, h=dp(32),
                  size_hint_x=None, width=dp(70))
        add.bind(on_release=lambda _e: app.open_editor(kind, -1))
        clr = btn("CLEAR", bg=(0.60, 0.64, 0.70, 1), fs=FS_CAP, h=dp(32),
                  size_hint_x=None, width=dp(70))
        clr.bind(on_release=lambda _e: app.clear_list(kind))
        head.add_widget(add)
        head.add_widget(clr)
        self.add_widget(head)
        self.scroll = ScrollView()
        self.grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None,
                               padding=(0, dp(2), 0, dp(8)))
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.scroll.add_widget(self.grid)
        self.add_widget(self.scroll)

    def refresh(self):
        self.grid.clear_widgets()
        items = self.app.demands if self.kind == "demand" else self.app.stocks
        if not items:
            empty = Card(padding=dp(10), size_hint_y=None, height=dp(58))
            empty.add_widget(lbl("No rows yet — tap ADD to enter "
                                 + ("demand sizes." if self.kind == "demand"
                                    else "stock sheets."),
                                 fs=FS_SMALL, color=MUTED, halign="left",
                                 valign="middle"))
            self.grid.add_widget(empty)
            return
        for i, it in enumerate(items):
            if self.kind == "demand":
                head = f"{it['L']:g} x {it['W']:g} mm"
                flags = ("ROT " if it.get("rot") else "") + \
                        ("GRAIN" if it.get("grain") else "")
                tail = f"x{it['qty']} pcs" + (f"  ·  {it['material']}" if it.get("material") else "")
                if it.get("label"):
                    tail += f"  ·  {it['label']}"
                t = f"{head}\n{tail}{('  ·  ' + flags) if flags else ''}"
            else:
                t = (f"{it['L']:g} x {it['W']:g} mm\n"
                     f"x{it['qty']} pcs  ·  {it.get('material', '')}"
                     f"  ·  Rs.{it.get('price', 0):g}")
            row = Card(orientation="horizontal", padding=(dp(8), dp(8), dp(6), dp(6)),
                       spacing=dp(4), size_hint_y=None, height=dp(62))
            row.add_widget(lbl(t, fs=FS_SMALL, halign="left", valign="middle"))
            eb = btn("EDIT", bg=BLUE, fs=FS_CAP, h=dp(34), size_hint_x=None,
                     width=dp(58))
            eb.bind(on_release=lambda _e, j=i: self.app.open_editor(self.kind, j))
            db = btn("DEL", bg=RED, fs=FS_CAP, h=dp(34), size_hint_x=None,
                     width=dp(50))
            db.bind(on_release=lambda _e, j=i: self.app.delete_row(self.kind, j))
            row.add_widget(eb)
            row.add_widget(db)
            self.grid.add_widget(row)


class SheetPreview(Widget):
    """Cutting diagram of one sheet: outlined pieces + hatched scrap areas."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.sheet = None
        self.trim = 0.0
        self.bind(size=self._draw, pos=self._draw)

    def show(self, sheet, trim=0.0):
        self.sheet = sheet
        self.trim = trim
        self._draw()

    def _draw(self, * _a):
        self.canvas.clear()
        if not self.sheet:
            return
        sw, sh = self.sheet["sw"], self.sheet["sh"]
        pad = dp(3)
        sc = min((self.width - 2 * pad) / sw, (self.height - 2 * pad) / sh)
        if sc <= 0:
            return
        ox = self.x + (self.width - sw * sc) / 2
        oy = self.y + (self.height - sh * sc) / 2
        tr = self.trim
        step = dp(7)

        with self.canvas:
            # ---- sheet ----
            Color(*SCRAP)
            Rectangle(pos=(ox, oy), size=(sw * sc, sh * sc))

            # ---- scrap: the free rectangles MaxRects could not fill ----
            segs = []
            for (fx, fy, fw, fh) in self.sheet.get("free", []):
                x1 = ox + (fx + tr) * sc
                y2 = oy + (sh - fy - tr) * sc
                x2 = x1 + fw * sc
                y1 = y2 - fh * sc
                if x2 - x1 > dp(4) and y2 - y1 > dp(4):
                    segs += hatch_segments(x1, y1, x2, y2, step, dp(1.1))
            draw_quads(self.canvas, segs, HATCH)
            Color(0.72, 0.72, 0.72, 1)
            for (fx, fy, fw, fh) in self.sheet.get("free", []):
                x1 = ox + (fx + tr) * sc
                y2 = oy + (sh - fy - tr) * sc
                w, h = fw * sc, fh * sc
                if w > dp(4) and h > dp(4):
                    Line(rectangle=(x1, y2 - h, w, h), width=0.6)

            # ---- demand panels: filled + outlined ----
            places = self.sheet["places"]
            many = len(places) > 60
            for i, (x, y, w, h, _rot, ref) in enumerate(places):
                px1 = ox + x * sc
                py2 = oy + (sh - y) * sc
                pw, ph = w * sc, h * sc
                Color(*PALETTE[ref % len(PALETTE)])
                Rectangle(pos=(px1, py2 - ph), size=(pw, ph))
                if i == 0:                       # where cutting starts
                    Color(*CUT_START)
                    Line(rectangle=(px1, py2 - ph, pw, ph), width=dp(1.3))
                else:
                    Color(*PIECE_EDGE)
                    Line(rectangle=(px1, py2 - ph, pw, ph), width=0.9)
                if many or pw < dp(34) or ph < dp(17):
                    continue
                fs = dp(10) if ph < dp(30) else dp(11)
                tex = piece_label(f"{w:g}x{h:g}", fs)
                cx = px1 + pw / 2 - tex.width / 2
                cy = py2 - ph / 2 - tex.height / 2
                Color(1, 1, 1, 0.88)
                Rectangle(pos=(cx - 2, cy - 1), size=(tex.width + 4, tex.height + 2))
                Color(1, 1, 1, 1)
                Rectangle(texture=tex, pos=(cx, cy), size=tex.size)

            # ---- sheet border ----
            Color(*NAVY)
            Line(rectangle=(ox, oy, sw * sc, sh * sc), width=dp(1.6))


class CutMitraApp(App):
    title = "CutMitra"

    def build(self):
        try:
            return self._build()
        except Exception:
            tb = traceback.format_exc()
            save_error(tb)
            raise

    def _build(self):
        self.demands = [{"L": 380.0, "W": 955.0, "qty": 200, "rot": True,
                         "grain": False, "material": "", "label": ""}]
        self.stocks = [{"L": 1250.0, "W": 2500.0, "qty": 200, "material": "",
                        "label": "", "price": 0.0}]
        self.sheets = []
        self.stock_used = []
        self.trim_v = 0.0
        self.cur = 0

        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            Color(*BG)
            self._rbg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda o, v: setattr(self._rbg, "pos", v),
                  size=lambda o, v: setattr(self._rbg, "size", v))

        # ---- app bar ----
        bar = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(58),
                        padding=(dp(14), dp(6), dp(10), dp(6)), spacing=dp(0))
        with bar.canvas.before:
            Color(*NAVY)
            self._hbg = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=lambda o, v: setattr(self._hbg, "pos", v),
                 size=lambda o, v: setattr(self._hbg, "size", v))
        title_row = BoxLayout(spacing=dp(6))
        brand = BoxLayout(orientation="vertical", spacing=dp(0))
        brand.add_widget(lbl("CutMitra", fs=FS_H1, color=(1, 1, 1, 1), bold=True,
                             size_hint_y=None, height=dp(24), halign="left",
                             valign="bottom"))
        brand.add_widget(lbl("OFFLINE SHEET NESTING", fs=FS_CAP,
                             color=(0.62, 0.70, 0.82, 1), bold=True,
                             size_hint_y=None, height=dp(14), halign="left",
                             valign="top"))
        title_row.add_widget(brand)
        ver = lbl("v" + VERSION, fs=FS_CAP, color=(0.85, 0.89, 0.95, 1),
                  bold=True, size_hint_x=None, width=dp(56),
                  size_hint_y=None, height=dp(24), halign="right",
                  valign="middle")
        title_row.add_widget(ver)
        bar.add_widget(title_row)
        root.add_widget(bar)

        self.tabs = TabbedPanel(do_default_tab=False, border=(0, 0, 0, 0))
        self.tabs.tab_width = dp(68)
        self.tab_d = TabbedPanelItem(text="DEMAND")
        self.tab_s = TabbedPanelItem(text="STOCK")
        self.tab_r = TabbedPanelItem(text="RUN")
        self.tab_o = TabbedPanelItem(text="RESULT")
        self.tab_a = TabbedPanelItem(text="ABOUT")
        for t in (self.tab_d, self.tab_s, self.tab_r, self.tab_o, self.tab_a):
            t.font_size = dp(FS_CAP)
        self.tabs.add_widget(self.tab_d)
        self.tabs.add_widget(self.tab_s)
        self.tabs.add_widget(self.tab_r)
        self.tabs.add_widget(self.tab_o)
        self.tabs.add_widget(self.tab_a)

        self.dlist = RowList(self, "demand")
        self.tab_d.add_widget(self.dlist)
        self.slist = RowList(self, "stock")
        self.tab_s.add_widget(self.slist)
        self.tab_r.add_widget(self._run_tab())
        self.tab_o.add_widget(self._result_tab())
        self.tab_a.add_widget(self._about_tab())
        root.add_widget(self.tabs)
        self.refresh_lists()
        return root

    # ---------- RUN tab ----------
    def _run_tab(self):
        lay = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))

        form = Card(title="Saw settings (mm)", size_hint_y=None, height=dp(176),
                    spacing=dp(8))
        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(104))
        for cap, val in (("KERF", "3"), ("TRIM EDGE", "0")):
            grid.add_widget(lbl(cap, fs=FS_CAP, color=MUTED, bold=True,
                                size_hint_y=None, height=dp(44),
                                halign="left", valign="middle"))
        self.kerf_in = TextInput(text="3", input_filter="float", multiline=False,
                                 font_size=dp(FS_BODY), size_hint_y=None,
                                 height=dp(44))
        self.trim_in = TextInput(text="0", input_filter="float", multiline=False,
                                 font_size=dp(FS_BODY), size_hint_y=None,
                                 height=dp(44))
        grid.add_widget(self.kerf_in)
        grid.add_widget(self.trim_in)
        form.add_widget(grid)
        form.add_widget(lbl("Kerf is added between parts so the panel fits "
                            "the saw; trim shrinks the usable sheet on all "
                            "four sides.", fs=FS_CAP, color=MUTED,
                            halign="left", valign="top"))
        lay.add_widget(form)

        go = btn("START NESTING", bg=GREEN, fs=16, h=dp(58))
        go.bind(on_release=lambda _e: self.start_nesting())
        lay.add_widget(go)

        info = Card(title="What the run does", size_hint_y=None, height=dp(120))
        info.add_widget(lbl("MaxRects best-short-side-fit packing, the same "
                            "engine as the desktop app. Rotation and grain are "
                            "honoured per row, then sheets and panels are "
                            "drawn with the scrap area hatched.",
                            fs=FS_SMALL, color=BODY, halign="left", valign="top"))
        lay.add_widget(info)
        return lay

    # ---------- RESULT tab ----------
    def _result_tab(self):
        lay = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(8))

        # KPI tiles
        tiles = GridLayout(cols=3, spacing=dp(6), size_hint_y=None, height=dp(126))
        self.t_sheets = Tile("Sheets", "—")
        self.t_rm = Tile("RM (m2)", "—")
        self.t_pcs = Tile("Pieces", "—")
        self.t_util = Tile("Utilisation", "—", color=GREEN)
        self.t_waste = Tile("Scrap", "—", color=AMBER)
        self.t_cost = Tile("Cost (Rs)", "—")
        for t in (self.t_sheets, self.t_rm, self.t_pcs,
                  self.t_util, self.t_waste, self.t_cost):
            tiles.add_widget(t)
        lay.add_widget(tiles)

        # running metre card
        self.run_card = Card(title="Running metre (cut edge)", padding=dp(10),
                             spacing=dp(2), size_hint_y=None, height=dp(84))
        run_row = BoxLayout(spacing=dp(8))
        self.t_run = lbl("—", fs=24, color=BLUE, bold=True, size_hint_y=None,
                         height=dp(34), halign="left", valign="middle")
        run_row.add_widget(self.t_run)
        self.run_note = lbl("", fs=FS_CAP, color=MUTED, halign="right",
                            valign="middle")
        run_row.add_widget(self.run_note)
        self.run_card.add_widget(run_row)
        self.run_scroll = ScrollView(do_scroll_x=False)
        self.run_label = lbl("", fs=FS_SMALL, color=BODY, halign="left",
                             valign="top", size_hint_y=None)
        self.run_label.bind(texture_size=lambda o, v: setattr(o, "height", v[1]))
        self.run_label.bind(width=lambda o, v: setattr(o, "text_size", (v, None)))
        self.run_scroll.add_widget(self.run_label)
        self.run_card.add_widget(self.run_scroll)
        lay.add_widget(self.run_card)

        # diagram card
        self.sheet_card = Card(padding=(dp(6), dp(6), dp(6), dp(6)), spacing=dp(4),
                               size_hint_y=2.6)
        nav = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))
        pv = btn("PREV", bg=(0.88, 0.90, 0.93, 1), fg=INK, fs=FS_CAP, h=dp(34),
                 size_hint_x=None, width=dp(70))
        pv.bind(on_release=lambda _e: self.step_sheet(-1))
        nx = btn("NEXT", bg=(0.88, 0.90, 0.93, 1), fg=INK, fs=FS_CAP, h=dp(34),
                 size_hint_x=None, width=dp(70))
        nx.bind(on_release=lambda _e: self.step_sheet(1))
        self.sheet_label = lbl("Sheet -/-", fs=FS_BODY, color=INK, bold=True)
        nav.add_widget(pv)
        nav.add_widget(self.sheet_label)
        nav.add_widget(nx)
        self.sheet_card.add_widget(nav)
        self.preview = SheetPreview()
        self.sheet_card.add_widget(self.preview)
        lay.add_widget(self.sheet_card)

        # cut list
        self.cut_card = Card(title="Panel cut list", padding=dp(8), spacing=dp(4),
                             size_hint_y=1.0)
        self.cut_scroll = ScrollView(do_scroll_x=False)
        self.cut_label = lbl("", fs=FS_SMALL, color=BODY, halign="left",
                             valign="top", size_hint_y=None)
        self.cut_label.bind(texture_size=lambda o, v: setattr(o, "height", v[1]))
        self.cut_label.bind(width=lambda o, v: setattr(o, "text_size", (v, None)))
        self.cut_scroll.add_widget(self.cut_label)
        self.cut_card.add_widget(self.cut_scroll)
        lay.add_widget(self.cut_card)
        return lay

    # ---------- ABOUT tab ----------
    def _about_tab(self):
        lay = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))
        head = Card(padding=dp(14), spacing=dp(2), size_hint_y=None, height=dp(112))
        head.add_widget(lbl("CutMitra", fs=FS_H1, color=INK, bold=True,
                            size_hint_y=None, height=dp(28), halign="left",
                            valign="bottom"))
        head.add_widget(lbl(f"Version {VERSION}  ·  offline sheet nesting",
                            fs=FS_CAP, color=MUTED, bold=True,
                            size_hint_y=None, height=dp(16), halign="left",
                            valign="top"))
        head.add_widget(lbl("100% offline — no internet, no account, "
                            "no tracking.", fs=FS_SMALL, color=BODY,
                            halign="left", valign="top"))
        lay.add_widget(head)

        eng = Card(title="Engine", size_hint_y=None, height=dp(104))
        eng.add_widget(lbl("MaxRects best-short-side-fit packing — the exact "
                           "same core (core_nest.py) the desktop app uses, so "
                           "phone and PC give identical sheet counts.",
                           fs=FS_SMALL, color=BODY, halign="left", valign="top"))
        lay.add_widget(eng)

        dev = Card(title="Developers", size_hint_y=None, height=dp(156))
        dev.add_widget(lbl(DEVELOPERS[0], fs=FS_BODY, color=INK, bold=True,
                           size_hint_y=None, height=dp(22), halign="left",
                           valign="middle"))
        dev.add_widget(lbl("Founder, CutMitra", fs=FS_CAP, color=MUTED,
                           size_hint_y=None, height=dp(15), halign="left",
                           valign="middle"))
        dev.add_widget(lbl("", size_hint_y=None, height=dp(6)))
        dev.add_widget(lbl(DEVELOPERS[1], fs=FS_BODY, color=INK, bold=True,
                           size_hint_y=None, height=dp(22), halign="left",
                           valign="middle"))
        dev.add_widget(lbl("Co-developer, CutMitra", fs=FS_CAP, color=MUTED,
                           size_hint_y=None, height=dp(15), halign="left",
                           valign="middle"))
        lay.add_widget(dev)

        sp = BoxLayout()
        sp.bind(minimum_height=sp.setter("height"))
        lay.add_widget(sp)
        return lay

    # ---------- data ops ----------
    def refresh_lists(self):
        self.dlist.refresh()
        self.slist.refresh()

    def clear_list(self, kind):
        if kind == "demand":
            self.demands.clear()
        else:
            self.stocks.clear()
        self.refresh_lists()

    def delete_row(self, kind, j):
        items = self.demands if kind == "demand" else self.stocks
        if 0 <= j < len(items):
            del items[j]
        self.refresh_lists()

    @crash_guard
    def open_editor(self, kind, j):
        is_stock = kind == "stock"
        cur = None
        if j >= 0:
            items = self.stocks if is_stock else self.demands
            cur = items[j]
        grid = GridLayout(cols=2, spacing=(dp(8), dp(6)), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        edits = {}

        def field(name, val, filt=None):
            grid.add_widget(lbl(name.upper(), fs=FS_CAP, color=MUTED, bold=True,
                                size_hint_y=None, height=dp(44), halign="left",
                                valign="middle"))
            ti = TextInput(text=str(val), multiline=False, font_size=dp(FS_BODY),
                           size_hint_y=None, height=dp(44))
            if filt:
                ti.input_filter = filt
            grid.add_widget(ti)
            edits[name] = ti

        field("Length", cur["L"] if cur else "", "float")
        field("Width", cur["W"] if cur else "", "float")
        field("Qty", cur["qty"] if cur else "1", "int")
        field("Material", cur.get("material", "") if cur else "")
        if is_stock:
            field("Price", cur.get("price", 0) if cur else "0", "float")
            switches = {}
        else:
            switches = {}
            for key, label in (("rot", "Rotation"), ("grain", "Grain lock")):
                grid.add_widget(lbl(label.upper(), fs=FS_CAP, color=MUTED,
                                    bold=True, size_hint_y=None, height=dp(44),
                                    halign="left", valign="middle"))
                sw = Switch(active=bool(cur.get(key, key == "rot")) if cur else key == "rot",
                            size_hint_y=None, height=dp(44))
                grid.add_widget(sw)
                switches[key] = sw

        box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        scr = ScrollView()
        scr.add_widget(grid)
        box.add_widget(scr)
        btns = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        save = btn("SAVE", bg=GREEN, fs=FS_BODY, h=dp(44))
        cancel = btn("CANCEL", bg=(0.60, 0.64, 0.70, 1), fs=FS_BODY, h=dp(44))
        btns.add_widget(save)
        btns.add_widget(cancel)
        box.add_widget(btns)
        pop = Popup(title=("Edit STOCK" if is_stock else "Edit DEMAND") if cur
                    else ("Add STOCK" if is_stock else "Add DEMAND"),
                    content=box, size_hint=(0.92, 0.72),
                    separator_color=BLUE)

        def do_save(_e):
            try:
                rec = {"L": _num(edits["Length"].text, "Length"),
                       "W": _num(edits["Width"].text, "Width"),
                       "qty": _int(edits["Qty"].text, "Qty"),
                       "material": edits["Material"].text.strip(),
                       "label": ""}
                if is_stock:
                    rec["price"] = _num(edits["Price"].text, "Price", allow_zero=True)
                else:
                    rec["rot"] = switches["rot"].active
                    rec["grain"] = switches["grain"].active
                    if rec["grain"]:
                        rec["rot"] = False
            except ValueError as e:
                err_popup(str(e))
                return
            items = self.stocks if is_stock else self.demands
            if cur is None:
                items.append(rec)
            else:
                items[j].update(rec)
            self.refresh_lists()
            pop.dismiss()

        save.bind(on_release=do_save)
        cancel.bind(on_release=pop.dismiss)
        pop.open()

    # ---------- optimize ----------
    @crash_guard
    def start_nesting(self):
        if not self.demands:
            return err_popup("Add at least one DEMAND row.")
        if not self.stocks:
            return err_popup("Add at least one STOCK row.")
        try:
            kerf = _num(self.kerf_in.text, "Kerf", allow_zero=True)
            trim = _num(self.trim_in.text, "Trim", allow_zero=True)
        except ValueError as e:
            return err_popup(str(e))
        res, info = core_nest.SheetPacker.optimize(self.demands, self.stocks, kerf, trim)
        if res is None:
            return err_popup(info)
        self.sheets = res
        self.stock_used = info.get("stock_used", [])
        self.trim_v = trim
        self.cur = 0
        self.show_result()
        self.tabs.switch_to(self.tab_o)

    def show_result(self):
        total, blocks = core_nest.summarize_nesting(
            self.sheets, self.demands, self.stocks, self.stock_used)
        self.t_sheets.set(str(total["sheets"]))
        self.t_rm.set(f"{total['rm_sqm']:.2f}")
        self.t_pcs.set(str(total["pcs"]))
        self.t_util.set(f"{total['util']:.1f}%")
        self.t_waste.set(f"{total['waste']:.1f}%")
        self.t_cost.set(f"{total['cost']:,.0f}")

        # ---- running metre of the demand ----
        self.t_run.text = f"{total['run_m']:,.2f} m"
        self.run_note.text = (f"{len(total['parts'])} size(s)  ·  "
                              f"{total['pcs']} pcs")
        rows = [("SIZE", "PCS", "M/PC", "RUNNING M")]
        for p in total["parts"]:
            rows.append((p["size"], str(p["qty"]), f"{p['m_each']:.2f}",
                         f"{p['run_m']:.2f}"))
        width = max(len(r[0]) for r in rows)
        lines = []
        for i, (a, b, c, d) in enumerate(rows):
            lines.append(f"{a:<{width}}  {b:>5}  {c:>6}  {d:>9}")
            if i == 0:
                lines.append("-" * (width + 25))
        self.run_label.text = "\n".join(lines)
        self.show_sheet()

    @crash_guard
    def step_sheet(self, d):
        if not self.sheets:
            return
        self.cur = max(0, min(len(self.sheets) - 1, self.cur + d))
        self.show_sheet()

    def show_sheet(self):
        if not self.sheets:
            return
        sh = self.sheets[self.cur]
        self.sheet_label.text = f"Sheet {self.cur + 1}/{len(self.sheets)}"
        self.preview.show(sh, getattr(self, "trim_v", 0.0))
        lines = []
        for k, (x, y, w, h, rot, ref) in enumerate(sh["places"], 1):
            dd = self.demands[ref]
            lines.append(f"[{k}] {dd['L']:g}x{dd['W']:g} X={x:.0f} Y={y:.0f}"
                         f"{' ROT' if rot else ''}")
        self.cut_label.text = "\n".join(lines)


if __name__ == "__main__":
    def _excepthook(exc_type, exc, tb):
        save_error("".join(traceback.format_exception(exc_type, exc, tb)))
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _excepthook
    CutMitraApp().run()
