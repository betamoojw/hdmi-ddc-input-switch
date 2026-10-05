# Render the guide and README pictures in the FreeCAD GUI (saveImage needs the GUI).
# First, headless:  freecadcmd case/assembly.py  and  freecadcmd case/steps.py
# Then in the FreeCAD Python console:
#   p = "case/render.py"; exec(open(p).read(), {"__file__": p})
# Writes PNGs to web/images/.

import os
import FreeCAD as App
import FreeCADGui

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "web", "images")
V = App.Vector

lib = {"__file__": os.path.join(HERE, "show.py"), "__name__": "show_lib"}
exec(open(lib["__file__"], encoding="utf-8").read(), lib)

BIG, SMALL = (2400, 1600), (1800, 1200)
ISO = V(-1, 1, -1)                     # FreeCAD's isometric: from the front right, above

# (document, output file, camera look direction (where the camera points), size,
#  only show objects whose name starts with one of these; None = everything)
SHOTS = [
    ("Assembly", "01-assembled.png", ISO, BIG, None),
    ("AssemblyExploded", "02-exploded.png", ISO, BIG, None),
    ("Assembly", "03-three-quarter.png", V(-0.3, 0.8, -0.52), BIG, None),
    ("HdmiDdcCase", "04-lid-underside.png", V(0.45, 0.6, 0.66), BIG, ("Lid",)),
    ("Step1", "step1-tray-inserts.png", V(0.45, 0.65, -0.62), SMALL, None),  # from above, front-left
    ("Step2", "step2-lid-inserts.png", V(0.35, -0.45, 0.82), SMALL, None),   # from below and behind
    ("Step3", "step3-board.png", V(0.45, 0.65, -0.62), SMALL, None),
    ("Step4", "step4-plate-buttons.png", ISO, SMALL, None),
    ("Step5", "step5-close-up.png", V(-0.45, -0.70, 0.55), SMALL, None),     # from below and behind
]

# light gradient background for the pictures (the user's own setting is restored after)
BG_TOP, BG_BOTTOM = (0xd3, 0xd6, 0xdb), (0xf5, 0xf5, 0xf7)


def packed(rgb):
    r, g, b = rgb
    return (r << 24) | (g << 16) | (b << 8) | 0xFF


def look_at(view, look):
    """Point the camera along `look` with world +z as screen-up."""
    look = V(look); look.normalize()
    zc = look * -1
    up = V(0, 0, 1)
    xc = up.cross(zc); xc.normalize()
    yc = zc.cross(xc)
    m = App.Matrix(xc.x, yc.x, zc.x, 0, xc.y, yc.y, zc.y, 0, xc.z, yc.z, zc.z, 0, 0, 0, 0, 1)
    view.setCameraType("Orthographic")
    view.setCameraOrientation(App.Rotation(m), False)   # no animation: save the final view
    view.fitAll()
    FreeCADGui.updateGui()


prefs = App.ParamGet("User parameter:BaseApp/Preferences/View")
saved = {k: prefs.GetBool(k, d) for k, d in (("UseNavigationAnimations", True), ("Simple", True),
                                             ("Gradient", False), ("RadialGradient", False))}
saved_cols = {k: prefs.GetUnsigned(k, 0) for k in ("BackgroundColor2", "BackgroundColor3")}
# view-change animations would keep turning the camera after we set it
prefs.SetBool("UseNavigationAnimations", False)
prefs.SetBool("Simple", False); prefs.SetBool("Gradient", True); prefs.SetBool("RadialGradient", False)
prefs.SetUnsigned("BackgroundColor2", packed(BG_TOP))
prefs.SetUnsigned("BackgroundColor3", packed(BG_BOTTOM))

try:
    os.makedirs(OUT, exist_ok=True)
    for doc_name, fname, look, (w, h), only in SHOTS:
        doc = lib["show"](doc_name)
        if doc is None:
            print("missing", doc_name, "- run case/assembly.py and case/steps.py first")
            continue
        if only:
            for o in doc.Objects:
                o.ViewObject.Visibility = o.Name.startswith(only)
        view = FreeCADGui.getDocument(doc_name).ActiveView
        look_at(view, look)
        path = os.path.join(OUT, fname)
        view.saveImage(path, w, h, "Current")
        print("rendered", os.path.normpath(path))
finally:
    for k, v in saved.items():
        prefs.SetBool(k, v)
    for k, v in saved_cols.items():
        prefs.SetUnsigned(k, v)
