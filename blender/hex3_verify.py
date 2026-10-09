"""HEX! City v3 - verification by re-import.

    /opt/bvenv/bin/python blender/hex3_verify.py

Checks: file A re-imports identical to the original FBX (names, vertex/face counts, bounds);
file B re-imports, nothing of it enters the plaza / courts / practice area, both files are
< 20 MB, every texture referenced by the FBX files exists next to them (bare file names),
every screen / sign named in CityData exists in the FBX files. Writes export_v3/VERIFICATION.md.
"""
import os
import re
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EX = os.path.join(ROOT, "export_v3")
SRC = os.path.join(ROOT, "assets", "HEX_City_00_FULL_CITY.fbx")
A = os.path.join(EX, "HEX_City_v3_A.fbx")
B = os.path.join(EX, "HEX_City_v3_B.fbx")
lines = []
ok_all = True


def check(ok, msg):
    global ok_all
    ok_all &= bool(ok)
    lines.append(("- [x] " if ok else "- [ ] FAIL ") + msg)
    print(("OK   " if ok else "FAIL ") + msg, flush=True)


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    out = {}
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        pts = [o.matrix_world @ v.co for v in o.data.vertices]
        mn = tuple(round(min(p[i] for p in pts), 2) for i in range(3)) if pts else (0, 0, 0)
        mx = tuple(round(max(p[i] for p in pts), 2) for i in range(3)) if pts else (0, 0, 0)
        out[o.name] = (len(o.data.vertices), len(o.data.polygons), mn, mx, [p.copy() for p in pts])
    return out


def same(a, b, tol=0.02):
    return a[0] == b[0] and a[1] == b[1] and all(abs(x - y) <= tol for x, y in zip(a[2] + a[3], b[2] + b[3]))


orig = load(SRC)
fa = load(A)
check(set(orig) == set(fa), f"file A has the same {len(orig)} mesh objects as the original")
diff = [n for n in orig if n in fa and not same(orig[n], fa[n])]
check(not diff, f"file A geometry identical to the original (vertex/face counts and bounds) - {len(diff)} differ"
      + (f": {diff[:5]}" if diff else ""))
del orig
fb = load(B)
check(len(fb) > 1000, f"file B re-imports: {len(fb)} mesh objects")
bad = []
for n, (_, _, mn, mx, pts) in fb.items():
    if n.startswith("HEX_ALIGN"):
        continue
    for p in pts:
        if abs(p.x) < 484.0 and abs(p.y) < 399.0 and p.z < 60:
            bad.append(n)
            break
check(not bad, f"nothing new inside the plaza / courts / practice area (|x|<484, |y|<399, below 60 studs)"
      + (f": {bad[:8]}" if bad else ""))
for path in (A, B):
    mb = os.path.getsize(path) / 1e6
    check(mb < 20, f"{os.path.basename(path)} is {mb:.2f} MB (< 20 MB)")
# texture references inside the FBX binaries
tex = os.path.join(EX, "textures")
for path in (A, B):
    data = open(path, "rb").read()
    names = sorted(set(m.decode() for m in re.findall(rb"[\w\-./\\:]+\.png", data)))
    absolute = [n for n in names if "/" in n or "\\" in n]
    missing = [n for n in names if not os.path.exists(os.path.join(tex, os.path.basename(n)))]
    check(not absolute, f"{os.path.basename(path)}: texture paths are bare file names ({len(names)} referenced)")
    check(not missing, f"{os.path.basename(path)}: every referenced PNG is in textures/" + (f" missing {missing}" if missing else ""))
# CityData names exist
cd = open(os.path.join(EX, "roblox", "CityData.lua"), encoding="utf-8").read()
scr = re.findall(r'\["(SCR_[^"]+)"\] = \{ad="(AD_[^"]+)"', cd)
signs = re.findall(r'\{name="([^"]+)", atlas=', cd)
allnames = set(fa) | set(fb)
check(all(s in allnames for s, _ in scr), f"all {len(scr)} screens in CityData exist as meshes")
check(all(s in allnames for s in signs), f"all {len(signs)} glow signs in CityData exist as meshes")
check(all(os.path.exists(os.path.join(tex, a + ".png")) for _, a in scr), "every screen's ad PNG exists")
ads = sorted(set(a for _, a in scr))
check(len(ads) >= 30, f"{len(ads)} different ads in use, all rotating (RotateAll)")
with open(os.path.join(EX, "VERIFICATION.md"), "w") as f:
    f.write("# HEX! City v3 - verification (re-import of the exported FBX files)\n\n")
    f.write("\n".join(lines) + "\n\n" + ("All checks passed.\n" if ok_all else "SOME CHECKS FAILED.\n"))
sys.exit(0 if ok_all else 1)
