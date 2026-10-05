# Assembly preview: case + Feather + switches + keycaps, for looking at (not printing).
#
# Reuses case.py and keycaps.py, so it always matches what they export. The switch is
# a simplified MX-style model (housing outline, stem, pins) good enough for fit and
# looks; dimensions are nominal Cherry MX.
#
# Run inside FreeCAD (GUI or freecadcmd):
#   p = "case/assembly.py"; exec(open(p).read(), {"__file__": p})
# Saves case/build/Assembly.FCStd.

import os
import FreeCAD as App
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
V = App.Vector


def load(name, module_name):
    """Execute a sibling script without running its build/export step."""
    p = os.path.join(HERE, name)
    g = {"__file__": p, "__name__": module_name}
    exec(open(p, encoding="utf-8").read(), g)
    return g


case = load("case.py", "case_check")
caps = load("keycaps.py", "keycaps_check")
cadlib = case["cadlib"]

# ---- nominal MX switch, z = 0 at the plate's top face -------------------------
SW_BOTTOM      = (13.9, 5.0)   # housing below the plate: square side, depth
SW_TOP         = (15.6, 11.0, 5.6)  # housing above the plate: base side, top side, height
SW_STEM_TOP    = caps["SW_STEM_TOP"]   # stem top above the plate (at rest)
SW_CROSS_LEN   = caps["STEM_THROW"]    # cross part of the stem, which the keycap grips
SW_TRAVEL      = min(caps["TRAVEL_STOP"], caps["SW_TRAVEL"])  # skirt stop or switch bottom-out
HOUSING_COLOUR = (0.08, 0.08, 0.09)
STEM_COLOUR    = (0.55, 0.35, 0.2)   # Kailh Brown
CAP_COLOUR     = (0.15, 0.15, 0.17)


def rsquare_wire(side, r, z):
    s = side / 2 - r
    f = Part.Face(Part.makePolygon([V(-s, -s, 0), V(s, -s, 0), V(s, s, 0), V(-s, s, 0), V(-s, -s, 0)]))
    w = f.makeOffset2D(r).OuterWire
    w.translate(V(0, 0, z))
    return w


def switch():
    """(housing, stem) in the switch frame."""
    side, depth = SW_BOTTOM
    housing = Part.makeBox(side, side, depth, V(-side / 2, -side / 2, -depth))
    housing = housing.fuse(Part.makeCylinder(2.0, 3.3, V(0, 0, -depth - 3.3)))   # centre post
    for x, y in ((-3.81, 2.54), (2.54, 5.08)):                                   # pins
        housing = housing.fuse(Part.makeCylinder(0.75, 3.3, V(x, y, -depth - 3.3)))
    base, top, h = SW_TOP
    housing = housing.fuse(Part.makeLoft([rsquare_wire(base, 0.8, 0), rsquare_wire(top, 1.5, h)], True))
    # opening the slider (and, on a full press, the keycap's stem) moves down into
    housing = housing.cut(Part.makeBox(7.4, 5.9, h + 1, V(-3.7, -2.95, 0.5)))
    slider = Part.makeBox(7.0, 5.5, SW_STEM_TOP - SW_CROSS_LEN - h + 0.2,
                          V(-3.5, -2.75, h - 0.2))
    z0 = SW_STEM_TOP - SW_CROSS_LEN
    cross = Part.makeBox(4.0, 1.2, SW_CROSS_LEN, V(-2.0, -0.6, z0)).fuse(
        Part.makeBox(1.2, 4.0, SW_CROSS_LEN, V(-0.6, -2.0, z0)))
    return housing, slider.fuse(cross)


def build(pressed=False):
    L = case["Layout"]()
    tray = case["build_tray"](L)
    lid, labels = case["build_lid"](L)
    plate = case["build_plate"](L) if case["SEPARATE_PLATE"] else None
    import math
    T = case["T"]
    u = L.key_y / math.cos(T)
    plate_top = case["LID_T"] - case["KEY_SINK"]                      # plate top, lid frame
    travel = SW_TRAVEL - 0.05 if pressed else 0                          # just short of landing
    cap_z = caps["TRAVEL_STOP"] - travel                                 # skirt bottom

    housing0, stem0 = switch()
    parts = {"switches": [], "stems": [], "caps": [], "legends": []}
    for i, x in enumerate(L.key_x):
        for name, shape, dz in (("switches", housing0, 0), ("stems", stem0, -travel)):
            s = shape.copy()
            s.translate(V(x, u, plate_top + dz))
            parts[name].append(L.to_lid(s))
        body, legend = caps["build_cap"](caps["LEGENDS"][i % len(caps["LEGENDS"])])
        for name, s in (("caps", body), ("legends", legend)):
            s = s.copy()
            s.translate(V(x, u, plate_top + cap_z))
            parts[name].append(L.to_lid(s))
    return L, tray, lid, labels, parts, plate


def build_all():
    L, tray, lid, labels, parts, plate = build()
    doc = cadlib.fresh_document("Assembly")
    cadlib.show(doc, "Tray", tray, (0.35, 0.37, 0.40))
    cadlib.show(doc, "Lid", lid, (0.88, 0.89, 0.90))
    if plate is not None:
        cadlib.show(doc, "Plate", plate, (0.2, 0.2, 0.22))
    if case["BUTTONS"]:
        pins, letters, _ = case["build_buttons"](L)
        for i, (b, t) in enumerate(zip(pins, letters)):
            cadlib.show(doc, f"Button{i}", b, (1.0, 0.48, 0.0))
            cadlib.show(doc, f"Letter{i}", t, (0.1, 0.1, 0.1))
    for colour, s in labels.items():
        cadlib.show(doc, case["label_name"](colour), s, cadlib.hex_rgb(colour))
    cadlib.show(doc, "Feather", case["board_ghost"](L), (0.1, 0.1, 0.12))
    colours = {"switches": HOUSING_COLOUR, "stems": STEM_COLOUR, "caps": CAP_COLOUR,
               "legends": cadlib.hex_rgb("#ffd700")}
    for name, shapes in parts.items():
        for i, s in enumerate(shapes):
            cadlib.show(doc, f"{name[:-1].capitalize()}{i}", s, colours[name])
    doc.recompute()
    doc.saveAs(os.path.join(HERE, "build", "Assembly.FCStd"))

    # keycaps must clear the lid, the switch housings and each other, at rest and
    # pressed to the travel stop
    for pressed in (False, True):
        parts_p = build(pressed)[4] if pressed else parts
        caps_all = Part.makeCompound(parts_p["caps"])
        housings = Part.makeCompound(parts_p["switches"])
        state = "pressed" if pressed else "rest"
        solid = lid if plate is None else lid.fuse(plate)
        print(f"keycaps x lid+plate ({state}):", round(caps_all.common(solid).Volume, 3),
              f"| keycaps x switch housings ({state}):", round(caps_all.common(housings).Volume, 3))
    print(f"keytop height above the lid surface: "
          f"{caps['SW_STEM_TOP'] + caps['SOCKET_CLEAR'] + caps['TOP_T'] - case['KEY_SINK']:.1f} mm")
    a = parts["caps"]
    print("keycap x keycap:", round(sum(a[i].common(a[i + 1]).Volume for i in range(len(a) - 1)), 3))
    return doc


# ---- exploded view: each group lifted (world z, mm) in assembly order -------
EXPLODE = {"tray": 0, "board": 18, "plate": 52, "buttons": 68, "lid": 84, "caps": 122}


def build_exploded():
    """Same parts as the assembly, pulled apart vertically. Saves build/AssemblyExploded.FCStd."""
    L, tray, lid, labels, parts, plate = build()
    pins, letters, _ = case["build_buttons"](L) if case["BUTTONS"] else ([], [], [])
    groups = {
        "tray": [("Tray", tray, (0.35, 0.37, 0.40))],
        "board": [("Feather", case["board_ghost"](L), (0.1, 0.1, 0.12))],
        "plate": ([("Plate", plate, (0.2, 0.2, 0.22))] if plate is not None else [])
                 + [(f"Switche{i}", s, HOUSING_COLOUR) for i, s in enumerate(parts["switches"])]
                 + [(f"Stem{i}", s, STEM_COLOUR) for i, s in enumerate(parts["stems"])],
        "buttons": [(f"Button{i}", s, (1.0, 0.48, 0.0)) for i, s in enumerate(pins)]
                   + [(f"Letter{i}", s, (0.1, 0.1, 0.1)) for i, s in enumerate(letters)],
        "lid": [("Lid", lid, (0.88, 0.89, 0.90))]
               + [(case["label_name"](c), s, cadlib.hex_rgb(c)) for c, s in labels.items()],
        "caps": [(f"Cap{i}", s, CAP_COLOUR) for i, s in enumerate(parts["caps"])]
                + [(f"Legend{i}", s, cadlib.hex_rgb("#ffd700")) for i, s in enumerate(parts["legends"])],
    }
    doc = cadlib.fresh_document("AssemblyExploded")
    for group, items in groups.items():
        for name, shape, colour in items:
            s = shape.copy()
            s.translate(V(0, 0, EXPLODE[group]))
            cadlib.show(doc, name, s, colour)
    doc.recompute()
    doc.saveAs(os.path.join(HERE, "build", "AssemblyExploded.FCStd"))
    return doc


if __name__ != "assembly_check":
    build_all()
    build_exploded()
