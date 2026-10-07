"""
export_roblox.py - build a Roblox-Studio-ready FBX of the cyberpunk HEX City.

Roblox can't run Blender shaders, so the cyberpunk look is rebuilt in Roblox by
the Luau scripts in roblox/CyberpunkCity.rbxmx. This script prepares the mesh:

  * every object is split by material, so each Roblox MeshPart has one job, and
    renamed with a tag suffix the Luau scripts look for:
        __bld  __street  __concrete  __led  __screen  __sign  __signlit
  * concrete/building/street parts lose the flat palette texture and get world
    space box-projected UVs, so Roblox's own Concrete/Asphalt materials tile
    properly on them instead of smearing
  * transforms are applied, so imported MeshParts are axis aligned
  * billboard screen placement data (per atlas island) is written to
    roblox/BillboardData.lua, and a window-grid texture is shipped inside the
    FBX on a small carrier mesh so Roblox uploads it automatically

Usage:
  blender -b -P blender/export_roblox.py -- assets/HEX_City_00_FULL_CITY.fbx roblox/
"""

import math
import os
import random
import re
import sys
from collections import defaultdict

import bpy  # must precede bmesh when running as the bpy module
import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cyberpunk_city as cc  # noqa: E402  (classification shared with the Blender look)

UV_METERS = 8.0  # one material tile per 8 m
SEED = 2077
CARRIER_NAME = "CP_TextureCarrier_Windows"
CARRIER_SIZE = 10.0  # metres; Roblox side measures it to learn the stud scale

KIND_TAG = {"building": "bld", "street": "street", "concrete": "concrete", "led": "led"}
MAT_TAG = {"Screen_Atlas": "screen", "SignV_Lit": "signlit", "SignH_Lit": "signlit",
           "SignV": "sign", "SignH": "sign"}
GROUP_OF_TAG = {"bld": "Buildings", "street": "Streets", "concrete": "Props", "led": "NeonLED",
                "screen": "Billboards", "sign": "Signs", "signlit": "Signs"}
FLAT_COLORS = {"bld": (0.18, 0.18, 0.2), "street": (0.08, 0.08, 0.09),
               "concrete": (0.45, 0.44, 0.42), "led": (0.0, 0.85, 1.0)}


def to_roblox(v):
    """Blender Z-up vector -> Roblox Y-up (what the FBX Y-up export does)."""
    return (v.x, v.z, -v.y)


def flatten_and_classify():
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    for o in [o for o in bpy.data.objects if o.type != "MESH"]:
        bpy.data.objects.remove(o)

    lo, hi = cc.world_bounds(meshes)
    building_h = max(8.0, 0.15 * (hi.z - lo.z))
    kinds = {o.name: cc.classify(o, 1.0, building_h) for o in meshes}

    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.make_single_user(object=True, obdata=True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return kinds


def split_by_material(kinds):
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="MATERIAL")
    bpy.ops.object.mode_set(mode="OBJECT")

    pieces = [o for o in bpy.data.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.material_slot_remove_unused()

    tagged = []
    for o in pieces:
        origin = o.name if o.name in kinds else re.sub(r"\.\d{3,}$", "", o.name)
        mat = o.material_slots[0].material if o.material_slots else None
        tag = MAT_TAG.get(cc.base_name(mat.name) if mat else "", None)
        if tag is None:
            tag = KIND_TAG[kinds.get(origin, "concrete")]
        tagged.append((o, origin, tag))
    for o, origin, tag in tagged:  # rename after the loop so origin lookup stays valid
        o.name = f"{origin}__{tag}"
        o.data.name = o.name
    return tagged


def box_uvs(obj):
    """Replace UVs with world-space box projection (location is still unapplied)."""
    me = obj.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    me.uv_layers.new(name="UVMap")
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    loc = obj.location
    for f in bm.faces:
        n = f.normal
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        for loop in f.loops:
            p = loop.vert.co + loc
            if az >= ax and az >= ay:
                u, v = p.x, p.y
            elif ax >= ay:
                u, v = p.y, p.z
            else:
                u, v = p.x, p.z
            loop[uv].uv = (u / UV_METERS, v / UV_METERS)
    bm.to_mesh(me)
    bm.free()


def plain_material(tag, cache={}):
    if tag not in cache:
        m = bpy.data.materials.new(f"CP_{tag}")
        m.diffuse_color = (*FLAT_COLORS[tag], 1.0)
        g = cc.Graph(m)
        g.finish(FLAT_COLORS[tag], 0.9)
        cache[tag] = m
    return cache[tag]


def screen_panels(obj, rng):
    """Placement data for billboard screens.

    Faces are clustered into flat panels (same plane). Panels whose atlas rects
    touch (e.g. the strips of a curved screen) form one group that scrolls as a
    single image. Each panel records which fraction of its group's rect it shows.
    """
    me = obj.data
    uvl = me.uv_layers.active
    if not uvl:
        return None
    loc = obj.location
    lo = Vector([min(c[i] for c in obj.bound_box) for i in range(3)])
    hi = Vector([max(c[i] for c in obj.bound_box) for i in range(3)])
    bb_center = loc + (lo + hi) / 2

    clusters = defaultdict(list)
    for p in me.polygons:
        n = p.normal
        if abs(n.z) > 0.7:
            continue
        key = (round(n.x, 2), round(n.y, 2), round(n.z, 2), round(p.center.dot(n), 1))
        clusters[key].append(p)

    panels = []
    for polys in clusters.values():
        n = polys[0].normal.copy()
        big = max(polys, key=lambda p: p.area)
        li = list(big.loop_indices)[:3]
        p0, p1, p2 = (me.vertices[me.loops[i].vertex_index].co for i in li)
        t0, t1, t2 = (uvl.data[i].uv for i in li)
        e1, e2 = p1 - p0, p2 - p0
        du1, dv1, du2, dv2 = t1.x - t0.x, t1.y - t0.y, t2.x - t0.x, t2.y - t0.y
        det = du1 * dv2 - du2 * dv1
        if abs(det) < 1e-12:
            continue
        tangent = (e1 * dv2 - e2 * dv1) / det  # dP/du
        bitangent = (e2 * du1 - e1 * du2) / det  # dP/dv
        right = (tangent - n * tangent.dot(n)).normalized()
        up = n.cross(right)
        if bitangent.dot(up) <= 0:  # mirrored mapping; skip rather than show it upside down
            continue
        pts = [me.vertices[v].co + loc for p in polys for v in p.vertices]
        rs = [q.dot(right) for q in pts]
        us = [q.dot(up) for q in pts]
        uvs = [uvl.data[i].uv for p in polys for i in p.loop_indices]
        panels.append({
            "area": sum(p.area for p in polys), "n": n, "right": right,
            "center": right * (min(rs) + max(rs)) / 2 + up * (min(us) + max(us)) / 2
                      + n * max(q.dot(n) for q in pts),
            "w": max(rs) - min(rs), "h": max(us) - min(us),
            "rect": (min(t.x for t in uvs), min(t.y for t in uvs),
                     max(t.x for t in uvs), max(t.y for t in uvs)),
        })
    if not panels:
        return None
    biggest = max(p["area"] for p in panels)
    panels = [p for p in panels if p["area"] >= 0.15 * biggest]

    # Group panels whose atlas rects touch and that face roughly the same way
    parent = list(range(len(panels)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    eps = 1e-3
    for i, a in enumerate(panels):
        for j in range(i + 1, len(panels)):
            b = panels[j]
            ra, rb = a["rect"], b["rect"]
            touch = (ra[0] <= rb[2] + eps and rb[0] <= ra[2] + eps
                     and ra[1] <= rb[3] + eps and rb[1] <= ra[3] + eps)
            if touch and a["n"].dot(b["n"]) > 0.3:
                parent[find(i)] = find(j)

    groups, gindex = [], {}
    for i, p in enumerate(panels):
        root = find(i)
        if root not in gindex:
            gindex[root] = len(groups)
            groups.append([])
        groups[gindex[root]].append(p)

    out_groups, out_panels = [], []
    for gi, members in enumerate(groups):
        u0 = min(p["rect"][0] for p in members)
        v0 = min(p["rect"][1] for p in members)
        u1 = max(p["rect"][2] for p in members)
        v1 = max(p["rect"][3] for p in members)
        uw, vh = max(u1 - u0, 1e-6), max(v1 - v0, 1e-6)
        ref = max(members, key=lambda p: p["area"])
        mpu = ref["w"] / max(ref["rect"][2] - ref["rect"][0], 1e-6)
        mpv = ref["h"] / max(ref["rect"][3] - ref["rect"][1], 1e-6)
        out_groups.append({"uv": (u0, v0, uw, vh),
                           "s": rng.uniform(0.08, 0.2) * rng.choice((-1, 1)),
                           "ax": "X" if uw * mpu >= vh * mpv else "Y"})
        for p in members:
            r = p["rect"]
            out_panels.append({
                "g": gi + 1, "o": to_roblox(p["center"] - bb_center), "n": to_roblox(p["n"]),
                "r": to_roblox(p["right"]), "w": p["w"], "h": p["h"],
                # fraction of the group rect shown: x0, x1 (left->right), y0, y1 (top->bottom)
                "f": ((r[0] - u0) / uw, (r[2] - u0) / uw, (v1 - r[3]) / vh, (v1 - r[1]) / vh),
            })
    return {"groups": out_groups, "panels": out_panels}


def lua_num(x):
    return f"{x:.4f}".rstrip("0").rstrip(".") if x != 0 else "0"


def lua_vec(v):
    return "{" + ",".join(lua_num(c) for c in v) + "}"


def write_billboard_data(path, screens):
    lines = [
        "-- Generated by blender/export_roblox.py. Billboard screen placement, in metres,",
        "-- relative to each __screen MeshPart's bounding-box centre (Roblox axes).",
        f"return {{ carrierMeters = {lua_num(CARRIER_SIZE)}, screens = {{",
    ]
    for name in sorted(screens):
        obj, data = screens[name]
        size = tuple(abs(c) for c in to_roblox(obj.dimensions))
        groups = ", ".join(f"{{uv={lua_vec(g['uv'])},s={lua_num(g['s'])},ax=\"{g['ax']}\"}}"
                           for g in data["groups"])
        panels = ", ".join(
            f"{{g={p['g']},o={lua_vec(p['o'])},n={lua_vec(p['n'])},r={lua_vec(p['r'])},"
            f"w={lua_num(p['w'])},h={lua_num(p['h'])},f={lua_vec(p['f'])}}}" for p in data["panels"])
        lines.append(f'\t["{name}"] = {{size={lua_vec(size)}, groups={{{groups}}}, panels={{{panels}}}}},')
    lines.append("}}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def make_window_texture(outdir, rng):
    """256x512 tile = 4 windows x 4 floors. Lit windows opaque, dark glass translucent."""
    W, H, cols, rows = 256, 512, 4, 4
    px = [0.0] * (W * H * 4)
    cw, ch = W // cols, H // rows
    palette = [(1.0, 0.78, 0.5)] * 6 + [(1.0, 0.9, 0.75)] * 3 + [(0.3, 0.9, 1.0), (1.0, 0.3, 0.75)]
    for cy in range(rows):
        for cx in range(cols):
            lit = rng.random() < 0.4
            col = rng.choice(palette) if lit else (0.03, 0.05, 0.09)
            a = 1.0 if lit else 0.55
            x0, x1 = cx * cw + int(cw * 0.16), cx * cw + int(cw * 0.84)
            y0, y1 = cy * ch + int(ch * 0.22), cy * ch + int(ch * 0.8)
            for y in range(y0, y1):
                for x in range(x0, x1):
                    i = (y * W + x) * 4
                    px[i:i + 4] = (*col, a)
    img = bpy.data.images.new("cp_windows", W, H, alpha=True)
    img.pixels.foreach_set(px)
    os.makedirs(os.path.join(outdir, "textures"), exist_ok=True)
    path = os.path.join(outdir, "textures", "cp_windows.png")
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    return img


def make_carrier(img):
    me = bpy.data.meshes.new(CARRIER_NAME)
    s = CARRIER_SIZE / 2
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for i, c in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = c
    obj = bpy.data.objects.new(CARRIER_NAME, me)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (0, 0, -200)
    m = bpy.data.materials.new(CARRIER_NAME)
    g = cc.Graph(m)
    g.finish(g.image(img, g.new("ShaderNodeTexCoord").outputs["UV"]), 0.5)
    me.materials.append(m)
    return obj


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) < 2:
        raise SystemExit("usage: blender -b -P export_roblox.py -- input.fbx outdir/")
    fbx, outdir = os.path.abspath(argv[0]), os.path.abspath(argv[1])
    os.makedirs(outdir, exist_ok=True)
    rng = random.Random(SEED)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fbx)
    kinds = flatten_and_classify()
    pieces = split_by_material(kinds)

    groups = {}
    screens = {}
    counts = defaultdict(int)
    for obj, _origin, tag in pieces:
        counts[tag] += 1
        if tag in FLAT_COLORS:
            box_uvs(obj)
            obj.data.materials.clear()
            obj.data.materials.append(plain_material(tag))
        elif tag == "screen":
            data = screen_panels(obj, rng)
            if data:
                screens[obj.name] = (obj, data)
        group = GROUP_OF_TAG[tag]
        if group not in groups:
            groups[group] = bpy.data.objects.new(group, None)
            bpy.context.scene.collection.objects.link(groups[group])
        obj.parent = groups[group]

    make_carrier(make_window_texture(outdir, rng))
    write_billboard_data(os.path.join(outdir, "BillboardData.lua"), screens)

    out = os.path.join(outdir, "HEX_City_Cyberpunk_Roblox.fbx")
    bpy.ops.export_scene.fbx(
        filepath=out, object_types={"MESH", "EMPTY"}, apply_unit_scale=True,
        bake_space_transform=True, path_mode="COPY", embed_textures=True,
        mesh_smooth_type="FACE", add_leaf_bones=False, bake_anim=False)
    print(f"[roblox] parts per tag: {dict(counts)}; screens with data: {len(screens)}")
    print(f"[roblox] wrote {out}")


if __name__ == "__main__":
    main()
