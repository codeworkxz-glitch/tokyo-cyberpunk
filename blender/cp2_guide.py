"""Writes export/ROBLOX_SETUP_GUIDE.md from the real export (texture sizes, mesh counts, verification).

    python3 blender/cp2_guide.py
"""
import csv
import json
import os
from collections import Counter, defaultdict

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EX = os.path.join(ROOT, "export")
TEX = os.path.join(EX, "textures")

PBR = [  # key, material, texture base, tile (studs), used for
    ("GLS", "CP_GlassCurtain", "T_GlassCurtain", "32 x 48", "curtain-wall glazing, mullion grid matches 5.33-stud bays / 12-stud floors"),
    ("RIB", "CP_GlassRibbon", "T_GlassRibbon", "32 x 24", "ribbon windows with concrete spandrels"),
    ("PNL", "CP_PanelMetal", "T_PanelMetal", "24 x 24", "gunmetal cladding, fascias, screen backs, recess linings"),
    ("CON", "CP_ConcreteDark", "T_ConcreteDark", "32 x 32", "board-formed concrete: party walls, pilasters, slabs, parapets"),
    ("TEC", "CP_TechPanel", "T_TechPanel", "16 x 16", "sci-fi panelling, crown blocks, balustrades"),
    ("MEC", "CP_Mechanical", "T_Mechanical", "8 x 8", "HVAC, ducts, vents, cooling towers, generators, AC units"),
    ("ROF", "CP_RoofDeck", "T_RoofDeck", "32 x 32", "roof membranes"),
    ("STL", "CP_Steel", "T_Steel", "8 x 8", "trusses, exoskeletons, frames, catwalks, pipes, railings, antennas"),
    ("LOU", "CP_Louver", "T_Louver", "8 x 12", "louvred midground facades"),
    ("TWN", "CP_TowerNight", "T_TowerNight", "32 x 48", "midground / skyline glazing (pale windows baked into the colour map)"),
]
NEON = [
    ("NEON_CYN", (0, 230, 255), "cyan accent strips / outlines"),
    ("NEON_MAG", (255, 25, 175), "magenta accent strips / outlines"),
    ("NEON_VIO", (150, 45, 255), "violet accents"),
    ("NEON_BLU", (30, 95, 255), "electric blue accents"),
    ("NEON_RED", (255, 32, 45), "aircraft beacons, occasional red accents, lanterns"),
    ("NEON_AMB", (255, 150, 25), "occasional amber (lanterns, a few signs)"),
    ("NEON_WHT", (200, 215, 255), "LED strips under canopies, billboard flood bars"),
    ("WIN_WRM", (150, 110, 70), "lit windows, warm"),
    ("WIN_COL", (80, 115, 160), "lit windows, cool"),
    ("WIN_PNK", (160, 70, 125), "lit windows, pink"),
    ("WIN_VIO", (105, 80, 165), "lit windows, violet; skybridge glow"),
    ("SHOP_LIT", (175, 160, 140), "storefront glass, vending machine fronts"),
]


def kb(p):
    return f"{os.path.getsize(p) / 1024:.0f} KB"


def main():
    rows = list(csv.DictReader(open(os.path.join(EX, "texture_assignment.csv"))))
    screens = list(csv.DictReader(open(os.path.join(EX, "screens.csv"))))
    ver = json.load(open(os.path.join(EX, "verification.json")))
    by_key = Counter((r["file"], r["key"]) for r in rows)
    tris_key = Counter()
    for r in rows:
        tris_key[r["key"]] += int(r["triangles"])
    ad_use = defaultdict(list)
    for s in screens:
        ad_use[s["ad texture"]].append(s)
    tex_total = sum(os.path.getsize(os.path.join(TEX, f)) for f in os.listdir(TEX))

    o = []
    w = o.append
    w("# HEX! Cyberpunk City v2 — Roblox Studio setup & texture / material guide")
    w("")
    w("Everything here is generated from the actual export (`blender/cp2_guide.py`). "
      "Per-object detail: [`texture_assignment.csv`](texture_assignment.csv) (every MeshPart → material → PNG maps → Roblox setting) "
      "and [`screens.csv`](screens.csv) (every screen → ad texture). Export checks: [`VERIFICATION.md`](VERIFICATION.md).")
    w("")
    w("## 1. Files")
    w("")
    w("| File | Size | Contents |")
    w("|---|---|---|")
    w(f"| `HEX_Cyberpunk_City_A.fbx` | {ver['files']['A']['MB']} MB | the original basketball park (unchanged, included only here), "
      f"all foreground buildings around the plaza, the 4 corner landmarks, side-street ad gates / skybridges, their screens and props — "
      f"{ver['objects']['A']} meshes, {ver['triangles']['A']:,} triangles |")
    w(f"| `HEX_Cyberpunk_City_B.fbx` | {ver['files']['B']['MB']} MB | midground towers, skyline towers, 12 megatowers, their screens and props — "
      f"{ver['objects']['B']} meshes, {ver['triangles']['B']:,} triangles |")
    w(f"| `textures/` | {tex_total / 1e6:.1f} MB | every PNG the materials use (listed below) |")
    w("| `roblox/CyberpunkCityV2.rbxmx` | | setup / animation scripts + `CityData` (screen panels, lights, alignment) |")
    w("| `../output/HEX_Cyberpunk_City.blend` | | editable Blender project (collections `A_*` = file A, `B_*` = file B) |")
    w("| `../output/HEX_City_00_original_backup.blend` | | backup of the untouched original scene |")
    w("")
    w("Both FBX files use the **same world origin, units and axes as `HEX_City_00_FULL_CITY.fbx`** "
      "(Blender default FBX export: Y-up, 1 unit = 1 stud, no global scale), so import them with the same settings you used for the original map. "
      "Each file contains a 4-stud cube at (0, −60, 0) (`HEX_ALIGN_A` / `HEX_ALIGN_B`, 60 studs under the plaza) used to line the two imports up; "
      "file A also has two 2-stud cubes 100 studs along +X and +Y (`HEX_AXIS_X` / `HEX_AXIS_Y`) so the setup script can detect an offset, rotation or rescale applied by the importer. "
      "The script hides all four; you can delete them once the setup has run.")
    w("")
    w("## 2. Import steps")
    w("")
    w("1. Put both FBX files and **all PNGs from `textures/` in the same folder** (the PNGs directly next to the FBX files, not in a subfolder). "
      "The FBX files reference each texture by bare file name (e.g. `T_GlassCurtain_Color.png`), so Studio looks for them beside the FBX. "
      "`HEX_Cyberpunk_Import.zip` (release download) is already laid out this way.")
    w("2. **File → Import 3D** → `HEX_Cyberpunk_City_A.fbx`. Use the same import options as for your original map (no rescale; keep the file's scene position if your Studio version offers it; Anchored). "
      "File A already contains the park, so remove the old `HEX_City_00_FULL_CITY` model to avoid a duplicate.")
    w("3. **File → Import 3D** → `HEX_Cyberpunk_City_B.fbx` with the same options.")
    w("4. In the Importer, check that materials show textures. If a texture is missing, upload the PNG from `textures/` (Asset Manager → Bulk Import) "
      "and assign it (section 4), or fill the ids into `CyberpunkConfig.SurfaceTextures` and let the setup script apply them.")
    w("5. Right-click **Workspace → Insert from File…** → `roblox/CyberpunkCityV2.rbxmx`.")
    w("6. Paste into the **command bar** and press Enter: `require(workspace.CyberpunkCityV2.CyberpunkSetup).run()`  \n"
      "   This (a) moves model B so its marker sits exactly on A's marker, warns if either import was rescaled or rotated, and maps all screen / light positions through the measured transform, "
      "(b) turns every `__NEON_*` / `__WIN_*` / `__SHOP_LIT` part into **Neon** with its colour, "
      "(c) builds a self-lit SurfaceGui on every screen, (d) places the court flood SpotLights, shop/beacon PointLights and screen SurfaceLights, "
      "(e) sets the night Lighting (Future, Atmosphere, Bloom, ColorCorrection). Running it from the command bar bakes the result into the place; "
      "otherwise `RunSetup` does it at game start.")
    w("7. Press **Play** to see the client animation (scan lines, rotating billboards, blinking beacons, a few buzzing neon tubes).")
    w("")
    w("The setup script reports how many parts got Neon, kept textures, or fell back to plain Roblox materials, so you can see at a glance whether textures came through.")
    w("")
    w("## 3. How the scene is organised")
    w("")
    w("* **One material per object.** Every Blender object (= one Roblox MeshPart) has exactly one material; its name ends with `__<KEY>` "
      "(e.g. `A_N_05_Zakkyo__GLS`, `B_Mega_03__NEON_MAG`). The largest single mesh is 6,600 triangles (anything over 18,000 would be split into `__KEY_2`, staying under Roblox's per-mesh limit).")
    w("* **Naming:** `A_<row>_<lot>_<type>` foreground (row N/S/E/W = plaza side), `A_Corner_NE/NW/SE/SW` landmarks, `A_Gate_*` side-street gates, "
      "`B_<row>_<lot>` midground, `B_Sky_<sector>` skyline (merged per 400-stud sector), `B_Mega_<n>` megatowers, "
      "`*_P<n>_<PROP>` instanced rooftop machinery, `*_V<n>_VEND_*` vending machines, `SCR_*` screens, `HEX_ALIGN_*` / `HEX_AXIS_*` alignment markers.")
    w("* **Instancing:** rooftop machinery uses 11 shared meshes (HVAC, cooling towers, tanks, vents, dishes, stacks, fan boxes, generators, vending machines) "
      "placed hundreds of times; the FBX stores each mesh once.")
    w("* **Three levels of detail:** foreground = full facades, storefronts, signage, screens, machinery; midground = simplified facades with lit windows, crowns, rooftop/facade screens; "
      "skyline = merged silhouette towers (10 shape families), lit-window bands, crown neon, beacons; megatowers 900–1,700 studs tall.")
    w("* **Scale:** upper floors are 12 studs, ground-floor shops 16 studs with 10-stud glazing, doors ~8 studs, railings 3.4 studs — sized for R15 avatars. Nothing was globally scaled; the preserved park is geometrically identical to the original, every vertex within 0.01 studs (see VERIFICATION.md).")
    w("")
    w("## 4. Textured PBR materials → SurfaceAppearance")
    w("")
    w("All maps are 1024 × 1024 PNG (Roblox stores uploaded images at most 1024 px, so larger maps would only be downscaled). "
      "Normal maps are tangent-space **OpenGL (Y+)**, which is what SurfaceAppearance expects. Roughness / Metalness are greyscale. "
      "UVs are world-scaled: one texture tile covers the stud size in the table, so textures never stretch, and glass mullions line up with the floor/bay grid of the lit-window meshes.")
    w("")
    w("| Key (name suffix) | Material in FBX | SurfaceAppearance maps (in `textures/`) | Tile (studs) | Meshes A / B | Triangles | Used for |")
    w("|---|---|---|---|---|---|---|")
    for key, mat, base, tile, use in PBR:
        maps = "<br>".join(f"{m}: `{base}_{m}.png` ({kb(os.path.join(TEX, f'{base}_{m}.png'))})"
                           for m in ("Color", "Normal", "Roughness", "Metalness"))
        w(f"| `__{key}` | `{mat}` | {maps} | {tile} | {by_key[('A', key)]} / {by_key[('B', key)]} | {tris_key[key]:,} | {use} |")
    w("")
    w("If the 3D Importer created the SurfaceAppearance for you, nothing else is needed. To assign by hand: select the MeshParts whose names end in the key "
      "(Explorer filter, e.g. `__GLS`), insert a **SurfaceAppearance**, set ColorMap / NormalMap / RoughnessMap / MetalnessMap to the uploaded ids. "
      "SurfaceAppearance maps can only be set in Studio (Properties or command bar), not by game scripts at runtime — that is why `CyberpunkSetup` only fills them when run from the command bar. "
      "If you would rather not use textures for some keys, `CyberpunkConfig.Fallback` gives each key a plain Roblox Material + Color (Glass, Metal, Concrete, DiamondPlate, Slate).")
    w("")
    w("## 5. Emissive materials → Material.Neon (no texture)")
    w("")
    w("Blender emission and bloom do not transfer to Roblox, so every glowing surface is its own mesh that becomes **Neon** in Roblox "
      "(glows at its Color under any lighting). The `F_<KEY>.png` 16-px swatches only exist so the FBX material previews in the right colour; they are not needed in Roblox. "
      "Lit-window colours are deliberately darker than the accents so windows read as interiors, not as neon.")
    w("")
    w("| Key | Roblox Color (Neon) | Meshes A / B | Used for |")
    w("|---|---|---|---|")
    for key, c, use in NEON:
        w(f"| `__{key}` | {c[0]}, {c[1]}, {c[2]} | {by_key[('A', key)]} / {by_key[('B', key)]} | {use} |")
    w("")
    w("Lighting hierarchy: landmark buildings (4 corner landmarks + 4 mega ad towers) carry full outlines, exoskeleton ribs and the biggest screens; "
      "about a quarter of the other buildings get two accents, a third one accent, the rest stay dark so the lit ones stand out.")
    w("")
    w("## 6. Signs (texture atlases from the original map)")
    w("")
    w(f"| Key | Texture | Meshes A / B | Notes |")
    w("|---|---|---|---|")
    w(f"| `__SGH` | `signs_h.png` ({kb(os.path.join(TEX, 'signs_h.png'))}, 2048²) | {by_key[('A', 'SGH')]} / {by_key[('B', 'SGH')]} | horizontal shop signs, floor directories, noren curtains; UVs point into the atlas cells |")
    w(f"| `__SGV` | `signs_v.png` ({kb(os.path.join(TEX, 'signs_v.png'))}, 2048²) | {by_key[('A', 'SGV')]} / {by_key[('B', 'SGV')]} | vertical blade signs (both faces), A-frame sidewalk signs |")
    w("")
    w("These are your original map's sign atlases (2048 px; Roblox will store them at 1024 px, which is enough for sign text at street distance). "
      "Apply as MeshPart **TextureID** or SurfaceAppearance ColorMap. They sit next to Neon frames and shop lights, so they read at night without extra setup.")
    w("")
    w("## 7. Screens (separate meshes, animation-ready)")
    w("")
    kinds = Counter(s["kind"] for s in screens)
    w(f"{len(screens)} screens, every one a separate MeshPart named `SCR_*` with its own `AD_*` material and 0–1 UVs across the display surface. "
      f"Kinds: " + ", ".join(f"{k} {v}" for k, v in kinds.most_common()) + ".")
    w("")
    w("* **Static look:** the MeshPart's TextureID / ColorMap shows the ad (a placeholder until you animate it).")
    w("* **Self-lit + animated:** `CyberpunkSetup` adds an invisible anchor Part per flat panel with a **SurfaceGui** (`LightInfluence = 0`, Brightness from config) holding an ImageLabel. "
      "Curved screens (corner landmarks, modern towers) are made of flat facets; each facet gets its own SurfaceGui showing its slice of the artwork via `ImageRectOffset/ImageRectSize`, so the picture wraps the corner continuously. "
      "Anchors are tagged `HEX_Screen` with attributes `Ad`, `Kind`, `Screen`, `Panel`.")
    w("* **Video:** put `[\"SCR_name\"] = \"rbxassetid://<video>\"` into `CyberpunkConfig.Videos` and the screen gets a looping **VideoFrame** instead (curved screens too, sliced per facet).")
    w("* **Rotating billboards:** screen kinds in `CyberpunkConfig.RotateKinds` cycle between ads of the same aspect ratio (client script). Swap or add images any time — layouts are in the formats below.")
    w("* Nothing depends on Blender shader animation.")
    w("")
    w("| Ad texture | Size (px) | Format | Screens using it |")
    w("|---|---|---|---|")
    for f in sorted(x for x in os.listdir(TEX) if x.startswith("AD_")):
        im = Image.open(os.path.join(TEX, f))
        use = ad_use.get(f, [])
        fmt = use[0]["format"] if use else ""
        w(f"| `{f}` | {im.size[0]} × {im.size[1]} | {fmt} | {len(use)} |")
    w("")
    w("Formats: W 2:1 facade / rooftop billboards, X 4:1 banners / tickers, P 8:3 curved corner wraps, T 1:2 tall facade screens, S 1:4 holo strips / blades, Q 1:1 square. "
      "All artwork is original (fictional brands) — drawn by `blender/cp2_ads.py`, so you can edit text/colours and regenerate.")
    w("")
    w("## 8. Lights (from `CityData.lights`)")
    w("")
    w("* **Court floods:** a shadow-casting SpotLight at the top of each `LightMast_*`, aimed at the courts (Brightness `CourtFloodBrightness`). Together with `OutdoorAmbient` this keeps both courts clearly playable.")
    w("* **Screen spill:** SurfaceLights in front of the big screens (magenta/cyan tint, range ≤ 60).")
    w("* **Street level:** PointLights inside every second shop; red PointLights on antenna beacons.")
    w("* Total is capped by `MaxLights`; set `ShopLights = false` or `ScreenSurfaceLights = false` on low-end targets.")
    w("")
    w("## 9. Performance notes")
    w("")
    w("* FBX size is not runtime cost. Runtime totals: "
      f"{ver['objects']['A'] + ver['objects']['B']:,} MeshParts, {ver['triangles']['A'] + ver['triangles']['B']:,} triangles, "
      "10 PBR texture sets + 45 ad images + 2 sign atlases.")
    w("* File B (midground/skyline) is unreachable: the setup turns off its collisions (`CollideFileB = false`). For StreamingEnabled places, set model B's `ModelStreamingMode = Persistent` so the skyline never pops out, and keep `RenderFidelity = Automatic` on its MeshParts.")
    w("* Small details (neon, windows, signs, screens, small props) have CanCollide / CanQuery / CastShadow off.")
    w("* Instanced props share one mesh asset each, so Roblox can batch them.")
    w("")
    w("## 10. What does not transfer automatically")
    w("")
    w("* Blender bloom, emission strength, volumetric haze and the preview renders' area lights: replaced in Roblox by Neon parts, SurfaceGuis, Lights and the Lighting effects from `CyberpunkSetup`.")
    w("* Whether the 3D Importer auto-creates SurfaceAppearances from the FBX texture references depends on your Studio version; section 4 covers the manual path.")
    w("* Animated screens only animate through the included scripts (or your own VideoFrames / SurfaceGuis) — not from anything inside the FBX.")
    with open(os.path.join(EX, "ROBLOX_SETUP_GUIDE.md"), "w") as f:
        f.write("\n".join(o) + "\n")
    print("wrote export/ROBLOX_SETUP_GUIDE.md")


if __name__ == "__main__":
    main()
