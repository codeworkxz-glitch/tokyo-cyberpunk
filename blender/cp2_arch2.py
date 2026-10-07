"""HEX! Cyberpunk City v2 - corner landmarks, midground towers, skyline towers, megatowers,
street-spanning advertisement structures."""
import math
import random

from mathutils import Vector

import cp2_lib as L
from cp2_lib import FLOOR, Frame, box, quad, prism, tube, beam, cylinder
from cp2_arch import (Ctx, mass, side_plain, w_curtain, w_ribbon, w_louver, w_tech, w_exo, w_plain, w_punched,
                      podium, neon_v, neon_h, neon_rect, roof_kit, antenna, mast, rooftop_billboard, add_screen,
                      recessed_screen, exo_braces, ribs, catwalk, blade_screen, lit_windows, cantilever_billboard)


# =========================================================================== corner landmarks
def _arc_wall(B, F, cx, cy, r, a0, a1, z0, z1, segs, style, **kw):
    pts = [(cx + r * math.cos(a0 + (a1 - a0) * i / segs), cy + r * math.sin(a0 + (a1 - a0) * i / segs))
           for i in range(segs + 1)]
    for i in range(segs):
        WF, Ln = F.wall(pts[i], pts[i + 1])
        style(B, WF, 0, Ln, z0, z1, **kw)
    return pts


def _ring(B, F, cx, cy, r, z, key, segs=24, w=0.5, a0=0.0, a1=2 * math.pi):
    full = abs(a1 - a0 - 2 * math.pi) < 1e-6
    for i in range(segs):
        t0 = a0 + (a1 - a0) * i / segs
        t1 = a0 + (a1 - a0) * (i + 1) / segs
        p0 = (cx + r * math.cos(t0), cy + r * math.sin(t0))
        p1 = (cx + r * math.cos(t1), cy + r * math.sin(t1))
        WF, Ln = F.wall(p0, p1)
        box(B.g, WF, -0.05, -w, z - w / 2, Ln + 0.05, 0, z + w / 2, key, skip=("back",))


def corner_drum(B, F, W, D):
    """NE: rounded glass drum tower wrapped by a giant curved screen, ring crown + needle."""
    r_ = B.rng
    B.hero = 3
    B.zb = 16.0
    g = B.g
    R = min(W, D) * 0.44
    cx, cy = R + 4, R + 4
    # podium following the round corner
    base = L.rounded_rect(0, 0, W, D, R * 0.9, n=10, corners=(1, 0, 0, 0))
    n = len(base)
    for i in range(n):
        a, b = base[i], base[(i + 1) % n]
        WF, Ln = F.wall(a, b)
        nx, ny = (b[1] - a[1]) / Ln, -(b[0] - a[0]) / Ln
        if nx + ny < -0.2 and Ln > 9:
            podium(B, WF, 0, Ln, zp=16.0, second=True)
        elif nx + ny < -0.2:
            w_curtain(B, WF, 0, Ln, -1, 28, fins=False, slabs=True, p=0.7)
            neon_h(B, WF, 0, Ln, 10.4, B.neon2, y=-0.6)
        else:
            side_plain(B, WF, 0, Ln, -1, 28)
    g.face("ROF", [F.w(p[0], p[1], 28) for p in base])
    # drum
    H = 336.0
    segs = 28
    a_front = 1.25 * math.pi
    drum = L.circle_poly(cx, cy, R, segs)
    for i in range(segs):
        a, b = drum[i], drum[(i + 1) % segs]
        WF, Ln = F.wall(a, b)
        mid = math.atan2((a[1] + b[1]) / 2 - cy, (a[0] + b[0]) / 2 - cx) % (2 * math.pi)
        facing = abs((mid - a_front + math.pi) % (2 * math.pi) - math.pi) < 0.6 * math.pi
        if facing:
            w_curtain(B, WF, 0, Ln, 28, H, fins=True, slabs=False, p=0.32)
        else:
            w_ribbon(B, WF, 0, Ln, 28, H, shades=False)
    g.face("ROF", [F.w(p[0], p[1], H) for p in drum])
    # curved wrap screens (main + ticker band)
    span = 0.5 * math.pi
    zc = 64.0
    arc = (R + 1.6) * 2 * span
    hh = arc * 3 / 8
    ob, rec = L.curved_screen(F, cx, cy, R + 1.6, a_front - span, a_front + span, zc, zc + hh, B.scr_name("C"), B.cs,
                              r_, segs=18, fmt="P")
    B.objs.append(ob)
    for zz in (zc - 1.2, zc + hh + 0.2):
        _ring(B, F, cx, cy, R + 2.4, zz + 0.5, "STL", segs=18, w=1.6, a0=a_front - span - 0.05, a1=a_front + span + 0.05)
        _ring(B, F, cx, cy, R + 4.1, zz + 0.5, B.neon, segs=18, w=0.4, a0=a_front - span - 0.05, a1=a_front + span + 0.05)
    zt = 236.0
    span2 = 0.42 * math.pi
    arc2 = (R + 1.4) * 2 * span2
    ob, rec = L.curved_screen(F, cx, cy, R + 1.4, a_front - span2, a_front + span2, zt, zt + arc2 / 4,
                              B.scr_name("C"), B.cs, r_, segs=16, fmt="X")
    B.objs.append(ob)
    _ring(B, F, cx, cy, R + 2.2, zt - 0.6, "STL", segs=16, w=1.4, a0=a_front - span2, a1=a_front + span2)
    # neon rings every 4 floors on the plaza side
    k = 1
    while 28 + k * 4 * FLOOR < H - 10:
        z = 28 + k * 4 * FLOOR
        if not (zc - 2 < z < zc + hh + 2 or zt - 2 < z < zt + arc2 / 4 + 2):
            _ring(B, F, cx, cy, R + 0.6, z, B.neon2 if k % 2 else B.neon, segs=18, w=0.45,
                  a0=a_front - 0.7 * math.pi, a1=a_front + 0.7 * math.pi)
        k += 1
    # stepped ring crown + needle
    z = H
    for i, (rr, hh2) in enumerate(((R * 0.82, 14), (R * 0.62, 12), (R * 0.4, 10))):
        cylinder(g, F, cx, cy, rr, z, z + hh2, "TEC" if i % 2 == 0 else "PNL", n=20, top="ROF")
        _ring(B, F, cx, cy, rr + 0.3, z + hh2 - 1.5, B.neon, segs=20, w=0.5)
        z += hh2
    tube(g, F.w(cx, cy, z), F.w(cx, cy, z + 120), 1.4, "STL", n=8)
    tube(g, F.w(cx, cy, z + 120), F.w(cx, cy, z + 160), 0.5, "STL", n=6)
    for zz in (z + 40, z + 80, z + 118):
        _ring(B, F, cx, cy, 3.0, zz, "NEON_RED" if zz > z + 100 else B.neon, segs=10, w=0.6)
    box(g, F, cx - 0.8, cy - 0.8, z + 160, cx + 0.8, cy + 0.8, z + 162, "NEON_RED")
    L.light(F.w(cx, cy, z + 161), (255, 30, 40), 30, 2, name=f"{B.bid}_needle")
    # back tower in the far corner
    bpoly = [(W * 0.62, D * 0.62), (W, D * 0.62), (W, D), (W * 0.62, D)]
    mass(B, F, bpoly, 28, 210, front=w_tech, side=w_tech, back=side_plain, front_dir=(-0.7, -0.7))
    roof_kit(B, F, W * 0.62, D * 0.62, W, D, 210, level=2)
    for p in ((cx, cy - R - 20), (cx - R - 20, cy)):
        L.light(F.w(p[0], p[1], 80), (255, 60, 200), 60, 2.0, name=f"{B.bid}_spill")


def corner_dept(B, F, W, D):
    """NW: stepped department megablock, atrium corner with neon fins, two giant facade screens,
    a 45-degree rooftop billboard facing the plaza."""
    r_ = B.rng
    B.hero = 3
    B.zb = 16.0
    g = B.g
    c = 18.0
    poly = L.chamfer_rect(0, 0, W, D, c, corners=(1, 0, 0, 0))
    # podium faces
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        WF, Ln = F.wall(a, b)
        nx, ny = (b[1] - a[1]) / Ln, -(b[0] - a[0]) / Ln
        if nx + ny < -0.2:
            podium(B, WF, 0, Ln, zp=16.0, second=True)
        else:
            side_plain(B, WF, 0, Ln, -1, 28)
    # tier 1: full block to 130 with screens on both front faces
    H1, H2, H3 = 130.0, 196.0, 252.0
    WFx, Lx = F.wall(poly[1], poly[2])   # faces -y (front along x)
    WFy, Ly = F.wall(poly[-1], poly[0])  # faces -x
    hx = (8, 40, 8 + (Lx - 16), 40 + min(80, (Lx - 16) / 2))
    hy = (8, 40, 8 + (Ly - 16), 40 + min(80, (Ly - 16) / 2))
    holes = {1: hx, len(poly) - 1: hy}
    mass(B, F, poly, 28, H1, front=w_punched, side=side_plain, back=side_plain, front_dir=(-0.7, -0.7), holes=holes,
         front_kw={"key": "TEC"})
    recessed_screen(B, WFx, *hx)
    recessed_screen(B, WFy, *hy)
    # atrium chamfer: glass with neon fins
    WFa, La = F.wall(poly[0], poly[1])
    ribs(B, WFa, 0, La, 28, H1, spacing=3.2, depth=2.2, neon_every=1)
    # tier 2 + 3 stepping back
    p2 = L.chamfer_rect(10, 10, W, D, c, corners=(1, 0, 0, 0))
    mass(B, F, p2, H1, H2, front=w_exo, side=side_plain, back=side_plain, front_dir=(-0.7, -0.7))
    roof_kit(B, F, 0, 0, W, 10, H1, level=1, para=True, poly=poly)
    p3 = [(W * 0.4, D * 0.4), (W, D * 0.4), (W, D), (W * 0.4, D)]
    mass(B, F, p3, H2, H3, front=w_curtain, side=w_curtain, back=side_plain, front_dir=(-0.7, -0.7))
    for (pp, z) in ((poly, H1), (p2, H2), (p3, H3)):
        for i in range(len(pp)):
            a, b = pp[i], pp[(i + 1) % len(pp)]
            WF, Ln = F.wall(a, b)
            nx, ny = (b[1] - a[1]) / Ln, -(b[0] - a[0]) / Ln
            if nx + ny < -0.2:
                neon_h(B, WF, 0, Ln, z - 1.0, B.neon, y=-0.3, w=0.55)
    # 45-degree billboard on tier 2 roof
    s2 = math.sqrt(0.5)
    Fb = Frame(F.w(W * 0.36, D * 0.36, 0), F.d(s2, -s2), F.d(s2, s2))
    bw = 64
    rooftop_billboard(B, Fb, -bw / 2, bw / 2, -10, H2, bw / 2, fmt="W", legs=6)
    roof_kit(B, F, 10, 10, W * 0.4, D, H2, level=2, para=False)
    antenna(B, F, W * 0.75, D * 0.75, H3, 60, base=4)
    roof_kit(B, F, W * 0.4, D * 0.4, W, D, H3, level=2)


def corner_wrap(B, F, W, D):
    """SE: angular tower with a giant chamfer screen, exoskeleton and a cantilevered prow."""
    r_ = B.rng
    B.hero = 3
    B.zb = 16.0
    g = B.g
    c = 34.0
    poly = L.chamfer_rect(0, 0, W, D, c, corners=(1, 0, 0, 0))
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        WF, Ln = F.wall(a, b)
        nx, ny = (b[1] - a[1]) / Ln, -(b[0] - a[0]) / Ln
        if nx + ny < -0.2:
            podium(B, WF, 0, Ln, zp=16.0, second=True)
        else:
            side_plain(B, WF, 0, Ln, -1, 28)
    H = 300.0
    WFc, Lc = F.wall(poly[0], poly[1])
    sw = Lc - 6
    sh = sw * 2
    hole = (3, 44, 3 + sw, 44 + sh)
    mass(B, F, poly, 28, H - 30, front=w_exo, side=w_ribbon, back=side_plain, front_dir=(-0.7, -0.7),
         holes={0: hole})
    recessed_screen(B, WFc, *hole, depth=2.4)
    neon_v(B, WFc, -0.2, 28, H - 30, B.neon, w=0.7)
    neon_v(B, WFc, Lc + 0.2, 28, H - 30, B.neon, w=0.7)
    # prow block cantilevered over the chamfer
    pp = L.chamfer_rect(-6, -6, W, D, c, corners=(1, 0, 0, 0))
    box(g, F, 0, 0, H - 31, 2, 2, H - 30, "STL")
    mass(B, F, pp, H - 30, H, front=w_tech, side=w_tech, back=side_plain, front_dir=(-0.7, -0.7))
    WFp, Lp = F.wall(pp[0], pp[1])
    neon_rect(B, WFp, 0.5, H - 29, Lp - 0.5, H - 1, B.neon2, y=-0.3, w=0.6)
    add_screen(B, WFp, 4, H - 26, Lp - 4, H - 26 + (Lp - 8) / 4, -0.8, kind="ticker", fmt="X", frame=False)
    roof_kit(B, F, 0, 0, W, D, H, level=3, para=True, poly=pp)
    antenna(B, F, W * 0.7, D * 0.7, H, 70, base=4.2)
    for (px, py) in ((W - 10, D * 0.35), (W * 0.35, D - 10)):
        cylinder(g, F, px, py, 3.2, H, H + 26, "MEC", n=12, top="MEC")
        B.reserved.append((px - 4, py - 4, px + 4, py + 4))


def corner_round(B, F, W, D):
    """SW: Shibuya-109 style low drum with screen band + slender needle megatower with holo rings."""
    r_ = B.rng
    B.hero = 3
    B.zb = 16.0
    g = B.g
    R = min(W, D) * 0.4
    cx, cy = R + 3, R + 3
    a_front = 1.25 * math.pi
    Hd = 100.0
    segs = 26
    drum = L.circle_poly(cx, cy, R, segs)
    for i in range(segs):
        a, b = drum[i], drum[(i + 1) % segs]
        WF, Ln = F.wall(a, b)
        mid = math.atan2((a[1] + b[1]) / 2 - cy, (a[0] + b[0]) / 2 - cx) % (2 * math.pi)
        facing = abs((mid - a_front + math.pi) % (2 * math.pi) - math.pi) < 0.55 * math.pi
        if facing:
            podium(B, WF, 0, Ln, zp=16.0) if Ln > 7.5 else w_curtain(B, WF, 0, Ln, -1, 16, fins=False, p=0.8)
            w_curtain(B, WF, 0, Ln, 16, Hd, fins=False, slabs=True, p=0.35)
        else:
            side_plain(B, WF, 0, Ln, -1, Hd)
    g.face("ROF", [F.w(p[0], p[1], Hd) for p in drum])
    span = 0.55 * math.pi
    arc = (R + 1.5) * 2 * span
    hh = min(arc * 3 / 8, 50)
    ob, rec = L.curved_screen(F, cx, cy, R + 1.5, a_front - span, a_front + span, 34, 34 + hh, B.scr_name("C"), B.cs,
                              r_, segs=20, fmt="P")
    B.objs.append(ob)
    for zz in (33.0, 34 + hh + 0.5):
        _ring(B, F, cx, cy, R + 2.3, zz, "STL", segs=20, w=1.6, a0=a_front - span, a1=a_front + span)
        _ring(B, F, cx, cy, R + 4.0, zz, B.neon, segs=20, w=0.45, a0=a_front - span, a1=a_front + span)
    # crown cylinder w/ vertical light fins on the drum
    cylinder(g, F, cx, cy, R * 0.9, Hd, Hd + 10, "TEC", n=20, top="ROF")
    for k in range(10):
        t = a_front - 0.5 * math.pi + math.pi * k / 9
        p = (cx + (R * 0.9 + 0.3) * math.cos(t), cy + (R * 0.9 + 0.3) * math.sin(t))
        box(g, F, p[0] - 0.3, p[1] - 0.3, Hd + 1, p[0] + 0.3, p[1] + 0.3, Hd + 9, B.neon2)
    # needle tower behind
    tx, ty = W * 0.72, D * 0.72
    Ht = 430.0
    for (r0, z0, z1, style) in ((16, -1, 180, w_curtain), (13, 180, 330, w_exo), (10, 330, Ht, w_tech)):
        poly = L.circle_poly(tx, ty, r0, 8, a0=math.pi / 8)
        mass(B, F, poly, z0, z1, front=style, side=w_ribbon, back=side_plain, front_dir=(-0.7, -0.7), roof="ROF")
        _ring(B, F, tx, ty, r0 + 0.4, z1 - 1.5, B.neon, segs=8, w=0.6)
    for zr in (210.0, 290.0, 380.0):  # floating holo rings
        _ring(B, F, tx, ty, 26.0, zr, B.neon2, segs=24, w=0.9)
        for k in range(4):
            t = math.pi / 4 + k * math.pi / 2
            beam(g, F.w(tx + 12 * math.cos(t), ty + 12 * math.sin(t), zr), F.w(tx + 25.5 * math.cos(t),
                                                                              ty + 25.5 * math.sin(t), zr), 0.5, "STL")
    tube(g, F.w(tx, ty, Ht), F.w(tx, ty, Ht + 90), 1.0, "STL", n=6)
    box(g, F, tx - 0.8, ty - 0.8, Ht + 90, tx + 0.8, ty + 0.8, Ht + 92, "NEON_RED")
    L.light(F.w(tx, ty, Ht + 91), (255, 30, 40), 30, 2, name=f"{B.bid}_needle")
    # vertical holo strip on the needle
    p0 = (tx + 8.5 * math.cos(a_front - 0.2), ty + 8.5 * math.sin(a_front - 0.2))
    WFs = Frame(F.w(p0[0], p0[1], 0), F.d(math.cos(a_front - 0.5 * math.pi), math.sin(a_front - 0.5 * math.pi)),
                F.d(-math.cos(a_front), -math.sin(a_front)))
    add_screen(B, WFs, -6, 200, 6, 248, -8.6, kind="holo", fmt="S", neon=B.neon)
    for (px, py) in ((tx, ty),):
        L.light(F.w(cx - R - 15, cy - R - 15, 50), (255, 70, 200), 60, 2.0, name=f"{B.bid}_spill")


# =========================================================================== midground
def mg_lot(B, F, W, D):
    r = B.rng
    B.zb = 16.0
    g = B.g
    B.win_p *= 0.65
    # base block
    Hb = r.choice([28, 40, 52, 64])
    mass(B, F, [(0, 0), (W, 0), (W, D), (0, D)], -1, Hb, front=w_plain, side=w_plain, back=None,
         front_kw={"key": "CON", "windows": 0.2}, side_kw={"key": "CON", "windows": 0.1},
         skip_edges=(2,))
    # tower
    m = r.uniform(2, 6)
    tx0, ty0, tx1, ty1 = m, m, W - r.uniform(2, 6), D - r.uniform(2, 8)
    if tx1 - tx0 < 14 or ty1 - ty0 < 14:
        tx0, ty0, tx1, ty1 = 0.5, 0.5, W - 0.5, D - 0.5
    H = r.choice([156, 172, 196, 220, 244, 268, 292, 316, 340, 376, 412])
    shape = r.choice(["box", "chamfer", "round", "setback", "setback", "cant"])
    face = r.choice(["TWN", "TWN", "GLS", "RIB", "LOU", "TEC"])
    fstyle = {
        "TWN": lambda B_, WF, s0, s1, z0, z1, **k: _flat(B_, WF, s0, s1, z0, z1, "TWN", bay=4.0, wz=(1.9, 11.1)),
        "GLS": lambda B_, WF, s0, s1, z0, z1, **k: _flat(B_, WF, s0, s1, z0, z1, "GLS"),
        "RIB": lambda B_, WF, s0, s1, z0, z1, **k: _flat(B_, WF, s0, s1, z0, z1, "RIB", bay=4.0, wz=(0.3, 7.4)),
        "LOU": lambda B_, WF, s0, s1, z0, z1, **k: _flat(B_, WF, s0, s1, z0, z1, "LOU", lit=False),
        "TEC": lambda B_, WF, s0, s1, z0, z1, **k: w_tech(B_, WF, s0, s1, z0, z1),
    }[face]
    sstyle = lambda B_, WF, s0, s1, z0, z1, **k: _flat(B_, WF, s0, s1, z0, z1, "TWN", bay=4.0, wz=(1.9, 11.1), p=0.12)
    if shape == "chamfer":
        poly = L.chamfer_rect(tx0, ty0, tx1, ty1, min(8, (tx1 - tx0) * 0.2))
    elif shape == "round":
        poly = L.rounded_rect(tx0, ty0, tx1, ty1, min(10, (tx1 - tx0) * 0.3, (ty1 - ty0) * 0.3), n=4,
                              corners=r.choice([(1, 1, 0, 0), (1, 0, 0, 0), (0, 1, 0, 0), (1, 1, 1, 1)]))
    else:
        poly = [(tx0, ty0), (tx1, ty0), (tx1, ty1), (tx0, ty1)]
    zsplit = H if shape not in ("setback", "cant") else Hb + (H - Hb) * r.uniform(0.5, 0.75)
    mass(B, F, poly, Hb, zsplit, front=fstyle, side=sstyle, back=sstyle)
    top_poly = poly
    if shape == "setback":
        sx = (tx1 - tx0) * r.uniform(0.15, 0.3)
        if r.random() < 0.5:
            top_poly = [(tx0 + sx, ty0 + 4), (tx1, ty0 + 4), (tx1, ty1), (tx0 + sx, ty1)]
        else:
            top_poly = [(tx0, ty0 + 4), (tx1 - sx, ty0 + 4), (tx1 - sx, ty1), (tx0, ty1)]
        mass(B, F, top_poly, zsplit, H, front=fstyle, side=sstyle, back=sstyle)
    elif shape == "cant":
        top_poly = [(tx0 - 3, ty0 - 5), (tx1 + 3, ty0 - 5), (tx1 + 3, ty1), (tx0 - 3, ty1)]
        box(g, F, tx0 - 3, ty0 - 5, zsplit - 1.5, tx1 + 3, ty1, zsplit, "STL")
        mass(B, F, top_poly, zsplit, H, front=lambda *a, **k: w_tech(*a), side=sstyle, back=sstyle)
    # neon accents
    WF0, L0 = F.wall(top_poly[0], top_poly[1]) if shape not in ("chamfer",) else F.wall(top_poly[1], top_poly[2])
    if B.hero >= 2:
        neon_h(B, WF0, 0, L0, H - 1.0, B.neon, y=-0.3, w=0.6)
        if r.random() < 0.5:
            neon_v(B, WF0, 0.3, Hb, H, B.neon2, w=0.6)
            neon_v(B, WF0, L0 - 0.3, Hb, H, B.neon2, w=0.6)
    elif B.hero == 1 and r.random() < 0.5:
        neon_h(B, WF0, 0, L0, H - 1.0, B.neon, y=-0.3, w=0.6)
    # screens visible over the foreground
    rs = r.random()
    if rs < 0.5 and L0 > 20 and H > 200:
        sw = min(L0 + r.uniform(0, 12), 84)
        sh = sw / 2 if r.random() < 0.5 else min(sw * 2, (H - 170) * 0.85)
        z0 = max(170.0, H - sh - r.uniform(10, 30))
        if z0 + sh < H + 2:
            add_screen(B, WF0, (L0 - sw) / 2, z0, (L0 + sw) / 2, z0 + sh, -2.5, kind="mg_facade",
                       neon=B.neon if B.hero >= 1 else None)
            for zz in (z0 + sh * 0.25, z0 + sh * 0.75):
                box(g, WF0, (L0 - sw) / 2 + 2, -1.4, zz - 0.6, (L0 + sw) / 2 - 2, 0, zz + 0.6, "STL")
    elif rs < 0.62:
        blade_screen(B, WF0, L0 - 0.6, max(170.0, H * 0.45), min(60, H * 0.3), out=8)
    # roof
    bx = [p[0] for p in top_poly]
    by = [p[1] for p in top_poly]
    if r.random() < 0.3 and (max(bx) - min(bx)) > 22:
        bw = min(max(bx) - min(bx) - 4, 60)
        cxm = (max(bx) + min(bx)) / 2
        rooftop_billboard(B, F, cxm - bw / 2, cxm + bw / 2, min(by) + 3, H, bw / 2, fmt="W", legs=r.uniform(3, 8))
    from cp2_arch import crown
    has_bb = any(True for _ in B.reserved)
    ztop = H if has_bb else crown(B, F, min(bx), min(by), max(bx), max(by), H)
    rk = r.random()
    if rk < 0.22:
        antenna(B, F, (min(bx) + max(bx)) / 2, (min(by) + max(by)) / 2 + 3, ztop, r.uniform(20, 50), base=2.5)
    elif rk < 0.5:
        mast(B, F, max(bx) - 3, max(by) - 3, ztop, r.uniform(12, 30))
    roof_kit(B, F, min(bx), min(by), max(bx), max(by), H, level=1 if B.hero < 2 else 2, poly=top_poly,
             para=has_bb)
    g.face("ROF", [F.w(0, 0, Hb), F.w(W, 0, Hb), F.w(W, D, Hb), F.w(0, D, Hb)])


def _flat(B, WF, s0, s1, z0, z1, key, bay=None, wz=(1.9, 11.7), lit=True, p=None):
    quad(B.g, WF, s0, z0, s1, z1, 0, key, o=WF.w(0, 0, B.zb))
    if lit:
        lit_windows(B, WF, s0, s1, max(z0, B.zb), z1, bay=bay or L.BAY, wz=wz, p=p)


# =========================================================================== skyline
def _strips(B, WF, Ln, z0, z1, every=2, p=0.55):
    """Distant lit-window bands: one quad per lit run (cheap)."""
    k = 0
    z = z0 + 4
    r = B.rng
    while z + 6 < z1:
        if k % every == 0 and r.random() < p:
            x = r.uniform(0, Ln * 0.4)
            while x < Ln - 2:
                run = r.uniform(4, Ln * 0.6)
                if r.random() < 0.6:
                    quad(B.g, WF, x, z, min(Ln - 1, x + run), z + 5.5, -0.08, B.win_key(0, 0))
                x += run + r.uniform(2, 10)
        z += FLOOR
        k += 1


def _bg_mass(B, F, poly, z0, z1, face="TWN", strips=True, every=2, p=0.5):
    n = len(poly)
    for i in range(n):
        WF, Ln = F.wall(poly[i], poly[(i + 1) % n])
        if Ln < 0.3:
            continue
        quad(B.g, WF, 0, z0, Ln, z1, 0, face, o=WF.w(0, 0, 0))
        if strips and Ln > 6:
            _strips(B, WF, Ln, z0, z1, every=every, p=p)
    B.g.face("ROF", [F.w(pp[0], pp[1], z1) for pp in poly])


def _crown(B, F, poly, z, key=None, w=0.7):
    n = len(poly)
    for i in range(n):
        WF, Ln = F.wall(poly[i], poly[(i + 1) % n])
        box(B.g, WF, 0, -w, z - w, Ln, 0, z, key or B.neon, skip=("back",))


def _rot(poly, cx, cy, a):
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + (x - cx) * ca - (y - cy) * sa, cy + (x - cx) * sa + (y - cy) * ca) for x, y in poly]


def bg_tower(B, F, s, H, near):
    """Skyline tower centred on local (0,0); s = footprint half-size. Families give varied silhouettes."""
    r = B.rng
    g = B.g
    fam = r.choice(["stepped", "oct", "twist", "cylfins", "twin", "cant", "hex", "cluster", "stepped", "slab"])
    every = 2 if near else 3
    p = 0.55 if near else 0.45
    neon_on = r.random() < (0.35 if near else 0.25)
    top = H
    if fam == "stepped":
        tiers = r.randint(3, 5)
        z = -1
        ss = s
        for t in range(tiers):
            z1 = z + (H / tiers) * r.uniform(0.8, 1.2) if t < tiers - 1 else H
            poly = L.chamfer_rect(-ss, -ss * r.uniform(0.7, 1), ss, ss, ss * 0.18 * r.random())
            _bg_mass(B, F, poly, z, z1, every=every, p=p)
            if neon_on:
                _crown(B, F, poly, z1, B.neon if t % 2 == 0 else B.neon2)
            z = z1
            ss *= r.uniform(0.68, 0.85)
        top = z
        tube(g, F.w(0, 0, top), F.w(0, 0, top + H * 0.12), 0.8, "STL", n=4)
        top += H * 0.12
    elif fam == "oct":
        z = -1
        rr = s * 1.1
        for t in range(3):
            z1 = z + H / 3
            poly = L.circle_poly(0, 0, rr, 8, a0=math.pi / 8)
            _bg_mass(B, F, poly, z, z1, every=every, p=p)
            if neon_on:
                _crown(B, F, poly, z1, B.neon)
            z = z1
            rr *= 0.8
        prism(g, F, L.circle_poly(0, 0, rr * 0.8, 8, a0=math.pi / 8), z, z + 0.01, "PNL")
        # spire
        for i in range(8):
            a0 = math.pi / 8 + i * math.pi / 4
            a1 = a0 + math.pi / 4
            g.face("PNL", [F.w(rr * math.cos(a0), rr * math.sin(a0), z), F.w(rr * math.cos(a1), rr * math.sin(a1), z),
                           F.w(0, 0, z + H * 0.15)])
        top = z + H * 0.15
    elif fam == "twist":
        nseg = r.randint(6, 10)
        dz = H / nseg
        a = 0.0
        da = math.radians(r.uniform(5, 9)) * r.choice([-1, 1])
        for t in range(nseg):
            poly = _rot([(-s, -s * 0.8), (s, -s * 0.8), (s, s * 0.8), (-s, s * 0.8)], 0, 0, a)
            _bg_mass(B, F, poly, -1 + t * dz, -1 + (t + 1) * dz, every=every, p=p)
            if neon_on and t % 2 == 1:
                _crown(B, F, poly, -1 + (t + 1) * dz, B.neon2, w=0.5)
            a += da
            s *= 0.97
        top = H
    elif fam == "cylfins":
        _bg_mass(B, F, L.circle_poly(0, 0, s, 12), -1, H, every=every, p=p)
        nf = r.choice([4, 6, 8])
        for k in range(nf):
            t = 2 * math.pi * k / nf
            WFf = Frame(F.w(s * math.cos(t), s * math.sin(t), 0), F.d(-math.sin(t), math.cos(t)),
                        F.d(-math.cos(t), -math.sin(t)))
            box(g, WFf, -0.8, -5, 0, 0.8, 0, H * r.uniform(0.85, 1.05), "PNL", skip=("back", "bottom"))
            if neon_on:
                box(g, WFf, -0.2, -5.3, 4, 0.2, -5, H * 0.85, B.neon, skip=("back",))
        top = H
    elif fam == "twin":
        for sx in (-1, 1):
            poly = [(sx * s * 0.15, -s * 0.6), (sx * s, -s * 0.6), (sx * s, s * 0.6), (sx * s * 0.15, s * 0.6)]
            if sx < 0:
                poly = [(sx * s, -s * 0.6), (sx * s * 0.15, -s * 0.6), (sx * s * 0.15, s * 0.6), (sx * s, s * 0.6)]
            hh = H * (1 if sx < 0 else r.uniform(0.75, 0.92))
            _bg_mass(B, F, poly, -1, hh, every=every, p=p)
            if neon_on:
                _crown(B, F, poly, hh, B.neon)
        for zb_ in (H * 0.35, H * 0.62):
            box(g, F, -s * 0.15, -s * 0.3, zb_, s * 0.15, s * 0.3, zb_ + 8, "GLS")
            if neon_on:
                box(g, F, -s * 0.15, -s * 0.32, zb_ - 0.6, s * 0.15, -s * 0.3, zb_, B.neon2)
        top = H
    elif fam == "cant":
        poly = [(-s, -s * 0.7), (s * 0.6, -s * 0.7), (s * 0.6, s * 0.7), (-s, s * 0.7)]
        _bg_mass(B, F, poly, -1, H * 0.78, every=every, p=p)
        poly2 = [(-s * 0.5, -s * 0.9), (s * 1.3, -s * 0.9), (s * 1.3, s * 0.8), (-s * 0.5, s * 0.8)]
        box(g, F, -s * 0.5, -s * 0.9, H * 0.78 - 2, s * 1.3, s * 0.8, H * 0.78, "STL")
        _bg_mass(B, F, poly2, H * 0.78, H, face="TEC", every=every, p=p)
        if neon_on:
            _crown(B, F, poly2, H, B.neon)
            _crown(B, F, poly2, H * 0.78 + 1.5, B.neon2, w=0.5)
        top = H
    elif fam == "hex":
        poly = L.circle_poly(0, 0, s * 1.1, 6)
        _bg_mass(B, F, poly, -1, H * 0.85, every=every, p=p)
        poly2 = L.circle_poly(0, 0, s * 0.8, 6, a0=math.pi / 6)
        _bg_mass(B, F, poly2, H * 0.85, H, face="PNL", strips=False)
        if neon_on:
            _crown(B, F, poly, H * 0.85, B.neon)
        for k in range(3):
            t = 2 * math.pi * k / 3
            tube(g, F.w(s * 0.5 * math.cos(t), s * 0.5 * math.sin(t), H), F.w(s * 0.5 * math.cos(t),
                                                                            s * 0.5 * math.sin(t), H + H * 0.1),
                 0.5, "STL", n=4)
        top = H * 1.1
    elif fam == "cluster":
        for k, (ox, oy, f) in enumerate(((-s * 0.45, 0, 1.0), (s * 0.5, -s * 0.3, 0.8), (s * 0.3, s * 0.55, 0.62))):
            ss = s * 0.48
            poly = L.chamfer_rect(ox - ss, oy - ss, ox + ss, oy + ss, ss * 0.3)
            _bg_mass(B, F, poly, -1, H * f, every=every, p=p)
            if neon_on and k == 0:
                _crown(B, F, poly, H * f, B.neon)
        top = H
    else:  # slab
        poly = [(-s * 1.2, -s * 0.45), (s * 1.2, -s * 0.45), (s * 1.2, s * 0.45), (-s * 1.2, s * 0.45)]
        _bg_mass(B, F, poly, -1, H, every=every, p=p)
        WF, Ln = F.wall(poly[0], poly[1])
        if neon_on:
            for x in (0.3, Ln - 0.3):
                neon_v(B, WF, x, 4, H, B.neon, w=0.8)
        top = H
    # roof clutter for silhouettes (merged, cheap)
    if r.random() < 0.6:
        for _ in range(r.randint(1, 3)):
            px, py = r.uniform(-s * 0.4, s * 0.4), r.uniform(-s * 0.3, s * 0.3)
            hz = top if fam not in ("oct", "hex", "stepped") else H
            box(g, F, px - 2, py - 2, hz, px + 2, py + 2, hz + r.uniform(2, 6), "MEC", skip=("bottom",))
    if r.random() < 0.55:
        h = r.uniform(12, 40)
        tube(g, F.w(s * 0.3, s * 0.2, H), F.w(s * 0.3, s * 0.2, H + h), 0.4, "STL", n=4)
        box(g, F, s * 0.3 - 0.5, s * 0.2 - 0.5, H + h, s * 0.3 + 0.5, s * 0.2 + 0.5, H + h + 1, "NEON_RED")
    return top


def bg_screen(B, F, s, H):
    """Crown-level billboard on a skyline tower facing the plaza (local -y)."""
    r = B.rng
    sw = min(s * 2.4, r.uniform(50, 90))
    sh = sw / 2
    z0 = H - sh - r.uniform(10, 30)
    WF = Frame(F.w(-sw / 2, -s * 0.9 - 3, 0), F.ax, F.ay)
    add_screen(B, WF, 0, z0, sw, z0 + sh, 0, kind="skyline", fmt="W", neon=B.neon, light=False)
    for x in (2, sw - 2):
        beam(B.g, WF.w(x, 0.5, z0 + sh * 0.5), WF.w(x, 4.5, z0 + sh * 0.5), 0.8, "STL")


# =========================================================================== megatowers
def mega_tower(B, F, H, s):
    """Extremely tall distant megastructure (900-1700 studs) with sky lobbies, ribs, giant screens."""
    r = B.rng
    g = B.g
    B.hero = 3
    B.zb = 0.0
    n_seg = r.randint(3, 4)
    z = -1.0
    ss = s
    shape = r.choice(["chamfer", "oct", "round"])
    ribs_on = True
    seg_h = (H * 0.86) / n_seg
    polys = []
    for t in range(n_seg):
        if shape == "oct":
            poly = L.circle_poly(0, 0, ss * 1.08, 8, a0=math.pi / 8)
        elif shape == "round":
            poly = L.rounded_rect(-ss, -ss, ss, ss, ss * 0.35, n=3)
        else:
            poly = L.chamfer_rect(-ss, -ss, ss, ss, ss * 0.28)
        z1 = z + seg_h - (24 if t < n_seg - 1 else 0)
        _bg_mass(B, F, poly, z, z1, every=2, p=0.5)
        polys.append((poly, z, z1))
        _crown(B, F, poly, z1, B.neon if t % 2 == 0 else B.neon2, w=1.2)
        # vertical ribs on the corners / mid faces
        n = len(poly)
        for i in range(n):
            WF, Ln = F.wall(poly[i], poly[(i + 1) % n])
            if Ln > 20:
                box(g, WF, Ln / 2 - 1.2, -3, z + 6, Ln / 2 + 1.2, 0, z1 - 4, "PNL", skip=("back", "bottom"))
                box(g, WF, Ln / 2 - 0.3, -3.4, z + 8, Ln / 2 + 0.3, -3, z1 - 6, B.neon2 if i % 2 else B.neon,
                    skip=("back",))
        if t < n_seg - 1:
            # sky lobby: exposed columns + glowing band
            zl0, zl1 = z1, z1 + 24
            inner = [(x * 0.8, y * 0.8) for x, y in poly]
            _bg_mass(B, F, inner, zl0, zl1, face="GLS", strips=False)
            for (x, y) in poly:
                box(g, F, x * 0.96 - 1.5, y * 0.96 - 1.5, zl0, x * 0.96 + 1.5, y * 0.96 + 1.5, zl1, "STL")
            nI = len(inner)
            for i in range(nI):
                WF, Ln = F.wall(inner[i], inner[(i + 1) % nI])
                quad(g, WF, 0.5, zl0 + 4, Ln - 0.5, zl1 - 4, -0.1, "WIN_VIO" if t % 2 else "WIN_COL")
            g.face("STL", [F.w(p[0], p[1], zl0) for p in poly])
            z = zl1
        else:
            z = z1
        ss *= r.uniform(0.72, 0.84)
    # giant vertical screen on the plaza-facing side of the lowest/middle segment
    poly, za, zbb = polys[min(1, len(polys) - 1)]
    sw = min(70.0, s * 1.1)
    sh = min(sw * 2, (zbb - za) * 0.8)
    zc = za + (zbb - za - sh) / 2
    WF = Frame(F.w(-sw / 2, min(p[1] for p in poly) - 4, 0), F.ax, F.ay)
    add_screen(B, WF, 0, zc, sw, zc + sh, 0, kind="mega", fmt="T", neon=B.neon, light=False)
    for zz in (zc + sh * 0.25, zc + sh * 0.75):
        for x in (3, sw - 3):
            beam(g, WF.w(x, 0.5, zz), WF.w(x, 4.5, zz), 1.0, "STL")
    # crown + spire + holo rings
    top_poly = polys[-1][0]
    zt = polys[-1][2]
    cr = max(abs(p[0]) for p in top_poly) * 0.7
    for k in range(3):
        cylinder(g, F, 0, 0, cr * (1 - 0.22 * k), zt + k * 14, zt + (k + 1) * 14, "TEC" if k % 2 else "PNL", n=12,
                 top="ROF")
        _ring_simple(B, F, 0, 0, cr * (1 - 0.22 * k) + 0.4, zt + (k + 1) * 14 - 1.5, B.neon, 12)
    zs = zt + 42
    tube(g, F.w(0, 0, zs), F.w(0, 0, zs + H * 0.14), 2.2, "STL", n=8)
    tube(g, F.w(0, 0, zs + H * 0.14), F.w(0, 0, zs + H * 0.2), 0.8, "STL", n=6)
    box(g, F, -1.5, -1.5, zs + H * 0.2, 1.5, 1.5, zs + H * 0.2 + 3, "NEON_RED")
    for k in range(2):
        _ring_simple(B, F, 0, 0, cr * 1.6 + k * 10, zs + 20 + k * 40, B.neon2, 20, w=1.5)
    L.light(F.w(0, 0, zs + H * 0.2 + 1), (255, 30, 40), 60, 3, name=f"{B.bid}_beacon")


def _ring_simple(B, F, cx, cy, r, z, key, segs, w=0.8):
    for i in range(segs):
        t0, t1 = 2 * math.pi * i / segs, 2 * math.pi * (i + 1) / segs
        p0 = (cx + r * math.cos(t0), cy + r * math.sin(t0))
        p1 = (cx + r * math.cos(t1), cy + r * math.sin(t1))
        WF, Ln = F.wall(p0, p1)
        box(B.g, WF, -0.1, -w, z - w / 2, Ln + 0.1, 0, z + w / 2, key, skip=("back",))


# =========================================================================== streetscape
def street_gate(B, F, width, z0, h):
    """Advertisement panel suspended across a side street, between the flanking buildings.
    F: origin at the left kerb, x across the street, -y faces the plaza."""
    g = B.g
    sw = width - 10
    add_screen(B, F, 5, z0, 5 + sw, z0 + sh_of(sw, "W"), 0, kind="suspended", fmt="W", neon=B.neon)
    # back face shows another ad (faces away from the plaza)
    Fb = Frame(F.w(width, 1.3, 0), -F.ax, -F.ay)
    add_screen(B, Fb, 5, z0, 5 + sw, z0 + sh_of(sw, "W"), 0, kind="suspended", fmt="W", frame=False, light=False)
    zt = z0 + sh_of(sw, "W")
    # cables / hangers to the buildings
    for x in (6, width - 6):
        tube(g, F.w(x, 0.6, zt + 1), F.w(0 if x < width / 2 else width, 0.6, zt + 14), 0.25, "STL", n=4)
        tube(g, F.w(x, 0.6, z0 - 1), F.w(0 if x < width / 2 else width, 0.6, z0 - 10), 0.25, "STL", n=4)
    box(g, F, 0, -0.6, zt + 13, width, 1.8, zt + 14.2, "STL")
    neon_h(B, F, 0.5, width - 0.5, zt + 12.6, B.neon2, y=-0.8, w=0.35)
    # enclosed glass skybridge further up, deeper in the side street
    zb = B.rng.choice([104.0, 116.0, 128.0])
    yb = 22.0
    box(g, F, -1, yb, zb - 1.2, width + 1, yb + 9, zb, "STL")                    # deck
    box(g, F, -1, yb, zb + 8.5, width + 1, yb + 9, zb + 9.4, "STL")              # roof
    for (y0, y1) in ((yb, yb + 0.3), (yb + 8.7, yb + 9)):
        box(g, F, 0, y0, zb, width, y1, zb + 8.5, "GLS", skip=("top", "bottom"))
    x = 0.0
    while x <= width:
        box(g, F, x - 0.35, yb - 0.3, zb, x + 0.35, yb + 9.3, zb + 8.5, "STL", skip=("bottom", "top"))
        x += 6.0
    quad(g, F, 0.5, zb + 0.4, width - 0.5, zb + 7.8, yb + 0.35, "WIN_VIO")
    neon_h(B, F, 0, width, zb - 1.4, B.neon, y=yb - 0.2, w=0.3)
    neon_h(B, F, 0, width, zb + 9.6, B.neon2, y=yb - 0.2, w=0.3)


def sh_of(w, fmt):
    return w / L.FMT_ASPECT[fmt]
