"""HEX! Cyberpunk City v2 - original advertisement artwork for the screen meshes.

Every ad is drawn from scratch (fictional brands, original layouts) in one of the
screen formats used by cp2_build.py:

    W  2:1   1024x512   facade / rooftop billboards
    X  4:1   1024x256   banners, tickers, canopy screens
    P  8:3   1024x384   curved corner wraps
    T  1:2   512x1024   tall facade screens
    S  1:4   256x1024   vertical holo strips / blades
    Q  1:1   1024x1024  square screens

Output: export/textures/AD_<Name>.png (1024 px max, the largest size Roblox keeps).

    python3 blender/cp2_ads.py export/textures
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else "export/textures"
SS = 2  # supersampling

FONT_JP = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
FONT_JP2 = "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"
FONT_BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FONT_BOLD = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FONT_THIN = "/usr/share/fonts/opentype/inter/InterDisplay-Light.otf"
FONT_ITAL = "/usr/share/fonts/opentype/inter/InterDisplay-BlackItalic.otf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

SIZES = {"W": (1024, 512), "X": (1024, 256), "P": (1024, 384), "T": (512, 1024), "S": (256, 1024), "Q": (1024, 1024)}

MAG, CYN, VIO, BLU, RED = (255, 30, 170), (0, 230, 255), (150, 50, 255), (40, 100, 255), (255, 40, 60)
PNK, YEL, WHT, ORG = (255, 120, 210), (255, 225, 60), (240, 245, 255), (255, 140, 30)


def font(path, px):
    return ImageFont.truetype(path, int(px))


class Ad:
    def __init__(self, fmt, seed):
        self.fmt = fmt
        w, h = SIZES[fmt]
        self.W, self.H = w * SS, h * SS
        self.img = Image.new("RGB", (self.W, self.H), (0, 0, 0))
        self.rng = np.random.default_rng(seed)

    # coordinates are fractions of the canvas
    def p(self, x, y):
        return (x * self.W, y * self.H)

    def px(self, v, axis="h"):
        return v * (self.H if axis == "h" else self.W)

    # ---------------------------------------------------------------- backgrounds
    def grad(self, stops, angle=90):
        """Linear gradient; angle 90 = top->bottom."""
        yy, xx = np.mgrid[0:self.H, 0:self.W].astype(float)
        a = math.radians(angle)
        t = (xx / self.W) * math.cos(a) + (yy / self.H) * math.sin(a)
        t = (t - t.min()) / (t.max() - t.min() + 1e-9)
        pos = [s[0] for s in stops]
        out = np.zeros((self.H, self.W, 3))
        for c in range(3):
            out[..., c] = np.interp(t, pos, [s[1][c] for s in stops])
        self.img = Image.fromarray(out.astype(np.uint8))

    def radial(self, cx, cy, r, inner, outer=None, strength=1.0):
        yy, xx = np.mgrid[0:self.H, 0:self.W].astype(float)
        d = np.sqrt((xx - cx * self.W) ** 2 + (yy - cy * self.H) ** 2) / (r * max(self.W, self.H))
        k = np.clip(1 - d, 0, 1) ** 1.6 * strength
        base = np.asarray(self.img).astype(float)
        col = np.array(inner, float)
        out = base * (1 - k[..., None]) + col * k[..., None] if outer is None else base + col * k[..., None]
        self.img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

    # ---------------------------------------------------------------- layers
    def layer(self):
        L = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        return L, ImageDraw.Draw(L)

    def put(self, L, glow=0.0, glow_mul=1.0, mode="normal"):
        """Composite an RGBA layer; glow = blur radius as fraction of height (additive)."""
        if glow > 0:
            g = L.filter(ImageFilter.GaussianBlur(glow * self.H))
            ga = np.asarray(g).astype(float)
            add = ga[..., :3] * (ga[..., 3:4] / 255.0) * glow_mul
            base = np.asarray(self.img).astype(float) + add
            self.img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
        if mode == "add":
            la = np.asarray(L).astype(float)
            base = np.asarray(self.img).astype(float) + la[..., :3] * (la[..., 3:4] / 255.0)
            self.img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
        else:
            self.img.paste(L, (0, 0), L)

    def text(self, s, fpath, size, x, y, fill, anchor="mm", glow=0.0, stroke=0, stroke_fill=None, glow_mul=1.2,
             spacing=0):
        L, d = self.layer()
        f = font(fpath, self.H * size)
        if spacing:
            # manual letter spacing
            widths = [d.textlength(ch, font=f) for ch in s]
            total = sum(widths) + spacing * self.H * (len(s) - 1)
            cx, cy = self.p(x, y)
            sx = cx - total / 2 if anchor[0] == "m" else (cx if anchor[0] == "l" else cx - total)
            for ch, w in zip(s, widths):
                d.text((sx, cy), ch, font=f, fill=fill, anchor="l" + anchor[1], stroke_width=int(stroke * self.H),
                       stroke_fill=stroke_fill)
                sx += w + spacing * self.H
        else:
            d.text(self.p(x, y), s, font=f, fill=fill, anchor=anchor, stroke_width=int(stroke * self.H),
                   stroke_fill=stroke_fill)
        self.put(L, glow, glow_mul)
        return L

    def vtext(self, s, fpath, size, x, y0, fill, step=1.0, glow=0.0):
        L, d = self.layer()
        f = font(fpath, self.H * size)
        for i, ch in enumerate(s):
            d.text(self.p(x, y0 + i * size * step), ch, font=f, fill=fill, anchor="mt")
        self.put(L, glow)

    def poly(self, pts, fill=None, outline=None, width=0.0, glow=0.0, glow_mul=1.0):
        L, d = self.layer()
        P = [self.p(*q) for q in pts]
        d.polygon(P, fill=fill)
        if outline:
            d.line(P + [P[0]], fill=outline, width=max(1, int(width * self.H)), joint="curve")
        self.put(L, glow, glow_mul)

    def line(self, pts, color, width, glow=0.0, glow_mul=1.0):
        L, d = self.layer()
        d.line([self.p(*q) for q in pts], fill=color, width=max(1, int(width * self.H)), joint="curve")
        self.put(L, glow, glow_mul)

    def circle(self, cx, cy, r, fill=None, outline=None, width=0.0, glow=0.0, axis="h"):
        L, d = self.layer()
        R = r * (self.H if axis == "h" else self.W)
        X, Y = self.p(cx, cy)
        d.ellipse([X - R, Y - R, X + R, Y + R], fill=fill, outline=outline, width=max(1, int(width * self.H)) if outline else 0)
        self.put(L, glow)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=0.0, glow=0.0, radius=0.0):
        L, d = self.layer()
        box = [*self.p(x0, y0), *self.p(x1, y1)]
        if radius:
            d.rounded_rectangle(box, radius=radius * self.H, fill=fill, outline=outline,
                                width=max(1, int(width * self.H)) if outline else 0)
        else:
            d.rectangle(box, fill=fill, outline=outline, width=max(1, int(width * self.H)) if outline else 0)
        self.put(L, glow)

    # ---------------------------------------------------------------- motifs
    def hud_corners(self, color, inset=0.04, ln=0.08, width=0.008):
        ix, iy = inset * self.H / self.W, inset
        lx, ly = ln * self.H / self.W, ln
        for (x, y, sx, sy) in ((ix, iy, 1, 1), (1 - ix, iy, -1, 1), (ix, 1 - iy, 1, -1), (1 - ix, 1 - iy, -1, -1)):
            self.line([(x, y + sy * ly), (x, y), (x + sx * lx, y)], color, width, glow=0.01)

    def scan_grid(self, color, spacing=0.06, alpha=40, horizon=None):
        L, d = self.layer()
        c = (*color, alpha)
        n = int(1 / spacing) + 2
        for i in range(n):
            y = i * spacing * self.H
            d.line([(0, y), (self.W, y)], fill=c, width=SS)
        for i in range(int(self.W / (spacing * self.H)) + 2):
            x = i * spacing * self.H
            d.line([(x, 0), (x, self.H)], fill=c, width=SS)
        self.put(L)

    def perspective_grid(self, color, horizon=0.6, lines=18, alpha=200):
        L, d = self.layer()
        hy = horizon * self.H
        for i in range(-lines, lines + 1):
            d.line([(self.W / 2, hy), (self.W / 2 + i * self.W / lines * 1.6, self.H)], fill=(*color, alpha), width=2 * SS)
        for k in range(1, 12):
            t = (k / 12) ** 2.2
            y = hy + (self.H - hy) * t
            d.line([(0, y), (self.W, y)], fill=(*color, alpha), width=2 * SS)
        self.put(L, glow=0.01)

    def stripes(self, color, angle=-30, width=0.05, gap=0.05, alpha=60, region=None):
        L, d = self.layer()
        diag = math.hypot(self.W, self.H)
        step = (width + gap) * self.H
        a = math.radians(angle)
        dx, dy = math.cos(a), math.sin(a)
        nx, ny = -dy, dx
        for i in range(-int(diag / step) - 2, int(diag / step) + 2):
            ox, oy = self.W / 2 + nx * i * step, self.H / 2 + ny * i * step
            w = width * self.H
            pts = [(ox - dx * diag, oy - dy * diag), (ox + dx * diag, oy + dy * diag),
                   (ox + dx * diag + nx * w, oy + dy * diag + ny * w), (ox - dx * diag + nx * w, oy - dy * diag + ny * w)]
            d.polygon(pts, fill=(*color, alpha))
        if region:
            m = Image.new("L", (self.W, self.H), 0)
            ImageDraw.Draw(m).rectangle([*self.p(*region[:2]), *self.p(*region[2:])], fill=255)
            L.putalpha(ImageChops.multiply(L.getchannel("A"), m))
        self.put(L)

    def halftone(self, color, cx, cy, r, cell=0.025, alpha=255):
        L, d = self.layer()
        c = cell * self.H
        for gy in np.arange(0, self.H, c):
            for gx in np.arange(0, self.W, c):
                dist = math.hypot(gx - cx * self.W, gy - cy * self.H) / (r * self.H)
                s = max(0.0, 1 - dist) * c * 0.48
                if s > 0.6:
                    d.ellipse([gx - s, gy - s, gx + s, gy + s], fill=(*color, alpha))
        self.put(L)

    def barcode(self, x0, y0, x1, y1, color):
        L, d = self.layer()
        X0, Y0 = self.p(x0, y0)
        X1, Y1 = self.p(x1, y1)
        x = X0
        while x < X1:
            w = self.rng.integers(1, 5) * SS
            if self.rng.random() < 0.6:
                d.rectangle([x, Y0, min(X1, x + w), Y1], fill=color)
            x += w + SS
        self.put(L)

    def glitch(self, bands=6, maxshift=0.05):
        a = np.asarray(self.img).copy()
        for _ in range(bands):
            y0 = int(self.rng.integers(0, self.H - 10))
            hh = int(self.rng.integers(4, max(6, self.H // 25)))
            sh = int(self.rng.uniform(-maxshift, maxshift) * self.W)
            a[y0:y0 + hh] = np.roll(a[y0:y0 + hh], sh, axis=1)
        self.img = Image.fromarray(a)

    def chroma(self, shift=0.006):
        r, g, b = self.img.split()
        s = int(shift * self.W)
        r = ImageChops.offset(r, s, 0)
        b = ImageChops.offset(b, -s, 0)
        self.img = Image.merge("RGB", (r, g, b))

    def finish(self, led=True, vignette=0.25):
        img = self.img.resize((self.W // SS, self.H // SS), Image.LANCZOS)
        a = np.asarray(img).astype(float)
        h, w = a.shape[:2]
        if led:  # subtle LED pixel grid + scanlines
            yy, xx = np.mgrid[0:h, 0:w]
            a *= (1 - 0.10 * ((yy % 3) == 2))[..., None]
            a *= (1 - 0.06 * ((xx % 3) == 2))[..., None]
        if vignette:
            yy, xx = np.mgrid[0:h, 0:w].astype(float)
            v = 1 - vignette * (((xx / w - 0.5) * 2) ** 4 + ((yy / h - 0.5) * 2) ** 4) / 2
            a *= v[..., None]
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


# =============================================================================== ads
ADS = {}


def ad(name, fmt):
    def deco(fn):
        ADS[name] = (fmt, fn)
        return fn
    return deco


@ad("HexLeague", "W")
def hex_league(a):
    a.grad([(0, (40, 0, 60)), (0.55, (150, 10, 90)), (1, (255, 90, 30))], angle=20)
    a.stripes((255, 255, 255), angle=-25, width=0.02, gap=0.12, alpha=25)
    # basketball
    cx, cy, r = 0.73, 0.5, 0.36
    a.circle(cx, cy, r, fill=(255, 120, 30), glow=0.04)
    a.radial(cx - 0.03, cy - 0.15, 0.15, (255, 220, 160), strength=0.5)
    L, d = a.layer()
    X, Y = a.p(cx, cy)
    R = r * a.H
    w = int(0.012 * a.H)
    d.line([(X - R, Y), (X + R, Y)], fill=(30, 10, 10), width=w)
    d.line([(X, Y - R), (X, Y + R)], fill=(30, 10, 10), width=w)
    d.arc([X - R * 1.6, Y - R, X - R * 0.25, Y + R], -60, 60, fill=(30, 10, 10), width=w)
    d.arc([X + R * 0.25, Y - R, X + R * 1.6, Y + R], 120, 240, fill=(30, 10, 10), width=w)
    a.put(L)
    # dunking player silhouette
    sil = [(0.50, 0.95), (0.53, 0.70), (0.50, 0.55), (0.53, 0.40), (0.58, 0.30), (0.62, 0.12), (0.64, 0.10),
           (0.62, 0.30), (0.60, 0.42), (0.62, 0.55), (0.60, 0.72), (0.57, 0.95)]
    a.poly([(x - 0.12, y) for x, y in sil], fill=(15, 0, 25))
    a.circle(0.475, 0.24, 0.05, fill=(15, 0, 25))
    a.text("HEX LEAGUE", FONT_ITAL, 0.15, 0.04, 0.3, WHT, anchor="lm", glow=0.02)
    a.text("FINALS 2099", FONT_BLACK, 0.11, 0.045, 0.52, (255, 230, 120), anchor="lm")
    a.text("バスケ決勝  ·  TONIGHT 21:00  ·  PLAZA COURT", FONT_JP, 0.055, 0.045, 0.68, WHT, anchor="lm")
    a.rect(0.045, 0.78, 0.33, 0.9, fill=(0, 230, 255), glow=0.02)
    a.text("WATCH LIVE ▶", FONT_BOLD, 0.06, 0.19, 0.84, (10, 0, 30))


@ad("DenkiCola", "T")
def denki_cola(a):
    a.grad([(0, (0, 10, 40)), (0.6, (10, 0, 60)), (1, (60, 0, 80))])
    a.radial(0.5, 0.45, 0.6, (0, 120, 255), strength=0.6)
    for i in range(7):  # lightning bolts
        x = a.rng.uniform(0.05, 0.95)
        pts = [(x, 0.0)]
        y = 0.0
        while y < 1:
            y += a.rng.uniform(0.05, 0.12)
            x += a.rng.uniform(-0.08, 0.08)
            pts.append((x, y))
        a.line(pts, (120, 220, 255), 0.003, glow=0.01, glow_mul=1.5)
    # can
    a.rect(0.24, 0.2, 0.76, 0.78, fill=(230, 20, 140), radius=0.04, glow=0.03)
    a.rect(0.24, 0.2, 0.40, 0.78, fill=(255, 90, 190), radius=0.04)
    a.rect(0.27, 0.17, 0.73, 0.21, fill=(190, 195, 210), radius=0.015)
    a.rect(0.27, 0.77, 0.73, 0.81, fill=(160, 165, 180), radius=0.015)
    a.vtext("電気", FONT_JP, 0.14, 0.5, 0.25, WHT, glow=0.0)
    a.rect(0.24, 0.56, 0.76, 0.66, fill=(0, 230, 255))
    a.text("DENKI", FONT_BLACK, 0.06, 0.5, 0.61, (20, 0, 40))
    a.text("COLA", FONT_BLACK, 0.05, 0.5, 0.71, WHT)
    a.text("⚡ 300% VOLTAGE", FONT_BOLD, 0.035, 0.5, 0.88, (0, 230, 255), glow=0.01)
    a.text("限定 NEON FLAVOR", FONT_JP, 0.03, 0.5, 0.94, WHT)


@ad("YumeOptics", "W")
def yume_optics(a):
    a.grad([(0, (5, 0, 20)), (1, (40, 0, 70))], angle=0)
    a.scan_grid((120, 60, 255), 0.08, 30)
    cx, cy = 0.28, 0.5
    for k, r in enumerate([0.44, 0.36, 0.29, 0.22, 0.15]):
        col = [CYN, VIO, MAG, CYN, WHT][k]
        a.circle(cx, cy, r, outline=col, width=0.012 if k % 2 else 0.006, glow=0.015)
    a.circle(cx, cy, 0.12, fill=(10, 0, 30))
    a.circle(cx, cy, 0.06, fill=(0, 230, 255), glow=0.05)
    for ang in range(0, 360, 15):
        t = math.radians(ang)
        a.line([(cx + math.cos(t) * 0.18 * a.H / a.W, cy + math.sin(t) * 0.18),
                (cx + math.cos(t) * 0.27 * a.H / a.W, cy + math.sin(t) * 0.27)], (180, 120, 255), 0.004)
    a.line([(0.47, 0.5), (0.53, 0.5), (0.56, 0.28), (0.95, 0.28)], CYN, 0.004, glow=0.01)
    a.text("YUME OPTICS", FONT_BLACK, 0.13, 0.56, 0.42, WHT, anchor="lm", glow=0.015)
    a.text("夢の目  —  SEE MORE THAN REALITY", FONT_JP, 0.055, 0.56, 0.58, (200, 170, 255), anchor="lm")
    a.text("IRIS-9 IMPLANT  ¥ 299,800", FONT_MONO, 0.05, 0.56, 0.72, CYN, anchor="lm")
    a.hud_corners(CYN)


@ad("NeonNoodle", "Q")
def neon_noodle(a):
    a.grad([(0, (60, 0, 20)), (1, (10, 0, 30))])
    a.halftone((255, 40, 80), 0.5, 0.6, 0.6, 0.03, 120)
    # bowl
    a.poly([(0.18, 0.55), (0.82, 0.55), (0.72, 0.82), (0.28, 0.82)], fill=(230, 30, 60), glow=0.03)
    a.rect(0.16, 0.52, 0.84, 0.57, fill=(255, 210, 220))
    for i in range(6):
        y = 0.6 + i * 0.03
        a.line([(0.24 + i * 0.01, y), (0.76 - i * 0.01, y)], (255, 200, 120), 0.006)
    a.poly([(0.36, 0.86), (0.64, 0.86), (0.6, 0.82), (0.4, 0.82)], fill=(180, 20, 40))
    for k in range(3):  # steam
        x = 0.38 + k * 0.12
        pts = [(x + 0.03 * math.sin(t * 0.6), 0.5 - t * 0.03) for t in range(10)]
        a.line(pts, (255, 220, 255), 0.01, glow=0.02)
    a.line([(0.62, 0.2), (0.48, 0.55)], (240, 200, 160), 0.012)  # chopsticks
    a.line([(0.68, 0.22), (0.52, 0.55)], (240, 200, 160), 0.012)
    a.text("ネオン麺", FONT_JP, 0.17, 0.5, 0.13, WHT, glow=0.02, stroke=0.006, stroke_fill=(255, 30, 120))
    a.text("NEON NOODLE · 24H", FONT_BLACK, 0.055, 0.5, 0.93, (255, 220, 120), glow=0.01)


@ad("KoiAir", "X")
def koi_air(a):
    a.grad([(0, (0, 20, 70)), (1, (0, 120, 220))], angle=0)
    a.stripes((255, 255, 255), angle=0, width=0.01, gap=0.09, alpha=25)
    car = [(0.62, 0.62), (0.66, 0.42), (0.74, 0.32), (0.86, 0.3), (0.95, 0.42), (0.97, 0.6), (0.9, 0.7), (0.66, 0.7)]
    a.poly(car, fill=(10, 10, 30), outline=CYN, width=0.02, glow=0.03)
    a.poly([(0.75, 0.36), (0.85, 0.34), (0.9, 0.44), (0.72, 0.46)], fill=(0, 200, 255))
    a.line([(0.2, 0.6), (0.6, 0.62)], (255, 60, 180), 0.03, glow=0.05)
    a.text("KOI AIR", FONT_ITAL, 0.42, 0.03, 0.45, WHT, anchor="lm", glow=0.02)
    a.text("SKY TAXI 24H  ·  空のタクシー", FONT_JP, 0.15, 0.03, 0.82, (180, 240, 255), anchor="lm")


@ad("SynthFM", "W")
def synth_fm(a):
    a.grad([(0, (20, 0, 50)), (0.6, (120, 0, 120)), (1, (20, 0, 40))])
    # sun
    L, d = a.layer()
    X, Y = a.p(0.5, 0.55)
    R = 0.36 * a.H
    for i in range(int(R * 2)):
        yy = Y - R + i
        t = i / (2 * R)
        if yy > Y - R * 0.1 and int((yy - (Y - R * 0.1)) / (0.03 * a.H)) % 2 == 1:
            continue
        half = math.sqrt(max(0, R * R - (yy - Y) ** 2))
        col = (255, int(220 - 180 * t), int(80 + 100 * t), 255)
        d.line([(X - half, yy), (X + half, yy)], fill=col)
    a.put(L, glow=0.05)
    a.rect(0, 0.62, 1, 1, fill=(15, 0, 30))
    a.perspective_grid((255, 40, 200), horizon=0.62)
    a.text("SYNTH FM", FONT_ITAL, 0.2, 0.5, 0.2, WHT, glow=0.02, stroke=0.006, stroke_fill=(0, 230, 255))
    a.text("88.7", FONT_BLACK, 0.12, 0.88, 0.85, CYN, glow=0.02)
    a.text("夜のラジオ", FONT_JP, 0.07, 0.12, 0.85, PNK, glow=0.01)


@ad("OkamiArms", "T")
def okami(a):
    a.grad([(0, (30, 0, 0)), (1, (0, 0, 0))])
    a.stripes((255, 30, 40), angle=-60, width=0.03, gap=0.04, alpha=40, region=(0, 0.7, 1, 1))
    # geometric wolf head
    pts = [(0.5, 0.62), (0.3, 0.45), (0.22, 0.18), (0.36, 0.3), (0.5, 0.26), (0.64, 0.3), (0.78, 0.18), (0.7, 0.45)]
    a.poly(pts, fill=(25, 0, 0), outline=RED, width=0.006, glow=0.02)
    for tri in ([(0.5, 0.26), (0.36, 0.3), (0.42, 0.4)], [(0.5, 0.26), (0.64, 0.3), (0.58, 0.4)],
                [(0.42, 0.4), (0.5, 0.62), (0.5, 0.45)], [(0.58, 0.4), (0.5, 0.62), (0.5, 0.45)]):
        a.poly(tri, outline=(255, 80, 80), width=0.003)
    a.poly([(0.38, 0.38), (0.45, 0.4), (0.4, 0.41)], fill=(255, 40, 40), glow=0.03)
    a.poly([(0.62, 0.38), (0.55, 0.4), (0.6, 0.41)], fill=(255, 40, 40), glow=0.03)
    a.text("OKAMI", FONT_BLACK, 0.1, 0.5, 0.72, WHT, glow=0.01)
    a.text("ARMS", FONT_THIN, 0.06, 0.5, 0.8, (255, 80, 80), spacing=0.03)
    a.text("狼 · PERSONAL DEFENSE", FONT_JP, 0.025, 0.5, 0.9, (200, 200, 200))


@ad("AikoLive", "T")
def aiko(a):
    a.grad([(0, (255, 60, 180)), (0.5, (120, 30, 220)), (1, (20, 0, 60))])
    for _ in range(40):  # stars
        x, y, r = a.rng.uniform(0, 1), a.rng.uniform(0, 0.7), a.rng.uniform(0.003, 0.01)
        a.circle(x, y, r, fill=(255, 255, 255), glow=0.01)
    # idol silhouette (head, twin tails, shoulders, mic)
    a.circle(0.5, 0.38, 0.09, fill=(30, 0, 50))
    a.poly([(0.42, 0.33), (0.25, 0.6), (0.32, 0.62), (0.44, 0.42)], fill=(30, 0, 50))
    a.poly([(0.58, 0.33), (0.75, 0.6), (0.68, 0.62), (0.56, 0.42)], fill=(30, 0, 50))
    a.poly([(0.3, 0.75), (0.38, 0.52), (0.62, 0.52), (0.7, 0.75)], fill=(30, 0, 50))
    a.line([(0.6, 0.56), (0.66, 0.44)], (200, 200, 220), 0.012)
    a.circle(0.665, 0.435, 0.018, fill=(0, 230, 255), glow=0.02)
    a.rect(0, 0.75, 1, 1, fill=(15, 0, 40))
    a.text("AIKO", FONT_ITAL, 0.11, 0.5, 0.82, WHT, glow=0.02, stroke=0.004, stroke_fill=MAG)
    a.text("夜 LIVE TOUR 2099", FONT_JP, 0.035, 0.5, 0.9, (0, 230, 255), glow=0.01)
    a.text("SOLD OUT 完売", FONT_JP, 0.03, 0.5, 0.95, PNK)


@ad("MiraiBank", "X")
def mirai_bank(a):
    a.grad([(0, (0, 10, 40)), (1, (0, 30, 90))], angle=0)
    L, d = a.layer()  # hex pattern
    s = 0.12 * a.H
    for j in range(12):
        for i in range(40):
            cx = i * s * 1.5
            cy = j * s * math.sqrt(3) + (i % 2) * s * math.sqrt(3) / 2
            pts = [(cx + s * math.cos(math.radians(60 * k)), cy + s * math.sin(math.radians(60 * k))) for k in range(6)]
            d.polygon(pts, outline=(60, 120, 255, 60))
    a.put(L)
    a.poly([(0.06, 0.2), (0.12, 0.2), (0.15, 0.5), (0.12, 0.8), (0.06, 0.8), (0.09, 0.5)], fill=(0, 200, 255), glow=0.05)
    a.text("MIRAI BANK", FONT_BLACK, 0.36, 0.19, 0.42, WHT, anchor="lm")
    a.text("YOUR FUTURE, SECURED.  未来銀行", FONT_JP, 0.14, 0.19, 0.78, (120, 200, 255), anchor="lm")


@ad("SakuraLink", "W")
def sakura_link(a):
    a.grad([(0, (30, 0, 40)), (1, (90, 0, 80))], angle=30)
    nodes = [(a.rng.uniform(0.45, 0.98), a.rng.uniform(0.05, 0.95)) for _ in range(26)]
    for i, n1 in enumerate(nodes):
        for n2 in nodes[i + 1:]:
            if math.dist(n1, n2) < 0.28:
                a.line([n1, n2], (255, 120, 210), 0.003)
    for n in nodes:
        a.circle(*n, 0.012, fill=(255, 160, 230), glow=0.015)
    for _ in range(22):  # petals
        x, y = a.rng.uniform(0, 1), a.rng.uniform(0, 1)
        r = a.rng.uniform(0.01, 0.03)
        a.poly([(x, y - r), (x + r * 0.4, y), (x, y + r), (x - r * 0.4, y)], fill=(255, 170, 220))
    a.text("SAKURA", FONT_BLACK, 0.2, 0.05, 0.3, WHT, anchor="lm", glow=0.015)
    a.text("LINK 6G", FONT_THIN, 0.17, 0.05, 0.52, PNK, anchor="lm", glow=0.01)
    a.text("桜ネット — ALWAYS CONNECTED", FONT_JP, 0.05, 0.05, 0.75, WHT, anchor="lm")
    a.rect(0.05, 0.83, 0.3, 0.86, fill=(0, 230, 255), glow=0.01)


@ad("RyuGames", "Q")
def ryu_games(a):
    a.grad([(0, (10, 0, 0)), (1, (60, 0, 20))])
    a.radial(0.5, 0.45, 0.6, (255, 40, 40), strength=0.35)
    a.text("龍", FONT_JP, 0.78, 0.5, 0.45, (255, 50, 60), glow=0.04, glow_mul=1.4)
    a.glitch(14, 0.07)
    a.chroma(0.008)
    a.rect(0, 0.82, 1, 1, fill=(0, 0, 0))
    a.text("RYU GAMES", FONT_BLACK, 0.09, 0.5, 0.88, WHT, spacing=0.01)
    a.text("新作 DRAGON PROTOCOL — OUT NOW", FONT_JP, 0.035, 0.5, 0.95, (0, 230, 255))


@ad("VoltRunner", "W")
def volt_runner(a):
    a.grad([(0, (0, 0, 20)), (1, (0, 40, 90))], angle=0)
    for i in range(14):
        y = a.rng.uniform(0.2, 0.85)
        a.line([(0, y), (a.rng.uniform(0.3, 0.55), y)], (0, 200, 255), 0.006, glow=0.01)
    shoe = [(0.35, 0.72), (0.38, 0.5), (0.48, 0.45), (0.56, 0.33), (0.66, 0.35), (0.7, 0.5), (0.86, 0.56),
            (0.92, 0.66), (0.9, 0.76), (0.36, 0.78)]
    a.poly(shoe, fill=(235, 240, 255), glow=0.02)
    a.poly([(0.36, 0.72), (0.9, 0.7), (0.9, 0.78), (0.36, 0.79)], fill=(0, 230, 255), glow=0.03)
    a.line([(0.5, 0.55), (0.66, 0.62), (0.82, 0.6)], (255, 30, 170), 0.03)
    a.text("VOLT RUNNER", FONT_ITAL, 0.12, 0.04, 0.14, WHT, anchor="lm")
    a.text("跳べ。 JUMP HIGHER.", FONT_JP, 0.06, 0.04, 0.27, CYN, anchor="lm")
    a.text("¥ 34,900", FONT_BLACK, 0.08, 0.96, 0.14, (255, 30, 170), anchor="rm")


@ad("BladeEdge", "S")
def blade_edge(a):
    a.grad([(0, (0, 0, 0)), (0.5, (60, 0, 10)), (1, (0, 0, 0))])
    a.line([(0.1, 0.95), (0.9, 0.05)], (220, 230, 255), 0.006, glow=0.02, glow_mul=1.5)
    a.line([(0.1, 0.95), (0.25, 0.78)], (255, 40, 60), 0.012)
    a.vtext("刀剣", FONT_JP, 0.12, 0.5, 0.18, (255, 40, 60), glow=0.03)
    a.text("BLADE//EDGE", FONT_BLACK, 0.025, 0.5, 0.06, WHT)
    a.text("PvP 新シーズン", FONT_JP, 0.022, 0.5, 0.93, WHT)


@ad("Tokyo2099", "S")
def tokyo_2099(a):
    a.grad([(0, (255, 0, 140)), (0.5, (80, 0, 200)), (1, (0, 150, 255))])
    a.stripes((0, 0, 0), angle=90, width=0.004, gap=0.01, alpha=70)
    a.vtext("東京", FONT_JP, 0.17, 0.5, 0.08, WHT, glow=0.02)
    a.text("2099", FONT_BLACK, 0.06, 0.5, 0.5, WHT)
    a.vtext("サイバー", FONT_JP, 0.07, 0.5, 0.58, (20, 0, 50))


@ad("NexusAndroids", "T")
def nexus(a):
    a.grad([(0, (230, 240, 255)), (1, (150, 170, 220))])
    a.scan_grid((40, 80, 160), 0.05, 50)
    # robot head
    a.poly([(0.3, 0.2), (0.7, 0.2), (0.78, 0.4), (0.7, 0.62), (0.5, 0.7), (0.3, 0.62), (0.22, 0.4)],
           fill=(240, 245, 255), outline=(40, 60, 100), width=0.004)
    a.poly([(0.3, 0.36), (0.7, 0.36), (0.66, 0.44), (0.34, 0.44)], fill=(10, 20, 40))
    a.rect(0.36, 0.385, 0.46, 0.405, fill=(0, 220, 255), glow=0.02)
    a.rect(0.54, 0.385, 0.64, 0.405, fill=(0, 220, 255), glow=0.02)
    a.line([(0.4, 0.55), (0.6, 0.55)], (40, 60, 100), 0.006)
    a.line([(0.5, 0.2), (0.5, 0.1)], (40, 60, 100), 0.006)
    a.circle(0.5, 0.09, 0.015, fill=(255, 30, 120), glow=0.02)
    a.text("NEXUS", FONT_BLACK, 0.09, 0.5, 0.78, (20, 30, 70))
    a.text("ANDROIDS  ·  家族の一員", FONT_JP, 0.03, 0.5, 0.85, (60, 80, 140))
    a.rect(0.2, 0.9, 0.8, 0.95, fill=(255, 30, 140))
    a.text("RESERVE NOW", FONT_BOLD, 0.03, 0.5, 0.925, WHT)


@ad("NanoMed", "X")
def nano_med(a):
    a.grad([(0, (0, 30, 40)), (1, (0, 10, 30))], angle=0)
    a.poly([(0.05, 0.4), (0.09, 0.4), (0.09, 0.2), (0.13, 0.2), (0.13, 0.4), (0.17, 0.4), (0.17, 0.6), (0.13, 0.6),
            (0.13, 0.8), (0.09, 0.8), (0.09, 0.6), (0.05, 0.6)], fill=(0, 255, 210), glow=0.05)
    pts = [(0.2, 0.5)]
    x = 0.2
    for k in range(16):
        x += 0.026
        pts.append((x, 0.5 + (0.35 if k % 6 == 2 else (-0.3 if k % 6 == 3 else 0))))
    a.line(pts, (0, 255, 210), 0.02, glow=0.02)
    a.text("NANO-MED", FONT_BLACK, 0.3, 0.98, 0.35, WHT, anchor="rm")
    a.text("24H CLINIC · 再生医療", FONT_JP, 0.14, 0.98, 0.74, (0, 255, 210), anchor="rm")


@ad("SushiSpeed", "W")
def sushi(a):
    a.grad([(0, (0, 20, 60)), (1, (0, 0, 20))])
    a.rect(0, 0.0, 1, 0.08, fill=(255, 40, 60))
    a.rect(0, 0.92, 1, 1, fill=(255, 40, 60))
    for i, x in enumerate([0.52, 0.68, 0.84]):
        a.rect(x - 0.07, 0.5, x + 0.07, 0.68, fill=(245, 245, 240), radius=0.05)
        topc = [(255, 120, 70), (230, 30, 50), (255, 200, 40)][i]
        a.rect(x - 0.08, 0.4, x + 0.08, 0.54, fill=topc, radius=0.05, glow=0.01)
        for k in range(3):
            a.line([(x - 0.05 + k * 0.04, 0.42), (x - 0.03 + k * 0.04, 0.52)], (255, 230, 220), 0.008)
    a.text("寿司", FONT_JP, 0.36, 0.2, 0.45, WHT, glow=0.02)
    a.text("SPEED BAR", FONT_BLACK, 0.08, 0.2, 0.75, (255, 220, 60))
    a.text("回転寿司 · DRONE DELIVERY 3 MIN", FONT_JP, 0.04, 0.7, 0.82, WHT)


@ad("Karaoke24", "Q")
def karaoke(a):
    a.grad([(0, (60, 0, 120)), (1, (10, 0, 30))])
    for k in range(8):  # sound waves
        r = 0.12 + k * 0.07
        L, d = a.layer()
        X, Y = a.p(0.5, 0.45)
        R = r * a.H
        col = (255, 40, 200, 220 - k * 22) if k % 2 == 0 else (0, 230, 255, 200 - k * 20)
        d.arc([X - R, Y - R, X + R, Y + R], 200, 340, fill=col, width=int(0.012 * a.H))
        a.put(L, glow=0.01)
    a.rect(0.44, 0.3, 0.56, 0.52, fill=(230, 230, 240), radius=0.06)
    a.rect(0.48, 0.52, 0.52, 0.66, fill=(160, 160, 180))
    a.line([(0.44, 0.38), (0.56, 0.38)], (100, 100, 120), 0.004)
    a.text("カラオケ", FONT_JP, 0.15, 0.5, 0.78, WHT, glow=0.02, stroke=0.005, stroke_fill=MAG)
    a.text("KARAOKE 24H · ALL ROOMS 4D", FONT_BLACK, 0.045, 0.5, 0.9, CYN)


@ad("Titan3", "P")
def titan(a):
    a.grad([(0, (0, 0, 30)), (1, (0, 30, 80))])
    a.radial(0.7, 0.4, 0.5, (255, 40, 60), strength=0.4)
    # mecha silhouette
    m = [(0.62, 0.95), (0.64, 0.6), (0.6, 0.55), (0.6, 0.35), (0.66, 0.25), (0.7, 0.12), (0.76, 0.12), (0.8, 0.25),
         (0.86, 0.35), (0.86, 0.55), (0.82, 0.6), (0.84, 0.95), (0.77, 0.95), (0.74, 0.65), (0.71, 0.65), (0.69, 0.95)]
    a.poly(m, fill=(5, 5, 20), outline=(255, 60, 80), width=0.004, glow=0.02)
    a.poly([(0.86, 0.36), (0.97, 0.3), (0.98, 0.36), (0.86, 0.44)], fill=(5, 5, 20), outline=(255, 60, 80), width=0.004)
    a.rect(0.705, 0.17, 0.755, 0.2, fill=(255, 40, 40), glow=0.03)
    a.text("TITAN III", FONT_BLACK, 0.26, 0.04, 0.38, WHT, anchor="lm", glow=0.01)
    a.text("NOW STREAMING · 配信中", FONT_JP, 0.09, 0.04, 0.62, (255, 90, 110), anchor="lm")
    a.text("EP. 01–12", FONT_MONO, 0.07, 0.04, 0.8, CYN, anchor="lm")


@ad("NewsTicker", "X")
def news(a):
    a.grad([(0, (10, 10, 30)), (1, (10, 10, 30))])
    a.rect(0, 0, 0.18, 1, fill=(255, 30, 60))
    a.text("NEWS", FONT_BLACK, 0.3, 0.09, 0.42, WHT)
    a.text("速報", FONT_JP, 0.22, 0.09, 0.78, WHT)
    a.text("▶ HEX LEAGUE PLAYOFFS TONIGHT  ·  SHIBUYA SKYRAIL +3 LINES  ·  円 ▲ 2.4%", FONT_BOLD, 0.2, 0.2, 0.35,
           WHT, anchor="lm")
    a.text("気温 18°C  ·  雨 40%  ·  NIGHT MARKET OPEN UNTIL 05:00  ·  ", FONT_JP, 0.17, 0.2, 0.72, CYN, anchor="lm")


@ad("Pachinko", "T")
def pachinko(a):
    a.grad([(0, (255, 0, 120)), (0.5, (255, 140, 0)), (1, (80, 0, 160))])
    for _ in range(70):
        x, y = a.rng.uniform(0, 1), a.rng.uniform(0, 1)
        a.circle(x, y, a.rng.uniform(0.01, 0.025), fill=(235, 235, 245))
        a.radial(x - 0.005, y - 0.005, 0.005, (255, 255, 255), strength=0.6)
    a.rect(0.05, 0.36, 0.95, 0.64, fill=(20, 0, 40), radius=0.03, glow=0.03)
    a.text("パチンコ", FONT_JP, 0.085, 0.5, 0.45, (255, 230, 60), glow=0.02)
    a.text("777 JACKPOT", FONT_BLACK, 0.05, 0.5, 0.56, WHT)
    a.text("新台入替", FONT_JP, 0.06, 0.5, 0.9, WHT, stroke=0.004, stroke_fill=(20, 0, 40))


@ad("HoloKoi", "S")
def holo_koi(a):
    a.grad([(0, (0, 10, 30)), (1, (0, 30, 60))])
    a.stripes((0, 230, 255), angle=0, width=0.002, gap=0.006, alpha=40)
    body = [(0.5, 0.15), (0.7, 0.3), (0.72, 0.5), (0.6, 0.7), (0.5, 0.75), (0.4, 0.7), (0.28, 0.5), (0.3, 0.3)]
    a.poly(body, fill=(0, 120, 160), outline=CYN, width=0.004, glow=0.03)
    a.poly([(0.5, 0.75), (0.75, 0.9), (0.5, 0.82), (0.25, 0.9)], fill=(0, 120, 160), outline=CYN, width=0.004)
    for y in np.arange(0.3, 0.7, 0.05):
        a.line([(0.36, y), (0.5, y + 0.03), (0.64, y)], (120, 240, 255), 0.002)
    a.circle(0.43, 0.24, 0.008, fill=WHT, glow=0.01)
    a.circle(0.57, 0.24, 0.008, fill=WHT, glow=0.01)
    a.text("鯉", FONT_JP, 0.08, 0.5, 0.06, CYN, glow=0.02)
    a.text("AQUA·NET", FONT_BOLD, 0.024, 0.5, 0.96, WHT)


@ad("KirinDeck", "W")
def kirin(a):
    a.grad([(0, (5, 0, 20)), (1, (20, 0, 50))])
    L, d = a.layer()  # circuit traces
    for _ in range(60):
        x, y = a.rng.uniform(0, 1) * a.W, a.rng.uniform(0, 1) * a.H
        pts = [(x, y)]
        for _ in range(4):
            if a.rng.random() < 0.5:
                x += a.rng.choice([-1, 1]) * a.rng.uniform(20, 120) * SS
            else:
                y += a.rng.choice([-1, 1]) * a.rng.uniform(20, 80) * SS
            pts.append((x, y))
        d.line(pts, fill=(140, 60, 255, 140), width=2 * SS)
        d.ellipse([x - 4 * SS, y - 4 * SS, x + 4 * SS, y + 4 * SS], fill=(0, 230, 255, 200))
    a.put(L, glow=0.01)
    a.rect(0.58, 0.18, 0.92, 0.82, fill=(15, 15, 30), outline=(0, 230, 255), width=0.008, glow=0.02, radius=0.02)
    a.rect(0.65, 0.3, 0.85, 0.7, fill=(40, 0, 80), outline=(200, 120, 255), width=0.004)
    a.text("K9", FONT_BLACK, 0.18, 0.75, 0.5, (0, 230, 255), glow=0.02)
    a.text("KIRIN", FONT_BLACK, 0.2, 0.05, 0.32, WHT, anchor="lm")
    a.text("CYBERDECK X9", FONT_THIN, 0.09, 0.05, 0.52, (200, 150, 255), anchor="lm")
    a.text("量子コア搭載 · 1.2 PETAFLOP", FONT_JP, 0.05, 0.05, 0.7, CYN, anchor="lm")


@ad("NoirParfum", "T")
def noir(a):
    a.grad([(0, (0, 0, 0)), (1, (50, 0, 40))])
    a.radial(0.5, 0.5, 0.4, (255, 30, 170), strength=0.35)
    a.rect(0.36, 0.36, 0.64, 0.72, fill=(20, 0, 20), outline=(255, 120, 210), width=0.004, radius=0.02, glow=0.02)
    a.rect(0.45, 0.28, 0.55, 0.36, fill=(200, 160, 220))
    a.rect(0.42, 0.22, 0.58, 0.28, fill=(30, 30, 40), radius=0.01)
    a.text("夜", FONT_JP, 0.12, 0.5, 0.54, (255, 120, 210), glow=0.02)
    a.text("N O I R", FONT_THIN, 0.07, 0.5, 0.15, WHT, spacing=0.02)
    a.text("EAU DE NUIT · 東京", FONT_JP, 0.025, 0.5, 0.85, (230, 180, 230))


@ad("AkaiMotors", "W")
def akai(a):
    a.grad([(0, (60, 0, 0)), (1, (0, 0, 0))], angle=0)
    a.stripes((255, 255, 255), angle=-15, width=0.004, gap=0.03, alpha=30)
    bike = [(0.42, 0.68), (0.5, 0.5), (0.62, 0.42), (0.72, 0.42), (0.8, 0.5), (0.9, 0.52), (0.94, 0.62), (0.86, 0.68)]
    a.poly(bike, fill=(230, 20, 30), glow=0.03)
    for cx in (0.47, 0.88):
        a.circle(cx, 0.72, 0.13, outline=(255, 255, 255), width=0.02, glow=0.01)
        a.circle(cx, 0.72, 0.06, fill=(255, 60, 60))
    a.line([(0.66, 0.42), (0.7, 0.3), (0.76, 0.3)], (220, 220, 230), 0.012)
    a.text("AKAI", FONT_ITAL, 0.26, 0.04, 0.3, WHT, anchor="lm", glow=0.02)
    a.text("MOTORS", FONT_THIN, 0.09, 0.04, 0.5, (255, 90, 90), anchor="lm", spacing=0.02)
    a.text("赤い稲妻 · EV-HYPER", FONT_JP, 0.05, 0.04, 0.67, WHT, anchor="lm")


@ad("ScanMe", "Q")
def scan_me(a):
    a.grad([(0, (10, 0, 30)), (1, (0, 10, 40))])
    L, d = a.layer()
    n = 21
    s = 0.6 * a.H / n
    X0, Y0 = a.p(0.2, 0.14)
    for j in range(n):
        for i in range(n):
            finder = (i < 7 and j < 7) or (i >= n - 7 and j < 7) or (i < 7 and j >= n - 7)
            on = a.rng.random() < 0.5
            if finder:
                ii, jj = i % (n - 7) if i >= n - 7 else i, j % (n - 7) if j >= n - 7 else j
                on = ii in (0, 6) or jj in (0, 6) or (2 <= ii <= 4 and 2 <= jj <= 4)
            if on:
                d.rectangle([X0 + i * s, Y0 + j * s, X0 + (i + 1) * s - SS, Y0 + (j + 1) * s - SS], fill=(0, 230, 255, 255))
    a.put(L, glow=0.01)
    a.text("SCAN ME", FONT_BLACK, 0.09, 0.5, 0.84, WHT, glow=0.01)
    a.text("¥0 で始めよう · HEXPAY", FONT_JP, 0.04, 0.5, 0.92, (255, 90, 200))


@ad("PlayHex", "W")
def play_hex(a):
    a.grad([(0, (255, 0, 150)), (0.5, (90, 0, 200)), (1, (0, 180, 255))], angle=0)
    a.halftone((255, 255, 255), 0.85, 0.2, 0.6, 0.035, 60)
    a.rect(0.52, 0.3, 0.92, 0.75, fill=(15, 10, 30), radius=0.18, glow=0.03)
    a.rect(0.58, 0.47, 0.66, 0.5, fill=(240, 240, 255))
    a.rect(0.605, 0.42, 0.635, 0.55, fill=(240, 240, 255))
    for (x, y, c) in ((0.82, 0.42, CYN), (0.86, 0.5, MAG), (0.78, 0.5, YEL), (0.82, 0.58, RED)):
        a.circle(x, y, 0.035, fill=c, glow=0.01)
    a.text("PLAY//HEX", FONT_ITAL, 0.17, 0.04, 0.35, WHT, anchor="lm", glow=0.015)
    a.text("NEXT-GEN CONSOLE", FONT_BOLD, 0.07, 0.04, 0.55, (20, 0, 50), anchor="lm")
    a.text("予約受付中", FONT_JP, 0.08, 0.04, 0.72, WHT, anchor="lm")


@ad("NeoShibuya", "P")
def neo_shibuya(a):
    a.grad([(0, (20, 0, 60)), (0.7, (200, 30, 140)), (1, (255, 120, 60))])
    xs = 0
    L, d = a.layer()
    while xs < a.W:
        w = a.rng.uniform(0.03, 0.08) * a.W
        h = a.rng.uniform(0.3, 0.85) * a.H
        d.rectangle([xs, a.H - h, xs + w, a.H], fill=(10, 0, 30, 255))
        for k in range(int(h / (12 * SS))):
            if a.rng.random() < 0.35:
                yy = a.H - h + k * 12 * SS + 4 * SS
                d.rectangle([xs + 4 * SS, yy, xs + w - 4 * SS, yy + 3 * SS], fill=(255, 200, 140, 160))
        xs += w + a.rng.uniform(0, 6) * SS
    a.put(L)
    a.text("WELCOME TO", FONT_THIN, 0.09, 0.5, 0.14, WHT, spacing=0.02)
    a.text("NEO-SHIBUYA", FONT_BLACK, 0.26, 0.5, 0.38, WHT, glow=0.02, stroke=0.004, stroke_fill=(0, 230, 255))
    a.text("ネオ渋谷へようこそ", FONT_JP, 0.08, 0.5, 0.6, (255, 230, 250), glow=0.01)


@ad("TipOff", "X")
def tip_off(a):
    a.grad([(0, (0, 0, 0)), (1, (20, 0, 40))])
    a.rect(0.01, 0.08, 0.99, 0.92, outline=(255, 120, 30), width=0.03)
    a.text("HEX LEAGUE", FONT_BLACK, 0.2, 0.05, 0.36, (255, 170, 60), anchor="lm")
    a.text("TIP-OFF IN  試合開始", FONT_JP, 0.14, 0.05, 0.66, WHT, anchor="lm")
    a.text("00:21:47", FONT_MONO, 0.55, 0.96, 0.52, (255, 60, 40), anchor="rm", glow=0.03)


@ad("Cyber", "S")
def cyber_strip(a):
    a.grad([(0, (0, 0, 20)), (1, (0, 20, 50))])
    a.rect(0.08, 0.02, 0.92, 0.98, outline=(0, 230, 255), width=0.004, glow=0.01)
    a.vtext("サイバー", FONT_JP, 0.16, 0.5, 0.06, CYN, step=1.05, glow=0.02)
    a.text("CYBER", FONT_BOLD, 0.03, 0.5, 0.82, WHT)
    a.barcode(0.2, 0.86, 0.8, 0.95, (0, 230, 255))


@ad("MatchaPlus", "S")
def matcha(a):
    a.grad([(0, (0, 40, 30)), (1, (0, 10, 20))])
    for _ in range(9):
        x, y = a.rng.uniform(0.15, 0.85), a.rng.uniform(0.45, 0.85)
        r = a.rng.uniform(0.02, 0.05)
        a.poly([(x, y - r), (x + r * 0.5, y), (x, y + r), (x - r * 0.5, y)], fill=(80, 255, 180), glow=0.01)
    a.vtext("緑茶", FONT_JP, 0.17, 0.5, 0.05, (150, 255, 200), glow=0.02)
    a.text("MATCHA+", FONT_BLACK, 0.035, 0.5, 0.9, WHT)
    a.text("FOCUS DRINK", FONT_BOLD, 0.022, 0.5, 0.95, (0, 230, 255))


@ad("RamenIchiban", "X")
def ramen_banner(a):
    a.grad([(0, (180, 0, 30)), (1, (90, 0, 20))], angle=0)
    a.stripes((0, 0, 0), angle=-45, width=0.06, gap=0.06, alpha=50, region=(0.72, 0, 1, 1))
    a.text("ラーメン一番", FONT_JP, 0.6, 0.03, 0.5, WHT, anchor="lm", glow=0.015)
    a.circle(0.86, 0.5, 0.38, fill=(255, 220, 60))
    a.text("¥680", FONT_BLACK, 0.3, 0.86, 0.52, (150, 0, 20))


@ad("MegaSale", "W")
def mega_sale(a):
    a.grad([(0, (255, 0, 140)), (1, (120, 0, 255))], angle=45)
    for i in range(6):  # chevrons
        x = 0.62 + i * 0.07
        a.poly([(x, 0.2), (x + 0.05, 0.5), (x, 0.8), (x + 0.025, 0.8), (x + 0.075, 0.5), (x + 0.025, 0.2)],
               fill=(255, 230, 60) if i % 2 == 0 else (0, 230, 255))
    a.text("MEGA", FONT_ITAL, 0.24, 0.05, 0.28, WHT, anchor="lm", glow=0.015)
    a.text("SALE", FONT_ITAL, 0.24, 0.05, 0.56, (255, 230, 60), anchor="lm", glow=0.015)
    a.text("70% OFF · 大売出し", FONT_JP, 0.08, 0.05, 0.82, WHT, anchor="lm")


@ad("ArashiSec", "T")
def arashi(a):
    a.grad([(0, (0, 10, 50)), (1, (0, 0, 10))])
    a.scan_grid((40, 90, 255), 0.04, 40)
    a.poly([(0.5, 0.12), (0.8, 0.22), (0.76, 0.5), (0.5, 0.68), (0.24, 0.5), (0.2, 0.22)], fill=(10, 30, 90),
           outline=(60, 140, 255), width=0.008, glow=0.03)
    a.text("嵐", FONT_JP, 0.2, 0.5, 0.38, (255, 50, 60), glow=0.02)
    a.text("ARASHI", FONT_BLACK, 0.08, 0.5, 0.78, WHT)
    a.text("SECURITY · 24/7 DRONE PATROL", FONT_BOLD, 0.022, 0.5, 0.85, (120, 170, 255))
    a.text("あなたを守る", FONT_JP, 0.035, 0.5, 0.92, WHT)


@ad("MindUpload", "W")
def mind_upload(a):
    a.grad([(0, (0, 0, 10)), (1, (10, 0, 40))], angle=0)
    prof = [(0.3, 0.95), (0.3, 0.8), (0.24, 0.72), (0.25, 0.62), (0.2, 0.55), (0.24, 0.5), (0.22, 0.42), (0.25, 0.3),
            (0.33, 0.15), (0.45, 0.08), (0.55, 0.12), (0.6, 0.3), (0.58, 0.5), (0.52, 0.65), (0.5, 0.95)]
    a.poly([(x * 0.9, y) for x, y in prof], outline=CYN, width=0.006, glow=0.02)
    L, d = a.layer()
    for _ in range(40):
        x, y = a.rng.uniform(0.25, 0.5) * a.W * 0.9, a.rng.uniform(0.15, 0.6) * a.H
        x2 = x + a.rng.uniform(0.2, 0.6) * a.W
        d.line([(x, y), (x2, y)], fill=(150, 60, 255, 120), width=SS)
    a.put(L, glow=0.005)
    a.text("MIND UPLOAD", FONT_BLACK, 0.13, 0.95, 0.35, WHT, anchor="rm")
    a.text("意識をクラウドへ", FONT_JP, 0.08, 0.95, 0.55, (180, 140, 255), anchor="rm", glow=0.01)
    a.text("ETERNA CORP · BETA", FONT_MONO, 0.05, 0.95, 0.72, CYN, anchor="rm")


@ad("OrbitalResorts", "Q")
def orbital(a):
    a.grad([(0, (0, 0, 20)), (1, (30, 0, 60))])
    for _ in range(120):
        a.circle(a.rng.uniform(0, 1), a.rng.uniform(0, 1), a.rng.uniform(0.001, 0.004), fill=WHT)
    a.circle(0.5, 0.45, 0.25, fill=(80, 40, 200), glow=0.04)
    a.radial(0.42, 0.38, 0.2, (180, 140, 255), strength=0.6)
    L, d = a.layer()
    X, Y = a.p(0.5, 0.45)
    d.ellipse([X - 0.42 * a.H, Y - 0.08 * a.H, X + 0.42 * a.H, Y + 0.08 * a.H], outline=(0, 230, 255, 255),
              width=int(0.012 * a.H))
    a.put(L, glow=0.01)
    a.text("ORBITAL", FONT_BLACK, 0.1, 0.5, 0.8, WHT, spacing=0.01)
    a.text("RESORTS · 宇宙旅行", FONT_JP, 0.045, 0.5, 0.89, (180, 160, 255))


@ad("ShibuyaKanji", "P")
def shibuya_kanji(a):
    a.grad([(0, (0, 0, 0)), (1, (30, 0, 50))])
    a.rect(0.02, 0.06, 0.98, 0.94, outline=(255, 30, 170), width=0.02, glow=0.02)
    a.rect(0.04, 0.12, 0.96, 0.88, outline=(0, 230, 255), width=0.008)
    a.text("渋谷", FONT_JP, 0.7, 0.32, 0.5, WHT, glow=0.03, stroke=0.006, stroke_fill=(255, 30, 170))
    a.text("SHIBUYA", FONT_BLACK, 0.18, 0.78, 0.4, (0, 230, 255))
    a.text("CROSSING 2099", FONT_THIN, 0.1, 0.78, 0.62, WHT, spacing=0.01)


@ad("NekoNet", "T")
def neko(a):
    a.grad([(0, (255, 100, 200)), (1, (90, 0, 160))])
    a.halftone((255, 255, 255), 0.5, 0.4, 0.5, 0.04, 50)
    a.poly([(0.28, 0.25), (0.36, 0.08), (0.44, 0.22)], fill=(255, 255, 255))
    a.poly([(0.56, 0.22), (0.64, 0.08), (0.72, 0.25)], fill=(255, 255, 255))
    a.circle(0.5, 0.32, 0.14, fill=(255, 255, 255))
    a.circle(0.43, 0.3, 0.02, fill=(20, 0, 40))
    a.circle(0.57, 0.3, 0.02, fill=(20, 0, 40))
    a.rect(0.3, 0.42, 0.7, 0.68, fill=(255, 255, 255), radius=0.08)
    a.line([(0.7, 0.45), (0.78, 0.3), (0.74, 0.22)], (255, 255, 255), 0.03)
    a.circle(0.5, 0.52, 0.04, fill=(255, 210, 60))
    a.text("NEKO NET", FONT_BLACK, 0.075, 0.5, 0.8, WHT, glow=0.01)
    a.text("招き猫 · 光回線 10Tbps", FONT_JP, 0.03, 0.5, 0.88, (40, 0, 60))


@ad("HexLeagueTall", "T")
def hex_tall(a):
    a.grad([(0, (255, 100, 20)), (0.5, (200, 0, 120)), (1, (20, 0, 50))])
    a.stripes((0, 0, 0), angle=-70, width=0.02, gap=0.06, alpha=50)
    a.circle(0.5, 0.33, 0.22, fill=(255, 130, 30), glow=0.03)
    L, d = a.layer()
    X, Y = a.p(0.5, 0.33)
    R = 0.22 * a.H
    w = int(0.008 * a.H)
    d.line([(X - R, Y), (X + R, Y)], fill=(40, 10, 10), width=w)
    d.line([(X, Y - R), (X, Y + R)], fill=(40, 10, 10), width=w)
    d.arc([X - R * 1.5, Y - R, X - R * 0.3, Y + R], -60, 60, fill=(40, 10, 10), width=w)
    d.arc([X + R * 0.3, Y - R, X + R * 1.5, Y + R], 120, 240, fill=(40, 10, 10), width=w)
    a.put(L)
    a.text("HEX", FONT_ITAL, 0.13, 0.5, 0.66, WHT, glow=0.02)
    a.text("LEAGUE", FONT_BLACK, 0.06, 0.5, 0.76, (255, 230, 120))
    a.text("決勝戦 · TONIGHT", FONT_JP, 0.035, 0.5, 0.86, WHT)


@ad("DataStream", "X")
def data_stream(a):
    a.grad([(0, (0, 0, 10)), (1, (0, 0, 10))])
    f = font(FONT_MONO, a.H * 0.16)
    L, d = a.layer()
    for row in range(6):
        s = "".join(a.rng.choice(list("01アイウエオカキクケコ#$%<>")) for _ in range(70))
        d.text((0, row * a.H * 0.17), s, font=f, fill=(0, 255, 180, 130 if row % 2 else 220))
    a.put(L, glow=0.01)
    a.rect(0.3, 0.2, 0.7, 0.8, fill=(0, 0, 10), outline=(0, 255, 180), width=0.04)
    a.text("SYSTEM//ONLINE", FONT_MONO, 0.3, 0.5, 0.5, (0, 255, 180), glow=0.02)


@ad("HoloDancer", "S")
def holo_dancer(a):
    a.grad([(0, (40, 0, 80)), (1, (0, 0, 20))])
    a.stripes((180, 100, 255), angle=0, width=0.002, gap=0.008, alpha=50)
    fig = [(0.5, 0.2), (0.56, 0.25), (0.75, 0.18), (0.78, 0.2), (0.6, 0.3), (0.58, 0.45), (0.7, 0.62), (0.66, 0.64),
           (0.52, 0.5), (0.42, 0.66), (0.36, 0.64), (0.44, 0.45), (0.42, 0.3), (0.25, 0.36), (0.24, 0.33), (0.44, 0.25)]
    a.poly(fig, fill=(150, 60, 255), outline=(230, 200, 255), width=0.003, glow=0.04)
    a.circle(0.5, 0.15, 0.03, fill=(150, 60, 255), glow=0.02)
    a.text("ダンス", FONT_JP, 0.05, 0.5, 0.8, WHT, glow=0.01)
    a.text("CLUB VOID", FONT_BLACK, 0.028, 0.5, 0.88, (0, 230, 255))
    a.text("B2F · 23:00–", FONT_BOLD, 0.022, 0.5, 0.93, WHT)


@ad("CourtKings", "Q")
def court_kings(a):
    a.grad([(0, (10, 0, 40)), (1, (60, 0, 80))])
    # top-down court lines
    a.rect(0.12, 0.1, 0.88, 0.62, outline=(255, 140, 40), width=0.01, glow=0.01)
    a.line([(0.5, 0.1), (0.5, 0.62)], (255, 140, 40), 0.008)
    a.circle(0.5, 0.36, 0.08, outline=(255, 140, 40), width=0.008)
    for x in (0.12, 0.88):
        L, d = a.layer()
        X, Y = a.p(x, 0.36)
        R = 0.2 * a.H
        d.arc([X - R, Y - R, X + R, Y + R], -90 if x < 0.5 else 90, 90 if x < 0.5 else 270, fill=(255, 140, 40, 255),
              width=int(0.008 * a.H))
        a.put(L, glow=0.01)
    a.circle(0.62, 0.3, 0.03, fill=(255, 130, 30), glow=0.03)
    a.text("COURT KINGS", FONT_ITAL, 0.11, 0.5, 0.74, WHT, glow=0.015)
    a.text("3v3 ストリート大会 · HEX PLAZA", FONT_JP, 0.04, 0.5, 0.84, (0, 230, 255))
    a.text("ENTRY ¥0", FONT_BLACK, 0.05, 0.5, 0.92, (255, 230, 60))


@ad("KitsuneMask", "Q")
def kitsune(a):
    a.grad([(0, (40, 0, 30)), (1, (0, 0, 20))])
    a.radial(0.5, 0.42, 0.45, (255, 40, 120), strength=0.35)
    a.poly([(0.5, 0.72), (0.28, 0.48), (0.26, 0.14), (0.4, 0.3), (0.5, 0.28), (0.6, 0.3), (0.74, 0.14),
            (0.72, 0.48)], fill=(240, 240, 250), glow=0.02)
    a.poly([(0.3, 0.2), (0.38, 0.32), (0.32, 0.36)], fill=(255, 40, 80))
    a.poly([(0.7, 0.2), (0.62, 0.32), (0.68, 0.36)], fill=(255, 40, 80))
    a.line([(0.36, 0.44), (0.45, 0.47)], (255, 30, 60), 0.012)
    a.line([(0.64, 0.44), (0.55, 0.47)], (255, 30, 60), 0.012)
    a.poly([(0.47, 0.62), (0.53, 0.62), (0.5, 0.67)], fill=(30, 0, 30))
    a.text("狐", FONT_JP, 0.12, 0.84, 0.82, (255, 60, 120), glow=0.02)
    a.text("KITSUNE", FONT_BLACK, 0.08, 0.38, 0.82, WHT)
    a.text("STREAMWEAR · 新作", FONT_JP, 0.035, 0.38, 0.9, (255, 170, 220))


@ad("Hanabi", "Q")
def hanabi(a):
    a.grad([(0, (0, 0, 20)), (1, (30, 0, 50))])
    for (cx, cy, col) in ((0.3, 0.3, MAG), (0.68, 0.24, CYN), (0.5, 0.48, YEL), (0.8, 0.5, VIO)):
        for k in range(28):
            t = 2 * math.pi * k / 28
            r = a.rng.uniform(0.12, 0.2)
            a.line([(cx + 0.03 * math.cos(t), cy + 0.03 * math.sin(t)), (cx + r * math.cos(t), cy + r * math.sin(t))],
                   col, 0.004, glow=0.006)
    a.text("花火大会", FONT_JP, 0.14, 0.5, 0.78, WHT, glow=0.02, stroke=0.004, stroke_fill=MAG)
    a.text("SHIBUYA SKY FESTIVAL · 21:00", FONT_BOLD, 0.04, 0.5, 0.9, (0, 230, 255))


@ad("Onigiri24", "Q")
def onigiri(a):
    a.grad([(0, (0, 40, 90)), (1, (0, 10, 40))])
    a.stripes((255, 255, 255), angle=-30, width=0.01, gap=0.05, alpha=25)
    for i, (x, y) in enumerate(((0.3, 0.42), (0.55, 0.36), (0.75, 0.46))):
        a.poly([(x, y - 0.16), (x + 0.14, y + 0.1), (x - 0.14, y + 0.1)], fill=(250, 250, 245), glow=0.01)
        a.rect(x - 0.07, y + 0.0, x + 0.07, y + 0.1, fill=(20, 30, 20))
    a.text("おにぎり", FONT_JP, 0.13, 0.5, 0.74, WHT, glow=0.01)
    a.text("KONBINI 24 · ¥120", FONT_BLACK, 0.06, 0.5, 0.86, (255, 230, 60))


def main():
    os.makedirs(OUT, exist_ok=True)
    meta = []
    for i, (name, (fmt, fn)) in enumerate(ADS.items()):
        a = Ad(fmt, 7000 + i)
        fn(a)
        img = a.finish()
        img.save(f"{OUT}/AD_{name}.png", optimize=True)
        meta.append((name, fmt, img.size))
    with open(os.path.join(OUT, "..", "ads_index.txt"), "w") as f:
        for m in meta:
            f.write(f"AD_{m[0]}\t{m[1]}\t{m[2][0]}x{m[2][1]}\n")
    print("wrote", len(meta), "ads")


if __name__ == "__main__":
    main()
