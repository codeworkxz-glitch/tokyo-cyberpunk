"""HEX! Cyberpunk City v2 - full rebuild of the city around the basketball park.

    /opt/bvenv/bin/python blender/cp2_build.py            (bpy module)
    blender -b -P blender/cp2_build.py                     (Blender 5.x)

Steps: import original FBX -> back it up -> record lots / sign cells -> delete old buildings,
signs, billboards and skyline blobs (the park is untouched) -> generate new foreground,
midground, skyline and megatowers -> save the editable .blend -> export
HEX_Cyberpunk_City_A.fbx / _B.fbx -> write Roblox data (screens, lights, alignment).
"""
import json
import math
import os
import random
import sys
import time

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cp2_lib as L  # noqa: E402
import cp2_arch as A  # noqa: E402
import cp2_arch2 as A2  # noqa: E402

ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "assets", "HEX_City_00_FULL_CITY.fbx")
EXPORT = os.path.join(ROOT, "export")
TEX = os.path.join(EXPORT, "textures")
OUT_BLEND = os.path.join(ROOT, "output", "HEX_Cyberpunk_City.blend")
BACKUP_BLEND = os.path.join(ROOT, "output", "HEX_City_00_original_backup.blend")
QUICK = "--quick" in sys.argv  # build only a slice (for tests)

REPLACE_PREFIX = ("FG_", "MG_", "Skyline_", "Sign_", "Billboard_")
t0 = time.time()


def log(*a):
    print(f"[{time.time() - t0:7.1f}s]", *a, flush=True)


def wbbox(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(c[i] for c in cs) for i in range(3)]), Vector([max(c[i] for c in cs) for i in range(3)])


# ----------------------------------------------------------------------------- import
def clean_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)


def import_original():
    clean_scene()
    bpy.ops.import_scene.fbx(filepath=SRC)
    for im in bpy.data.images:  # unpack the original atlases next to our textures
        if im.packed_file and im.filepath:
            base = os.path.basename(im.filepath)
            dst = os.path.join(TEX, base)
            if not os.path.exists(dst):
                with open(dst, "wb") as f:
                    f.write(im.packed_file.data)
    log("imported", len(bpy.data.objects), "objects")


def sign_cells():
    """UV rectangles of the original sign meshes = cells of signs_h / signs_v."""
    cells = {"SGH": set(), "SGV": set()}
    for o in bpy.data.objects:
        if not o.name.startswith("Sign_") or o.type != "MESH" or not o.data.materials:
            continue
        mn = o.data.materials[0].name if o.data.materials[0] else ""
        kind = "SGH" if mn.startswith("SignH") else ("SGV" if mn.startswith("SignV") else None)
        if not kind or not o.data.uv_layers:
            continue
        uv = o.data.uv_layers.active.data
        best = None
        for p in o.data.polygons:
            if best is None or p.area > best.area:
                best = p
        us = [uv[i].uv for i in best.loop_indices]
        r = (round(min(u.x for u in us), 4), round(min(u.y for u in us), 4),
             round(max(u.x for u in us), 4), round(max(u.y for u in us), 4))
        if r[2] - r[0] > 0.01 and r[3] - r[1] > 0.01:
            cells[kind].add(r)
    for k in cells:
        A.SIGN_CELLS[k] = sorted(cells[k])
    log("sign cells", {k: len(v) for k, v in cells.items()})


def collect_lots():
    fg, mg, corners = {}, [], {}
    for o in bpy.data.objects:
        if o.parent is not None or o.type != "MESH":
            continue
        n = o.name
        if n.startswith("FG_Corner_"):
            corners[n.split("_")[2]] = (n, *wbbox(o))
        elif n.startswith("FG_"):
            stem = n.replace("_Back", "")
            fg.setdefault(stem, []).append(o)
        elif n.startswith("MG_"):
            mg.append((n, *wbbox(o)))
    lots = []
    for stem, objs in sorted(fg.items()):
        main = [o for o in objs if o.name == stem]
        if not main:
            continue
        mn, mx = wbbox(main[0])
        un = Vector(mn); ux = Vector(mx)
        for o in objs:
            a, b = wbbox(o)
            un = Vector([min(un[i], a[i]) for i in range(3)])
            ux = Vector([max(ux[i], b[i]) for i in range(3)])
        row = stem.split("_")[1]
        kind = stem.split("_")[3]
        lots.append(dict(name=stem, row=row, kind=kind, main=(mn, mx), union=(un, ux)))
    return lots, mg, corners


def row_frame(row, mn, mx, umn=None, umx=None, inset=0.3):
    umn = umn or mn
    umx = umx or mx
    if row == "N":
        F = L.Frame((mn.x + inset, mn.y, 0), (1, 0, 0), (0, 1, 0)); W = mx.x - mn.x; D = umx.y - mn.y
    elif row == "S":
        F = L.Frame((mx.x - inset, mx.y, 0), (-1, 0, 0), (0, -1, 0)); W = mx.x - mn.x; D = mx.y - umn.y
    elif row == "E":
        F = L.Frame((mn.x, mx.y - inset, 0), (0, -1, 0), (1, 0, 0)); W = mx.y - mn.y; D = umx.x - mn.x
    else:
        F = L.Frame((mx.x, mn.y + inset, 0), (0, 1, 0), (-1, 0, 0)); W = mx.y - mn.y; D = mx.x - umn.x
    return F, W - 2 * inset, D


def corner_frame(tag, mn, mx):
    if tag == "NE":
        return L.Frame((mn.x, mn.y, 0), (1, 0, 0), (0, 1, 0)), mx.x - mn.x, mx.y - mn.y
    if tag == "NW":
        return L.Frame((mx.x, mn.y, 0), (0, 1, 0), (-1, 0, 0)), mx.y - mn.y, mx.x - mn.x
    if tag == "SE":
        return L.Frame((mn.x, mx.y, 0), (0, -1, 0), (1, 0, 0)), mx.y - mn.y, mx.x - mn.x
    return L.Frame((mx.x, mx.y, 0), (-1, 0, 0), (0, -1, 0)), mx.x - mn.x, mx.y - mn.y


def delete_old():
    kill = [o for o in bpy.data.objects if o.name.startswith(REPLACE_PREFIX)]
    for o in kill:
        bpy.data.objects.remove(o)
    for m in list(bpy.data.meshes):
        if m.users == 0:
            bpy.data.meshes.remove(m)
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)
    log("deleted", len(kill), "old building / sign / billboard / skyline objects")


# ----------------------------------------------------------------------------- build
def seed_of(s):
    h = 2166136261
    for ch in s:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


def make_ctx(bid, cg, cs, cp, hero=None):
    B = A.Ctx(bid, seed_of(bid), cg, cs, cp)
    if hero is not None:
        B.hero = hero
    else:
        r = B.rng.random()
        B.hero = 2 if r < 0.25 else (1 if r < 0.62 else 0)
    return B


def build_foreground(lots, corners, C):
    n = 0
    for lot in lots:
        if QUICK and lot["row"] != "N":
            continue
        F, W, D = row_frame(lot["row"], *lot["main"], *lot["union"])
        landmark = lot["kind"].startswith("Landmark")
        bid = "A_" + lot["name"][3:].replace("Landmark", "LM")
        B = make_ctx(bid, C["fg"], C["fg_scr"], C["fg_prop"], hero=3 if landmark else None)
        A.fg_lot(B, F, W, D, lot["kind"], landmark=landmark)
        B.finish()
        n += 1
    log("foreground lots:", n)
    builders = {"NE": A2.corner_drum, "NW": A2.corner_dept, "SE": A2.corner_wrap, "SW": A2.corner_round}
    for tag, (name, mn, mx) in corners.items():
        if QUICK and tag not in ("NE", "NW"):
            continue
        F, W, D = corner_frame(tag, mn, mx)
        B = make_ctx(f"A_Corner_{tag}", C["fg"], C["fg_scr"], C["fg_prop"], hero=3)
        builders[tag](B, F, W, D)
        B.finish()
    log("corner landmarks done")


def side_street_gates(lots, C):
    """Suspended advertisement panels across the four side streets (visible from the plaza)."""
    rows = {}
    for lot in lots:
        F, W, D = row_frame(lot["row"], *lot["main"], *lot["union"])
        rows.setdefault(lot["row"], []).append((lot, F, W, D))
    k = 0
    for row, items in rows.items():
        def along(it):
            F = it[1]
            return F.o.dot(F.ax)
        items.sort(key=along)
        for a, b in zip(items, items[1:]):
            Fa, Wa = a[1], a[2]
            end_a = Fa.w(Wa, 0, 0)
            start_b = b[1].o
            gap = (start_b - end_a).dot(Fa.ax)
            if gap > 30:
                depth = min(a[3], b[3])
                o = end_a + Fa.ay * 10
                F = L.Frame(o, Fa.ax, Fa.ay)
                B = make_ctx(f"A_Gate_{row}{k}", C["fg"], C["fg_scr"], C["fg_prop"], hero=2)
                A2.street_gate(B, F, gap, 50.0, 0)
                B.finish()
                k += 1
    log("side-street gates:", k)


def build_midground(mg, C):
    n = 0
    for (name, mn, mx) in sorted(mg):
        row = name.split("_")[1]
        if QUICK and row != "N":
            continue
        F, W, D = row_frame(row, mn, mx, inset=0.4)
        B = make_ctx("B_" + name[3:], C["mg"], C["mg_scr"], C["mg_prop"])
        A2.mg_lot(B, F, W, D)
        B.finish()
        n += 1
    log("midground lots:", n)


def ring_frame(x, y, inset=0.0):
    if abs(x) >= abs(y):
        if x > 0:
            return L.Frame((x, y, 0), (0, -1, 0), (1, 0, 0))
        return L.Frame((x, y, 0), (0, 1, 0), (-1, 0, 0))
    if y > 0:
        return L.Frame((x, y, 0), (1, 0, 0), (0, 1, 0))
    return L.Frame((x, y, 0), (-1, 0, 0), (0, -1, 0))


def build_skyline(C):
    rng = random.Random(2099)
    # megatowers on the outer ring
    megas = []
    nm = 12
    for i in range(nm):
        a = 2 * math.pi * (i + rng.uniform(-0.25, 0.25)) / nm + 0.2
        rad = rng.uniform(1260, 1400)
        x, y = rad * math.cos(a), rad * math.sin(a)
        k = max(abs(x), abs(y)) / rng.uniform(1300, 1420)
        x, y = x / k, y / k
        megas.append((x, y, rng.uniform(900, 1700), rng.uniform(55, 75)))
    if QUICK:
        megas = [m for m in megas if m[1] > 600]
    for i, (x, y, H, s) in enumerate(megas):
        B = make_ctx(f"B_Mega_{i + 1:02d}", C["bg"], C["bg_scr"], C["bg_prop"], hero=3)
        A2.mega_tower(B, ring_frame(x, y), H, s)
        B.finish()
    log("megatowers:", len(megas))
    # skyline grid - towers are merged per 400-stud sector (fewer parts, smaller FBX)
    n = 0
    step = 105.0
    g = int(1500 / step) + 1
    sectors = {}
    for i in range(-g, g + 1):
        for j in range(-g, g + 1):
            x = i * step + rng.uniform(-24, 24)
            y = j * step + rng.uniform(-24, 24)
            m = max(abs(x), abs(y))
            if m < 800 or m > 1465:
                continue
            if QUICK and y < 600:
                continue
            if any(math.hypot(x - mx_, y - my_) < ms * 1.6 + 40 for (mx_, my_, _, ms) in megas):
                continue
            if rng.random() < 0.1:
                continue
            near = m < 1080
            s = rng.uniform(16, 34) if near else rng.uniform(18, 38)
            H = rng.uniform(230, 520) + (m - 800) * rng.uniform(0.1, 0.45)
            if rng.random() < 0.12:
                H += rng.uniform(150, 300)
            key = (round(x / 400), round(y / 400), near)
            if key not in sectors:
                sectors[key] = make_ctx("B_Sky_%s%d_%s%d_%s" % ("E" if key[0] >= 0 else "W", abs(key[0]),
                                                                  "N" if key[1] >= 0 else "S", abs(key[1]),
                                                                  "near" if near else "far"),
                                        C["bg"], C["bg_scr"], C["bg_prop"])
            B = sectors[key]
            B.neon, B.neon2 = A.PALETTES[rng.randrange(len(A.PALETTES))]
            B.win_main = rng.choices(["WIN_WRM", "WIN_COL", "WIN_VIO", "WIN_PNK"], [6, 4, 1.2, 1])[0]
            F = ring_frame(x, y)
            A2.bg_tower(B, F, s, H, near)
            if near and rng.random() < 0.25:
                A2.bg_screen(B, F, s, H)
            n += 1
    for B in sectors.values():
        B.finish()
    log("skyline towers:", n)


# ----------------------------------------------------------------------------- organisation
def collections():
    sc = bpy.context.scene.collection
    A_ = L.coll("A_HEX_Cyberpunk_City_A")
    B_ = L.coll("B_HEX_Cyberpunk_City_B")
    C = {
        "map": L.coll("A_Preserved_BasketballMap", A_),
        "fg": L.coll("A_Foreground_Buildings", A_),
        "fg_scr": L.coll("A_Foreground_Screens", A_),
        "fg_prop": L.coll("A_Foreground_Props", A_),
        "mg": L.coll("B_Midground_Buildings", B_),
        "mg_scr": L.coll("B_Midground_Screens", B_),
        "mg_prop": L.coll("B_Midground_Props", B_),
        "bg": L.coll("B_Skyline_Buildings", B_),
        "bg_scr": L.coll("B_Skyline_Screens", B_),
        "bg_prop": L.coll("B_Skyline_Props", B_),
        "proto": L.coll("Z_Prototypes_NotExported"),
        "preview": L.coll("Z_BlenderPreview_NotExported"),
    }
    return C


def move_preserved(C):
    for o in list(bpy.data.objects):
        if o.type != "MESH" or o.name.startswith(("PROTO_",)):
            continue
        if o.users_collection and o.users_collection[0] == bpy.context.scene.collection:
            bpy.context.scene.collection.objects.unlink(o)
            C["map"].objects.link(o)
    log("preserved map objects:", len(C["map"].objects))


def markers(C):
    """4-stud origin cubes in both files + two 2-stud axis cubes in file A (+100 X, +100 Y) so the
    Roblox setup can recover offset, rotation and scale of the import."""
    F = L.Frame((0, 0, 0), (1, 0, 0), (0, 1, 0))
    for tag, col in (("A", C["map"]), ("B", C["bg"])):
        g = L.Geo()
        L.box(g, F, -2, -2, -62, 2, 2, -58, "CON")
        L.flush(g, f"HEX_ALIGN_{tag}", col)
    for tag, (x, y) in (("X", (100, 0)), ("Y", (0, 100))):
        g = L.Geo()
        L.box(g, F, x - 1, y - 1, -61, x + 1, y + 1, -59, "CON")
        L.flush(g, f"HEX_AXIS_{tag}", C["map"])


def blender_preview_lights(C):
    """Blender-only lights so the Cycles previews match the intended Roblox lighting."""
    col = C["preview"]
    for o in bpy.data.objects:
        if o.name.startswith("LightMast_Plaza") or o.name.startswith("LightMast_Practice"):
            mn, mx = wbbox(o)
            top = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mx.z - 1))
            target = Vector((0, -170 if "Practice" in o.name else 0, 0))
            ld = bpy.data.lights.new(o.name + "_spot", "SPOT")
            ld.energy = 1.3e6 if "Plaza" in o.name else 6e5
            ld.color = (0.85, 0.9, 1.0)
            ld.spot_size = math.radians(95)
            ld.spot_blend = 0.6
            ld.use_shadow = True
            lo = bpy.data.objects.new(o.name + "_spot", ld)
            lo.location = top
            d = (target - top).normalized()
            lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
            col.objects.link(lo)
            L.light(top, (215, 228, 255), 60, 3.0, kind="spot", direction=tuple(d), angle=70, name=o.name)


def write_data(path):
    def rb(v):  # Blender (x, y, z) -> Roblox (x, z, -y), studs
        return [round(v[0], 3), round(v[2], 3), round(-v[1], 3)]

    def lua_vec(v):
        return "{" + ",".join(f"{c:g}" for c in v) + "}"

    out = ["-- Generated by blender/cp2_build.py - HEX! Cyberpunk City v2 data (Roblox coordinates, studs).",
           "-- Positions assume both FBX files were imported without rescaling; CyberpunkSetup measures the",
           "-- HEX_ALIGN markers and corrects any offset / uniform scale automatically.",
           "return {",
           f"\tmarkerA = {lua_vec(rb((0, 0, -60)))}, markerB = {lua_vec(rb((0, 0, -60)))}, markerSize = 4,",
           f"\taxisX = {lua_vec(rb((100, 0, -60)))}, axisY = {lua_vec(rb((0, 100, -60)))},",
           "\tscreens = {"]
    for s in L.SCREENS:
        panels = []
        for p in s["panels"]:
            panels.append("{c=%s,n=%s,r=%s,w=%g,h=%g,u0=%g,u1=%g}" % (
                lua_vec(rb(p["c"])), lua_vec(rb(p["n"])), lua_vec(rb(p["r"])), round(p["w"], 3), round(p["h"], 3),
                round(p["u0"], 4), round(p["u1"], 4)))
        out.append('\t\t["%s"] = {ad="%s", kind="%s", layer=%d, panels={%s}},' % (
            s["name"], s["ad"], s["kind"], s["layer"], ",".join(panels)))
    out.append("\t},")
    out.append("\tads = {")
    for name, (w, h) in sorted(L.AD_SIZES.items()):
        out.append('\t\t["%s"] = {%d, %d},' % (name, w, h))
    out.append("\t},")
    out.append("\tlights = {")
    for l_ in L.LIGHTS:
        extra = ""
        if l_["dir"]:
            extra += ", dir=" + lua_vec(rb(l_["dir"]))
        if l_["angle"]:
            extra += f", angle={l_['angle']}"
        out.append('\t\t{kind="%s", pos=%s, color={%d,%d,%d}, range=%g, brightness=%g%s},' % (
            l_["kind"], lua_vec(rb(l_["pos"])), *l_["color"], l_["range"], l_["brightness"], extra))
    out.append("\t},")
    out.append("}")
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")
    with open(path.replace(".lua", ".json"), "w") as f:
        json.dump({"screens": L.SCREENS, "lights": L.LIGHTS}, f)
    log("wrote", path, "screens:", len(L.SCREENS), "lights:", len(L.LIGHTS))


def export_fbx(colls, path):
    bpy.ops.object.select_all(action="DESELECT")
    objs = []
    for c in colls:
        for o in c.all_objects:
            if o.type == "MESH" and not o.get("cp_proto"):
                o.hide_set(False)
                o.select_set(True)
                objs.append(o)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={"MESH"}, global_scale=1.0, apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_NONE", axis_forward="-Z", axis_up="Y", bake_space_transform=False,
        use_mesh_modifiers=True, mesh_smooth_type="OFF", use_tspace=False, use_custom_props=False,
        add_leaf_bones=False, bake_anim=False, path_mode="RELATIVE", embed_textures=False, batch_mode="OFF")
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
    log(f"exported {os.path.basename(path)}: {len(objs)} objects, {tris} tris, "
        f"{os.path.getsize(path) / 1e6:.2f} MB")
    return len(objs), tris


def stats():
    out = {}
    for c in bpy.data.collections:
        objs = [o for o in c.objects if o.type == "MESH" and not o.get("cp_proto")]
        out[c.name] = (len(objs), sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs))
    return out


ROBLOX_SETUP = {
    "GLS": "SurfaceAppearance (Color/Normal/Roughness/Metalness)", "RIB": "SurfaceAppearance", "PNL": "SurfaceAppearance",
    "CON": "SurfaceAppearance", "TEC": "SurfaceAppearance", "MEC": "SurfaceAppearance", "ROF": "SurfaceAppearance",
    "STL": "SurfaceAppearance", "LOU": "SurfaceAppearance", "TWN": "SurfaceAppearance",
    "SGH": "TextureID / SurfaceAppearance ColorMap (atlas)", "SGV": "TextureID / SurfaceAppearance ColorMap (atlas)",
}


def write_assignment(path_csv, path_screens):
    """One row per exported mesh: which material / PNG maps / Roblox setting it needs."""
    import csv
    rows = []
    for tag, cname in (("A", "A_HEX_Cyberpunk_City_A"), ("B", "B_HEX_Cyberpunk_City_B")):
        for o in L.COLL[cname].all_objects:
            if o.type != "MESH" or o.get("cp_proto"):
                continue
            m = o.data.materials[0]
            key = o.name.split("__")[-1].rsplit("_", 1)[0] if "__" in o.name and o.name.split("__")[-1][-1].isdigit() \
                else (o.name.split("__")[-1] if "__" in o.name else "")
            if o.name.startswith("SCR_"):
                key = "SCREEN"
            if m.name == "HEX_Palette":
                key = "HEX_Palette"
            if key in L.MATS:
                base = L.MATS[key][1]
                tex = ";".join(f"{base}_{k}.png" for k in ("Color", "Normal", "Roughness", "Metalness"))
                setup = ROBLOX_SETUP[key]
            elif key in L.FLATS:
                tex = f"F_{key}.png (swatch only)"
                c = L.FLATS[key][0]
                setup = f"Material=Neon, Color={c[0]},{c[1]},{c[2]} (CyberpunkConfig.NeonColors)"
            elif key in L.SIGNS:
                tex = L.SIGNS[key][1] + ".png"
                setup = ROBLOX_SETUP[key]
            elif key == "SCREEN":
                tex = m.name + ".png"
                setup = "TextureID + SurfaceGui overlay (CyberpunkSetup)"
            elif key == "HEX_Palette":
                tex = "palette.png"
                setup = "original map material (unchanged)"
            else:
                tex, setup = "", ""
            tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
            rows.append((tag, o.name, m.name, key, tex, setup, tris, o.data.name if o.data.users > 1 else ""))
    rows.sort()
    with open(path_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "object (Roblox MeshPart name)", "material", "key", "texture files", "Roblox setup",
                    "triangles", "shared mesh (instanced)"])
        w.writerows(rows)
    with open(path_screens, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["screen object", "file", "ad texture", "format", "kind", "panels", "width (studs)", "height (studs)"])
        for s_ in sorted(L.SCREENS, key=lambda r: r["name"]):
            width = sum(p["w"] for p in s_["panels"])
            tag = "A" if s_["name"].startswith("SCR_A_") else "B"
            w.writerow([s_["name"], tag, s_["ad"] + ".png", s_["fmt"], s_["kind"], len(s_["panels"]), round(width, 2),
                        round(s_["panels"][0]["h"], 2)])
    log("wrote", path_csv, len(rows), "rows;", path_screens)


def main():
    os.makedirs(TEX, exist_ok=True)
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    L.set_tex_dir(TEX)
    L.load_ads(os.path.join(EXPORT, "ads_index.txt"))
    import_original()
    if not QUICK:
        bpy.ops.wm.save_as_mainfile(filepath=BACKUP_BLEND, compress=True)
        log("backup saved", BACKUP_BLEND)
    sign_cells()
    lots, mg, corners = collect_lots()
    log(f"lots: {len(lots)} foreground, {len(corners)} corners, {len(mg)} midground")
    delete_old()
    C = collections()
    move_preserved(C)
    A.build_props(C["proto"])
    build_foreground(lots, corners, C)
    side_street_gates(lots, C)
    build_midground(mg, C)
    build_skyline(C)
    markers(C)
    blender_preview_lights(C)
    for o in [o for o in bpy.data.objects if o.get("cp_proto")]:
        bpy.data.objects.remove(o)  # instances keep the shared meshes
    for k, v in stats().items():
        log(f"  {k:36s} objects={v[0]:6d} tris={v[1]:8d}")
    bpy.context.preferences.filepaths.use_relative_paths = True
    out_blend = OUT_BLEND if not QUICK else OUT_BLEND.replace(".blend", "_quick.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out_blend, compress=True, relative_remap=True)
    log("saved", out_blend)
    write_data(os.path.join(EXPORT, "roblox", "CityData.lua") if not QUICK else os.path.join(EXPORT, "quick_data.lua"))
    if "--no-export" not in sys.argv:
        sfx = "_quick" if QUICK else ""
        a = export_fbx([L.COLL["A_HEX_Cyberpunk_City_A"]], os.path.join(EXPORT, f"HEX_Cyberpunk_City_A{sfx}.fbx"))
        b = export_fbx([L.COLL["B_HEX_Cyberpunk_City_B"]], os.path.join(EXPORT, f"HEX_Cyberpunk_City_B{sfx}.fbx"))
    if not QUICK:
        write_assignment(os.path.join(EXPORT, "texture_assignment.csv"), os.path.join(EXPORT, "screens.csv"))


if __name__ == "__main__":
    main()
