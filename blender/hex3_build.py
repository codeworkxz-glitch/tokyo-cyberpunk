"""HEX! City v3 - the ORIGINAL map, far more detailed, with game ads that all rotate.

    /opt/bvenv/bin/python blender/hex3_build.py

File A  HEX_City_v3_A.fbx  the original HEX_City_00_FULL_CITY.fbx, every object unchanged.
File B  HEX_City_v3_B.fbx  everything new:
  * a rotating screen on every one of the 576 original billboards (exact display face,
    0-1 UVs, separate mesh) + lit rooftop billboards + big LED screens on the landmarks
  * Center-gai style street lamps (twin globes, arch sign, pole banners)
  * string lights across the side streets, pedestrian signals, vertical tenant signs
Roblox data (export_v3/roblox/CityData.lua): screen panels, glow panels for every lit
sign of the original map, lights, alignment references.
"""
import math
import os
import random
import shutil
import sys
import time

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cp2_lib as L  # noqa: E402

ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "assets", "HEX_City_00_FULL_CITY.fbx")
EX = os.path.join(ROOT, "export_v3")
TEX = os.path.join(EX, "textures")
OLD_TEX = os.path.join(ROOT, "export", "textures")
OUT_BLEND = os.path.join(ROOT, "output", "HEX_City_v3.blend")
FMT = {"S3": 1 / 3, "T": 0.5, "V": 0.75, "Q": 1.0, "L": 1.5, "W": 2.0, "X3": 3.0}
t0 = time.time()

L.FLATS.update({"LAMP": ((255, 236, 205), 4.0), "SIG_RED": ((255, 40, 40), 6.0), "SIG_GRN": ((40, 255, 150), 6.0),
                "BULB": ((255, 214, 150), 5.0)})
L.FMT_ASPECT.clear()
L.FMT_ASPECT.update(FMT)


def log(*a):
    print(f"[{time.time() - t0:6.1f}s]", *a, flush=True)


def wbbox(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(c[i] for c in cs) for i in range(3)]), Vector([max(c[i] for c in cs) for i in range(3)])


def rb(v):  # Blender -> Roblox axes
    return [round(v[0], 3), round(v[2], 3), round(-v[1], 3)]


# ----------------------------------------------------------------------------- textures
def prepare_textures():
    os.makedirs(TEX, exist_ok=True)
    for base in ("T_Steel", "T_PanelMetal", "T_Mechanical", "T_ConcreteDark", "T_TechPanel"):
        for m in ("Color", "Normal", "Roughness", "Metalness"):
            shutil.copy(os.path.join(OLD_TEX, f"{base}_{m}.png"), TEX)
    from PIL import Image, ImageDraw, ImageFont
    for k, (c, _) in L.FLATS.items():
        Image.new("RGB", (16, 16), c).save(os.path.join(TEX, f"F_{k}.png"))
    jp = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
    bold = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
    # arch sign of the street lamps (cream plate, dark green lettering - like 渋谷センター街)
    im = Image.new("RGB", (1024, 256), (238, 240, 214))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([10, 10, 1014, 246], 60, outline=(70, 110, 60), width=10)
    d.text((512, 120), "HEX センター街", font=ImageFont.truetype(jp, 120), fill=(30, 60, 36), anchor="mm")
    d.text((512, 212), "HEX CENTER STREET", font=ImageFont.truetype(bold, 34), fill=(70, 110, 60), anchor="mm")
    im.save(os.path.join(TEX, "LAMPSIGN.png"))
    # pole banners
    specs = [("BANNER_Welcome", (232, 64, 26), "WELCOME", "TO HEX", "ようこそ"),
             ("BANNER_League", (26, 74, 255), "HEX", "LEAGUE", "開幕"),
             ("BANNER_Storm", (20, 22, 28), "GO", "STORM", "渋谷")]
    for name, col, a, b, j in specs:
        im = Image.new("RGB", (256, 640), col)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 255, 40], fill=(255, 255, 255))
        d.rectangle([0, 600, 255, 639], fill=(255, 255, 255))
        d.ellipse([58, 80, 198, 220], outline=(255, 255, 255), width=10)
        d.text((128, 150), "H", font=ImageFont.truetype(bold, 90), fill=(255, 255, 255), anchor="mm")
        d.text((128, 300), a, font=ImageFont.truetype(bold, 52), fill=(255, 255, 255), anchor="mm")
        d.text((128, 370), b, font=ImageFont.truetype(bold, 52), fill=(255, 255, 255), anchor="mm")
        d.text((128, 480), j, font=ImageFont.truetype(jp, 64), fill=(255, 255, 255), anchor="mm")
        im.save(os.path.join(TEX, name + ".png"))


# ----------------------------------------------------------------------------- import
def import_original():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    bpy.ops.import_scene.fbx(filepath=SRC)
    for im in bpy.data.images:
        if im.packed_file and im.filepath:
            dst = os.path.join(TEX, os.path.basename(im.filepath))
            with open(dst, "wb") as f:
                f.write(im.packed_file.data)
            im.unpack(method="REMOVE") if False else None
    log("imported", len(bpy.data.objects), "original objects")


# ----------------------------------------------------------------------------- face analysis
def face_groups(o, min_frac=0.25):
    """Large vertical faces of a box-like sign/billboard grouped by side (front / back).
    Returns [(normal, [poly...])]."""
    me = o.data
    mw = o.matrix_world
    m3 = mw.to_3x3()
    polys = list(me.polygons)
    if not polys:
        return []
    amax = max(p.area for p in polys)
    big = max(polys, key=lambda p: p.area)
    nb = (m3 @ big.normal).normalized()
    front, back = [], []
    for p in polys:
        n = (m3 @ p.normal).normalized()
        if p.area < amax * min_frac or abs(n.z) > 0.5:
            continue
        (front if n.dot(nb) > 0 else back).append(p)
    out = []
    if front:
        out.append(front)
    if back:
        out.append(back)
    return out


def panel_of(o, polys, uvmap):
    """SurfaceGui panel (centre, normal, right, w, h, u0, u1, uvrect) for coplanar-ish faces.
    uvmap(u, v) -> (u', v') maps raw UVs (e.g. into a billboard cell)."""
    me = o.data
    mw = o.matrix_world
    uvl = me.uv_layers.active.data
    pts, uvs = [], []
    nacc = Vector((0, 0, 0))
    tu = Vector((0, 0, 0))
    for p in polys:
        nacc += (mw.to_3x3() @ p.normal) * p.area
        li = list(p.loop_indices)
        P = [mw @ me.vertices[me.loops[i].vertex_index].co for i in li]
        U = [uvmap(*uvl[i].uv) for i in li]
        pts += P
        uvs += U
        e1, e2 = P[1] - P[0], P[2] - P[0]
        du1, dv1 = U[1][0] - U[0][0], U[1][1] - U[0][1]
        du2, dv2 = U[2][0] - U[0][0], U[2][1] - U[0][1]
        det = du1 * dv2 - du2 * dv1
        if abs(det) > 1e-9:
            tu += (e1 * dv2 - e2 * dv1) / det
    n = nacc.normalized()
    r = (tu - n * tu.dot(n))
    if r.length < 1e-6:
        r = n.cross(Vector((0, 0, 1)))
    r.normalize()
    up = n.cross(r).normalized()
    mirrored = False
    if up.z < 0:  # texture mapped mirrored on this side: show it readable instead
        r = -r
        up = n.cross(r).normalized()
        mirrored = True
    c0 = sum(pts, Vector((0, 0, 0))) / len(pts)
    xs = [(q - c0).dot(r) for q in pts]
    zs = [(q - c0).dot(up) for q in pts]
    c = c0 + r * (min(xs) + max(xs)) / 2 + up * (min(zs) + max(zs)) / 2
    us = [u for u, _ in uvs]
    vs = [v for _, v in uvs]
    return {"c": tuple(c), "n": tuple(n), "r": tuple(r), "w": max(xs) - min(xs), "h": max(zs) - min(zs),
            "u0": max(0.0, min(us)), "u1": min(1.0, max(us)), "uv": (min(us), min(vs), max(us), max(vs)),
            "mirrored": mirrored}


def cell_of(o):
    """Atlas cell (4x4 grid) of a billboard from its largest face."""
    me = o.data
    uvl = me.uv_layers.active.data
    big = max(me.polygons, key=lambda p: p.area)
    us = [uvl[i].uv for i in big.loop_indices]
    cu = sum(u.x for u in us) / len(us)
    cv = sum(u.y for u in us) / len(us)
    i, j = min(3, int(cu * 4)), min(3, int(cv * 4))
    return (i / 4 + 0.002, j / 4 + 0.002, (i + 1) / 4 - 0.002, (j + 1) / 4 - 0.002)


# ----------------------------------------------------------------------------- screens on billboards
def billboard_screens(C):
    rng = random.Random(7)
    n = 0
    for o in sorted([o for o in bpy.data.objects if o.name.startswith("Billboard_")], key=lambda o: o.name):
        x0, y0, x1, y1 = cell_of(o)
        cw, ch = x1 - x0, y1 - y0
        um = lambda u, v: ((u - x0) / cw, (v - y0) / ch)
        groups = face_groups(o, 0.25 if "Curved" not in o.name else 0.2)
        for gi, polys in enumerate(groups):
            # only faces that really show the cell (the back of a billboard may be blank)
            uvl = o.data.uv_layers.active.data
            inside = []
            for p in polys:
                cu = sum(uvl[i].uv.x for i in p.loop_indices) / p.loop_total
                cv = sum(uvl[i].uv.y for i in p.loop_indices) / p.loop_total
                if x0 - 0.01 <= cu <= x1 + 0.01 and y0 - 0.01 <= cv <= y1 + 0.01:
                    inside.append(p)
            if not inside:
                continue
            curved = "Curved" in o.name
            if curved:  # one panel per facet so the SurfaceGuis follow the curve
                panels = [panel_of(o, [p], um) for p in sorted(inside, key=lambda p: min(
                    um(*uvl[i].uv)[0] for i in p.loop_indices))]
                panels = [q for q in panels if q["w"] > 0.05 and q["h"] > 0.5]
                width = sum(q["w"] for q in panels)
                height = max(q["h"] for q in panels)
            else:
                panels = [panel_of(o, inside, um)]
                width, height = panels[0]["w"], panels[0]["h"]
            if not panels or height < 0.5:
                continue
            asp = width / height
            fmt = min(FMT, key=lambda f: abs(math.log(FMT[f] / asp)))
            ad = L.pick_ad(fmt, rng)
            # screen mesh: copy of the display faces 0.06 in front, 0-1 UVs inside the cell
            me = o.data
            mw = o.matrix_world
            verts, faces, uvs = [], [], []
            for p in inside:
                nrm = (mw.to_3x3() @ p.normal).normalized()
                base = len(verts)
                for li in p.loop_indices:
                    verts.append(tuple(mw @ me.vertices[me.loops[li].vertex_index].co + nrm * 0.06))
                    u, v = um(*uvl[li].uv)
                    uvs += [min(1, max(0, u)), min(1, max(0, v))]
                faces.append(tuple(range(base, base + p.loop_total)))
            if panels[0]["mirrored"]:
                uvs = [1 - x if k % 2 == 0 else x for k, x in enumerate(uvs)]
            name = f"SCR_{o.name}" + ("" if gi == 0 else "_back")
            sm = bpy.data.meshes.new(name)
            sm.from_pydata(verts, [], faces)
            sm.uv_layers.new(name="UVMap").data.foreach_set("uv", uvs)
            sm.materials.append(L.material(ad))
            so = bpy.data.objects.new(name, sm)
            C["scr"].objects.link(so)
            L.SCREENS.append({"name": name, "ad": ad, "fmt": fmt, "kind": "billboard", "layer": 0, "panels": [
                {k: q[k] for k in ("c", "n", "r", "w", "h", "u0", "u1")} for q in panels]})
            n += 1
            if width * height > 500:
                c = Vector(panels[len(panels) // 2]["c"]) + Vector(panels[len(panels) // 2]["n"]) * 6
                L.light(c, (255, 245, 230), 40, 1.0, kind="surface", direction=panels[len(panels) // 2]["n"],
                        name=name)
    log("billboard screens:", n)


# ----------------------------------------------------------------------------- lit sign glow
SIGN_GLOW = []


def sign_glow():
    for o in sorted(bpy.data.objects, key=lambda o: o.name):
        if not o.name.startswith("Sign_") or not o.data.materials:
            continue
        mn = o.data.materials[0].name
        if not mn.endswith("_Lit"):
            continue
        atlas = "H" if mn.startswith("SignH") else "V"
        panels = []
        for polys in face_groups(o, 0.6):
            q = panel_of(o, polys, lambda u, v: (u, v))
            if q["w"] > 0.3 and q["h"] > 0.3:
                panels.append(q)
        if panels:
            SIGN_GLOW.append({"name": o.name, "atlas": atlas, "panels": panels})
    log("lit sign glow entries:", len(SIGN_GLOW))


# ----------------------------------------------------------------------------- detail kit
def globe(g, c, r, key, n=10):
    """Lamp globe: 4-ring faceted sphere."""
    rings = [(-1.0, 0.0), (-0.7, 0.72), (0.0, 1.0), (0.7, 0.72), (1.0, 0.0)]
    pts = []
    for zf, rf in rings:
        pts.append([Vector((c[0] + r * rf * math.cos(2 * math.pi * i / n), c[1] + r * rf * math.sin(2 * math.pi * i / n),
                            c[2] + r * zf)) for i in range(n)])
    for k in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            a, b, cc, d = pts[k][i], pts[k][j], pts[k + 1][j], pts[k + 1][i]
            if k == 0:
                g.face(key, [a, cc, d])
            elif k == len(rings) - 2:
                g.face(key, [a, b, cc])
            else:
                g.face(key, [a, b, cc, d])


def street_lamp(g, F, x, y, sign_flip=False, banner=None):
    """Center-gai lamp: pole, crossarm with two globes, arch sign plate, two pole banners.
    F: frame whose x runs along the street, y towards the street (outward)."""
    W = F.w
    L.tube(g, W(x, y, 0), W(x, y, 19.5), 0.32, "STL", n=8)
    L.box(g, F, x - 0.6, y - 0.6, 0, x + 0.6, y + 0.6, 1.0, "STL", skip=("bottom",))
    L.tube(g, W(x, y - 3.2, 19.0), W(x, y + 3.2, 19.0), 0.18, "STL", n=6)
    for s in (-1, 1):
        L.tube(g, W(x, y + s * 3.0, 19.0), W(x, y + s * 3.0, 19.6), 0.1, "STL", n=4)
        globe(g, (W(x, y + s * 3.0, 20.6)), 1.15, "LAMP")
        L.light(W(x, y + s * 3.0, 20.6), (255, 226, 190), 26, 1.3, name="lamp")
    # arch sign plate under the crossarm, readable from both sides of the street
    Fs = L.Frame(W(x, y, 0), F.ay, -F.ax)
    L.box(g, Fs, -3.0, -0.2, 15.6, 3.0, 0.2, 18.2, "STL", skip=("front", "back"))
    L.quad(g, Fs, -2.9, 15.7, 2.9, 18.1, -0.22, "LAMPSIGN", uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    Fb = L.Frame(W(x, y, 0), -F.ay, F.ax)
    L.quad(g, Fb, -2.9, 15.7, 2.9, 18.1, -0.22, "LAMPSIGN", uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    for k in (0, 1):
        L.tube(g, W(x, y, 15.4), W(x, y, 15.4), 0.1, "STL")
    # pole banners on short arms (one each side of the pole)
    if banner:
        for s, bkey in ((-1, banner[0]), (1, banner[1])):
            L.tube(g, W(x, y, 13.6), W(x + s * 2.2, y, 13.6), 0.07, "STL", n=4)
            Fx = L.Frame(W(x, y, 0), F.ax, F.ay)
            xa, xb = (x - 2.2, x - 0.4) if s < 0 else (x + 0.4, x + 2.2)
            L.quad(g, Fx, xa, 9.2, xb, 13.5, -0.02, bkey, uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
            Fx2 = L.Frame(W(x, y, 0), -F.ax, -F.ay)
            L.quad(g, Fx2, -xb, 9.2, -xa, 13.5, -0.02, bkey, uv=[(0, 0), (1, 0), (1, 1), (0, 1)])


def ped_signal(g, F, x, y, facing):
    """Pedestrian signal pole with two lit heads (red over green), facing +/- F.ay."""
    W = F.w
    L.tube(g, W(x, y, 0), W(x, y, 11.0), 0.25, "STL", n=6)
    Fh = L.Frame(W(x, y, 0), F.ax * facing, F.ay * -facing) if facing else F
    Fh = L.Frame(W(x, y, 0), F.ax if facing > 0 else -F.ax, -F.ay if facing > 0 else F.ay)
    L.box(g, Fh, -0.75, -0.9, 7.2, 0.75, -0.25, 10.6, "STL")
    L.quad(g, Fh, -0.55, 9.0, 0.55, 10.3, -0.92, "SIG_RED")
    L.quad(g, Fh, -0.55, 7.5, 0.55, 8.8, -0.92, "TEC")


def string_lights(g, p0, p1, sag, n=14):
    pts = []
    for i in range(n + 1):
        t = i / n
        p = p0.lerp(p1, t)
        p.z -= sag * 4 * t * (1 - t)
        pts.append(p)
    for a, b in zip(pts, pts[1:]):
        L.tube(g, a, b, 0.05, "STL", n=3)
    for p in pts[1:-1]:
        globe(g, (p.x, p.y, p.z - 0.45), 0.32, "BULB", n=6)


# ----------------------------------------------------------------------------- placement
def collect():
    """Foreground rows (front line / along-axis ranges), side-street gaps, landmark lots."""
    rows = {"N": [], "S": [], "E": [], "W": []}
    obstacles = []
    children = {}
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        n = o.name
        if n.startswith(("UtilityPole", "LightMast", "Stair", "Skybridge")):
            obstacles.append(wbbox(o))
        if o.parent is not None:
            children.setdefault(o.parent.name, []).append(wbbox(o))
        if o.parent is None and n.startswith("FG_") and not n.startswith("FG_Corner") and "_Back" not in n:
            rows[n.split("_")[1]].append((n, *wbbox(o), o))
    return rows, obstacles, children


def row_axes(r):
    # along-street axis (ax), outward to the plaza street (out), front coordinate getter
    return {"N": ((1, 0, 0), (0, -1, 0), lambda mn, mx: mn.y),
            "S": ((-1, 0, 0), (0, 1, 0), lambda mn, mx: mx.y),
            "E": ((0, -1, 0), (-1, 0, 0), lambda mn, mx: mn.x),
            "W": ((0, 1, 0), (1, 0, 0), lambda mn, mx: mx.x)}[r]


def near_obstacle(p, obstacles, d=4.0):
    for mn, mx in obstacles:
        if mn.x - d < p.x < mx.x + d and mn.y - d < p.y < mx.y + d:
            return True
    return False


def overlaps(bmn, bmx, boxes, pad=0.5):
    for mn, mx in boxes:
        if (bmn.x < mx.x + pad and bmx.x > mn.x - pad and bmn.y < mx.y + pad and bmx.y > mn.y - pad
                and bmn.z < mx.z + pad and bmx.z > mn.z - pad):
            return True
    return False


def build_streets(C, rows, obstacles):
    g = L.Geo()
    banners = ["BANNER_Welcome", "BANNER_League", "BANNER_Storm"]
    nl = 0
    gaps = []
    for r, items in rows.items():
        ax, out, front = row_axes(r)
        ax, out = Vector(ax), Vector(out)
        items.sort(key=lambda it: Vector(((it[1] + it[2]) / 2)).dot(ax))
        fr = sorted(front(mn, mx) for _, mn, mx, _ in items)[len(items) // 2]
        lo = min(min(mn.dot(ax), mx.dot(ax)) for _, mn, mx, _ in items)
        hi = max(max(mn.dot(ax), mx.dot(ax)) for _, mn, mx, _ in items)
        # gaps between consecutive buildings = side streets
        prev = None
        for _, mn, mx, _ in items:
            a0, a1 = sorted((mn.dot(ax), mx.dot(ax)))
            if prev is not None and a0 - prev > 30:
                gaps.append((r, prev, a0, fr))
            prev = a1 if prev is None else max(prev, a1)
        # lamps along the plaza-side sidewalk, 12 studs out from the facades (near the kerb)
        origin = Vector((0, 0, 0))
        F = L.Frame(origin, ax, -out)  # x along street, y away from the plaza
        s = lo + 18
        k = 0
        while s < hi - 18:
            p = ax * s + (-out) * 0  # along-axis position
            # world point: along-axis component s, front component fr - 11.5 towards the plaza
            if r in ("N", "S"):
                wp = Vector((s * ax.x if ax.x else 0, 0, 0))
                wp = Vector((ax.x * s, fr + out.y * 11.5, 0))
            else:
                wp = Vector((fr + out.x * 11.5, ax.y * s, 0))
            in_gap = any(g_[0] == r and g_[1] - 6 < s < g_[2] + 6 for g_ in gaps)
            if not in_gap and not near_obstacle(wp, obstacles, 5):
                Fl = L.Frame(wp, ax, out)
                street_lamp(g, Fl, 0, 0, banner=(banners[k % 3], banners[(k + 1) % 3]))
                nl += 1
                k += 1
            s += 34
    # side streets: lamps down both sides, string lights across, signals at the mouth
    ns = 0
    for (r, a0, a1, fr) in gaps:
        ax, out, _ = row_axes(r)
        ax, out = Vector(ax), Vector(out)
        inward = -out
        def W(a, depth, z=0.0):
            if r in ("N", "S"):
                return Vector((ax.x * a, fr + inward.y * depth, z))
            return Vector((fr + inward.x * depth, ax.y * a, z))
        width = a1 - a0
        for side, a in ((-1, a0 + 3.5), (1, a1 - 3.5)):
            for depth in (10, 34, 58, 82):
                p = W(a, depth)
                if near_obstacle(p, obstacles, 3.5):
                    continue
                Fl = L.Frame(p, inward, ax * side)
                street_lamp(g, Fl, 0, 0, banner=(banners[ns % 3], banners[(ns + 2) % 3]))
                ns += 1
        for depth in (16, 28, 40, 52, 64, 76):
            string_lights(g, W(a0 + 0.5, depth, 38 + (depth % 3)), W(a1 - 0.5, depth + 5, 38 + (depth % 2)), 3.0)
        for a in (a0 + 2.0, a1 - 2.0):
            p = W(a, -2.0)
            if not near_obstacle(p, obstacles, 2.5):
                ped_signal(g, L.Frame(p, ax, inward), 0, 0, 1)
                L.light(p + Vector((0, 0, 9.6)), (255, 60, 60), 8, 0.6, name="signal")
    L.flush(g, "B_Streetscape", C["det"])
    log(f"street lamps: {nl} along the plaza, {ns} in side streets; side streets: {len(gaps)}")


def rooftop_billboards(C, rows, children):
    """Lit box billboards on the front edge of foreground roofs, facing the plaza."""
    rng = random.Random(11)
    n = 0
    for r, items in rows.items():
        ax, out, front = row_axes(r)
        ax, out = Vector(ax), Vector(out)
        inward = -out
        for (name, mn, mx, o) in items:
            if "Landmark" in name or rng.random() > 0.55:
                continue
            me = o.data
            mw = o.matrix_world
            fr = front(mn, mx)
            # roof height at the front 6 studs of the building
            zs = [(mw @ v.co).z for v in me.vertices if abs(((mw @ v.co) - Vector((0, 0, 0))).dot(out) + fr * (
                out.x + out.y) * -1 * -1) < 1e9]
            fz = []
            for v in me.vertices:
                w = mw @ v.co
                depth = (w.y - fr) if r == "N" else ((fr - w.y) if r == "S" else ((w.x - fr) if r == "E" else (fr - w.x)))
                if 0 <= depth <= 6:
                    fz.append(w.z)
            if not fz:
                continue
            z = max(fz)
            a0, a1 = sorted((mn.dot(ax), mx.dot(ax)))
            width = min((a1 - a0) * 0.8, 44)
            if width < 12 or z > 190:
                continue
            fmt = rng.choice(["W", "L", "W", "X3"])
            h = width / FMT[fmt]
            legs = rng.uniform(2.5, 6)
            am = (a0 + a1) / 2

            def W(a, depth, zz):
                if r in ("N", "S"):
                    return Vector((ax.x * a, fr + inward.y * depth, zz))
                return Vector((fr + inward.x * depth, ax.y * a, zz))
            bmn = Vector([min(W(am - width / 2, 2, z)[i], W(am + width / 2, 6, z + legs + h)[i]) for i in range(3)])
            bmx = Vector([max(W(am - width / 2, 2, z)[i], W(am + width / 2, 6, z + legs + h)[i]) for i in range(3)])
            if overlaps(bmn, bmx, children.get(name, [])):
                continue
            g = L.Geo()
            F = L.Frame(W(am - width / 2, 0, 0), ax if r in ("N", "E") or True else -ax, inward)
            F = L.Frame(W(0, 0, 0), ax, inward)
            x0, x1 = am - width / 2, am + width / 2
            # make the frame's local x match the along-axis coordinate
            Fo = L.Frame(W(0, 0, 0) - ax * 0, ax, inward)
            base = W(0, 0, 0)
            Fo = L.Frame(base - ax * (base.dot(ax)), ax, inward)
            Fo.o = Vector((base.x, base.y, 0)) if False else Fo.o
            ys = 3.0
            zs0 = z + legs
            for i in range(max(2, int(width / 12) + 1)):
                xx = x0 + 1 + (width - 2) * i / max(1, int(width / 12))
                L.box(g, Fo, xx - 0.4, ys + 1.0, z, xx + 0.4, ys + 1.8, zs0 + h, "STL")
                L.beam(g, Fo.w(xx, ys + 1.4, zs0 + h * 0.6), Fo.w(xx, ys + 1.4 + h * 0.45, z), 0.4, "STL")
            L.box(g, Fo, x0 - 0.5, ys, zs0 - 0.6, x1 + 0.5, ys + 1.0, zs0 + h + 0.6, "PNL", skip=("front",))
            L.box(g, Fo, x0 - 0.5, ys - 2.4, zs0 - 1.0, x1 + 0.5, ys + 1.0, zs0 - 0.7, "STL")
            for i in range(int(width / 7) + 1):
                xx = x0 + 1 + i * 7
                if xx < x1 - 0.5:
                    L.box(g, Fo, xx - 0.45, ys - 2.2, zs0 - 0.7, xx + 0.45, ys - 1.4, zs0 - 0.2, "LAMP")
            L.flush(g, f"B_RoofBB_{name[3:]}", C["det"])
            ob, rec = L.screen(Fo, x0, zs0, x1, zs0 + h, ys - 0.05, f"SCR_Roof_{name[3:]}", C["scr"], rng, kind="rooftop",
                               fmt=fmt)
            L.light(Fo.w(am, ys - 8, zs0 + h / 2), (255, 245, 230), 40, 1.0, kind="surface", direction=tuple(-inward),
                    name=rec["name"])
            n += 1
    log("rooftop billboards:", n)


def landmark_screens(C, rows, children):
    """Big LED video screens (like 109 / Q-Front) on the plaza-facing facades of landmark lots."""
    rng = random.Random(5)
    n = 0
    for r, items in rows.items():
        ax, out, front = row_axes(r)
        ax, out = Vector(ax), Vector(out)
        inward = -out
        for (name, mn, mx, o) in items:
            if "Landmark" not in name and "Modern" not in name:
                continue
            if "Modern" in name and rng.random() > 0.5:
                continue
            fr = front(mn, mx)
            a0, a1 = sorted((mn.dot(ax), mx.dot(ax)))
            top = mx.z
            best = None
            for fmt in ("T", "V", "Q", "L", "W"):
                for wf in (0.9, 0.75, 0.6):
                    w = (a1 - a0) * wf
                    h = w / FMT[fmt]
                    for z0 in (34.0, 46.0, 58.0, 70.0):
                        if z0 + h > top - 8 or w < 14:
                            continue
                        am = (a0 + a1) / 2

                        def W(a, depth, zz):
                            if r in ("N", "S"):
                                return Vector((ax.x * a, fr + inward.y * depth, zz))
                            return Vector((fr + inward.x * depth, ax.y * a, zz))
                        p0, p1 = W(am - w / 2, -2.0, z0), W(am + w / 2, 0.5, z0 + h)
                        bmn = Vector([min(p0[i], p1[i]) for i in range(3)])
                        bmx = Vector([max(p0[i], p1[i]) for i in range(3)])
                        if overlaps(bmn, bmx, children.get(name, []), pad=0.3):
                            continue
                        if best is None or w * h > best[0]:
                            best = (w * h, fmt, w, h, z0)
            if not best:
                continue
            _, fmt, w, h, z0 = best
            base = Vector((fr * abs(out.x), fr * abs(out.y), 0))
            Fo = L.Frame(base, ax, inward)
            am = (a0 + a1) / 2
            g = L.Geo()
            y = -1.4
            L.box(g, Fo, am - w / 2 - 0.8, y - 0.2, z0 - 0.8, am + w / 2 + 0.8, 0.0, z0, "STL")
            L.box(g, Fo, am - w / 2 - 0.8, y - 0.2, z0 + h, am + w / 2 + 0.8, 0.0, z0 + h + 0.8, "STL")
            L.box(g, Fo, am - w / 2 - 0.8, y - 0.2, z0, am - w / 2, 0.0, z0 + h, "STL")
            L.box(g, Fo, am + w / 2, y - 0.2, z0, am + w / 2 + 0.8, 0.0, z0 + h, "STL")
            L.flush(g, f"B_LED_{name[3:]}", C["det"])
            ob, rec = L.screen(Fo, am - w / 2, z0, am + w / 2, z0 + h, y + 0.1, f"SCR_LED_{name[3:]}", C["scr"], rng,
                               kind="giant", fmt=fmt)
            L.light(Fo.w(am, y - 10, z0 + h / 2), (255, 245, 235), 60, 1.6, kind="surface", direction=tuple(-inward),
                    name=rec["name"])
            n += 1
    log("landmark LED screens:", n)


# ----------------------------------------------------------------------------- output
def write_data(path, refs):
    def vec(v):
        return "{" + ",".join(f"{c:g}" for c in v) + "}"
    o = ["-- Generated by blender/hex3_build.py - HEX! City v3 data (Roblox axes, studs).",
         "return {",
         "\tversion = 3, markerSize = 4,",
         f"\tmarkerB = {vec(rb((0, 0, -60)))},",
         "\trefs = {" + ", ".join('{name="%s", pos=%s}' % (n, vec(rb(p))) for n, p in refs) + "},",
         "\tscreens = {"]
    for s in L.SCREENS:
        ps = ",".join("{c=%s,n=%s,r=%s,w=%g,h=%g,u0=%g,u1=%g}" % (vec(rb(p["c"])), vec(rb(p["n"])), vec(rb(p["r"])),
                                                                   round(p["w"], 3), round(p["h"], 3), round(p["u0"], 4),
                                                                   round(p["u1"], 4)) for p in s["panels"])
        o.append('\t\t["%s"] = {ad="%s", kind="%s", layer=0, panels={%s}},' % (s["name"], s["ad"], s["kind"], ps))
    o.append("\t},")
    o.append("\tsigns = {")
    for s in SIGN_GLOW:
        ps = ",".join("{c=%s,n=%s,r=%s,w=%g,h=%g,uv={%g,%g,%g,%g}}" % (
            vec(rb(p["c"])), vec(rb(p["n"])), vec(rb(p["r"])), round(p["w"], 3), round(p["h"], 3),
            *[round(x, 4) for x in p["uv"]]) for p in s["panels"])
        if s["atlas"] == "self":
            from PIL import Image
            key = s["name"].split("__")[-1]
            px = Image.open(os.path.join(TEX, key + ".png")).size
        else:
            px = (1024, 1024)  # Roblox stores the 2048 sign atlases at 1024
        o.append('\t\t{name="%s", atlas="%s", px={%d,%d}, panels={%s}},' % (s["name"], s["atlas"], *px, ps))
    o.append("\t},")
    o.append("\tads = {")
    for name, (w, h) in sorted(L.AD_SIZES.items()):
        o.append('\t\t["%s"] = {%d, %d},' % (name, w, h))
    o.append("\t},")
    o.append("\tlights = {")
    for l_ in L.LIGHTS:
        extra = (", dir=" + vec(rb(l_["dir"]))) if l_["dir"] else ""
        extra += f", angle={l_['angle']}" if l_["angle"] else ""
        o.append('\t\t{kind="%s", pos=%s, color={%d,%d,%d}, range=%g, brightness=%g, name="%s"%s},' % (
            l_["kind"], vec(rb(l_["pos"])), *l_["color"], l_["range"], l_["brightness"], l_["name"], extra))
    o.append("\t},")
    o.append("}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(o) + "\n")
    log("wrote", path, "screens", len(L.SCREENS), "signs", len(SIGN_GLOW), "lights", len(L.LIGHTS))


def export(objs, path):
    import io_scene_fbx.export_fbx_bin as efb
    if not getattr(efb, "_cp_bare", False):
        orig = efb._gen_vid_path

        def bare(img, scene_data):
            _a, rel = orig(img, scene_data)
            nm = os.path.basename(rel.replace("\\", "/"))
            return nm, nm
        efb._gen_vid_path = bare
        efb._cp_bare = True
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"MESH"}, global_scale=1.0,
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE", axis_forward="-Z", axis_up="Y",
                             bake_space_transform=False, mesh_smooth_type="OFF", use_custom_props=False,
                             add_leaf_bones=False, bake_anim=False, path_mode="STRIP", embed_textures=False)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
    log(f"exported {os.path.basename(path)}: {len(objs)} objects, {tris} tris, {os.path.getsize(path) / 1e6:.2f} MB")


def main():
    prepare_textures()
    L.set_tex_dir(TEX)
    L.load_ads(os.path.join(EX, "ads_index.txt"))
    import_original()
    original = [o for o in bpy.data.objects if o.type == "MESH"]
    refs = [(n, (lambda b: (b[0] + b[1]) / 2)(wbbox(bpy.data.objects[n]))) for n in
            ("Plaza_Curb", "LightMast_Plaza_11", "LightMast_Plaza_02")]
    C = {"A": L.coll("A_Original_Map_Unchanged"), "B": L.coll("B_HEX_v3_Detail")}
    C["scr"] = L.coll("B_Screens", C["B"])
    C["det"] = L.coll("B_Streets_Billboards", C["B"])
    for o in original:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        C["A"].objects.link(o)
    billboard_screens(C)
    sign_glow()
    rows, obstacles, children = collect()
    build_streets(C, rows, obstacles)
    rooftop_billboards(C, rows, children)
    landmark_screens(C, rows, children)
    mg = {"N": [], "S": [], "E": [], "W": []}
    for o in bpy.data.objects:
        if o.type == "MESH" and o.parent is None and o.name.startswith("MG_") and o.name.split("_")[1] in mg:
            mg[o.name.split("_")[1]].append((o.name, *wbbox(o), o))
    rooftop_billboards(C, mg, children)
    import hex3_detail as D
    D.run(C, rows, obstacles, children, SIGN_GLOW, TEX, log)
    g = L.Geo()
    L.box(g, L.Frame((0, 0, 0), (1, 0, 0), (0, 1, 0)), -2, -2, -62, 2, 2, -58, "STL")
    L.flush(g, "HEX_ALIGN_B", C["det"])
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    bpy.context.preferences.filepaths.use_relative_paths = True
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True, relative_remap=True)
    log("saved", OUT_BLEND)
    write_data(os.path.join(EX, "roblox", "CityData.lua"), refs)
    export(original, os.path.join(EX, "HEX_City_v3_A.fbx"))
    export([o for o in C["B"].all_objects if o.type == "MESH"], os.path.join(EX, "HEX_City_v3_B.fbx"))


if __name__ == "__main__":
    main()
