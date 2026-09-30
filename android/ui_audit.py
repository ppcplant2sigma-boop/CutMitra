"""Layout audit — proves nothing on screen is clipped or squashed.

The UI complaints that keep coming back ("button label is not proper", "text is
cut off") are all layout bugs: a Label whose texture is taller than its box, a
Button whose text is wider than the button, a widget left with zero height.
This script boots the real app at phone size, walks every tab and reports
exactly that, so the regressions show up on a PC instead of on the shop floor.

    pip install kivy
    python android/ui_audit.py

Exit code is non-zero if anything is clipped, so it doubles as a CI check.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

if not os.path.exists(os.path.join(HERE, "core_nest.py")):
    shutil.copy(os.path.join(HERE, os.pardir, "src", "core_nest.py"), HERE)

from kivy.config import Config            # noqa: E402
Config.set("graphics", "width", "360")    # a small phone, the tightest case
Config.set("graphics", "height", "700")
Config.set("graphics", "resizable", "0")

from kivy.clock import Clock               # noqa: E402
from kivy.core.text import Label as CoreLabel  # noqa: E402
from kivy.metrics import dp                # noqa: E402

import main as m                           # noqa: E402

TABS = ("DEMAND", "STOCK", "RUN", "RESULT", "ABOUT")
problems = []
seen = []


def text_width(txt, font_px, bold=False):
    """Widest rendered line, in pixels."""
    widest = 0
    for line in str(txt).split("\n"):
        cl = CoreLabel(text=line, font_size=font_px, bold=bold)
        cl.refresh()
        widest = max(widest, cl.texture.width)
    return widest


def walk(widget, tab):
    """Report clipped labels, overflowing buttons and zero-size widgets."""
    for w in widget.children:
        if hasattr(w, "children"):
            walk(w, tab)
        if getattr(w, "opacity", 1) == 0:
            continue
        seen.append((tab, type(w).__name__))
        if w.width <= 1 or w.height <= 1:
            problems.append(f"{tab}: {type(w).__name__} "
                            f"{getattr(w, 'text', '')[:24]!r} has no room "
                            f"({w.width:.0f}x{w.height:.0f}) in "
                            f"{type(w.parent).__name__}")
            continue
        label = getattr(w, "text", None)
        if label is None:
            continue
        if isinstance(w, m.Button):
            need = text_width(label, w.font_size, w.bold) + dp(4)
            if need > w.width:
                problems.append(f"{tab}: button {label!r} needs {need:.0f}px "
                                f"but is {w.width:.0f}px wide")
        elif (isinstance(w, m.Label) and w.size_hint_y is None
              and w.texture_size[1] > w.height + dp(2)):
            problems.append(f"{tab}: label {label[:24]!r} needs "
                            f"{w.texture_size[1]:.0f}px but is {w.height:.0f}px high")


def audit(app):
    """TabbedPanel keeps the selected tab's content as its own child, so the
    audit walks the panel — and fails loudly if nothing got attached."""
    tabs = (app.tab_d, app.tab_s, app.tab_r, app.tab_o, app.tab_a)

    def visit(i):
        if i >= len(tabs):
            Clock.schedule_once(lambda _d: finish(app), 0.05)
            return
        app.tabs.switch_to(tabs[i])
        # let Kivy lay the freshly shown tab out before measuring it
        Clock.schedule_once(lambda _d: (check_tab(app, tabs[i], TABS[i]),
                                        visit(i + 1)), 0.05)

    visit(0)


def check_tab(app, tab, name):
    # TabbedPanel puts the selected tab's content inside its own `content` box
    if tab.content not in app.tabs.content.children:
        problems.append(f"{name}: tab content is not shown")
        return
    walk(app.tabs.content, name)


def step(dt):
    app = m.CutMitraApp.get_running_app()
    app.kerf_in.text = "3"
    app.trim_in.text = "0"
    app.start_nesting()
    audit(app)


def finish(app):
    if problems:
        print(f"\n{len(problems)} LAYOUT PROBLEM(S) "
              f"({len(seen)} widgets inspected):", flush=True)
        for p in problems:
            print("  FAIL  " + p, flush=True)
    else:
        print(f"\nLAYOUT OK — {len(seen)} widgets inspected across "
              f"{len(TABS)} tabs, nothing clipped", flush=True)
    app.stop()


class _AuditApp(m.CutMitraApp):
    def build(self):
        root = super().build()
        Clock.schedule_once(step, 1.2)
        return root


_AuditApp().run()
print("UI AUDIT FINISHED", flush=True)
sys.exit(1 if problems else 0)
