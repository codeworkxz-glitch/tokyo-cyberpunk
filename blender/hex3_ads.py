"""HEX! City v3 - advertisement artwork that goes with the game.

Basketball / HEX League campaigns (teams, MVP race, 3v3, dunk contest, jerseys, official
ball, sports drinks) mixed with everyday Shibuya ads (ramen, karaoke, konbini, cafe,
festivals, music) so the city reads like a real place. Fictional brands only.

Moderation-safe: no QR codes / barcodes, prices or currency, links or handles, purchase
calls to action, gambling or weapons.

Aspect classes (match the existing billboards of HEX_City_00_FULL_CITY.fbx):
    S3 1:3  256x768     T 1:2  512x1024    V 3:4 768x1024    Q 1:1 1024x1024
    L  3:2  1024x683    W 2:1  1024x512    X3 3:1 1024x341

    python3 blender/hex3_ads.py export_v3/textures
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cp2_ads as K  # noqa: E402  (Poster toolkit)
from cp2_ads import C, F_BLACK, F_BOLD, F_SEMI, F_MED, F_LIGHT, F_THIN, F_ITAL, F_JP  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "export_v3/textures"
K.SIZES.update({"S3": (256, 768), "T": (512, 1024), "V": (768, 1024), "Q": (1024, 1024), "L": (1024, 683),
                "W": (1024, 512), "X3": (1024, 341)})
ASPECT = {"S3": 1 / 3, "T": 0.5, "V": 0.75, "Q": 1.0, "L": 1.5, "W": 2.0, "X3": 3.0}
ORANGE, CREAM = "#ff6a1a", "#fff4e6"

ADS = {}


def ad(name, fmt):
    def deco(fn):
        ADS[name] = (fmt, fn)
        return fn
    return deco


# ------------------------------------------------------------------ extra motifs
def jersey(p, x, y, s, body, trim, number, name=None):
    """Basketball jersey (tank) with number, drawn flat with soft shading."""
    u = s * p.u
    cx, cy = p.X(x), p.Y(y)
    pts = [(-0.42, -0.55), (-0.2, -0.55), (-0.1, -0.38), (0.1, -0.38), (0.2, -0.55), (0.42, -0.55), (0.44, -0.2),
           (0.36, -0.05), (0.38, 0.6), (-0.38, 0.6), (-0.36, -0.05), (-0.44, -0.2)]
    L = Image.new("L", (p.W, p.H), 0)
    d = ImageDraw.Draw(L)
    d.polygon([(cx + a * u, cy + b * u) for a, b in pts], fill=255)
    m = p._mask(L.filter(ImageFilter.GaussianBlur(1.5)))
    t = np.clip((p.xx - (cx - 0.42 * u)) / (0.84 * u), 0, 1)[..., None]
    shade = 0.72 + 0.28 * np.sin(t * math.pi)
    p.a = p.a * (1 - m) + C(body) * shade * m
    L2 = Image.new("L", (p.W, p.H), 0)
    d2 = ImageDraw.Draw(L2)
    w = max(3, int(u * 0.035))
    d2.line([(cx - 0.2 * u, cy - 0.55 * u), (cx - 0.1 * u, cy - 0.38 * u), (cx + 0.1 * u, cy - 0.38 * u),
             (cx + 0.2 * u, cy - 0.55 * u)], fill=255, width=w)
    d2.line([(cx - 0.42 * u, cy - 0.55 * u), (cx - 0.44 * u, cy - 0.2 * u), (cx - 0.36 * u, cy - 0.05 * u)], fill=255,
            width=w)
    d2.line([(cx + 0.42 * u, cy - 0.55 * u), (cx + 0.44 * u, cy - 0.2 * u), (cx + 0.36 * u, cy - 0.05 * u)], fill=255,
            width=w)
    m2 = p._mask(L2) * m
    p.a = p.a * (1 - m2) + C(trim) * m2
    p.text(number, F_BLACK, s * 0.42, x, y + s * 0.27 * p.u / p.H, trim, anchor="mm")
    if name:
        p.text(name, F_BOLD, s * 0.08, x, y - s * 0.14 * p.u / p.H, trim, anchor="mm", track=0.2)


def hoop(p, x, y, s, col="#ffffff"):
    """Backboard + rim, line art with glow."""
    u = s * p.u
    cx, cy = p.X(x), p.Y(y)
    L = Image.new("L", (p.W, p.H), 0)
    d = ImageDraw.Draw(L)
    w = max(2, int(u * 0.02))
    d.rectangle([cx - 0.5 * u, cy - 0.35 * u, cx + 0.5 * u, cy + 0.25 * u], outline=255, width=w)
    d.rectangle([cx - 0.18 * u, cy - 0.12 * u, cx + 0.18 * u, cy + 0.12 * u], outline=255, width=w)
    d.ellipse([cx - 0.22 * u, cy + 0.2 * u, cx + 0.22 * u, cy + 0.32 * u], outline=255, width=w * 2)
    for i in range(7):
        x0 = cx - 0.2 * u + i * 0.4 * u / 6
        d.line([(x0, cy + 0.28 * u), (cx + (x0 - cx) * 0.6, cy + 0.6 * u)], fill=255, width=max(1, w // 2))
    p.a += p._mask(L.filter(ImageFilter.GaussianBlur(6))) * C(col) * 0.5
    m = p._mask(L)
    p.a = p.a * (1 - m) + C(col) * m


def court_lines(p, col, k=0.5):
    L = Image.new("L", (p.W, p.H), 0)
    d = ImageDraw.Draw(L)
    w = max(2, int(0.006 * p.u))
    d.line([(p.W / 2, 0), (p.W / 2, p.H)], fill=255, width=w)
    r = 0.22 * p.u
    d.ellipse([p.W / 2 - r, p.H / 2 - r, p.W / 2 + r, p.H / 2 + r], outline=255, width=w)
    R = 0.6 * p.u
    d.arc([-R, p.H / 2 - R, R, p.H / 2 + R], -90, 90, fill=255, width=w)
    d.arc([p.W - R, p.H / 2 - R, p.W + R, p.H / 2 + R], 90, 270, fill=255, width=w)
    p.a += p._mask(L) * C(col) * k


def team_mark(p, x, y, s, shape, col, letter):
    u = s * p.u
    cx, cy = p.X(x), p.Y(y)
    L = Image.new("L", (p.W, p.H), 0)
    d = ImageDraw.Draw(L)
    if shape == "shield":
        d.polygon([(cx - 0.5 * u, cy - 0.5 * u), (cx + 0.5 * u, cy - 0.5 * u), (cx + 0.5 * u, cy + 0.05 * u),
                   (cx, cy + 0.55 * u), (cx - 0.5 * u, cy + 0.05 * u)], fill=255)
    elif shape == "hex":
        d.polygon([(cx + 0.55 * u * math.cos(math.radians(60 * i + 30)), cy + 0.55 * u * math.sin(math.radians(60 * i + 30)))
                   for i in range(6)], fill=255)
    else:
        d.ellipse([cx - 0.5 * u, cy - 0.5 * u, cx + 0.5 * u, cy + 0.5 * u], fill=255)
    m = p._mask(L.filter(ImageFilter.GaussianBlur(1)))
    p.a = p.a * (1 - m) + C(col) * m
    p.text(letter, F_BLACK, s * 0.62, x, y + s * 0.02 * p.u / p.H, "#ffffff", anchor="mm")


# ================================================================== game: HEX League
@ad("HexFinals", "W")
def hex_finals(p):
    p.linear([(0, "#0b0612"), (1, "#2a0d08")], 0)
    p.blob(0.75, 0.5, 0.6, ORANGE, 0.45)
    court_lines(p, "#ff9a5a", 0.12)
    p.basketball(0.75, 0.5, 0.33)
    p.logo("hex", "HEX LEAGUE", 0.04, 0.08, 0.075, acc=ORANGE)
    p.text("FINALS", F_BLACK, 0.27, 0.04, 0.62, maxw=0.5)
    p.text("SHIBUYA STORM vs TOKYO TITANS", F_SEMI, 0.042, 0.045, 0.74, "#ffc49a", track=0.12, maxw=0.5)
    p.rule(0.045, 0.81, 0.2, ORANGE, 0.006)
    p.text("決勝 ・ HEX プラザ ・ 今夜 21:00", F_JP, 0.05, 0.045, 0.91, maxw=0.5)


@ad("HexOpener", "L")
def hex_opener(p):
    p.linear([(0, "#05070f"), (1, "#101c3a")], 90)
    p.blob(0.5, 0.35, 0.6, "#2a6aff", 0.45)
    hoop(p, 0.5, 0.33, 0.42, "#e8f0ff")
    p.basketball(0.62, 0.28, 0.07)
    p.logo("hex", "HEX LEAGUE", 0.04, 0.06, 0.07, acc="#4a8aff")
    p.text("SEASON 1", F_BLACK, 0.17, 0.5, 0.8, anchor="mm", maxw=0.9)
    p.text("TIP-OFF THIS WEEKEND ・ 開幕", F_JP, 0.05, 0.5, 0.91, "#a8c4ff", anchor="mm")


@ad("MvpRace", "T")
def mvp_race(p):
    p.linear([(0, "#140805"), (1, "#020101")], 90)
    p.blob(0.5, 0.35, 0.6, ORANGE, 0.4)
    p.text("MVP", F_BLACK, 0.55, 0.5, 0.5, ORANGE, anchor="ms", k=0.3)
    jersey(p, 0.5, 0.4, 0.62, "#f4f4f8", "#e8401a", "7", "STORM")
    p.logo("hex", "HEX LEAGUE", 0.08, 0.04, 0.09, acc=ORANGE)
    p.text("THE MVP RACE", F_BLACK, 0.1, 0.5, 0.8, anchor="mm", maxw=0.86)
    p.text("WHO TAKES THE CROWN?", F_LIGHT, 0.06, 0.5, 0.86, "#ffc49a", anchor="mm", track=0.15, maxw=0.86)
    p.text("最優秀選手", F_JP, 0.07, 0.5, 0.93, anchor="mm")


@ad("CourtKings3v3", "Q")
def court_kings(p):
    p.linear([(0, "#07030d"), (1, "#1a0712")], 90)
    court_lines(p, "#ffb070", 0.35)
    p.blob(0.5, 0.42, 0.4, ORANGE, 0.35)
    p.basketball(0.5, 0.4, 0.17)
    p.text("3v3", F_BLACK, 0.2, 0.5, 0.15, "#ffffff", anchor="mt")
    p.text("COURT KINGS", F_ITAL, 0.11, 0.5, 0.78, anchor="mm", maxw=0.86)
    p.text("STREET TOURNAMENT ・ SATURDAY", F_SEMI, 0.04, 0.5, 0.86, "#ffb070", anchor="mm", track=0.2)
    p.text("ストリート大会 ・ HEX プラザ", F_JP, 0.045, 0.5, 0.93, anchor="mm")


@ad("DunkContest", "V")
def dunk(p):
    p.linear([(0, "#0a0418"), (1, "#020008")], 90)
    for i in range(9):
        p.streak(0.5, -0.05, 0.05 + i * 0.11, 0.7, "#ff9a3a" if i % 2 else "#ffffff", w=0.004, k=0.3, glow=0.05)
    hoop(p, 0.5, 0.36, 0.5)
    p.basketball(0.5, 0.2, 0.08)
    p.text("DUNK", F_ITAL, 0.24, 0.5, 0.8, anchor="ms", glow=0.01, glow_col=ORANGE)
    p.text("CONTEST", F_BLACK, 0.085, 0.5, 0.86, ORANGE, anchor="mm", track=0.35)
    p.text("ダンクコンテスト ・ 金曜夜", F_JP, 0.05, 0.5, 0.93, anchor="mm")


@ad("RookieWatch", "S3")
def rookie(p):
    p.linear([(0, "#101a30"), (1, "#02040a")], 90)
    p.blob(0.5, 0.3, 0.9, "#3a7aff", 0.3)
    p.vtext("新人", F_JP, 0.7, 0.5, 0.05, glow=0.02)
    p.basketball(0.5, 0.68, 0.32)
    p.text("ROOKIE", F_BLACK, 0.2, 0.5, 0.85, anchor="mm", maxw=0.86)
    p.text("WATCH", F_LIGHT, 0.16, 0.5, 0.92, "#9cc0ff", anchor="mm", track=0.2, maxw=0.86)


@ad("Playoffs", "S3")
def playoffs(p):
    p.linear([(0, "#2a0806"), (1, "#060101")], 90)
    p.blob(0.5, 0.35, 0.9, ORANGE, 0.3)
    p.vtext("決戦", F_JP, 0.62, 0.5, 0.06, glow=0.02)
    p.rule(0.2, 0.8, 0.8, ORANGE, 0.012)
    p.text("PLAYOFFS", F_BLACK, 0.17, 0.5, 0.87, anchor="mm", maxw=0.88)
    p.text("HEX LEAGUE", F_MED, 0.1, 0.5, 0.94, "#ffc49a", anchor="mm", track=0.2, maxw=0.88)


@ad("TeamStorm", "T")
def team_storm(p):
    p.linear([(0, "#071226"), (1, "#01030a")], 90)
    p.blob(0.5, 0.35, 0.6, "#2a8aff", 0.4)
    for i in range(6):
        p.streak(0.2 + i * 0.12, 0.05, 0.1 + i * 0.12, 0.6, "#8ad0ff", w=0.002, k=0.4, glow=0.02)
    team_mark(p, 0.5, 0.35, 0.5, "shield", "#1a5aff", "S")
    p.text("SHIBUYA", F_LIGHT, 0.09, 0.5, 0.72, anchor="mm", track=0.4, maxw=0.86)
    p.text("STORM", F_BLACK, 0.2, 0.5, 0.82, anchor="mm", maxw=0.86)
    p.text("渋谷ストーム ・ HOME GAME", F_JP, 0.05, 0.5, 0.92, "#9cc8ff", anchor="mm", maxw=0.86)


@ad("TeamTitans", "L")
def team_titans(p):
    p.linear([(0, "#1a0808"), (1, "#050202")], 0)
    p.blob(0.28, 0.5, 0.5, "#ff2a2a", 0.35)
    team_mark(p, 0.27, 0.5, 0.42, "hex", "#c81e1e", "T")
    p.text("TOKYO", F_LIGHT, 0.09, 0.53, 0.38, track=0.4, maxw=0.44)
    p.text("TITANS", F_BLACK, 0.18, 0.53, 0.6, maxw=0.44)
    p.text("東京タイタンズ ・ 応援しよう", F_JP, 0.05, 0.53, 0.76, "#ffb0b0", maxw=0.44)


@ad("TeamHawks", "V")
def team_hawks(p):
    p.linear([(0, "#0c1a10"), (1, "#020604")], 90)
    p.blob(0.5, 0.36, 0.5, "#2aff8a", 0.25)
    team_mark(p, 0.5, 0.36, 0.42, "circle", "#14a050", "H")
    p.text("HARAJUKU", F_LIGHT, 0.08, 0.5, 0.72, anchor="mm", track=0.3, maxw=0.86)
    p.text("HAWKS", F_BLACK, 0.17, 0.5, 0.82, anchor="mm", maxw=0.86)
    p.text("原宿ホークス", F_JP, 0.06, 0.5, 0.92, "#a8ffcc", anchor="mm")


@ad("TeamDragons", "W")
def team_dragons(p):
    p.linear([(0, "#140a20"), (1, "#05020a")], 0)
    p.blob(0.78, 0.5, 0.45, "#a03aff", 0.4)
    team_mark(p, 0.78, 0.5, 0.48, "shield", "#7a1ad8", "D")
    p.text("AKIBA", F_LIGHT, 0.1, 0.04, 0.4, track=0.4, maxw=0.55)
    p.text("DRAGONS", F_BLACK, 0.18, 0.04, 0.66, maxw=0.55)
    p.text("秋葉原ドラゴンズ ・ 今季も熱く", F_JP, 0.05, 0.045, 0.84, "#d8b0ff", maxw=0.55)


@ad("NewJerseys", "L")
def new_jerseys(p):
    p.linear([(0, "#f2f2f4"), (1, "#d8dbe2")], 90)
    jersey(p, 0.17, 0.5, 0.55, "#1a4aff", "#ffffff", "23", "STORM")
    jersey(p, 0.42, 0.53, 0.55, "#c81e1e", "#ffffff", "11", "TITANS")
    p.text("NEW", F_THIN, 0.12, 0.96, 0.32, "#14161c", anchor="rs")
    p.text("JERSEYS", F_BLACK, 0.12, 0.96, 0.48, "#14161c", anchor="rs")
    p.text("2099 HOME & AWAY", F_SEMI, 0.04, 0.96, 0.58, "#e8401a", anchor="rs", track=0.2)
    p.text("新ユニフォーム登場", F_JP, 0.045, 0.96, 0.7, "#3a3f4a", anchor="rs")


@ad("HexBall", "Q")
def hex_ball(p):
    p.linear([(0, "#141414"), (1, "#050505")], 90)
    p.blob(0.5, 0.42, 0.45, ORANGE, 0.35)
    p.basketball(0.5, 0.42, 0.28)
    p.logo("hex", "HEX", 0.075, 0.07, 0.06, acc=ORANGE)
    p.text("OFFICIAL GAME BALL", F_BLACK, 0.065, 0.5, 0.85, anchor="mm", track=0.1)
    p.text("公式試合球", F_JP, 0.05, 0.5, 0.92, "#ffc49a", anchor="mm")


@ad("SwishDrink", "T")
def swish(p):
    p.linear([(0, "#00122a"), (1, "#00040c")], 90)
    p.blob(0.5, 0.42, 0.6, "#00c8ff", 0.45)
    for _ in range(40):
        p.blob(p.rng.uniform(0.1, 0.9), p.rng.uniform(0.15, 0.7), p.rng.uniform(0.005, 0.014), "#bff4ff", 0.6)
    p.can(0.5, 0.42, 0.42, 0.42, "#00a8e8", "#ffffff")
    p.text("SWISH", F_ITAL, 0.11, 0.5, 0.45, "#0a2a5a", anchor="mm")
    p.text("HYDRATE.", F_BLACK, 0.12, 0.5, 0.78, anchor="mm", maxw=0.86)
    p.text("PLAY LONGER.", F_LIGHT, 0.08, 0.5, 0.85, "#9ce6ff", anchor="mm", maxw=0.86)
    p.text("スポーツドリンク", F_JP, 0.06, 0.5, 0.93, anchor="mm")


@ad("BounceEnergy", "V")
def bounce(p):
    p.linear([(0, "#1a0a00"), (1, "#060200")], 90)
    p.blob(0.5, 0.42, 0.5, "#ffb000", 0.45)
    p.bottle(0.5, 0.43, 0.3, 0.46, "#4a2a00", "#ff9a00")
    p.text("BOUNCE", F_BLACK, 0.13, 0.5, 0.8, "#ffd040", anchor="mm", maxw=0.86)
    p.text("ENERGY FOR THE 4TH QUARTER", F_SEMI, 0.035, 0.5, 0.86, anchor="mm", track=0.15, maxw=0.86)
    p.text("エナジードリンク", F_JP, 0.05, 0.5, 0.93, "#ffd890", anchor="mm")


@ad("HexcoreShoes", "W")
def hexcore(p):
    p.linear([(0, "#ffffff"), (1, "#e6e8ee")], 0)
    for i in range(5):
        x = 0.5 + i * 0.1
        L = Image.new("L", (p.W, p.H), 0)
        ImageDraw.Draw(L).polygon([(p.X(x), p.H), (p.X(x + 0.05), p.H), (p.X(x + 0.2), 0), (p.X(x + 0.15), 0)], fill=255)
        m = p._mask(L) * 0.9
        p.a = p.a * (1 - m) + C(["#e8401a", "#ff7a3a", "#14161c", "#e8401a", "#ffb070"][i]) * m
    p.basketball(0.82, 0.62, 0.16)
    p.logo("hex", "HEXCORE", 0.04, 0.08, 0.07, col="#14161c", acc="#e8401a")
    p.text("PLAY", F_ITAL, 0.2, 0.04, 0.55, "#14161c")
    p.text("FASTER", F_ITAL, 0.2, 0.04, 0.8, "#e8401a")
    p.text("新作バッシュ", F_JP, 0.05, 0.045, 0.92, "#3a3f4a")


@ad("HexTV", "L")
def hex_tv(p):
    p.linear([(0, "#05050a"), (1, "#151520")], 90)
    p.a[int(p.Y(0.12)):int(p.Y(0.7)), int(p.X(0.08)):int(p.X(0.92))] = C("#0e1a2a")
    court_lines(p, "#3a6aaa", 0.0)
    p.blob(0.5, 0.4, 0.4, "#2a6aff", 0.3)
    p.basketball(0.5, 0.41, 0.13)
    p.text("ON AIR", F_BLACK, 0.05, 0.11, 0.2, "#ff3030")
    p.text("HEX TV", F_BLACK, 0.15, 0.5, 0.83, anchor="mm")
    p.text("EVERY GAME ・ 全試合生中継", F_JP, 0.05, 0.5, 0.93, "#a8c4ff", anchor="mm")


@ad("FreeThrow", "X3")
def free_throw(p):
    p.linear([(0, "#0a0602"), (1, "#2a1206")], 0)
    p.blob(0.85, 0.5, 0.7, ORANGE, 0.4)
    p.basketball(0.86, 0.5, 0.36)
    p.text("FREE THROW", F_BLACK, 0.3, 0.03, 0.55, maxw=0.62)
    p.text("CHALLENGE ・ フリースロー大会", F_JP, 0.14, 0.03, 0.85, "#ffc49a", maxw=0.62)


@ad("SeasonOne", "X3")
def season_one(p):
    p.linear([(0, "#060a18"), (1, "#14244a")], 0)
    p.logo("hex", "HEX!", 0.025, 0.2, 0.22, acc=ORANGE)
    p.text("SEASON 1 IS HERE", F_BLACK, 0.3, 0.97, 0.55, anchor="rs", maxw=0.68)
    p.text("新シーズン開幕 ・ PLAY NOW AT THE PLAZA", F_JP, 0.13, 0.97, 0.85, "#a8c4ff", anchor="rs", maxw=0.68)


@ad("HexTraining", "X3")
def hex_training(p):
    p.linear([(0, "#001a14"), (1, "#003a2a")], 0)
    for i in range(14):
        p.streak(0.45 + i * 0.04, 0.95, 0.55 + i * 0.04, 0.05, "#3affb0", w=0.002, k=0.4, glow=0.01)
    p.text("TRAIN", F_ITAL, 0.42, 0.03, 0.62, maxw=0.4)
    p.text("LIKE A PRO ・ 毎日練習", F_JP, 0.14, 0.03, 0.88, "#a8ffd8", maxw=0.45)
    p.text("HEX GYM", F_BLACK, 0.2, 0.97, 0.6, anchor="rs")


@ad("GameNight", "W")
def game_night(p):
    p.linear([(0, "#04040a"), (1, "#0c0618")], 90)
    for i in range(8):
        p.streak(0.1 + i * 0.11, -0.1, 0.5, 0.9, "#ffffff", w=0.003, k=0.25, glow=0.05)
    p.blob(0.5, 0.95, 0.5, ORANGE, 0.4)
    p.text("GAME", F_BLACK, 0.26, 0.5, 0.48, anchor="ms")
    p.text("NIGHT", F_THIN, 0.2, 0.5, 0.72, ORANGE, anchor="ms", track=0.3)
    p.text("毎週金曜 ・ HEX プラザ", F_JP, 0.05, 0.5, 0.88, anchor="mm")


# ================================================================== city life (Shibuya)
@ad("RamenIchiban", "X3")
def ramen(p):
    p.linear([(0, "#2a0306"), (1, "#5a0a0e")], 0)
    p.blob(0.88, 0.5, 0.6, "#ff9a3a", 0.35)
    p.text("ラーメン一番", F_JP, 0.55, 0.03, 0.8, maxw=0.6)
    p.text("TONKOTSU", F_BLACK, 0.2, 0.7, 0.5, "#ffd27a", maxw=0.27)
    p.text("SINCE 1987", F_MED, 0.12, 0.7, 0.8, track=0.3, maxw=0.27)


@ad("Karaoke", "S3")
def karaoke(p):
    p.linear([(0, "#ff2a6a"), (1, "#7a0a30")], 90)
    p.vtext("カラオケ", F_JP, 0.5, 0.5, 0.05)
    p.rule(0.2, 0.83, 0.8, "#ffffff", 0.01)
    p.text("KARAOKE", F_BLACK, 0.16, 0.5, 0.89, anchor="mm", maxw=0.88)
    p.text("24H", F_MED, 0.12, 0.5, 0.95, "#ffe0ea", anchor="mm")


@ad("Konbini", "Q")
def konbini(p):
    p.linear([(0, "#ffffff"), (1, "#e8eef4")], 90)
    for i, c in enumerate(("#16a34a", "#2563eb", "#e11d48")):
        p.a[int(p.Y(0.08 + i * 0.05)):int(p.Y(0.11 + i * 0.05))] = C(c)
    p.text("KONBINI", F_BLACK, 0.16, 0.5, 0.5, "#0b1020", anchor="mm")
    p.text("24", F_THIN, 0.3, 0.5, 0.74, "#e11d48", anchor="mm")
    p.text("いつでも、そばに。", F_JP, 0.05, 0.5, 0.92, "#334155", anchor="mm")


@ad("KissaCafe", "V")
def kissa(p):
    p.linear([(0, "#f2e6d6"), (1, "#d8c2a6")], 90)
    p.sphere(0.5, 0.38, 0.22, "#5a3418", light=(-0.5, -0.7), spec=0.3)
    p.ring(0.5, 0.38, 0.27, "#ffffff", w=0.01, k=0.9, glow=0.002)
    p.text("喫茶", F_JP, 0.16, 0.5, 0.72, "#3a2010", anchor="mm")
    p.text("RENOIR COFFEE", F_BOLD, 0.06, 0.5, 0.84, "#5a3418", anchor="mm", track=0.25, maxw=0.86)
    p.text("since 1964", F_LIGHT, 0.045, 0.5, 0.9, "#7a5a3a", anchor="mm")


@ad("Hanabi", "Q")
def hanabi(p):
    p.linear([(0, "#02000a"), (1, "#0c0218")], 90)
    for (cx, cy, col) in ((0.3, 0.28, "#ff3a8a"), (0.7, 0.22, "#3ad8ff"), (0.52, 0.45, "#ffd24a")):
        for k in range(36):
            t = 2 * math.pi * k / 36
            r = p.rng.uniform(0.14, 0.2)
            p.streak(cx + 0.03 * math.cos(t), cy + 0.03 * math.sin(t), cx + r * math.cos(t), cy + r * math.sin(t), col,
                     w=0.002, k=0.6, glow=0.01)
        p.blob(cx, cy, 0.05, col, 0.6)
    p.text("花火大会", F_JP, 0.14, 0.5, 0.77, anchor="mm")
    p.text("SUMMER FIREWORKS FESTIVAL", F_BOLD, 0.04, 0.5, 0.87, "#9fe6ff", anchor="mm", track=0.2)


@ad("AikoTour", "T")
def aiko(p):
    p.linear([(0, "#1a0a2a"), (1, "#05020a")], 90)
    for i in range(7):
        p.streak(0.5, 0.0, 0.1 + i * 0.13, 0.75, "#ff8ad8" if i % 2 else "#8a7aff", w=0.006, k=0.3, glow=0.06)
    p.particles(70, "#ffffff", 0, 0, 1, 0.7, 0.004, 0.8)
    p.text("AIKO", F_BLACK, 0.4, 0.5, 0.72, anchor="ms")
    p.text("ARENA TOUR", F_SEMI, 0.07, 0.5, 0.79, "#ffd0f0", anchor="mm", track=0.25, maxw=0.86)
    p.text("夜を歌う", F_JP, 0.09, 0.5, 0.92, anchor="mm")


@ad("TitanMovie", "L")
def titan(p):
    p.linear([(0, "#020208"), (1, "#0a0f24")], 0)
    p.blob(0.7, 0.42, 0.6, "#ff3a2a", 0.35)
    p.sphere(0.7, 0.45, 0.24, "#1a0a10", light=(0.4, -0.5), spec=0.4, rim="#ff5a3a", rim_k=1.4)
    p.logo("tri", "STUDIO KAZE", 0.04, 0.07, 0.065, acc="#ff5a3a")
    p.text("TITAN", F_BLACK, 0.2, 0.04, 0.62, maxw=0.5)
    p.text("IN CINEMAS ・ 劇場公開", F_JP, 0.05, 0.045, 0.75, "#ffb3bb", maxw=0.5)


@ad("WelcomeShibuya", "W")
def welcome(p):
    p.linear([(0, "#ffffff"), (1, "#eef2ff")], 90)
    for _ in range(26):
        x, y, r = p.rng.uniform(0, 1), p.rng.uniform(0, 1), p.rng.uniform(0.03, 0.08)
        p.ring(x, y, r, ["#e8401a", "#2a6aff", "#ff5aa0", "#16a34a"][int(p.rng.integers(0, 4))], w=0.006, k=0.5,
               glow=0.001)
    p.text("WELCOME", F_BLACK, 0.2, 0.5, 0.5, "#14161c", anchor="ms")
    p.text("TO SHIBUYA", F_LIGHT, 0.1, 0.5, 0.68, "#2a6aff", anchor="ms", track=0.3)
    p.text("ようこそ渋谷へ", F_JP, 0.06, 0.5, 0.86, "#3a3f4a", anchor="mm")


@ad("MatchaTea", "S3")
def matcha(p):
    p.linear([(0, "#e8f2e0"), (1, "#b8d4a4")], 90)
    p.vtext("緑茶", F_JP, 0.55, 0.5, 0.05, "#1a4a1a")
    p.rule(0.25, 0.83, 0.75, "#1a4a1a", 0.008)
    p.text("MATCHA", F_BLACK, 0.17, 0.5, 0.89, "#1a4a1a", anchor="mm", maxw=0.86)
    p.text("宇治", F_JP, 0.12, 0.5, 0.95, "#3a6a2a", anchor="mm")


@ad("SkyDeck", "S3")
def skydeck(p):
    p.linear([(0, "#0a2a5a"), (0.6, "#ff9a5a"), (1, "#2a0a1a")], 90)
    p.blob(0.5, 0.62, 0.6, "#ffd090", 0.4)
    x = 0.0
    while x < 1:
        w, h = p.rng.uniform(0.06, 0.16), p.rng.uniform(0.08, 0.25)
        m = ((p.xx >= p.X(x)) & (p.xx < p.X(x + w)) & (p.yy > p.Y(0.8 - h)) & (p.yy < p.Y(0.8)))[..., None]
        p.a = np.where(m, C("#1a0a1a"), p.a)
        x += w + 0.01
    p.text("SKY", F_BLACK, 0.3, 0.5, 0.15, anchor="mm")
    p.text("DECK", F_LIGHT, 0.18, 0.5, 0.21, anchor="mm", track=0.3)
    p.text("展望台", F_JP, 0.16, 0.5, 0.9, anchor="mm")


@ad("BigSale", "X3")
def big_sale(p):
    p.linear([(0, "#e8001a"), (1, "#b0000e")], 0)
    p.text("大売出し", F_JP, 0.55, 0.03, 0.8, maxw=0.45)
    p.text("SUMMER SALE", F_BLACK, 0.3, 0.97, 0.55, anchor="rs", maxw=0.45)
    p.text("DEPARTMENT STORE 7F–B1", F_MED, 0.11, 0.97, 0.85, "#ffe0e0", anchor="rs", maxw=0.45)


@ad("HexArena", "V")
def hex_arena(p):
    p.linear([(0, "#05060c"), (1, "#14182a")], 90)
    for i in range(12):
        t = math.pi * (0.1 + 0.8 * i / 11)
        p.streak(0.5 + 0.48 * math.cos(t), 0.02, 0.5 + 0.1 * math.cos(t), 0.62, "#ffffff", w=0.002, k=0.25, glow=0.04)
    p.blob(0.5, 0.62, 0.35, ORANGE, 0.35)
    hoop(p, 0.5, 0.38, 0.36)
    p.logo("hex", "HEX ARENA", 0.07, 0.04, 0.07, acc=ORANGE)
    p.text("FEEL THE CROWD", F_BLACK, 0.085, 0.5, 0.82, anchor="mm", maxw=0.86)
    p.text("満員御礼", F_JP, 0.06, 0.5, 0.91, "#ffc49a", anchor="mm")


@ad("HeadphonesBeat", "V")
def beat(p):
    p.linear([(0, "#ece8f4"), (1, "#c8c0dc")], 90)
    L = Image.new("L", (p.W, p.H), 0)
    d = ImageDraw.Draw(L)
    cx, cy, r = p.X(0.5), p.Y(0.42), 0.3 * p.u
    d.arc([cx - r, cy - r, cx + r, cy + r], 180, 360, fill=255, width=int(0.05 * p.u))
    m = p._mask(L)
    p.a = p.a * (1 - m) + C("#14161c") * m
    for sx in (-1, 1):
        p.sphere(0.5 + sx * 0.3 * p.u / p.W, 0.5, 0.11, "#e8401a", light=(-0.4, -0.6), spec=0.6)
    p.text("BEAT", F_BLACK, 0.17, 0.5, 0.82, "#14161c", anchor="mm")
    p.text("HEAR EVERY BOUNCE", F_MED, 0.045, 0.5, 0.89, "#e8401a", anchor="mm", track=0.25, maxw=0.86)


@ad("StreetFood", "L")
def street_food(p):
    p.linear([(0, "#1a0805"), (1, "#060201")], 90)
    for i in range(10):
        x, y = 0.08 + i * 0.095, 0.14 + 0.03 * math.sin(i)
        p.blob(x, y, 0.05, "#ff3a2a", 0.9)
        p.blob(x, y, 0.025, "#ffd27a", 0.9)
    p.text("たこ焼き", F_JP, 0.2, 0.5, 0.58, anchor="mm")
    p.text("YATAI STREET", F_BLACK, 0.09, 0.5, 0.76, "#ffd27a", anchor="mm", track=0.2)
    p.text("屋台 ・ 毎晩 18:00から", F_JP, 0.05, 0.5, 0.88, anchor="mm")


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.startswith("AD_") and f.endswith(".png"):
            os.remove(os.path.join(OUT, f))
    meta = []
    for i, (name, (fmt, fn)) in enumerate(ADS.items()):
        p = K.Poster(fmt, 12000 + i)
        fn(p)
        img = p.finish()
        img.save(f"{OUT}/AD_{name}.png", optimize=True)
        meta.append((name, fmt, img.size))
    with open(os.path.join(OUT, "..", "ads_index.txt"), "w") as f:
        for m in meta:
            f.write(f"AD_{m[0]}\t{m[1]}\t{m[2][0]}x{m[2][1]}\n")
    from collections import Counter
    print("wrote", len(meta), "ads", Counter(m[1] for m in meta))


if __name__ == "__main__":
    main()
