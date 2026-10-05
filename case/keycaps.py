# Printable MX keycaps with flush two-colour legends.
#
# DSA-like profile with a flat top, printed face-down: the legend is the first
# LEGEND_DEPTH of the print, inlaid flush in the top. Low-sitting: the top sits just
# above the switch stem, and a deep skirt hides the switch and doubles as the travel
# stop (TRAVEL_STOP mm, past the ~2 mm actuation point). Exported as one 3MF with two
# objects ("Keycaps" and "Legends") — load as a single multi-part object and give
# the Legends part its own filament.
#
# Also exports a stem-fit test: stems with different cross widths. Press each onto a
# switch; use the snuggest one that goes on fully as STEM_CROSS_W.
#
# Run inside FreeCAD (GUI or freecadcmd):
#   p = "case/keycaps.py"; exec(open(p).read(), {"__file__": p})
# Exports to case/export/.

import os
import sys
import FreeCAD as App
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadlib  # noqa: E402

# ---- legends (one cap each) -------------------------------------------------
LEGENDS        = ["HDMI\n1", "HDMI\n2", "DP", "USB\nC"]   # left to right; "\n" = line break

# ---- how the cap sits on an MX switch (heights above the switch plate) --------
SW_STEM_TOP    = 11.6      # MX stem top at rest
STEM_THROW     = 4.0       # length of stem cross that enters the cap (as KeyV2)
SOCKET_CLEAR   = 0.2       # gap between stem top and the inside of the cap top
SW_TRAVEL      = 4.0       # switch's own full travel
TRAVEL_STOP    = 4.0       # skirt bottom above the plate at rest. Below SW_TRAVEL the skirt
                           # lands on the plate and limits travel (Browns actuate at ~2 mm);
                           # at or above it the switch bottoms out on its own

# ---- cap shape --------------------------------------------------------------
BASE           = 18.0      # skirt, square
TOP            = 12.7      # top face, square
BASE_R         = 1.0       # corner radius at the skirt
TOP_R          = 2.0       # corner radius at the top
TOP_FILLET     = 0.8       # rounds the keytop's edge (on the bed when printing; keep small)
WALL           = 1.0       # thin enough that the skirt clears the switch housing
TOP_T          = 1.6       # top thickness (legend is inlaid into this)
STEM_INSET     = SW_STEM_TOP - STEM_THROW - TRAVEL_STOP   # skirt hangs this far below the stem
HEIGHT         = STEM_INSET + STEM_THROW + SOCKET_CLEAR + TOP_T   # skirt bottom to top face

# ---- legend -----------------------------------------------------------------
LEGEND_DEPTH   = 0.6       # 3 layers at 0.2 mm
LEGEND_MAX_H   = 4.0      # text size cap (all caps use the largest size that fits every legend)
LEGEND_MIN_H   = 2.6       # below this, a label with a space wraps to two lines
LEGEND_MARGIN  = 1.0      # from the top face edge (keeps text off the top fillet)
LINE_GAP       = 0.8
LEGEND_FONT    = "ARIALNB.TTF"   # Arial Narrow Bold: lets "HDMI" fit larger
LEGEND_BOLD    = 0.12      # grow the strokes this much each side (letters spaced to match)

# ---- MX stem socket ---------------------------------------------------------
STEM_D         = 5.5
STEM_CROSS_L   = 4.1       # arm length
STEM_CROSS_W   = 1.30      # arm width (tune with the stem-fit test)
FIT_TEST_W     = [1.20, 1.25, 1.30, 1.35, 1.40]

SPACING        = 22.0      # between caps on the print bed
# -----------------------------------------------------------------------------

V = App.Vector


def rrect_wire(size, r, z):
    s = size / 2 - r
    sq = Part.Face(Part.makePolygon([V(-s, -s, 0), V(s, -s, 0), V(s, s, 0), V(-s, s, 0), V(-s, -s, 0)]))
    w = sq.makeOffset2D(r).OuterWire
    w.translate(V(0, 0, z))
    return w


def size_at(z):
    return BASE - (BASE - TOP) * z / HEIGHT


def stem(cross_w, z0, z1):
    s = Part.makeCylinder(STEM_D / 2, z1 - z0, V(0, 0, z0))
    for lx, ly in ((STEM_CROSS_L, cross_w), (cross_w, STEM_CROSS_L)):
        s = s.cut(Part.makeBox(lx, ly, z1 - z0 + 2, V(-lx / 2, -ly / 2, z0 - 1)))
    return s


def legend_height():
    """One text size for every cap: the largest at which all LEGENDS fit."""
    room = TOP - 2 * LEGEND_MARGIN
    return min(cadlib.fit_height(lb.split("\n"), room, room, LEGEND_FONT, LINE_GAP, LEGEND_MAX_H,
                                 LEGEND_BOLD)
               for lb in LEGENDS)


def legend_solid(label):
    """Legend text centred at the origin, z from 0 to LEGEND_DEPTH."""
    room = TOP - 2 * LEGEND_MARGIN
    return cadlib.fit_text(label, room, room, LEGEND_DEPTH, LEGEND_FONT, min_h=LEGEND_MIN_H,
                           line_gap=LINE_GAP, line_max_h=LEGEND_MAX_H, height=legend_height(),
                           bold=LEGEND_BOLD)


def build_cap(label):
    """Returns (body, legend), modelled upright: skirt at z=0, top face at z=HEIGHT."""
    outer = Part.makeLoft([rrect_wire(BASE, BASE_R, 0), rrect_wire(TOP, TOP_R, HEIGHT)], True)
    if TOP_FILLET > 0:
        top = max(outer.Faces, key=lambda f: f.CenterOfMass.z)
        outer = outer.makeFillet(TOP_FILLET, top.Edges)
    inner_top = HEIGHT - TOP_T
    ri = 0.3
    inner = Part.makeLoft([rrect_wire(BASE - 2 * WALL, ri, -0.1),
                           rrect_wire(size_at(inner_top) - 2 * WALL, ri, inner_top)], True)
    body = outer.cut(inner).fuse(stem(STEM_CROSS_W, STEM_INSET, inner_top + 0.1))

    legend = legend_solid(label)
    legend.translate(V(0, 0, HEIGHT - LEGEND_DEPTH))
    legend = legend.common(outer)
    return body.cut(legend).removeSplitter(), legend


def build_fit_test():
    """Stems on a strip, printed upright like the caps. Labels are on the strip."""
    n = len(FIT_TEST_W)
    pitch = 10.0
    strip = Part.makeBox(n * pitch, 14.0, 1.6, V(0, -9.0, 0))
    for i, w in enumerate(FIT_TEST_W):
        x = pitch * (i + 0.5)
        s = stem(w, 1.6, 1.6 + STEM_THROW + SOCKET_CLEAR + 1.0)
        s.translate(V(x, 0, 0))
        strip = strip.fuse(s)
        # open the cross through the strip so the switch stem can pass
        for lx, ly in ((STEM_CROSS_L, w), (w, STEM_CROSS_L)):
            strip = strip.cut(Part.makeBox(lx, ly, 3, V(x - lx / 2, -ly / 2, -1)))
        t = cadlib.text_solid(f"{w:.2f}", 2.2, 0.5)
        cadlib.place_centered(t, x, -6.5, 1.6 - 0.4)
        strip = strip.cut(t)
    return strip.removeSplitter()


def build_all(export=True):
    doc = cadlib.fresh_document("Keycaps")
    bodies, legends = [], []
    for i, label in enumerate(LEGENDS):
        body, legend = build_cap(label)
        for s in (body, legend):
            s.translate(V(i * SPACING, 0, 0))
        bodies.append(body)
        legends.append(legend)
        cadlib.show(doc, f"Cap{i}", body, (0.15, 0.15, 0.17))
        cadlib.show(doc, f"Legend{i}", legend, (0.95, 0.95, 0.95))
    test = build_fit_test()
    test.translate(V(0, -30, 0))
    cadlib.show(doc, "StemFitTest", test, (0.6, 0.6, 0.6))
    doc.recompute()

    if export:
        out = os.path.join(HERE, "export")
        body_all = Part.makeCompound([face_down(b) for b in bodies])
        legend_all = Part.makeCompound([face_down(lg) for lg in legends])
        cadlib.export_parts([("Keycaps", body_all), ("Legends", legend_all)], out, "keycaps")
        cadlib.export_mesh(test, out, "stem-fit-test")
    print("keycaps:", ", ".join(lb.replace("\n", " ") for lb in LEGENDS),
          f"| text {legend_height():.2f} mm | valid:",
          all(b.isValid() for b in bodies), all(l.isValid() for l in legends))
    return bodies, legends, test


def face_down(shape):
    """Flip about the cap's mid-height so the top face lands on z = 0. Bodies and
    legends get the same transform, so they stay aligned in the 3MF."""
    s = shape.copy()
    s.rotate(V(0, 0, HEIGHT / 2), V(1, 0, 0), 180)
    return s


if __name__ != "keycaps_check":
    BODIES, LEGEND_SOLIDS, FIT = build_all()
