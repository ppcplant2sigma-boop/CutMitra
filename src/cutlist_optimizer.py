"""CutMitra — offline Windows app (Pro-style).
Improvements vs Cutting Optimization Pro (from screenshot analysis):
 + Kerf (saw width) + Trim edge
 + Grain lock (forces no-rotation), Material match, Label, Price/Cost
 + Zoom, cut-position table (X/Y), per-sheet stats, DXF export, CSV import
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import csv

APP_TITLE = "CutMitra"
APP_VERSION = "1.0.3"
DEVELOPERS = ("Er. Durgesh Pandey", "Er. Arun Shukla")


from core_nest import (SheetPacker, write_dxf,
                        parse_dxf_parts, parse_pdf_parts)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_TITLE} — offline")
        self.root.geometry("1360x840")

        self.dL = tk.StringVar(value="380")
        self.dW = tk.StringVar(value="955")
        self.dQ = tk.StringVar(value="200")
        self.dRot = tk.BooleanVar(value=True)
        self.dGrain = tk.BooleanVar(value=False)
        self.dMat = tk.StringVar(value="")
        self.dLab = tk.StringVar(value="")

        self.sL = tk.StringVar(value="1250")
        self.sW = tk.StringVar(value="2500")
        self.sQ = tk.StringVar(value="200")
        self.sMat = tk.StringVar(value="")
        self.sPrice = tk.StringVar(value="0")

        self.kerf = tk.StringVar(value="3")
        self.trim = tk.StringVar(value="0")
        self.zoom = tk.DoubleVar(value=1.0)

        self.opt_size = tk.BooleanVar(value=True)
        self.opt_waste = tk.BooleanVar(value=True)
        self.opt_label = tk.BooleanVar(value=True)
        self.opt_index = tk.BooleanVar(value=False)

        self.demands = [{"L": 380.0, "W": 955.0, "qty": 200, "rot": True,
                         "grain": False, "material": "", "label": ""}]
        self.stocks = [{"L": 1250.0, "W": 2500.0, "qty": 200, "material": "", "label": "", "price": 0.0}]
        self.sheets = []
        self.cur_sheet = 0

        self.build_ui()
        self.refresh_all()
        self._set_icon()

    def _set_icon(self):
        # window + taskbar logo; silent fallbacks if assets are missing
        try:
            import os
            import sys
            here = os.path.dirname(os.path.abspath(__file__))
            base = getattr(sys, "_MEIPASS", None)  # PyInstaller bundle dir
            ico = [os.path.join(base, "assets", "logo.ico")] if base else []
            ico += [os.path.join(here, "..", "assets", "logo.ico")]
            png = ([os.path.join(base, "assets", "logo.png")] if base else [])
            png += [os.path.join(here, "..", "assets", "logo.png")]
            for p in ico:
                if os.path.isfile(p):
                    try:
                        self.root.iconbitmap(default=p)
                        break
                    except Exception:
                        continue
            for p in png:
                if os.path.isfile(p):
                    try:
                        img = tk.PhotoImage(file=p)
                        self.root.iconphoto(True, img)
                        self._icon_img = img  # keep a reference
                        break
                    except Exception:
                        continue
        except Exception:
            pass

    # ---------- helpers ----------
    def _num(self, s, name, allow_zero=False):
        v = float(str(s).strip())
        if (v < 0) or (not allow_zero and v <= 0):
            raise ValueError(f"{name} must be {'>= 0' if allow_zero else '> 0'}.")
        return v

    def _int(self, s, name):
        v = int(float(str(s).strip()))
        if v <= 0:
            raise ValueError(f"{name} must be > 0.")
        return v

    # ---------- UI ----------
    def build_ui(self):
        menubar = tk.Menu(self.root)
        mf = tk.Menu(menubar, tearoff=0)
        mf.add_command(label="New", command=self.new_project)
        mf.add_command(label="Open JSON…", command=self.open_project)
        mf.add_command(label="Save JSON…", command=self.save_project)
        mf.add_separator()
        mf.add_command(label="Import DEMAND csv…", command=self.import_demand)
        mf.add_command(label="Import STOCK csv…", command=self.import_stock)
        mf.add_separator()
        mf.add_command(label="Read PDF drawing → DEMAND…", command=lambda: self.import_drawing("PDF"))
        mf.add_command(label="Read DXF drawing → DEMAND…", command=lambda: self.import_drawing("DXF"))
        mf.add_separator()
        mf.add_command(label="Export report (.txt)…", command=self.export_report)
        mf.add_command(label="Export DXF (.dxf)…", command=self.export_dxf)
        menubar.add_cascade(label="File", menu=mf)
        mh = tk.Menu(menubar, tearoff=0)
        mh.add_command(label=f"About {APP_TITLE}…", command=self.show_about)
        menubar.add_cascade(label="Help", menu=mh)
        self.root.config(menu=menubar)

        # ---- professional theme (navy / steel, no harsh blues) ----
        NAVY, STEEL = "#1F3864", "#D9E1F2"
        self.NAVY = NAVY
        tsty = ttk.Style()
        try:
            tsty.theme_use("clam")
        except Exception:
            pass
        tsty.configure("Toolbar.TFrame", background=STEEL)
        tsty.configure("Toolbar.TLabel", background=STEEL)
        tsty.configure("Start.TButton", background="#375623", foreground="white",
                       font=("Segoe UI", 9, "bold"), padding=6)
        tsty.map("Start.TButton", background=[("active", "#43682C")],
                 foreground=[("active", "white")])
        tsty.configure("Treeview.Heading", background=NAVY, foreground="white",
                       font=("Segoe UI", 9, "bold"))
        tsty.configure("Treeview", rowheight=23, fieldbackground="white")
        tsty.map("Treeview", background=[("selected", "#2E75B6")],
                 foreground=[("selected", "white")])

        tb = ttk.Frame(self.root, padding=4, style="Toolbar.TFrame")
        tb.pack(fill=tk.X)
        ttk.Button(tb, text="▶ Start", command=self.run, style="Start.TButton").pack(side=tk.LEFT, padx=3)
        ttk.Button(tb, text="💾 Save", command=self.save_project).pack(side=tk.LEFT, padx=3)
        ttk.Button(tb, text="🖨 Print report", command=self.export_report).pack(side=tk.LEFT, padx=3)
        ttk.Button(tb, text="DXF", command=self.export_dxf).pack(side=tk.LEFT, padx=3)
        # Pro settings: kerf + trim + zoom
        ttk.Label(tb, text="Kerf saw (mm):", style="Toolbar.TLabel").pack(side=tk.LEFT, padx=(14, 2))
        ttk.Entry(tb, textvariable=self.kerf, width=6).pack(side=tk.LEFT)
        ttk.Label(tb, text="Trim edge (mm):", style="Toolbar.TLabel").pack(side=tk.LEFT, padx=(10, 2))
        ttk.Entry(tb, textvariable=self.trim, width=6).pack(side=tk.LEFT)
        ttk.Label(tb, text="Zoom:", style="Toolbar.TLabel").pack(side=tk.LEFT, padx=(10, 2))
        ttk.Scale(tb, from_=0.3, to=2.0, variable=self.zoom,
                  orient=tk.HORIZONTAL, length=110, command=lambda _e: self.redraw()).pack(side=tk.LEFT)
        ttk.Label(tb, text="CutMitra — 100% offline",
                  style="Toolbar.TLabel", foreground="#404040").pack(side=tk.LEFT, padx=10)

        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        left = ttk.Frame(main, width=470)
        right = ttk.Frame(main)
        main.add(left, weight=1)
        main.add(right, weight=3)

        # DEMAND — direct edit inside the table (no separate Add bar)
        tk.Label(left, text="  DEMAND — parts to cut", bg=self.NAVY, fg="white",
                 font=("Segoe UI", 10, "bold"), anchor=tk.W).pack(fill=tk.X, pady=(2, 0))
        ttk.Label(left, text="Double-click cell to edit • Tab = next cell • click Rot/Grain to toggle • + row adds • Del deletes",
                  foreground="#595959", font=("Segoe UI", 8)).pack(anchor=tk.W)
        dbar = ttk.Frame(left)
        dbar.pack(fill=tk.X, pady=1)
        ttk.Button(dbar, text="Delete", command=self.del_demand, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(dbar, text="Clear", command=lambda: (self.demands.clear(), self.refresh_all()),
                   width=8).pack(side=tk.LEFT, padx=2)

        self.dtree = ttk.Treeview(left, columns=("n", "L", "W", "qty", "rot", "grain", "mat", "lab"),
                                  show="headings", height=7)
        for c, w, t in [("n", 28, "#"), ("L", 62, "Length"), ("W", 62, "Width"), ("qty", 55, "Qty"),
                        ("rot", 52, "Rot"), ("grain", 52, "Grain"), ("mat", 60, "Mat"), ("lab", 70, "Label")]:
            self.dtree.heading(c, text=t)
            self.dtree.column(c, width=w, anchor=tk.CENTER)
        self.dtree.pack(fill=tk.X, pady=2)
        self.dtree.bind("<Button-1>", self.on_d_click)
        self.dtree.bind("<Double-1>", self.on_d_edit)
        self.dtree.bind("<Delete>", lambda _e: self.del_demand())
        self.dtree.tag_configure("even", background="white")
        self.dtree.tag_configure("odd", background="#EDF2F9")
        self.dtree.tag_configure("addrow", background="#E2EFDA", foreground="#375623")

        # STOCK — direct edit inside the table (no separate Add bar)
        tk.Label(left, text="  STOCK — sheets available", bg=self.NAVY, fg="white",
                 font=("Segoe UI", 10, "bold"), anchor=tk.W).pack(fill=tk.X, pady=(6, 0))
        ttk.Label(left, text="Double-click cell to edit • Tab = next cell • + row adds • Del deletes",
                  foreground="#595959", font=("Segoe UI", 8)).pack(anchor=tk.W)
        sbar = ttk.Frame(left)
        sbar.pack(fill=tk.X, pady=1)
        ttk.Button(sbar, text="Delete", command=self.del_stock, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(sbar, text="Clear", command=lambda: (self.stocks.clear(), self.refresh_all()),
                   width=8).pack(side=tk.LEFT, padx=2)

        self.stree = ttk.Treeview(left, columns=("n", "L", "W", "qty", "mat", "price"),
                                   show="headings", height=7)
        for c, w, t in [("n", 28, "#"), ("L", 70, "Length"), ("W", 70, "Width"),
                        ("qty", 55, "Qty"), ("mat", 70, "Mat"), ("price", 70, "Price")]:
            self.stree.heading(c, text=t)
            self.stree.column(c, width=w, anchor=tk.CENTER)
        self.stree.pack(fill=tk.X, pady=2)
        self.stree.bind("<Double-1>", self.on_s_edit)
        self.stree.bind("<Delete>", lambda _e: self.del_stock())
        self.stree.tag_configure("even", background="white")
        self.stree.tag_configure("odd", background="#EDF2F9")
        self.stree.tag_configure("addrow", background="#E2EFDA", foreground="#375623")

        # RIGHT
        ctrl = ttk.Frame(right)
        ctrl.pack(fill=tk.X)
        ttk.Checkbutton(ctrl, text="Show size of the pieces", variable=self.opt_size,
                        command=self.redraw).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(ctrl, text="Show size of the wastes", variable=self.opt_waste,
                        command=self.redraw).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(ctrl, text="Show piece label", variable=self.opt_label,
                        command=self.redraw).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(ctrl, text="Show index of cutting", variable=self.opt_index,
                        command=self.redraw).pack(side=tk.LEFT, padx=4)

        nav = ttk.Frame(right)
        nav.pack(fill=tk.X, pady=3)
        ttk.Button(nav, text="◀ Prev", command=self.prev_sheet, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav, text="Next ▶", command=self.next_sheet, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Label(nav, text="Sheet:").pack(side=tk.LEFT, padx=(10, 2))
        self.sheet_combo = ttk.Combobox(nav, state="readonly", width=26)
        self.sheet_combo.pack(side=tk.LEFT)
        self.sheet_combo.bind("<<ComboboxSelected>>", self.on_sheet_pick)
        self.sheet_info = ttk.Label(nav, text="", foreground="gray")
        self.sheet_info.pack(side=tk.LEFT, padx=12)

        paned_r = ttk.PanedWindow(right, orient=tk.VERTICAL)
        paned_r.pack(fill=tk.BOTH, expand=True)
        cwrap = ttk.Frame(paned_r)
        bwrap = ttk.Frame(paned_r)
        paned_r.add(cwrap, weight=3)
        paned_r.add(bwrap, weight=1)

        self.canvas = tk.Canvas(cwrap, bg="white", highlightthickness=0, bd=1, relief=tk.SOLID)
        hbar = ttk.Scrollbar(cwrap, orient=tk.HORIZONTAL, command=self.canvas.xview)
        vbar = ttk.Scrollbar(cwrap, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        cwrap.rowconfigure(0, weight=1)
        cwrap.columnconfigure(0, weight=1)

        ttk.Label(bwrap, text="Cut list — current sheet (X, Y positions)").pack(anchor=tk.W)
        self.ctree = ttk.Treeview(bwrap, columns=("i", "size", "x", "y", "rot", "lab"),
                                  show="headings", height=6)
        for c, w, t in [("i", 40, "#"), ("size", 130, "Size LxW"), ("x", 80, "X"),
                        ("y", 80, "Y"), ("rot", 70, "Rotated"), ("lab", 120, "Label")]:
            self.ctree.heading(c, text=t)
            self.ctree.column(c, width=w, anchor=tk.CENTER)
        self.ctree.pack(fill=tk.BOTH, expand=True)

        # Pro-style status bar
        bar = ttk.Frame(self.root)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.st_util = ttk.Label(bar, text="Utilization: —", relief=tk.SUNKEN, anchor=tk.W, width=24)
        self.st_waste = ttk.Label(bar, text="Waste: —", relief=tk.SUNKEN, anchor=tk.W, width=18)
        self.st_qty = ttk.Label(bar, text="Quantity: —", relief=tk.SUNKEN, anchor=tk.W, width=18)
        self.st_cost = ttk.Label(bar, text="Cost: —", relief=tk.SUNKEN, anchor=tk.W, width=22)
        self.st_msg = ttk.Label(bar, text="Ready.", relief=tk.SUNKEN, anchor=tk.W)
        self.st_util.pack(side=tk.LEFT, fill=tk.X)
        self.st_waste.pack(side=tk.LEFT, fill=tk.X)
        self.st_qty.pack(side=tk.LEFT, fill=tk.X)
        self.st_cost.pack(side=tk.LEFT, fill=tk.X)
        self.st_msg.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # ---------- data ops — direct in-table edit (spreadsheet style) ----------
    D_EDIT_COLS = ("#2", "#3", "#4", "#7", "#8")
    S_EDIT_COLS = ("#2", "#3", "#4", "#5", "#6")

    def _cell_editor(self, tree, rowid, col, cur, commit, on_tab=None):
        # commit any other open editor first so no keystroke is lost
        if getattr(self, "_open_editor", None):
            old_ent, old_commit = self._open_editor
            self._open_editor = None
            try:
                if old_ent.winfo_exists():
                    old_commit(old_ent.get())
                    old_ent.destroy()
            except Exception:
                pass
        for w in tree.place_slaves():
            w.destroy()
        try:
            bbox = tree.bbox(rowid, col)
        except Exception:
            return
        if not bbox:
            return
        x, y, w, h = bbox
        ent = tk.Entry(tree, highlightthickness=2, highlightcolor="#2E75B6",
                       highlightbackground="#2E75B6")
        ent.place(x=x, y=y, width=w, height=h)
        ent.insert(0, cur)
        ent.focus_set()
        ent.select_range(0, tk.END)
        closed = {"v": False}
        self._open_editor = (ent, commit)

        def close():
            if not closed["v"]:
                closed["v"] = True
                if getattr(self, "_open_editor", (None, None))[0] is ent:
                    self._open_editor = None
                if ent.winfo_exists():
                    ent.destroy()

        def done(_e=None):
            try:
                commit(ent.get())
            finally:
                close()

        def tab(step):
            def _go(_e=None):
                try:
                    commit(ent.get())
                finally:
                    close()
                if on_tab is not None:
                    tree.after(20, lambda: on_tab(step))
                return "break"
            return _go

        ent.bind("<Return>", done)
        ent.bind("<KP_Enter>", done)
        ent.bind("<Escape>", lambda _e: close())
        ent.bind("<Tab>", tab(+1))       # Excel-style: Tab commits + jumps to next cell
        ent.bind("<Shift-Tab>", tab(-1))
        ent.bind("<FocusOut>", lambda _e: done())

    def del_demand(self):
        for s in sorted([self.dtree.index(x) for x in self.dtree.selection()], reverse=True):
            if 0 <= s < len(self.demands):
                del self.demands[s]
        self.refresh_all()

    def del_stock(self):
        for s in sorted([self.stree.index(x) for x in self.stree.selection()], reverse=True):
            if 0 <= s < len(self.stocks):
                del self.stocks[s]
        self.refresh_all()

    def on_d_click(self, evt):
        # single click on Rot / Grain toggles it — no separate toggle button
        row = self.dtree.identify_row(evt.y)
        col = self.dtree.identify_column(evt.x)
        if not row:
            return
        i = self.dtree.index(row)
        if i >= len(self.demands):
            return
        if col == "#5":
            self.demands[i]["rot"] = not self.demands[i].get("rot", True)
            if self.demands[i]["rot"]:
                self.demands[i]["grain"] = False
            self.refresh_all()
        elif col == "#6":
            self.demands[i]["grain"] = not self.demands[i].get("grain", False)
            if self.demands[i]["grain"]:
                self.demands[i]["rot"] = False
            self.refresh_all()

    def _edit_demand_cell(self, i, col):
        # open editor for demands[i] (or the + placeholder row) at column col
        if col not in self.D_EDIT_COLS:
            return
        kids = self.dtree.get_children()
        if not (0 <= i < len(kids)):
            return
        row = kids[i]
        is_new = i >= len(self.demands)
        cur = ""
        if not is_new:
            d = self.demands[i]
            cur = {"#2": f"{d['L']:g}", "#3": f"{d['W']:g}", "#4": str(d["qty"]),
                   "#7": d.get("material", ""), "#8": d.get("label", "")}.get(col, "")

        def commit(val):
            val = val.strip()
            try:
                if self.dtree.index(row) >= len(self.demands):
                    nd = {"L": 300.0, "W": 300.0, "qty": 1, "rot": True,
                          "grain": False, "material": "", "label": ""}
                    if col == "#2":
                        nd["L"] = self._num(val, "Length")
                    elif col == "#3":
                        nd["W"] = self._num(val, "Width")
                    elif col == "#4":
                        nd["qty"] = self._int(val, "Qty")
                    elif col == "#7":
                        nd["material"] = val
                    elif col == "#8":
                        nd["label"] = val
                    self.demands.append(nd)
                else:
                    d = self.demands[self.dtree.index(row)]
                    if col == "#2":
                        d["L"] = self._num(val, "Length")
                    elif col == "#3":
                        d["W"] = self._num(val, "Width")
                    elif col == "#4":
                        d["qty"] = self._int(val, "Qty")
                    elif col == "#7":
                        d["material"] = val
                    elif col == "#8":
                        d["label"] = val
            except ValueError as e:
                messagebox.showerror("Invalid value", str(e))
            self.refresh_all()

        def on_tab(step):
            cols = self.D_EDIT_COLS
            j = cols.index(col) + step
            ni = i
            if j >= len(cols):  # Tab past last cell -> first cell of next row
                j, ni = 0, i + 1
            elif j < 0:         # Shift-Tab past first cell -> last cell of prev row
                j, ni = len(cols) - 1, i - 1
            if 0 <= ni <= len(self.demands):  # include + placeholder row
                self._edit_demand_cell(ni, cols[j])

        self._cell_editor(self.dtree, row, col, cur, commit, on_tab)

    def on_d_edit(self, evt):
        row = self.dtree.identify_row(evt.y)
        col = self.dtree.identify_column(evt.x)
        if not row or col in ("#1", "#5", "#6"):  # # / Rot / Grain: click toggles, nothing to type
            return
        self._edit_demand_cell(self.dtree.index(row), col)

    def _edit_stock_cell(self, i, col):
        if col not in self.S_EDIT_COLS:
            return
        kids = self.stree.get_children()
        if not (0 <= i < len(kids)):
            return
        row = kids[i]
        is_new = i >= len(self.stocks)
        cur = ""
        if not is_new:
            s = self.stocks[i]
            cur = {"#2": f"{s['L']:g}", "#3": f"{s['W']:g}", "#4": str(s["qty"]),
                   "#5": s.get("material", ""), "#6": f"{s.get('price', 0):g}"}.get(col, "")

        def commit(val):
            val = val.strip()
            try:
                if self.stree.index(row) >= len(self.stocks):
                    ns = {"L": 1250.0, "W": 2500.0, "qty": 1, "material": "",
                          "label": "", "price": 0.0}
                    if col == "#2":
                        ns["L"] = self._num(val, "Length")
                    elif col == "#3":
                        ns["W"] = self._num(val, "Width")
                    elif col == "#4":
                        ns["qty"] = self._int(val, "Qty")
                    elif col == "#5":
                        ns["material"] = val
                    elif col == "#6":
                        ns["price"] = self._num(val, "Price", allow_zero=True)
                    self.stocks.append(ns)
                else:
                    s = self.stocks[self.stree.index(row)]
                    if col == "#2":
                        s["L"] = self._num(val, "Length")
                    elif col == "#3":
                        s["W"] = self._num(val, "Width")
                    elif col == "#4":
                        s["qty"] = self._int(val, "Qty")
                    elif col == "#5":
                        s["material"] = val
                    elif col == "#6":
                        s["price"] = self._num(val, "Price", allow_zero=True)
            except ValueError as e:
                messagebox.showerror("Invalid value", str(e))
            self.refresh_all()

        def on_tab(step):
            cols = self.S_EDIT_COLS
            j = cols.index(col) + step
            ni = i
            if j >= len(cols):
                j, ni = 0, i + 1
            elif j < 0:
                j, ni = len(cols) - 1, i - 1
            if 0 <= ni <= len(self.stocks):
                self._edit_stock_cell(ni, cols[j])

        self._cell_editor(self.stree, row, col, cur, commit, on_tab)

    def on_s_edit(self, evt):
        row = self.stree.identify_row(evt.y)
        col = self.stree.identify_column(evt.x)
        if not row or col == "#1":
            return
        self._edit_stock_cell(self.stree.index(row), col)

    def refresh_all(self):
        for r in self.dtree.get_children():
            self.dtree.delete(r)
        for i, d in enumerate(self.demands, 1):
            self.dtree.insert("", tk.END, values=(i, f"{d['L']:g}", f"{d['W']:g}", d["qty"],
                                                  "Y" if d.get("rot") else "N",
                                                  "Y" if d.get("grain") else "-",
                                                  d.get("material", ""), d.get("label", "")),
                              tags=("even" if i % 2 else "odd",))
        self.dtree.insert("", tk.END, values=("+", "type here…", "", "", "", "", "", ""),
                          tags=("addrow",))
        for r in self.stree.get_children():
            self.stree.delete(r)
        for i, s in enumerate(self.stocks, 1):
            self.stree.insert("", tk.END, values=(i, f"{s['L']:g}", f"{s['W']:g}", s["qty"],
                                                  s.get("material", ""), f"{s.get('price', 0):g}"),
                              tags=("even" if i % 2 else "odd",))
        self.stree.insert("", tk.END, values=("+", "type here…", "", "", "", ""),
                          tags=("addrow",))

    # ---------- run ----------
    def settings(self):
        try:
            k = self._num(self.kerf.get(), "Kerf", allow_zero=True)
            t = self._num(self.trim.get(), "Trim", allow_zero=True)
        except ValueError as e:
            messagebox.showerror("Invalid setting", str(e))
            return None
        return k, t

    def run(self):
        st = self.settings()
        if st is None:
            return
        kerf, trim = st
        if not self.demands:
            return messagebox.showwarning("No demand", "Add at least one DEMAND row.")
        if not self.stocks:
            return messagebox.showwarning("No stock", "Add at least one STOCK row.")
        sheets, info = SheetPacker.optimize(self.demands, self.stocks, kerf, trim)
        if sheets is None:
            self.sheets = []
            self.st_msg.config(text=info)
            return messagebox.showerror("Cannot optimize", info)
        self.sheets = sheets
        self.stock_used = info.get("stock_used", [])
        self.cur_sheet = 0
        names = [f"Sheet{i+1} ({sh['sw']:g}x{sh['sh']:g})" for i, sh in enumerate(sheets)]
        names.append("Statistics: 2D")
        self.sheet_combo["values"] = names
        self.sheet_combo.current(0)
        self.update_status()
        self.redraw()
        self.summary_popup()

    def totals(self):
        tot_sheet = sum(sh["sw"] * sh["sh"] for sh in self.sheets)
        tot_part = sum(d["L"] * d["W"] * d["qty"] for d in self.demands)
        util = tot_part / tot_sheet * 100 if tot_sheet else 0
        cost = sum(self.stocks[sh["stock_idx"]].get("price", 0) for sh in self.sheets)
        return tot_sheet, tot_part, util, cost

    def update_status(self):
        if not self.sheets:
            return
        _, _, util, cost = self.totals()
        self.st_util.config(text=f"Utilization:{util:.3f} %")
        self.st_waste.config(text=f"Waste:{100-util:.2f} %")
        self.st_qty.config(text=f"Quantity:{len(self.sheets)}")
        self.st_cost.config(text=f"Cost:{cost:,.0f}")
        self.st_msg.config(text=f"Sheets:{len(self.sheets)} Parts:{sum(d['qty'] for d in self.demands)}")

    def material_stats(self):
        """Material-wise RM usage for the current nesting. Returns (total, rows)."""
        groups = {}
        for sh in self.sheets:
            s = self.stocks[sh["stock_idx"]]
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
        rows = []
        for mat in sorted(groups):
            g = groups[mat]
            u = g["part_area"] / g["sheet_area"] * 100 if g["sheet_area"] else 0
            rows.append({"material": mat, "sheets": g["sheets"],
                         "rm_sqm": g["sheet_area"] / 1e6, "pcs": g["pcs"],
                         "util": u, "waste": 100 - u, "cost": g["cost"]})
        _, _, tutil, tcost = self.totals()
        total = {"sheets": len(self.sheets),
                 "rm_sqm": sum(sh["sw"] * sh["sh"] for sh in self.sheets) / 1e6,
                 "pcs": sum(d["qty"] for d in self.demands),
                 "util": tutil, "waste": 100 - tutil, "cost": tcost}
        return total, rows

    def rm_breakdown(self):
        """Per-material sections, each listing stock sizes used + qty.
        Returns (total, [blocks]) with block = {material, sheets, rm_sqm,
        pcs, util, cost, sizes:[{size, qty, sqm}]}."""
        total, mrows = self.material_stats()
        used = list(getattr(self, "stock_used", []) or [0] * len(self.stocks))
        blocks = []
        for r in mrows:
            mat = r["material"]
            sizes = []
            for i, s in enumerate(self.stocks):
                sm = (s.get("material", "") or "").strip() or "— Unspecified —"
                u = used[i] if i < len(used) else 0
                if u > 0 and sm == mat:
                    sizes.append({"size": f"{s['L']:g} x {s['W']:g}", "qty": u,
                                  "sqm": s["L"] * s["W"] * u / 1e6})
            blocks.append({"material": mat, "sheets": r["sheets"], "rm_sqm": r["rm_sqm"],
                           "pcs": r["pcs"], "util": r["util"], "cost": r["cost"], "sizes": sizes})
        return total, blocks

    def summary_popup(self):
        # pop-up summary of TOTAL RM used, separated per material with sheet sizes
        total, blocks = self.rm_breakdown()
        pop = tk.Toplevel(self.root)
        pop.title("Nesting complete — RM summary")
        pop.geometry("600x480")
        pop.transient(self.root)
        tk.Label(pop, text="✓ Nesting complete — Total RM used",
                 bg=self.NAVY, fg="white", font=("Segoe UI", 11, "bold"),
                 anchor=tk.W, padx=10, pady=6).pack(fill=tk.X)
        frm = ttk.Frame(pop)
        frm.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        txt = tk.Text(frm, wrap=tk.WORD, font=("Consolas", 10))
        sb = ttk.Scrollbar(frm, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        L = [f"TOTAL RM USED : {total['sheets']} sheets  |  {total['rm_sqm']:.3f} m²  |  "
             f"{total['pcs']} pcs",
             f"Utilization   : {total['util']:.2f} %   |   Waste : {total['waste']:.2f} %",
             f"Total cost    : {total['cost']:,.0f}", ""]
        for b in blocks:
            L.append("=" * 56)
            L.append(f"MATERIAL : {b['material']}  —  {b['sheets']} sheets  |  "
                     f"{b['rm_sqm']:.3f} m²  |  {b['pcs']} pcs")
            L.append(f"           Util {b['util']:.2f}%  |  Cost {b['cost']:,.0f}")
            L.append("  SHEETS USED:")
            for sz in b["sizes"]:
                L.append(f"    {sz['size']}   × {sz['qty']}  =  {sz['sqm']:.3f} m²")
            L.append("")
        txt.insert("1.0", "\n".join(L))
        txt.configure(state=tk.DISABLED)
        bf = ttk.Frame(pop)
        bf.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(bf, text="OK", command=pop.destroy).pack(side=tk.RIGHT, padx=4)

        def goto_stats():
            pop.destroy()
            self.sheet_combo.current(len(self.sheets))
            self.on_sheet_pick()
        ttk.Button(bf, text="Open Statistics: 2D", command=goto_stats).pack(side=tk.RIGHT, padx=4)
        pop.grab_set()
        pop.focus_set()

    def prev_sheet(self):
        if self.sheets and self.cur_sheet > 0:
            self.cur_sheet -= 1
            self.sheet_combo.current(self.cur_sheet)
            self.redraw()

    def next_sheet(self):
        if self.sheets and self.cur_sheet < len(self.sheets) - 1:
            self.cur_sheet += 1
            self.sheet_combo.current(self.cur_sheet)
            self.redraw()

    def on_sheet_pick(self, _e=None):
        idx = self.sheet_combo.current()
        if 0 <= idx < len(self.sheets):
            self.cur_sheet = idx
            self.redraw()
        elif idx == len(self.sheets):
            self.show_stats()

    def show_stats(self):
        self.canvas.delete("all")
        _, _, util, cost = self.totals()
        total, blocks = self.rm_breakdown()
        lines = [f"Sheets: {len(self.sheets)}  Parts: {sum(d['qty'] for d in self.demands)}",
                 f"Utilization: {util:.3f} %   Waste: {100-util:.3f} %   Cost: {cost:,.0f}", "",
                 "MATERIAL-WISE RM REPORT", ""]
        for b in blocks:
            lines.append(f"[ {b['material']} ]  {b['sheets']} sheets  {b['rm_sqm']:.3f} m²  "
                         f"{b['pcs']} pcs  Util {b['util']:.2f}%  Cost {b['cost']:,.0f}")
            for sz in b["sizes"]:
                lines.append(f"    {sz['size']}  x {sz['qty']}  =  {sz['sqm']:.3f} m²")
            lines.append("")
        lines.append(f"TOTAL  {total['sheets']} sheets  {total['rm_sqm']:.3f} m²  "
                     f"{total['pcs']} pcs  Util {total['util']:.2f}%  Cost {total['cost']:,.0f}")
        lines.append("")
        for i, sh in enumerate(self.sheets, 1):
            pa = sum(w * h for (_, _, w, h, _, _) in sh["places"])
            u = pa / (sh["sw"] * sh["sh"]) * 100
            lines.append(f"Sheet{i}: {sh['sw']:g}x{sh['sh']:g} — {len(sh['places'])} pcs — {u:.1f}%")
        self.canvas.create_text(20, 20, anchor=tk.NW, text="\n".join(lines), font=("Consolas", 11))
        self.sheet_info.config(text="Statistics")
        for r in self.ctree.get_children():
            self.ctree.delete(r)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    # ---------- draw ----------
    def redraw(self):
        for r in self.ctree.get_children():
            self.ctree.delete(r)
        if not self.sheets:
            self.canvas.delete("all")
            self.canvas.create_text(30, 30, anchor=tk.NW, text="Press ▶ Start to generate the cutting plan.",
                                    font=("Segoe UI", 11), fill="gray")
            return
        if self.sheet_combo.current() == len(self.sheets):
            return self.show_stats()
        sh = self.sheets[self.cur_sheet]
        sw, sh_h = sh["sw"], sh["sh"]
        self.canvas.delete("all")
        z = max(0.3, min(2.0, float(self.zoom.get())))
        cw = max(600, self.canvas.winfo_width() - 20)
        chh = max(500, self.canvas.winfo_height() - 20)
        sc = min((cw - 140) / sw, (chh - 120) / sh_h) * z
        sc = max(sc, 0.03)
        ox, oy = 90, 40
        W, H = sw * sc, sh_h * sc
        self.canvas.create_rectangle(ox, oy, ox + W, oy + H, fill="#f2f2f2",
                                         outline=self.NAVY, width=2)

        def hatch(x1, y1, x2, y2):
            if x2 - x1 < 2 or y2 - y1 < 2:
                return
            self.canvas.create_rectangle(x1, y1, x2, y2, outline="#8a8a8a", dash=(3, 3))
            step = 9
            x = x1 - (y2 - y1)
            while x < x2:
                self.canvas.create_line(max(x, x1), y2, min(x + (y2 - y1), x2),
                                        y1 if x + (y2 - y1) <= x2 else y2 - (x2 - x), fill="#8a8a8a")
                x += step

        def tag(text, tx, ty, font, fill="#111111"):
            # text with white backing so hatch lines / borders never hide it
            tid = self.canvas.create_text(tx, ty, text=text, font=font, fill=fill)
            try:
                bx1, by1, bx2, by2 = self.canvas.bbox(tid)
                self.canvas.create_rectangle(bx1 - 2, by1 - 1, bx2 + 2, by2 + 1,
                                             fill="white", outline="")
                self.canvas.tag_raise(tid)
            except Exception:
                pass
            return tid

        colors = ["#ffffff", "#ffd9d9", "#d9eaff", "#d9f2d9", "#fff3c4", "#e8d9ff", "#e0f7fa"]
        for idx, (x, y, w, h, rot, ref) in enumerate(sh["places"]):
            d = self.demands[ref]
            x1, y1 = ox + x * sc, oy + y * sc
            x2, y2 = ox + (x + w) * sc, oy + (y + h) * sc
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=colors[(ref + 1) % len(colors)],
                                         outline="#B00020" if idx == 0 else "#333333",
                                         width=2 if idx == 0 else 1)
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            pw, ph = x2 - x1, y2 - y1
            if self.opt_size.get() and pw > 36 and ph > 30:
                tag(f"{w:g}", cx, y1 + 11, ("Segoe UI", 9))
                if ph > 44:
                    tag(f"{h:g}", x1 + 17, cy, ("Segoe UI", 9))
            if self.opt_label.get() and d.get("label") and pw > 50 and ph > 40:
                tag(d["label"], cx, cy, ("Segoe UI", 8, "bold"))
            if self.opt_index.get() and pw > 26 and ph > 26:
                tag(f"{idx+1}", x2 - 12, y2 - 10, ("Segoe UI", 7), fill="#444444")
            self.ctree.insert("", tk.END, values=(idx + 1, f"{d['L']:g}x{d['W']:g}",
                                                  f"{x:.0f}", f"{y:.0f}",
                                                  "Yes" if rot else "No", d.get("label", "")))
        if self.opt_waste.get():
            st = self.settings() or (0, 0)
            trim_v = st[1]
            # true leftover free-rects from MaxRects nesting
            for (fx, fy, fw, fh) in sh.get("free", []):
                rx1 = ox + (fx + trim_v) * sc
                ry1 = oy + (fy + trim_v) * sc
                rx2 = rx1 + fw * sc
                ry2 = ry1 + fh * sc
                if rx2 - rx1 > 3 and ry2 - ry1 > 3:
                    hatch(rx1, ry1, rx2, ry2)
        self.canvas.create_text(ox + W / 2, oy - 22, text=f"{sw:g}", font=("Segoe UI", 11, "bold"))
        self.canvas.create_text(ox - 55, oy + H / 2, text=f"{sh_h:g}", font=("Segoe UI", 11, "bold"))
        qty = sum(1 for s in self.sheets
                  if sorted((round(w, 2), round(h, 2)) for (_, _, w, h, _, _) in s["places"]) ==
                  sorted((round(w, 2), round(h, 2)) for (_, _, w, h, _, _) in sh["places"]))
        self.canvas.create_text(ox + W + 60, oy + H / 2, text=f"Quantity = {qty}",
                                font=("Segoe UI", 10), angle=90)
        pa = sum(w * h for (_, _, w, h, _, _) in sh["places"])
        u = pa / (sw * sh_h) * 100
        self.sheet_info.config(text=f"{sw:g} x {sh_h:g} — {len(sh['places'])} pcs — Util {u:.2f}%")
        self.canvas.configure(scrollregion=(0, 0, ox + W + 140, oy + H + 80))

    # ---------- files ----------
    def new_project(self):
        self.demands, self.stocks, self.sheets = [], [], []
        self.cur_sheet = 0
        self.sheet_combo.set("")
        self.sheet_combo["values"] = []
        self.refresh_all()
        self.redraw()

    def save_project(self):
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if p:
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"demands": self.demands, "stocks": self.stocks,
                           "kerf": self.kerf.get(), "trim": self.trim.get()}, f, indent=2)
            self.st_msg.config(text=f"Saved {p}")

    def open_project(self):
        p = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if p:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            self.demands = d.get("demands", [])
            self.stocks = d.get("stocks", [])
            self.kerf.set(str(d.get("kerf", "3")))
            self.trim.set(str(d.get("trim", "0")))
            self.sheets = []
            self.refresh_all()
            self.redraw()

    def import_demand(self):
        p = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not p:
            return
        with open(p, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                try:
                    self.demands.append({
                        "L": float(row.get("Length", row.get("L", 0))),
                        "W": float(row.get("Width", row.get("W", 0))),
                        "qty": int(float(row.get("Quantity", row.get("Qty", 1)))),
                        "rot": str(row.get("Rotation", "Y")).strip().upper() not in ("N", "0", "NO", "FALSE"),
                        "grain": str(row.get("Grain", "")).strip().upper() in ("Y", "1", "YES", "TRUE"),
                        "material": row.get("Material", ""), "label": row.get("Label", "")})
                except Exception:
                    continue
        self.refresh_all()

    def import_stock(self):
        p = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not p:
            return
        with open(p, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                try:
                    self.stocks.append({
                        "L": float(row.get("Length", row.get("L", 0))),
                        "W": float(row.get("Width", row.get("W", 0))),
                        "qty": int(float(row.get("Quantity", row.get("Qty", 1)))),
                        "material": row.get("Material", ""), "label": row.get("Label", ""),
                        "price": float(row.get("Price", 0) or 0)})
                except Exception:
                    continue
        self.refresh_all()

    def import_drawing(self, kind):
        # read a PDF / DXF drawing and auto-fill DEMAND with detected part sizes
        if kind == "PDF":
            p = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        else:
            p = filedialog.askopenfilename(filetypes=[("DXF files", "*.dxf")])
        if not p:
            return
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Read {kind} → DEMAND")
        dlg.geometry("360x250")
        dlg.transient(self.root)
        sc_v = tk.StringVar(value="1.0")
        md_v = tk.StringVar(value="10")
        mat_v = tk.StringVar(value="")
        rot_v = tk.BooleanVar(value=True)
        ttk.Label(dlg, text=f"File: {p[-55:]}", font=("Segoe UI", 8),
                  foreground="#595959").pack(anchor=tk.W, padx=10, pady=(8, 2))
        body = ttk.Frame(dlg)
        body.pack(fill=tk.X, padx=10, pady=4)
        ttk.Label(body, text="Scale (drawing unit → mm):").grid(row=0, column=0, sticky=tk.W, pady=3)
        ttk.Entry(body, textvariable=sc_v, width=10).grid(row=0, column=1, padx=6)
        ttk.Label(body, text="Ignore parts smaller than (mm):").grid(row=1, column=0, sticky=tk.W, pady=3)
        ttk.Entry(body, textvariable=md_v, width=10).grid(row=1, column=1, padx=6)
        ttk.Label(body, text="Material for all parts:").grid(row=2, column=0, sticky=tk.W, pady=3)
        ttk.Entry(body, textvariable=mat_v, width=10).grid(row=2, column=1, padx=6)
        ttk.Checkbutton(body, text="Allow Rotation", variable=rot_v).grid(row=3, column=0,
                                                                          sticky=tk.W, pady=3)
        if kind == "PDF":
            ttk.Label(dlg, text="Tip: CAD PDF in points? use scale 0.3528. Scanned PDFs have\n"
                                "no vectors — use DXF for those.",
                      font=("Segoe UI", 8), foreground="#595959").pack(padx=10, pady=2)
        else:
            ttk.Label(dlg, text="Closed outlines + circles become parts; SHEET / DIM /\n"
                                "TEXT / HATCH layers are ignored.",
                      font=("Segoe UI", 8), foreground="#595959").pack(padx=10, pady=2)

        def go():
            try:
                scale = float(sc_v.get())
                mind = float(md_v.get())
                if scale <= 0 or mind < 0:
                    raise ValueError
            except ValueError:
                return messagebox.showerror("Invalid", "Scale must be > 0, min size >= 0.")
            try:
                if kind == "PDF":
                    found = parse_pdf_parts(p, scale, mind)
                else:
                    found = parse_dxf_parts(p, scale, mind)
            except ImportError:
                return messagebox.showerror("Missing",
                                            "PDF reading needs PyMuPDF (pip install pymupdf).")
            except Exception as e:
                return messagebox.showerror(f"{kind} read failed", str(e))
            if not found:
                return messagebox.showwarning("Nothing found",
                                              "No usable part outlines detected.\n"
                                              "Check scale / min-size, or use DXF for scans.")
            for L, W, q in found:
                self.demands.append({"L": L, "W": W, "qty": q, "rot": bool(rot_v.get()),
                                     "grain": False, "material": mat_v.get().strip(), "label": ""})
            self.refresh_all()
            dlg.destroy()
            messagebox.showinfo(f"{kind} → DEMAND",
                                f"Auto-added {len(found)} size(s), "
                                f"{sum(q for _, _, q in found)} pcs to DEMAND.\n"
                                f"Verify sizes in the table, then press ▶ Start.")

        bf = ttk.Frame(dlg)
        bf.pack(fill=tk.X, padx=10, pady=6)
        ttk.Button(bf, text="Read + Add", command=go).pack(side=tk.RIGHT, padx=3)
        ttk.Button(bf, text="Cancel", command=dlg.destroy).pack(side=tk.RIGHT)
        dlg.grab_set()
        dlg.focus_set()

    def export_report(self):
        if not self.sheets:
            return messagebox.showinfo("Nothing", "Run ▶ Start first.")
        p = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if not p:
            return
        _, _, util, cost = self.totals()
        st = self.settings() or (0, 0)
        with open(p, "w", encoding="utf-8") as f:
            f.write(f"{APP_TITLE} — cutting report (offline)\n")
            f.write(f"Kerf={st[0]:g}mm Trim={st[1]:g}mm | Sheets:{len(self.sheets)} "
                    f"Util:{util:.2f}% Waste:{100-util:.2f}% Cost:{cost:,.0f}\n")
            _tot, _blocks = self.rm_breakdown()
            f.write("\nMATERIAL-WISE RM REPORT\n")
            for _b in _blocks:
                f.write(f"  [{_b['material']}] {_b['sheets']} sheets, {_b['rm_sqm']:.3f} m², "
                        f"{_b['pcs']} pcs, Util {_b['util']:.2f}%, Cost {_b['cost']:,.0f}\n")
                for _sz in _b["sizes"]:
                    f.write(f"      {_sz['size']} x {_sz['qty']} = {_sz['sqm']:.3f} m²\n")
            f.write("\nDEMAND\n")
            for i, d in enumerate(self.demands, 1):
                f.write(f"  {i}. {d['L']:g}x{d['W']:g}x{d['qty']} rot={'Y' if d.get('rot') else 'N'} "
                        f"grain={'Y' if d.get('grain') else 'N'} mat='{d.get('material','')}' lab='{d.get('label','')}'\n")
            f.write("\nSTOCK\n")
            for i, s in enumerate(self.stocks, 1):
                f.write(f"  {i}. {s['L']:g}x{s['W']:g}x{s['qty']} mat='{s.get('material','')}' price={s.get('price',0):g}\n")
            f.write("\nCUTTING PLAN\n")
            for i, sh in enumerate(self.sheets, 1):
                f.write(f"Sheet{i} ({sh['sw']:g}x{sh['sh']:g}):\n")
                for j, (x, y, w, h, rot, ref) in enumerate(sh["places"], 1):
                    d = self.demands[ref]
                    f.write(f"  [{j}] {d['L']:g}x{d['W']:g} at X={x:.0f} Y={y:.0f}"
                            f"{' ROT' if rot else ''} '{d.get('label','')}'\n")
            f.write(f"\n--\nGenerated by {APP_TITLE} v{APP_VERSION} (offline)\n"
                    f"Developed by {', '.join(DEVELOPERS)}\n")
        self.st_msg.config(text=f"Report saved {p}")

    def export_dxf(self):
        if not self.sheets:
            return messagebox.showinfo("Nothing", "Run ▶ Start first.")
        p = filedialog.asksaveasfilename(defaultextension=".dxf", filetypes=[("DXF", "*.dxf")])
        if not p:
            return
        write_dxf(p, self.sheets, self.demands)
        self.st_msg.config(text=f"DXF saved {p}")

    def show_about(self):
        ab = tk.Toplevel(self.root)
        ab.title(f"About {APP_TITLE}")
        ab.geometry("420x300")
        ab.transient(self.root)
        ab.resizable(False, False)
        tk.Label(ab, text=f"{APP_TITLE}  v{APP_VERSION}", bg=self.NAVY, fg="white",
                 font=("Segoe UI", 14, "bold"), anchor=tk.CENTER,
                 padx=10, pady=12).pack(fill=tk.X)
        tk.Label(ab, text="Offline 2D sheet-cutting (nesting) optimizer",
                 font=("Segoe UI", 10)).pack(pady=(12, 2))
        tk.Label(ab, text="Developed by", font=("Segoe UI", 10, "bold"),
                 foreground="#595959").pack(pady=(10, 2))
        for name in DEVELOPERS:
            tk.Label(ab, text=name, font=("Segoe UI", 11)).pack()
        tk.Label(ab, text="© 2026 Link • 100% offline, no internet needed",
                 font=("Segoe UI", 8), foreground="#595959").pack(pady=(14, 2))
        ttk.Button(ab, text="Close", command=ab.destroy).pack(pady=8)
        ab.grab_set()
        ab.focus_set()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
