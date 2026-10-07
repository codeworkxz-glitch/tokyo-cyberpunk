"""HEX! Cyberpunk City v2 - tileable PBR surface textures.

Writes Color / Normal / Roughness / Metalness PNGs (1024x1024, tileable, OpenGL
normal maps) for every architectural material, plus flat swatches for the
Neon / lit-window materials.  Pure numpy + Pillow: no Blender procedural
shaders are involved, so what you see in Blender is what Roblox gets.

    python3 blender/cp2_textures.py export/textures
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

N = 1024
OUT = sys.argv[1] if len(sys.argv) > 1 else "export/textures"


# ----------------------------------------------------------------------------- noise
def vnoise(cells, rng, n=N):
    """Periodic (tileable) value noise in [0,1]."""
    g = rng.random((cells, cells))
    x = np.arange(n) * cells / n
    i0 = np.floor(x).astype(int)
    f = x - i0
    f = f * f * (3 - 2 * f)
    i1 = (i0 + 1) % cells
    fy, fx = f[:, None], f[None, :]
    a, b = g[np.ix_(i0, i0)], g[np.ix_(i0, i1)]
    c, d = g[np.ix_(i1, i0)], g[np.ix_(i1, i1)]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(base, octaves, rng, n=N, gain=0.5):
    acc, amp, tot = np.zeros((n, n)), 1.0, 0.0
    for o in range(octaves):
        acc += vnoise(base * 2 ** o, rng, n) * amp
        tot += amp
        amp *= gain
    return acc / tot


def streaks(rng, n=N, count=260, length=(40, 300), strength=0.25):
    """Vertical rain / grime streaks (wrap around)."""
    s = np.zeros((n, n))
    for _ in range(count):
        x = rng.integers(0, n)
        y = rng.integers(0, n)
        ln = rng.integers(*length)
        w = rng.integers(1, 4)
        fade = np.linspace(1, 0, ln) ** 1.5 * rng.uniform(0.3, 1)
        ys = (y + np.arange(ln)) % n
        for k in range(w):
            s[ys, (x + k) % n] += fade
    s = np.array(Image.fromarray((np.clip(s, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))) / 255
    return s * strength


def normal_from_height(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    dy = (np.roll(h, 1, 0) - np.roll(h, -1, 0)) * 0.5 * strength  # rows go down, +v goes up
    nz = np.ones_like(h)
    l = np.sqrt(dx * dx + dy * dy + nz * nz)
    nrm = np.stack([-dx / l, -dy / l, nz / l], -1)
    return ((nrm * 0.5 + 0.5) * 255).astype(np.uint8)


def save_set(name, color, height, rough, metal, nstrength=6.0):
    os.makedirs(OUT, exist_ok=True)
    c = np.clip(color, 0, 1)
    Image.fromarray((c * 255).astype(np.uint8), "RGB").save(f"{OUT}/{name}_Color.png", optimize=True)
    Image.fromarray(normal_from_height(height, nstrength), "RGB").save(f"{OUT}/{name}_Normal.png", optimize=True)
    Image.fromarray((np.clip(rough, 0, 1) * 255).astype(np.uint8), "L").save(f"{OUT}/{name}_Roughness.png", optimize=True)
    Image.fromarray((np.clip(metal, 0, 1) * 255).astype(np.uint8), "L").save(f"{OUT}/{name}_Metalness.png", optimize=True)
    print("wrote", name)


def rgb(*c):
    return np.array(c, dtype=float) / 255.0


def lines_mask(coords, period, width, offset=0.0):
    """1 where (coords - offset) mod period < width (pixel coords)."""
    return (((coords - offset) % period) < width).astype(float)


def soft(mask, r=1.0):
    im = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8))
    return np.array(im.filter(ImageFilter.GaussianBlur(r))) / 255.0


YY, XX = np.mgrid[0:N, 0:N].astype(float)


# ----------------------------------------------------------------------------- materials
# Tile sizes (studs) are what the Blender UVs use; keep in sync with cp2_build.py TILE.
def glass_curtain(rng):
    """Tile = 32 x 48 studs: 6 bays (5.33 studs) x 4 floors (12 studs)."""
    bay, flo = N / 6, N / 4
    glass = rgb(18, 24, 42)
    col = np.ones((N, N, 3)) * glass
    # per-pane reflection gradient + tint variation (dark sky / city reflection)
    pane_i = (XX // bay).astype(int)
    pane_j = (YY // flo).astype(int)
    tint = rng.random((7, 5))
    t = tint[pane_i % 6, pane_j % 4]
    grad = ((YY % flo) / flo)
    refl = 0.5 + 0.5 * np.sin((XX / N * 2 * np.pi) + t * 6)  # broad sweep
    sky = (rgb(34, 40, 78)[None, None] * (1 - grad[..., None]) + rgb(16, 19, 36)[None, None] * grad[..., None])
    col = sky * (0.8 + 0.4 * t[..., None]) + rgb(30, 18, 50) * (refl * 0.25)[..., None] * (t > 0.6)[..., None]
    col += (fbm(8, 4, rng) - 0.5)[..., None] * 0.02
    # spandrel band at each floor (dark metal panel, 1.8 studs)
    spand_h = flo * 1.8 / 12
    spand = ((YY % flo) > flo - spand_h).astype(float)
    mull = lines_mask(XX + 4, bay, 9)
    trans = lines_mask(YY + 3, flo, 7)
    metal_col = rgb(62, 65, 76)
    col = col * (1 - spand[..., None]) + (metal_col * 0.8 + (fbm(16, 3, rng)[..., None] - 0.5) * 0.04) * spand[..., None]
    frame = np.clip(mull + trans, 0, 1)
    col = col * (1 - frame[..., None]) + rgb(96, 100, 114) * frame[..., None]
    # thin highlight on mullion edge
    edge = lines_mask(XX + 4, bay, 2) * (1 - spand)
    col += edge[..., None] * 0.05
    h = frame * 0.8 + spand * 0.3 - soft(lines_mask(YY - flo + spand_h, flo, 3), 1) * 0.2
    rough = 0.08 + 0.05 * fbm(32, 3, rng) + frame * 0.3 + spand * 0.35
    metal = 0.55 + frame * 0.35 + spand * 0.25
    save_set("T_GlassCurtain", col, h, rough, metal, 5)


def glass_ribbon(rng):
    """Tile = 32 x 24 studs: 2 floors. Each floor: 4.5 stud spandrel + 7.5 stud ribbon window."""
    flo = N / 2
    sp = flo * 4.5 / 12
    in_sp = ((YY % flo) < sp).astype(float)  # spandrel at top of each floor-block (v high)
    n1 = fbm(12, 5, rng)
    conc = rgb(92, 93, 102) * (0.85 + 0.3 * n1[..., None]) - streaks(rng, strength=0.18)[..., None] * 0.25
    grooves = lines_mask(YY, flo, 3, sp * 0.5) * in_sp
    conc = conc * (1 - grooves[..., None] * 0.5)
    glass = rgb(20, 26, 46) + (1 - (YY % flo - sp) / (flo - sp))[..., None] * rgb(22, 20, 52)
    mull = lines_mask(XX + 3, N / 8, 6) * (1 - in_sp)
    col = conc * in_sp[..., None] + glass * (1 - in_sp[..., None])
    col = col * (1 - mull[..., None]) + rgb(80, 84, 96) * mull[..., None]
    sill = lines_mask(YY - sp, flo, 6) * 1.0
    col = col * (1 - sill[..., None]) + rgb(80, 82, 90) * sill[..., None]
    h = in_sp * 0.9 - grooves * 0.4 + mull * 0.6 + sill
    rough = in_sp * (0.75 + 0.15 * n1) + (1 - in_sp) * 0.1 + mull * 0.3
    metal = (1 - in_sp) * 0.6 + mull * 0.3
    save_set("T_GlassRibbon", col, h, rough, metal, 5)


def panel_metal(rng):
    """Tile = 24 x 24 studs: staggered 6 x 3 stud gunmetal panels."""
    pw, ph = N / 4, N / 8
    row = (YY // ph).astype(int)
    xo = XX + (row % 2) * pw / 2
    pid = (xo // pw).astype(int) % 4 + row * 4
    var = rng.random(64)[pid % 64]
    base = rgb(70, 74, 88) * (0.8 + 0.4 * var[..., None])
    n1 = fbm(10, 5, rng)
    col = base + (n1[..., None] - 0.5) * 0.05
    col -= streaks(rng, count=200, strength=0.3)[..., None] * 0.08
    seam = np.clip(lines_mask(xo, pw, 4) + lines_mask(YY, ph, 4), 0, 1)
    col = col * (1 - seam[..., None] * 0.7)
    # bolts near panel corners
    bx = (xo % pw)
    by = (YY % ph)
    bolt = np.zeros((N, N))
    for cx in (14, pw - 14):
        for cy in (12, ph - 12):
            bolt += (((bx - cx) ** 2 + (by - cy) ** 2) < 16).astype(float)
    col += bolt[..., None] * 0.08
    scratches = (fbm(64, 2, rng) > 0.78).astype(float) * 0.03
    col += scratches[..., None]
    h = 1 - seam * 0.9 + bolt * 0.6 + (n1 - 0.5) * 0.1
    rough = 0.4 + 0.25 * n1 + 0.2 * var + seam * 0.2
    metal = 0.85 - seam * 0.4
    save_set("T_PanelMetal", col, h, rough, metal, 5)


def concrete_dark(rng):
    """Tile = 32 x 32 studs: board-formed dark concrete, 8 x 4 stud pours with tie holes."""
    n1, n2 = fbm(8, 6, rng), fbm(48, 3, rng)
    col = rgb(88, 89, 98) * (0.75 + 0.45 * n1[..., None]) + (n2[..., None] - 0.5) * 0.06
    col -= streaks(rng, count=320, strength=0.35)[..., None] * 0.12
    pw, ph = N / 4, N / 8
    joint = np.clip(lines_mask(XX, pw, 3) + lines_mask(YY, ph, 2), 0, 1)
    col *= (1 - joint[..., None] * 0.35)
    tx, ty = XX % (pw / 2), YY % ph
    tie = (((tx - pw / 4) ** 2 + (ty - ph / 2) ** 2) < 25).astype(float)
    col *= (1 - tie[..., None] * 0.6)
    h = n1 * 0.4 + n2 * 0.3 - joint * 0.6 - tie
    rough = 0.82 + 0.12 * n2
    save_set("T_ConcreteDark", col, h, rough, np.zeros((N, N)), 4)


def tech_panel(rng):
    """Tile = 16 x 16 studs: recursive sci-fi panelling, grooves, vents, inlays."""
    img = Image.new("L", (N, N), 128)
    hd = ImageDraw.Draw(img)
    colimg = Image.new("RGB", (N, N), (50, 54, 70))
    cd = ImageDraw.Draw(colimg)

    def split(x0, y0, x1, y1, depth):
        w, h = x1 - x0, y1 - y0
        if depth > 4 or (w < 140 and h < 140) or (depth > 1 and rng.random() < 0.18):
            shade = int(rng.integers(48, 84))
            tint = (shade, shade + 3, shade + 12)
            cd.rectangle([x0 + 3, y0 + 3, x1 - 3, y1 - 3], fill=tint)
            hd.rectangle([x0 + 3, y0 + 3, x1 - 3, y1 - 3], fill=int(rng.integers(150, 200)))
            r = rng.random()
            if r < 0.22 and w > 60 and h > 60:  # vent slots
                for yy in range(int(y0 + 14), int(y1 - 14), 12):
                    cd.rectangle([x0 + 14, yy, x1 - 14, yy + 5], fill=(14, 15, 20))
                    hd.rectangle([x0 + 14, yy, x1 - 14, yy + 5], fill=60)
            elif r < 0.4 and w > 50 and h > 50:  # bolted plate
                for (bx, by) in ((x0 + 12, y0 + 12), (x1 - 12, y0 + 12), (x0 + 12, y1 - 12), (x1 - 12, y1 - 12)):
                    cd.ellipse([bx - 4, by - 4, bx + 4, by + 4], fill=(70, 72, 82))
                    hd.ellipse([bx - 4, by - 4, bx + 4, by + 4], fill=230)
            elif r < 0.52:  # inlay channel (where neon strips may sit)
                if w > h:
                    cy = (y0 + y1) // 2
                    cd.rectangle([x0 + 10, cy - 3, x1 - 10, cy + 3], fill=(18, 20, 32))
                    hd.rectangle([x0 + 10, cy - 3, x1 - 10, cy + 3], fill=80)
                else:
                    cx = (x0 + x1) // 2
                    cd.rectangle([cx - 3, y0 + 10, cx + 3, y1 - 10], fill=(18, 20, 32))
                    hd.rectangle([cx - 3, y0 + 10, cx + 3, y1 - 10], fill=80)
            return
        if w > h:
            s = int(x0 + w * rng.uniform(0.3, 0.7))
            split(x0, y0, s, y1, depth + 1)
            split(s, y0, x1, y1, depth + 1)
        else:
            s = int(y0 + h * rng.uniform(0.3, 0.7))
            split(x0, y0, x1, s, depth + 1)
            split(x0, s, x1, y1, depth + 1)

    for gx in range(2):
        for gy in range(2):
            split(gx * N // 2, gy * N // 2, (gx + 1) * N // 2, (gy + 1) * N // 2, 0)
    col = np.array(colimg) / 255.0
    h = np.array(img.filter(ImageFilter.GaussianBlur(1.5))) / 255.0
    n1 = fbm(16, 4, rng)
    col = col * (0.85 + 0.3 * n1[..., None]) - streaks(rng, count=150, strength=0.2)[..., None] * 0.06
    rough = 0.35 + 0.3 * n1 + (h < 0.4) * 0.2
    metal = 0.55 + 0.3 * (h > 0.55)
    save_set("T_TechPanel", col, h, rough, metal, 6)


def mech_grille(rng):
    """Tile = 8 x 8 studs: industrial louvre grille / ribbed duct sheet."""
    slat = N / 16
    p = (YY % slat) / slat
    h = np.clip(np.sin(p * np.pi) * 1.2, 0, 1)
    frame = np.clip(lines_mask(XX, N / 2, 18) + lines_mask(YY, N / 2, 18), 0, 1)
    h = h * (1 - frame) + frame * 1.0
    n1 = fbm(12, 5, rng)
    base = rgb(80, 86, 90) * (0.8 + 0.4 * n1[..., None])
    col = base * (0.35 + 0.65 * h[..., None])
    col -= streaks(rng, count=120, strength=0.3)[..., None] * 0.1
    rust = (fbm(20, 4, rng) > 0.68).astype(float) * 0.5
    col = col * (1 - rust[..., None] * 0.3) + rgb(70, 45, 30) * rust[..., None] * 0.3
    rough = 0.5 + 0.3 * n1 + rust * 0.2
    metal = 0.75 - rust * 0.5
    save_set("T_Mechanical", col, h, rough, metal, 8)


def roof_deck(rng):
    """Tile = 32 x 32 studs: membrane roofing sheets, seams, patches."""
    n1, n2 = fbm(6, 6, rng), fbm(40, 3, rng)
    col = rgb(64, 66, 74) * (0.75 + 0.5 * n1[..., None]) + (n2[..., None] - 0.5) * 0.05
    seam = np.clip(lines_mask(XX, N / 4, 5) + lines_mask(YY, N / 4, 5), 0, 1)
    col *= 1 - seam[..., None] * 0.25
    patch = np.zeros((N, N))
    pim = Image.new("L", (N, N), 0)
    pd = ImageDraw.Draw(pim)
    for _ in range(14):
        x, y = rng.integers(0, N - 140, 2)
        w, hh = rng.integers(40, 140, 2)
        pd.rectangle([x, y, x + w, y + hh], fill=255)
    patch = np.array(pim) / 255.0
    col = col * (1 - patch[..., None] * 0.2)
    puddle = (fbm(5, 4, rng) > 0.66).astype(float)
    col = col * (1 - puddle[..., None] * 0.3)
    h = n2 * 0.2 + seam * 0.5 + patch * 0.3
    rough = 0.85 - puddle * 0.7
    save_set("T_RoofDeck", col, h, rough, np.zeros((N, N)), 3)


def steel(rng):
    """Tile = 8 x 8 studs: painted dark steel with worn edges (beams, trusses, pipes, rails)."""
    n1, n2 = fbm(10, 6, rng), fbm(60, 2, rng)
    col = rgb(68, 72, 84) * (0.8 + 0.35 * n1[..., None])
    wear = soft((fbm(24, 4, rng) > 0.76).astype(float), 1.5)
    col = col * (1 - wear[..., None] * 0.6) + rgb(72, 75, 82) * wear[..., None] * 0.6
    col -= streaks(rng, count=90, strength=0.25)[..., None] * 0.08
    h = n2 * 0.3 + wear * 0.2
    rough = 0.45 + 0.25 * n1 - wear * 0.15
    metal = 0.6 + wear * 0.35
    save_set("T_Steel", col, h, rough, metal, 2)


def louver(rng):
    """Tile = 8 x 12 studs: vertical aluminium fins over dark glass (mid/background towers)."""
    fin = N / 8
    p = (XX % fin) / fin
    finmask = (p < 0.35).astype(float)
    shade = np.where(p < 0.35, 0.65 + 0.35 * np.sin(p / 0.35 * np.pi), 0.0)
    glass = rgb(18, 22, 40) + ((YY % (N / 1)) / N)[..., None] * rgb(18, 14, 44)
    finc = rgb(120, 126, 142) * shade[..., None]
    col = glass * (1 - finmask[..., None]) + finc * finmask[..., None]
    slab = lines_mask(YY, N, 26)
    col = col * (1 - slab[..., None]) + rgb(48, 50, 58) * slab[..., None]
    h = shade + slab * 0.6
    rough = 0.1 + finmask * 0.35 + slab * 0.4
    metal = 0.6 + finmask * 0.3
    save_set("T_Louver", col, h, rough, metal, 6)


def tower_night(rng):
    """Tile = 32 x 48 studs: background tower glazing with a baked scatter of pale windows.

    The bright panes are only in the colour map, so in Roblox they read as lit glass even
    under dim night ambient; the main glow still comes from the separate Neon window meshes."""
    bay, flo = N / 8, N / 4
    pi, pj = (XX // bay).astype(int), (YY // flo).astype(int)
    lit = rng.random((8, 4))
    warm = rng.random((8, 4))
    L = lit[pi % 8, pj % 4]
    W = warm[pi % 8, pj % 4]
    inpane = ((XX % bay) > 8) & ((XX % bay) < bay - 8) & ((YY % flo) > 18) & ((YY % flo) < flo - 40)
    glass = rgb(18, 22, 42) + ((YY % flo) / flo)[..., None] * rgb(20, 16, 48)
    litc = np.where((W > 0.5)[..., None], rgb(150, 120, 90), rgb(90, 120, 160))
    on = ((L > 0.62) & inpane).astype(float)
    col = glass * (1 - on[..., None]) + litc * on[..., None] * (0.7 + 0.3 * ((YY % flo) / flo))[..., None]
    frame = 1 - inpane.astype(float)
    col = col * (1 - frame[..., None] * 0.6) + rgb(58, 62, 74) * frame[..., None] * 0.6
    h = frame * 0.7
    rough = 0.12 + frame * 0.4
    metal = 0.5 + frame * 0.3
    save_set("T_TowerNight", col, h, rough, metal, 4)


# Neon / lit materials: flat colour. In Roblox these are Material = Neon + Color, the PNG
# swatch is only so the FBX material has a texture that previews correctly.
FLAT = {
    "NEON_CYN": (0, 230, 255), "NEON_MAG": (255, 25, 175), "NEON_VIO": (150, 45, 255),
    "NEON_BLU": (30, 95, 255), "NEON_RED": (255, 32, 45), "NEON_AMB": (255, 150, 25),
    "NEON_WHT": (215, 228, 255),
    "WIN_WRM": (255, 196, 135), "WIN_COL": (150, 205, 255), "WIN_PNK": (255, 125, 205),
    "WIN_VIO": (175, 135, 255), "SHOP_LIT": (255, 236, 212),
}


def flat_swatches():
    for k, c in FLAT.items():
        Image.new("RGB", (16, 16), c).save(f"{OUT}/F_{k}.png")
    print("wrote", len(FLAT), "flat swatches")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for i, fn in enumerate([glass_curtain, glass_ribbon, panel_metal, concrete_dark, tech_panel,
                            mech_grille, roof_deck, steel, louver, tower_night]):
        fn(np.random.default_rng(1000 + i))
    flat_swatches()
