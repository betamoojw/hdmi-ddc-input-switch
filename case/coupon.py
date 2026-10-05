# MX switch-plate test coupon.
#
# Prints a strip of switch cutouts at slightly different sizes so you can find
# the one your printer makes a snug, clicking fit. Put the winning value into
# SWITCH_CUTOUT in case.py.
#
# Run inside FreeCAD (GUI or freecadcmd):
#   p = "case/coupon.py"; exec(open(p).read(), {"__file__": p})
# Exports print-ready STL + 3MF (plate face down) to case/export/.

import os
import sys
import FreeCAD as App
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadlib  # noqa: E402

# ---- parameters -------------------------------------------------------------
SIZES        = [13.9, 14.0, 14.1, 14.2]   # square cutout side, mm
KEY_PITCH    = 19.05                       # MX standard
PLATE_T      = 1.5                         # MX clips need 1.5 mm
RIM_W        = 2.0                         # stiffening skirt wall thickness
RIM_H        = 3.0                         # skirt height below the plate
LABEL_STRIP  = 7.0                         # extra depth for size labels
LABEL_H      = 3.5                         # text height
LABEL_DEPTH  = 0.4                         # deboss depth
# -----------------------------------------------------------------------------


def build():
    n = len(SIZES)
    width = n * KEY_PITCH + 2 * RIM_W
    depth = KEY_PITCH + LABEL_STRIP + 2 * RIM_W
    top = RIM_H + PLATE_T

    plate = Part.makeBox(width, depth, PLATE_T, App.Vector(0, 0, RIM_H))
    outer = Part.makeBox(width, depth, RIM_H)
    inner = Part.makeBox(width - 2 * RIM_W, depth - 2 * RIM_W, RIM_H,
                         App.Vector(RIM_W, RIM_W, 0))
    body = plate.fuse(outer.cut(inner))

    cy = RIM_W + LABEL_STRIP + KEY_PITCH / 2
    for i, size in enumerate(SIZES):
        cx = RIM_W + KEY_PITCH * (i + 0.5)
        hole = Part.makeBox(size, size, top + 1,
                            App.Vector(cx - size / 2, cy - size / 2, -0.5))
        body = body.cut(hole)

        label = cadlib.text_solid(f"{size:.1f}", LABEL_H, LABEL_DEPTH + 0.1)
        cadlib.place_centered(label, cx, RIM_W + LABEL_STRIP / 2, top - LABEL_DEPTH)
        body = body.cut(label)

    return body.removeSplitter()


doc = cadlib.fresh_document("SwitchCoupon")
shape = build()
cadlib.show(doc, "Coupon", shape)
doc.recompute()
cadlib.export_mesh(cadlib.flip_for_print(shape), os.path.join(HERE, "export"), "switch-coupon")
print("coupon", shape.BoundBox, "valid", shape.isValid())
