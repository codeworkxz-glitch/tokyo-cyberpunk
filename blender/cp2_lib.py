"""HEX! Cyberpunk City v2 - geometry, material and screen helpers (used by cp2_build.py).

Conventions
-----------
* 1 Blender unit = 1 Roblox stud (same as HEX_City_00_FULL_CITY.fbx). Z up.
* A Frame maps local (x, y, z) to world: x along the facade (left -> right seen from
  outside), y = depth INTO the building (negative y = projecting outwards), z up.
  Frames are right-handed (ax x ay = +Z) so faces built from them point outwards.
* Every exported object carries exactly ONE material, so each Blender object becomes
  exactly one Roblox MeshPart. Object names end in `__<KEY>` (see MATS / FLATS).
"""
import math
import os
from collections import defaultdict

import bmesh
import bpy
from mathutils import Matrix, Vector

# --------------------------------------------------------------------------- materials
# key: (material name, texture basename, tile size in studs (u, v))
MATS = {
    "GLS": ("CP_GlassCurtain", "T_GlassCurtain", (32.0, 48.0)),
    "RIB": ("CP_GlassRibbon", "T_GlassRibbon", (32.0, 24.0)),
    "PNL": ("CP_PanelMetal", "T_PanelMetal", (24.0, 24.0)),
    "CON": ("CP_ConcreteDark", "T_ConcreteDark", (32.0, 32.0)),
    "TEC": ("CP_TechPanel", "T_TechPanel", (16.0, 16.0)),
    "MEC": ("CP_Mechanical", "T_Mechanical", (8.0, 8.0)),
    "ROF": ("CP_RoofDeck", "T_RoofDeck", (32.0, 32.0)),
    "STL": ("CP_Steel", "T_Steel", (8.0, 8.0)),
    "LOU": ("CP_Louver", "T_Louver", (8.0, 12.0)),
    "TWN": ("CP_TowerNight", "T_TowerNight", (32.0, 48.0)),
}
# Flat emissive keys -> Roblox Material.Neon with this Color3 (0-255). (Blender emission strength)
FLATS = {
    "NEON_CYN": ((0, 230, 255), 7.0), "NEON_MAG": ((255, 25, 175), 7.0), "NEON_VIO": ((150, 45, 255), 7.5),
    "NEON_BLU": ((30, 95, 255), 8.0), "NEON_RED": ((255, 32, 45), 7.0), "NEON_AMB": ((255, 150, 25), 6.0),
    "NEON_WHT": ((215, 228, 255), 4.0),
    "WIN_WRM": ((255, 190, 125), 1.1), "WIN_COL": ((140, 195, 255), 1.1), "WIN_PNK": ((255, 120, 200), 1.3),
    "WIN_VIO": ((170, 130, 255), 1.3), "SHOP_LIT": ((255, 232, 205), 1.3),
}
# Sign atlases from the original map (re-used for storefront / blade signage)
SIGNS = {"SGH": ("CP_SignsH", "signs_h"), "SGV": ("CP_SignsV", "signs_v")}

NEONS = ["NEON_CYN", "NEON_MAG", "NEON_VIO", "NEON_BLU", "NEON_RED", "NEON_AMB", "NEON_WHT"]
FLOOR = 12.0           # upper floor height (studs) - matches the glass textures
BAY = 32.0 / 6.0       # curtain-wall bay width (studs)

_mat_cache = {}
TEX_DIR = None


def set_tex_dir(d):
    global TEX_DIR
    TEX_DIR = d


def _img(name, colorspace="sRGB"):
    path = os.path.join(TEX_DIR, name + ".png")
    key = (name, colorspace)
    for im in bpy.data.images:
        if im.get("cp_key") == "|".join(key):
            return im
    im = bpy.data.images.load(path, check_existing=False)
    im.name = name
    im["cp_key"] = "|".join(key)
    im.colorspace_settings.name = colorspace
    return im


def material(key):
    """Blender material for a key (PBR image set, flat emissive, sign atlas or AD_*)."""
    if key in _mat_cache:
        return _mat_cache[key]
    if key in MATS:
        name = MATS[key][0]
    elif key in FLATS:
        name = "CP_" + key
    elif key in SIGNS:
        name = SIGNS[key][0]
    else:
        name = key  # AD_xxx
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    if key in MATS:
        base = MATS[key][1]
        tc = nt.nodes.new("ShaderNodeTexImage"); tc.image = _img(base + "_Color"); tc.location = (-500, 300)
        tr = nt.nodes.new("ShaderNodeTexImage"); tr.image = _img(base + "_Roughness", "Non-Color"); tr.location = (-500, 0)
        tm = nt.nodes.new("ShaderNodeTexImage"); tm.image = _img(base + "_Metalness", "Non-Color"); tm.location = (-500, -300)
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = _img(base + "_Normal", "Non-Color"); tn.location = (-500, -600)
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.location = (-200, -600)
        nt.links.new(tc.outputs[0], bsdf.inputs["Base Color"])
        nt.links.new(tr.outputs[0], bsdf.inputs["Roughness"])
        nt.links.new(tm.outputs[0], bsdf.inputs["Metallic"])
        nt.links.new(tn.outputs[0], nm.inputs["Color"])
        nt.links.new(nm.outputs[0], bsdf.inputs["Normal"])
    elif key in FLATS:
        c, strength = FLATS[key]
        col = tuple((v / 255.0) ** 2.2 for v in c) + (1.0,)
        bsdf.inputs["Base Color"].default_value = col
        bsdf.inputs["Emission Color"].default_value = col
        bsdf.inputs["Emission Strength"].default_value = strength
        bsdf.inputs["Roughness"].default_value = 0.4
        tc = nt.nodes.new("ShaderNodeTexImage"); tc.image = _img("F_" + key); tc.location = (-500, 300)
        # swatch only feeds the FBX texture slot; colour comes from the constant above
        m.diffuse_color = col
    else:
        im = _img(SIGNS[key][1] if key in SIGNS else key)
        tc = nt.nodes.new("ShaderNodeTexImage"); tc.image = im; tc.location = (-500, 200)
        nt.links.new(tc.outputs[0], bsdf.inputs["Base Color"])
        nt.links.new(tc.outputs[0], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.5 if key.startswith("AD_") else 1.1
        bsdf.inputs["Roughness"].default_value = 0.25
    _mat_cache[key] = m
    return m


# --------------------------------------------------------------------------- frames
class Frame:
    def __init__(self, origin, ax, ay):
        self.o = Vector(origin)
        self.ax = Vector(ax).normalized()
        self.ay = Vector(ay).normalized()
        self.az = Vector((0, 0, 1))

    def w(self, x, y, z):
        return self.o + self.ax * x + self.ay * y + self.az * z

    def d(self, x, y, z=0.0):
        return self.ax * x + self.ay * y + self.az * z

    def sub(self, x, y, ax2, ay2, z=0.0):
        """Child frame at local (x, y, z) whose axes are given in this frame's xy plane."""
        return Frame(self.w(x, y, z), self.d(*ax2), self.d(*ay2))

    def wall(self, a, b):
        """Frame on the footprint edge a->b (local xy, CCW footprint): x along edge, y inward."""
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        return Frame(self.w(a[0], a[1], 0), self.d(ux, uy), self.d(-uy, ux)), L


# --------------------------------------------------------------------------- geometry buffer
def newell(pts):
    n = Vector((0, 0, 0))
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]
        n.x += (p.y - q.y) * (p.z + q.z)
        n.y += (p.z - q.z) * (p.x + q.x)
        n.z += (p.x - q.x) * (p.y + q.y)
    return n.normalized() if n.length > 1e-9 else Vector((0, 0, 1))


def tile_of(key):
    if key in MATS:
        return MATS[key][2]
    return (8.0, 8.0)


class Geo:
    """Accumulates faces per material key; flushed into one object per key."""

    def __init__(self):
        self.b = defaultdict(lambda: ([], [], []))

    def face(self, key, pts, uv=None, o=None):
        V, Fc, U = self.b[key]
        base = len(V)
        V.extend(pts)
        Fc.append(tuple(range(base, base + len(pts))))
        if uv is None:
            uv = auto_uv(pts, key, o)
        U.extend(uv)

    def tris(self):
        return sum(sum(len(f) - 2 for f in v[1]) for v in self.b.values())


def auto_uv(pts, key, o=None):
    tw, th = tile_of(key)
    n = newell(pts)
    o = o if o is not None else Vector((0, 0, 0))
    if abs(n.z) > 0.7:
        return [((p.x - o.x) / tw, (p.y - o.y) / tw) for p in pts]
    t = Vector((-n.y, n.x, 0)).normalized()
    return [((p - o).dot(t) / tw, (p.z - o.z) / th) for p in pts]


# --------------------------------------------------------------------------- primitives
FACES = ("front", "back", "left", "right", "top", "bottom")


def box(g, F, x0, y0, z0, x1, y1, z1, key, skip=(), keys=None, o=None):
    if x1 < x0: x0, x1 = x1, x0
    if y1 < y0: y0, y1 = y1, y0
    if z1 < z0: z0, z1 = z1, z0
    w = F.w
    quads = {
        "front": (w(x0, y0, z0), w(x1, y0, z0), w(x1, y0, z1), w(x0, y0, z1)),
        "back": (w(x1, y1, z0), w(x0, y1, z0), w(x0, y1, z1), w(x1, y1, z1)),
        "left": (w(x0, y1, z0), w(x0, y0, z0), w(x0, y0, z1), w(x0, y1, z1)),
        "right": (w(x1, y0, z0), w(x1, y1, z0), w(x1, y1, z1), w(x1, y0, z1)),
        "top": (w(x0, y0, z1), w(x1, y0, z1), w(x1, y1, z1), w(x0, y1, z1)),
        "bottom": (w(x0, y1, z0), w(x1, y1, z0), w(x1, y0, z0), w(x0, y0, z0)),
    }
    for k, q in quads.items():
        if k in skip:
            continue
        g.face((keys or {}).get(k, key), list(q), o=o)


def quad(g, F, x0, z0, x1, z1, y, key, uv=None, o=None):
    """Facade-plane quad at depth y facing -y (outwards)."""
    g.face(key, [F.w(x0, y, z0), F.w(x1, y, z0), F.w(x1, y, z1), F.w(x0, y, z1)], uv=uv, o=o)


def prism(g, F, poly, z0, z1, side, top=None, bottom=None, o=None, side_keys=None):
    """Extrude a CCW local-xy polygon. side_keys: optional per-edge key list."""
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        k = side_keys[i] if side_keys else side
        if k is None:
            continue
        g.face(k, [F.w(a[0], a[1], z0), F.w(b[0], b[1], z0), F.w(b[0], b[1], z1), F.w(a[0], a[1], z1)], o=o)
    if top:
        g.face(top, [F.w(p[0], p[1], z1) for p in poly])
    if bottom:
        g.face(bottom, [F.w(p[0], p[1], z0) for p in reversed(poly)])


def _basis(d):
    d = d.normalized()
    ref = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
    u = d.cross(ref).normalized()
    v = d.cross(u).normalized()
    return u, v


def tube(g, p0, p1, r, key, n=6, caps=False):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    if d.length < 1e-6:
        return
    u, v = _basis(d)
    ring0, ring1 = [], []
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        off = (u * math.cos(a) + v * math.sin(a)) * r
        ring0.append(p0 + off)
        ring1.append(p1 + off)
    L = d.length
    circ = 2 * math.pi * r / 8.0
    for i in range(n):
        j = (i + 1) % n
        u0, u1 = circ * i / n, circ * (i + 1) / n
        g.face(key, [ring0[i], ring0[j], ring1[j], ring1[i]], uv=[(u0, 0), (u1, 0), (u1, L / 8), (u0, L / 8)])
    if caps:
        g.face(key, ring1)
        g.face(key, list(reversed(ring0)))


def beam(g, p0, p1, w, key, h=None):
    """Square/rect section member between two world points."""
    tube(g, p0, p1, (w * 0.7071), key, n=4, caps=False)


def cylinder(g, F, cx, cy, r, z0, z1, key, n=16, top=None, bottom=None, a0=0.0, a1=2 * math.pi):
    full = abs((a1 - a0) - 2 * math.pi) < 1e-6
    pts = []
    m = n if full else n + 1
    for i in range(m):
        a = a0 + (a1 - a0) * i / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    if full:
        prism(g, F, pts, z0, z1, key, top=top, bottom=bottom)
    else:
        for i in range(n):
            a, b = pts[i], pts[i + 1]
            g.face(key, [F.w(a[0], a[1], z0), F.w(b[0], b[1], z0), F.w(b[0], b[1], z1), F.w(a[0], a[1], z1)])


def circle_poly(cx, cy, r, n, a0=0.0):
    return [(cx + r * math.cos(a0 + 2 * math.pi * i / n), cy + r * math.sin(a0 + 2 * math.pi * i / n)) for i in range(n)]


def chamfer_rect(x0, y0, x1, y1, c, corners=(1, 1, 1, 1)):
    """CCW rectangle with chamfered corners; corner order (x0,y0),(x1,y0),(x1,y1),(x0,y1)."""
    cut = [((x0, y0 + c), (x0 + c, y0)), ((x1 - c, y0), (x1, y0 + c)),
           ((x1, y1 - c), (x1 - c, y1)), ((x0 + c, y1), (x0, y1 - c))]
    raw = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    pts = []
    for i in range(4):
        if corners[i] and c > 0:
            pts += list(cut[i])
        else:
            pts.append(raw[i])
    return pts


def _ccw(pts):
    a = 0.0
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]
        a += p[0] * q[1] - q[0] * p[1]
    return pts if a > 0 else list(reversed(pts))


def rounded_rect(x0, y0, x1, y1, r, n=4, corners=(1, 1, 1, 1)):
    pts = []
    cs = [(x0 + r, y0 + r, math.pi, 1.5 * math.pi), (x1 - r, y0 + r, 1.5 * math.pi, 2 * math.pi),
          (x1 - r, y1 - r, 0.0, 0.5 * math.pi), (x0 + r, y1 - r, 0.5 * math.pi, math.pi)]
    raw = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for i, (cx, cy, a0, a1) in enumerate(cs):
        if corners[i]:
            for k in range(n + 1):
                a = a0 + (a1 - a0) * k / n
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        else:
            pts.append(raw[i])
    return pts


# --------------------------------------------------------------------------- objects
COLL = {}


def coll(name, parent=None):
    if name in COLL:
        return COLL[name]
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    par = parent or bpy.context.scene.collection
    if c.name not in par.children:
        par.children.link(c)
    COLL[name] = c
    return c


MAX_TRIS = 18000  # Roblox MeshPart import limit is 20k triangles


def make_object(name, verts, faces, uvs, key, collection, merge=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    uvl = me.uv_layers.new(name="UVMap")
    flat = [c for uv in uvs for c in uv]
    uvl.data.foreach_set("uv", flat)
    me.materials.append(material(key))
    bm = bmesh.new()
    bm.from_mesh(me)
    if merge:
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.002)
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(me)
    bm.free()
    me.set_sharp_from_angle(angle=math.radians(35))
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    return ob


def flush(g, prefix, collection, out_list=None):
    """Turn a Geo into objects `<prefix>__<KEY>` (split if over the Roblox triangle limit)."""
    objs = []
    for key, (V, Fc, U) in g.b.items():
        if not Fc:
            continue
        # split face list into chunks below MAX_TRIS
        chunks, cur, curt = [], [], 0
        for f in Fc:
            t = len(f) - 2
            if curt + t > MAX_TRIS and cur:
                chunks.append(cur); cur, curt = [], 0
            cur.append(f); curt += t
        if cur:
            chunks.append(cur)
        for ci, ch in enumerate(chunks):
            idx = sorted({i for f in ch for i in f})
            remap = {i: k for k, i in enumerate(idx)}
            verts = [V[i] for i in idx]
            faces = [tuple(remap[i] for i in f) for f in ch]
            uvs = [U[i] for f in ch for i in f]
            nm = f"{prefix}__{key}" + (f"_{ci + 1}" if len(chunks) > 1 else "")
            ob = make_object(nm, verts, faces, uvs, key, collection)
            objs.append(ob)
    if out_list is not None:
        out_list.extend(objs)
    return objs


# --------------------------------------------------------------------------- screens
SCREENS = []     # data records for Roblox (SurfaceGui placement)
LIGHTS = []      # data records for Roblox lights
AD_FORMATS = {}  # ad name -> (fmt, aspect)
AD_SIZES = {}    # ad name -> (w, h) pixels
_ad_use = defaultdict(int)
FMT_ASPECT = {"W": 2.0, "X": 4.0, "P": 8 / 3, "T": 0.5, "S": 0.25, "Q": 1.0}


def load_ads(index_path):
    for line in open(index_path):
        name, fmt, size = line.strip().split("\t")
        w, h = map(int, size.split("x"))
        AD_FORMATS[name] = (fmt, w / h)
        AD_SIZES[name] = (w, h)


def pick_ad(fmt, rng, avoid=()):
    cands = [n for n, (f, _) in AD_FORMATS.items() if f == fmt and n not in avoid]
    if not cands:
        cands = [n for n, (f, _) in AD_FORMATS.items() if f == fmt]
    m = min(_ad_use[c] for c in cands)
    best = [c for c in cands if _ad_use[c] <= m + 1]
    c = best[rng.randrange(len(best))]
    _ad_use[c] += 1
    return c


def fmt_for(aspect):
    return min(FMT_ASPECT, key=lambda f: abs(math.log(FMT_ASPECT[f] / aspect)))


def screen(F, x0, z0, x1, z1, y, name, collection, rng, kind="facade", fmt=None, ad=None, layer=0):
    """Flat screen in frame F at depth y facing -y. Returns (object, record)."""
    w, h = abs(x1 - x0), abs(z1 - z0)
    fmt = fmt or fmt_for(w / h)
    ad = ad or pick_ad(fmt, rng)
    p = [F.w(x0, y, z0), F.w(x1, y, z0), F.w(x1, y, z1), F.w(x0, y, z1)]
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in p], [], [(0, 1, 2, 3)])
    uvl = me.uv_layers.new(name="UVMap")
    uvl.data.foreach_set("uv", [0, 0, 1, 0, 1, 1, 0, 1])
    me.materials.append(material(ad))
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    c = (p[0] + p[2]) / 2
    nrm = -F.ay
    rec = {"name": name, "ad": ad, "fmt": fmt, "kind": kind, "layer": layer,
           "panels": [{"c": tuple(c), "n": tuple(nrm), "r": tuple(F.ax), "w": w, "h": h, "u0": 0.0, "u1": 1.0}]}
    SCREENS.append(rec)
    return ob, rec


def curved_screen(F, cx, cy, r, a0, a1, z0, z1, name, collection, rng, segs=12, kind="curved", fmt="P", ad=None):
    """Convex screen wrapping a cylinder of radius r around local (cx, cy), from angle a0 to a1
    (counter-clockwise seen from above, so the picture reads left->right from outside)."""
    ad = ad or pick_ad(fmt, rng)
    verts, faces, uvs, panels = [], [], [], []
    pts = [(cx + r * math.cos(a0 + (a1 - a0) * i / segs), cy + r * math.sin(a0 + (a1 - a0) * i / segs)) for i in range(segs + 1)]
    for i in range(segs):
        a, b = pts[i], pts[i + 1]
        u0, u1 = i / segs, (i + 1) / segs
        q = [F.w(a[0], a[1], z0), F.w(b[0], b[1], z0), F.w(b[0], b[1], z1), F.w(a[0], a[1], z1)]
        base = len(verts)
        verts += q
        faces.append((base, base + 1, base + 2, base + 3))
        uvs += [u0, 0, u1, 0, u1, 1, u0, 1]
        right = (q[1] - q[0]).normalized()
        nrm = right.cross(Vector((0, 0, 1))).normalized()
        panels.append({"c": tuple((q[0] + q[2]) / 2), "n": tuple(nrm), "r": tuple(right),
                       "w": (q[1] - q[0]).length, "h": z1 - z0, "u0": u0, "u1": u1})
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.uv_layers.new(name="UVMap").data.foreach_set("uv", uvs)
    me.materials.append(material(ad))
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    rec = {"name": name, "ad": ad, "fmt": fmt, "kind": kind, "layer": 0, "panels": panels}
    SCREENS.append(rec)
    return ob, rec


def light(pos, color, rng_studs, brightness, kind="point", direction=None, angle=None, name=""):
    LIGHTS.append({"pos": tuple(pos), "color": tuple(color), "range": rng_studs, "brightness": brightness,
                   "kind": kind, "dir": tuple(direction) if direction else None, "angle": angle, "name": name})


# --------------------------------------------------------------------------- props (instanced)
PROTOS = {}


def proto(name, builder, collection):
    """Build a prop prototype mesh once; returns {key: mesh}."""
    if name in PROTOS:
        return PROTOS[name]
    g = Geo()
    builder(g)
    meshes = {}
    for key, (V, Fc, U) in g.b.items():
        ob = make_object(f"PROTO_{name}__{key}", V, Fc, U, key, collection)
        meshes[key] = ob.data
        ob.hide_render = True
        ob.hide_viewport = True
        ob["cp_proto"] = True
    PROTOS[name] = meshes
    return meshes


def place(name, meshes, loc, rot_z, collection, scale=1.0):
    obs = []
    for key, me in meshes.items():
        ob = bpy.data.objects.new(f"{name}__{key}", me)
        ob.matrix_world = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(rot_z, 4, "Z") @ Matrix.Scale(scale, 4)
        collection.objects.link(ob)
        obs.append(ob)
    return obs
