# Open the built models in the FreeCAD GUI with the preview palette.
#
# Files built by freecadcmd (headless) carry no colours, so run this inside the FreeCAD
# GUI after a rebuild (Macro > Macros..., or the Python console):
#   p = "case/show.py"; exec(open(p).read(), {"__file__": p})
#
# Preview colours only: black filament is shown dark gray so details stay visible.
# The real filament per part is chosen in Bambu Studio (see PLAN.md).

import math
import os
import FreeCAD as App
import FreeCADGui

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
DOCS = ["HdmiDdcCase", "Keycaps", "Assembly", "AssemblyExploded"]

BLACK = (0.24, 0.25, 0.27)      # "black" filament, shown dark gray
SWITCH = (0.16, 0.16, 0.17)
GRAY = (0.58, 0.59, 0.61)
BLUE = (0.0, 0.45, 0.85)
YELLOW = (1.0, 0.82, 0.1)
STEM = (0.55, 0.35, 0.2)        # Kailh Brown
BOARD = (0.1, 0.1, 0.35)

EXACT = {"Tray": BLACK, "Lid": GRAY, "Plate": BLACK, "Feather": BOARD, "FeatherGhost": BOARD,
         "Label_1a1a1a": BLACK, "Label_00a8e8": BLUE, "StemFitTest": GRAY}
BRASS = (0.80, 0.62, 0.25)
STEEL = (0.72, 0.74, 0.78)
PREFIX = [("Button", BLACK), ("Letter", YELLOW), ("Cap", BLACK), ("Legend", YELLOW),
          ("Switche", SWITCH), ("Stem", STEM), ("Insert", BRASS), ("Screw", STEEL)]
# inlays sit flush with the surface; lift them a hair so the viewer draws them on top
NUDGE = ("Letter", "Legend", "Label_")
TILT_DEG = 8.0


def colour_of(name):
    if name in EXACT:
        return EXACT[name]
    for prefix, colour in PREFIX:
        if name.startswith(prefix):
            return colour
    return None


def show(name):
    path = os.path.join(BUILD, name + ".FCStd")
    if not os.path.exists(path):
        return None
    if name in App.listDocuments():
        App.closeDocument(name)
    doc = App.openDocument(path)
    t = math.radians(TILT_DEG)
    up = App.Vector(0, -math.sin(t), math.cos(t)) * 0.05
    for o in doc.Objects:
        vo = o.ViewObject
        vo.Visibility = True
        c = colour_of(o.Name)
        if c:
            vo.ShapeColor = c
        if o.Name.startswith(NUDGE):
            vo.DisplayMode = "Shaded"   # bold text is many short edges: hide the outlines
        if o.Name.startswith(NUDGE) and name != "Keycaps":
            o.Placement.Base = o.Placement.Base + up
        elif o.Name.startswith("Legend") and name == "Keycaps":
            o.Placement.Base = o.Placement.Base + App.Vector(0, 0, 0.05)
    doc.recompute()
    FreeCADGui.getDocument(name).ActiveView.viewIsometric()
    FreeCADGui.SendMsgToActiveView("ViewFit")
    return doc


if __name__ != "show_lib":
    for n in DOCS:
        show(n)
    if "Assembly" in App.listDocuments():
        App.setActiveDocument("Assembly")
