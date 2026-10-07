"""Add cyberpunk dressing geometry around every building, for the Roblox export.

Per building (axis-aligned bounding box):
  * neon frame: corner strips, floor bands and a roof crown      -> <name>_N<k>__neon
  * Shinjuku-style vertical blade signs on street-facing walls    -> <name>_Blade<i>__blade
  * holographic billboards floating off facades and on rooftops   -> <name>_Holo<i>__holo
  * rooftop antennas / billboard supports                         -> <name>_Rig__rig
  * blinking beacons on antennas                                  -> <name>_Beacon__beacon

Signs and holograms are textured with the map's own atlases (ads, kanji signs),
so they show up straight after import; the Roblox scripts add glow and motion.
"""
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

Z = Vector((0, 0, 1))
DIRS = [Vector((1, 0, 0)), Vector((-1, 0, 0)), Vector((0, 1, 0)), Vector((0, -1, 0))]
NEON_T = 0.25
MAX_FOOTPRINT = 160.0
FLOOR_H = 3.6  # must match the facade texture (2 floors per 7.2 m tile)
BAY_W = 2.0  # 4 bays per 8 m tile
GLASS = (0.32, 0.86)  # glass strip, as a fraction of floor height
MAX_QUADS = 9000  # keeps each glow mesh under Roblox's 20k triangle limit


def world_bbox(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return (Vector([min(p[i] for p in pts) for i in range(3)]),
            Vector([max(p[i] for p in pts) for i in range(3)]))


def add_box(bm, center, size):
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(center) @ Matrix.Diagonal((*size, 1.0)))


def mesh_object(name, bm, mat, collection):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.uv_layers.new(name="UVMap")
    me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    collection.objects.link(obj)
    return obj


def panel_object(name, center, size, rect, mat, collection):
    """Box centred at `center` whose two large vertical faces show atlas `rect`."""
    bm = bmesh.new()
    add_box(bm, Vector(), size)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    uvl = me.uv_layers.new(name="UVMap")
    u0, v0, uw, vh = rect
    for p in me.polygons:
        n = p.normal
        if abs(n.z) < 0.5 and p.area >= max(size.x * size.z, size.y * size.z) * 0.9:
            right = Z.cross(n).normalized()
            width = abs(size.dot(Vector((abs(right.x), abs(right.y), 0))))
            for li in p.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                s = co.dot(right) / width + 0.5
                t = co.z / size.z + 0.5
                uvl.data[li].uv = (u0 + s * uw, v0 + t * vh)
        else:
            for li in p.loop_indices:
                uvl.data[li].uv = (u0 + 0.01 * uw, v0 + 0.01 * vh)
    me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    obj.location = center
    collection.objects.link(obj)
    return obj


class Dresser:
    def __init__(self, pools, mats, seed=2077):
        """pools: {'screen': [rect...], 'sign_v': [...], 'sign_h': [...]} (u0, v0, uw, vh)
        mats: {'screen', 'sign_v', 'sign_h', 'metal', 'beacon', 'neon1'..'neon6'} -> material"""
        self.pools = pools
        self.mats = mats
        self.seed = seed
        self.col = bpy.context.scene.collection
        self.depsgraph = bpy.context.evaluated_depsgraph_get()
        self.scene = bpy.context.scene

    def clear(self, origin, direction, dist):
        hit = self.scene.ray_cast(self.depsgraph, origin, direction, distance=dist)[0]
        return not hit

    def exposed_faces(self, lo, hi):
        """Sides of the bbox with open space in front of them."""
        out = []
        c = (lo + hi) / 2
        for d in DIRS:
            face = Vector((hi.x if d.x > 0 else lo.x if d.x < 0 else c.x,
                           hi.y if d.y > 0 else lo.y if d.y < 0 else c.y, 0))
            free = 0
            for fz in (0.15, 0.45, 0.75):
                o = face + d * 0.3
                o.z = lo.z + (hi.z - lo.z) * fz
                free += self.clear(o, d, 25.0)
            if free >= 2:
                out.append((d, face))
        return out

    def hits_self(self, obj, origin, direction, dist):
        hit, loc, nrm, _i, hobj, _m = self.scene.ray_cast(self.depsgraph, origin, direction, distance=dist)
        if hit and hobj.name == obj.name:
            return loc, nrm
        return None

    def windows(self, obj, origin, lo, hi, r, chance):
        """Glowing panes on the facade's glass strips, placed on the real walls."""
        quads = []
        floors = int((hi.z - lo.z) // FLOOR_H)
        g0, g1 = GLASS[0] * FLOOR_H, GLASS[1] * FLOOR_H
        half_w, half_h = BAY_W * 0.46, (g1 - g0) * 0.46
        for d in DIRS:
            tan = Vector((abs(d.y), abs(d.x), 0))
            depth = (hi - lo).dot(Vector((abs(d.x), abs(d.y), 0))) + 2
            bays = int((hi - lo).dot(tan) // BAY_W)
            for f in range(floors):
                zc = lo.z + f * FLOOR_H + (g0 + g1) / 2
                for b in range(bays):
                    if r.random() >= chance:
                        continue
                    p = lo + tan * ((b + 0.5) * BAY_W)
                    p.z = zc
                    if d.x:
                        p.x = (hi.x if d.x > 0 else lo.x) + d.x
                    else:
                        p.y = (hi.y if d.y > 0 else lo.y) + d.y
                    hit = self.hits_self(obj, p, -d, depth)
                    if not hit or hit[1].dot(d) < 0.9:
                        continue
                    ends = [self.hits_self(obj, p + tan * s, -d, depth) for s in (-half_w, half_w)]
                    if not all(ends) or any(abs((e[0] - hit[0]).dot(d)) > 0.15 for e in ends):
                        continue
                    quads.append((hit[0] + d * 0.06, tan, d))
        objs = []
        k = 1 + (0 if r.random() < 0.65 else r.randrange(6) + 1)  # 1 = warm white, 2..7 = accents
        for start in range(0, len(quads), MAX_QUADS):
            bm = bmesh.new()
            for c, t, d in quads[start:start + MAX_QUADS]:
                vs = [c - t * half_w - Z * half_h, c + t * half_w - Z * half_h,
                      c + t * half_w + Z * half_h, c - t * half_w + Z * half_h]
                if t.cross(Z).dot(d) < 0:
                    vs.reverse()
                bm.faces.new([bm.verts.new(v) for v in vs])
            name = f"{origin}_G{k - 1}W{start // MAX_QUADS + 1}__glow"
            objs.append((mesh_object(name, bm, self.mats[f"glow{k}"], self.col), origin, "glow"))
        return objs

    def dress(self, obj, origin):
        """Returns [(object, origin, tag)] for everything added around `obj`."""
        lo, hi = world_bbox(obj)
        size = hi - lo
        r = random.Random(f"{self.seed}:{origin}")
        if size.z < 12:
            return []
        huge = max(size.x, size.y) > MAX_FOOTPRINT
        out = self.windows(obj, origin, lo, hi, r, 0.05 if huge else 0.14)
        if huge:
            return out
        accent = r.randrange(6) + 1
        neon = bmesh.new()
        rig = bmesh.new()
        t = NEON_T

        # Neon frame: roof crown on most, corner strips / floor bands on some
        if r.random() < 0.3:
            for x in (lo.x - t / 2, hi.x + t / 2):
                for y in (lo.y - t / 2, hi.y + t / 2):
                    add_box(neon, Vector((x, y, lo.z + size.z / 2)), Vector((t, t, size.z)))
        levels = [hi.z - t * 1.5] if r.random() < 0.7 else []
        if r.random() < 0.3:
            spacing = r.uniform(14, 36)
            z = lo.z + spacing
            while z < hi.z - spacing * 0.5:
                levels.append(z)
                z += spacing
        for z in levels:
            add_box(neon, Vector((lo.x + size.x / 2, lo.y - t / 2, z)), Vector((size.x + 2 * t, t, t)))
            add_box(neon, Vector((lo.x + size.x / 2, hi.y + t / 2, z)), Vector((size.x + 2 * t, t, t)))
            add_box(neon, Vector((lo.x - t / 2, lo.y + size.y / 2, z)), Vector((t, size.y, t)))
            add_box(neon, Vector((hi.x + t / 2, lo.y + size.y / 2, z)), Vector((t, size.y, t)))

        faces = self.exposed_faces(lo, hi)
        r.shuffle(faces)

        def tangent_of(d):
            return Vector((abs(d.y), abs(d.x), 0))

        def face_width(d):
            return size.y if d.x else size.x

        # Vertical blade signs
        blade_faces = faces[:2]
        n_blades = r.choice((0, 1, 1, 2, 2, 3)) if self.pools["sign_v"] else 0
        for i in range(n_blades if blade_faces else 0):
            d, face = blade_faces[i % len(blade_faces)]
            rect = r.choice(self.pools["sign_v"])
            aspect = rect[2] / rect[3]
            bw = r.uniform(2.0, 3.2)
            bh = min(bw / aspect, size.z * 0.6, 40.0)
            if bh < 5:
                continue
            tan = tangent_of(d)
            fw = face_width(d)
            along = r.uniform(-0.4, 0.4) * fw
            base_z = lo.z + r.uniform(4.0, max(4.5, size.z * 0.5 - bh * 0.5))
            if base_z + bh > hi.z - 2:
                base_z = hi.z - 2 - bh
            mid = face + tan * along
            mid.z = base_z + bh / 2
            if not self.clear(mid + d * 0.3, d, bw + 1.5):
                continue
            center = mid + d * (bw / 2 + 0.25)
            bsize = Vector((abs(d.x) * bw + abs(tan.x) * 0.4, abs(d.y) * bw + abs(tan.y) * 0.4, bh))
            name = f"{origin}_Blade{i + 1}__blade"
            out.append((panel_object(name, center, bsize, rect, self.mats["sign_v"], self.col), origin, "blade"))
            # neon tube along the blade's outer edge and its top
            edge = mid + d * (bw + 0.4)
            add_box(neon, edge, Vector((0.25, 0.25, bh)))
            top = mid + d * (bw / 2 + 0.25)
            top.z = base_z + bh + 0.15
            add_box(neon, top, Vector((abs(d.x) * bw + 0.25, abs(d.y) * bw + 0.25, 0.25)))

        # Holographic billboards floating off a facade
        holo_faces = faces[2:] or faces
        n = 0
        if holo_faces and self.pools["screen"] and r.random() < 0.55:
            d, face = holo_faces[0]
            u0, v0, uw, vh = r.choice(self.pools["screen"])
            fw = face_width(d)
            wp = min(r.uniform(10, 28), fw * 0.75)
            if r.random() < 0.5:  # widescreen crop of the square ad
                rect = (u0, v0 + vh * 0.22, uw, vh * 0.5625)
                hp = wp * 0.5625
            else:
                rect = (u0, v0, uw, vh)
                hp = wp
            zc = lo.z + size.z * r.uniform(0.35, 0.8)
            zc = max(min(zc, hi.z - hp / 2 - 2), lo.z + 10 + hp / 2)
            if wp > 6 and lo.z + 8 + hp < hi.z:
                tan = tangent_of(d)
                mid = face + tan * r.uniform(-0.5, 0.5) * (fw - wp) * 0.8
                mid.z = zc
                center = mid + d * 1.6
                psize = Vector((abs(tan.x) * wp + abs(d.x) * 0.15, abs(tan.y) * wp + abs(d.y) * 0.15, hp))
                n += 1
                out.append((panel_object(f"{origin}_Holo{n}__holo", center, psize, rect,
                                         self.mats["screen"], self.col), origin, "holo"))
                proj = mid + d * 0.8
                proj.z = zc - hp / 2 - 0.4
                add_box(neon, proj, Vector((abs(tan.x) * wp + abs(d.x) * 1.2, abs(tan.y) * wp + abs(d.y) * 1.2, 0.3)))

        # Rooftop billboard on supports
        if faces and size.z > 25 and r.random() < 0.35:
            d, face = faces[-1]
            pool = self.pools["sign_h"] if (self.pools["sign_h"] and r.random() < 0.4) else self.pools["screen"]
            mat = self.mats["sign_h"] if pool is self.pools["sign_h"] else self.mats["screen"]
            rect = r.choice(pool)
            fw = face_width(d)
            wp = min(r.uniform(12, 26), fw * 0.9)
            hp = min(wp * rect[3] / rect[2], 18)
            if wp > 6:
                tan = tangent_of(d)
                base = face - d * 3.0
                base.z = hi.z
                center = base + Z * (2.5 + hp / 2)
                psize = Vector((abs(tan.x) * wp + abs(d.x) * 0.4, abs(tan.y) * wp + abs(d.y) * 0.4, hp))
                n += 1
                out.append((panel_object(f"{origin}_Holo{n}__holo", center, psize, rect, mat, self.col),
                            origin, "holo"))
                for s in (-0.35, 0.35):
                    leg = base + tan * (s * wp) - d * 0.5
                    leg.z = hi.z + 1.25
                    add_box(rig, leg, Vector((0.4, 0.4, 2.5)))
                bar = base + d * 0.3
                bar.z = hi.z + 2.2
                add_box(neon, bar, Vector((abs(tan.x) * wp + 0.3, abs(tan.y) * wp + 0.3, 0.3)))

        # Antenna with beacon
        if r.random() < 0.5:
            ah = r.uniform(8, 25)
            p = Vector((r.uniform(lo.x + 2, hi.x - 2), r.uniform(lo.y + 2, hi.y - 2), hi.z + ah / 2))
            add_box(rig, p, Vector((0.35, 0.35, ah)))
            add_box(rig, p - Z * (ah / 2 - 0.5), Vector((2.0, 2.0, 1.0)))
            beacon = bmesh.new()
            add_box(beacon, p + Z * (ah / 2 + 0.45), Vector((0.9, 0.9, 0.9)))
            out.append((mesh_object(f"{origin}_Beacon__beacon", beacon, self.mats["beacon"], self.col),
                        origin, "beacon"))

        if neon.verts:
            out.append((mesh_object(f"{origin}_N{accent}__neon", neon, self.mats[f"neon{accent}"], self.col),
                        origin, "neon"))
        else:
            neon.free()
        if rig.verts:
            out.append((mesh_object(f"{origin}_Rig__rig", rig, self.mats["metal"], self.col), origin, "rig"))
        else:
            rig.free()
        return out
