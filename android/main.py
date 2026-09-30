"""CutMitra Android app (Kivy) — offline 2D sheet nesting.

Same MaxRects engine as the desktop app (core_nest.py, copied next to this
file at package time). 100% offline. Mobile v1: manual size entry +
diagrams + material-wise summary (no file import/export yet).
"""
from kivy.app import App
from kivy.graphics import Color, Line, Rectangle
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

NAVY = (0.12, 0.22, 0.39, 1)
STEEL = (0.85, 0.88, 0.95, 1)
GREEN = (0.22, 0.34, 0.13, 1)
PALETTE = [(1, 1, 1, 1), (1, 0.85, 0.85, 1), (0.85, 0.92, 1, 1),
           (0.85, 0.95, 0.85, 1), (1, 0.95, 0.77, 1), (0.91, 0.85, 1, 1)]


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


def err_popup(msg):
    box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
    box.add_widget(Label(text=msg))
    btn = Button(text="OK", size_hint_y=None, height=dp(48))
    box.add_widget(btn)
    pop = Popup(title="CutMitra", content=box, size_hint=(0.85, 0.4))
    btn.bind(on_release=pop.dismiss)
    pop.open()


class RowList(BoxLayout):
    """Scrollable list of demand/stock rows with Edit + Del buttons."""

    def __init__(self, app, kind, **kw):
        super().__init__(orientation="vertical", **kw)
        self.app = app
        self.kind = kind  # "demand" or "stock"
        bar = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6))
        add = Button(text="+ Add", background_color=GREEN, color=(1, 1, 1, 1))
        add.bind(on_release=lambda _e: app.open_editor(kind, -1))
        clr = Button(text="Clear", size_hint_x=None, width=dp(90))
        clr.bind(on_release=lambda _e: app.clear_list(kind))
        bar.add_widget(add)
        bar.add_widget(clr)
        self.add_widget(bar)
        self.scroll = ScrollView()
        self.grid = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.scroll.add_widget(self.grid)
        self.add_widget(self.scroll)

    def refresh(self):
        self.grid.clear_widgets()
        items = self.app.demands if self.kind == "demand" else self.app.stocks
        for i, it in enumerate(items):
            if self.kind == "demand":
                t = (f"{it['L']:g} x {it['W']:g} x {it['qty']}  "
                     f"{'R' if it.get('rot') else '-'}{'G' if it.get('grain') else ''}  "
                     f"{it.get('material', '')} {it.get('label', '')}".strip())
            else:
                t = (f"{it['L']:g} x {it['W']:g} x {it['qty']}  "
                     f"{it.get('material', '')}  Rs.{it.get('price', 0):g}".strip())
            row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(4))
            row.add_widget(Label(text=t, halign="left", valign="middle"))
            eb = Button(text="Edit", size_hint_x=None, width=dp(70))
            eb.bind(on_release=lambda _e, j=i: self.app.open_editor(self.kind, j))
            db = Button(text="Del", size_hint_x=None, width=dp(60))
            db.bind(on_release=lambda _e, j=i: self.app.delete_row(self.kind, j))
            row.add_widget(eb)
            row.add_widget(db)
            self.grid.add_widget(row)


class SheetPreview(Widget):
    """Scaled drawing of one cutting sheet (y flipped to match diagrams)."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.sheet = None
        self.bind(size=self._draw, pos=self._draw)

    def show(self, sheet):
        self.sheet = sheet
        self._draw()

    def _draw(self, * _a):
        self.canvas.clear()
        if not self.sheet:
            return
        sw, sh = self.sheet["sw"], self.sheet["sh"]
        pad = dp(8)
        sc = min((self.width - 2 * pad) / sw, (self.height - 2 * pad) / sh)
        if sc <= 0:
            return
        ox = self.x + (self.width - sw * sc) / 2
        oy = self.y + (self.height - sh * sc) / 2
        with self.canvas:
            Color(0.95, 0.95, 0.95, 1)
            Rectangle(pos=(ox, oy), size=(sw * sc, sh * sc))
            for (x, y, w, h, _rot, ref) in self.sheet["places"]:
                Color(*PALETTE[ref % len(PALETTE)])
                fy = sh - y - h  # flip: our Y grows downward
                Rectangle(pos=(ox + x * sc, oy + fy * sc), size=(w * sc, h * sc))
            Color(*NAVY)
            Line(rectangle=(ox, oy, sw * sc, sh * sc), width=2)


class CutMitraApp(App):
    title = "CutMitra"

    def build(self):
        self.demands = [{"L": 380.0, "W": 955.0, "qty": 200, "rot": True,
                         "grain": False, "material": "", "label": ""}]
        self.stocks = [{"L": 1250.0, "W": 2500.0, "qty": 200, "material": "",
                        "label": "", "price": 0.0}]
        self.sheets = []
        self.stock_used = []
        self.cur = 0

        root = BoxLayout(orientation="vertical")
        head = Label(text="CutMitra — offline nesting", size_hint_y=None,
                     height=dp(44), color=(1, 1, 1, 1), bold=True)
        with head.canvas.before:
            Color(*NAVY)
            self._hbg = Rectangle(pos=head.pos, size=head.size)
        head.bind(pos=lambda o, v: setattr(self._hbg, "pos", v),
                  size=lambda o, v: setattr(self._hbg, "size", v))
        root.add_widget(head)

        self.tabs = TabbedPanel(do_default_tab=False)
        self.tabs.tab_width = dp(68)
        self.tab_d = TabbedPanelItem(text="DEMAND")
        self.tab_s = TabbedPanelItem(text="STOCK")
        self.tab_r = TabbedPanelItem(text="RUN")
        self.tab_o = TabbedPanelItem(text="RESULT")
        self.tab_a = TabbedPanelItem(text="ABOUT")
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
        lay = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        lay.add_widget(Label(text="Sheet nesting settings (mm)"))
        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(110))
        grid.add_widget(Label(text="Kerf saw blade:"))
        self.kerf_in = TextInput(text="3", input_filter="float", multiline=False)
        grid.add_widget(self.kerf_in)
        grid.add_widget(Label(text="Trim edge:"))
        self.trim_in = TextInput(text="0", input_filter="float", multiline=False)
        grid.add_widget(self.trim_in)
        lay.add_widget(grid)
        btn = Button(text="▶ START NESTING", size_hint_y=None, height=dp(64),
                     background_color=GREEN, color=(1, 1, 1, 1), bold=True)
        btn.bind(on_release=lambda _e: self.run())
        lay.add_widget(btn)
        lay.add_widget(Label(text="Same MaxRects engine as desktop.\nRotation + Grain respected per row.",
                             halign="center"))
        return lay

    # ---------- RESULT tab ----------
    def _result_tab(self):
        lay = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
        self.res_label = Label(text="Press ▶ START on the RUN tab.",
                               size_hint_y=None, height=dp(150),
                               halign="left", valign="top")
        lay.add_widget(self.res_label)
        nav = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        pv = Button(text="◀")
        pv.bind(on_release=lambda _e: self.step_sheet(-1))
        nx = Button(text="▶")
        nx.bind(on_release=lambda _e: self.step_sheet(1))
        self.sheet_label = Label(text="Sheet -/-")
        nav.add_widget(pv)
        nav.add_widget(self.sheet_label)
        nav.add_widget(nx)
        lay.add_widget(nav)
        self.preview = SheetPreview(size_hint_y=0.55)
        lay.add_widget(self.preview)
        self.cut_scroll = ScrollView()
        self.cut_label = Label(text="", halign="left", valign="top", size_hint_y=None)
        self.cut_label.bind(texture_size=lambda o, v: setattr(o, "height", v[1]))
        self.cut_label.bind(width=lambda o, v: setattr(o, "text_size", (v, None)))
        self.cut_scroll.add_widget(self.cut_label)
        lay.add_widget(self.cut_scroll)
        return lay

    # ---------- ABOUT tab ----------
    def _about_tab(self):
        lay = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        txt = ("CutMitra\nOffline 2D sheet nesting\n\n"
               f"Version {VERSION}\n\n"
               "Same MaxRects nesting engine as the\n"
               "desktop app. 100% offline —\n"
               "no internet, no account, no tracking.\n\n"
               "Developers\n" + "\n".join(DEVELOPERS))
        lab = Label(text=txt, halign="center", valign="top", size_hint_y=None)
        lab.bind(texture_size=lambda o, v: setattr(o, "height", v[1]))
        lab.bind(width=lambda o, v: setattr(o, "text_size", (v, None)))
        lay.add_widget(lab)
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

    def open_editor(self, kind, j):
        is_stock = kind == "stock"
        cur = None
        if j >= 0:
            items = self.stocks if is_stock else self.demands
            cur = items[j]
        grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        edits = {}

        def field(name, val, filt=None):
            grid.add_widget(Label(text=name, size_hint_y=None, height=dp(44)))
            ti = TextInput(text=str(val), multiline=False, size_hint_y=None, height=dp(44))
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
                grid.add_widget(Label(text=label, size_hint_y=None, height=dp(44)))
                sw = Switch(active=bool(cur.get(key, key == "rot")) if cur else key == "rot",
                            size_hint_y=None, height=dp(44))
                grid.add_widget(sw)
                switches[key] = sw

        box = BoxLayout(orientation="vertical", spacing=dp(6))
        scr = ScrollView()
        scr.add_widget(grid)
        box.add_widget(scr)
        btns = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6))
        save = Button(text="Save")
        cancel = Button(text="Cancel")
        btns.add_widget(save)
        btns.add_widget(cancel)
        box.add_widget(btns)
        pop = Popup(title=("Edit STOCK" if is_stock else "Edit DEMAND") if cur
                    else ("Add STOCK" if is_stock else "Add DEMAND"),
                    content=box, size_hint=(0.92, 0.75))

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
    def run(self):
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
        self.cur = 0
        self.show_result()
        self.tabs.switch_to(self.tab_o)

    def show_result(self):
        total, blocks = core_nest.summarize_nesting(
            self.sheets, self.demands, self.stocks, self.stock_used)
        L = [f"Sheets: {total['sheets']}  RM: {total['rm_sqm']:.2f} m2  Pcs: {total['pcs']}",
             f"Util: {total['util']:.2f}%  Waste: {total['waste']:.2f}%  Cost: {total['cost']:,.0f}", ""]
        for b in blocks:
            L.append(f"[{b['material']}] {b['sheets']} sheets, Util {b['util']:.1f}%")
            for sz in b["sizes"]:
                L.append(f"  {sz['size']} x {sz['qty']}")
        self.res_label.text = "\n".join(L)
        self.show_sheet()

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
        self.preview.show(sh)
        lines = []
        for k, (x, y, w, h, rot, ref) in enumerate(sh["places"], 1):
            dd = self.demands[ref]
            lines.append(f"[{k}] {dd['L']:g}x{dd['W']:g} X={x:.0f} Y={y:.0f}"
                         f"{' ROT' if rot else ''}")
        self.cut_label.text = "\n".join(lines)


if __name__ == "__main__":
    CutMitraApp().run()
