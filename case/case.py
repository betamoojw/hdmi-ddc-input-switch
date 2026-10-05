# Parametric enclosure for hdmi-ddc-input-switch.
#
# Two printed parts:
#   tray : floor, walls (tops follow the lid angle), Feather standoffs (M2.5 heat-set
#          inserts), port holes, screw counterbores underneath
#   lid  : flat plate mounted at TILT_DEG — MX switch cutouts, clip pockets, RESET/BOOT
#          pinholes, alignment lip, bosses with M3 heat-set inserts (M3 screws come up
#          through the floor)
#
# Layout (top view, user at the bottom):
#
#             +--------------+
#        USB= | [ Feather ]  |=HDMI     back section is board length + thin side walls,
#   +---------+              +------+   centred behind the keys
#   | [k1]  [k2]  [k3]  ...  [kN]   |
#   +-------------------------------+
#
# Side view: the lid slopes down toward the user; the back (over the board) is taller.
#
# The board sits fully inside the back section. The receptacle shells overhang the
# PCB edge into the (thinner) side walls, through slots that are open at the top (so
# the board drops straight in) and sized for the cable's plug housing (so the plug
# goes all the way in). The lid closes the top of each slot.
#
# Printing without supports:
#   tray — upright as modelled. Each screw counterbore ends in a one-layer bridge over
#          the clearance hole (SACRIFICIAL_LAYER); push the screw through it.
#          No foot recesses: stick bumpers to the flat bottom.
#   lid  — exported top-face down; bosses and lip lean TILT_DEG, which prints fine.
#
# Board coordinates come from Adafruit's Eagle files (Adafruit-Feather-RP2040-DVI-PCB).
# Connector heights are NOT in those files: measure yours and adjust USB_H / HDMI_H.
#
# Run inside FreeCAD (GUI or freecadcmd):
#   p = "case/case.py"; exec(open(p).read(), {"__file__": p})
# Exports print-ready STL + 3MF to case/export/.

import math
import os
import sys
import FreeCAD as App
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadlib  # noqa: E402

# ---- keys -------------------------------------------------------------------
NUM_KEYS       = 4
KEY_PITCH      = 19.05
SWITCH_CUTOUT  = 14.0      # from the test coupon
CLIP_POCKET    = 15.6      # recess under the plate so the switch clips can latch
PLATE_T        = 1.5       # plate thickness at each switch (MX clips need 1.5)
SWITCH_BELOW   = 8.3       # switch housing + pins below the plate's top face
SEPARATE_PLATE = True      # switches in a separate flat plate glued under a window in the
                           # lid: keys sit LID_T lower, and both parts print without supports
PLATE_FLANGE   = 3.0       # plate overlap (glue area) around the window
KEY_WINDOW     = 19.0      # window width per key (keycap 18 + clearance)
KEY_WINDOW_R   = 1.5       # window corner radius: keycap skirt corner (1.0) + the 0.5 mm gap
KEY_WINDOW_FILLET = 0.6    # rounds the window's top edge (on the bed when printing; keep small)
PIN_D, PIN_H   = 3.0, 1.0  # locating pins on the lid underside; matching holes in the plate
PIN_CLEAR      = 0.15
WIRE_ROOM      = 1.5       # floor to the lowest switch pin
SIDE_MARGIN    = 6.5       # inner wall to first/last key cell (keeps the front bosses clear of the key window)
KEY_Y_MARGIN   = 5.5   # inner wall to key cell, front and back (keys centred in the front section)
TILT_DEG       = 8.0       # lid angle, rising toward the back (0 = flat)

# ---- shell ------------------------------------------------------------------
WALL           = 2.4
FLOOR          = 3.0
LID_T          = 3.0
KEY_SINK       = LID_T if SEPARATE_PLATE else 0.0   # switch plate top below the lid surface
CORNER_R       = 3.0
LID_EDGE_R     = 1.2       # fillet on the lid's top outer edge (on the bed when printing; keep small)
LIP_H          = 2.0       # alignment lip on the lid, drops inside the walls
LIP_T          = 1.2
LIP_CLEAR      = 0.25
PORT_WALL      = 1.6       # side walls of the back section (the port walls)
PORT_CLEAR     = 0.25      # hole around each receptacle, each side
ABOVE_PORT     = 2.0       # wall material above the taller port hole

# ---- Feather RP2040 DVI (board coordinates, mm, origin = USB-C end, header JP1 side)
PCB_L, PCB_W, PCB_T = 50.8, 22.86, 1.6
PCB_HOLES      = [(2.54, 2.54), (2.54, 20.32), (48.26, 1.905), (48.26, 20.955)]
BOARD_CLEAR    = 0.3       # PCB to walls
STANDOFF_H     = 3.0       # gap under the board for untrimmed solder joints / wire ends
STANDOFF_D     = 6.0
M25_INSERT_D   = 3.2       # hole for an M2.5 x 4 x 3.5 OD heat-set insert
M25_INSERT_L   = 5.0       # hole depth: insert + screw tip; fits an M2.5 x 6 screw
RESET_XY       = (9.525, 5.08)    # SW1 -> RUN
BOOT_XY        = (15.875, 5.08)   # SW2 -> GPIO7 (readable as a button)
# RST/BOOT plunger buttons: a printed pin rests on each board button. It runs perpendicular
# to the lid (so its top sits flush and prints flat) through a rounded-rectangle hole (so
# it can't turn and its letter stays upright). A collar rides in a pocket in the lid's underside,
# closed by a tab on the switch plate: it limits travel down (the press) and up. A sleeve
# under the tab guides the tip, whose end is cut level so it sits flat on the button.
# Needs SEPARATE_PLATE.
BUTTONS        = True
BUTTON_LETTERS = ("R", "B")   # inlaid on the pin tops (RST, BOOT)
LETTER_H       = 3.76      # same size and weight as the keycap legends (they print cleanly)
LETTER_FONT    = "ARIALNB.TTF"
LETTER_BOLD    = 0.12      # strokes grown this much each side, as on the keycaps
RST_BOOT_TEXT  = False        # "RST"/"BOOT" text on the lid next to the buttons
BTN_H          = 2.6       # board button height above the PCB (measured)
BTN_BODY       = (4.2, 3.05)  # board button footprint (for clash checks)
BTN_TRAVEL     = 0.4       # press travel before the collar lands on the plate tab
PLUNGER_W      = 4.4       # pin top, left-right (what you press)
PLUNGER_L      = 5.0       # pin top, front-back
PLUNGER_R      = 0.8       # pin top corner radius
PLUNGER_CLEAR  = 0.25      # each side, in the lid hole
PLUNGER_RECESS = 0.0       # pin top below the lid surface (0 = flush)
BTN_FILLET     = 0.3       # rounds the pin tops and the top edges of their holes
COLLAR_GROW    = (0.3, 0.8)  # collar beyond the shaft: left-right (the pins are close), front-back
COLLAR_T       = 0.6       # flat part of the collar; above it a taper to the shaft
TIP_D          = 2.8       # pin below the collar, onto the button
TIP_CLEAR      = 0.3       # radial, in the tab hole and sleeve (must slide freely)
SLEEVE_WALL    = 1.0
SLEEVE_GAP     = 1.2       # sleeve end above the board button
LID_SKIN       = 1.0       # lid material above the collar pocket (sets how far a pin can lift)
POCKET_CLEAR   = 0.25      # radial, around the collar
PINHOLE_D      = PLUNGER_L + 2 * PLUNGER_CLEAR if BUTTONS else 2.2   # front-back hole size

USB_Y          = 11.43     # receptacle centreline (board y)
USB_W          = 8.94      # receptacle width (from footprint)
USB_H          = 3.3       # receptacle height above PCB top   (measured)
USB_OVERHANG   = 1.2       # receptacle face past the PCB edge (measured)

HDMI_Y         = 11.43
HDMI_W         = 14.5      # receptacle width (from footprint)
HDMI_H         = 6.2       # receptacle height above PCB top   (measured)
HDMI_DEPTH     = 11.3      # receptacle length back from the PCB edge
HDMI_OVERHANG  = 1.0       # receptacle face past the PCB edge  (measured)

# Cable plugs: the moulded housing behind the metal shell. Measure your cables and set
# these (width along the wall, height); the port slots are cut to fit them, so the plug
# goes all the way in. USB-C spec maximum is 12.35 x 6.5.
USB_PLUG       = (12.5, 7.0)
HDMI_PLUG      = (20.0, 11.0)
PLUG_CLEAR     = 0.5       # around the plug housing, each side
SLOT_R         = 1.5       # corners of the plug recesses
SLOT_BELOW     = 0.1       # receptacle slot bottom below the PCB top (hides the PCB edge)
POCKET_EXTRA   = 0.1       # plug recess deeper than the receptacle face
MIN_SKIN       = 0.5       # wall left behind a plug recess
FILLER_CLEAR   = 0.15      # lid filler tab to slot, each side

BACK_ROOM      = 1.5       # board to back wall (clears the rear standoffs)

# ---- rear screws: two M3 x 6 go horizontally through the back wall into inserts in
#      small bosses hanging from the lid, just above the board's back strip.
REAR_SCREW_X   = 6.9       # each screw's distance from the back section's centreline
REAR_BOSS_W    = 7.0       # boss width / height (insert OD 5 leaves 1 mm walls)
REAR_BOSS_L    = 7.0       # boss length from the back wall (insert 4 + screw tip + floor)
REAR_SCREW_DROP = 4.0      # screw axis below the lid underside at the back wall
TEARDROP_TRUNC = 1.2       # sideways holes are teardrops (45-degree point toward print-up),
                           # clipped at this many radii above the centre
REAR_HEAD_DEPTH = 1.0      # counterbore for the button head in the back wall

# Taller parts on the board's top side (board coords x0, x1, y0, y1, height), for
# clash checks against the rear bosses: JST-PH battery jack, STEMMA QT jack.
BOARD_PARTS    = [(6.9, 14.9, 14.8, 22.3, 6.0), (30.45, 33.35, 13.0, 19.2, 3.0)]
SCREW_HEAD     = (4.6, 2.0)   # M2.5 board screw head diameter, height

# ---- fasteners --------------------------------------------------------------
BOSS_D         = 8.0
BOSS_INSET     = 3.4       # boss centre from the inner wall faces
M3_INSERT_D    = 4.2       # hole for an M3 x 4 x 5 OD heat-set insert
M3_INSERT_L    = 6.0       # hole depth: insert + screw tip (M3 x 5 or M3 x 6 screw)
M3_CLEAR_D     = 3.4
M3_HEAD_D      = 6.2       # button-head counterbore
M3_HEAD_H      = 2.0
SACRIFICIAL_LAYER = 0.2    # one layer bridging each counterbore; set to your layer height

# ---- lid labels (inlaid flush, printed as a second colour) -------------------
LABEL_H        = 2.4       # RST / BOOT text height
INLAY_DEPTH    = 0.6       # 3 layers at 0.2 mm
LID_ART        = "monitor" # "monitor": ultrawide monitor icon; "svg": TITLE_SVG; "text": TITLE_TEXT
TITLE_TEXT     = "INPUT SWITCH"
TITLE_SVG      = "logo.svg"  # your SVG in case/ (solid fills); one part per fill colour
TEXT_COLOUR    = "#1a1a1a" # RST/BOOT (and TITLE_TEXT); reuse an art colour to save an AMS slot

# "monitor" art: an ultrawide monitor centred in the open area above RST/BOOT,
# sized to fill it (width-limited by MON_SIDE_MARGIN, height by the area)
FRAME_COLOUR   = "#1a1a1a"
SCREEN_COLOUR  = "#00a8e8"
MON_ASPECT     = 5760 / 1440 # screen proportions (4:1 ultrawide)
MON_FRAME      = 1.2
MON_SIDE_MARGIN = 4.0        # from the back section's walls
MON_LABEL_GAP  = 1.6         # between the RST/BOOT labels and the stand base
MON_NECK       = (0.10, 2.0) # stand neck: width as a fraction of the monitor, height
MON_BASE       = (0.50, 1.2) # stand base: width as a fraction of the monitor, height
ART_GAP        = 0.8         # minimum gap between the art, labels and holes
MAX_LABEL_COLOURS = 3      # 4-slot AMS minus the lid's own filament
TITLE_MAX_H    = 9.0       # text line height cap
TITLE_MARGIN   = 3.0       # from the edges of the area over the board
# -----------------------------------------------------------------------------

V = App.Vector
T = math.radians(TILT_DEG)
BIG = 500.0


def poly_face(pts):
    return Part.Face(Part.makePolygon([V(x, y, 0) for x, y in pts] + [V(*pts[0], 0)]))


def box(x0, y0, z0, x1, y1, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def teardrop_y(d, x, z, y0, y1, up=1):
    """Hole along y that prints round when its axis is horizontal: a circle with a
    45-degree point toward print-up (up=+1: +z, up=-1: -z), clipped at TEARDROP_TRUNC radii."""
    r = d / 2
    k = r / math.sqrt(2)
    tri = Part.Face(Part.makePolygon([V(x - k, y0, z + up * k), V(x, y0, z + up * r * math.sqrt(2)),
                                      V(x + k, y0, z + up * k), V(x - k, y0, z + up * k)]))
    shape = cyl_y(d, x, z, y0, y1).fuse(tri.extrude(V(0, y1 - y0, 0)))
    clip = r * TEARDROP_TRUNC
    keep = box(x - d, y0 - 1, z - clip, x + d, y1 + 1, z + clip)
    return shape.common(keep).removeSplitter()


def cyl_y(d, x, z, y0, y1):
    return Part.makeCylinder(d / 2, y1 - y0, V(x, y0, z), V(0, 1, 0))


def cyl(d, x, y, z0, z1):
    return Part.makeCylinder(d / 2, z1 - z0, V(x, y, z0))


class Layout:
    def __init__(self):
        p = KEY_PITCH
        span = PCB_L + 2 * (BOARD_CLEAR + PORT_WALL)      # back section outer width

        self.W = max(2 * WALL + 2 * SIDE_MARGIN + NUM_KEYS * p, span)
        self.key_y = WALL + KEY_Y_MARGIN + p / 2
        x0 = (self.W - NUM_KEYS * p) / 2
        self.key_x = [x0 + p * (i + 0.5) for i in range(NUM_KEYS)]

        # back section centred on the keys, board fully inside its walls
        self.back_l = (self.W - span) / 2
        self.back_r = self.back_l + span
        self.bx = self.back_l + PORT_WALL + BOARD_CLEAR   # PCB x origin
        self.step_y = self.key_y + p / 2 + KEY_Y_MARGIN + WALL   # wings end: keys centred
        # PCB y origin: board fully in the back section, ports centred on its side walls
        # (step_y .. D), never closer to the step than BOARD_CLEAR
        self.by = self.step_y + max(BOARD_CLEAR, PCB_W + BACK_ROOM + WALL - 2 * USB_Y)
        self.D = self.by + PCB_W + BACK_ROOM + WALL
        self.has_wings = self.back_l > 1.0

        self.pcb_bot = FLOOR + STANDOFF_H
        self.pcb_top = self.pcb_bot + PCB_T

        # lid underside is the plane z = z0 + y*tan(T); pick z0 so that both the
        # switches (front) and the port holes (over the board) fit
        port_top = self.pcb_top + max(max(USB_H, HDMI_H) + PORT_CLEAR + ABOVE_PORT,
                                      USB_H / 2 + USB_PLUG[1] / 2 + PLUG_CLEAR,
                                      HDMI_H / 2 + HDMI_PLUG[1] / 2 + PLUG_CLEAR)
        flare = PORT_WALL + BOARD_CLEAR - min(USB_OVERHANG, HDMI_OVERHANG) + POCKET_EXTRA
        port_top += flare                                  # the recess funnel's top edge
        port_y = self.by + min(USB_Y - USB_PLUG[0] / 2, HDMI_Y - HDMI_PLUG[0] / 2) - PLUG_CLEAR - flare
        u = self.key_y / math.cos(T) - 7.0
        w = LID_T - KEY_SINK - SWITCH_BELOW
        self.z0 = max(port_top - port_y * math.tan(T),
                      FLOOR + WIRE_ROOM - (u * math.sin(T) + w * math.cos(T)))

        i = BOSS_INSET + WALL
        self.bosses = [(i, i), (self.W - i, i)]    # front: screws up through the floor

        # rear: screws through the back wall, axis along y
        cx = (self.back_l + self.back_r) / 2
        self.back_in = self.D - WALL
        self.rear_z = self.lid_z(self.back_in) - REAR_SCREW_DROP
        self.rear_screws = [cx - REAR_SCREW_X, cx + REAR_SCREW_X]

    def rear_bosses(self):
        """Lid bosses for the rear screws, hanging from the underside against the back wall."""
        h = REAR_BOSS_W / 2
        out = None
        for x in self.rear_screws:
            b = box(x - h, self.back_in - REAR_BOSS_L, self.rear_z - h, x + h, self.back_in - 0.1, BIG)
            b = b.common(self.to_lid(box(-BIG, -BIG, -BIG, BIG, BIG, 0.01)))
            out = b if out is None else out.fuse(b)
        return out

    def rear_insert_holes(self):
        """Cut after the bosses and the lip are fused (the lip runs through the bosses)."""
        out = None
        for x in self.rear_screws:
            # lid prints face-down, so print-up is world-down here
            h = teardrop_y(M3_INSERT_D, x, self.rear_z, self.back_in - M3_INSERT_L, self.back_in + 1, up=-1)
            out = h if out is None else out.fuse(h)
        return out

    def rear_screw_holes(self):
        """Clearance + counterbore through the tray's back wall."""
        out = None
        for x in self.rear_screws:
            h = teardrop_y(M3_CLEAR_D, x, self.rear_z, self.back_in - 1, self.D + 1)
            h = h.fuse(teardrop_y(M3_HEAD_D, x, self.rear_z, self.D - REAR_HEAD_DEPTH, self.D + 1))
            out = h if out is None else out.fuse(h)
        return out

    def board(self, x, y):
        return self.bx + x, self.by + y

    def key_window(self):
        """Key window outline in the lid frame (x, u), as a face at w = 0."""
        u = self.key_y / math.cos(T)
        h = KEY_WINDOW / 2
        return rrect_face(self.key_x[0] - h, u - h, self.key_x[-1] + h, u + h, KEY_WINDOW_R)

    def window_top_edges(self, lid):
        """Edges where the key window meets the lid's top face."""
        bb = self.key_window().BoundBox
        return self.top_edges_in(lid, bb.XMin, bb.XMax, bb.YMin, bb.YMax)

    def top_edges_in(self, lid, x0, x1, u0, u1):
        """Edges on the lid's top face inside a lid-frame (x, u) rectangle."""
        inv = App.Placement(V(0, 0, self.z0), App.Rotation(V(1, 0, 0), TILT_DEG)).inverse()
        out = []
        for e in lid.Edges:
            p = inv.multVec(e.valueAt((e.FirstParameter + e.LastParameter) / 2))
            if abs(p.z - LID_T) < 1e-3 and x0 - 0.1 <= p.x <= x1 + 0.1 and u0 - 0.1 <= p.y <= u1 + 0.1:
                out.append(e)
        return out

    def button_axis(self, xy):
        """Plunger axis for a board button: (x, u) in the lid frame (the axis is the lid
        normal through the button's top centre) and w of the button top."""
        x, y = self.board(*xy)
        z = self.pcb_top + BTN_H
        p = App.Placement(V(0, 0, self.z0), App.Rotation(V(1, 0, 0), TILT_DEG)).inverse()
        q = p.multVec(V(x, y, z))
        return q.x, q.y, q.z

    def button_hole_xy(self, xy):
        """Plan position where the plunger meets the lid's top surface."""
        x, u, _ = self.button_axis(xy)
        return x, u * math.cos(T) - LID_T * math.sin(T)

    def pin_positions(self):
        """Locating pins, centred in the flange at each end of the window (lid frame)."""
        u = self.key_y / math.cos(T)
        h = KEY_WINDOW / 2 + PLATE_FLANGE / 2
        return [(self.key_x[0] - h, u), (self.key_x[-1] + h, u)]

    def lid_z(self, y):
        """Lid underside at plan y."""
        return self.z0 + y * math.tan(T)

    def top_z(self, y):
        return self.lid_z(y) + LID_T / math.cos(T)

    def to_lid(self, shape):
        """Place a shape modelled in the flat lid frame (x, u along the slope, w up;
        w = 0 is the underside)."""
        s = shape.copy()
        s.rotate(V(0, 0, 0), V(1, 0, 0), TILT_DEG)
        s.translate(V(0, 0, self.z0))
        return s

    def above_underside(self):
        return self.to_lid(box(-BIG, -BIG, 0, BIG, BIG, BIG))

    def below_underside(self):
        return self.to_lid(box(-BIG, -BIG, -BIG, BIG, BIG, 0))

    def outline(self):
        W, D, l, r, s = self.W, self.D, self.back_l, self.back_r, self.step_y
        if self.has_wings:
            pts = [(0, 0), (W, 0), (W, s), (r, s), (r, D), (l, D), (l, s), (0, s)]
        else:
            pts = [(0, 0), (W, 0), (W, D), (0, D)]
        return poly_face(pts).makeOffset2D(-CORNER_R).makeOffset2D(CORNER_R)

    def title_area(self):
        """Plan rectangle (x0, x1, y0, y1) of open lid top over the board, behind
        the RST/BOOT labels."""
        _, label_y = self.board(0, max(RESET_XY[1], BOOT_XY[1]))
        return (self.back_l + WALL, self.back_r - WALL,
                label_y + LABEL_H, self.D - WALL - LID_EDGE_R)

    def prism(self, face):
        return face.extrude(V(0, 0, BIG))

    def ports(self):
        """(wall outer x, wall inner x, centre y, receptacle w, h, face depth inside the
        outer wall surface, plug w x h) for each port."""
        _, uy = self.board(0, USB_Y)
        _, hy = self.board(0, HDMI_Y)
        depth = lambda overhang: PORT_WALL + BOARD_CLEAR - overhang
        return [(self.back_l, self.back_l + PORT_WALL, uy, USB_W, USB_H, depth(USB_OVERHANG), USB_PLUG),
                (self.back_r, self.back_r - PORT_WALL, hy, HDMI_W, HDMI_H, depth(HDMI_OVERHANG), HDMI_PLUG)]

    def port_cuts(self):
        """Per port: (slot, pocket, filler) in world coordinates.
        slot   - tight around the receptacle, through the wall and open to the top, so
                 the board drops straight in; its bottom hides the PCB edge.
        pocket - shallow recess in the outer face for the plug housing, just deep enough
                 that the plug seats fully.
        filler - lid tab that closes the slot above the receptacle (fused to the lid)."""
        out = []
        for xo, xi, cy, w, h, depth, (pw, ph) in self.ports():
            sgn = 1 if xi > xo else -1                     # inward direction
            zc = self.pcb_top + h / 2
            sw = w + 2 * PORT_CLEAR
            slot = box(min(xo, xi) - 1, cy - sw / 2, self.pcb_top - SLOT_BELOW,
                       max(xo, xi) + 1, cy + sw / 2, BIG)
            d = depth + POCKET_EXTRA
            if PORT_WALL - d < MIN_SKIN:
                raise ValueError(f"port pocket leaves {PORT_WALL - d:.2f} mm of wall")
            # recess: a rounded-rectangle funnel. The floor fits the plug housing; the
            # sides flare out at 45 degrees all round (prints without supports)
            y0, y1 = cy - pw / 2 - PLUG_CLEAR, cy + pw / 2 + PLUG_CLEAR
            z0, z1 = zc - ph / 2 - PLUG_CLEAR, zc + ph / 2 + PLUG_CLEAR
            pocket = self._wall_funnel((y0, z0, y1, z1), SLOT_R, xo, sgn, d)
            filler = box(min(xo, xi), cy - sw / 2 + FILLER_CLEAR, self.pcb_top + h + PORT_CLEAR,
                         max(xo, xi), cy + sw / 2 - FILLER_CLEAR, BIG)
            filler = filler.common(self.to_lid(box(-BIG, -BIG, -BIG, BIG, BIG, 0.01))).cut(pocket)
            out.append((slot, pocket, filler))
        return out

    @staticmethod
    def _wall_funnel(rect_yz, r, xo, sgn, depth):
        """Recess in the wall at x = xo: rounded rectangle rect_yz = (y0, z0, y1, z1) at
        `depth` inside, growing 1:1 toward the outside (continued 1 mm past the face)."""
        y0, z0, y1, z1 = rect_yz
        wires = []
        for c in (depth, -1.0):                            # c: distance inside the face
            g = depth - c
            w = rrect_face(y0 - g, z0 - g, y1 + g, z1 + g, r + g).OuterWire
            w.translate(V(0, 0, c))
            wires.append(w)
        solid = Part.makeLoft(wires, True, True)           # drawn as (y, z, inward)
        return solid.transformGeometry(App.Matrix(0, 0, sgn, xo,
                                                  1, 0, 0, 0,
                                                  0, 1, 0, 0,
                                                  0, 0, 0, 1))

    def port_walls_thinning(self):
        """Cavity extension that thins the back section's side walls to PORT_WALL
        alongside the board (the rear corners stay full thickness for the bosses)."""
        return box(self.back_l + PORT_WALL, self.by - BOARD_CLEAR, FLOOR,
                   self.back_r - PORT_WALL, self.by + PCB_W + BOARD_CLEAR, BIG)


def build_tray(L):
    outer = L.outline()
    tray = L.prism(outer)
    cavity = L.prism(outer.makeOffset2D(-WALL))
    cavity.translate(V(0, 0, FLOOR))
    tray = tray.cut(cavity).cut(L.port_walls_thinning()).cut(L.above_underside())
    tray = tray.cut(L.rear_screw_holes())

    for slot, pocket, _ in L.port_cuts():
        tray = tray.cut(slot).cut(pocket)

    for hx, hy in PCB_HOLES:
        x, y = L.board(hx, hy)
        tray = tray.fuse(cyl(STANDOFF_D, x, y, FLOOR - 0.1, L.pcb_bot).common(L.prism(outer)))
        tray = tray.cut(cyl(M25_INSERT_D, x, y, L.pcb_bot - M25_INSERT_L, L.pcb_bot + 0.1))

    # screws up through the floor into the lid bosses; one sacrificial layer caps
    # each counterbore so it prints without supports
    for x, y in L.bosses:
        tray = tray.cut(cyl(M3_HEAD_D, x, y, -1, M3_HEAD_H))
        tray = tray.cut(cyl(M3_CLEAR_D, x, y, M3_HEAD_H + SACRIFICIAL_LAYER, FLOOR + 1))

    return tray.removeSplitter()


def build_lid(L):
    outer = L.outline()
    lid = L.to_lid(box(-1, -BIG, 0, L.W + 1, BIG, LID_T)).common(L.prism(outer))
    if LID_EDGE_R > 0:
        up = V(0, -math.sin(T), math.cos(T))
        top = max((f for f in lid.Faces if f.normalAt(0, 0).getAngle(up) < 1e-3),
                  key=lambda f: f.CenterOfMass.z)
        lid = lid.makeFillet(LID_EDGE_R, top.Edges)

    # lip: vertical walls just inside the tray walls, hanging LIP_H below the underside
    lip_out = outer.makeOffset2D(-(WALL + LIP_CLEAR))
    ring = L.prism(lip_out).cut(L.prism(lip_out.makeOffset2D(-LIP_T)))
    band = L.to_lid(box(-BIG, -BIG, -LIP_H, BIG, BIG, 0.01))
    lid = lid.fuse(ring.common(band)).fuse(L.rear_bosses()).cut(L.rear_insert_holes())

    # bosses are trimmed to the cavity so they slide past the tray walls
    cavity = L.prism(outer.makeOffset2D(-(WALL + 0.2)))
    for x, y in L.bosses:
        boss = cyl(BOSS_D, x, y, FLOOR, BIG).common(cavity).common(
            L.to_lid(box(-BIG, -BIG, -BIG, BIG, BIG, 0.01)))
        lid = lid.fuse(boss).cut(cyl(M3_INSERT_D, x, y, FLOOR - 0.1, FLOOR + M3_INSERT_L))

    # keep the lip clear of the receptacle bodies inside the case
    lid = lid.cut(connectors(L, PORT_CLEAR))

    u = L.key_y / math.cos(T)
    s, c = SWITCH_CUTOUT, CLIP_POCKET
    if SEPARATE_PLATE:
        # window through the lid; the plate is glued underneath, located by two pins
        win = L.key_window().extrude(V(0, 0, LID_T + 2))
        win.translate(V(0, 0, -1))
        lid = lid.cut(L.to_lid(win))
        if KEY_WINDOW_FILLET > 0:
            lid = lid.makeFillet(KEY_WINDOW_FILLET, L.window_top_edges(lid))
        for px, pu in L.pin_positions():
            lid = lid.fuse(L.to_lid(Part.makeCylinder(PIN_D / 2, PIN_H + 0.01, V(px, pu, -PIN_H))))
    else:
        for x in L.key_x:
            lid = lid.cut(L.to_lid(box(x - s / 2, u - s / 2, -LIP_H - 1, x + s / 2, u + s / 2, LID_T + 1)))
            # clip pocket stays within the plate (the key margins keep it clear of the bosses)
            lid = lid.cut(L.to_lid(box(x - c / 2, u - c / 2, -0.01, x + c / 2, u + c / 2, LID_T - PLATE_T)))

    for xy in (RESET_XY, BOOT_XY):
        if BUTTONS:
            x, u, _ = L.button_axis(xy)
            c = PLUNGER_CLEAR
            lid = lid.cut(L.to_lid(rrect_prism(x, u, PLUNGER_W + 2 * c, PLUNGER_L + 2 * c,
                                               PLUNGER_R + c, -LIP_H - 1, LID_T + 1)))
            cw, cl = collar_size()
            p = POCKET_CLEAR
            lid = lid.cut(L.to_lid(rrect_prism(x, u, cw + 2 * p, cl + 2 * p, PLUNGER_R + p,
                                               -1, LID_T - LID_SKIN)))
            if BTN_FILLET > 0:
                hw, hl = PLUNGER_W / 2 + c, PLUNGER_L / 2 + c
                lid = lid.makeFillet(BTN_FILLET, L.top_edges_in(lid, x - hw, x + hw, u - hl, u + hl))
        else:
            x, y = L.board(*xy)
            lid = lid.cut(cyl(PINHOLE_D, x, y, L.lid_z(y) - LIP_H - 1, L.top_z(y) + 2))

    labels = build_labels(L)
    for s in labels.values():
        lid = lid.cut(s)

    # tabs closing the port slots above the receptacles
    for _, _, filler in L.port_cuts():
        lid = lid.fuse(filler.cut(connectors(L, PORT_CLEAR)))
    return lid.removeSplitter(), labels


def rst_boot_label_positions(L):
    """(label, x, plan y, width) — RST left of its hole, BOOT right of its hole."""
    out = []
    for xy, label, side in ((RESET_XY, "RST", -1), (BOOT_XY, "BOOT", +1)):
        x, y = L.button_hole_xy(xy) if BUTTONS else L.board(*xy)
        w = cadlib.text_solid(label, LABEL_H, 0.1).BoundBox.XLength
        out.append((label, x + side * (PINHOLE_D / 2 + 1.0 + w / 2), y, w))
    return out


def rrect_face(x0, y0, x1, y1, r):
    r = min(r, (x1 - x0) / 2 - 0.01, (y1 - y0) / 2 - 0.01)
    f = poly_face([(x0 + r, y0 + r), (x1 - r, y0 + r), (x1 - r, y1 - r), (x0 + r, y1 - r)])
    return f.makeOffset2D(r) if r > 0 else poly_face([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def monitor_art(L):
    """{colour: [plan faces]}: an ultrawide monitor on a stand, as large as fits in the
    open lid area above RST/BOOT, centred in it."""
    if RST_BOOT_TEXT:
        labels_top = max(y + LABEL_H / 2 for _, _, y, _ in rst_boot_label_positions(L))
    else:
        holes = [L.button_hole_xy(xy) if BUTTONS else L.board(*xy) for xy in (RESET_XY, BOOT_XY)]
        labels_top = max(y for _, y in holes) + PINHOLE_D / 2
    y_lo = labels_top + MON_LABEL_GAP
    y_hi = L.D - WALL - LID_EDGE_R - ART_GAP
    x_lo, x_hi = L.back_l + WALL + MON_SIDE_MARGIN, L.back_r - WALL - MON_SIDE_MARGIN
    f = MON_FRAME
    fixed_h = MON_BASE[1] + MON_NECK[1] + 2 * f              # height not scaling with width
    w = min(x_hi - x_lo, (y_hi - y_lo - fixed_h) * MON_ASPECT + 2 * f)
    h = (w - 2 * f) / MON_ASPECT + 2 * f                      # frame outside height
    total = MON_BASE[1] + MON_NECK[1] + h
    cx, y0 = L.W / 2, (y_lo + y_hi) / 2 - total / 2

    bw, bh = MON_BASE[0] * w, MON_BASE[1]
    nw, nh = MON_NECK[0] * w, MON_NECK[1]
    base = rrect_face(cx - bw / 2, y0, cx + bw / 2, y0 + bh, bh / 2)
    neck = rrect_face(cx - nw / 2, y0 + bh - 0.1, cx + nw / 2, y0 + bh + nh + 0.1, 0)
    fy0 = y0 + bh + nh
    outer = rrect_face(cx - w / 2, fy0, cx + w / 2, fy0 + h, 1.2)
    screen = rrect_face(cx - w / 2 + f, fy0 + f, cx + w / 2 - f, fy0 + h - f, 0.3)
    frame = outer.cut(screen).Faces[0]
    return {FRAME_COLOUR: [frame, neck, base], SCREEN_COLOUR: [screen]}


def plan_face_to_lid(face, z):
    """Extrude a plan-coordinate face into an inlay on the lid's top face."""
    m = App.Matrix()
    m.scale(1, 1 / math.cos(T), 1)
    f = face.transformGeometry(m)
    f.translate(V(0, LID_T * math.sin(T) / math.cos(T), 0))
    s = f.extrude(V(0, 0, INLAY_DEPTH))
    s.translate(V(0, 0, z))
    return s


def top_u(y):
    """Lid-frame u of the point on the lid's top face that sits over plan y
    (the top face is LID_T above the rotation plane, so it shifts by LID_T*sin(T))."""
    return (y + LID_T * math.sin(T)) / math.cos(T)


def build_labels(L):
    """Inlays flush with the lid top: RST/BOOT beside the pinholes, and the title
    (text or SVG) in the open area over the board. Returns {colour: solid}, one
    printed part per colour, placed in world coordinates."""
    z = LID_T - INLAY_DEPTH
    by_colour = {}

    def add(colour, solid):
        by_colour[colour] = by_colour[colour].fuse(solid) if colour in by_colour else solid

    for label, x, y, _ in (rst_boot_label_positions(L) if RST_BOOT_TEXT else []):
        t = cadlib.text_solid(label, LABEL_H, INLAY_DEPTH)
        add(TEXT_COLOUR, cadlib.place_centered(t, x, top_u(y), z))

    x0, x1, y0, y1 = L.title_area()
    w, h = x1 - x0 - 2 * TITLE_MARGIN, y1 - y0 - 2 * TITLE_MARGIN
    cx, cy = (x0 + x1) / 2, top_u((y0 + y1) / 2)
    if LID_ART == "monitor":
        for colour, faces in monitor_art(L).items():
            for f in faces:
                add(colour, plan_face_to_lid(f, z))
    elif LID_ART == "svg":
        # all colours share one placement so they stay registered
        for colour, s in cadlib.svg_color_solids(os.path.join(HERE, TITLE_SVG), w, h, INLAY_DEPTH):
            s.translate(V(cx, cy, z))
            add(colour, s)
    else:
        title = cadlib.fit_text(TITLE_TEXT, w, h, INLAY_DEPTH, min_h=TITLE_MAX_H * 0.7,
                                line_gap=1.5, line_max_h=TITLE_MAX_H)
        add(TEXT_COLOUR, cadlib.place_centered(title, cx, cy, z))

    if len(by_colour) > MAX_LABEL_COLOURS:
        raise ValueError(f"{len(by_colour)} label colours {sorted(by_colour)}; the AMS has room "
                         f"for {MAX_LABEL_COLOURS} besides the lid. Merge colours in the SVG "
                         f"or set TEXT_COLOUR to one of the SVG's colours.")
    clip = L.prism(L.outline())
    out = {}
    for colour, s in by_colour.items():
        s.translate(V(0, 0, 0.01))     # flush: the top of the inlay is the lid top
        out[colour] = L.to_lid(s).common(clip)
    return out


def connectors(L, grow=0.0):
    x0, _ = L.board(0, 0)
    _, uy = L.board(0, USB_Y)
    _, hy = L.board(0, HDMI_Y)
    g, z = grow, L.pcb_top
    usb = box(x0 - USB_OVERHANG - g, uy - USB_W / 2 - g, z,
              x0 + 6.1 + g, uy + USB_W / 2 + g, z + USB_H + g)
    hdmi = box(x0 + PCB_L - HDMI_DEPTH - g, hy - HDMI_W / 2 - g, z,
               x0 + PCB_L + HDMI_OVERHANG + g, hy + HDMI_W / 2 + g, z + HDMI_H + g)
    return usb.fuse(hdmi)


def board_ghost(L):
    """Feather + connectors, for visual and interference checks (not exported)."""
    x0, y0 = L.board(0, 0)
    g = box(x0, y0, L.pcb_bot, x0 + PCB_L, y0 + PCB_W, L.pcb_top).fuse(connectors(L))
    for px0, px1, py0, py1, h in BOARD_PARTS:
        g = g.fuse(box(x0 + px0, y0 + py0, L.pcb_top, x0 + px1, y0 + py1, L.pcb_top + h))
    for bx, by in (RESET_XY, BOOT_XY):
        x, y = L.board(bx, by)
        w, d = BTN_BODY
        g = g.fuse(box(x - w / 2, y - d / 2, L.pcb_top, x + w / 2, y + d / 2, L.pcb_top + BTN_H))
    d, h = SCREW_HEAD
    for hx, hy in PCB_HOLES:
        x, y = L.board(hx, hy)
        g = g.fuse(cyl(d, x, y, L.pcb_top, L.pcb_top + h))
    return g


def build_plate(L):
    """Separate switch plate: flat, PLATE_T thick, glued under the lid's key window.
    Notched around the front bosses and kept inside the lid's lip."""
    u = L.key_y / math.cos(T)
    outline = L.key_window().makeOffset2D(PLATE_FLANGE)
    plate = outline.extrude(V(0, 0, PLATE_T))
    plate.translate(V(0, 0, -PLATE_T))
    plate = L.to_lid(plate)
    # stay inside the lip and clear of the boss columns
    inside = L.prism(L.outline().makeOffset2D(-(WALL + LIP_CLEAR + LIP_T + 0.3)))
    inside.translate(V(0, 0, -BIG / 2))
    plate = plate.common(inside)
    for x, y in L.bosses:
        plate = plate.cut(cyl(BOSS_D + 0.6, x, y, -BIG, BIG))
    s = SWITCH_CUTOUT
    for x in L.key_x:
        plate = plate.cut(L.to_lid(box(x - s / 2, u - s / 2, -PLATE_T - 1, x + s / 2, u + s / 2, 1)))
    for px, pu in L.pin_positions():
        plate = plate.cut(L.to_lid(Part.makeCylinder(PIN_D / 2 + PIN_CLEAR, PLATE_T + 2,
                                                     V(px, pu, -PLATE_T - 1))))
    if BUTTONS:
        # tab reaching back under the RST/BOOT plungers: closes their collar pockets and
        # carries the sleeves that guide the pin tips
        axes = [L.button_axis(xy) for xy in (RESET_XY, BOOT_XY)]
        m = max(collar_size()) / 2 + POCKET_CLEAR + 2.0
        u0 = outline.BoundBox.YMax - 1.0
        u1 = max(u for _, u, _ in axes) + m
        tab = box(min(x for x, _, _ in axes) - m, u0, -PLATE_T, max(x for x, _, _ in axes) + m, u1, 0)
        plate = plate.fuse(L.to_lid(tab).common(inside))
        for x, u, w_btn in axes:
            w_end = w_btn + SLEEVE_GAP                       # sleeve end, above the button
            r_hole = TIP_D / 2 + TIP_CLEAR
            sleeve = Part.makeCylinder(r_hole + SLEEVE_WALL, -PLATE_T - w_end + 0.01, V(x, u, w_end))
            plate = plate.fuse(L.to_lid(sleeve))
            plate = plate.cut(L.to_lid(Part.makeCylinder(r_hole, BIG, V(x, u, w_end - 1))))
    return plate.removeSplitter()


def rrect_prism(x, u, w, l, r, w0, w1):
    """Rounded rectangle centred on (x, u), extruded along w from w0 to w1 (lid frame)."""
    f = rrect_face(x - w / 2, u - l / 2, x + w / 2, u + l / 2, r)
    f.translate(V(0, 0, w0))
    return f.extrude(V(0, 0, w1 - w0))


def rrect_wire(x, u, w, l, r, wz):
    f = rrect_face(x - w / 2, u - l / 2, x + w / 2, u + l / 2, r)
    wire = f.OuterWire
    wire.translate(V(0, 0, wz))
    return wire


def collar_size():
    gx, gu = COLLAR_GROW
    return PLUNGER_W + 2 * gx, PLUNGER_L + 2 * gu


def build_buttons(L):
    """The two plunger pins at rest on their buttons (world coordinates).
    Returns (pins, letters, info); info = (travel down, travel up, pin length)."""
    pins, letters, info = [], [], []
    cw, cl = collar_size()
    taper = max(COLLAR_GROW)                           # 45 degrees on the side that grows most
    h_collar = COLLAR_T + taper
    for xy, letter in zip((RESET_XY, BOOT_XY), BUTTON_LETTERS):
        x, u, w_btn = L.button_axis(xy)
        w_top = LID_T - PLUNGER_RECESS
        w_c = BTN_TRAVEL                               # collar bottom at rest (tab top is w = 0)
        up = (LID_T - LID_SKIN) - (w_c + h_collar)
        if up < 0.1:
            raise ValueError(f"button can only rise {up:.2f} mm before the collar stops")
        tip = Part.makeCylinder(TIP_D / 2, w_c + 0.01 - (w_btn - 2), V(x, u, w_btn - 2))
        collar = rrect_prism(x, u, cw, cl, PLUNGER_R, w_c, w_c + COLLAR_T)
        tapered = Part.makeLoft([rrect_wire(x, u, cw, cl, PLUNGER_R, w_c + COLLAR_T - 0.01),
                                 rrect_wire(x, u, PLUNGER_W, PLUNGER_L, PLUNGER_R, w_c + h_collar)], True)
        shaft = rrect_prism(x, u, PLUNGER_W, PLUNGER_L, PLUNGER_R, w_c + h_collar - 0.02, w_top)
        pin = tip.fuse(collar).fuse(tapered).fuse(shaft).removeSplitter()
        if BTN_FILLET > 0:
            top = max(pin.Faces, key=lambda f: f.CenterOfMass.z)
            pin = pin.makeFillet(BTN_FILLET, top.Edges)
        pin = L.to_lid(pin)
        # tip end cut level with the board, so it sits flat on the button
        bx, by = L.board(*xy)
        pin = pin.cut(box(bx - 5, by - 5, -BIG, bx + 5, by + 5, L.pcb_top + BTN_H))
        # letter inlay on the top
        t = cadlib.text_solid(letter, LETTER_H, INLAY_DEPTH, LETTER_FONT, LETTER_BOLD)
        cadlib.place_centered(t, x, u, w_top - INLAY_DEPTH)
        t.translate(V(0, 0, 0.01))
        t = L.to_lid(t)
        pins.append(pin.cut(t).removeSplitter())
        letters.append(t)
        info.append((BTN_TRAVEL, up, w_top - w_btn))
    return pins, letters, info


def switch_ghost(L):
    """Switch bodies + pins below the plate, for interference checks."""
    u = L.key_y / math.cos(T)
    sw = None
    for x in L.key_x:
        b = L.to_lid(box(x - 7, u - 7, LID_T - KEY_SINK - SWITCH_BELOW, x + 7, u + 7, LID_T - KEY_SINK - PLATE_T))
        sw = b if sw is None else sw.fuse(b)
    return sw


def build_all(export=True):
    L = Layout()
    tray = build_tray(L)
    lid, labels = build_lid(L)
    plate = build_plate(L) if SEPARATE_PLATE else None
    doc = cadlib.fresh_document("HdmiDdcCase")
    cadlib.show(doc, "Tray", tray, (0.35, 0.37, 0.40))
    cadlib.show(doc, "Lid", lid, (0.75, 0.77, 0.80))
    if plate is not None:
        cadlib.show(doc, "Plate", plate, (0.2, 0.2, 0.22))
    buttons, letters, _ = build_buttons(L) if BUTTONS else ([], [], [])
    for i, (b, t) in enumerate(zip(buttons, letters)):
        cadlib.show(doc, f"Button{i}", b, (1.0, 0.48, 0.0))
        cadlib.show(doc, f"Letter{i}", t, (0.1, 0.1, 0.1))
    for colour, s in labels.items():
        cadlib.show(doc, label_name(colour), s, cadlib.hex_rgb(colour))
    cadlib.show(doc, "FeatherGhost", board_ghost(L), (0.1, 0.4, 0.8))
    doc.recompute()
    if export:
        out = os.path.join(HERE, "export")
        cadlib.export_mesh(tray, out, "case-tray")
        # lid + one part per label colour in one 3MF, top face down; same transform for all
        dz = -lid_print_pose(lid).optimalBoundingBox().ZMin   # tight box: top face on the bed
        parts = [("Lid", lid_print_pose(lid, dz))]
        parts += [(label_name(c), lid_print_pose(s, dz)) for c, s in labels.items()]
        cadlib.export_parts(parts, out, "case-lid")
        if plate is not None:
            # glue side down, so the button sleeves point up
            flat = plate.copy()
            flat.rotate(V(0, 0, 0), V(1, 0, 0), -TILT_DEG)
            flat = cadlib.flip_for_print(flat)
            flat.translate(V(0, 0, -flat.optimalBoundingBox().ZMin))
            cadlib.export_mesh(flat, out, "case-plate")
        if buttons:
            # top face down (letters on the bed), side by side; pins + letters as two parts
            laid_pins, laid_letters = [], []
            for i, (b, t) in enumerate(zip(buttons, letters)):
                pose = []
                for shape in (b, t):
                    f = shape.copy()
                    f.rotate(V(0, 0, 0), V(1, 0, 0), -TILT_DEG)
                    pose.append(f)
                c = pose[0].BoundBox.Center
                for f in pose:
                    f.rotate(c, V(1, 0, 0), 180)
                bb = pose[0].optimalBoundingBox()
                for f in pose:
                    f.translate(V(i * 9.0 - bb.Center.x, -bb.Center.y, -bb.ZMin))
                laid_pins.append(pose[0])
                laid_letters.append(pose[1])
            cadlib.export_parts([("Buttons", Part.makeCompound(laid_pins)),
                                 ("Letters", Part.makeCompound(laid_letters))], out, "case-buttons")
    print(f"case {L.W:.1f} x {L.D:.1f} mm, height {L.top_z(0):.1f} front / {L.top_z(L.D):.1f} back, "
          f"back section {L.back_r - L.back_l:.1f} wide, "
          f"tray valid={tray.isValid()}, lid valid={lid.isValid()}, "
          f"label colours {list(labels)} valid={all(s.isValid() for s in labels.values())}")
    return L, tray, lid, labels


def label_name(colour):
    return "Label_" + colour.lstrip("#")


def lid_print_pose(shape, dz=0.0):
    s = shape.copy()
    s.rotate(V(0, 0, 0), V(1, 0, 0), -TILT_DEG)
    s.rotate(V(0, 0, 0), V(1, 0, 0), 180)
    s.translate(V(0, 0, dz))
    return s


if __name__ != "case_check":
    L, TRAY, LID, LABELS = build_all()
