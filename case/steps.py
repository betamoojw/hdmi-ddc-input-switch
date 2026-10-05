# Assembly-step scenes for the build guide: one FreeCAD document per step, parts pulled
# apart along the direction they go together. Reuses case.py / keycaps.py / assembly.py,
# so the pictures always match the printed parts.
#
# Headless:  freecadcmd case/steps.py   -> case/build/Step1..Step5.FCStd
# Then in the FreeCAD GUI run case/render.py to colour them and save the images.

import math
import os
import FreeCAD as App
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
V = App.Vector


def load(name, module_name):
    p = os.path.join(HERE, name)
    g = {"__file__": p, "__name__": module_name}
    exec(open(p, encoding="utf-8").read(), g)
    return g


case = load("case.py", "case_check")
asm = load("assembly.py", "assembly_check")
cadlib = case["cadlib"]
L = case["Layout"]()
T = case["T"]

# ---- hardware models ----------------------------------------------------------
def insert(d, length, axis=V(0, 0, 1)):
    """Heat-set insert: knurled-looking cylinder (rings) with a bore, base at origin."""
    body = Part.makeCylinder(d / 2, length, V(0, 0, 0), axis)
    bore = Part.makeCylinder(d / 2 * 0.55, length + 1, V(0, 0, 0) - axis * 0.5, axis)
    return body.cut(bore)


def screw(d, length, head_d, head_h, axis=V(0, 0, 1)):
    """Button-head screw pointing along `axis` (tip at origin + axis*length)."""
    shaft = Part.makeCylinder(d / 2, length, V(0, 0, 0), axis)
    head = Part.makeCylinder(head_d / 2, head_h, V(0, 0, 0) - axis * head_h, axis)
    return shaft.fuse(head)


def moved(shape, v):
    s = shape.copy()
    s.translate(v)
    return s


def save(name, items):
    """items: [(object name, shape)]; colours are applied by render.py from the names."""
    doc = cadlib.fresh_document(name)
    for n, s in items:
        cadlib.show(doc, n, s)
    doc.recompute()
    doc.saveAs(os.path.join(HERE, "build", name + ".FCStd"))
    print("saved", name, len(items), "objects")


# ---- the parts, assembled ------------------------------------------------------
tray = case["build_tray"](L)
lid, labels = case["build_lid"](L)
plate = case["build_plate"](L)
pins, letters, _ = case["build_buttons"](L)
board = case["board_ghost"](L)
_, _, _, _, parts, _ = asm["build"]()
labels = list(labels.items())

# ---- step 1: tray inserts (M2.5, pressed down into the standoffs) --------------
items = [("Tray", tray)]
for i, (hx, hy) in enumerate(case["PCB_HOLES"]):
    x, y = L.board(hx, hy)
    items.append((f"Insert{i}", moved(insert(3.5, 4.0), V(x, y, L.pcb_bot + 6))))
save("Step1", items)

# ---- step 2: lid inserts (front: up into the posts; rear: into the sideways holes) --
items = [("Lid", lid)] + [(case["label_name"](c), s) for c, s in labels]
for i, (x, y) in enumerate(L.bosses):
    items.append((f"Insert{i}", moved(insert(5.0, 4.0), V(x, y, case["FLOOR"] - 10))))
for i, x in enumerate(L.rear_screws):
    ins = insert(5.0, 4.0, V(0, -1, 0))                    # pressed in toward the front
    items.append((f"Insert{i + 2}", moved(ins, V(x, L.back_in + 10, L.rear_z))))
save("Step2", items)

# ---- step 3: the Feather onto the tray, 4 x M2.5 x 6 ----------------------------
items = [("Tray", tray), ("Feather", moved(board, V(0, 0, 14)))]
for i, (hx, hy) in enumerate(case["PCB_HOLES"]):
    x, y = L.board(hx, hy)
    items.append((f"Screw{i}", moved(screw(2.5, 6, 4.5, 1.6, V(0, 0, -1)), V(x, y, L.pcb_top + 26))))
save("Step3", items)

# ---- step 4: lid upside-down; buttons drop in, then the plate with switches ------
# (modelled in place and pulled apart along the lid's normal, viewed from below)
n = V(0, -math.sin(T), math.cos(T))                         # lid normal (up out of the top)
items = [("Lid", lid)] + [(case["label_name"](c), s) for c, s in labels]
for i, (p, t) in enumerate(zip(pins, letters)):
    items += [(f"Button{i}", moved(p, n * -10)), (f"Letter{i}", moved(t, n * -10))]
items.append(("Plate", moved(plate, n * -36)))
for i, (sw, st) in enumerate(zip(parts["switches"], parts["stems"])):
    items += [(f"Switche{i}", moved(sw, n * -36)), (f"Stem{i}", moved(st, n * -36))]
save("Step4", items)

# ---- step 5: close up: lid onto the tray, 2 screws up through the floor, 2 through
# the back wall, then the keycaps ------------------------------------------------
lift = V(0, 0, 22)
items = [("Tray", tray), ("Feather", board)]
items += [("Lid", moved(lid, lift)), ("Plate", moved(plate, lift))]
items += [(case["label_name"](c), moved(s, lift)) for c, s in labels]
for i, (p, t) in enumerate(zip(pins, letters)):
    items += [(f"Button{i}", moved(p, lift)), (f"Letter{i}", moved(t, lift))]
for i, (sw, st) in enumerate(zip(parts["switches"], parts["stems"])):
    items += [(f"Switche{i}", moved(sw, lift)), (f"Stem{i}", moved(st, lift))]
for i, (c, lg) in enumerate(zip(parts["caps"], parts["legends"])):
    items += [(f"Cap{i}", moved(c, lift + V(0, 0, 18))), (f"Legend{i}", moved(lg, lift + V(0, 0, 18)))]
for i, (x, y) in enumerate(L.bosses):
    items.append((f"Screw{i}", moved(screw(3.0, 6, 5.7, 1.65, V(0, 0, 1)), V(x, y, -14))))
for i, x in enumerate(L.rear_screws):
    items.append((f"Screw{i + 2}", moved(screw(3.0, 6, 5.7, 1.65, V(0, -1, 0)), V(x, L.D + 14, L.rear_z))))
save("Step5", items)
