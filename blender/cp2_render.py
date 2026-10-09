"""HEX! Cyberpunk City v2 - night preview renders (Cycles) from Roblox player height and above.

    /opt/bvenv/bin/python blender/cp2_render.py <file.blend> <out_dir> [cam,cam,...] [--samples N] [--res WxH]

This approximates the intended Roblox night look (dark sky, Neon glow, lit screens, court
flood lights). Bloom/haze are added in the compositor-free post step below (numpy), so they
are not baked into any texture.
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
BLEND, OUT = argv[0], argv[1]
CAMS = argv[2].split(",") if len(argv) > 2 and not argv[2].startswith("--") else None
SAMPLES = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 48
RES = tuple(map(int, argv[argv.index("--res") + 1].split("x"))) if "--res" in argv else (1600, 900)

AMBIENT = float(argv[argv.index("--ambient") + 1]) if "--ambient" in argv else 0.22
EYE = 5.0  # Roblox avatar eye height (studs)
CAMERAS = {
    # name: (location, look-at, lens mm)
    "player_center_north": ((0, 40, EYE), (0, 500, 95), 16),
    "player_center_up_north": ((30, 230, EYE), (10, 520, 230), 14),
    "player_center_east": ((40, 0, EYE), (560, 30, 110), 16),
    "player_center_south": ((-20, 120, EYE), (40, -520, 80), 16),
    "player_center_west": ((-60, 40, EYE), (-560, 30, 110), 16),
    "player_corner_ne": ((260, 180, EYE), (590, 505, 130), 18),
    "player_corner_sw": ((-280, -150, EYE), (-590, -505, 110), 18),
    "player_street_north": ((260, 430, EYE), (-200, 452, 40), 16),
    "player_practice": ((0, -150, -16 + EYE), (0, -560, 90), 16),
    "player_landmark_north": ((-30, 395, EYE), (-30, 470, 170), 16),
    "player_drum_ne": ((470, 390, EYE), (590, 505, 110), 15),
    "detail_facade": ((-300, 400, 25), (-330, 470, 75), 26),
    "aerial_overview": ((1500, -2700, 1300), (0, 0, 60), 26),
    "player_side_street": ((150, 405, EYE), (150, 520, 30), 18),
    "rooftops_north": ((-150, 380, 230), (-260, 560, 120), 20),
    "aerial_skyline": ((0, -380, 260), (0, 900, 380), 18),
}


def setup_world(sc):
    w = bpy.data.worlds.get("CP_Night") or bpy.data.worlds.new("CP_Night")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs[2], ramp.inputs[0])
    cr = ramp.color_ramp
    cr.elements[0].position = 0.5
    cr.elements[0].color = (0.060, 0.030, 0.110, 1)
    cr.elements[1].position = 0.66
    cr.elements[1].color = (0.010, 0.012, 0.040, 1)
    nt.links.new(ramp.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = 1.0
    # ambient fill (= Roblox OutdoorAmbient) for lighting, dark sky for camera rays
    amb = nt.nodes.new("ShaderNodeBackground")
    amb.inputs[0].default_value = (0.11, 0.10, 0.22, 1)
    amb.inputs[1].default_value = AMBIENT
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(amb.outputs[0], mix.inputs[1])
    nt.links.new(bg.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    sc.world = w
    if not bpy.data.objects.get("CP_Moon"):
        ld = bpy.data.lights.new("CP_Moon", "SUN")
        ld.energy = 0.12
        ld.color = (0.55, 0.62, 1.0)
        ld.angle = math.radians(3)
        mo = bpy.data.objects.new("CP_Moon", ld)
        mo.rotation_euler = (math.radians(50), 0, math.radians(35))
        sc.collection.objects.link(mo)


def setup_render(sc):
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.cycles.max_bounces = 4
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 2
    sc.cycles.use_light_tree = True
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "AgX"
    for look in ("AgX - Punchy", "Punchy", "AgX - Medium High Contrast"):
        try:
            sc.view_settings.look = look
            break
        except Exception:
            continue
    sc.view_settings.exposure = 0.6
    sc.render.film_transparent = False
    vl = sc.view_layers[0]
    vl.use_pass_mist = True
    sc.world.mist_settings.start = 300
    sc.world.mist_settings.depth = 2600
    sc.world.mist_settings.falloff = "QUADRATIC"


def screen_spill():
    """Area light in front of every large screen, tinted with its artwork's average colour
    (the Blender stand-in for the SurfaceLight that CyberpunkSetup adds in Roblox)."""
    from PIL import Image
    cache = {}
    n = 0
    for o in list(bpy.data.objects):
        if not o.name.startswith("SCR_") or o.type != "MESH" or not o.data.materials:
            continue
        me = o.data
        area = sum(p.area for p in me.polygons)
        if area < 120:
            continue
        mat = me.materials[0]
        img = None
        for nd in mat.node_tree.nodes:
            if nd.type == "TEX_IMAGE" and nd.image:
                img = nd.image
        if img is None:
            continue
        if img.name not in cache:
            a = np.asarray(Image.open(bpy.path.abspath(img.filepath)).convert("RGB").resize((32, 32))).reshape(-1, 3)
            c = a.mean(0) / 255.0
            c = c / max(1e-3, c.max())
            cache[img.name] = c
        col = cache[img.name]
        p = max(me.polygons, key=lambda q: q.area)
        nrm = (o.matrix_world.to_3x3() @ p.normal).normalized()
        ctr = o.matrix_world @ p.center
        ld = bpy.data.lights.new(o.name + "_spill", "AREA")
        ld.shape = "RECTANGLE"
        ld.size = math.sqrt(area) * 0.9
        ld.size_y = math.sqrt(area) * 0.9
        ld.energy = area * 380.0
        ld.color = tuple(float(v) for v in col)
        lo = bpy.data.objects.new(o.name + "_spill", ld)
        lo.visible_camera = False
        lo.visible_glossy = False
        lo.location = ctr + nrm * 1.5
        lo.rotation_euler = nrm.to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.collection.objects.link(lo)
        n += 1
    print("screen spill lights:", n)


def look_at(cam, loc, tgt):
    cam.location = Vector(loc)
    d = (Vector(tgt) - Vector(loc)).normalized()
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def post(path):
    """Bloom + atmospheric haze in numpy (Blender preview only)."""
    from PIL import Image, ImageFilter
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32) / 255.0
    lum = a.max(axis=2)
    bright = np.clip((lum - 0.72) / 0.28, 0, 1)[..., None] * a
    b8 = Image.fromarray((bright * 255).astype(np.uint8))
    bl = np.zeros_like(a)
    for r, wgt in ((4, 0.55), (14, 0.45), (40, 0.35)):
        bl += np.asarray(b8.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255.0 * wgt
    out = 1 - (1 - a) * (1 - np.clip(bl, 0, 1))
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(path)


def main():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    sc = bpy.context.scene
    setup_world(sc)
    setup_render(sc)
    for o in bpy.data.objects:  # hide prototypes
        if o.get("cp_proto"):
            o.hide_render = True
    screen_spill()
    cam_d = bpy.data.cameras.new("PreviewCam")
    cam_d.clip_start = 0.5
    cam_d.clip_end = 8000
    cam = bpy.data.objects.new("PreviewCam", cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    os.makedirs(OUT, exist_ok=True)
    for name, (loc, tgt, lens) in CAMERAS.items():
        if CAMS and name not in CAMS:
            continue
        look_at(cam, loc, tgt)
        cam_d.lens = lens
        sc.render.filepath = os.path.join(OUT, name + ".png")
        bpy.ops.render.render(write_still=True)
        post(sc.render.filepath)
        print("rendered", sc.render.filepath, flush=True)


main()
