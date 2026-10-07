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

FACADE_VARIANTS = {
    "warm": [(1.0, 0.78, 0.45), (1.0, 0.9, 0.7), (1.0, 0.65, 0.3)],
    "cyan": [(0.55, 0.9, 1.0), (0.2, 0.85, 1.0), (1.0, 0.85, 0.6)],
    "pink": [(1.0, 0.4, 0.8), (0.75, 0.5, 1.0), (1.0, 0.85, 0.6)],
}


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


def facade(rng, palette, lit_chance=0.45):
    img = to_rgba(concrete_value(rng, tone=0.32, seams=False), (0.95, 0.95, 1.0))
    cols, rows = 4, 2
    cw, ch = N // cols, N // rows
    for fy in range(rows):
        y0 = fy * ch
        # floor slab: lighter band with a shadow line above it
        slab = int(ch * 0.12)
        img[y0:y0 + slab, :, :3] *= 1.25
        img[y0 + slab:y0 + slab + 4, :, :3] *= 0.45
        for fx in range(cols):
            x0 = fx * cw
            wx0, wx1 = x0 + int(cw * 0.14), x0 + int(cw * 0.86)
            wy0, wy1 = y0 + int(ch * 0.2), y0 + int(ch * 0.9)
            img[wy0:wy1, wx0:wx1, :3] = 0.07  # frame
            gx0, gx1, gy0, gy1 = wx0 + 7, wx1 - 7, wy0 + 7, wy1 - 7
            h = gy1 - gy0
            t = np.linspace(0.0, 1.0, h)[:, None, None]  # 0 bottom .. 1 top
            if rng.random() < lit_chance:
                col = np.array(palette[rng.integers(len(palette))])
                glass = col * (0.75 + 0.25 * t)
                glass = np.broadcast_to(glass, (h, gx1 - gx0, 3)).copy()
                if rng.random() < 0.5:  # blinds
                    glass[::14, :, :] *= 0.7
            else:
                diag = np.linspace(0.0, 1.0, gx1 - gx0)[None, :, None]
                refl = 0.035 + 0.09 * np.clip(t * 0.7 + diag * 0.5 - 0.3, 0, 1)
                glass = refl * np.array((0.6, 0.75, 1.0))
                glass = np.broadcast_to(glass, (h, gx1 - gx0, 3)).copy()
            img[gy0:gy1, gx0:gx1, :3] = glass
            mid = (gx0 + gx1) // 2
            img[gy0:gy1, mid - 2:mid + 2, :3] = 0.07  # mullion
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
    }
    for key, palette in FACADE_VARIANTS.items():
        imgs[f"facade_{key}"] = save(facade(rng, palette), f"cp_facade_{key}", outdir)
    return imgs
