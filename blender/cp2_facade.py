"""HEX! Cyberpunk City v2.1 - architectural facade systems.

Replaces the v2 facades (flat textured planes + glowing squares) with built windows:
every opening has reveals, recessed glass, mullions / transoms and a sill; lit windows show
a room set back behind the frame instead of a flat light. Lighting follows tenancy: whole
office floors, individual flats, dark floors - not random confetti.

All styles keep the v2 signature  style(B, WF, s0, s1, z0, z1, **kw)  and cover the wall
rectangle [s0, s1] x [z0, z1] of the wall frame WF (x along the wall, y into the building).
"""
import math

import cp2_lib as L
from cp2_lib import FLOOR, box, quad

ROOM = 1.6  # depth of the visible room behind a lit window


def _o(B, WF):
    return WF.w(0, 0, B.zb)


def _cap(B, detail, z=None):
    """Archetypes lower B.detail_cap for rear / distant masses; high floors (small from the
    plaza) lose detail too."""
    d = min(detail, getattr(B, "detail_cap", 2))
    if z is not None:
        if z > 180:
            d = min(d, 0)
        elif z > 100:
            d = min(d, 1)
    return d


# ----------------------------------------------------------------------------- lighting plan
def floor_type(B, zf):
    """Tenancy of a floor (shared by every wall of the building)."""
    plan = B.__dict__.setdefault("_floors", {})
    k = int(round(zf))
    if k not in plan:
        r = B.rng
        mix = B.__dict__.setdefault("_mix", r.choice([(0.35, 0.4), (0.15, 0.6), (0.5, 0.25), (0.25, 0.45)]))
        v = r.random()
        if v < mix[0]:
            t = ("office", r.choices(["WIN_COL", "WIN_WRM"], [3, 2])[0], r.uniform(0.6, 0.95))
        elif v < mix[0] + mix[1]:
            t = ("resi", None, r.uniform(0.12, 0.35))
        else:
            t = ("dark", None, r.uniform(0.0, 0.06))
        plan[k] = t
    return plan[k]


def window_light(B, zf, i):
    """None (dark) or the WIN_* key for bay i of the floor at zf."""
    kind, key, p = floor_type(B, zf)
    r = B.rng
    if kind == "office":
        runs = B.__dict__.setdefault("_runs", {})
        st = runs.setdefault(int(zf), [r.random() < p, 0])
        st[1] += 1
        if st[1] > r.randint(3, 8):  # occasional switched-off section
            st[0] = r.random() < p
            st[1] = 0
        return key if st[0] else None
    if kind == "resi":
        if r.random() < p:
            return r.choices(["WIN_WRM", "WIN_WRM", "WIN_WRM", "WIN_COL", "WIN_PNK", "WIN_VIO"])[0]
        return None
    return "WIN_WRM" if r.random() < p else None


def _room(B, WF, x0, z0, x1, z1, d, key, frame_key):
    """Lit room seen through an opening whose glass plane sits at depth d."""
    g = B.g
    cap = _cap(B, 2, z0)
    if cap <= 0:
        quad(g, WF, x0, z0, x1, z1, d, key)
        return
    dr = d + ROOM
    w = WF.w
    g.face(frame_key, [w(x0, d, z0), w(x0, dr, z0), w(x0, dr, z1), w(x0, d, z1)])
    g.face(frame_key, [w(x1, dr, z0), w(x1, d, z0), w(x1, d, z1), w(x1, dr, z1)])
    if cap == 1:
        quad(g, WF, x0, z0, x1, z1, dr, key)
        return
    g.face(frame_key, [w(x0, dr, z1), w(x1, dr, z1), w(x1, d, z1), w(x0, d, z1)])  # ceiling
    r = B.rng.random()
    if r < 0.25:   # blinds partly down
        zb = z1 - (z1 - z0) * B.rng.uniform(0.25, 0.55)
        quad(g, WF, x0, z0, x1, zb, dr, key)
        quad(g, WF, x0, zb, x1, z1, d + 0.15, "TEC")
    elif r < 0.35:  # curtain on one side
        xm = x0 + (x1 - x0) * B.rng.uniform(0.35, 0.6)
        quad(g, WF, x0, z0, xm, z1, dr, key)
        quad(g, WF, xm, z0, x1, z1, d + 0.15, "TEC")
    else:
        quad(g, WF, x0, z0, x1, z1, dr, key)
        # ceiling light line
        quad(g, WF, x0 + 0.2, z1 - 0.35, x1 - 0.2, z1 - 0.15, dr - 0.05, "NEON_WHT" if key == "WIN_COL" else key)
    # interior silhouettes so rooms read as occupied, not as light panels
    v = B.rng.random()
    h = z1 - z0
    if v < 0.35:      # desk / counter
        quad(g, WF, x0, z0, x1, z0 + h * 0.3, dr - 0.5, "STL")
    elif v < 0.5:     # shelving unit on one side
        xa = x0 if B.rng.random() < 0.5 else x1 - (x1 - x0) * 0.35
        quad(g, WF, xa, z0, xa + (x1 - x0) * 0.35, z0 + h * 0.8, dr - 0.6, "STL")
    elif v < 0.6:     # partition with a doorway glow
        xm = x0 + (x1 - x0) * B.rng.uniform(0.3, 0.7)
        quad(g, WF, x0, z0, xm, z1 - 0.4, dr - 0.3, "TEC")


def opening(B, WF, x0, z0, x1, z1, d, zf, i, wall_key, frame_key="STL", mull=1, transom=True, sill=True,
            detail=2):
    """One window: reveals, glass or lit room, mullions, transom, sill."""
    g = B.g
    w = WF.w
    o = _o(B, WF)
    g.face(wall_key, [w(x0, 0, z0), w(x0, d, z0), w(x0, d, z1), w(x0, 0, z1)], o=o)
    g.face(wall_key, [w(x1, d, z0), w(x1, 0, z0), w(x1, 0, z1), w(x1, d, z1)], o=o)
    g.face(wall_key, [w(x0, 0, z0), w(x1, 0, z0), w(x1, d, z0), w(x0, d, z0)], o=o)
    g.face(wall_key, [w(x0, d, z1), w(x1, d, z1), w(x1, 0, z1), w(x0, 0, z1)], o=o)
    lit = window_light(B, zf, i)
    if lit:
        _room(B, WF, x0, z0, x1, z1, d, lit, frame_key)
    else:
        quad(g, WF, x0, z0, x1, z1, d, "GLS", o=o)
    detail = _cap(B, detail, z0)
    if detail >= 1:
        t = 0.2
        for k in range(1, mull + 1):
            xm = x0 + (x1 - x0) * k / (mull + 1)
            quad(g, WF, xm - t / 2, z0, xm + t / 2, z1, d - 0.12, frame_key)
        if transom and z1 - z0 > 5:
            zt = z0 + (z1 - z0) * 0.74
            quad(g, WF, x0, zt - t / 2, x1, zt + t / 2, d - 0.12, frame_key)
    if sill and detail >= 2:
        box(g, WF, x0 - 0.3, -0.45, z0 - 0.3, x1 + 0.3, 0, z0, wall_key, skip=("back", "bottom", "left", "right"))


def _floors(B, z0, z1):
    out = []
    k = math.ceil((z0 - B.zb) / FLOOR - 1e-6)
    while B.zb + (k + 1) * FLOOR <= z1 + 1e-6:
        out.append(B.zb + k * FLOOR)
        k += 1
    return out


def _bays(s0, s1, bay):
    n = max(1, int(round((s1 - s0) / bay)))
    bw = (s1 - s0) / n
    return [(s0 + i * bw, s0 + (i + 1) * bw) for i in range(n)]


def _fill_rest(B, WF, s0, s1, z0, z1, floors, key):
    o = _o(B, WF)
    if not floors:
        quad(B.g, WF, s0, z0, s1, z1, 0, key, o=o)
        return
    if floors[0] > z0 + 1e-3:
        quad(B.g, WF, s0, z0, s1, floors[0], 0, key, o=o)
    top = floors[-1] + FLOOR
    if top < z1 - 1e-3:
        quad(B.g, WF, s0, top, s1, z1, 0, key, o=o)


# ----------------------------------------------------------------------------- styles
def w_punched(B, WF, s0, s1, z0, z1, key=None, bay=None, win_w=None, sill=2.6, head=10.0, depth=0.9, p=None,
              detail=2, slab=True, **kw):
    """Masonry / panel wall with punched windows (reveals, mullion, transom, sill), slab bands."""
    g = B.g
    key = key or B.__dict__.setdefault("_wall", B.rng.choice(["CON", "PNL", "CON", "TEC"]))
    bay = bay or B.__dict__.setdefault("_bay", B.rng.choice([4.5, 5.0, 5.5, 6.0]))
    win_w = win_w or bay * B.__dict__.setdefault("_ww", B.rng.uniform(0.55, 0.72))
    o = _o(B, WF)
    floors = _floors(B, z0, z1)
    _fill_rest(B, WF, s0, s1, z0, z1, floors, key)
    bays = _bays(s0, s1, bay)
    for zf in floors:
        za, zb = zf + sill, zf + head
        quad(g, WF, s0, zf, s1, za, 0, key, o=o)
        quad(g, WF, s0, zb, s1, zf + FLOOR, 0, key, o=o)
        x_prev = s0
        for i, (b0, b1) in enumerate(bays):
            ww = min(win_w, (b1 - b0) - 0.8)
            x0 = (b0 + b1) / 2 - ww / 2
            x1 = x0 + ww
            quad(g, WF, x_prev, za, x0, zb, 0, key, o=o)
            opening(B, WF, x0, za, x1, zb, depth, zf, i, key, mull=1 if ww > 3 else 0, detail=detail)
            x_prev = x1
        quad(g, WF, x_prev, za, s1, zb, 0, key, o=o)
        if slab and _cap(B, detail) >= 1:
            box(g, WF, s0, -0.35, zf - 0.45, s1, 0, zf + 0.55, "CON" if key != "CON" else "PNL", skip=("back",))
    if _cap(B, detail) >= 1 and z1 - z0 > 20:
        cornice(B, WF, s0, s1, z1)


def w_ribbon(B, WF, s0, s1, z0, z1, key=None, shades=True, depth=1.0, p=None, detail=2, **kw):
    """Continuous ribbon windows recessed between solid spandrels, mullions every bay."""
    g = B.g
    key = key or B.__dict__.setdefault("_wall", B.rng.choice(["CON", "PNL", "TEC"]))
    o = _o(B, WF)
    floors = _floors(B, z0, z1)
    _fill_rest(B, WF, s0, s1, z0, z1, floors, key)
    bays = _bays(s0, s1, 3.6)
    w = WF.w
    for zf in floors:
        za, zb = zf + 3.4, zf + 10.6
        quad(g, WF, s0, zf, s1, za, 0, key, o=o)
        quad(g, WF, s0, zb, s1, zf + FLOOR, 0, key, o=o)
        d = depth
        g.face(key, [w(s0, 0, za), w(s1, 0, za), w(s1, d, za), w(s0, d, za)], o=o)
        g.face(key, [w(s0, d, zb), w(s1, d, zb), w(s1, 0, zb), w(s0, 0, zb)], o=o)
        g.face(key, [w(s0, d, za), w(s0, 0, za), w(s0, 0, zb), w(s0, d, zb)][::-1], o=o)
        g.face(key, [w(s1, d, za), w(s1, 0, za), w(s1, 0, zb), w(s1, d, zb)], o=o)
        # glass in runs; lit bays become rooms
        run0 = None
        for i, (b0, b1) in enumerate(bays):
            lit = window_light(B, zf, i)
            if lit:
                if run0 is not None:
                    quad(g, WF, run0, za, b0, zb, d, "GLS", o=o)
                    run0 = None
                _room(B, WF, b0, za, b1, zb, d, lit, "STL")
            elif run0 is None:
                run0 = b0
        if run0 is not None:
            quad(g, WF, run0, za, s1, zb, d, "GLS", o=o)
        if _cap(B, detail) >= 1:
            for (b0, b1) in bays[1:]:
                quad(g, WF, b0 - 0.12, za, b0 + 0.12, zb, d - 0.12, "STL")
            if shades:
                box(g, WF, s0, -1.3, zb - 0.1, s1, 0, zb + 0.3, "STL", skip=("back",))
    if _cap(B, detail) >= 1 and z1 - z0 > 20:
        cornice(B, WF, s0, s1, z1)


def w_curtain(B, WF, s0, s1, z0, z1, fins=True, slabs=True, glass="GLS", fin_key="STL", p=None, detail=2,
              bay=None, **kw):
    """Unitised curtain wall: projecting mullion grid, floor transoms, rooms behind lit panels."""
    g = B.g
    o = _o(B, WF)
    bay = bay or B.__dict__.setdefault("_cbay", B.rng.choice([3.2, 4.0, 5.33]))
    floors = _floors(B, z0, z1)
    _fill_rest(B, WF, s0, s1, z0, z1, floors, glass)
    bays = _bays(s0, s1, bay)
    gd = 0.25  # glass set back behind the mullion faces
    for zf in floors:
        za, zb = zf + 1.4, zf + FLOOR
        quad(g, WF, s0, zf, s1, za, gd, "PNL", o=o)  # spandrel / floor edge
        run0 = None
        for i, (b0, b1) in enumerate(bays):
            lit = window_light(B, zf, i)
            if lit:
                if run0 is not None:
                    quad(g, WF, run0, za, b0, zb, gd, glass, o=o)
                    run0 = None
                _room(B, WF, b0, za, b1, zb, gd, lit, "STL")
            elif run0 is None:
                run0 = b0
        if run0 is not None:
            quad(g, WF, run0, za, s1, zb, gd, glass, o=o)
        # horizontal transom at the floor line (a flat band once it is small from the plaza)
        if _cap(B, 2, zf) <= 0:
            quad(g, WF, s0, zf, s1, zf + 1.4, -0.35, fin_key)
        else:
            box(g, WF, s0, -0.35, zf, s1, gd, zf + 1.4, fin_key, skip=("back",))
    # continuous vertical mullions (one member per bay line, full height)
    if floors:
        zt0, zt1 = floors[0], floors[-1] + FLOOR
        dep = 0.9 if fins else 0.35
        for (b0, b1) in bays[1:]:
            box(g, WF, b0 - 0.15, -dep, zt0, b0 + 0.15, gd, zt1, fin_key, skip=("back", "bottom"))
    if _cap(B, detail) >= 1 and z1 - z0 > 20:
        cornice(B, WF, s0, s1, z1, key="STL", h=1.2)


def w_louver(B, WF, s0, s1, z0, z1, fin_key="PNL", pitch=2.0, depth=1.8, p=None, **kw):
    """Curtain wall screened by deep vertical fins."""
    w_curtain(B, WF, s0, s1, z0, z1, fins=False, p=p)
    x = s0 + pitch / 2
    while x < s1 - 0.3:
        box(B.g, WF, x - 0.2, -depth, z0, x + 0.2, -0.35, z1, fin_key, skip=("back", "bottom"))
        x += pitch


def w_balcony(B, WF, s0, s1, z0, z1, p=None, **kw):
    """Residential: full-height glazed doors behind continuous balconies with dividers + AC units."""
    g = B.g
    w_punched(B, WF, s0, s1, z0, z1, key="CON", bay=4.0, win_w=3.2, sill=0.4, head=9.6, depth=0.6, detail=1,
              slab=False)
    unit = max(8.0, (s1 - s0) / max(1, round((s1 - s0) / 10)))
    for zf in _floors(B, z0, z1):
        box(g, WF, s0, -3.4, zf - 0.6, s1, 0, zf, "CON", skip=("back",))
        box(g, WF, s0, -3.4, zf, s1, -3.15, zf + 3.4, "TEC", skip=("back", "bottom"))
        box(g, WF, s0, -3.5, zf + 3.4, s1, -3.05, zf + 3.6, "STL", skip=("back", "bottom"))
        x = s0
        while x < s1 - 1:
            box(g, WF, x, -3.4, zf, x + 0.3, 0, zf + FLOOR - 0.6, "CON", skip=("back", "bottom", "top"))
            if B.rng.random() < 0.4:
                box(g, WF, x + 1, -2.6, zf, x + 3.2, -1.4, zf + 1.6, "MEC", skip=("back", "bottom"))
            x += unit


def w_tech(B, WF, s0, s1, z0, z1, p=None, strips=True, **kw):
    """Sci-fi panel cladding with tall narrow windows."""
    w_punched(B, WF, s0, s1, z0, z1, key="TEC", bay=3.2, win_w=1.7, sill=1.8, head=10.6, depth=0.8, detail=1)


def w_exo(B, WF, s0, s1, z0, z1, p=None, ribs_neon=True, **kw):
    from cp2_arch import exo_braces
    w_curtain(B, WF, s0, s1, z0, z1, fins=False, p=p)
    exo_braces(B, WF, s0, s1, z0, z1, neon=False)


def w_plain(B, WF, s0, s1, z0, z1, key="CON", windows=0.0, wkey="TWN", **kw):
    """Secondary / party walls: plain cladding. Above ~5 floors a wall that shows over the
    neighbours uses the night-glazing texture (pale windows baked in) instead of geometry."""
    o = _o(B, WF)
    if windows > 0 and z1 > 64 and z1 - z0 > 24:
        zc = max(z0, 52.0)
        if zc > z0:
            quad(B.g, WF, s0, z0, s1, zc, 0, key, o=o)
        quad(B.g, WF, s0, zc, s1, z1, 0, wkey, o=WF.w(0, 0, 0))
    else:
        quad(B.g, WF, s0, z0, s1, z1, 0, key, o=o)


def cornice(B, WF, s0, s1, z, key="CON", h=1.6, out=0.9):
    box(B.g, WF, s0 - 0.01, -out, z - h, s1 + 0.01, 0, z, key, skip=("back",))
