"""
cyberpunk_city.py - turn HEX_City_00_FULL_CITY.fbx into a neon cyberpunk city.

What it does
  * Every surface that used the flat HEX_Palette material gets a procedural
    concrete material (grain, stains, rain streaks, formwork seams, bump),
    still tinted by the original palette colour so districts keep identity.
    - Streets/ground get a dark wet asphalt-concrete with reflective puddles.
    - Towers/buildings get dark weathered concrete plus glowing window grids
      (random lit/unlit per window), neon floor bands and a neon roof crown,
      one accent colour per building (cyan / magenta / purple / amber / ...).
  * Billboards (Screen_Atlas) are animated: each screen scrolls its own ad
    inside its atlas cell, with LED pixel grid, rolling scan bar, hue drift,
    flicker, occasional glitch tearing and short blackouts. Every billboard
    is offset in time so they never move in sync.
  * Neon signs (SignV/H_Lit) glow and breathe; ~18% of them buzz like faulty
    tubes. Unlit signs get a dim backlight.
  * Night world, optional volumetric haze, bloom, AgX look, a camera if the
    scene has none, and a looping 10 s timeline.

Procedural materials and drivers do not survive FBX export, so the result is
saved as a .blend (render it, or bake it for a game engine).

Usage (Blender 4.2+ / 5.x):
  blender -b -P blender/cyberpunk_city.py -- HEX_City_00_FULL_CITY.fbx [out.blend]
          [--still preview.png] [--spin-landmarks] [--no-fog] [--scale 0.01]
or import the FBX in Blender and run this file from the Text Editor; it then
works on the current scene and does not save anything.
"""

import math
import os
import random
import re
import sys
from collections import defaultdict

import bpy
from mathutils import Vector

FPS = 24
LOOP_SECONDS = 10
SEED = 2077

BILLBOARD_MAT = "Screen_Atlas"
SIGN_LIT_MATS = ("SignV_Lit", "SignH_Lit")
SIGN_MATS = ("SignV", "SignH")
# Object classification, tested in this order against the object name.
SIGNAGE_RE = re.compile(r"^(Billboard|Sign)_")
LED_RE = re.compile(r"_LED(\.\d+)?$")
PROP_RE = re.compile(r"HVAC|Vent|Vending|SatDish|Antenna|CoolingTower|Tank|Pipe|Pole|LightMast|"
                     r"UtilityLines|Stair|Railing|Fence|Bench|Lamp", re.I)
STREET_RE = re.compile(r"street|road|ground|plaza|sidewalk|pavement|terrain|asphalt|crosswalk|_floor", re.I)
BUILDING_RE = re.compile(r"^(FG|MG|Skyline)_|tower|building|bldg|skyscraper|apartment|office|hotel", re.I)

NEON = [
    (0.00, 0.85, 1.00),  # cyan
    (1.00, 0.05, 0.55),  # magenta
    (0.55, 0.10, 1.00),  # purple
    (1.00, 0.45, 0.02),  # amber
    (0.20, 1.00, 0.35),  # acid green
    (1.00, 0.08, 0.10),  # red
]


# --------------------------------------------------------------------------
# Small node-graph helper
# --------------------------------------------------------------------------

class Graph:
    def __init__(self, mat):
        if bpy.app.version < (5, 0, 0) and not mat.use_nodes:  # always on in 5.x
            mat.use_nodes = True
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.count = 0

    def new(self, idname, inputs=None, **props):
        n = self.nt.nodes.new(idname)
        n.location = ((self.count // 12) * 220 - 4000, -(self.count % 12) * 170)
        self.count += 1
        for k, v in props.items():
            setattr(n, k, v)
        for k, v in (inputs or {}).items():
            self.set(n.inputs[k], v)
        return n

    def set(self, sock, v):
        if v is None:
            return
        if isinstance(v, bpy.types.NodeSocket):
            self.nt.links.new(v, sock)
            return
        if sock.type == "VECTOR" and isinstance(v, (int, float)):
            v = (v, v, v)
        if sock.type == "RGBA" and isinstance(v, (int, float)):
            v = (v, v, v, 1.0)
        if sock.type == "RGBA" and len(v) == 3:
            v = (*v, 1.0)
        sock.default_value = v

    @staticmethod
    def sock(sockets, ident):
        for s in sockets:
            if s.identifier == ident:
                return s
        raise KeyError(ident)

    # math -----------------------------------------------------------------
    def math(self, op, a, b=0.0, c=0.0, clamp=False):
        n = self.new("ShaderNodeMath", operation=op, use_clamp=clamp)
        self.set(n.inputs[0], a)
        self.set(n.inputs[1], b)
        self.set(n.inputs[2], c)
        return n.outputs[0]

    def vmath(self, op, a, b=0.0, scale=None):
        n = self.new("ShaderNodeVectorMath", operation=op)
        self.set(n.inputs[0], a)
        self.set(n.inputs[1], b)
        if scale is not None:
            self.set(n.inputs[3], scale)
        if op in ("DOT_PRODUCT", "LENGTH", "DISTANCE"):
            return n.outputs["Value"]
        return n.outputs["Vector"]

    def in_range(self, x, lo, hi):
        return self.math("MULTIPLY", self.math("GREATER_THAN", x, lo), self.math("LESS_THAN", x, hi))

    def map_range(self, v, a, b, c=0.0, d=1.0):
        n = self.new("ShaderNodeMapRange", clamp=True)
        self.set(n.inputs["Value"], v)
        self.set(n.inputs["From Min"], a)
        self.set(n.inputs["From Max"], b)
        self.set(n.inputs["To Min"], c)
        self.set(n.inputs["To Max"], d)
        return n.outputs["Result"]

    def separate(self, v):
        n = self.new("ShaderNodeSeparateXYZ")
        self.set(n.inputs[0], v)
        return n.outputs

    def combine(self, x=0.0, y=0.0, z=0.0):
        n = self.new("ShaderNodeCombineXYZ")
        self.set(n.inputs["X"], x)
        self.set(n.inputs["Y"], y)
        self.set(n.inputs["Z"], z)
        return n.outputs[0]

    # mixing ---------------------------------------------------------------
    def mix_color(self, fac, a, b, blend="MIX"):
        n = self.new("ShaderNodeMix", data_type="RGBA", blend_type=blend)
        self.set(self.sock(n.inputs, "Factor_Float"), fac)
        self.set(self.sock(n.inputs, "A_Color"), a)
        self.set(self.sock(n.inputs, "B_Color"), b)
        return self.sock(n.outputs, "Result_Color")

    def mix_float(self, fac, a, b):
        n = self.new("ShaderNodeMix", data_type="FLOAT")
        self.set(self.sock(n.inputs, "Factor_Float"), fac)
        self.set(self.sock(n.inputs, "A_Float"), a)
        self.set(self.sock(n.inputs, "B_Float"), b)
        return self.sock(n.outputs, "Result_Float")

    def mix_vec(self, fac, a, b):
        n = self.new("ShaderNodeMix", data_type="VECTOR")
        self.set(self.sock(n.inputs, "Factor_Float"), fac)
        self.set(self.sock(n.inputs, "A_Vector"), a)
        self.set(self.sock(n.inputs, "B_Vector"), b)
        return self.sock(n.outputs, "Result_Vector")

    def scale_color(self, col, f):
        """col * f, where f is a float socket or number (allows HDR > 1)."""
        return self.vmath("SCALE", col, scale=f)

    # textures -------------------------------------------------------------
    def noise(self, vec, scale=1.0, detail=2.0, rough=0.5):
        n = self.new("ShaderNodeTexNoise", noise_dimensions="3D",
                     inputs={"Scale": scale, "Detail": detail, "Roughness": rough})
        self.set(n.inputs["Vector"], vec)
        return n.outputs["Fac"]

    def noise1d(self, w, scale=1.0, detail=1.0):
        n = self.new("ShaderNodeTexNoise", noise_dimensions="1D",
                     inputs={"Scale": scale, "Detail": detail})
        self.set(n.inputs["W"], w)
        return n.outputs["Fac"]

    def white(self, vec):
        n = self.new("ShaderNodeTexWhiteNoise", noise_dimensions="3D")
        self.set(n.inputs["Vector"], vec)
        return n.outputs["Value"]

    def ramp(self, fac, stops, interp="LINEAR"):
        n = self.new("ShaderNodeValToRGB")
        cr = n.color_ramp
        cr.interpolation = interp
        first, last = stops[0], stops[-1]
        cr.elements[0].position, cr.elements[0].color = first[0], (*first[1], 1.0)
        cr.elements[1].position, cr.elements[1].color = last[0], (*last[1], 1.0)
        for pos, col in stops[1:-1]:
            cr.elements.new(pos).color = (*col, 1.0)
        self.set(n.inputs["Fac"], fac)
        return n.outputs["Color"]

    def image(self, img, vec, interp="Linear"):
        n = self.new("ShaderNodeTexImage", interpolation=interp)
        n.image = img
        self.set(n.inputs["Vector"], vec)
        return n.outputs["Color"]

    def attr(self, name, kind="GEOMETRY"):
        return self.new("ShaderNodeAttribute", attribute_type=kind, attribute_name=name).outputs

    # inputs ---------------------------------------------------------------
    def time(self):
        """Scene time in seconds, driven by the current frame."""
        n = self.new("ShaderNodeValue")
        fc = n.outputs[0].driver_add("default_value")
        fc.driver.type = "SCRIPTED"
        fc.driver.expression = f"frame / {FPS}"
        return n.outputs[0]

    def finish(self, base, rough, metal=0.0, normal=None, emission=None):
        p = self.new("ShaderNodeBsdfPrincipled")
        self.set(p.inputs["Base Color"], base)
        self.set(p.inputs["Roughness"], rough)
        self.set(p.inputs["Metallic"], metal)
        self.set(p.inputs["Normal"], normal)
        emit_name = "Emission Color" if "Emission Color" in p.inputs else "Emission"
        if emission is not None:
            self.set(p.inputs[emit_name], emission)
            self.set(p.inputs["Emission Strength"], 1.0)
        out = self.new("ShaderNodeOutputMaterial")
        self.nt.links.new(p.outputs["BSDF"], out.inputs["Surface"])


# --------------------------------------------------------------------------
# Shared shader building blocks
# --------------------------------------------------------------------------

def surface_inputs(g, world_scale):
    geo = g.new("ShaderNodeNewGeometry")
    pos = g.vmath("SCALE", geo.outputs["Position"], scale=world_scale)
    return pos, geo.outputs["Normal"]


def box_coords(g, pos, nrm):
    """2D coordinates projected along the dominant normal axis (walls vs floors)."""
    p = g.separate(pos)
    n = g.separate(nrm)
    ax = g.math("ABSOLUTE", n["X"])
    ay = g.math("ABSOLUTE", n["Y"])
    az = g.math("ABSOLUTE", n["Z"])
    wall = g.mix_vec(g.math("GREATER_THAN", ay, ax),
                     g.combine(p["Y"], p["Z"]), g.combine(p["X"], p["Z"]))
    is_floor = g.math("GREATER_THAN", az, 0.7)
    return g.mix_vec(is_floor, wall, g.combine(p["X"], p["Y"])), is_floor


def concrete(g, pos, nrm, palette, lo, hi, tint, panel=(3.0, 1.5), puddles=0.0):
    """Procedural concrete. Returns dict(color, rough, height, is_floor, uv2, z)."""
    uv2, is_floor = box_coords(g, pos, nrm)
    is_wall = g.math("SUBTRACT", 1.0, is_floor)

    big = g.noise(pos, scale=0.08, detail=4.0, rough=0.6)
    fine = g.noise(pos, scale=6.0, detail=8.0, rough=0.7)
    grit = g.noise(pos, scale=45.0, detail=2.0, rough=0.5)

    col = g.ramp(big, [(0.3, lo), (0.7, hi)])
    col = g.mix_color(0.55, col, g.ramp(fine, [(0.35, (0.45, 0.45, 0.45)), (0.65, (1, 1, 1))]), "MULTIPLY")
    col = g.mix_color(0.25, col, g.ramp(grit, [(0.4, (0.7, 0.7, 0.7)), (0.6, (1, 1, 1))]), "MULTIPLY")

    # Voronoi stains / patches
    vor = g.new("ShaderNodeTexVoronoi", inputs={"Scale": 0.6, "Randomness": 1.0})
    g.set(vor.inputs["Vector"], pos)
    stain = g.map_range(g.math("MULTIPLY", g.noise(pos, 0.9, 3.0), vor.outputs["Distance"]), 0.15, 0.45, 0.0, 0.35)
    col = g.mix_color(stain, col, (0.35, 0.33, 0.30), "MULTIPLY")

    # Vertical rain streaks on walls
    streak = g.noise(g.vmath("MULTIPLY", pos, (1.6, 1.6, 0.04)), scale=1.0, detail=3.0)
    streak = g.math("MULTIPLY", g.map_range(streak, 0.5, 0.72, 0.0, 0.55), is_wall)
    col = g.mix_color(streak, col, (0.25, 0.25, 0.27), "MULTIPLY")

    # Formwork panel seams
    cell = g.vmath("FRACTION", g.vmath("DIVIDE", uv2, (panel[0], panel[1], 1.0)))
    c = g.separate(cell)
    seam = g.math("MAXIMUM",
                  g.math("LESS_THAN", c["X"], 0.03 / panel[0]),
                  g.math("LESS_THAN", c["Y"], 0.03 / panel[1]))
    col = g.mix_color(g.math("MULTIPLY", seam, 0.6), col, (0.2, 0.2, 0.2), "MULTIPLY")

    # Keep a hint of the original palette colour
    if palette is not None:
        col = g.mix_color(tint, col, palette, "MULTIPLY")

    rough = g.map_range(fine, 0.3, 0.7, 0.72, 0.92)
    height = g.math("SUBTRACT", g.math("ADD", g.math("MULTIPLY", fine, 0.6),
                                       g.math("MULTIPLY", grit, 0.4)), seam)

    if puddles > 0.0:
        pn = g.noise(pos, scale=0.06, detail=3.0)
        mask = g.math("MULTIPLY", is_floor, g.map_range(pn, 0.62 - puddles * 0.12, 0.65 - puddles * 0.12))
        col = g.mix_color(g.math("MULTIPLY", mask, 0.7), col, (0.2, 0.2, 0.22), "MULTIPLY")
        rough = g.mix_float(mask, rough, 0.03)
        height = g.mix_float(mask, height, 0.5)

    return {"color": col, "rough": rough, "height": height, "is_floor": is_floor,
            "is_wall": is_wall, "uv2": uv2, "z": g.separate(pos)["Z"]}


def bump(g, height, strength=0.25):
    b = g.new("ShaderNodeBump", inputs={"Strength": strength, "Distance": 0.05})
    g.set(b.inputs["Height"], height)
    return b.outputs["Normal"]


def palette_color(g, img):
    if img is None:
        return None
    uv = g.new("ShaderNodeTexCoord").outputs["UV"]
    return g.image(img, uv, interp="Closest")


def find_image(mat):
    if mat is None or not mat.node_tree:
        return None
    for n in mat.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image:
            return n.image
    return None


# --------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------

def make_concrete_material(name, img, world_scale):
    m = bpy.data.materials.new(name)
    g = Graph(m)
    pos, nrm = surface_inputs(g, world_scale)
    c = concrete(g, pos, nrm, palette_color(g, img),
                 lo=(0.20, 0.20, 0.20), hi=(0.48, 0.47, 0.45), tint=0.45, puddles=0.5)
    g.finish(c["color"], c["rough"], normal=bump(g, c["height"]))
    return m


def make_asphalt_material(name, img, world_scale):
    m = bpy.data.materials.new(name)
    g = Graph(m)
    pos, nrm = surface_inputs(g, world_scale)
    c = concrete(g, pos, nrm, palette_color(g, img),
                 lo=(0.035, 0.035, 0.04), hi=(0.12, 0.12, 0.13), tint=0.2,
                 panel=(6.0, 6.0), puddles=1.0)
    g.finish(c["color"], c["rough"], normal=bump(g, c["height"], 0.35))
    return m


def make_building_material(name, img, world_scale):
    m = bpy.data.materials.new(name)
    g = Graph(m)
    t = g.time()
    pos, nrm = surface_inputs(g, world_scale)
    c = concrete(g, pos, nrm, palette_color(g, img),
                 lo=(0.12, 0.12, 0.13), hi=(0.34, 0.33, 0.34), tint=0.25,
                 panel=(4.0, 3.6), puddles=0.6)
    wall = c["is_wall"]

    rnd = g.new("ShaderNodeObjectInfo").outputs["Random"]
    rnd2 = g.math("FRACT", g.math("MULTIPLY", rnd, 7.31))
    rnd3 = g.math("FRACT", g.math("MULTIPLY", rnd, 13.7))
    accent = g.ramp(rnd, [(i / len(NEON), col) for i, col in enumerate(NEON)], interp="CONSTANT")

    # Window grid: random lit / dark per window, occupancy varies per building
    cell = g.vmath("DIVIDE", c["uv2"], (1.8, 3.6, 1.0))
    f = g.separate(g.vmath("FRACTION", cell))
    win = g.math("MULTIPLY", g.math("MULTIPLY", g.in_range(f["X"], 0.16, 0.84),
                                    g.in_range(f["Y"], 0.22, 0.80)), wall)
    cid = g.vmath("ADD", g.vmath("FLOOR", cell), g.combine(0.0, 0.0, g.math("MULTIPLY", rnd, 100.0)))
    w1 = g.white(cid)
    w2 = g.white(g.vmath("ADD", cid, (5.3, 1.1, 0.0)))
    lit = g.math("MULTIPLY", win, g.math("GREATER_THAN", w1, g.math("ADD", 0.62, g.math("MULTIPLY", rnd2, 0.3))))
    win_col = g.mix_color(g.math("GREATER_THAN", w2, 0.72), (1.0, 0.78, 0.5), accent)
    win_emit = g.scale_color(win_col, g.math("MULTIPLY", lit, g.math("ADD", 0.8, g.math("MULTIPLY", w2, 1.7))))

    # Neon floor bands + roof crown, gently pulsing
    spacing = g.math("ADD", 10.0, g.math("MULTIPLY", rnd3, 25.0))
    fz = g.math("MULTIPLY", g.math("FRACT", g.math("DIVIDE", c["z"], spacing)), spacing)
    band = g.math("MULTIPLY", g.math("LESS_THAN", fz, 0.35), wall)
    top = g.math("MULTIPLY", g.attr("cp_top", "OBJECT")["Fac"], world_scale)
    crown = g.math("MULTIPLY", g.in_range(c["z"], g.math("SUBTRACT", top, 1.0),
                                          g.math("SUBTRACT", top, 0.25)), wall)
    neon = g.math("MAXIMUM", band, crown)
    pulse = g.math("ADD", 0.65, g.math("MULTIPLY", 0.35, g.math(
        "SINE", g.math("ADD", g.math("MULTIPLY", t, 1.5), g.math("MULTIPLY", rnd, 20.0)))))
    neon_emit = g.scale_color(accent, g.math("MULTIPLY", g.math("MULTIPLY", neon, pulse), 14.0))

    emission = g.vmath("ADD", win_emit, neon_emit)
    base = g.mix_color(win, c["color"], (0.02, 0.025, 0.035))
    base = g.mix_color(neon, base, accent)
    rough = g.mix_float(win, c["rough"], 0.08)
    metal = g.math("MULTIPLY", win, 0.6)
    normal = bump(g, g.math("MULTIPLY", c["height"], g.math("SUBTRACT", 1.0, win)))
    g.finish(base, rough, metal, normal, emission)
    return m


def make_led_material(name, img, world_scale):
    """Neon LED strips on building facades with a light pulse chasing along them."""
    m = bpy.data.materials.new(name)
    g = Graph(m)
    t = g.time()
    pos, _ = surface_inputs(g, world_scale)
    rnd = g.new("ShaderNodeObjectInfo").outputs["Random"]
    accent = g.ramp(rnd, [(i / len(NEON), col) for i, col in enumerate(NEON)], interp="CONSTANT")
    p = g.separate(pos)
    along = g.math("ADD", g.math("ADD", p["X"], p["Y"]), g.math("MULTIPLY", p["Z"], 0.5))
    phase = g.math("SUBTRACT", g.math("MULTIPLY", along, 0.4),
                   g.math("MULTIPLY", t, g.math("ADD", 4.0, g.math("MULTIPLY", rnd, 6.0))))
    chase = g.math("POWER", g.math("ADD", 0.5, g.math("MULTIPLY", 0.5, g.math("SINE", phase))), 6.0)
    strength = g.math("ADD", 2.0, g.math("MULTIPLY", chase, 18.0))
    g.finish(g.scale_color(accent, 0.2), 0.3, emission=g.scale_color(accent, strength))
    return m


def make_billboard_material(img):
    """Animated screen. Each atlas island scrolls inside its own UV rect."""
    m = bpy.data.materials.new("CP_Billboard_Animated")
    g = Graph(m)
    t = g.time()
    rnd = g.new("ShaderNodeObjectInfo").outputs["Random"]
    tt = g.math("ADD", t, g.math("MULTIPLY", rnd, 37.0))  # per-object time offset

    uv = g.new("ShaderNodeTexCoord").outputs["UV"]
    rmin = g.attr("cp_rect_min")["Vector"]
    rsize_raw = g.attr("cp_rect_size")["Vector"]
    scroll = g.attr("cp_scroll")["Vector"]
    has_rect = g.math("GREATER_THAN", g.separate(rsize_raw)["X"], 0.0)
    rsize = g.vmath("MAXIMUM", rsize_raw, 1e-5)

    local = g.vmath("DIVIDE", g.vmath("SUBTRACT", uv, rmin), rsize)
    ly = g.separate(local)["Y"]
    moved = g.vmath("ADD", local, g.vmath("SCALE", scroll, scale=tt))

    # Glitch: brief horizontal line tearing
    gate = g.math("GREATER_THAN", g.noise1d(g.math("MULTIPLY", tt, 1.7)), 0.66)
    jit = g.noise(g.combine(0.0, g.math("MULTIPLY", ly, 25.0), g.math("MULTIPLY", tt, 15.0)), detail=0.0)
    jit = g.math("MULTIPLY", g.math("SUBTRACT", jit, 0.5), g.math("MULTIPLY", gate, 0.25))
    moved = g.vmath("ADD", moved, g.combine(jit))

    wrapped = g.vmath("FRACTION", moved)
    anim_uv = g.vmath("ADD", rmin, g.vmath("MULTIPLY", wrapped, rsize))
    col = g.image(img, g.mix_vec(has_rect, uv, anim_uv)) if img else g.ramp(rnd, [(0, NEON[0]), (1, NEON[1])])

    # Hue drift
    hs = g.new("ShaderNodeHueSaturation")
    g.set(hs.inputs["Hue"], g.math("ADD", 0.5, g.math("MULTIPLY", 0.06, g.math("SINE", g.math("MULTIPLY", tt, 0.4)))))
    g.set(hs.inputs["Saturation"], 1.15)
    g.set(hs.inputs["Color"], col)
    col = hs.outputs["Color"]

    # LED pixel grid, rolling scan bar, flicker, rare blackout
    w = g.separate(wrapped)
    led = g.math("MULTIPLY",
                 g.math("ABSOLUTE", g.math("SINE", g.math("MULTIPLY", w["X"], math.pi * 160))),
                 g.math("ABSOLUTE", g.math("SINE", g.math("MULTIPLY", w["Y"], math.pi * 90))))
    led = g.math("ADD", 0.65, g.math("MULTIPLY", led, 0.35))
    bar = g.math("POWER", g.math("FRACT", g.math("ADD", ly, g.math("MULTIPLY", tt, 0.3))), 30.0)
    bar = g.math("ADD", 1.0, g.math("MULTIPLY", bar, 1.5))
    flick = g.math("ADD", 0.8, g.math("MULTIPLY", g.noise1d(g.math("MULTIPLY", tt, 6.0)), 0.4))
    blackout = g.math("SUBTRACT", 1.0, g.math("MULTIPLY", 0.85, g.math(
        "LESS_THAN", g.noise1d(g.math("ADD", g.math("MULTIPLY", tt, 0.9), 13.0)), 0.3)))
    glow = g.math("ADD", 3.0, g.attr("cp_glow", "OBJECT")["Fac"])

    strength = g.math("MULTIPLY", g.math("MULTIPLY", g.math("MULTIPLY", led, bar),
                                         g.math("MULTIPLY", flick, blackout)), glow)
    g.finish(g.scale_color(col, 0.15), 0.25, emission=g.scale_color(col, strength))
    return m


def make_sign_material(src, lit):
    m = bpy.data.materials.new(f"CP_{src.name.split('.')[0]}")
    g = Graph(m)
    img = find_image(src)
    rnd = g.new("ShaderNodeObjectInfo").outputs["Random"]
    if img:
        col = g.image(img, g.new("ShaderNodeTexCoord").outputs["UV"])
    else:
        col = g.ramp(rnd, [(i / len(NEON), c) for i, c in enumerate(NEON)], interp="CONSTANT")

    if lit:
        t = g.time()
        tt = g.math("ADD", t, g.math("MULTIPLY", rnd, 50.0))
        faulty = g.math("GREATER_THAN", rnd, 0.82)
        buzz = g.math("GREATER_THAN", g.noise1d(g.math("MULTIPLY", tt, 9.0)), 0.38)
        flick = g.mix_float(faulty, 1.0, buzz)
        breathe = g.math("ADD", 0.85, g.math("MULTIPLY", 0.15, g.math("SINE", g.math("MULTIPLY", tt, 2.0))))
        emission = g.scale_color(col, g.math("MULTIPLY", g.math("MULTIPLY", flick, breathe), 6.0))
    else:
        emission = g.scale_color(col, 0.6)
    g.finish(g.scale_color(col, 0.3), 0.35, emission=emission)
    return m


# --------------------------------------------------------------------------
# Billboard UV-rect tagging
# --------------------------------------------------------------------------

def tag_billboard_mesh(me, atlas_slots, rng):
    """Store per-face UV rect + scroll direction for each connected atlas island."""
    uvl = me.uv_layers.active
    if not uvl:
        return
    polys = [p for p in me.polygons if p.material_index in atlas_slots]
    if not polys:
        return

    parent = {p.index: p.index for p in polys}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    owner = {}
    for p in polys:
        for v in p.vertices:
            if v in owner:
                parent[find(p.index)] = find(owner[v])
            else:
                owner[v] = p.index

    islands = defaultdict(list)
    for p in polys:
        islands[find(p.index)].append(p)

    n = len(me.polygons)
    rmin, rsize, scroll = [0.0] * (3 * n), [0.0] * (3 * n), [0.0] * (3 * n)
    for isl in islands.values():
        us, vs, cos = [], [], []
        for p in isl:
            for li in p.loop_indices:
                u, v = uvl.data[li].uv
                us.append(u)
                vs.append(v)
            cos.extend(me.vertices[i].co for i in p.vertices)
        u0, v0 = min(us), min(vs)
        w, h = max(max(us) - u0, 1e-5), max(max(vs) - v0, 1e-5)
        dx = max(c.x for c in cos) - min(c.x for c in cos)
        dy = max(c.y for c in cos) - min(c.y for c in cos)
        dz = max(c.z for c in cos) - min(c.z for c in cos)
        speed = rng.uniform(0.1, 0.25) * rng.choice((-1.0, 1.0))
        sx, sy = (speed, 0.0) if max(dx, dy) >= dz else (0.0, speed)
        for p in isl:
            i = p.index * 3
            rmin[i:i + 3] = (u0, v0, 0.0)
            rsize[i:i + 3] = (w, h, 0.0)
            scroll[i:i + 3] = (sx, sy, 0.0)

    for name, data in (("cp_rect_min", rmin), ("cp_rect_size", rsize), ("cp_scroll", scroll)):
        if name in me.attributes:
            me.attributes.remove(me.attributes[name])
        a = me.attributes.new(name, "FLOAT_VECTOR", "FACE")
        a.data.foreach_set("vector", data)


# --------------------------------------------------------------------------
# Scene
# --------------------------------------------------------------------------

def world_bounds(objs):
    lo = Vector((1e18, 1e18, 1e18))
    hi = -lo
    for o in objs:
        for c in o.bound_box:
            p = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, p))
            hi = Vector(map(max, hi, p))
    return lo, hi


def base_name(name):
    return re.sub(r"\.\d{3}$", "", name)


def setup_scene(scene, lo, hi, fog, world_scale):
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = FPS * LOOP_SECONDS

    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    for attr, val in (("use_raytracing", True), ("use_shadows", True), ("use_bloom", True)):
        try:
            setattr(scene.eevee, attr, val)
        except Exception:
            pass
    try:
        scene.view_settings.view_transform = "AgX"
        for look in ("AgX - Punchy", "Punchy"):
            try:
                scene.view_settings.look = look
                break
            except TypeError:
                continue
    except Exception:
        pass

    # Night sky + optional haze
    world = scene.world or bpy.data.worlds.new("CP_World")
    scene.world = world
    g = Graph(world)
    bg = g.new("ShaderNodeBackground", inputs={"Color": (0.035, 0.03, 0.08, 1.0), "Strength": 1.0})
    out = g.new("ShaderNodeOutputWorld")
    g.nt.links.new(bg.outputs[0], out.inputs["Surface"])
    if fog:
        extent = max((hi - lo).length * world_scale, 1.0)
        vol = g.new("ShaderNodeVolumePrincipled",
                    inputs={"Color": (0.35, 0.25, 0.6, 1.0), "Density": 1.2 / extent})
        g.nt.links.new(vol.outputs[0], out.inputs["Volume"])

    setup_bloom(scene)

    # Cool moonlight so the concrete reads between the neon
    if not any(o.type == "LIGHT" for o in scene.objects):
        moon = bpy.data.objects.new("CP_Moon", bpy.data.lights.new("CP_Moon", "SUN"))
        moon.data.energy = 2.5
        moon.data.color = (0.55, 0.65, 1.0)
        moon.data.angle = math.radians(2.0)
        moon.rotation_euler = (math.radians(50), 0.0, math.radians(35))
        scene.collection.objects.link(moon)

    if scene.camera is None:
        center = (lo + hi) / 2
        size = (hi - lo).length
        cam = bpy.data.objects.new("CP_Camera", bpy.data.cameras.new("CP_Camera"))
        scene.collection.objects.link(cam)
        cam.location = center + Vector((size * 0.22, -size * 0.22, size * 0.1))
        cam.data.lens = 35
        cam.data.clip_end = size * 4
        target = bpy.data.objects.new("CP_CameraTarget", None)
        scene.collection.objects.link(target)
        target.location = center
        con = cam.constraints.new("TRACK_TO")
        con.target = target
        scene.camera = cam


def setup_bloom(scene):
    """Glare/bloom in the compositor (EEVEE bloom was removed in 4.2)."""
    try:
        if hasattr(scene, "compositing_node_group"):  # Blender 5.x
            ng = bpy.data.node_groups.new("CP_Compositor", "CompositorNodeTree")
            ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
            scene.compositing_node_group = ng
            nodes, links = ng.nodes, ng.links
            out = nodes.new("NodeGroupOutput")
            out_sock = out.inputs[0]
        else:  # Blender 4.x
            scene.use_nodes = True
            nodes, links = scene.node_tree.nodes, scene.node_tree.links
            nodes.clear()
            out_sock = nodes.new("CompositorNodeComposite").inputs["Image"]
        rl = nodes.new("CompositorNodeRLayers")
        glare = nodes.new("CompositorNodeGlare")
        for prop, val in (("glare_type", "BLOOM"), ("quality", "HIGH"), ("threshold", 0.8), ("size", 8)):
            try:
                setattr(glare, prop, val)
            except Exception:
                pass
        for sock, val in (("Type", "Bloom"), ("Threshold", 0.8), ("Strength", 1.0), ("Size", 0.6)):
            if sock in glare.inputs:
                try:
                    glare.inputs[sock].default_value = val
                except Exception:
                    pass
        links.new(rl.outputs["Image"], glare.inputs["Image"])
        links.new(glare.outputs["Image"], out_sock)
    except Exception as exc:  # compositor API differs between versions; bloom is optional
        print(f"[cyberpunk] bloom skipped: {exc}")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"fbx": None, "out": None, "still": None, "spin": False, "fog": True, "scale": None}
    positional = []
    it = iter(argv)
    for a in it:
        if a == "--still":
            opts["still"] = next(it)
        elif a == "--spin-landmarks":
            opts["spin"] = True
        elif a == "--no-fog":
            opts["fog"] = False
        elif a == "--scale":
            opts["scale"] = float(next(it))
        else:
            positional.append(a)
    if positional:
        opts["fbx"] = os.path.abspath(positional[0])
    if len(positional) > 1:
        opts["out"] = os.path.abspath(positional[1])
    elif opts["fbx"]:
        opts["out"] = os.path.splitext(opts["fbx"])[0] + "_cyberpunk.blend"
    return opts


def classify(obj, world_scale, building_h):
    name = base_name(obj.name)
    dims = obj.dimensions * world_scale
    if SIGNAGE_RE.search(name):
        return "concrete"  # frames/backs of billboards and signs
    if LED_RE.search(name):
        return "led"
    if PROP_RE.search(name):
        return "concrete"
    if STREET_RE.search(name) or (dims.z < 5.0 and max(dims.x, dims.y) > 50.0):
        return "street"
    if BUILDING_RE.search(name) or (dims.z > building_h and dims.z > 0.8 * min(dims.x, dims.y)):
        return "building"
    return "concrete"


def import_fbx(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        bpy.ops.import_scene.fbx(filepath=path)
    except (AttributeError, RuntimeError):
        bpy.ops.wm.fbx_import(filepath=path)


def main():
    opts = parse_args()
    if opts["fbx"]:
        import_fbx(opts["fbx"])

    rng = random.Random(SEED)
    scene = bpy.context.scene
    meshes = [o for o in scene.objects if o.type == "MESH"]
    if not meshes:
        raise SystemExit("[cyberpunk] no mesh objects found")

    lo, hi = world_bounds(meshes)
    world_scale = opts["scale"] or (0.01 if (hi - lo).length > 5000 else 1.0)  # cm exports
    building_h = max(8.0, 0.15 * (hi.z - lo.z) * world_scale)

    # Source materials (shared by many objects)
    billboard_mat = None
    sign_mats = {}
    surface_cache = {}

    def surface_mat(kind, img):
        key = (kind, img.name if img else None)
        if key not in surface_cache:
            make = {"building": make_building_material, "street": make_asphalt_material,
                    "concrete": make_concrete_material, "led": make_led_material}[kind]
            surface_cache[key] = make(f"CP_{kind.title()}", img, world_scale)
        return surface_cache[key]

    tagged_meshes = set()
    stats = defaultdict(int)
    for obj in meshes:
        kind = classify(obj, world_scale, building_h)

        atlas_slots = set()
        if not obj.material_slots:
            obj.data.materials.append(surface_mat(kind, None))
        for i, slot in enumerate(obj.material_slots):
            src = slot.material
            key = base_name(src.name) if src else None
            if key == BILLBOARD_MAT:
                if billboard_mat is None:
                    billboard_mat = make_billboard_material(find_image(src))
                slot.material = billboard_mat
                atlas_slots.add(i)
            elif key in SIGN_LIT_MATS or key in SIGN_MATS:
                if key not in sign_mats:
                    sign_mats[key] = make_sign_material(src, key in SIGN_LIT_MATS)
                slot.material = sign_mats[key]
            elif src is None or not src.name.startswith("CP_"):
                slot.link = "OBJECT"  # mesh data can be shared between categories
                slot.material = surface_mat(kind, find_image(src))
                stats[kind] += 1

        if atlas_slots:
            stats["billboard"] += 1
            obj["cp_glow"] = 4.0 if re.search(r"Landmark|Large|Skyline", obj.name) else 1.5
            if obj.data.name not in tagged_meshes:
                tag_billboard_mesh(obj.data, atlas_slots, rng)
                tagged_meshes.add(obj.data.name)
            if opts["spin"] and "LandmarkCurved" in obj.name:
                fc = obj.driver_add("rotation_euler", 2)
                fc.driver.expression = f"{obj.rotation_euler.z:.5f} + frame / {FPS} * 0.3"
        if kind == "building":
            obj["cp_top"] = max((obj.matrix_world @ Vector(c)).z for c in obj.bound_box)

    setup_scene(scene, lo, hi, opts["fog"], world_scale)
    print(f"[cyberpunk] materials assigned: {dict(stats)}  (world scale {world_scale})")

    if opts["out"]:
        try:
            bpy.ops.file.pack_all()
        except RuntimeError as exc:
            print(f"[cyberpunk] could not pack images: {exc}")
        bpy.ops.wm.save_as_mainfile(filepath=opts["out"])
        print(f"[cyberpunk] saved {opts['out']}")
    if opts["still"]:
        scene.frame_set(FPS * 2)
        scene.render.filepath = os.path.abspath(opts["still"])
        bpy.ops.render.render(write_still=True)
        print(f"[cyberpunk] rendered {scene.render.filepath}")


if __name__ == "__main__":
    main()
