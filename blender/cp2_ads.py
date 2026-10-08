"""HEX! Cyberpunk City v2.1 - advertisement artwork (campaign-style redesign).

Each ad follows real campaign conventions instead of clip-art: a brand lockup in a fixed
corner, a strict margin grid, one hero visual (rendered with shading / light, never flat
silhouettes), a big headline, one supporting line and a Japanese line. Fictional brands.

Moderation-safe by construction: no QR codes or barcodes, no prices or currency, no URLs,
handles or "scan / link / pay / live / stream" calls to action, no gambling, no weapons.

Formats (Roblox stores images at most 1024 px):
    W 2:1 1024x512   X 4:1 1024x256   P 8:3 1024x384
    T 1:2 512x1024   S 1:4 256x1024   Q 1:1 1024x1024

    python3 blender/cp2_ads.py export/textures
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else "export/textures"
SS = 2

F_BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
F_BOLD = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
F_SEMI = "/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf"
F_MED = "/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf"
F_LIGHT = "/usr/share/fonts/opentype/inter/InterDisplay-Light.otf"
F_THIN = "/usr/share/fonts/opentype/inter/InterDisplay-Thin.otf"
F_ITAL = "/usr/share/fonts/opentype/inter/InterDisplay-BlackItalic.otf"
F_JP = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"

SIZES = {"W": (1024, 512), "X": (1024, 256), "P": (1024, 384), "T": (512, 1024), "S": (256, 1024), "Q": (1024, 1024)}


def C(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


_FONTS = {}


def font(path, px):
    k = (path, int(px))
    if k not in _FONTS:
        _FONTS[k] = ImageFont.truetype(path, max(4, int(px)))
    return _FONTS[k]


class Poster:
    def __init__(self, fmt, seed):
        self.fmt = fmt
        w, h = SIZES[fmt]
        self.W, self.H = w * SS, h * SS
        self.a = np.zeros((self.H, self.W, 3), float)
        self.rng = np.random.default_rng(seed)
        self.yy, self.xx = np.mgrid[0:self.H, 0:self.W].astype(np.float32)

    @property
    def u(self):
        return min(self.W, self.H)

    def X(self, x):
        return x * self.W

    def Y(self, y):
        return y * self.H

    def _mask(self, L):
        return np.asarray(L, float)[..., None] / 255

    # ------------------------------------------------------------- backgrounds
    def linear(self, stops, angle=90):
        a = math.radians(angle)
        t = (self.xx / self.W) * math.cos(a) + (self.yy / self.H) * math.sin(a)
        t = (t - t.min()) / (t.max() - t.min() + 1e-9)
        pos = [s[0] for s in stops]
        for c in range(3):
            self.a[..., c] = np.interp(t, pos, [C(s[1])[c] for s in stops])

    def blob(self, x, y, r, col, k=1.0):
        """Soft gaussian light (r in fraction of the short side)."""
        d2 = ((self.xx - self.X(x)) ** 2 + (self.yy - self.Y(y)) ** 2) / (r * self.u) ** 2
        self.a += (np.exp(-d2 * 2.2) * k)[..., None] * C(col)

    # ------------------------------------------------------------- light
    def streak(self, x0, y0, x1, y1, col, w=0.004, k=1.0, glow=0.03):
        X0, Y0, X1, Y1 = self.X(x0), self.Y(y0), self.X(x1), self.Y(y1)
        dx, dy = X1 - X0, Y1 - Y0
        L2 = dx * dx + dy * dy + 1e-9
        t = np.clip(((self.xx - X0) * dx + (self.yy - Y0) * dy) / L2, 0, 1)
        d = np.sqrt((self.xx - X0 - t * dx) ** 2 + (self.yy - Y0 - t * dy) ** 2)
        v = np.exp(-(d / (w * self.u)) ** 2) + 0.35 * np.exp(-(d / (glow * self.u)) ** 2)
        self.a += (v * np.clip(np.sin(np.pi * t), 0, 1) ** 0.5 * k)[..., None] * C(col)

    def ring(self, x, y, r, col, w=0.006, k=1.0, glow=0.025, a0=0, a1=360):
        d = np.sqrt((self.xx - self.X(x)) ** 2 + (self.yy - self.Y(y)) ** 2) - r * self.u
        v = np.exp(-(d / (w * self.u)) ** 2) + 0.4 * np.exp(-(d / (glow * self.u)) ** 2)
        if a1 - a0 < 360:
            ang = (np.degrees(np.arctan2(self.yy - self.Y(y), self.xx - self.X(x))) + 360) % 360
            v = v * (((ang - a0) % 360) <= (a1 - a0))
        self.a += (v * k)[..., None] * C(col)

    def particles(self, n, col, x0=0, y0=0, x1=1, y1=1, smax=0.006, k=1.0):
        for _ in range(n):
            self.blob(self.rng.uniform(x0, x1), self.rng.uniform(y0, y1), self.rng.uniform(0.001, smax), col,
                      k * self.rng.uniform(0.4, 1.0))

    # ------------------------------------------------------------- rendered objects
    def sphere(self, x, y, r, base, light=(-0.5, -0.6), spec=0.6, rim=None, rim_k=0.8):
        R = r * self.u
        dx = (self.xx - self.X(x)) / R
        dy = (self.yy - self.Y(y)) / R
        d2 = dx * dx + dy * dy
        nz = np.sqrt(np.clip(1 - d2, 0, 1))
        lx, ly = light
        lz = math.sqrt(max(0.05, 1 - lx * lx - ly * ly))
        lam = np.clip(dx * lx + dy * ly + nz * lz, 0, 1)
        col = C(base)[None, None] * (0.16 + 0.84 * lam[..., None])
        hn = math.sqrt(lx * lx + ly * ly + (lz + 1) ** 2)
        col = col + (np.clip((dx * lx + dy * ly + nz * (lz + 1)) / hn, 0, 1) ** 40 * 255 * spec)[..., None]
        if rim:
            col = col + (np.clip(1 - nz, 0, 1) ** 3 * rim_k)[..., None] * C(rim)
        aa = np.clip((1 - np.sqrt(d2)) * R / 1.5, 0, 1)[..., None]
        self.a = self.a * (1 - aa) + col * aa

    def basketball(self, x, y, r):
        self.blob(x, y, r * 1.6, "#ff6a1a", 0.35)
        self.sphere(x, y, r, "#e8661c", spec=0.35, rim="#ffd0a0", rim_k=0.5)
        R = r * self.u
        cx, cy = self.X(x), self.Y(y)
        L = Image.new("L", (self.W, self.H), 0)
        d = ImageDraw.Draw(L)
        w = max(2, int(0.035 * R))
        d.line([(cx - R, cy), (cx + R, cy)], fill=255, width=w)
        d.line([(cx, cy - R), (cx, cy + R)], fill=255, width=w)
        d.arc([cx - R * 1.55, cy - R, cx - R * 0.25, cy + R], -62, 62, fill=255, width=w)
        d.arc([cx + R * 0.25, cy - R, cx + R * 1.55, cy + R], 118, 242, fill=255, width=w)
        m = self._mask(L.filter(ImageFilter.GaussianBlur(1)))
        circ = (((self.xx - cx) ** 2 + (self.yy - cy) ** 2) <= (R * 0.98) ** 2)[..., None]
        self.a = self.a * (1 - m * circ * 0.85)

    def can(self, x, y, w, h, body, label):
        X0, X1 = self.X(x - w / 2), self.X(x + w / 2)
        Y0, Y1 = self.Y(y - h / 2), self.Y(y + h / 2)
        inside = (self.xx >= X0) & (self.xx <= X1) & (self.yy >= Y0) & (self.yy <= Y1)
        t = np.clip((self.xx - X0) / (X1 - X0), 0, 1)
        shade = (0.25 + 0.75 * np.clip(np.sin(t * math.pi), 0, 1) ** 0.8)[..., None]
        spec = (np.exp(-((t - 0.3) / 0.05) ** 2) * 200 + np.exp(-((t - 0.78) / 0.03) ** 2) * 60)[..., None]
        ty = (self.yy - Y0) / (Y1 - Y0)
        col = np.where(((ty > 0.3) & (ty < 0.72))[..., None], C(label), C(body)) * shade + spec
        rim = ((ty < 0.05) | (ty > 0.95))[..., None]
        col = np.where(rim, C("#c8ccd8") * shade + spec * 0.5, col)
        self.a = np.where(inside[..., None], col, self.a)

    def bottle(self, x, y, w, h, glass, liquid, cap="#d8d0e8"):
        X0, X1 = self.X(x - w / 2), self.X(x + w / 2)
        Y0, Y1 = self.Y(y - h / 2 + h * 0.18), self.Y(y + h / 2)
        L = Image.new("L", (self.W, self.H), 0)
        ImageDraw.Draw(L).rounded_rectangle([X0, Y0, X1, Y1], radius=(X1 - X0) * 0.18, fill=255)
        m = self._mask(L.filter(ImageFilter.GaussianBlur(1.2)))
        t = np.clip((self.xx - X0) / (X1 - X0), 0, 1)[..., None]
        ty = np.clip((self.yy - Y0) / (Y1 - Y0), 0, 1)[..., None]
        hl = np.exp(-((t - 0.22) / 0.04) ** 2)
        col = np.where(ty > 0.35, C(liquid) * (0.4 + 0.6 * np.sin(t * math.pi)) + hl * 120,
                       C(glass) * (0.3 + 0.7 * np.sin(t * math.pi)) + hl * 180)
        self.a = self.a * (1 - m) + col * m
        nw, cx = (X1 - X0) * 0.32, (X0 + X1) / 2
        L2 = Image.new("L", (self.W, self.H), 0)
        ImageDraw.Draw(L2).rectangle([cx - nw / 2, self.Y(y - h / 2), cx + nw / 2, Y0 + 2], fill=255)
        m2 = self._mask(L2)
        tc = np.clip((self.xx - (cx - nw / 2)) / nw, 0, 1)[..., None]
        self.a = self.a * (1 - m2) + C(cap) * (0.35 + 0.65 * np.sin(tc * math.pi)) * m2

    def grid_floor(self, horizon, col, k=0.7, lines=22):
        L = Image.new("L", (self.W, self.H), 0)
        d = ImageDraw.Draw(L)
        hy = self.Y(horizon)
        for i in range(-lines, lines + 1):
            d.line([(self.W / 2, hy), (self.W / 2 + i * self.W / lines * 1.8, self.H)], fill=255, width=SS * 2)
        for j in range(1, 14):
            y = hy + (self.H - hy) * (j / 14) ** 2.3
            d.line([(0, y), (self.W, y)], fill=255, width=SS * 2)
        m = self._mask(L.filter(ImageFilter.GaussianBlur(1)))
        fade = np.clip((self.yy - hy) / (self.H - hy + 1e-9), 0, 1)[..., None]
        self.a += m * fade * k * C(col)

    def stripes_sun(self, x, y, r, top, bottom, cut=0.45):
        R = r * self.u
        inside = ((self.xx - self.X(x)) ** 2 + (self.yy - self.Y(y)) ** 2) <= R * R
        t = np.clip((self.yy - (self.Y(y) - R)) / (2 * R), 0, 1)
        col = C(top)[None, None] * (1 - t[..., None]) + C(bottom)[None, None] * t[..., None]
        band = (t > cut) & ((((t - cut) * 18) % 1.0) < (0.25 + (t - cut) * 1.2))
        self.a = np.where((inside & ~band)[..., None], col, self.a)
        self.blob(x, y, r * 1.5, top, 0.35)

    # ------------------------------------------------------------- type
    def text(self, s, fp, size, x, y, col="#ffffff", anchor="ls", track=0.0, maxw=None, k=1.0, glow=0.0,
             glow_col=None):
        """size: em size as fraction of the short side; x, y in 0..1; track in em."""
        px = size * self.u
        f = font(fp, px)
        L = Image.new("L", (self.W, self.H), 0)
        d = ImageDraw.Draw(L)
        widths = [d.textlength(ch, font=f) for ch in s]
        tw = sum(widths) + track * px * (len(s) - 1)
        if maxw and tw > maxw * self.W:
            return self.text(s, fp, size * (maxw * self.W) / tw * 0.98, x, y, col, anchor, track, None, k, glow,
                             glow_col)
        X = self.X(x) - (tw / 2 if anchor[0] == "m" else (tw if anchor[0] == "r" else 0))
        for ch, wch in zip(s, widths):
            d.text((X, self.Y(y)), ch, font=f, fill=255, anchor="l" + anchor[1])
            X += wch + track * px
        m = self._mask(L) * k
        if glow:
            self.a += self._mask(L.filter(ImageFilter.GaussianBlur(glow * self.u))) * C(glow_col or col) * 0.9
        self.a = self.a * (1 - m) + C(col) * m

    def vtext(self, s, fp, size, x, y0, col="#ffffff", step=1.08, glow=0.0):
        for i, ch in enumerate(s):
            self.text(ch, fp, size, x, y0 + i * size * step * self.u / self.H, col, anchor="mt", glow=glow)

    def rule(self, x0, y, x1, col, w=0.004, k=0.8):
        y0, y1 = self.Y(y) - w * self.u / 2, self.Y(y) + w * self.u / 2
        m = ((self.yy >= y0) & (self.yy <= y1) & (self.xx >= self.X(x0)) & (self.xx <= self.X(x1)))[..., None]
        self.a = np.where(m, self.a * (1 - k) + C(col) * k, self.a)

    def logo(self, mark, name, x, y, size, col="#ffffff", acc=None):
        """Brand lockup: geometric mark + spaced wordmark, top-left anchored."""
        u = size * self.u
        cx, cy = self.X(x) + u / 2, self.Y(y) + u / 2
        L = Image.new("L", (self.W, self.H), 0)
        d = ImageDraw.Draw(L)
        lw = max(2, int(u * 0.11))
        if mark == "circle":
            d.ellipse([cx - u / 2, cy - u / 2, cx + u / 2, cy + u / 2], outline=255, width=lw)
            d.ellipse([cx - u / 6, cy - u / 6, cx + u / 6, cy + u / 6], fill=255)
        elif mark == "hex":
            d.polygon([(cx + u / 2 * math.cos(math.radians(60 * i + 30)), cy + u / 2 * math.sin(math.radians(60 * i + 30)))
                       for i in range(6)], outline=255, width=lw)
        elif mark == "slash":
            for o in (-u / 4, u / 4):
                d.polygon([(cx + o - u / 3, cy + u / 2), (cx + o, cy - u / 2), (cx + o + u / 5, cy - u / 2),
                           (cx + o - u / 3 + u / 5, cy + u / 2)], fill=255)
        elif mark == "square":
            d.rectangle([cx - u / 2, cy - u / 2, cx + u / 2, cy + u / 2], outline=255, width=lw)
            d.rectangle([cx - u / 8, cy - u / 2, cx + u / 8, cy + u / 2], fill=255)
        else:  # tri
            d.polygon([(cx, cy - u / 2), (cx + u / 2, cy + u / 2), (cx - u / 2, cy + u / 2)], outline=255, width=lw)
        m = self._mask(L)
        self.a = self.a * (1 - m) + C(acc or col) * m
        self.text(name, F_BOLD, size * 0.62, (cx + u * 0.85) / self.W, cy / self.H, col, anchor="lm", track=0.22)

    # ------------------------------------------------------------- output
    def finish(self, grain=0.0):
        a = self.a + (self.rng.normal(0, grain, self.a.shape) if grain else 0)
        img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((self.W // SS, self.H // SS), Image.LANCZOS)
        b = np.asarray(img).astype(float)
        yy = np.mgrid[0:b.shape[0], 0:b.shape[1]][0]
        b *= (1 - 0.05 * ((yy % 3) == 2))[..., None]  # faint LED row structure
        return Image.fromarray(np.clip(b, 0, 255).astype(np.uint8))


ADS = {}


def ad(name, fmt):
    def deco(fn):
        ADS[name] = (fmt, fn)
        return fn
    return deco


# ================================================================== W  2:1
@ad("HexLeague", "W")
def hex_league(p):
    p.linear([(0, "#07040f"), (0.6, "#1b0820"), (1, "#3a0f12")], 0)
    p.blob(0.74, 0.45, 0.55, "#ff5a1f", 0.5)
    p.blob(0.92, 0.1, 0.35, "#ff2a8a", 0.25)
    p.basketball(0.74, 0.5, 0.33)
    p.logo("hex", "HEX LEAGUE", 0.04, 0.08, 0.075, acc="#ff6a1a")
    p.text("FINALS", F_BLACK, 0.27, 0.04, 0.62, maxw=0.5)
    p.text("2099 CHAMPIONSHIP", F_SEMI, 0.05, 0.045, 0.74, "#ffb37a", track=0.25, maxw=0.48)
    p.rule(0.045, 0.81, 0.2, "#ff6a1a", 0.006)
    p.text("決勝 ・ プラザコート ・ 21:00", F_JP, 0.05, 0.045, 0.91, k=0.9, maxw=0.48)


@ad("YumeOptics", "W")
def yume(p):
    p.linear([(0, "#030510"), (1, "#0b0420")], 0)
    for i, (r, c) in enumerate([(0.42, "#5a2bff"), (0.34, "#00d6ff"), (0.27, "#b45bff"), (0.2, "#00f0ff")]):
        p.ring(0.72, 0.5, r, c, w=0.003 + 0.001 * i, k=0.8, glow=0.02)
    p.sphere(0.72, 0.5, 0.13, "#101a40", light=(-0.3, -0.5), spec=0.9, rim="#00e5ff", rim_k=1.2)
    p.blob(0.72, 0.5, 0.06, "#00e5ff", 0.9)
    p.logo("circle", "YUME OPTICS", 0.04, 0.08, 0.07, acc="#00e5ff")
    p.text("SEE", F_THIN, 0.17, 0.04, 0.52)
    p.text("BEYOND.", F_BLACK, 0.17, 0.04, 0.75, maxw=0.46)
    p.text("夢の目 ・ IRIS-9", F_JP, 0.045, 0.045, 0.9, "#9fe9ff")


@ad("AkaiMotors", "W")
def akai(p):
    p.linear([(0, "#060208"), (1, "#14030a")], 90)
    for i in range(9):
        y = 0.52 + i * 0.035
        p.streak(-0.05, y + 0.08, 1.05, y, "#ff1f3d" if i % 3 else "#ff7a3a", w=0.0025, k=0.9, glow=0.02)
    for i in range(5):
        y = 0.72 + i * 0.03
        p.streak(1.05, y, -0.05, y + 0.05, "#fff1e0", w=0.002, k=0.5, glow=0.015)
    p.blob(0.5, 1.0, 0.6, "#ff1f3d", 0.25)
    p.logo("slash", "AKAI", 0.04, 0.08, 0.07, acc="#ff2a45")
    p.text("R-9", F_ITAL, 0.24, 0.04, 0.5)
    p.text("ELECTRIC. RELENTLESS.", F_SEMI, 0.045, 0.045, 0.6, "#ffb0b8", track=0.3, maxw=0.5)
    p.text("赤い稲妻", F_JP, 0.05, 0.955, 0.14, anchor="rm", k=0.85)


@ad("SynthWave", "W")
def synth(p):
    p.linear([(0, "#0a0220"), (0.55, "#3b0a52"), (0.62, "#0b0218"), (1, "#05010e")], 90)
    p.stripes_sun(0.5, 0.48, 0.3, "#ffd24a", "#ff2a9a", cut=0.5)
    p.grid_floor(0.62, "#ff3ac8", k=0.9)
    p.particles(50, "#ffffff", 0, 0, 1, 0.4, 0.002, 0.8)
    p.text("SYNTHWAVE", F_BLACK, 0.14, 0.5, 0.2, anchor="mm", track=0.12, glow=0.01, glow_col="#ff3ac8")
    p.text("NIGHTS", F_THIN, 0.07, 0.5, 0.31, "#ffd6f4", anchor="mm", track=0.8)
    p.text("夜のラジオ ・ EVERY FRIDAY", F_JP, 0.04, 0.5, 0.93, anchor="mm", k=0.85)


@ad("Kirin", "W")
def kirin(p):
    p.linear([(0, "#02040a"), (1, "#0a0618")], 0)
    L = Image.new("L", (p.W, p.H), 0)
    d = ImageDraw.Draw(L)
    cx, cy, s = p.X(0.72), p.Y(0.5), 0.2 * p.u
    for i in range(32):
        side, o = i % 4, (i // 4 - 3.5) * s * 0.12
        if side == 0:
            pts = [(cx - s, cy + o), (cx - s * 1.5, cy + o), (cx - s * 1.8, cy + o * 1.6), (cx - s * 3.0, cy + o * 1.6)]
        elif side == 1:
            pts = [(cx + s, cy + o), (cx + s * 1.4, cy + o), (cx + s * 1.7, cy + o * 1.7), (cx + s * 2.2, cy + o * 1.7)]
        elif side == 2:
            pts = [(cx + o, cy - s), (cx + o, cy - s * 1.4), (cx + o * 1.5, cy - s * 1.8), (cx + o * 1.5, cy - s * 2.6)]
        else:
            pts = [(cx + o, cy + s), (cx + o, cy + s * 1.4), (cx + o * 1.5, cy + s * 1.8), (cx + o * 1.5, cy + s * 2.6)]
        d.line(pts, fill=255, width=SS * 2)
        d.ellipse([pts[-1][0] - 5, pts[-1][1] - 5, pts[-1][0] + 5, pts[-1][1] + 5], fill=255)
    p.a += p._mask(L.filter(ImageFilter.GaussianBlur(1))) * C("#2fd8ff") * 0.75
    p.a += p._mask(L.filter(ImageFilter.GaussianBlur(10))) * C("#7b4bff") * 0.6
    sq = ((np.abs(p.xx - cx) < s) & (np.abs(p.yy - cy) < s))[..., None]
    p.a = np.where(sq, C("#0d1022"), p.a)
    p.blob(0.72, 0.5, 0.12, "#2fd8ff", 0.5)
    p.text("K9", F_BLACK, 0.16, 0.72, 0.5, "#e8f6ff", anchor="mm")
    p.logo("square", "KIRIN", 0.04, 0.08, 0.07, acc="#2fd8ff")
    p.text("THINK", F_THIN, 0.13, 0.04, 0.55)
    p.text("FASTER.", F_BLACK, 0.13, 0.04, 0.73, maxw=0.38)
    p.text("量子コア ・ CYBERDECK", F_JP, 0.045, 0.045, 0.88, "#9adfff", maxw=0.38)


@ad("Eterna", "W")
def eterna(p):
    p.linear([(0, "#000004"), (1, "#060018")], 0)
    for i in range(14):
        p.ring(0.7, 0.5, 0.05 + i * 0.03, "#8a5bff" if i % 2 else "#3ad0ff", w=0.0015, k=0.65 - i * 0.035, glow=0.01)
    p.blob(0.7, 0.5, 0.1, "#ffffff", 0.7)
    p.logo("circle", "ETERNA", 0.04, 0.08, 0.07, acc="#b38bff")
    p.text("FOREVER", F_THIN, 0.12, 0.04, 0.58, track=0.12, maxw=0.48)
    p.text("STARTS NOW", F_BOLD, 0.06, 0.045, 0.7, "#c9b4ff", track=0.3, maxw=0.48)
    p.text("意識の未来", F_JP, 0.05, 0.045, 0.88, k=0.85)


@ad("SakuraAir", "W")
def sakura(p):
    p.linear([(0, "#14051e"), (0.5, "#4a0c3a"), (1, "#ff7aa8")], 100)
    p.blob(0.2, 0.9, 0.5, "#ff9ac1", 0.35)
    for _ in range(40):
        p.blob(p.rng.uniform(0.4, 1), p.rng.uniform(0, 1), p.rng.uniform(0.006, 0.016), "#ffd2e6", p.rng.uniform(0.4, 0.9))
    p.streak(0.3, 0.75, 1.02, 0.25, "#ffffff", w=0.002, k=0.8, glow=0.02)
    p.logo("tri", "SAKURA AIR", 0.04, 0.08, 0.07, acc="#ffc2dc")
    p.text("TOKYO", F_BLACK, 0.17, 0.04, 0.6)
    p.text("TO THE STARS", F_SEMI, 0.05, 0.045, 0.71, "#ffd6e8", track=0.35, maxw=0.45)
    p.text("桜航空 ・ 軌道便", F_JP, 0.045, 0.045, 0.88, k=0.9)


@ad("Volt", "W")
def volt(p):
    p.linear([(0, "#00141a"), (1, "#002838")], 20)
    for i in range(6):
        x = 0.42 + i * 0.1
        L = Image.new("L", (p.W, p.H), 0)
        ImageDraw.Draw(L).polygon([(p.X(x), p.H), (p.X(x + 0.06), p.H), (p.X(x + 0.22), 0), (p.X(x + 0.16), 0)], fill=255)
        m = p._mask(L) * 0.6 * (0.3 + i * 0.12)
        p.a = p.a * (1 - m) + C("#00e0ff" if i % 2 else "#00ffb0") * m
    p.blob(0.75, 0.5, 0.3, "#00ffd0", 0.35)
    p.logo("slash", "VOLT", 0.04, 0.08, 0.07, acc="#00ffd0")
    p.text("JUMP", F_ITAL, 0.2, 0.04, 0.55)
    p.text("HIGHER", F_ITAL, 0.2, 0.04, 0.8, "#00ffd0")
    p.text("跳べ", F_JP, 0.09, 0.955, 0.86, anchor="rs")


@ad("NightMarket", "W")
def night_market(p):
    p.linear([(0, "#0d0306"), (1, "#260710")], 90)
    for i in range(12):
        x, y = 0.08 + i * 0.08, 0.18 + 0.05 * math.sin(i * 0.9)
        p.blob(x, y, 0.05, "#ff3a2a", 0.9)
        p.blob(x, y, 0.025, "#ffd27a", 0.9)
    p.streak(0.0, 0.12, 1.0, 0.16, "#ffb070", w=0.0015, k=0.4)
    p.text("夜市", F_JP, 0.36, 0.05, 0.84, glow=0.01, glow_col="#ff3a2a")
    p.text("NIGHT", F_BLACK, 0.12, 0.95, 0.62, anchor="rs")
    p.text("MARKET", F_LIGHT, 0.08, 0.95, 0.76, "#ffd0a0", anchor="rs", track=0.25)
    p.text("FRI ・ SAT ・ 18:00–05:00", F_SEMI, 0.035, 0.95, 0.88, anchor="rs", track=0.2, k=0.8)


# ================================================================== X  4:1
@ad("HexNews", "X")
def hex_news(p):
    p.linear([(0, "#05060c"), (1, "#0c0f1e")], 0)
    p.a[:, :int(p.W * 0.2)] = C("#e8203a")
    p.text("HEX", F_BLACK, 0.34, 0.1, 0.5, anchor="mm")
    p.text("NEWS", F_LIGHT, 0.16, 0.1, 0.82, anchor="mm", track=0.4)
    p.text("HEX LEAGUE FINALS TONIGHT AT THE PLAZA", F_BOLD, 0.2, 0.24, 0.45, maxw=0.73)
    p.text("速報 ・ 渋谷スカイレール 新路線 ・ 晴れ 18°C", F_JP, 0.15, 0.24, 0.82, "#8fd8ff", maxw=0.73)


@ad("KoiAir", "X")
def koi_air(p):
    p.linear([(0, "#01061a"), (1, "#062a58")], 0)
    for i in range(7):
        p.streak(0.4 + i * 0.02, 0.85 - i * 0.1, 1.05, 0.55 - i * 0.07, "#4ad0ff" if i % 2 else "#ffffff", w=0.004,
                 k=0.7, glow=0.03)
    p.logo("circle", "KOI AIR", 0.025, 0.13, 0.2, acc="#4ad0ff")
    p.text("SKY TAXI ・ ALL NIGHT", F_BOLD, 0.2, 0.025, 0.86, track=0.2, maxw=0.5)
    p.text("空のタクシー", F_JP, 0.22, 0.975, 0.86, "#bfeaff", anchor="rs")


@ad("RamenIchiban", "X")
def ramen(p):
    p.linear([(0, "#2a0306"), (1, "#5a0a0e")], 0)
    p.blob(0.88, 0.5, 0.6, "#ff9a3a", 0.35)
    p.text("ラーメン一番", F_JP, 0.62, 0.03, 0.82, maxw=0.6)
    p.text("TONKOTSU", F_BLACK, 0.2, 0.7, 0.5, "#ffd27a", maxw=0.27)
    p.text("SINCE 2061", F_MED, 0.13, 0.7, 0.82, track=0.3, maxw=0.27)


@ad("TipOff", "X")
def tipoff(p):
    p.linear([(0, "#050208"), (1, "#16060a")], 0)
    p.blob(0.85, 0.5, 0.8, "#ff3a20", 0.3)
    p.logo("hex", "HEX LEAGUE", 0.025, 0.14, 0.2, acc="#ff6a1a")
    p.text("TIP-OFF", F_BLACK, 0.38, 0.025, 0.9, maxw=0.45)
    p.text("21:00", F_THIN, 0.62, 0.975, 0.8, "#ffb070", anchor="rs", glow=0.01)


@ad("MiraiBank", "X")
def mirai(p):
    p.linear([(0, "#020614"), (1, "#0a1a3a")], 0)
    p.streak(0.55, 0.5, 1.05, 0.5, "#d8b56a", w=0.002, k=0.6, glow=0.01)
    p.logo("square", "MIRAI BANK", 0.025, 0.14, 0.2, acc="#d8b56a")
    p.text("YOUR FUTURE, SECURED.", F_LIGHT, 0.22, 0.025, 0.86, track=0.08, maxw=0.6)
    p.text("未来銀行", F_JP, 0.36, 0.975, 0.82, "#e9d3a0", anchor="rs")


# ================================================================== P  8:3 (curved wraps)
@ad("NeoShibuya", "P")
def neo_shibuya(p):
    p.linear([(0, "#05020f"), (0.65, "#3a0c52"), (1, "#ff5a8a")], 90)
    x = 0.0
    while x < 1:
        w, h = p.rng.uniform(0.02, 0.06), p.rng.uniform(0.25, 0.7)
        m = ((p.xx >= p.X(x)) & (p.xx < p.X(x + w)) & (p.yy > p.Y(1 - h)))[..., None]
        p.a = np.where(m, C("#07020f"), p.a)
        x += w + p.rng.uniform(0, 0.01)
    p.particles(220, "#ffd0a0", 0, 0.4, 1, 1, 0.0025, 0.6)
    p.text("WELCOME TO", F_LIGHT, 0.07, 0.5, 0.17, anchor="mm", track=0.6)
    p.text("NEO-SHIBUYA", F_BLACK, 0.22, 0.5, 0.42, anchor="mm", glow=0.012, glow_col="#ff5a8a")
    p.text("ネオ渋谷へようこそ", F_JP, 0.07, 0.5, 0.58, "#ffd6e8", anchor="mm")


@ad("Titan3", "P")
def titan(p):
    p.linear([(0, "#020208"), (1, "#0a0f24")], 0)
    p.blob(0.72, 0.42, 0.6, "#ff2a3a", 0.35)
    for i in range(12):
        t = i * math.pi / 6
        p.streak(0.72, 0.42, 0.72 + math.cos(t) * 0.5, 0.42 + math.sin(t) * 1.2, "#ff6a5a", w=0.002, k=0.4, glow=0.02)
    p.sphere(0.72, 0.42, 0.18, "#1a0a10", light=(0.4, -0.5), spec=0.4, rim="#ff3a4a", rim_k=1.4)
    p.logo("tri", "STUDIO KAZE", 0.03, 0.09, 0.08, acc="#ff3a4a")
    p.text("TITAN III", F_BLACK, 0.24, 0.03, 0.62, maxw=0.5)
    p.text("SEASON 3 ・ 新章", F_JP, 0.07, 0.035, 0.8, "#ffb3bb")


@ad("ShibuyaKanji", "P")
def shibuya_kanji(p):
    p.linear([(0, "#000000"), (1, "#14051e")], 0)
    p.blob(0.3, 0.5, 0.5, "#ff2a9a", 0.35)
    p.text("渋谷", F_JP, 0.72, 0.04, 0.9, glow=0.015, glow_col="#ff2a9a")
    p.text("SHIBUYA", F_BLACK, 0.17, 0.6, 0.5, "#00e0ff", maxw=0.36)
    p.text("CROSSING 2099", F_LIGHT, 0.08, 0.6, 0.7, track=0.3, maxw=0.36)


# ================================================================== T  1:2
@ad("DenkiCola", "T")
def denki(p):
    p.linear([(0, "#02020c"), (1, "#14022a")], 90)
    p.blob(0.5, 0.42, 0.7, "#2a6aff", 0.45)
    p.blob(0.5, 0.42, 0.3, "#ff2aa8", 0.35)
    p.can(0.5, 0.42, 0.42, 0.42, "#e81e8c", "#101018")
    p.text("電気", F_JP, 0.17, 0.5, 0.45, anchor="mm")
    p.logo("slash", "DENKI", 0.08, 0.04, 0.09, acc="#ff2aa8")
    p.text("FEEL", F_THIN, 0.17, 0.5, 0.76, anchor="mm", track=0.1)
    p.text("THE CHARGE", F_BLACK, 0.11, 0.5, 0.84, anchor="mm", maxw=0.86)
    p.text("NEON FLAVOR ・ 限定", F_JP, 0.055, 0.5, 0.93, "#9fd6ff", anchor="mm", maxw=0.86)


@ad("AikoTour", "T")
def aiko(p):
    p.linear([(0, "#14021e"), (1, "#020008")], 90)
    for i in range(7):
        p.streak(0.5, 0.0, 0.1 + i * 0.13, 0.75, "#ff6ad0" if i % 2 else "#7a5bff", w=0.006, k=0.35, glow=0.06)
    p.particles(80, "#ffffff", 0, 0, 1, 0.7, 0.004, 0.8)
    p.text("AIKO", F_BLACK, 0.4, 0.5, 0.72, anchor="ms", glow=0.012, glow_col="#ff6ad0")
    p.text("WORLD TOUR 2099", F_SEMI, 0.07, 0.5, 0.79, "#ffc6ee", anchor="mm", track=0.25, maxw=0.86)
    p.rule(0.3, 0.84, 0.7, "#ff6ad0", 0.006)
    p.text("夜を歌う", F_JP, 0.09, 0.5, 0.92, anchor="mm")


@ad("NoirParfum", "T")
def noir(p):
    p.linear([(0, "#000000"), (1, "#18020f")], 90)
    p.blob(0.5, 0.45, 0.45, "#ff2a8a", 0.35)
    p.bottle(0.5, 0.46, 0.34, 0.4, "#3a0a24", "#a01a5a")
    p.text("夜", F_JP, 0.14, 0.5, 0.55, "#ffd0e8", anchor="mm", k=0.9)
    p.text("N O I R", F_THIN, 0.13, 0.5, 0.13, anchor="mm", track=0.2)
    p.text("EAU DE NUIT", F_MED, 0.055, 0.5, 0.82, "#ffc2dc", anchor="mm", track=0.5, maxw=0.86)
    p.text("東京", F_JP, 0.06, 0.5, 0.9, anchor="mm", k=0.8)


@ad("ArashiWatch", "T")
def arashi(p):
    p.linear([(0, "#02040c"), (1, "#0c1430")], 90)
    p.blob(0.5, 0.42, 0.4, "#3a8aff", 0.3)
    p.sphere(0.5, 0.42, 0.3, "#0c1020", light=(-0.4, -0.6), spec=0.8, rim="#7ab0ff", rim_k=0.7)
    p.ring(0.5, 0.42, 0.26, "#c8d6ff", w=0.004, k=0.8)
    sx, sy = p.u / p.W, p.u / p.H
    for i in range(12):
        t = i * math.pi / 6
        p.streak(0.5 + 0.21 * math.cos(t) * sx, 0.42 + 0.21 * math.sin(t) * sy, 0.5 + 0.245 * math.cos(t) * sx,
                 0.42 + 0.245 * math.sin(t) * sy, "#ffffff", w=0.004, k=1.0, glow=0.004)
    p.streak(0.5, 0.42, 0.5 + 0.12 * sx, 0.42 - 0.09 * sy, "#ffffff", w=0.007, k=1.0, glow=0.01)
    p.streak(0.5, 0.42, 0.5 - 0.06 * sx, 0.42 - 0.2 * sy, "#ff3a4a", w=0.004, k=1.0, glow=0.01)
    p.logo("hex", "ARASHI", 0.08, 0.04, 0.09, acc="#7ab0ff")
    p.text("PRECISION", F_LIGHT, 0.1, 0.5, 0.76, anchor="mm", track=0.2, maxw=0.86)
    p.text("IN THE STORM", F_BOLD, 0.075, 0.5, 0.83, "#9cc2ff", anchor="mm", track=0.2, maxw=0.86)
    p.text("嵐 ・ 東京製", F_JP, 0.06, 0.5, 0.92, anchor="mm")


@ad("Nexus", "T")
def nexus(p):
    p.linear([(0, "#dfe6f4"), (1, "#9aa8c8")], 90)
    p.sphere(0.5, 0.4, 0.32, "#e9eef8", light=(-0.4, -0.5), spec=0.9)
    band = ((np.abs(p.yy - p.Y(0.4)) < 0.035 * p.u) & (np.abs(p.xx - p.X(0.5)) < 0.27 * p.u))[..., None]
    p.a = np.where(band, C("#0b1230"), p.a)
    p.blob(0.5, 0.4, 0.05, "#00d0ff", 0.9)
    p.logo("circle", "NEXUS", 0.08, 0.04, 0.09, col="#0b1230", acc="#0090ff")
    p.text("HUMAN,", F_LIGHT, 0.12, 0.5, 0.76, "#0b1230", anchor="mm")
    p.text("UPGRADED.", F_BLACK, 0.12, 0.5, 0.84, "#0b1230", anchor="mm", maxw=0.86)
    p.text("家族の一員", F_JP, 0.06, 0.5, 0.92, "#3a4a70", anchor="mm")


@ad("HexLeague23", "T")
def hex23(p):
    p.linear([(0, "#140205"), (1, "#050102")], 90)
    p.blob(0.5, 0.3, 0.6, "#ff4a1a", 0.4)
    p.text("23", F_BLACK, 0.95, 0.5, 0.62, "#ff6a1a", anchor="ms", k=0.25)
    p.basketball(0.5, 0.42, 0.28)
    p.logo("hex", "HEX LEAGUE", 0.08, 0.04, 0.09, acc="#ff6a1a")
    p.text("ONE NIGHT.", F_BLACK, 0.1, 0.5, 0.78, anchor="mm", maxw=0.86)
    p.text("ONE CHAMPION.", F_LIGHT, 0.08, 0.5, 0.85, "#ffc09a", anchor="mm", maxw=0.86)
    p.text("決勝戦", F_JP, 0.07, 0.5, 0.93, anchor="mm")


@ad("Okami", "T")
def okami(p):
    p.linear([(0, "#0a0a0c"), (1, "#000000")], 90)
    p.blob(0.5, 0.35, 0.4, "#ff2030", 0.25)
    L = Image.new("L", (p.W, p.H), 0)
    d = ImageDraw.Draw(L)
    cx, cy, s = p.X(0.5), p.Y(0.36), 0.32 * p.u
    pts = [(0, 0.95), (-0.55, 0.35), (-0.7, -0.75), (-0.32, -0.3), (0, -0.4), (0.32, -0.3), (0.7, -0.75), (0.55, 0.35)]
    P = [(cx + x * s, cy + y * s) for x, y in pts]
    d.line(P + [P[0]], fill=255, width=int(0.012 * p.u), joint="curve")
    for a, b in [((-0.32, -0.3), (-0.12, 0.12)), ((0.32, -0.3), (0.12, 0.12)), ((-0.12, 0.12), (0, 0.95)),
                 ((0.12, 0.12), (0, 0.95)), ((-0.55, 0.35), (-0.12, 0.12)), ((0.55, 0.35), (0.12, 0.12))]:
        d.line([(cx + a[0] * s, cy + a[1] * s), (cx + b[0] * s, cy + b[1] * s)], fill=255, width=int(0.006 * p.u))
    p.a += p._mask(L.filter(ImageFilter.GaussianBlur(14))) * C("#ff2030") * 0.8
    m = p._mask(L)
    p.a = p.a * (1 - m) + C("#ff3a44") * m
    p.text("OKAMI", F_BLACK, 0.2, 0.5, 0.78, anchor="mm", track=0.1, maxw=0.86)
    p.text("STREETWEAR ・ AW99", F_MED, 0.05, 0.5, 0.85, "#c8c8d0", anchor="mm", track=0.3, maxw=0.86)
    p.text("狼", F_JP, 0.09, 0.5, 0.93, "#ff3a44", anchor="mm")


# ================================================================== S  1:4 (holo strips)
def _strip(p, kanji, latin, top, bottom, accent, sub):
    p.linear([(0, top), (1, bottom)], 90)
    p.blob(0.5, 0.25, 0.9, accent, 0.25)
    size = min(0.8, 0.66 * p.H / p.u / max(1, len(kanji)) / 1.08)
    p.vtext(kanji, F_JP, size, 0.5, 0.06, glow=0.03)
    p.rule(0.25, 0.86, 0.75, accent, 0.012)
    p.text(latin, F_BLACK, 0.2, 0.5, 0.91, anchor="mm", maxw=0.84)
    p.text(sub, F_MED, 0.11, 0.5, 0.955, accent, anchor="mm", track=0.2, maxw=0.84)


@ad("Tokyo2099", "S")
def s_tokyo(p):
    _strip(p, "東京", "TOKYO", "#ff2a9a", "#2a0a5a", "#00e0ff", "2099")


@ad("Cyber", "S")
def s_cyber(p):
    _strip(p, "サイバー", "CYBER", "#001024", "#00060e", "#00e0ff", "CITY")


@ad("Matcha", "S")
def s_matcha(p):
    _strip(p, "緑茶", "MATCHA+", "#00281e", "#000a08", "#4affb0", "FOCUS")


@ad("Katana", "S")
def s_katana(p):
    _strip(p, "刀", "KATANA", "#1a0004", "#050001", "#ff2a3a", "S3")


@ad("ClubVoid", "S")
def s_dance(p):
    _strip(p, "ダンス", "CLUB VOID", "#1a0430", "#04000a", "#b45bff", "B2F")


@ad("Aquarium", "S")
def s_koi(p):
    _strip(p, "鯉", "AQUARIUM", "#002030", "#00060c", "#3ad8ff", "OPEN")


# ================================================================== Q  1:1
@ad("NeonNoodle", "Q")
def noodle(p):
    p.linear([(0, "#1a0206"), (1, "#060104")], 90)
    p.blob(0.5, 0.5, 0.45, "#ff3a1a", 0.35)
    cx, cy, rw, rh = p.X(0.5), p.Y(0.52), 0.36 * p.u, 0.26 * p.u
    dx, dy = (p.xx - cx) / rw, (p.yy - cy) / rh
    bowl = ((dx * dx + dy * dy <= 1) & (p.yy >= cy))[..., None]
    # bowl lit from the upper left: darker towards the bottom, highlight band on the left
    shade = (0.3 + 0.7 * np.clip(1 - dy, 0, 1) * (0.55 + 0.45 * np.clip(1 - np.abs(dx + 0.25), 0, 1)))[..., None]
    p.a = np.where(bowl, C("#c8102e") * shade + np.exp(-((dx + 0.6) / 0.07) ** 2)[..., None] * 90, p.a)
    ry = rh * 0.22
    top = (dx * dx + ((p.yy - cy) / ry) ** 2)
    p.a = np.where((top <= 1.0)[..., None], C("#ffe9dc"), p.a)                       # rim
    p.a = np.where((top <= 0.86)[..., None], C("#e09a3a") * (0.75 + 0.25 * np.clip(1 - np.abs(dx), 0, 1))[..., None],
                   p.a)                                                               # broth
    for i in range(7):  # noodles
        yy = cy + (i - 3) * ry * 0.22
        p.streak(0.5 - 0.22 + i * 0.01, yy / p.H, 0.5 + 0.2 - i * 0.012, yy / p.H + 0.004, "#fff1b0", w=0.003, k=0.6,
                 glow=0.004)
    p.sphere(0.6, (cy - ry * 0.1) / p.H, 0.05, "#ffffff", light=(-0.4, -0.7), spec=0.2)   # egg
    p.sphere(0.6, (cy - ry * 0.1) / p.H, 0.025, "#ffb020", light=(-0.4, -0.7), spec=0.6)
    p.streak(0.66, 0.2, 0.42, (cy - ry * 0.2) / p.H, "#e8d0b0", w=0.006, k=0.9, glow=0.004)  # chopsticks
    p.streak(0.71, 0.22, 0.47, (cy - ry * 0.1) / p.H, "#e8d0b0", w=0.006, k=0.9, glow=0.004)
    for i in range(3):
        x = 0.4 + i * 0.1
        pts = [(x + 0.025 * math.sin(t * 1.3 + i), 0.45 - t * 0.04) for t in range(9)]
        for a, b in zip(pts, pts[1:]):
            p.streak(a[0], a[1], b[0], b[1], "#ffffff", w=0.004, k=0.35, glow=0.02)
    p.text("ネオン麺", F_JP, 0.13, 0.5, 0.2, anchor="mm", glow=0.01, glow_col="#ff3a1a")
    p.text("NEON NOODLE", F_BLACK, 0.075, 0.5, 0.86, anchor="mm", track=0.12)
    p.text("OPEN ALL NIGHT", F_MED, 0.04, 0.5, 0.92, "#ffb070", anchor="mm", track=0.4)


@ad("RyuGames", "Q")
def ryu(p):
    p.linear([(0, "#0a0002"), (1, "#200006")], 90)
    p.blob(0.5, 0.45, 0.5, "#ff1a2a", 0.4)
    p.text("龍", F_JP, 0.7, 0.5, 0.48, "#ff2a3a", anchor="mm", glow=0.02, glow_col="#ff1a2a")
    for _ in range(10):
        y0 = int(p.rng.integers(0, p.H - 40))
        hh = int(p.rng.integers(6, 40))
        p.a[y0:y0 + hh] = np.roll(p.a[y0:y0 + hh], int(p.rng.integers(-60, 60)), axis=1)
    p.logo("slash", "RYU GAMES", 0.075, 0.07, 0.06, acc="#ff2a3a")
    p.text("DRAGON PROTOCOL", F_BLACK, 0.07, 0.5, 0.88, anchor="mm", track=0.1)
    p.text("新作", F_JP, 0.045, 0.5, 0.94, "#00e0ff", anchor="mm")


@ad("Karaoke", "Q")
def karaoke(p):
    p.linear([(0, "#14002a"), (1, "#04000a")], 90)
    for i in range(9):
        p.ring(0.5, 0.42, 0.06 + i * 0.045, "#ff3ac8" if i % 2 else "#00e0ff", w=0.004, k=0.9 - i * 0.08,
               glow=0.02, a0=200, a1=340)
    p.blob(0.5, 0.42, 0.06, "#ffffff", 0.9)
    p.text("カラオケ", F_JP, 0.15, 0.5, 0.74, anchor="mm", glow=0.01, glow_col="#ff3ac8")
    p.text("KARAOKE ・ 24H", F_BLACK, 0.06, 0.5, 0.85, "#00e0ff", anchor="mm", track=0.25)


@ad("Orbital", "Q")
def orbital(p):
    p.linear([(0, "#02000a"), (1, "#0c0420")], 90)
    p.particles(200, "#ffffff", 0, 0, 1, 1, 0.0018, 0.9)
    p.blob(0.5, 0.42, 0.45, "#6a3aff", 0.35)
    p.sphere(0.5, 0.42, 0.24, "#5a3ad8", light=(-0.6, -0.4), spec=0.3, rim="#9ae6ff", rim_k=1.2)
    p.ring(0.5, 0.42, 0.36, "#00e0ff", w=0.004, k=0.9, a0=150, a1=390)
    p.logo("circle", "ORBITAL RESORTS", 0.075, 0.07, 0.06, acc="#00e0ff")
    p.text("STAY ABOVE IT ALL", F_LIGHT, 0.07, 0.5, 0.85, anchor="mm", track=0.2)
    p.text("宇宙旅行", F_JP, 0.05, 0.5, 0.92, "#b8a8ff", anchor="mm")


@ad("CourtKings", "Q")
def court_kings(p):
    p.linear([(0, "#05030c"), (1, "#14051a")], 90)
    L = Image.new("L", (p.W, p.H), 0)
    d = ImageDraw.Draw(L)
    x0, y0, x1, y1 = p.X(0.12), p.Y(0.14), p.X(0.88), p.Y(0.62)
    w = int(0.006 * p.u)
    d.rectangle([x0, y0, x1, y1], outline=255, width=w)
    d.line([((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)], fill=255, width=w)
    r = 0.08 * p.u
    d.ellipse([(x0 + x1) / 2 - r, (y0 + y1) / 2 - r, (x0 + x1) / 2 + r, (y0 + y1) / 2 + r], outline=255, width=w)
    R = 0.2 * p.u
    d.arc([x0 - R, (y0 + y1) / 2 - R, x0 + R, (y0 + y1) / 2 + R], -90, 90, fill=255, width=w)
    d.arc([x1 - R, (y0 + y1) / 2 - R, x1 + R, (y0 + y1) / 2 + R], 90, 270, fill=255, width=w)
    p.a += p._mask(L.filter(ImageFilter.GaussianBlur(8))) * C("#ff6a1a") * 0.6
    m = p._mask(L)
    p.a = p.a * (1 - m) + C("#ffb070") * m
    p.basketball(0.64, 0.33, 0.06)
    p.text("COURT KINGS", F_ITAL, 0.11, 0.5, 0.78, anchor="mm", maxw=0.86)
    p.text("3 v 3 ・ HEX PLAZA ・ SATURDAY", F_SEMI, 0.04, 0.5, 0.86, "#ffb070", anchor="mm", track=0.2)
    p.text("ストリート大会", F_JP, 0.05, 0.5, 0.93, anchor="mm")


@ad("KitsuneCafe", "Q")
def kitsune(p):
    p.linear([(0, "#f4ece4"), (1, "#e2d2c4")], 90)
    L = Image.new("L", (p.W, p.H), 0)
    cx, cy, s = p.X(0.5), p.Y(0.4), 0.25 * p.u
    ImageDraw.Draw(L).polygon([(cx, cy + s), (cx - s * 0.75, cy + s * 0.05), (cx - s * 0.8, cy - s * 0.9),
                               (cx - s * 0.3, cy - s * 0.45), (cx + s * 0.3, cy - s * 0.45), (cx + s * 0.8, cy - s * 0.9),
                               (cx + s * 0.75, cy + s * 0.05)], fill=255)
    m = p._mask(L)
    p.a = p.a * (1 - m) + C("#d9481a") * m
    p.text("KITSUNE", F_BLACK, 0.11, 0.5, 0.78, "#2a1a14", anchor="mm", track=0.25)
    p.text("COFFEE ・ 狐カフェ", F_JP, 0.05, 0.5, 0.87, "#8a4a2a", anchor="mm")


@ad("Hanabi", "Q")
def hanabi(p):
    p.linear([(0, "#02000a"), (1, "#0c0218")], 90)
    for (cx, cy, col) in ((0.3, 0.28, "#ff3ac8"), (0.7, 0.22, "#3ad8ff"), (0.52, 0.45, "#ffd24a")):
        for k in range(36):
            t = 2 * math.pi * k / 36
            r = p.rng.uniform(0.14, 0.2)
            p.streak(cx + 0.03 * math.cos(t), cy + 0.03 * math.sin(t), cx + r * math.cos(t), cy + r * math.sin(t), col,
                     w=0.002, k=0.6, glow=0.01)
        p.blob(cx, cy, 0.05, col, 0.6)
    p.text("花火大会", F_JP, 0.14, 0.5, 0.77, anchor="mm", glow=0.01, glow_col="#ff3ac8")
    p.text("SHIBUYA SKY FESTIVAL", F_BOLD, 0.045, 0.5, 0.87, "#9fe6ff", anchor="mm", track=0.25)


@ad("Konbini", "Q")
def konbini(p):
    p.linear([(0, "#ffffff"), (1, "#e8eef4")], 90)
    for i, c in enumerate(("#16a34a", "#2563eb", "#e11d48")):
        p.a[int(p.Y(0.08 + i * 0.05)):int(p.Y(0.11 + i * 0.05))] = C(c)
    p.text("KONBINI", F_BLACK, 0.16, 0.5, 0.5, "#0b1020", anchor="mm")
    p.text("24", F_THIN, 0.3, 0.5, 0.74, "#e11d48", anchor="mm")
    p.text("いつでも、そばに。", F_JP, 0.05, 0.5, 0.92, "#334155", anchor="mm")


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):  # remove artwork from previous versions
        if f.startswith("AD_") and f.endswith(".png"):
            os.remove(os.path.join(OUT, f))
    meta = []
    for i, (name, (fmt, fn)) in enumerate(ADS.items()):
        p = Poster(fmt, 9000 + i)
        fn(p)
        img = p.finish()
        img.save(f"{OUT}/AD_{name}.png", optimize=True)
        meta.append((name, fmt, img.size))
    with open(os.path.join(OUT, "..", "ads_index.txt"), "w") as f:
        for m in meta:
            f.write(f"AD_{m[0]}\t{m[1]}\t{m[2][0]}x{m[2][1]}\n")
    print("wrote", len(meta), "ads")


if __name__ == "__main__":
    main()
