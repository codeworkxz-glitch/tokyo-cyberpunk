"""HEX! Cyberpunk City v2 - architectural kit: facades, storefronts, signage, billboards,
rooftop machinery and the building archetypes (foreground / midground / skyline / mega).
"""
import math
import random

from mathutils import Vector

import cp2_lib as L
from cp2_lib import BAY, FLOOR, Frame, Geo, box, quad, prism, tube, beam, cylinder

SIGN_CELLS = {"SGH": [], "SGV": []}  # filled by cp2_build from the original map's sign UVs

PALETTES = [
    ("NEON_CYN", "NEON_MAG"), ("NEON_MAG", "NEON_VIO"), ("NEON_BLU", "NEON_CYN"), ("NEON_VIO", "NEON_CYN"),
    ("NEON_MAG", "NEON_CYN"), ("NEON_CYN", "NEON_VIO"), ("NEON_RED", "NEON_MAG"), ("NEON_VIO", "NEON_MAG"),
    ("NEON_BLU", "NEON_MAG"), ("NEON_CYN", "NEON_BLU"),
]


class Ctx:
    """Per-building context."""

    def __init__(self, bid, seed, coll_geo, coll_scr, coll_prop, hero=1):
        self.bid = bid
        self.rng = random.Random(seed)
        self.g = Geo()
        self.cg, self.cs, self.cp = coll_geo, coll_scr, coll_prop
        self.hero = hero
        r = self.rng
        self.neon, self.neon2 = PALETTES[r.randrange(len(PALETTES))]
        self.win_main = r.choices(["WIN_WRM", "WIN_COL", "WIN_VIO", "WIN_PNK"], [6, 4, 1.2, 1])[0]
        self.win_acc = r.choice(["WIN_PNK", "WIN_VIO", "WIN_COL", "WIN_WRM"])
        self.win_mode = r.choices(["scatter", "bands", "cluster", "columns"], [4, 2, 3, 1])[0]
        self.win_p = r.uniform(0.12, 0.32)
        self.ph = (r.uniform(0, 6.28), r.uniform(0, 6.28), r.uniform(0.4, 1.1), r.uniform(0.4, 1.1))
        self.zb = 16.0  # uv / floor base above the podium
        self.nscr = 0
        self.nprop = 0
        self.objs = []
        self.reserved = []  # roof rects (world-ish local) not to fill with props

    def scr_name(self, tag=""):
        self.nscr += 1
        return f"SCR_{self.bid}_{self.nscr:02d}{tag}"

    def win_key(self, i, k):
        r = self.rng.random()
        return self.win_acc if r < 0.14 else self.win_main

    def finish(self):
        return L.flush(self.g, self.bid, self.cg, self.objs)


# =========================================================================== facade styles
# style(B, WF, s0, s1, z0, z1, **kw) must cover the wall rectangle [s0,s1] x [z0,z1] at y=0.

def _o(B, WF):
    return WF.w(0, 0, B.zb)


def lit_windows(B, WF, s0, s1, z0, z1, bay=BAY, wz=(2.8, 10.9), bx=0.55, y=-0.06, p=None, mode=None, keyf=None):
    g = B.g
    mode = mode or B.win_mode
    p = B.win_p if p is None else p
    r = B.rng
    i0, i1 = math.ceil(s0 / bay - 1e-6), math.floor(s1 / bay + 1e-6)
    k0 = math.ceil((z0 - B.zb) / FLOOR - 1e-6)
    k1 = math.floor((z1 - B.zb) / FLOOR + 1e-6)
    a, b, fa, fb = B.ph
    band_on = {}
    col_on = {}
    for k in range(k0, k1):
        zf = B.zb + k * FLOOR
        if mode == "bands":
            band_on[k] = r.random() < p * 1.6
        for i in range(i0, i1):
            if mode == "scatter":
                on = r.random() < p
            elif mode == "bands":
                on = band_on[k] and r.random() < 0.85
            elif mode == "cluster":
                v = math.sin(i * fa + a) + math.sin(k * fb + b) + r.uniform(-0.6, 0.6)
                on = v > 1.6 - p * 3.2
            else:
                if i not in col_on:
                    col_on[i] = r.random() < p * 1.5
                on = col_on[i] and r.random() < 0.8
            if not on:
                continue
            key = keyf(i, k) if keyf else B.win_key(i, k)
            x0, x1 = i * bay + bx, (i + 1) * bay - bx
            za, zb_ = zf + wz[0], zf + wz[1]
            v = r.random()
            if v < 0.22:      # blinds half down
                za = za + (zb_ - za) * r.uniform(0.35, 0.6)
            elif v < 0.32:    # lamp glow in one corner of the room
                if r.random() < 0.5:
                    x1 = x0 + (x1 - x0) * 0.5
                else:
                    x0 = x1 - (x1 - x0) * 0.5
            elif v < 0.38:    # screen-lit, low strip
                zb_ = za + (zb_ - za) * 0.35
            quad(g, WF, x0, za, x1, zb_, y, key)


def w_plain(B, WF, s0, s1, z0, z1, key="CON", windows=0.0, wkey="TWN"):
    quad(B.g, WF, s0, z0, s1, z1, 0, key, o=_o(B, WF))
    if windows > 0 and z1 - z0 > 14:
        lit_windows(B, WF, s0, s1, max(z0, B.zb), z1, bay=4.0, wz=(3, 9), p=windows, mode="scatter")


def w_curtain(B, WF, s0, s1, z0, z1, fins=True, slabs=True, glass="GLS", fin_key="STL", p=None):
    g = B.g
    o = _o(B, WF)
    quad(g, WF, s0, z0, s1, z1, 0, glass, o=o)
    if fins:
        i = math.ceil(s0 / (BAY * 2))
        while i * BAY * 2 < s1 - 0.5:
            x = i * BAY * 2
            if x > s0 + 0.5:
                box(g, WF, x - 0.2, -0.7, z0, x + 0.2, 0, z1, fin_key, skip=("back", "bottom"))
            i += 1
    if slabs:
        k = math.ceil((z0 - B.zb) / FLOOR)
        while B.zb + k * FLOOR < z1 - 1:
            z = B.zb + k * FLOOR
            if z > z0 + 0.5 and k % 2 == 0:
                box(g, WF, s0, -0.5, z - 0.3, s1, 0, z + 0.4, fin_key, skip=("back",))
            k += 1
    lit_windows(B, WF, s0, s1, max(z0, B.zb), z1, p=p)


def w_ribbon(B, WF, s0, s1, z0, z1, shades=True, p=None):
    g = B.g
    quad(g, WF, s0, z0, s1, z1, 0, "RIB", o=_o(B, WF))
    if shades:
        k = math.ceil((z0 - B.zb) / FLOOR)
        while B.zb + k * FLOOR + 7.6 < z1:
            z = B.zb + k * FLOOR + 7.6
            box(g, WF, s0, -1.4, z, s1, 0, z + 0.35, "STL", skip=("back",))
            k += 1
    lit_windows(B, WF, s0, s1, max(z0, B.zb), z1, bay=4.0, wz=(0.3, 7.4), bx=0.12, p=p)


def _grid_wall(B, WF, s0, s1, z0, z1, cols, rows, key, depth, glass="GLS", o=None):
    """Wall with recessed openings: cols = [(a,b)], rows = [(c,d)] (absolute s / z)."""
    g = B.g
    # horizontal strips between rows
    zs = [z0] + [v for r_ in rows for v in r_] + [z1]
    for i in range(0, len(zs), 2):
        if zs[i + 1] - zs[i] > 1e-3:
            quad(g, WF, s0, zs[i], s1, zs[i + 1], 0, key, o=o)
    ss = [s0] + [v for c in cols for v in c] + [s1]
    for (c0, c1) in rows:
        for i in range(0, len(ss), 2):
            if ss[i + 1] - ss[i] > 1e-3:
                quad(g, WF, ss[i], c0, ss[i + 1], c1, 0, key, o=o)
        for (a, b) in cols:  # opening: reveals + glass
            w = WF.w
            g.face(key, [w(a, 0, c0), w(a, depth, c0), w(a, depth, c1), w(a, 0, c1)], o=o)
            g.face(key, [w(b, depth, c0), w(b, 0, c0), w(b, 0, c1), w(b, depth, c1)], o=o)
            g.face(key, [w(a, 0, c0), w(b, 0, c0), w(b, depth, c0), w(a, depth, c0)], o=o)
            g.face(key, [w(a, depth, c1), w(b, depth, c1), w(b, 0, c1), w(a, 0, c1)], o=o)
            quad(g, WF, a, c0, b, c1, depth, glass, o=o)


def w_punched(B, WF, s0, s1, z0, z1, key="PNL", win_w=3.4, win_h=7.0, depth=0.9, bay=None, p=None):
    bay = bay or BAY
    o = _o(B, WF)
    cols = []
    i = math.ceil(s0 / bay)
    while (i + 1) * bay <= s1 + 1e-6:
        c = (i + 0.5) * bay
        cols.append((c - win_w / 2, c + win_w / 2))
        i += 1
    rows = []
    k = math.ceil((z0 - B.zb) / FLOOR - 1e-6)
    while B.zb + (k + 1) * FLOOR <= z1 + 1e-6:
        zf = B.zb + k * FLOOR
        rows.append((zf + 3.0, zf + 3.0 + win_h))
        k += 1
    if not cols or not rows:
        quad(B.g, WF, s0, z0, s1, z1, 0, key, o=o)
        return
    _grid_wall(B, WF, s0, s1, z0, z1, cols, rows, key, depth, o=o)
    pp = B.win_p if p is None else p
    for (a, b) in cols:
        for (c0, c1) in rows:
            if B.rng.random() < pp:
                quad(B.g, WF, a + 0.1, c0 + 0.1, b - 0.1, c1 - 0.1, depth - 0.05, B.win_key(0, 0))
            # small facade AC units under some windows
            if B.rng.random() < 0.06:
                ac_unit(B, WF, a, c0 - 2.0)


def w_louver(B, WF, s0, s1, z0, z1, fin_key="PNL", pitch=2.67, depth=1.8, p=None):
    g = B.g
    quad(g, WF, s0, z0, s1, z1, 0, "GLS", o=_o(B, WF))
    x = s0 + pitch / 2
    while x < s1 - 0.3:
        box(g, WF, x - 0.25, -depth, z0, x + 0.25, 0, z1, fin_key, skip=("back", "bottom"))
        x += pitch
    lit_windows(B, WF, s0, s1, max(z0, B.zb), z1, p=p)


def w_balcony(B, WF, s0, s1, z0, z1, p=None):
    g = B.g
    o = _o(B, WF)
    quad(g, WF, s0, z0, s1, z1, 0, "GLS", o=o)
    k = math.ceil((z0 - B.zb) / FLOOR - 1e-6)
    unit = max(8.0, (s1 - s0) / max(1, round((s1 - s0) / 10)))
    while B.zb + k * FLOOR < z1 - 2:
        z = B.zb + k * FLOOR
        if z >= z0:
            box(g, WF, s0, -3.4, z - 0.6, s1, 0, z, "CON", skip=("back",))          # slab
            box(g, WF, s0, -3.4, z, s1, -3.1, z + 3.4, "TEC", skip=("back", "bottom"))  # balustrade
            x = s0
            while x < s1 - 1:
                box(g, WF, x, -3.4, z, x + 0.35, 0, z + FLOOR - 0.6, "CON", skip=("back", "bottom", "top"))
                if B.rng.random() < 0.35:
                    box(g, WF, x + 1, -2.4, z, x + 3.2, -1.2, z + 1.6, "MEC", skip=("back", "bottom"))
                x += unit
        k += 1
    lit_windows(B, WF, s0, s1, max(z0, B.zb), z1, p=p)


def w_tech(B, WF, s0, s1, z0, z1, p=None, strips=True):
    g = B.g
    quad(g, WF, s0, z0, s1, z1, 0, "TEC", o=_o(B, WF))
    # horizontal slit windows
    k = math.ceil((z0 - B.zb) / FLOOR - 1e-6)
    pp = B.win_p if p is None else p
    while B.zb + (k + 1) * FLOOR <= z1 + 1e-6:
        zf = B.zb + k * FLOOR
        x = s0 + 1.0
        while x < s1 - 3:
            w = B.rng.uniform(3, 9)
            if B.rng.random() < pp:
                quad(g, WF, x, zf + 5.0, min(s1 - 1, x + w), zf + 6.6, -0.06, B.win_key(0, k))
            x += w + B.rng.uniform(1, 3)
        k += 1
    if strips and B.hero >= 2:
        n = max(1, int((s1 - s0) / 14))
        for j in range(n):
            x = s0 + (j + 0.5) * (s1 - s0) / n
            box(g, WF, x - 0.2, -0.25, z0 + 2, x + 0.2, 0, z1 - 2, B.neon2 if j % 2 else B.neon, skip=("back",))


def w_exo(B, WF, s0, s1, z0, z1, p=None, ribs_neon=True):
    w_curtain(B, WF, s0, s1, z0, z1, fins=False, slabs=False, p=p)
    exo_braces(B, WF, s0, s1, z0, z1, neon=ribs_neon)


STYLES = {"curtain": w_curtain, "ribbon": w_ribbon, "punched": w_punched, "louver": w_louver,
          "balcony": w_balcony, "tech": w_tech, "exo": w_exo, "plain": w_plain}


# =========================================================================== small elements
def ac_unit(B, WF, s, z):
    box(B.g, WF, s, -1.2, z, s + 2.2, 0, z + 1.5, "MEC", skip=("back",))


def neon_v(B, WF, s, z0, z1, key=None, y=-0.3, w=0.45):
    box(B.g, WF, s - w / 2, y - w / 2, z0, s + w / 2, y + w / 2, z1, key or B.neon, skip=("bottom",))


def neon_h(B, WF, s0, s1, z, key=None, y=-0.3, w=0.45):
    box(B.g, WF, s0, y - w / 2, z - w / 2, s1, y + w / 2, z + w / 2, key or B.neon, skip=("back",))


def neon_rect(B, WF, s0, z0, s1, z1, key=None, y=-0.3, w=0.4):
    neon_h(B, WF, s0, s1, z0, key, y, w)
    neon_h(B, WF, s0, s1, z1, key, y, w)
    neon_v(B, WF, s0, z0, z1, key, y, w)
    neon_v(B, WF, s1, z0, z1, key, y, w)


def pipes(B, WF, s, z0, z1, n=3, y=-0.9):
    for i in range(n):
        r = B.rng.choice([0.3, 0.4, 0.55])
        x = s + i * 1.3
        tube(B.g, WF.w(x, y, z0), WF.w(x, y, z1), r, "STL", n=6)
    zz = z0 + 6
    while zz < z1:
        box(B.g, WF, s - 0.6, -1.6, zz, s + (n - 1) * 1.3 + 0.6, 0, zz + 0.5, "STL", skip=("back",))
        zz += 12


def catwalk(B, WF, s0, s1, z, out=2.6, lights=True):
    g = B.g
    box(g, WF, s0, -out, z - 0.35, s1, 0, z, "STL", skip=("back",))
    tube(g, WF.w(s0, -out + 0.15, z + 3.4), WF.w(s1, -out + 0.15, z + 3.4), 0.12, "STL", n=4)
    tube(g, WF.w(s0, -out + 0.15, z + 1.7), WF.w(s1, -out + 0.15, z + 1.7), 0.08, "STL", n=4)
    x = s0
    while x <= s1 + 0.01:
        tube(g, WF.w(x, -out + 0.15, z), WF.w(x, -out + 0.15, z + 3.4), 0.1, "STL", n=4)
        x += 4.0
    # brackets
    x = s0 + 1
    while x < s1:
        beam(g, WF.w(x, 0, z - 3), WF.w(x, -out + 0.3, z - 0.3), 0.3, "STL")
        x += 8
    if lights and B.hero >= 2:
        neon_h(B, WF, s0, s1, z - 0.45, B.neon, y=-out + 0.3, w=0.25)


def ribs(B, WF, s0, s1, z0, z1, spacing=6.0, depth=1.6, neon_every=2, key="PNL"):
    i = 0
    x = s0 + spacing / 2
    while x < s1 - 0.4:
        box(B.g, WF, x - 0.35, -depth, z0, x + 0.35, 0, z1, key, skip=("back", "bottom"))
        if neon_every and i % neon_every == 0 and B.hero >= 2:
            box(B.g, WF, x - 0.12, -depth - 0.2, z0 + 1, x + 0.12, -depth, z1 - 1, B.neon if i % 4 == 0 else B.neon2,
                skip=("back",))
        i += 1
        x += spacing


def exo_braces(B, WF, s0, s1, z0, z1, bay=None, neon=True):
    g = B.g
    span = s1 - s0
    n = max(1, round(span / (bay or 14.0)))
    xs = [s0 + span * i / n for i in range(n + 1)]
    xs[0] += 0.8
    xs[-1] -= 0.8
    lv = 3 * FLOOR
    zs = []
    z = z0
    while z < z1 - 4:
        zs.append(z)
        z += lv
    zs.append(z1)
    for x in xs:
        box(g, WF, x - 0.8, -3.2, z0, x + 0.8, -1.6, z1, "STL", skip=("bottom",))
        if neon and B.hero >= 2:
            box(g, WF, x - 0.15, -3.4, z0 + 2, x + 0.15, -3.2, z1 - 2, B.neon, skip=("back",))
    for z in zs:
        box(g, WF, s0, -3.0, z - 0.5, s1, -1.8, z + 0.5, "STL", skip=())
    for j in range(len(zs) - 1):
        za, zb_ = zs[j], zs[j + 1]
        for i in range(len(xs) - 1):
            xa, xb = xs[i], xs[i + 1]
            beam(g, WF.w(xa, -2.4, za), WF.w(xb, -2.4, zb_), 0.55, "STL")
            beam(g, WF.w(xb, -2.4, za), WF.w(xa, -2.4, zb_), 0.55, "STL")
    # brackets back to facade
    for x in xs:
        for z in zs:
            box(g, WF, x - 0.3, -1.6, z - 0.3, x + 0.3, 0, z + 0.3, "STL", skip=("back",))


def alley_dressing(B, WF, Ln, z0, z1):
    """Service-alley side wall: big ventilation duct riser with branches, fire-escape stair,
    stacked AC units, cables and a small neon sign."""
    r = B.rng
    g = B.g
    s = r.uniform(2.0, max(2.1, Ln * 0.3))
    top = min(z1 - 2, z0 + r.uniform(60, 140))
    box(g, WF, s, -2.6, z0, s + 2.6, 0, top, "MEC", skip=("back", "bottom"))
    zz = z0 + 14
    while zz < top - 6:
        if r.random() < 0.6:
            box(g, WF, s + 2.6, -1.8, zz, s + r.uniform(5, 9), 0, zz + 1.6, "MEC", skip=("back",))
        box(g, WF, s - 0.3, -2.9, zz, s + 2.9, -2.6, zz + 0.6, "STL", skip=("back",))
        zz += r.uniform(10, 18)
    cylinder(g, WF, s + 1.3, -1.3, 1.6, top, top + 3.0, "MEC", n=8, top="MEC")
    # zig-zag fire escape
    fx = min(Ln - 7, s + 6)
    z = z0 + 12
    flip = False
    while z < min(top, z0 + 80) and fx > 0:
        box(g, WF, fx, -2.4, z - 0.3, fx + 6, 0, z, "STL", skip=("back",))
        tube(g, WF.w(fx, -2.3, z + 3.2), WF.w(fx + 6, -2.3, z + 3.2), 0.08, "STL", n=4)
        a, b = (fx + 0.5, fx + 5.5) if not flip else (fx + 5.5, fx + 0.5)
        beam(g, WF.w(a, -1.4, z), WF.w(b, -1.4, z + 12), 0.5, "STL")
        flip = not flip
        z += 12
    for _ in range(r.randint(2, 5)):
        ac_unit(B, WF, r.uniform(1, max(1.1, Ln - 3)), r.uniform(z0 + 6, min(top, z0 + 60)))
    if B.hero >= 1:
        flat_sign(B, WF, max(0.5, Ln - 5), z0 + 9, 3.2, 1.4, y=-0.4, kind="SGH")


def bay_boxes(B, WF, s0, s1, z0, z1):
    """Projecting glazed bay boxes on alternate floors: layered zakkyo facade."""
    r = B.rng
    g = B.g
    w = min(7.0, (s1 - s0) * 0.4)
    sx = r.choice([s0 + 1.0, s1 - 1.0 - w, (s0 + s1 - w) / 2])
    k = math.ceil((z0 - B.zb) / FLOOR)
    while B.zb + (k + 1) * FLOOR <= z1:
        z = B.zb + k * FLOOR
        if (k % 2 == 0) and r.random() < 0.8:
            box(g, WF, sx, -1.8, z + 0.6, sx + w, 0, z + FLOOR - 0.6, "PNL", skip=("back", "front"))
            quad(g, WF, sx, z + 0.6, sx + w, z + FLOOR - 0.6, -1.8, "GLS", o=WF.w(0, 0, B.zb))
            if r.random() < 0.55:
                quad(g, WF, sx + 0.4, z + 2.6, sx + w - 0.4, z + FLOOR - 1.2, -1.86, B.win_key(0, k))
        k += 1


def sign_cell(kind, rng, aspect=None):
    cells = SIGN_CELLS[kind]
    if aspect:
        cells = sorted(cells, key=lambda c: abs(math.log(((c[2] - c[0]) * 1.0) / max(1e-6, (c[3] - c[1])) / aspect)))[:12]
    return rng.choice(cells)


def _sign_uv(cell, flip=False):
    u0, v0, u1, v1 = cell
    if flip:
        u0, u1 = u1, u0
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def flat_sign(B, WF, s0, z0, w, h, y=-0.5, kind="SGH", glow=True):
    """Box sign on the facade; front face shows a cell of the sign atlas."""
    cell = sign_cell(kind, B.rng, aspect=w / h)
    box(B.g, WF, s0, y, z0, s0 + w, 0, z0 + h, "STL", skip=("front", "back"))
    quad(B.g, WF, s0, z0, s0 + w, z0 + h, y, kind, uv=_sign_uv(cell))
    if glow and B.hero >= 1 and B.rng.random() < 0.35:
        neon_rect(B, WF, s0 - 0.25, z0 - 0.25, s0 + w + 0.25, z0 + h + 0.25, B.rng.choice([B.neon, B.neon2]), y=y - 0.1,
                  w=0.22)


def blade_sign(B, WF, s, z0, h, out=4.2, t=0.6, kind="SGV"):
    """Vertical sign projecting perpendicular from the facade (both sides textured)."""
    cell = sign_cell(kind, B.rng, aspect=out / h)
    g = B.g
    w = WF.w
    x0, x1 = s - t / 2, s + t / 2
    y0, y1 = -out - 0.4, -0.4
    # side facing -x (left)
    g.face(kind, [w(x0, y1, z0), w(x0, y0, z0), w(x0, y0, z0 + h), w(x0, y1, z0 + h)], uv=_sign_uv(cell, flip=True))
    g.face(kind, [w(x1, y0, z0), w(x1, y1, z0), w(x1, y1, z0 + h), w(x1, y0, z0 + h)], uv=_sign_uv(cell))
    box(g, WF, x0, y0, z0, x1, y1, z0 + h, "STL", skip=("left", "right", "back"))
    box(g, WF, s - 0.2, y1, z0 + 1, s + 0.2, 0, z0 + 1.5, "STL")
    box(g, WF, s - 0.2, y1, z0 + h - 1.5, s + 0.2, 0, z0 + h - 1, "STL")
    if B.rng.random() < 0.45:
        box(g, WF, x0 - 0.1, y0 - 0.25, z0, x1 + 0.1, y0, z0 + h, B.rng.choice([B.neon, B.neon2]), skip=("back",))


# =========================================================================== screens
def screen_frame(B, WF, x0, z0, x1, z1, y, t=0.7, depth=1.2, neon=None, back=True):
    g = B.g
    box(g, WF, x0 - t, y - 0.3, z0 - t, x1 + t, y + depth, z0, "STL")
    box(g, WF, x0 - t, y - 0.3, z1, x1 + t, y + depth, z1 + t, "STL")
    box(g, WF, x0 - t, y - 0.3, z0, x0, y + depth, z1, "STL", skip=("top", "bottom"))
    box(g, WF, x1, y - 0.3, z0, x1 + t, y + depth, z1, "STL", skip=("top", "bottom"))
    if back:
        box(g, WF, x0, y + 0.05, z0, x1, y + depth, z1, "PNL", skip=("front", "top", "bottom", "left", "right"))
    if neon:
        neon_rect(B, WF, x0 - t - 0.3, z0 - t - 0.3, x1 + t + 0.3, z1 + t + 0.3, neon, y=y - 0.5, w=0.35)


def add_screen(B, WF, x0, z0, x1, z1, y, kind="facade", fmt=None, frame=True, neon=None, light=True, layer=0):
    ob, rec = L.screen(WF, x0, z0, x1, z1, y, B.scr_name(), B.cs, B.rng, kind=kind, fmt=fmt, layer=layer)
    B.objs.append(ob)
    if frame:
        screen_frame(B, WF, x0, z0, x1, z1, y, t=0.5 + 0.02 * (x1 - x0), neon=neon)
    if light and (x1 - x0) * (z1 - z0) > 300:
        c = WF.w((x0 + x1) / 2, y - 6, (z0 + z1) / 2)
        L.light(c, (255, 120, 220) if "MAG" in (neon or "") else (120, 200, 255), 40, 1.2, kind="surface",
                direction=tuple(-WF.ay), name=rec["name"])
    return ob, rec


def recessed_screen(B, WF, x0, z0, x1, z1, depth=1.6, neon=None):
    """Screen set into the facade: reveals + glowing outline. Caller leaves the hole."""
    g = B.g
    w = WF.w
    g.face("STL", [w(x0, 0, z0), w(x0, depth, z0), w(x0, depth, z1), w(x0, 0, z1)])
    g.face("STL", [w(x1, depth, z0), w(x1, 0, z0), w(x1, 0, z1), w(x1, depth, z1)])
    g.face("STL", [w(x0, depth, z0), w(x1, depth, z0), w(x1, 0, z0), w(x0, 0, z0)][::-1])
    g.face("STL", [w(x0, depth, z1), w(x1, depth, z1), w(x1, 0, z1), w(x0, 0, z1)])
    ob, rec = L.screen(WF, x0, z0, x1, z1, depth, B.scr_name(), B.cs, B.rng, kind="giant")
    B.objs.append(ob)
    neon_rect(B, WF, x0 - 0.6, z0 - 0.6, x1 + 0.6, z1 + 0.6, neon or B.neon, y=-0.25, w=0.5)
    c = WF.w((x0 + x1) / 2, -10, (z0 + z1) / 2)
    L.light(c, (255, 140, 230), 60, 1.6, kind="surface", direction=tuple(-WF.ay), name=rec["name"])
    return ob, rec


def wall_with_hole(B, WF, s0, s1, z0, z1, hole, style, **kw):
    hx0, hz0, hx1, hz1 = hole
    if hz0 > z0:
        style(B, WF, s0, s1, z0, hz0, **kw)
    if hz1 < z1:
        style(B, WF, s0, s1, hz1, z1, **kw)
    if hx0 > s0:
        style(B, WF, s0, hx0, hz0, hz1, **kw)
    if hx1 < s1:
        style(B, WF, hx1, s1, hz0, hz1, **kw)


def cantilever_billboard(B, WF, x0, x1, z0, h, out=5.0, tilt=0.0, fmt=None):
    g = B.g
    y = -out
    ob, rec = add_screen(B, WF, x0, z0, x1, z0 + h, y, kind="cantilever", fmt=fmt, neon=B.neon if B.hero >= 1 else None)
    for x in (x0 + 1.5, x1 - 1.5):
        beam(g, WF.w(x, 0, z0 + 1), WF.w(x, y + 1.2, z0 + 1), 0.7, "STL")
        beam(g, WF.w(x, 0, z0 + h - 1), WF.w(x, y + 1.2, z0 + h - 1), 0.7, "STL")
        beam(g, WF.w(x, 0, z0 - 4), WF.w(x, y + 1.2, z0 + 1), 0.5, "STL")
    return ob


def blade_screen(B, WF, s, z0, h, out=6.0, t=0.8):
    """Double-sided vertical holo blade projecting from the facade."""
    g = B.g
    y0, y1 = -out - 0.6, -0.6
    for side in (-1, 1):
        x = s + side * t / 2
        # left face (side -1) looks along -ax, right face along +ax; local x runs along the blade
        F2 = Frame(WF.w(x, 0, 0), WF.ay * side, WF.ax * (-side))
        a0, a1 = (0.6, out + 0.6) if side < 0 else (-(out + 0.6), -0.6)
        ob, rec = L.screen(F2, a0, z0, a1, z0 + h, 0, B.scr_name("H"), B.cs, B.rng, kind="holo")
        B.objs.append(ob)
    box(g, WF, s - t / 2, y0, z0 - 0.6, s + t / 2, y1, z0, "STL")
    box(g, WF, s - t / 2, y0, z0 + h, s + t / 2, y1, z0 + h + 0.6, "STL")
    box(g, WF, s - t / 2 + 0.05, y0 - 0.3, z0, s + t / 2 - 0.05, y0, z0 + h, B.neon2, skip=("back",))
    for z in (z0 + 1, z0 + h - 1):
        box(g, WF, s - 0.25, y1, z - 0.3, s + 0.25, 0, z + 0.3, "STL")


def rooftop_billboard(B, F, x0, x1, y, z, h, fmt=None, legs=4.0):
    """Billboard standing on a roof, facing -y of F (towards the plaza)."""
    g = B.g
    zs = z + legs
    ob, rec = add_screen(B, F, x0, zs, x1, zs + h, y, kind="rooftop", fmt=fmt,
                         neon=B.neon if B.hero >= 1 else None, light=True)
    n = max(2, int((x1 - x0) / 14) + 1)
    for i in range(n):
        x = x0 + (x1 - x0) * i / (n - 1)
        x = min(max(x, x0 + 0.6), x1 - 0.6)
        box(g, F, x - 0.45, y + 1.3, z, x + 0.45, y + 2.2, zs + h, "STL")
        beam(g, F.w(x, y + 1.7, zs + h * 0.6), F.w(x, y + 1.7 + h * 0.5, z), 0.45, "STL")
    box(g, F, x0, y + 1.3, zs + h * 0.33 - 0.3, x1, y + 2.2, zs + h * 0.33 + 0.3, "STL")
    # catwalk with flood lights under the screen
    box(g, F, x0, y - 2.2, zs - 1.0, x1, y + 1.3, zs - 0.7, "STL")
    tube(g, F.w(x0, y - 2.1, zs + 0.5), F.w(x1, y - 2.1, zs + 0.5), 0.1, "STL", n=4)
    for i in range(int((x1 - x0) / 8) + 1):
        x = x0 + 2 + i * 8
        if x < x1 - 1:
            box(g, F, x - 0.5, y - 2.0, zs - 0.7, x + 0.5, y - 1.2, zs - 0.1, "NEON_WHT")
    B.reserved.append((min(x0, x1) - 2, y - 3, max(x0, x1) + 2, y + 6))
    return ob


# =========================================================================== storefront podium
def podium(B, WF, s0, s1, zp=16.0, second=False, shops=None, style_key="PNL"):
    """Shibuya-style ground floor: narrow recessed shops, signs, canopies, LED strips."""
    g = B.g
    r = B.rng
    o = _o(B, WF)
    z_glass = 10.2
    x = s0
    units = []
    while x < s1 - 4:
        w = r.uniform(7.5, 15.0)
        if s1 - (x + w) < 7:
            w = s1 - x
        units.append((x, min(s1, x + w)))
        x += w
    if not units:
        units = [(s0, s1)]
    shop_neons = [B.neon, B.neon2, r.choice(L.NEONS)]
    for ui, (a, b) in enumerate(units):
        pil = 0.9
        a2, b2 = a + pil, b - (pil if ui == len(units) - 1 else 0)
        # pilasters
        box(g, WF, a, -0.35, -1, a + pil, 0, zp, "CON", skip=("back", "bottom"), o=o)
        if ui == len(units) - 1:
            box(g, WF, b - pil, -0.35, -1, b, 0, zp, "CON", skip=("back", "bottom"), o=o)
        dep = r.uniform(1.6, 3.2)
        # recess
        w = WF.w
        g.face("PNL", [w(a2, 0, -1), w(a2, dep, -1), w(a2, dep, z_glass), w(a2, 0, z_glass)], o=o)
        g.face("PNL", [w(b2, dep, -1), w(b2, 0, -1), w(b2, 0, z_glass), w(b2, dep, z_glass)], o=o)
        g.face("PNL", [w(a2, dep, z_glass), w(b2, dep, z_glass), w(b2, 0, z_glass), w(a2, 0, z_glass)], o=o)
        quad(g, WF, a2, -1, b2, z_glass, dep, r.choice(["SHOP_LIT", "SHOP_LIT", "SHOP_LIT", "WIN_PNK", "WIN_COL",
                                                         "WIN_VIO", "WIN_WRM"]))
        # interior read-through: display counter, shelving silhouettes
        box(g, WF, a2 + 0.4, dep - 1.1, -1, b2 - 0.4, dep - 0.02, 2.6, "PNL", skip=("back", "bottom"))
        for zs in (5.0, 7.6):
            if r.random() < 0.8:
                box(g, WF, a2 + 0.6, dep - 0.5, zs, b2 - 0.6, dep - 0.02, zs + 0.25, "STL", skip=("back",))
        # noren curtain (sign-atlas cloth) over the door / paper lanterns
        dx = r.uniform(a2 + 1.0, max(a2 + 1.1, b2 - 5.0))
        if r.random() < 0.35:
            cell = sign_cell("SGV" if r.random() < 0.5 else "SGH", r, aspect=1.4)
            quad(g, WF, dx, 6.6, dx + 3.8, 9.6, dep - 0.7, "SGV" if cell in SIGN_CELLS["SGV"] else "SGH",
                 uv=_sign_uv(cell))
        if r.random() < 0.25:
            for lx in (a2 + 1.0, b2 - 1.0):
                cylinder(g, WF, lx, -1.2, 0.55, 7.4, 8.8, r.choice(["NEON_RED", "NEON_AMB"]), n=6, top="NEON_RED")
                tube(g, WF.w(lx, -1.2, 8.8), WF.w(lx, -1.2, z_glass - 0.6), 0.05, "STL", n=3)
        # A-frame sidewalk sign
        if r.random() < 0.3:
            ax_ = r.uniform(a2 + 0.5, b2 - 2.0)
            cell = sign_cell("SGV", r, aspect=0.5)
            box(g, WF, ax_, -5.2, -1, ax_ + 1.6, -4.4, 2.6, "STL", skip=("front", "bottom"))
            quad(g, WF, ax_, 0.0, ax_ + 1.6, 2.5, -5.2, "SGV", uv=_sign_uv(cell))
        # mullions + door frame
        n = max(2, int((b2 - a2) / 3.6))
        for k in range(1, n):
            xm = a2 + (b2 - a2) * k / n
            box(g, WF, xm - 0.12, dep - 0.35, -1, xm + 0.12, dep, z_glass, "STL", skip=("back", "bottom", "top"))
        box(g, WF, a2, dep - 0.35, 7.6, b2, dep, 8.0, "STL", skip=("back",))
        # fascia
        quad(g, WF, a2, z_glass, b2, zp, 0, style_key, o=o)
        sw = min(b2 - a2 - 1.2, 16)
        if r.random() < 0.82:
            flat_sign(B, WF, (a2 + b2) / 2 - sw / 2, z_glass + 1.2, sw, min(3.6, zp - z_glass - 1.6), kind="SGH")
        elif zp - z_glass > 4:
            add_screen(B, WF, (a2 + b2) / 2 - sw / 2, z_glass + 1.1, (a2 + b2) / 2 + sw / 2, z_glass + 1.1 + sw / 4,
                       -0.4, kind="storefront", fmt="X", frame=False, light=False)
        neon_h(B, WF, a2 + 0.3, b2 - 0.3, z_glass + 0.45, shop_neons[ui % 3], y=-0.6, w=0.28)
        # canopy with LED underside
        if r.random() < 0.6:
            box(g, WF, a2 - 0.2, -3.2, z_glass - 0.6, b2 + 0.2, 0, z_glass - 0.1, "STL", skip=("back",))
            neon_h(B, WF, a2, b2, z_glass - 0.72, "NEON_WHT" if r.random() < 0.25 else shop_neons[(ui + 1) % 3],
                   y=-2.9, w=0.22)
        # interior glow light (Roblox PointLight)
        if ui % 2 == 0:
            L.light(WF.w((a2 + b2) / 2, -2.0, 6.0), (255, 225, 190), 18, 0.8, name=f"{B.bid}_shop{ui}")
        # vending machines / AC by the door
        if r.random() < 0.28 and b2 - a2 > 9:
            vend(B, WF, b2 - 3.4, -1.4)
    # vertical blade sign at the podium corner
    if r.random() < 0.75:
        blade_sign(B, WF, s0 + 0.6 if r.random() < 0.5 else s1 - 0.6, zp + 1.5, r.uniform(10, 22))
    if second:
        # second-floor commercial band
        w_curtain(B, WF, s0, s1, zp, zp + 12, fins=False, slabs=False, p=0.6)
        box(g, WF, s0, -0.6, zp - 0.4, s1, 0, zp + 0.4, "STL", skip=("back",))
        x = s0 + 1
        while x < s1 - 6:
            ww = r.uniform(5, 9)
            if x + ww > s1 - 1:
                break
            flat_sign(B, WF, x, zp + 8.2, ww, 2.6, y=-0.6, kind="SGH", glow=False)
            x += ww + r.uniform(1.5, 4)


def vend(B, WF, s, y):
    meshes_b = L.PROTOS.get("VEND_BODY")
    if not meshes_b:
        return
    B.nprop += 1
    loc = WF.w(s, y, 0)
    rot = math.atan2(WF.ax.y, WF.ax.x)
    for nm in ("VEND_BODY", "VEND_FACE"):
        for ob in L.place(f"{B.bid}_V{B.nprop:02d}_{nm}", L.PROTOS[nm], loc, rot, B.cp):
            B.objs.append(ob)


# =========================================================================== roofs
def parapet(B, F, poly, z, h=2.4, t=0.7, key="CON"):
    n = len(poly)
    for i in range(n):
        WF, Ln = F.wall(poly[i], poly[(i + 1) % n])
        box(B.g, WF, 0, 0, z, Ln, t, z + h, key, skip=("bottom",))


def antenna(B, F, x, y, z, h, base=3.0, top=0.6, levels=None):
    g = B.g
    levels = levels or max(3, int(h / 6))
    legs = []
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        legs.append((math.cos(a), math.sin(a)))
    pts = lambda t, lg: F.w(x + lg[0] * (base + (top - base) * t), y + lg[1] * (base + (top - base) * t), z + h * t)
    for lg in legs:
        tube(g, pts(0, lg), pts(1, lg), 0.22, "STL", n=4)
    for j in range(levels):
        t0, t1 = j / levels, (j + 1) / levels
        for k in range(4):
            la, lb = legs[k], legs[(k + 1) % 4]
            beam(g, pts(t1, la), pts(t1, lb), 0.14, "STL")
            beam(g, pts(t0, la), pts(t1, lb), 0.1, "STL")
    tube(g, F.w(x, y, z + h), F.w(x, y, z + h + h * 0.35), 0.15, "STL", n=4)
    box(g, F, x - 0.5, y - 0.5, z + h * 1.35, x + 0.5, y + 0.5, z + h * 1.35 + 1.0, "NEON_RED")
    box(g, F, x - 0.45, y - 0.45, z + h * 0.6, x + 0.45, y + 0.45, z + h * 0.6 + 0.9, "NEON_RED")
    L.light(F.w(x, y, z + h * 1.35 + 0.5), (255, 30, 40), 20, 1.0, name=f"{B.bid}_beacon")
    B.reserved.append((x - base - 1, y - base - 1, x + base + 1, y + base + 1))


def mast(B, F, x, y, z, h):
    """Simple communication pole with dishes and a beacon."""
    g = B.g
    tube(g, F.w(x, y, z), F.w(x, y, z + h), 0.35, "STL", n=6)
    for k in range(2):
        zz = z + h * (0.45 + 0.25 * k)
        box(g, F, x - 0.3, y - 1.6, zz, x + 0.3, y + 1.6, zz + 1.6, "MEC")
    box(g, F, x - 0.4, y - 0.4, z + h, x + 0.4, y + 0.4, z + h + 0.8, "NEON_RED")
    B.reserved.append((x - 2, y - 2, x + 2, y + 2))


PROP_SIZES = {"HVAC_L": (10, 6), "HVAC_S": (4, 3), "COOL": (9, 9), "TANK": (7, 7), "VENT": (2, 2), "DISH": (4, 4),
              "STACK": (3, 3), "FANBOX": (8, 8), "GEN": (12, 5)}


def roof_kit(B, F, x0, y0, x1, y1, z, level=1, para=True, poly=None):
    if para:
        parapet(B, F, poly or [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z)
    r = B.rng
    counts = {0: (1, 3), 1: (3, 6), 2: (5, 9), 3: (7, 12)}[level]
    want = r.randint(*counts)
    pool = ["HVAC_L", "HVAC_S", "HVAC_S", "VENT", "VENT", "COOL", "TANK", "DISH", "STACK", "FANBOX", "GEN"]
    placed = list(B.reserved)
    tries = 0
    while want > 0 and tries < 60:
        tries += 1
        p = r.choice(pool)
        sx, sy = PROP_SIZES[p]
        rot = r.choice([0, 1])
        if rot:
            sx, sy = sy, sx
        if x1 - x0 < sx + 3 or y1 - y0 < sy + 3:
            continue
        px = r.uniform(x0 + 1.5 + sx / 2, x1 - 1.5 - sx / 2)
        py = r.uniform(y0 + 1.5 + sy / 2, y1 - 1.5 - sy / 2)
        rect = (px - sx / 2 - 0.5, py - sy / 2 - 0.5, px + sx / 2 + 0.5, py + sy / 2 + 0.5)
        if any(not (rect[2] < q[0] or rect[0] > q[2] or rect[3] < q[1] or rect[1] > q[3]) for q in placed):
            continue
        placed.append(rect)
        B.nprop += 1
        loc = F.w(px, py, z)
        rotz = math.atan2(F.ax.y, F.ax.x) + rot * math.pi / 2
        for ob in L.place(f"{B.bid}_P{B.nprop:02d}_{p}", L.PROTOS[p], loc, rotz, B.cp):
            B.objs.append(ob)
        want -= 1
    # duct runs between machinery
    if level >= 2 and x1 - x0 > 16:
        yy = r.uniform(y0 + 3, y1 - 3)
        box(B.g, F, x0 + 2, yy - 0.9, z, x1 - 2, yy + 0.9, z + 1.8, "MEC", skip=("bottom",))


def build_props(collection):
    """Prototype meshes for instanced rooftop machinery (single material each)."""
    W = Frame((0, 0, 0), (1, 0, 0), (0, 1, 0))

    def hvac_l(g):
        box(g, W, -5, -3, 0, 5, 3, 3.6, "MEC", skip=("bottom",))
        for x in (-2.5, 2.5):
            cylinder(g, W, x, 0, 1.8, 3.6, 4.4, "MEC", n=10, top="MEC")
        box(g, W, -5.3, -3.3, 0, 5.3, 3.3, 0.5, "MEC", skip=("bottom",))

    def hvac_s(g):
        box(g, W, -2, -1.5, 0, 2, 1.5, 2.6, "MEC", skip=("bottom",))
        cylinder(g, W, 0, 0, 1.1, 2.6, 3.0, "MEC", n=8, top="MEC")

    def cool(g):
        prism(g, W, L.circle_poly(0, 0, 4.4, 8), 0, 2.0, "MEC")
        prism(g, W, L.circle_poly(0, 0, 4.0, 8), 2.0, 6.5, "MEC", top="MEC")
        cylinder(g, W, 0, 0, 2.6, 6.5, 7.6, "MEC", n=10, top="MEC")

    def tank(g):
        for (x, y) in ((-2, -2), (2, -2), (2, 2), (-2, 2)):
            box(g, W, x - 0.25, y - 0.25, 0, x + 0.25, y + 0.25, 2.2, "MEC", skip=("bottom",))
        cylinder(g, W, 0, 0, 3.2, 2.2, 7.4, "MEC", n=12, bottom="MEC")
        prism(g, W, L.circle_poly(0, 0, 3.2, 12), 7.4, 7.4, "MEC")
        g.face("MEC", [W.w(*p, 7.4) for p in L.circle_poly(0, 0, 3.3, 12)])

    def vent(g):
        cylinder(g, W, 0, 0, 0.6, 0, 2.2, "MEC", n=8)
        cylinder(g, W, 0, 0, 1.1, 2.2, 2.7, "MEC", n=8, top="MEC", bottom="MEC")

    def dish(g):
        tube(g, (0, 0, 0), (0, 0, 2.5), 0.25, "MEC", n=6)
        ring = [Vector((0.3 + 1.8 * math.cos(a) * 0.5, 1.8 * math.sin(a), 3.2 + 1.8 * math.cos(a))) for a in
                [2 * math.pi * i / 10 for i in range(10)]]
        c = Vector((1.0, 0, 3.2))
        for i in range(10):
            g.face("MEC", [c, ring[(i + 1) % 10], ring[i]])
            g.face("MEC", [c, ring[i], ring[(i + 1) % 10]])

    def stack(g):
        cylinder(g, W, 0, 0, 1.3, 0, 16, "MEC", n=10)
        for zz in (5, 10, 15.2):
            cylinder(g, W, 0, 0, 1.55, zz, zz + 0.6, "MEC", n=10, top="MEC", bottom="MEC")

    def fanbox(g):
        box(g, W, -4, -4, 0, 4, 4, 3, "MEC", skip=("bottom",))
        cylinder(g, W, 0, 0, 3.3, 3, 4.4, "MEC", n=14, top="MEC")

    def gen(g):
        box(g, W, -6, -2.5, 0, 6, 2.5, 5, "MEC", skip=("bottom",))
        for x in range(-5, 6, 2):
            box(g, W, x - 0.2, -2.8, 0.3, x + 0.2, 2.8, 4.7, "MEC", skip=("bottom",))

    def vend_body(g):
        box(g, W, -1.5, 0, 0, 1.5, 2.4, 6.2, "PNL", skip=("bottom",))

    def vend_face(g):
        quad(g, W, -1.2, 1.4, 1.2, 5.6, -0.02, "SHOP_LIT")

    for nm, fn in (("HVAC_L", hvac_l), ("HVAC_S", hvac_s), ("COOL", cool), ("TANK", tank), ("VENT", vent),
                   ("DISH", dish), ("STACK", stack), ("FANBOX", fanbox), ("GEN", gen), ("VEND_BODY", vend_body),
                   ("VEND_FACE", vend_face)):
        L.proto(nm, fn, collection)


# =========================================================================== crowns
def crown(B, F, x0, y0, x1, y1, z, style=None):
    """Distinctive tower tops. Returns the new top height (for antennas)."""
    r = B.rng
    g = B.g
    w, d = x1 - x0, y1 - y0
    style = style or r.choice(["parapet", "stepped", "slant", "frame", "mech", "helipad", "stepped", "slant"])
    if w < 10 or d < 10:
        style = "parapet"
    if style == "parapet":
        parapet(B, F, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z)
        return z
    if style == "stepped":
        top = z
        m = 0.0
        for k in range(r.randint(1, 3)):
            m += min(w, d) * r.uniform(0.1, 0.18)
            h = r.uniform(5, 10)
            if x1 - x0 - 2 * m < 6 or y1 - y0 - 2 * m < 6:
                break
            box(g, F, x0 + m, y0 + m, top, x1 - m, y1 - m, top + h, "PNL" if k % 2 else "TEC", skip=("bottom",),
                keys={"top": "ROF"})
            if B.hero >= 3 and k == 0:
                WF, Ln = F.wall((x0 + m, y0 + m), (x1 - m, y0 + m))
                neon_h(B, WF, 0, Ln, top + h - 0.8, B.neon2, y=-0.2, w=0.35)
            top += h
        return top
    if style == "slant":
        # sloped roof plane rising towards the back (or front), a strong silhouette
        h = min(w, d) * r.uniform(0.35, 0.7)
        back_high = r.random() < 0.7
        za, zb_ = (z, z + h) if back_high else (z + h, z)
        p = [F.w(x0, y0, za), F.w(x1, y0, za), F.w(x1, y1, zb_), F.w(x0, y1, zb_)]
        g.face("PNL", p)
        g.face("PNL", [F.w(x0, y1, z), F.w(x0, y0, z), F.w(x0, y0, za), F.w(x0, y1, zb_)])
        g.face("PNL", [F.w(x1, y0, z), F.w(x1, y1, z), F.w(x1, y1, zb_), F.w(x1, y0, za)])
        if back_high:
            g.face("PNL", [F.w(x1, y1, z), F.w(x0, y1, z), F.w(x0, y1, zb_), F.w(x1, y1, zb_)])
        else:
            g.face("PNL", [F.w(x0, y0, z), F.w(x1, y0, z), F.w(x1, y0, za), F.w(x0, y0, za)])
        if B.hero >= 3:
            # neon on the sloped edges
            for xx in (x0 + 0.3, x1 - 0.3):
                tube(g, F.w(xx, y0, za + 0.3), F.w(xx, y1, zb_ + 0.3), 0.25, B.neon, n=4)
        return z + h
    if style == "frame":
        # open steel crown frame holding a screen facing the plaza
        h = r.uniform(14, 24)
        for (xx, yy) in ((x0 + 0.6, y0 + 0.6), (x1 - 0.6, y0 + 0.6), (x1 - 0.6, y1 - 0.6), (x0 + 0.6, y1 - 0.6)):
            box(g, F, xx - 0.6, yy - 0.6, z, xx + 0.6, yy + 0.6, z + h, "STL", skip=("bottom",))
        for zz in (z + h * 0.5, z + h):
            box(g, F, x0, y0, zz - 0.8, x1, y0 + 1.2, zz, "STL")
            box(g, F, x0, y1 - 1.2, zz - 0.8, x1, y1, zz, "STL")
            box(g, F, x0, y0, zz - 0.8, x0 + 1.2, y1, zz, "STL")
            box(g, F, x1 - 1.2, y0, zz - 0.8, x1, y1, zz, "STL")
        sw = w - 4
        sh = min(h - 3, sw / 2)
        WF = Frame(F.w(x0 + 2, y0 + 1.5, 0), F.ax, F.ay)
        add_screen(B, WF, 0, z + 1.5, sw, z + 1.5 + sh, 0, kind="crown", frame=False, light=False)
        if B.hero >= 1:
            neon_rect(B, WF, -0.3, z + 1.2, sw + 0.3, z + 1.8 + sh, B.neon, y=-0.3, w=0.3)
        return z + h
    if style == "mech":
        m = min(w, d) * 0.15
        h = r.uniform(6, 11)
        box(g, F, x0 + m, y0 + m, z, x1 - m, y1 - m, z + h, "MEC", skip=("bottom",), keys={"top": "ROF"})
        for k in range(r.randint(1, 3)):
            px = r.uniform(x0 + m + 2, x1 - m - 2)
            py = r.uniform(y0 + m + 2, y1 - m - 2)
            cylinder(g, F, px, py, r.uniform(0.9, 1.6), z + h, z + h + r.uniform(6, 16), "MEC", n=8, top="MEC")
        parapet(B, F, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z)
        return z + h
    # helipad: octagonal pad cantilevered over the roof on a core, neon edge ring
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rr = min(w, d) * 0.62
    box(g, F, cx - 3, cy - 3, z, cx + 3, cy + 3, z + 6, "CON", skip=("bottom",))
    pad = L.circle_poly(cx, cy, rr, 8, a0=math.pi / 8)
    prism(g, F, pad, z + 6, z + 7.2, "STL", top="ROF", bottom="STL")
    if B.hero >= 1:
        n = len(pad)
        for i in range(n):
            WF, Ln = F.wall(pad[i], pad[(i + 1) % n])
            box(g, WF, 0, -0.3, z + 6.6, Ln, 0, z + 7.0, B.neon2 if B.hero >= 2 else "NEON_WHT", skip=("back",))
    return z + 7.2


def sky_screen(B, F, xa, xb, y_front, z0, width, fmt="T", out=6.0):
    """Skyscraper-scale screen cantilevered from a landmark's upper facade, wider than the tower."""
    g = B.g
    h = width / L.FMT_ASPECT[fmt]
    cx = (xa + xb) / 2
    x0, x1 = cx - width / 2, cx + width / 2
    WF = Frame(F.w(0, y_front - out, 0), F.ax, F.ay)
    ob, rec = add_screen(B, WF, x0, z0, x1, z0 + h, 0, kind="sky", fmt=fmt, neon=B.neon, light=True)
    # trusses back to the tower core
    for zz in (z0 + h * 0.15, z0 + h * 0.5, z0 + h * 0.85):
        box(g, WF, xa + 1, 1.2, zz - 0.8, xb - 1, out, zz + 0.8, "STL")
        for x in (x0 + 2, x1 - 2):
            beam(g, WF.w(x, 1.2, zz), WF.w(min(max(x, xa + 2), xb - 2), out, zz + (6 if x < cx else -6)), 0.6, "STL")
    # maintenance gantry on top
    box(g, WF, x0 - 1, -1.5, z0 + h + 0.6, x1 + 1, 2.5, z0 + h + 1.0, "STL")
    for i in range(int(width / 10) + 1):
        x = x0 + i * 10
        box(g, WF, x - 0.5, -1.4, z0 + h + 1.0, x + 0.5, -0.6, z0 + h + 1.8, "NEON_WHT")
    return z0 + h


# =========================================================================== masses
def mass(B, F, poly, z0, z1, front=None, side=None, back=None, roof="ROF", front_kw=None, side_kw=None,
         back_kw=None, front_dir=(0, -1), holes=None, skip_edges=(), detail=None):
    """Extrude a footprint and dress each wall with a facade style depending on its orientation.
    detail: cap for the built-window detail (2 full, 1 no sills, 0 distant)."""
    if detail is not None:
        prev = getattr(B, "detail_cap", 2)
        B.detail_cap = detail
        try:
            return mass(B, F, poly, z0, z1, front, side, back, roof, front_kw, side_kw, back_kw, front_dir, holes,
                        skip_edges)
        finally:
            B.detail_cap = prev
    n = len(poly)
    front = front or w_curtain
    side = side or w_plain
    back = back or w_plain
    fd = Vector((front_dir[0], front_dir[1]))
    for i in range(n):
        if i in skip_edges:
            continue
        a, b = poly[i], poly[(i + 1) % n]
        WF, Ln = F.wall(a, b)
        if Ln < 0.05:
            continue
        nx, ny = (b[1] - a[1]) / Ln, -(b[0] - a[0]) / Ln  # outward normal (local)
        dot = nx * fd.x + ny * fd.y
        if dot > 0.35:
            st, kw = front, (front_kw or {})
        elif dot < -0.7:
            st, kw = back, (back_kw or {})
        else:
            st, kw = side, (side_kw or {})
        if holes and i in holes:
            wall_with_hole(B, WF, 0, Ln, z0, z1, holes[i], st, **kw)
        else:
            st(B, WF, 0, Ln, z0, z1, **kw)
    if roof:
        B.g.face(roof, [F.w(p[0], p[1], z1) for p in poly])


def side_plain(B, WF, s0, s1, z0, z1, **kw):
    """Party / side walls: concrete or panels with sparse windows, pipes and AC units."""
    key = kw.get("key", "CON")
    w_plain(B, WF, s0, s1, z0, z1, key=key, windows=kw.get("windows", 0.12))
    if s1 - s0 > 10 and z1 - z0 > 30 and B.rng.random() < 0.35:
        pipes(B, WF, s0 + B.rng.uniform(1.5, (s1 - s0) * 0.4), z0 + 2, z1 - 1, n=B.rng.randint(2, 4))
    if s1 - s0 > 6 and z1 - z0 > 24 and B.rng.random() < 0.4:
        for _ in range(B.rng.randint(1, 4)):
            ac_unit(B, WF, B.rng.uniform(s0 + 0.5, s1 - 3), B.rng.uniform(z0 + 18, z1 - 4))


# =========================================================================== FG archetypes
def fg_frame_style(B, kind):
    r = B.rng
    if kind == "Zakkyo":
        return r.choice([w_punched, w_punched, w_ribbon, w_tech])
    if kind == "Mansion":
        return w_balcony
    if kind == "Louver":
        return w_louver
    if kind == "Pencil":
        return r.choice([w_curtain, w_tech, w_ribbon])
    if kind == "Modern":
        return r.choice([w_curtain, w_exo, w_ribbon, w_curtain])
    return r.choice([w_curtain, w_ribbon, w_punched])


def floors_to(z_top_floors):
    return 16.0 + z_top_floors * FLOOR


def fg_lot(B, F, Wd, D, kind, landmark=False):
    """Foreground building in a lot of width Wd (along the plaza) and depth D. Front at y=0."""
    r = B.rng
    xa, xb = 0.0, Wd
    alley_side = None
    if Wd >= 24 and not landmark and r.random() < 0.3:
        aw = r.uniform(3.5, 5.5)
        if r.random() < 0.5:
            xa = aw; alley_side = "L"
        else:
            xb = Wd - aw; alley_side = "R"
    w = xb - xa
    B.alley = alley_side
    B.lot = (0.0, Wd)
    if landmark:
        return fg_landmark(B, F, xa, xb, D)
    if kind == "Arcade":
        return fg_arcade(B, F, xa, xb, D)
    if kind == "Low":
        return fg_low(B, F, xa, xb, D)
    if kind == "Pencil" or w < 17:
        return fg_pencil(B, F, xa, xb, D)
    if kind == "Modern" and r.random() < 0.6:
        return fg_modern(B, F, xa, xb, D)
    return fg_stack(B, F, xa, xb, D, kind)


def _podium_all(B, F, xa, xb, Df, zp, second=False):
    WF, Ln = F.wall((xa, 0), (xb, 0))
    podium(B, WF, 0, Ln, zp=zp, second=second)
    return WF


def fg_stack(B, F, xa, xb, D, kind):
    """Zakkyo / mansion / louver blocks: podium + front block + taller rear tower."""
    r = B.rng
    w = xb - xa
    second = r.random() < 0.35
    zp = 16.0
    B.zb = zp
    Df = max(18.0, D * r.uniform(0.42, 0.62))
    nf = r.randint(5, 11)
    Hf = zp + (12 if second else 0) + nf * FLOOR
    style = fg_frame_style(B, kind)
    # podium shell (side walls of the ground floors)
    WFp = _podium_all(B, F, xa, xb, Df, zp, second)
    z_body = zp + (12 if second else 0)
    for (a, b) in (((xb, 0), (xb, Df)), ((xa, Df), (xa, 0))):
        WF, Ln = F.wall(a, b)
        side_plain(B, WF, 0, Ln, -1, z_body)
    # front block (optionally cantilevered forward above the podium)
    cant = r.choice([0, 0, 0, 2.5, 4.0]) if kind != "Mansion" else 0
    ch = r.uniform(0, 3) if w > 20 else 0
    poly = L.chamfer_rect(xa, -cant, xb, Df, ch, corners=(1, 1, 0, 0)) if ch > 0.5 else [(xa, -cant), (xb, -cant), (xb, Df), (xa, Df)]
    if cant > 0:
        box(B.g, F, xa, -cant, z_body - 1.2, xb, 0, z_body, "STL")  # soffit
        WFc, Lc = F.wall((xa, -cant), (xb, -cant))
        neon_h(B, WFc, 0.5, Lc - 0.5, z_body - 1.4, B.neon, y=0.6, w=0.3)
    holes = None
    big = None
    if B.hero >= 2 and w >= 22 and nf >= 6:
        sw = w - 8
        sh = min(sw * 2, (Hf - z_body) - 16) if r.random() < 0.5 else sw / 2
        if sh > 12:
            hz0 = z_body + 6
            WF0, L0 = F.wall(poly[0], poly[1]) if ch <= 0.5 else F.wall(poly[1], poly[2])
            big = (WF0, (L0 - sw) / 2, hz0, (L0 + sw) / 2, hz0 + sh)
            holes = {0 if ch <= 0.5 else 1: (big[1], big[2], big[3], big[4])}
    mass(B, F, poly, z_body, Hf, front=style, side=side_plain, back=side_plain, holes=holes)
    if big:
        recessed_screen(B, big[0], big[1], big[2], big[3], big[4])
    if getattr(B, "alley", None):
        a_, b_ = ((xa, Df), (xa, -cant)) if B.alley == "L" else ((xb, -cant), (xb, Df))
        WFa, La = F.wall(a_, b_)
        alley_dressing(B, WFa, La, -1, Hf)
    if not big and style in (w_punched, w_ribbon, w_tech) and r.random() < 0.45:
        WFb, Lb = F.wall(poly[0], poly[1]) if ch <= 0.5 else F.wall(poly[1], poly[2])
        bay_boxes(B, WFb, 0, Lb, z_body, Hf)
    # stacked signage / screens on the front
    WFf, Lf = F.wall(poly[0], poly[1]) if ch <= 0.5 else F.wall(poly[1], poly[2])
    if kind in ("Zakkyo", "Pencil") or r.random() < 0.4:
        side_x = 0.6 if r.random() < 0.5 else Lf - 0.6
        nb = r.randint(1, 3)
        z = z_body + 2
        for _ in range(nb):
            h = r.uniform(14, 30)
            if z + h > Hf - 4:
                break
            blade_sign(B, WFf, side_x, z, h, out=r.uniform(3.5, 5.0))
            z += h + 2
        # floor directory signs (not over a facade screen)
        if Lf > 12 and not big:
            sx = 1.2 if side_x > Lf / 2 else Lf - 7.2
            k = 0
            while z_body + k * FLOOR + 10 < Hf - 2:
                if r.random() < 0.7:
                    flat_sign(B, WFf, sx, z_body + k * FLOOR + 8.4, 6.0, 2.4, kind="SGH", glow=k % 2 == 0)
                k += 1
    # rear tower
    rx0 = xa + r.uniform(0, w * 0.25)
    rx1 = xb - r.uniform(0, w * 0.25)
    if rx1 - rx0 < 10:
        rx0, rx1 = xa, xb
    Hr = Hf + r.choice([0, 24, 36, 48, 60, 84, 108])
    Hr = max(Hr, Hf + 12)
    rstyle = r.choice([w_curtain, w_ribbon, w_louver, w_curtain, w_tech])
    mass(B, F, [(rx0, Df), (rx1, Df), (rx1, D), (rx0, D)], -1, Hr, front=rstyle, side=side_plain, back=side_plain, detail=1)
    if r.random() < 0.4 and Hr - Hf > 30:
        WFr, Lr = F.wall((rx0, Df), (rx1, Df))
        catwalk(B, WFr, 0, Lr, Hf + r.choice([2, 3]) * FLOOR + 1)
    # roofs
    if r.random() < 0.3 and not big:
        crown(B, F, xa, -cant, xb, Df, Hf, style=r.choice(["frame", "stepped", "mech"]))
    roof_kit(B, F, xa, -cant, xb, Df, Hf, level=min(3, B.hero + 1),
             poly=poly)
    if r.random() < 0.35 and Lf > 16 and not big:
        bw = min(w + 8, 56)
        cxm = (xa + xb) / 2
        rooftop_billboard(B, F, cxm - bw / 2, cxm + bw / 2, 3.0, Hf, bw / 2, legs=r.uniform(3, 9))
    ztop = crown(B, F, rx0, Df, rx1, D, Hr)
    rk = r.random()
    if rk < 0.25:
        antenna(B, F, (rx0 + rx1) / 2, (Df + D) / 2, ztop, r.uniform(18, 40), base=r.uniform(2, 3.2))
    elif rk < 0.55:
        mast(B, F, rx0 + 3, D - 3, ztop, r.uniform(10, 22))
    roof_kit(B, F, rx0, Df, rx1, D, Hr, level=min(3, B.hero + 1), para=False)
    return Hf, Hr


def fg_pencil(B, F, xa, xb, D):
    """Narrow tall tower with vertical holo strip, chamfered crown and spike."""
    r = B.rng
    w = xb - xa
    zp = 16.0
    B.zb = zp
    Df = max(16.0, D * r.uniform(0.35, 0.55))
    H = zp + r.randint(9, 16) * FLOOR
    _podium_all(B, F, xa, xb, Df, zp)
    for (a, b) in (((xb, 0), (xb, Df)), ((xa, Df), (xa, 0))):
        WF, Ln = F.wall(a, b)
        side_plain(B, WF, 0, Ln, -1, zp)
    style = r.choice([w_curtain, w_tech, w_ribbon])
    ch = min(3.0, w * 0.18)
    poly = L.chamfer_rect(xa, 0, xb, Df, ch, corners=(1, 1, 0, 0))
    strip = w >= 10 and r.random() < 0.75
    holes = None
    WF1, L1 = F.wall(poly[1], poly[2])
    if strip:
        sw = min(8.0, L1 - 3)
        sh = sw * 4
        hz0 = zp + r.uniform(8, max(9, H - zp - sh - 10))
        if hz0 + sh < H - 6:
            holes = {1: ((L1 - sw) / 2, hz0, (L1 + sw) / 2, hz0 + sh)}
    mass(B, F, poly, zp, H, front=style, side=side_plain, back=side_plain, holes=holes)
    if holes:
        hx0, hz0, hx1, hz1 = holes[1]
        recessed_screen(B, WF1, hx0, hz0, hx1, hz1, depth=1.0)
    # crown: stepped top + spike
    cz = H
    box(B.g, F, xa + 1, 1, cz, xb - 1, Df - 1, cz + 6, "PNL", skip=("bottom",))
    if B.hero >= 1:
        WFc, Lc = F.wall((xa + 1, 1), (xb - 1, 1))
        neon_h(B, WFc, 0, Lc, cz + 5.4, B.neon2, y=-0.2)
    tube(B.g, F.w((xa + xb) / 2, Df / 2, cz + 6), F.w((xa + xb) / 2, Df / 2, cz + 6 + r.uniform(14, 30)), 0.5, "STL", n=6)
    # rear block
    Hr = H - r.choice([12, 24, 36, -24])
    mass(B, F, [(xa, Df), (xb, Df), (xb, D), (xa, D)], -1, Hr, front=r.choice([w_ribbon, w_curtain]), side=side_plain,
         back=side_plain, detail=1)
    roof_kit(B, F, xa, Df, xb, D, Hr, level=1)
    return H, Hr


def fg_modern(B, F, xa, xb, D):
    """Curved-corner glass tower, or stepped asymmetric megastructure."""
    r = B.rng
    w = xb - xa
    zp = 16.0 if r.random() < 0.5 else 28.0
    B.zb = 16.0
    Df = max(22.0, D * r.uniform(0.5, 0.7))
    variant = r.choice(["curved", "stepped", "curved"]) if w >= 24 else "stepped"
    _podium_all(B, F, xa, xb, Df, 16.0, second=zp > 16)
    for (a, b) in (((xb, 0), (xb, Df)), ((xa, Df), (xa, 0))):
        WF, Ln = F.wall(a, b)
        side_plain(B, WF, 0, Ln, -1, zp)
    g = B.g
    if variant == "curved":
        H = zp + r.randint(8, 15) * FLOOR
        rad = min(w * 0.35, Df * 0.5, 14)
        corners = r.choice([(1, 1, 0, 0), (1, 0, 0, 0), (0, 1, 0, 0)])
        poly = L.rounded_rect(xa, 0, xb, Df, rad, n=6, corners=corners)
        style = r.choice([w_curtain, w_exo, w_curtain])
        mass(B, F, poly, zp, H, front=style, side=side_plain, back=side_plain, front_kw={})
        # curved wrap screen on the rounded corner
        if B.hero >= 1 and r.random() < 0.7:
            ci = 0 if corners[0] else 1
            cx, cy = (xa + rad, rad) if ci == 0 else (xb - rad, rad)
            a0, a1 = (math.pi, 1.5 * math.pi) if ci == 0 else (1.5 * math.pi, 2 * math.pi)
            arc = rad * (a1 - a0) + 0.0
            zc = zp + r.randint(1, 3) * FLOOR
            hh = min(26.0, (H - zc - 8))
            if hh > 8:
                ob, rec = L.curved_screen(F, cx, cy, rad + 1.2, a0 - 0.15, a1 + 0.15, zc, zc + hh, B.scr_name("C"), B.cs, r,
                                          segs=8, fmt="T" if hh > arc * 1.3 else "P")
                B.objs.append(ob)
                for zz in (zc - 0.8, zc + hh + 0.2):
                    for k in range(8):
                        t0 = a0 - 0.15 + (a1 - a0 + 0.3) * k / 8
                        t1 = a0 - 0.15 + (a1 - a0 + 0.3) * (k + 1) / 8
                        p0 = (cx + (rad + 1.5) * math.cos(t0), cy + (rad + 1.5) * math.sin(t0))
                        p1 = (cx + (rad + 1.5) * math.cos(t1), cy + (rad + 1.5) * math.sin(t1))
                        WF, Ln = F.wall(p0, p1)
                        box(g, WF, 0, -0.5, zz, Ln, 1.5, zz + 0.6, B.neon2 if B.hero >= 2 else "STL")
        roof_kit(B, F, xa, 0, xb, Df, H, level=min(3, B.hero + 1), poly=poly)
        top = H
    else:
        # stepped: 3 tiers stepping back and sideways
        tiers = r.randint(2, 3)
        z = zp
        x0, x1, y0 = xa, xb, 0.0
        top = z
        for t in range(tiers):
            nfl = r.randint(3, 6)
            z1 = z + nfl * FLOOR
            poly = [(x0, y0), (x1, y0), (x1, Df), (x0, Df)]
            st = [w_curtain, w_exo, w_tech, w_ribbon][(t + r.randint(0, 3)) % 4]
            mass(B, F, poly, z, z1, front=st, side=side_plain, back=side_plain)
            WF, Ln = F.wall(poly[0], poly[1])
            # terrace roof of this tier (part in front of next tier)
            nx0 = x0 + r.uniform(0, (x1 - x0) * 0.3)
            nx1 = x1 - r.uniform(0, (x1 - x0) * 0.3)
            if nx1 - nx0 < 12:
                nx0, nx1 = x0, x1
            ny0 = y0 + r.uniform(4, 9)
            if ny0 > Df - 10:
                ny0 = y0
            roof_kit(B, F, x0, y0, x1, ny0 if ny0 > y0 else Df, z1, level=1, para=True,
                     poly=[(x0, y0), (x1, y0), (x1, Df), (x0, Df)])
            if t == tiers - 1 and B.hero >= 1 and x1 - x0 > 16 and r.random() < 0.6:
                rooftop_billboard(B, F, x0 + 1.5, x1 - 1.5, y0 + 3, z1, min(24, (x1 - x0 - 3) / 2))
            x0, x1, y0, z = nx0, nx1, ny0, z1
            top = z1
        H = top
    # rear mass
    Hr = top + r.choice([12, 24, 48, 72])
    rx0 = xa + r.uniform(0, w * 0.3)
    mass(B, F, [(rx0, Df), (xb, Df), (xb, D), (rx0, D)], -1, Hr, front=r.choice([w_curtain, w_louver]),
         side=side_plain, back=side_plain, detail=1)
    ztop = crown(B, F, rx0, Df, xb, D, Hr)
    if r.random() < 0.4:
        antenna(B, F, (rx0 + xb) / 2, (Df + D) / 2, ztop, r.uniform(20, 36))
    roof_kit(B, F, rx0, Df, xb, D, Hr, level=1, para=False)
    return top, Hr


def fg_arcade(B, F, xa, xb, D):
    """Game center / arcade: low-mid block whose front is a wall of stacked screens."""
    r = B.rng
    B.hero = max(B.hero, 2)
    w = xb - xa
    zp = 16.0
    B.zb = zp
    Df = max(20.0, D * r.uniform(0.5, 0.7))
    H = zp + r.randint(4, 7) * FLOOR
    _podium_all(B, F, xa, xb, Df, zp)
    for (a, b) in (((xb, 0), (xb, Df)), ((xa, Df), (xa, 0))):
        WF, Ln = F.wall(a, b)
        side_plain(B, WF, 0, Ln, -1, zp)
    poly = [(xa, 0), (xb, 0), (xb, Df), (xa, Df)]
    hole = (1.5, zp + 2, w - 1.5, H - 3)
    mass(B, F, poly, zp, H, front=w_tech, side=side_plain, back=side_plain, holes={0: hole})
    WF, Ln = F.wall(poly[0], poly[1])
    # recess + screen grid
    g = B.g
    wq = WF.w
    dep = 2.5
    x0, z0, x1, z1 = hole
    g.face("PNL", [wq(x0, 0, z0), wq(x0, dep, z0), wq(x0, dep, z1), wq(x0, 0, z1)])
    g.face("PNL", [wq(x1, dep, z0), wq(x1, 0, z0), wq(x1, 0, z1), wq(x1, dep, z1)])
    g.face("PNL", [wq(x0, 0, z1), wq(x1, 0, z1), wq(x1, dep, z1), wq(x0, dep, z1)][::-1])
    g.face("PNL", [wq(x0, dep, z0), wq(x1, dep, z0), wq(x1, 0, z0), wq(x0, 0, z0)][::-1])
    quad(g, WF, x0, z0, x1, z1, dep, "PNL")
    variant = r.choice(["grid", "hero", "mosaic"])
    if variant == "grid":
        cols = max(1, int((x1 - x0) / 16))
        cw = (x1 - x0) / cols
        rows = max(1, int((z1 - z0) / (cw / 2 + 1.6)))
        rh = (z1 - z0) / rows
        for i in range(cols):
            for j in range(rows):
                sx0, sz0 = x0 + i * cw + 0.8, z0 + j * rh + 0.8
                sx1, sz1 = sx0 + cw - 1.6, sz0 + rh - 1.6
                add_screen(B, WF, sx0, sz0, sx1, sz1, dep - 0.3, kind="arcade", frame=False, light=(i + j) % 2 == 0)
                neon_rect(B, WF, sx0 - 0.2, sz0 - 0.2, sx1 + 0.2, sz1 + 0.2, B.neon if (i + j) % 2 else B.neon2,
                          y=dep - 0.6, w=0.3)
    elif variant == "hero":
        # one big screen flanked by two vertical holo strips
        sw_ = (x1 - x0) * 0.62
        cx = (x0 + x1) / 2
        hh = min(z1 - z0 - 2, sw_ / 2)
        add_screen(B, WF, cx - sw_ / 2, z1 - 1 - hh, cx + sw_ / 2, z1 - 1, dep - 0.3, kind="arcade", fmt="W",
                   frame=False)
        neon_rect(B, WF, cx - sw_ / 2 - 0.3, z1 - 1.3 - hh, cx + sw_ / 2 + 0.3, z1 - 0.7, B.neon, y=dep - 0.6, w=0.4)
        stw = min((x1 - x0 - sw_) / 2 - 2, 7)
        for sx in (x0 + 1, x1 - 1 - stw):
            add_screen(B, WF, sx, z0 + 1, sx + stw, z0 + 1 + stw * 4 if z0 + 1 + stw * 4 < z1 - 1 else z1 - 1,
                       dep - 0.3, kind="holo", fmt="S", frame=False, light=False)
        if z1 - 1 - hh - (z0 + 1) > 8:
            add_screen(B, WF, cx - sw_ / 2, z0 + 1, cx + sw_ / 2, min(z1 - 2 - hh, z0 + 1 + sw_ / 4), dep - 0.3,
                       kind="ticker", fmt="X", frame=False, light=False)
    else:
        # staggered mosaic of mixed formats
        z = z0 + 0.8
        row = 0
        while z < z1 - 6:
            x = x0 + 0.8 + (3.0 if row % 2 else 0.0)
            h = r.choice([7.0, 9.0, 11.0])
            if z + h > z1 - 0.8:
                h = z1 - 0.8 - z
            while x < x1 - 6:
                fmt = r.choice(["W", "W", "X", "Q", "T"])
                wdt = h * L.FMT_ASPECT[fmt]
                if x + wdt > x1 - 0.8:
                    break
                add_screen(B, WF, x, z, x + wdt, z + h, dep - 0.3, kind="arcade", fmt=fmt, frame=False, light=False)
                neon_rect(B, WF, x - 0.2, z - 0.2, x + wdt + 0.2, z + h + 0.2, r.choice([B.neon, B.neon2]),
                          y=dep - 0.6, w=0.25)
                x += wdt + 1.4
            z += h + 1.4
            row += 1
    neon_rect(B, WF, x0 - 0.6, z0 - 0.6, x1 + 0.6, z1 + 0.6, B.neon, y=-0.3, w=0.6)
    # rooftop sign "GAME CENTER"
    roof_kit(B, F, xa, 0, xb, Df, H, level=1)
    sw = min(w - 4, 30)
    flat_sign(B, Frame(F.w(xa + (w - sw) / 2, 2, H + 2.4), F.ax, F.ay), 0, 0, sw, sw / 6, y=-0.6, kind="SGH")
    box(g, F, xa + (w - sw) / 2 + 2, 2.2, H, xa + (w + sw) / 2 - 2, 3.0, H + 2.4, "STL")
    Hr = H + r.choice([24, 36, 60])
    mass(B, F, [(xa, Df), (xb, Df), (xb, D), (xa, D)], -1, Hr, front=w_ribbon, side=side_plain, back=side_plain, detail=1)
    roof_kit(B, F, xa, Df, xb, D, Hr, level=1)
    return H, Hr


def fg_low(B, F, xa, xb, D):
    """Low 2-4 storey building carrying a giant rooftop billboard structure."""
    r = B.rng
    w = xb - xa
    zp = 16.0
    B.zb = zp
    Df = max(20.0, D * r.uniform(0.55, 0.8))
    H = zp + r.randint(1, 3) * FLOOR
    _podium_all(B, F, xa, xb, Df, zp, second=True)
    for (a, b) in (((xb, 0), (xb, Df)), ((xa, Df), (xa, 0))):
        WF, Ln = F.wall(a, b)
        side_plain(B, WF, 0, Ln, -1, H)
    z_body = zp + 12
    if H > z_body:
        mass(B, F, [(xa, 0), (xb, 0), (xb, Df), (xa, Df)], z_body, H, front=w_tech, side=side_plain, back=side_plain)
    else:
        B.g.face("ROF", [F.w(xa, 0, H), F.w(xb, 0, H), F.w(xb, Df, H), F.w(xa, Df, H)])
        H = z_body
        B.g.face("ROF", [F.w(xa, 0, H), F.w(xb, 0, H), F.w(xb, Df, H), F.w(xa, Df, H)])
    bw = w - 2
    bh = min(bw / 2, 36)
    rooftop_billboard(B, F, xa + 1, xb - 1, 4.0, H, bh, fmt="W", legs=r.uniform(4, 10))
    roof_kit(B, F, xa, 0, xb, Df, H, level=1)
    Hr = H + r.choice([24, 48, 72, 96])
    mass(B, F, [(xa, Df), (xb, Df), (xb, D), (xa, D)], -1, Hr, front=r.choice([w_curtain, w_ribbon]), side=side_plain,
         back=side_plain, detail=1)
    roof_kit(B, F, xa, Df, xb, D, Hr, level=1)
    return H, Hr


def fg_landmark(B, F, xa, xb, D):
    """Mega ad tower: grand podium, recessed screen, layered cantilever screen, exoskeleton,
    a skyscraper-scale screen wider than the tower above the neighbours, lattice comm tower."""
    r = B.rng
    B.hero = 3
    w = xb - xa
    zp = 28.0
    B.zb = 16.0
    Df = D * 0.72
    H = r.choice([336, 360, 384])
    _podium_all(B, F, xa, xb, Df, 16.0, second=True)
    for (a, b) in (((xb, 0), (xb, Df)), ((xa, Df), (xa, 0))):
        WF, Ln = F.wall(a, b)
        side_plain(B, WF, 0, Ln, -1, zp)
    g = B.g
    ch = min(6.0, w * 0.12)
    poly = L.chamfer_rect(xa + 1, 0, xb - 1, Df, ch)
    sw = (xb - xa) - 2 - 2 * ch - 6
    sh = min(sw * 2, 100)
    hz0 = zp + 14
    WF1, L1 = F.wall(poly[1], poly[2])
    hole = ((L1 - sw) / 2, hz0, (L1 + sw) / 2, hz0 + sh)
    mass(B, F, poly, zp, H, front=w_curtain, side=w_ribbon, back=side_plain, holes={1: hole},
         front_kw={"fins": True})
    recessed_screen(B, WF1, *hole, depth=2.0)
    # layered cantilever screen overlapping the lower corner of the recessed screen
    lx0 = hole[0] - 6
    add_screen(B, WF1, lx0, hz0 - 6, lx0 + 22, hz0 + 5, -4.5, kind="layered", fmt="W", neon=B.neon2, layer=1)
    for x in (lx0 + 2, lx0 + 20):
        beam(g, WF1.w(x, 0, hz0), WF1.w(x, -3.5, hz0), 0.6, "STL")
    # skyscraper-scale screen above the neighbours (z >= 200)
    big_w = max(56.0, w + 22)
    fmt = r.choice(["T", "W", "T"])
    zs0 = 205.0
    if fmt == "W":
        big_w = max(big_w, 80.0)
    top_scr = sky_screen(B, F, xa, xb, 0.0, zs0, big_w, fmt=fmt, out=7.0)
    if top_scr > H - 6:
        H = top_scr + 18
    # exoskeleton between the two screens
    if hz0 + sh + 12 < zs0 - 8:
        exo_braces(B, WF1, 0.5, L1 - 0.5, hz0 + sh + 6, zs0 - 6)
    for ei in (3, 7):
        a, b = poly[ei], poly[(ei + 1) % len(poly)]
        WFs, Ls = F.wall(a, b)
        if Ls > 8:
            ribs(B, WFs, 0, Ls, zp + 4, H - 4, spacing=5.5)
    ztop = crown(B, F, xa + 1, 0, xb - 1, Df, H, style=r.choice(["stepped", "helipad", "mech"]))
    for (px, py) in ((xa + 6, Df - 8), (xb - 6, Df - 8)):
        cylinder(g, F, px, py, 3.0, ztop, ztop + 22, "MEC", n=12, top="MEC")
        for zz in (ztop + 7, ztop + 14, ztop + 21):
            cylinder(g, F, px, py, 3.4, zz, zz + 0.8, "STL", n=12, top="STL", bottom="STL")
    antenna(B, F, (xa + xb) / 2, Df * 0.6, ztop, r.uniform(60, 90), base=4.5, top=0.8)
    # rear block
    Hr = r.choice([180, 210, 240])
    mass(B, F, [(xa, Df), (xb, Df), (xb, D), (xa, D)], -1, Hr, front=w_ribbon, side=side_plain, back=side_plain, detail=1)
    roof_kit(B, F, xa, Df, xb, D, Hr, level=2)
    L.light(F.w((xa + xb) / 2, -20, 60), (255, 60, 200), 60, 2.0, name=f"{B.bid}_spill")
    return H, Hr


# v2.1: built windows (reveals, mullions, sills, rooms behind lit glass) replace the v2 facades
from cp2_facade import (w_punched, w_ribbon, w_curtain, w_louver, w_balcony, w_tech, w_exo,  # noqa: E402,F811
                        w_plain, cornice)
STYLES.update({"curtain": w_curtain, "ribbon": w_ribbon, "punched": w_punched, "louver": w_louver,
               "balcony": w_balcony, "tech": w_tech, "exo": w_exo, "plain": w_plain})
