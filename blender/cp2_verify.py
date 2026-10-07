"""HEX! Cyberpunk City v2 - re-import verification of the two exported FBX files.

    /opt/bvenv/bin/python blender/cp2_verify.py [--render out.png]

Checks (written to export/VERIFICATION.md + verification.json):
  * each FBX < 20 MB
  * both files import into one clean scene; HEX_ALIGN_A / HEX_ALIGN_B sit at the same point
  * the preserved basketball-map objects are geometrically identical to the original FBX
  * no new geometry inside the plaza / practice area (playable surfaces stay empty)
  * no object exists in both files
  * every mesh has one material and a finite UV map; every texture file it references exists
"""
import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXPORT = os.path.join(ROOT, "export")
SRC = os.path.join(ROOT, "assets", "HEX_City_00_FULL_CITY.fbx")
FILES = {"A": os.path.join(EXPORT, "HEX_Cyberpunk_City_A.fbx"), "B": os.path.join(EXPORT, "HEX_Cyberpunk_City_B.fbx")}
LIMIT = 20 * 1024 * 1024
PRESERVED = ("Plaza_", "Practice_", "Stair_", "City_", "Street_", "LightMast_", "UtilityPole_", "UtilityLines_",
             "RailViaduct_", "Skybridge_")


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)
    for m in list(bpy.data.materials):
        bpy.data.materials.remove(m)
    for i in list(bpy.data.images):
        bpy.data.images.remove(i)


def geo_hash(o):
    """Sorted world-space vertex list (compared with a 0.01-stud tolerance)."""
    mw = o.matrix_world
    pts = sorted((round(v[0], 1), round(v[1], 1), round(v[2], 1), v[0], v[1], v[2])
                 for v in (mw @ vv.co for vv in o.data.vertices))
    return [p[3:] for p in pts], len(pts)


def same_geo(a, b, tol=0.01):
    if len(a) != len(b):
        return False
    import numpy as np
    A, B = np.array(a), np.array(b)
    # order-independent: compare after lexicographic sort on rounded coordinates
    ia = np.lexsort(np.round(A[:, ::-1], 2).T)
    ib = np.lexsort(np.round(B[:, ::-1], 2).T)
    return float(np.abs(A[ia] - B[ib]).max()) < tol


def import_fbx(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def main():
    rep = {"files": {}, "checks": {}}
    ok = True
    for k, p in FILES.items():
        sz = os.path.getsize(p)
        rep["files"][k] = {"path": os.path.relpath(p, ROOT), "bytes": sz, "MB": round(sz / 1e6, 2), "under_20MB": sz < LIMIT}
        ok &= sz < LIMIT

    # original preserved geometry
    clear()
    orig = {}
    for o in import_fbx(SRC):
        if o.type == "MESH" and o.parent is None and o.name.startswith(PRESERVED):
            orig[o.name] = geo_hash(o)
    clear()

    objs = {k: import_fbx(p) for k, p in FILES.items()}
    names = {k: {o.name for o in v} for k, v in objs.items()}
    allobj = objs["A"] + objs["B"]

    # alignment markers
    def center(name):
        o = next((o for o in allobj if o.name.startswith(name)), None)
        if not o:
            return None
        cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
        return [round(sum(c[i] for c in cs) / 8, 3) for i in range(3)], [round(max(c[i] for c in cs) - min(c[i] for c in cs), 3) for i in range(3)]
    ma, mb = center("HEX_ALIGN_A"), center("HEX_ALIGN_B")
    aligned = ma is not None and mb is not None and ma[0] == mb[0] and ma[0] == [0.0, 0.0, -60.0]
    rep["checks"]["alignment_markers"] = {"A": ma, "B": mb, "same_origin": aligned}
    ok &= aligned

    # preserved geometry identical
    same, diff, missing = 0, [], []
    for n, (h, nv) in orig.items():
        o = next((o for o in objs["A"] if o.name == n), None)
        if o is None:
            missing.append(n)
            continue
        if same_geo(geo_hash(o)[0], h):
            same += 1
        else:
            diff.append(n)
    in_b = [o.name for o in objs["B"] if o.name.startswith(PRESERVED)]
    rep["checks"]["preserved_map"] = {"objects": len(orig), "identical": same, "changed": diff, "missing": missing,
                                      "duplicated_in_B": in_b}
    ok &= same == len(orig) and not in_b

    # playable areas empty: no new vertex inside the plaza rectangle below 60 studs
    intr = Counter()
    for o in allobj:
        if o.type != "MESH" or o.name.startswith(PRESERVED) or o.name.startswith("HEX_ALIGN"):
            continue
        mw = o.matrix_world
        for v in o.data.vertices:
            p = mw @ v.co
            if abs(p.x) < 484 and abs(p.y) < 399 and p.z < 60:
                intr[o.name] += 1
    rep["checks"]["plaza_intrusions"] = dict(intr)
    ok &= not intr

    rep["checks"]["names_in_both_files"] = sorted(names["A"] & names["B"])
    ok &= not (names["A"] & names["B"])

    # materials / UVs / textures
    mats = defaultdict(lambda: {"objects": 0, "tris": 0, "textures": set(), "files": set()})
    bad_uv, no_uv, multi = [], [], []
    tex_missing = set()
    tris_total = Counter()
    for k, lst in objs.items():
        for o in lst:
            if o.type != "MESH":
                continue
            me = o.data
            t = sum(len(p.vertices) - 2 for p in me.polygons)
            tris_total[k] += t
            ms = [m for m in me.materials if m]
            if len(ms) != 1:
                multi.append(o.name)
            if not me.uv_layers:
                no_uv.append(o.name)
            else:
                d = [0.0] * (len(me.loops) * 2)
                me.uv_layers[0].data.foreach_get("uv", d)
                if any(not math.isfinite(x) for x in d):
                    bad_uv.append(o.name)
            for m in ms:
                e = mats[m.name.split(".")[0]]  # both files share material names (.001 on 2nd import)
                e["objects"] += 1
                e["tris"] += t
                e["files"].add(k)
                if m.use_nodes:
                    for nd in m.node_tree.nodes:
                        if nd.type == "TEX_IMAGE" and nd.image:
                            fp = bpy.path.abspath(nd.image.filepath)
                            e["textures"].add(os.path.basename(fp))
                            if not os.path.exists(fp):
                                tex_missing.add(fp)
    rep["checks"]["meshes_without_uv"] = no_uv
    rep["checks"]["non_finite_uv"] = bad_uv
    rep["checks"]["objects_with_not_exactly_one_material"] = multi
    rep["checks"]["missing_texture_files"] = sorted(tex_missing)
    ok &= not (no_uv or bad_uv or tex_missing or multi)
    rep["triangles"] = dict(tris_total)
    rep["objects"] = {k: len(v) for k, v in objs.items()}
    rep["materials"] = {n: {"objects": e["objects"], "tris": e["tris"], "textures": sorted(e["textures"]),
                            "files": sorted(e["files"])} for n, e in sorted(mats.items())}

    # bounds
    def bounds(lst):
        lo = [1e9] * 3
        hi = [-1e9] * 3
        for o in lst:
            if o.type != "MESH":
                continue
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                lo = [min(lo[i], w[i]) for i in range(3)]
                hi = [max(hi[i], w[i]) for i in range(3)]
        return [round(x, 1) for x in lo], [round(x, 1) for x in hi]
    rep["bounds"] = {k: bounds(v) for k, v in objs.items()}
    rep["ok"] = bool(ok)
    with open(os.path.join(EXPORT, "verification.json"), "w") as f:
        json.dump(rep, f, indent=1, default=list)

    # markdown summary
    L = ["# Export verification", "", f"Overall: **{'PASS' if ok else 'FAIL'}** (re-imported both FBX files into a clean Blender scene)", "",
         "| File | Size | Objects | Triangles | Bounds min | Bounds max |", "|---|---|---|---|---|---|"]
    for k in ("A", "B"):
        f_ = rep["files"][k]
        L.append(f"| `{os.path.basename(f_['path'])}` | {f_['MB']} MB {'(< 20 MB)' if f_['under_20MB'] else '(OVER 20 MB)'} | "
                 f"{rep['objects'][k]} | {rep['triangles'][k]} | {rep['bounds'][k][0]} | {rep['bounds'][k][1]} |")
    c = rep["checks"]
    L += ["", "| Check | Result |", "|---|---|",
          f"| Alignment markers (both at 0, 0, -60) | {'same origin' if c['alignment_markers']['same_origin'] else 'MISMATCH'}: A {c['alignment_markers']['A']}, B {c['alignment_markers']['B']} |",
          f"| Preserved basketball-map objects identical to the original FBX | {c['preserved_map']['identical']} / {c['preserved_map']['objects']} identical, changed {len(c['preserved_map']['changed'])}, missing {len(c['preserved_map']['missing'])} |",
          f"| Preserved map included only once (not in B) | {'yes' if not c['preserved_map']['duplicated_in_B'] else c['preserved_map']['duplicated_in_B']} |",
          f"| New geometry inside the plaza / practice area (below 60 studs) | {sum(c['plaza_intrusions'].values())} vertices |",
          f"| Objects present in both files | {len(c['names_in_both_files'])} |",
          f"| Meshes without UVs / non-finite UVs | {len(c['meshes_without_uv'])} / {len(c['non_finite_uv'])} |",
          f"| Meshes with other than exactly one material | {len(c['objects_with_not_exactly_one_material'])} |",
          f"| Referenced texture files missing on disk | {len(c['missing_texture_files'])} |",
          "", "## Materials after re-import", "", "| Material | Objects | Triangles | In file | Textures |", "|---|---|---|---|---|"]
    for n, e in rep["materials"].items():
        L.append(f"| `{n}` | {e['objects']} | {e['tris']} | {', '.join(e['files'])} | {', '.join(e['textures'])} |")
    with open(os.path.join(EXPORT, "VERIFICATION.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    print("VERIFY", "PASS" if ok else "FAIL")
    print(json.dumps({k: v for k, v in rep.items() if k not in ("materials",)}, indent=1, default=list)[:3000])

    if "--render" in sys.argv:
        out = sys.argv[sys.argv.index("--render") + 1]
        sc = bpy.context.scene
        sc.render.engine = "CYCLES"
        sc.cycles.samples = 16
        sc.cycles.use_denoising = True
        sc.render.resolution_x, sc.render.resolution_y = 1280, 720
        w = bpy.data.worlds.new("v")
        w.use_nodes = True
        w.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.1, 1)
        w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
        sc.world = w
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = 0.6
        sun.rotation_euler = (0.9, 0.2, 0.6)
        sc.collection.objects.link(sun)
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
        cam.data.lens = 16
        cam.data.clip_end = 8000
        sc.collection.objects.link(cam)
        sc.camera = cam
        cam.location = (0, 60, 5)
        d = (Vector((0, 500, 120)) - cam.location).normalized()
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        sc.view_settings.view_transform = "AgX"
        sc.render.filepath = out
        bpy.ops.render.render(write_still=True)
        print("rendered", out)


main()
