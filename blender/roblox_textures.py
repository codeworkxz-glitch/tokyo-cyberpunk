"""Tileable 1024px textures for the Roblox export (Roblox caps textures at 1024).

Arrays are (rows, cols, 4) with row 0 at the BOTTOM, matching Blender's
image.pixels and UV convention.
"""
import os

import bpy
import numpy as np

N = 1024

# Facade tile = 4 window bays x 2 floors
FACADE_METERS = (8.0, 7.2)
SURFACE_METERS = 8.0

# first colour = the neon line accent, the rest = lit interiors
FACADE_VARIANTS = {
    "cyan": [(0.0, 0.85, 1.0), (0.55, 0.9, 1.0), (1.0, 0.85, 0.6)],
    "pink": [(1.0, 0.1, 0.6), (1.0, 0.45, 0.8), (0.75, 0.5, 1.0)],
    "purple": [(0.6, 0.2, 1.0), (0.7, 0.55, 1.0), (0.4, 0.9, 1.0)],
    "amber": [(1.0, 0.5, 0.05), (1.0, 0.78, 0.45), (1.0, 0.9, 0.7)],
}
ACCENTS = [(0.0, 0.85, 1.0), (1.0, 0.05, 0.55), (0.55, 0.1, 1.0), (1.0, 0.45, 0.02),
           (0.2, 1.0, 0.35), (1.0, 0.08, 0.1)]


def spectral(rng, beta, aniso=(1.0, 1.0), n=N):
    """Periodic noise with a 1/f^beta spectrum, normalised to roughly 0..1."""
    kx = np.fft.fftfreq(n)[None, :] * aniso[0]
    ky = np.fft.fftfreq(n)[:, None] * aniso[1]
    k = np.sqrt(kx ** 2 + ky ** 2)
    k[0, 0] = 1.0
    amp = k ** (-beta / 2.0)
    amp[0, 0] = 0.0
    field = np.real(np.fft.ifft2(amp * np.exp(2j * np.pi * rng.random((n, n)))))
    lo, hi = np.percentile(field, (1, 99))
    return np.clip((field - lo) / (hi - lo), 0.0, 1.0)


def concrete_value(rng, tone=0.55, seams=True, n=N, seam_dark=0.55, tie_holes=True):
    blotch = spectral(rng, 3.2, n=n)
    mid = spectral(rng, 2.0, n=n)
    grain = spectral(rng, 0.6, n=n)
    v = tone + 0.16 * (blotch - 0.5) + 0.09 * (mid - 0.5) + 0.07 * (grain - 0.5)

    pores = spectral(rng, 0.0, n=n) > 0.985
    v = np.where(pores, v * 0.55, v)

    streak = spectral(rng, 2.4, aniso=(1.0, 14.0), n=n)
    v *= 1.0 - 0.28 * np.clip((streak - 0.55) / 0.3, 0.0, 1.0)

    if seams:  # 8 m x 4 m formwork panels with tie holes
        v[:, 0:3] *= seam_dark
        v[0:3, :] *= seam_dark
        v[n // 2:n // 2 + 3, :] *= seam_dark
        yy, xx = np.mgrid[0:n, 0:n]
        for cy in (n // 8, 3 * n // 8, 5 * n // 8, 7 * n // 8) if tie_holes else ():
            for cx in (n // 4, 3 * n // 4):
                d = np.hypot(yy - cy, xx - cx)
                v = np.where(d < 7, 0.3 * tone, v)
                v = np.where((d >= 7) & (d < 10), v * 1.12, v)
    return np.clip(v, 0.0, 1.0)


def to_rgba(v, tint):
    rgb = v[..., None] * np.array(tint)[None, None, :]
    return np.concatenate([np.clip(rgb, 0, 1), np.ones(v.shape + (1,))], axis=2)


def concrete(rng, tone=0.55, tint=(1.0, 0.98, 0.95), ground=False):
    v = concrete_value(rng, tone, seam_dark=0.85 if ground else 0.55, tie_holes=not ground)
    return to_rgba(v, tint)


def asphalt(rng):
    v = 0.12 + 0.05 * (spectral(rng, 1.8) - 0.5)
    stones = spectral(rng, 0.0)
    v = np.where(stones > 0.96, v + 0.07 * (stones - 0.96) / 0.04, v)
    wet = spectral(rng, 3.4)
    v *= 1.0 - 0.3 * np.clip((wet - 0.6) / 0.2, 0.0, 1.0)
    return to_rgba(np.clip(v, 0, 1), (1.0, 1.0, 1.05))


def facade(rng, palette, lit_chance=0.0):
    """Futuristic facade: dark metal/concrete spandrels, continuous strip windows,
    thin neon lines under some floors, a few lit interiors per floor."""
    v = concrete_value(rng, tone=0.2, seams=False)
    img = to_rgba(v, (0.85, 0.9, 1.05))
    cols, rows = 4, 2
    cw, ch = N // cols, N // rows
    accent = np.array(palette[0])
    for fy in range(rows):
        y0 = fy * ch
        # vertical panel seams on the spandrel
        for fx in range(cols + 1):
            x = (fx * cw) % N
            img[y0:y0 + ch, x:x + 3, :3] *= 0.5
        gy0, gy1 = y0 + int(ch * 0.32), y0 + int(ch * 0.86)
        h = gy1 - gy0
        t = np.linspace(0.0, 1.0, h)[:, None, None]
        # dark glass strip with a sky reflection gradient
        diag = np.linspace(0.0, 1.0, N)[None, :, None]
        refl = 0.03 + 0.07 * np.clip(t * 0.8 + diag * 0.3 - 0.25, 0, 1)
        img[gy0:gy1, :, :3] = refl * np.array((0.5, 0.7, 1.0))
        for fx in range(cols):  # lit bays
            if rng.random() < lit_chance:
                col = np.array(palette[rng.integers(len(palette))])
                x0, x1 = fx * cw + 4, (fx + 1) * cw - 4
                img[gy0:gy1, x0:x1, :3] = col * (0.55 + 0.45 * t)
                if rng.random() < 0.5:
                    img[gy0:gy1:12, x0:x1, :3] *= 0.6  # blinds
        for fx in range(cols * 2 + 1):  # mullions
            x = min(fx * cw // 2, N - 3)
            img[gy0:gy1, x:x + 3, :3] = 0.05
        img[gy0 - 5:gy0, :, :3] = 0.04  # sill
        img[gy1:gy1 + 5, :, :3] = 0.04  # head
        if rng.random() < 0.6:  # neon line under the floor
            img[gy0 - 12:gy0 - 8, :, :3] = accent
    return np.clip(img, 0, 1)


def solid(color, n=8):
    img = np.ones((n, n, 4))
    img[..., :3] = color
    return img


def save(arr, name, outdir):
    rows, cols = arr.shape[:2]
    img = bpy.data.images.new(name, cols, rows, alpha=False)
    img.pixels.foreach_set(arr.astype(np.float32).ravel())
    path = os.path.join(outdir, name + ".png")
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    return img


def build_all(outdir, seed=2077):
    """Create every texture; returns {key: bpy image}."""
    os.makedirs(outdir, exist_ok=True)
    rng = np.random.default_rng(seed)
    imgs = {
        "concrete": save(concrete(rng, 0.55), "cp_concrete", outdir),
        "pavement": save(concrete(rng, 0.6, (1.0, 0.99, 0.97), ground=True), "cp_pavement", outdir),
        "roof": save(concrete(rng, 0.38, (0.95, 0.95, 1.0), ground=True), "cp_roof", outdir),
        "asphalt": save(asphalt(rng), "cp_asphalt", outdir),
        "led": save(solid((0.0, 0.9, 1.0)), "cp_led", outdir),
        "beacon": save(solid((1.0, 0.05, 0.05)), "cp_beacon", outdir),
        "metal": save(to_rgba(concrete_value(rng, 0.16, seams=False), (0.9, 0.95, 1.05)), "cp_metal", outdir),
    }
    for i, col in enumerate(ACCENTS):
        imgs[f"neon{i + 1}"] = save(solid(col), f"cp_neon{i + 1}", outdir)
    # window glow: 1 = warm white, 2..7 = soft accent tints
    imgs["glow1"] = save(solid((1.0, 0.82, 0.6)), "cp_glow1", outdir)
    for i, col in enumerate(ACCENTS):
        soft = tuple(0.55 * c + 0.45 for c in col)
        imgs[f"glow{i + 2}"] = save(solid(soft), f"cp_glow{i + 2}", outdir)
    for key, palette in FACADE_VARIANTS.items():
        imgs[f"facade_{key}"] = save(facade(rng, palette), f"cp_facade_{key}", outdir)
    return imgs
