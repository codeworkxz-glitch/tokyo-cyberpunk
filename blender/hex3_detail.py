"""HEX! City v3 - extra street-level and rooftop detail (called from hex3_build.py).

Everything here goes into file B and sits outside the plaza / courts / practice area:
  * vertical blade signs on the foreground facades (original sign atlas, glow in Roblox)
  * gateway arches with lit name signs over every side-street mouth
  * vending machine groups in the side streets and at shop fronts
  * AC condensers and drain pipes on the side-street walls
  * rooftop plant: AC units, water tanks, stair huts, antennas with red beacons
  * bollards along the plaza-side kerb
"""
import math
import os
import random

import bpy
from mathutils import Vector

import cp2_lib as L

PLAZA = (486.0, 401.0)  # |x|, |y| of the play area (Plaza_Curb) - nothing new may enter it


def in_plaza(p, pad=0.0):
    return abs(p.x) < PLAZA[0] + pad and abs(p.y) < PLAZA[1] + pad


def row_axes(r):
    return {"N": ((1, 0, 0), (0, -1, 0), lambda mn, mx: mn.y),
            "S": ((-1, 0, 0), (0, 1, 0), lambda mn, mx: mx.y),
            "E": ((0, -1, 0), (-1, 0, 0), lambda mn, mx: mn.x),
            "W": ((0, 1, 0), (1, 0, 0), lambda mn, mx: mx.x)}[r]


def bbox_of(pts):
    return (Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)]))


def hits(bmn, bmx, boxes, pad=0.3):
    for mn, mx in boxes:
        if (bmn.x < mx.x + pad and bmx.x > mn.x - pad and bmn.y < mx.y + pad and bmx.y > mn.y - pad
                and bmn.z < mx.z + pad and bmx.z > mn.z - pad):
            return True
    return False


def vquad(g, c, n, w, h, key, uv):
    """Upright quad centred at c facing n, texture readable (u to the viewer's right)."""
    n = Vector(n).normalized()
    r = (-n).cross(Vector((0, 0, 1))).normalized()
    up = Vector((0, 0, 1))
    c = Vector(c)
    pts = [c - r * w / 2 - up * h / 2, c + r * w / 2 - up * h / 2, c + r * w / 2 + up * h / 2, c - r * w / 2 + up * h / 2]
    u0, v0, u1, v1 = uv
    g.face(key, pts, uv=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    return {"c": tuple(c), "n": tuple(n), "r": tuple(r), "w": w, "h": h, "uv": (u0, v0, u1, v1)}


# blade cells of signs_v.png (2048^2): two rows of 16 tall signs + 8 at the bottom right
def blade_cells():
    cells = []
    e = 0.004
    for row, (v0, v1) in enumerate(((0.752, 0.998), (0.502, 0.748))):
        for i in range(16):
            cells.append((i / 16 + e, v0 + e, (i + 1) / 16 - e, v1 - e))
    for i in range(8):
        cells.append((0.5 + i / 16 + e, 0.002 + e, 0.5 + (i + 1) / 16 - e, 0.248 - e))
    return cells


# ----------------------------------------------------------------------------- textures
def make_textures(TEX):
    from PIL import Image, ImageDraw, ImageFont
    jp = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
    bold = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
    # vending machine front (no prices, no brands): lit header, 4 shelves of cans/bottles, buttons
    for name, body, head in (("VEND_Blue", (28, 92, 200), (235, 245, 255)), ("VEND_Red", (205, 30, 40), (255, 240, 235)),
                             ("VEND_White", (232, 234, 238), (210, 235, 255))):
        im = Image.new("RGB", (256, 512), body)
        d = ImageDraw.Draw(im)
        d.rectangle([14, 14, 242, 340], fill=head)
        rng = random.Random(name)
        cols = [(230, 60, 40), (40, 140, 230), (250, 190, 30), (60, 180, 90), (240, 240, 240), (120, 70, 40),
                (250, 120, 30), (180, 40, 140)]
        for s in range(4):
            y0 = 26 + s * 78
            d.rectangle([20, y0 + 58, 236, y0 + 64], fill=(170, 175, 185))
            for k in range(6):
                x = 26 + k * 35
                c = rng.choice(cols)
                if rng.random() < 0.5:  # can
                    d.rounded_rectangle([x, y0 + 14, x + 26, y0 + 58], 5, fill=c)
                    d.rectangle([x, y0 + 30, x + 26, y0 + 40], fill=(255, 255, 255))
                else:  # bottle
                    d.rounded_rectangle([x + 4, y0 + 22, x + 22, y0 + 58], 6, fill=c)
                    d.rectangle([x + 9, y0 + 8, x + 17, y0 + 24], fill=c)
                    d.rectangle([x + 8, y0 + 4, x + 18, y0 + 9], fill=(250, 250, 250))
                d.rectangle([x + 5, y0 + 66, x + 21, y0 + 72], fill=(70, 230, 120) if rng.random() < 0.8 else (230, 60, 60))
        d.rectangle([14, 352, 242, 396], fill=(20, 22, 26))
        d.text((128, 374), "つめた〜い", font=ImageFont.truetype(jp, 26), fill=(110, 190, 255), anchor="mm")
        d.rectangle([40, 420, 216, 470], fill=(25, 25, 30))
        d.rectangle([180, 360, 236, 392], fill=(60, 64, 72)) if False else None
        im.save(os.path.join(TEX, name + ".png"))
    # gateway arch name signs (cream plates with green / red lettering)
    arches = [("ARCH_Center", "HEX センター街", "HEX CENTER STREET", (30, 70, 40)),
              ("ARCH_Basket", "バスケ通り", "BASKETBALL STREET", (190, 40, 30)),
              ("ARCH_Bunka", "文化村通り", "BUNKAMURA DORI", (30, 50, 120)),
              ("ARCH_Koen", "HEX 公園通り", "PARK STREET", (120, 40, 110))]
    for name, jtxt, etxt, col in arches:
        im = Image.new("RGB", (1024, 160), (242, 238, 220))
        d = ImageDraw.Draw(im)
        d.rectangle([4, 4, 1019, 155], outline=col, width=8)
        d.text((512, 70), jtxt, font=ImageFont.truetype(jp, 92), fill=col, anchor="mm")
        d.text((512, 134), etxt, font=ImageFont.truetype(bold, 26), fill=col, anchor="mm")
        im.save(os.path.join(TEX, name + ".png"))
    return [a[0] for a in arches]


# ----------------------------------------------------------------------------- pieces
def blade_sign(g, P, along, outv, z0, H, Wd, cell, glow):
    """Vertical tenant sign sticking out of a facade. P: attach point on the facade (z=0),
    along: unit along the street, outv: unit away from the facade."""
    t = 0.7
    a0 = P + outv * 0.9
    c = a0 + outv * (Wd / 2)
    Fs = L.Frame(a0 - along * (t / 2), outv, along)  # x outwards, y along the street
    L.box(g, Fs, -0.15, 0, z0 - 0.35, Wd + 0.15, t, z0, "STL")
    L.box(g, Fs, -0.15, 0, z0 + H, Wd + 0.15, t, z0 + H + 0.35, "STL")
    L.box(g, Fs, Wd, 0, z0, Wd + 0.15, t, z0 + H, "STL", skip=("top", "bottom"))
    for zz in (z0 + 1.5, z0 + H - 1.5):  # wall brackets
        L.box(g, Fs, -0.9, t / 2 - 0.15, zz - 0.15, 0, t / 2 + 0.15, zz + 0.15, "STL")
    pnl = []
    for s in (-1, 1):
        pnl.append(vquad(g, c + along * (s * (t / 2 + 0.03)) + Vector((0, 0, z0 + H / 2)), along * s, Wd, H, "SGV",
                         cell))
    glow.extend(pnl)


def vending(g, F, x, depth_y, key):
    """Vending machine in frame F (x along the wall, y away from the wall), back on the wall."""
    w, dd, h = 3.4, 2.4, 6.0
    L.box(g, F, x - w / 2, 0.05, 0, x + w / 2, 0.05 + dd, h, "PNL", skip=("front",))
    Fb = L.Frame(F.w(x, 0.05 + dd + 0.03, 0), -F.ax, -F.ay)  # facing away from the wall
    L.quad(g, Fb, -w / 2 + 0.15, 0.6, w / 2 - 0.15, h - 0.25, 0, key, uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    L.box(g, F, x - w / 2 - 0.1, 0.05, h, x + w / 2 + 0.1, 0.05 + dd + 0.25, h + 0.25, "STL")


def ac_unit(g, F, x, z, top=False):
    """Split AC condenser hung on a wall (F: x along wall, y out of the wall)."""
    L.box(g, F, x - 1.5, 0.0, z, x + 1.5, 1.3, z + 2.1, "MEC")
    L.box(g, F, x - 1.4, 0.0, z - 0.25, x - 1.2, 1.5, z, "STL", skip=("top",))
    L.box(g, F, x + 1.2, 0.0, z - 0.25, x + 1.4, 1.5, z, "STL", skip=("top",))
    L.tube(g, F.w(x + 1.6, 0.25, z + 0.6), F.w(x + 1.6, 0.25, z - 3.0), 0.09, "STL", n=4)


def roof_ac(g, F, x, y, z, rot=False):
    sx, sy = (3.2, 2.4) if not rot else (2.4, 3.2)
    L.box(g, F, x - sx / 2, y - sy / 2, z, x + sx / 2, y + sy / 2, z + 2.6, "MEC", skip=("bottom",))
    L.cylinder(g, F, x, y, 0.85, z + 2.6, z + 2.75, "STL", n=8, top="STL")


def water_tank(g, F, x, y, z, r, h):
    leg = 2.2
    for sx in (-1, 1):
        for sy in (-1, 1):
            L.box(g, F, x + sx * r * 0.6 - 0.2, y + sy * r * 0.6 - 0.2, z, x + sx * r * 0.6 + 0.2,
                  y + sy * r * 0.6 + 0.2, z + leg, "STL", skip=("bottom", "top"))
    L.box(g, F, x - r * 0.8, y - r * 0.8, z + leg - 0.3, x + r * 0.8, y + r * 0.8, z + leg, "STL", skip=("bottom",))
    L.cylinder(g, F, x, y, r, z + leg, z + leg + h, "PNL", n=12, top="PNL")
    L.tube(g, F.w(x, y - r, z + leg + h), F.w(x, y - r, z + leg + h + 0.01), 0.1, "STL")


def stair_hut(g, F, x, y, z, w, d, h):
    L.box(g, F, x - w / 2, y - d / 2, z, x + w / 2, y + d / 2, z + h, "CON", skip=("bottom",))
    L.box(g, F, x - w / 2 - 0.3, y - d / 2 - 0.3, z + h, x + w / 2 + 0.3, y + d / 2 + 0.3, z + h + 0.4, "STL",
          skip=("bottom",))
    L.quad(g, L.Frame(F.w(x, y - d / 2 - 0.02, 0), F.ax, F.ay), -1.2, z, 1.2, z + 5.2, 0, "STL")


def antenna(g, F, x, y, z, h):
    L.tube(g, F.w(x, y, z), F.w(x, y, z + h), 0.22, "STL", n=6)
    for k in range(1, 4):
        zz = z + h * k / 4
        L.tube(g, F.w(x - 1.6, y, zz), F.w(x + 1.6, y, zz), 0.07, "STL", n=4)
    L.box(g, F, x - 0.35, y - 0.35, z + h, x + 0.35, y + 0.35, z + h + 0.7, "SIG_RED")


def bollard(g, p):
    L.tube(g, p, p + Vector((0, 0, 2.6)), 0.32, "STL", n=6)
    L.tube(g, p + Vector((0, 0, 2.0)), p + Vector((0, 0, 2.25)), 0.36, "LAMP", n=6)


# ----------------------------------------------------------------------------- rooftop plant
def _in_tri(px, py, t):
    (x1, y1), (x2, y2), (x3, y3) = t
    d1 = (px - x2) * (y1 - y2) - (x1 - x2) * (py - y2)
    d2 = (px - x3) * (y2 - y3) - (x2 - x3) * (py - y3)
    d3 = (px - x1) * (y3 - y1) - (x3 - x1) * (py - y1)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def roof_faces(o):
    """Exposed, roughly rectangular flat roof areas (world bboxes) of a triangulated building."""
    me = o.data
    mw = o.matrix_world
    m3 = mw.to_3x3()
    flat = []  # (z, area, mn, mx, 2d pts, up)
    for p in me.polygons:
        n = (m3 @ p.normal).normalized()
        if abs(n.z) < 0.97:
            continue
        pts = [mw @ me.vertices[i].co for i in p.vertices]
        mn, mx = bbox_of(pts)
        area = 0.5 * abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y
                             for i in range(len(pts))))
        flat.append((mx.z, area, mn, mx, [(q.x, q.y) for q in pts], n.z > 0))
    ups = [f for f in flat if f[5] and f[0] > 8]
    # cluster touching triangles of the same height
    parent = list(range(len(ups)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(len(ups)):
        for j in range(i + 1, len(ups)):
            a, b = ups[i], ups[j]
            if abs(a[0] - b[0]) < 0.05 and a[2].x <= b[3].x + 0.01 and b[2].x <= a[3].x + 0.01 \
                    and a[2].y <= b[3].y + 0.01 and b[2].y <= a[3].y + 0.01:
                parent[find(i)] = find(j)
    groups = {}
    for i, f in enumerate(ups):
        groups.setdefault(find(i), []).append(f)
    out = []
    for fs in groups.values():
        z = fs[0][0]
        area = sum(f[1] for f in fs)
        mn = Vector((min(f[2].x for f in fs), min(f[2].y for f in fs), z))
        mx = Vector((max(f[3].x for f in fs), max(f[3].y for f in fs), z))
        if area < 70 or (mx.x - mn.x) * (mx.y - mn.y) > area * 1.15:
            continue
        # exposed? no horizontal face of this building above the sample points
        samples = [((mn.x + mx.x) / 2, (mn.y + mx.y) / 2), (mn.x + 3, mn.y + 3), (mx.x - 3, mx.y - 3)]
        covered = False
        for f in flat:
            if f[0] > z + 0.5 and any(_in_tri(sx, sy, f[4][:3]) for sx, sy in samples):
                covered = True
                break
        if not covered:
            out.append((mn, mx))
    return out


def rooftop_plant(C, buildings, children, front_keep):
    """buildings: list of (name, obj); front_keep: name -> (axis, coord, sign) strip kept free for billboards."""
    rng = random.Random(23)
    n = 0
    for name, o in buildings:
        g = L.Geo()
        occ = list(children.get(name, []))
        F = L.Frame((0, 0, 0), (1, 0, 0), (0, 1, 0))
        faces = roof_faces(o)
        tall = max((f[1].z for f in faces), default=0)
        for mn, mx in faces:
            z = mx.z
            x0, y0, x1, y1 = mn.x + 2.5, mn.y + 2.5, mx.x - 2.5, mx.y - 2.5
            if name in front_keep:
                ax_, coord, sgn = front_keep[name]
                if ax_ == "y":
                    if sgn > 0:
                        y0 = max(y0, coord + 9)
                    else:
                        y1 = min(y1, coord - 9)
                else:
                    if sgn > 0:
                        x0 = max(x0, coord + 9)
                    else:
                        x1 = min(x1, coord - 9)
            if x1 - x0 < 5 or y1 - y0 < 5:
                continue

            def place(sx, sy, hz, fn):
                for _ in range(8):
                    cx, cy = rng.uniform(x0 + sx / 2, x1 - sx / 2), rng.uniform(y0 + sy / 2, y1 - sy / 2)
                    if x1 - x0 < sx or y1 - y0 < sy:
                        return False
                    bmn = Vector((cx - sx / 2, cy - sy / 2, z + 0.05))
                    bmx = Vector((cx + sx / 2, cy + sy / 2, z + hz))
                    if hits(bmn, bmx, occ, 0.6):
                        continue
                    occ.append((bmn, bmx))
                    fn(cx, cy)
                    return True
                return False
            area = (x1 - x0) * (y1 - y0)
            if area > 260 and rng.random() < 0.55:
                w, d = rng.uniform(6, 8), rng.uniform(5, 6.5)
                place(w, d, 8, lambda cx, cy: stair_hut(g, F, cx, cy, z, w, d, rng.uniform(6.5, 8)))
            if area > 160 and rng.random() < 0.45:
                r = rng.uniform(2.4, 3.4)
                place(2 * r + 0.6, 2 * r + 0.6, 9, lambda cx, cy: water_tank(g, F, cx, cy, z, r, rng.uniform(4, 5.5)))
            for _ in range(min(7, int(area / 70) + 1)):
                rot = rng.random() < 0.5
                place(3.4 if not rot else 2.6, 2.6 if not rot else 3.4, 3,
                      lambda cx, cy: roof_ac(g, F, cx, cy, z, rot))
            if z >= tall - 0.1 and z > 110 and rng.random() < 0.4:
                place(3.6, 1.0, 30, lambda cx, cy: antenna(g, F, cx, cy, z, rng.uniform(10, 22)))
        if g.tris():
            L.flush(g, f"B_Roof_{name}", C["det"])
            n += 1
    return n


# ----------------------------------------------------------------------------- main entry
def run(C, rows, obstacles, children, sign_glow, TEX, log):
    arch_keys = make_textures(TEX)
    rng = random.Random(31)
    cells = blade_cells()
    placed = []  # new things that must not collide with each other
    # ---------------------------------------------------------------- blade signs
    nb = 0
    for r, items in rows.items():
        ax, out, front = row_axes(r)
        ax, out = Vector(ax), Vector(out)
        g = L.Geo()
        panels = []
        for (name, mn, mx, o) in items:
            fr = front(mn, mx)
            a0, a1 = sorted((mn.dot(ax), mx.dot(ax)))
            if a1 - a0 < 14:
                continue
            top = mx.z
            for edge in (a0 + 1.6, a1 - 1.6):
                if rng.random() < 0.25:
                    continue
                z = 13.0 + rng.choice((0.0, 2.0, 4.0))
                stack = 0
                while z + 16 < top - 6 and stack < 2:
                    H = rng.choice((16.0, 20.0, 24.0))
                    if z + H > top - 6:
                        H = 16.0
                    Wd = H / 4.0
                    if r in ("N", "S"):
                        P = Vector((ax.x * edge, fr, 0))
                    else:
                        P = Vector((fr, ax.y * edge, 0))
                    p0 = P + out * 0.2 - ax * 0.6 + Vector((0, 0, z - 0.5))
                    p1 = P + out * (Wd + 1.3) + ax * 0.6 + Vector((0, 0, z + H + 0.5))
                    bmn, bmx = bbox_of([p0, p1])
                    if not hits(bmn, bmx, children.get(name, []) + placed + obstacles, 0.4) and not in_plaza(bmx, 1):
                        cell = rng.choice(cells)
                        pn = []
                        blade_sign(g, P, ax, out, z, H, Wd, cell, pn)
                        panels.extend(pn)
                        placed.append((bmn, bmx))
                        nb += 1
                        stack += 1
                        z += H + 3.0
                    else:
                        z += 8.0
        if g.tris():
            objs = L.flush(g, f"B_Blade_{r}", C["det"])
            part = next((ob.name for ob in objs if ob.name.endswith("__SGV")), objs[0].name)
            for i in range(0, len(panels), 2):
                sign_glow.append({"name": part, "atlas": "V", "panels": panels[i:i + 2]})
    log("blade signs:", nb)
    # ---------------------------------------------------------------- side streets
    gaps = []
    for r, items in rows.items():
        ax, out, front = row_axes(r)
        ax = Vector(ax)
        its = sorted(items, key=lambda it: ((it[1] + it[2]) / 2).dot(ax))
        fr = sorted(front(mn, mx) for _, mn, mx, _ in its)[len(its) // 2]
        prev, prev_it = None, None
        for it in its:
            a0, a1 = sorted((it[1].dot(ax), it[2].dot(ax)))
            if prev is not None and a0 - prev > 30:
                gaps.append((r, prev, a0, fr, prev_it, it))
            if prev is None or a1 > prev:
                prev, prev_it = a1, it
    nv = na = 0
    for gi, (r, a0, a1, fr, left, right) in enumerate(gaps):
        ax, out, _ = row_axes(r)
        ax, out = Vector(ax), Vector(out)
        inward = -out

        def W(a, depth, z=0.0):
            if r in ("N", "S"):
                return Vector((ax.x * a, fr + inward.y * depth, z))
            return Vector((fr + inward.x * depth, ax.y * a, z))
        g = L.Geo()
        # gateway arch just inside the mouth
        zb = 26.0
        dep = None
        for cand in (3.0, 22.0, 46.0, 70.0):
            bmn, bmx = bbox_of([W(a0, cand - 2.5, 0), W(a1, cand + 2.5, zb + 10)])
            if not hits(bmn, bmx, obstacles + children.get(left[0], []) + children.get(right[0], []), 0.5):
                dep = cand
                break
        if dep is None:
            log("gate skipped in side street", gi)
        else:
            for a in (a0 + 1.4, a1 - 1.4):
                Fp = L.Frame(W(a, dep), ax, inward)
                L.box(g, Fp, -0.9, -0.9, 0, 0.9, 0.9, zb + 7.5, "STL", skip=("bottom",))
                L.box(g, Fp, -1.4, -1.4, 0, 1.4, 1.4, 1.2, "CON", skip=("bottom",))
                L.box(g, Fp, -0.6, -1.0, zb + 7.5, 0.6, 1.0, zb + 9.2, "LAMP")
            Fa = L.Frame(W(a0, dep), ax, inward)
            span = a1 - a0
            L.box(g, Fa, 1.4, -0.7, zb - 0.6, span - 1.4, 0.7, zb, "STL")
            L.box(g, Fa, 1.4, -0.7, zb + 6.6, span - 1.4, 0.7, zb + 7.2, "STL")
            for k in range(1, 12):
                x = 1.4 + (span - 2.8) * k / 12
                L.box(g, Fa, x - 0.12, -0.75, zb - 0.6, x + 0.12, 0.75, zb - 0.45, "LAMP")
            L.flush(g, f"B_Gate_{gi}", C["det"])
            ga = L.Geo()
            key = arch_keys[gi % len(arch_keys)]
            mid = W((a0 + a1) / 2, dep, zb + 3.3)
            sw = span - 3.0
            pn = [vquad(ga, mid - inward * 0.72, -inward, sw, 6.4, key, (0, 0, 1, 1)),
                  vquad(ga, mid + inward * 0.72, inward, sw, 6.4, key, (0, 0, 1, 1))]
            L.box(ga, Fa, 1.5, -0.7, zb, span - 1.5, 0.7, zb + 6.6, "STL", skip=("front", "back"))
            objs = L.flush(ga, f"B_GateSign_{gi}", C["det"])
            sign_glow.append({"name": next(ob.name for ob in objs if key in ob.name), "atlas": "self", "panels": pn})
            L.light(mid - inward * 6, (255, 240, 215), 22, 0.8, kind="surface", direction=tuple(-inward), name="gate")
            placed.append(bbox_of([W(a0, dep - 2, 0), W(a1, dep + 2, zb + 10)]))
            na += 1
        # vending machine groups against both side walls, AC units and pipes above
        gv = L.Geo()
        for side, a_wall, it in ((1, a0, left), (-1, a1, right)):
            name, mn, mx, o = it
            top = mx.z
            yd = ax * side  # away from the wall
            xd = yd.cross(Vector((0, 0, 1)))  # keeps the frame right-handed
            sg = 1.0 if xd.dot(inward) > 0 else -1.0
            Fw = L.Frame(W(a_wall, 0), xd, yd)  # x along the side street (sg = into it), y away from the wall
            occ = children.get(name, [])
            for d0 in (18.0, 64.0):
                if rng.random() < 0.2:
                    continue
                k = rng.choice((2, 3))
                bmn, bmx = bbox_of([Fw.w(sg * (d0 - 1.8), 0, 0), Fw.w(sg * (d0 + 3.5 * k + 0.2), 2.8, 6.5)])
                if hits(bmn, bmx, occ + placed, 0.2) or any(
                        mn_.x - 3 < bmx.x and mx_.x + 3 > bmn.x and mn_.y - 3 < bmx.y and mx_.y + 3 > bmn.y
                        for mn_, mx_ in obstacles):
                    continue
                for i in range(k):
                    vending(gv, Fw, sg * (d0 + 1.7 + i * 3.5), 0, rng.choice(("VEND_Blue", "VEND_Red", "VEND_White")))
                L.light(Fw.w(sg * (d0 + 1.7 * k), 4.0, 3.5), (225, 240, 255), 10, 0.6, name="vending")
                placed.append((bmn, bmx))
                nv += k
            # AC condensers on the side wall, one per floor in a few bays
            for d in (8.0, 30.0, 46.0, 76.0):
                if rng.random() < 0.35:
                    continue
                for z in range(24, int(top) - 10, 12):
                    if rng.random() < 0.3:
                        continue
                    bmn, bmx = bbox_of([Fw.w(sg * d - 1.8, 0, z - 3.2), Fw.w(sg * d + 1.8, 1.6, z + 2.2)])
                    if hits(bmn, bmx, occ + placed, 0.2):
                        continue
                    ac_unit(gv, Fw, sg * d, float(z))
            # drain pipe from the roof
            for d in (4.0, 54.0):
                x = sg * d
                bmn, bmx = bbox_of([Fw.w(x - 0.4, 0, 0), Fw.w(x + 0.4, 0.8, top - 1)])
                if not hits(bmn, bmx, occ + placed, 0.1):
                    L.tube(gv, Fw.w(x, 0.45, 0.2), Fw.w(x, 0.45, top - 1.0), 0.28, "STL", n=6)
                    for z in range(10, int(top) - 2, 14):
                        L.box(gv, Fw, x - 0.4, 0, z, x + 0.4, 0.75, z + 0.3, "STL")
        L.flush(gv, f"B_SideStreet_{gi}", C["det"])
    log(f"gateway arches: {na}, vending machines: {nv}")
    # ---------------------------------------------------------------- plaza-front vending + bollards
    gb = L.Geo()
    nbol = 0
    for r, items in rows.items():
        ax, out, front = row_axes(r)
        ax, out = Vector(ax), Vector(out)
        fr = sorted(front(mn, mx) for _, mn, mx, _ in items)[len(items) // 2]
        lo = min(min(mn.dot(ax), mx.dot(ax)) for _, mn, mx, _ in items)
        hi = max(max(mn.dot(ax), mx.dot(ax)) for _, mn, mx, _ in items)
        s = lo + 9
        while s < hi - 9:
            if r in ("N", "S"):
                p = Vector((ax.x * s, fr + out.y * 14.2, 0))
            else:
                p = Vector((fr + out.x * 14.2, ax.y * s, 0))
            in_gap = any(gg[0] == r and gg[1] - 4 < s < gg[2] + 4 for gg in gaps)
            lamp_here = (s - (lo + 18)) % 34 < 3 or (s - (lo + 18)) % 34 > 31
            near = any(mn_.x - 2 < p.x < mx_.x + 2 and mn_.y - 2 < p.y < mx_.y + 2 for mn_, mx_ in obstacles)
            if not in_gap and not lamp_here and not near and not in_plaza(p, 0.5):
                bollard(gb, p)
                nbol += 1
            s += 7.0
        for (name, mn, mx, o) in items:
            if rng.random() > 0.3:
                continue
            fr_b = front(mn, mx)
            a0, a1 = sorted((mn.dot(ax), mx.dot(ax)))
            if a1 - a0 < 16:
                continue
            a = a1 - 1.5 if rng.random() < 0.5 else a0 + 8.7
            if r in ("N", "S"):
                base = Vector((ax.x * a, fr_b, 0))
            else:
                base = Vector((fr_b, ax.y * a, 0))
            Fw = L.Frame(base, -ax, out)  # x runs back along the street from `a`
            bmn, bmx = bbox_of([Fw.w(0, 0, 0), Fw.w(7.2, 2.8, 6.5)])
            if hits(bmn, bmx, children.get(name, []) + placed, 0.2):
                continue
            for i in range(2):
                vending(gb, Fw, 1.7 + i * 3.5, 0, rng.choice(("VEND_Blue", "VEND_Red", "VEND_White")))
            placed.append((bmn, bmx))
            nv += 2
    L.flush(gb, "B_Sidewalk", C["det"])
    log(f"bollards: {nbol}, vending machines total: {nv}")
    # ---------------------------------------------------------------- rooftops
    blds = []
    keep = {}
    for o in bpy.data.objects:
        if o.type != "MESH" or o.parent is not None or not o.name.startswith(("FG_", "MG_")):
            continue
        blds.append((o.name, o))
    for r, items in rows.items():
        ax, out, front = row_axes(r)
        for (name, mn, mx, o) in items:
            fr = front(mn, mx)
            keep[name] = ("y" if r in ("N", "S") else "x", fr, -out[1] if r in ("N", "S") else -out[0])
    nr = rooftop_plant(C, sorted(blds), children, keep)
    log("rooftops with plant:", nr)
