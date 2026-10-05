# Shared helpers for the case scripts (run inside FreeCAD / freecadcmd).

import os
import FreeCAD as App
import Part
import MeshPart

FONT_DIR  = "C:/Windows/Fonts/"
FONT_FILE = "arialbd.ttf"


def text_solid(s, height, depth, font_file=FONT_FILE, bold=0.0):
    """Extruded text, positioned with its bounding box at the origin.
    `bold` grows every outline by that much (thicker strokes, smaller holes) and spaces
    the letters out by twice that, so the gaps between them stay as the font drew them."""
    faces = []
    for i, char in enumerate(Part.makeWireString(s, FONT_DIR, font_file, height)):
        if char:
            if bold > 0:
                # fine polygons first: offsetting the font's splines can give faces
                # that extrude into invalid solids
                poly = []
                for w in char:
                    pts = w.discretize(Deflection=0.005)
                    poly.append(Part.makePolygon(pts + [pts[0]] if pts[0] != pts[-1] else pts))
                f = Part.Face(poly, "Part::FaceMakerBullseye").makeOffset2D(bold, join=0)
            else:
                f = Part.Face(char, "Part::FaceMakerBullseye")
            if bold > 0:
                f.translate(App.Vector(2 * bold * i, 0, 0))
            faces.append(f)
    solid = Part.makeCompound(faces).extrude(App.Vector(0, 0, depth))
    bb = solid.BoundBox
    solid.translate(App.Vector(-bb.XMin, -bb.YMin, 0))
    return solid


def fit_height(lines, max_w, max_h, font_file=FONT_FILE, line_gap=0.8, line_max_h=None, bold=0.0):
    """Largest line height at which all `lines` fit a max_w x max_h box."""
    fits = []
    for s in lines:
        w10 = text_solid(s, 10.0, 0.1, font_file).BoundBox.XLength
        fits.append(10.0 * (max_w - 2 * bold * len(s)) / w10)    # bold adds 2*bold per letter
    n = len(lines)
    return min(line_max_h or max_h, min(fits), (max_h - 2 * bold * n - line_gap * (n - 1)) / n)


def fit_text(label, max_w, max_h, depth, font_file=FONT_FILE, min_h=None, line_gap=0.8,
             line_max_h=None, height=None, bold=0.0):
    """Text sized to fit a max_w x max_h box, centred on the origin, z from 0 to depth.
    Each line is at most line_max_h tall. "\\n" in the label forces line breaks; otherwise,
    if a single line would be shorter than min_h and the label has a space, it wraps
    onto two lines. `height` forces the line height (e.g. to match other labels)."""
    def line(s, h):
        return text_solid(s, h, depth, font_file, bold)

    if "\n" in label:
        lines = label.split("\n")
        h = fit_height(lines, max_w, max_h, font_file, line_gap, line_max_h, bold)
    else:
        lines = [label]
        h = fit_height(lines, max_w, max_h, font_file, line_gap, line_max_h, bold)
        if min_h and h < min_h and " " in label:
            lines = label.split(" ", 1)
            h = fit_height(lines, max_w, max_h, font_file, line_gap, line_max_h, bold)
    if height is not None:
        h = height

    pitch = h + 2 * bold + line_gap
    total = len(lines) * (h + 2 * bold) + (len(lines) - 1) * line_gap
    out = None
    for i, s in enumerate(lines):
        t = line(s, h)
        place_centered(t, 0, total / 2 - i * pitch - (h + 2 * bold) / 2, 0)
        out = t if out is None else out.fuse(t)
    return out


SVG_SHAPES = ("path", "rect", "circle", "ellipse", "polygon")
SVG_NAMED = {"black": "#000000", "white": "#ffffff", "red": "#ff0000", "green": "#008000",
             "blue": "#0000ff", "yellow": "#ffff00", "orange": "#ffa500", "gray": "#808080",
             "grey": "#808080"}


def _svg_fill(el, inherited):
    fill = el.get("fill")
    for decl in (el.get("style") or "").split(";"):
        k, _, v = decl.partition(":")
        if k.strip() == "fill":
            fill = v.strip()
    fill = (fill or inherited or "#000000").lower()
    fill = SVG_NAMED.get(fill, fill)
    if len(fill) == 4 and fill.startswith("#"):
        fill = "#" + "".join(c * 2 for c in fill[1:])
    return fill


def _svg_faces(svg_text):
    """Import SVG text into a temporary document; return one face per SVG shape
    (holes within a shape via nesting). Shapes may overlap each other."""
    import importSVG
    import re
    import tempfile
    # FreeCAD asks for a DPI when the root width has no unit; we rescale anyway,
    # so give it mm units to skip the dialog.
    for attr in ("width", "height"):
        svg_text = re.sub(rf'(<svg\b[^>]*?\b{attr}=")([\d.]+)(?:px)?"', r'\1\2mm"', svg_text, count=1)
    tmp = os.path.join(tempfile.gettempdir(), "cadlib-import.svg")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(svg_text)
    doc = App.newDocument("SvgTmp")
    try:
        importSVG.insert(tmp, doc.Name)
        faces = []
        for o in doc.Objects:
            if hasattr(o, "Shape") and not o.Shape.isNull():
                wires = [w for w in o.Shape.Wires if w.isClosed()]
                if wires:
                    faces.append(Part.makeFace(wires, "Part::FaceMakerBullseye"))
        return faces
    finally:
        App.closeDocument(doc.Name)


def svg_color_solids(path, max_w, max_h, depth):
    """Filled shapes from an SVG, one solid per fill colour, all scaled together to
    fit max_w x max_h and centred on the origin, z from 0 to depth.
    Returns [(colour "#rrggbb", solid), ...] in drawing order of first appearance.
    Colours drawn later are cut out of the ones beneath, so the solids don't overlap.
    Strokes are ignored; fill="none" shapes are skipped."""
    import copy
    import xml.etree.ElementTree as ET
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    tree = ET.parse(path)

    def tag(el):
        return el.tag.rsplit("}", 1)[-1]

    # effective fill of every shape, with a stable id so copies can be filtered
    order, n = [], 0

    def walk(el, inherited):
        nonlocal n
        fill = _svg_fill(el, inherited) if tag(el) in SVG_SHAPES + ("g", "svg") else inherited
        if tag(el) in SVG_SHAPES:
            el.set("data-cadlib", str(n))
            n += 1
            if fill != "none" and fill not in order:
                order.append(fill)
            el.set("data-cadlib-fill", fill)
        for child in list(el):
            walk(child, fill)
    walk(tree.getroot(), None)

    faces = []
    for colour in order:
        t = copy.deepcopy(tree)
        parents = {c: p for p in t.iter() for c in p}
        for el in list(t.iter()):
            if tag(el) in SVG_SHAPES and el.get("data-cadlib-fill") != colour:
                parents[el].remove(el)
        fs = _svg_faces(ET.tostring(t.getroot(), encoding="unicode"))
        if fs:
            faces.append((colour, fs))
    if not faces:
        raise ValueError(f"no filled shapes in {path}")

    bb = None
    for _, fs in faces:
        for f in fs:
            if bb is None:
                bb = f.BoundBox
            else:
                bb.add(f.BoundBox)
    s = min(max_w / bb.XLength, max_h / bb.YLength)
    centre = bb.Center
    solids = []
    for colour, fs in faces:
        solid = None
        for f in fs:
            f.scale(s, centre)
            f.translate(App.Vector(-centre.x, -centre.y, 0))
            e = f.extrude(App.Vector(0, 0, depth))
            solid = e if solid is None else solid.fuse(e)
        solids.append([colour, solid.removeSplitter()])
    for i in range(len(solids)):
        for j in range(i + 1, len(solids)):
            solids[i][1] = solids[i][1].cut(solids[j][1])
    return [(c, sol) for c, sol in solids if sol.Volume > 1e-6]


def place_centered(shape, x, y, z):
    """Move shape so its XY bounding-box centre is at (x, y) and its bottom at z."""
    bb = shape.BoundBox
    shape.translate(App.Vector(x - bb.Center.x, y - bb.Center.y, z - bb.ZMin))
    return shape


def flip_for_print(shape):
    """Rotate 180 degrees about X and drop onto the bed (z = 0)."""
    s = shape.copy()
    s.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 180)
    s.translate(App.Vector(0, 0, -s.BoundBox.ZMin))
    return s


def export_mesh(shape, export_dir, name, exts=("stl", "3mf")):
    os.makedirs(export_dir, exist_ok=True)
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.02,
                                  AngularDeflection=0.1, Relative=False)
    for ext in exts:
        mesh.write(os.path.join(export_dir, f"{name}.{ext}"))


def export_parts(parts, export_dir, name):
    """Write several shapes as the parts of ONE object in a 3MF (for multi-colour prints:
    each part gets its own filament). A parent object with components, not separate
    build items: slicers then load one object, so a tiny inlay (a few mm³) isn't taken
    for a model drawn in inches, and isn't sliced as an object of its own."""
    import zipfile
    from xml.sax.saxutils import quoteattr
    os.makedirs(export_dir, exist_ok=True)
    objects, components = [], []
    for i, (part_name, shape) in enumerate(parts, start=1):
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.01,
                                      AngularDeflection=0.1, Relative=False)
        points, facets = mesh.Topology
        verts = "".join(f'<vertex x="{p.x:.5f}" y="{p.y:.5f}" z="{p.z:.5f}"/>' for p in points)
        tris = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in facets)
        objects.append(f'<object id="{i}" name={quoteattr(part_name)} type="model"><mesh>'
                       f'<vertices>{verts}</vertices><triangles>{tris}</triangles></mesh></object>')
        components.append(f'<component objectid="{i}"/>')
    parent = len(parts) + 1
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<resources>{"".join(objects)}'
             f'<object id="{parent}" name={quoteattr(name)} type="model">'
             f'<components>{"".join(components)}</components></object></resources>'
             f'<build><item objectid="{parent}"/></build></model>')
    types = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
             '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(os.path.join(export_dir, f"{name}.3mf"), "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def hex_rgb(colour):
    """'#rrggbb' -> (r, g, b) floats; anything else -> mid grey."""
    c = colour.lstrip("#")
    if len(c) != 6:
        return (0.5, 0.5, 0.5)
    return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))


def fresh_document(name):
    if name in App.listDocuments():
        App.closeDocument(name)
    return App.newDocument(name)


def show(doc, name, shape, color=None, transparency=0):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    if App.GuiUp and color is not None:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.Transparency = transparency
    return obj
