# HEX! Cyberpunk City v2 — Roblox Studio setup & texture / material guide

Everything here is generated from the actual export (`blender/cp2_guide.py`). Per-object detail: [`texture_assignment.csv`](texture_assignment.csv) (every MeshPart → material → PNG maps → Roblox setting) and [`screens.csv`](screens.csv) (every screen → ad texture). Export checks: [`VERIFICATION.md`](VERIFICATION.md).

## 1. Files

| File | Size | Contents |
|---|---|---|
| `HEX_Cyberpunk_City_A.fbx` | 12.8 MB | the original basketball park (unchanged, included only here), all foreground buildings around the plaza, the 4 corner landmarks, side-street ad gates / skybridges, their screens and props — 3409 meshes, 317,410 triangles |
| `HEX_Cyberpunk_City_B.fbx` | 12.97 MB | midground towers, skyline towers, 12 megatowers, their screens and props — 2788 meshes, 248,296 triangles |
| `textures/` | 17.0 MB | every PNG the materials use (listed below) |
| `roblox/CyberpunkCityV2.rbxmx` | | setup / animation scripts + `CityData` (screen panels, lights, alignment) |
| `../output/HEX_Cyberpunk_City.blend` | | editable Blender project (collections `A_*` = file A, `B_*` = file B) |
| `../output/HEX_City_00_original_backup.blend` | | backup of the untouched original scene |

Both FBX files use the **same world origin, units and axes as `HEX_City_00_FULL_CITY.fbx`** (Blender default FBX export: Y-up, 1 unit = 1 stud, no global scale), so import them with the same settings you used for the original map. Each file contains a 4-stud cube at (0, −60, 0) (`HEX_ALIGN_A` / `HEX_ALIGN_B`, 60 studs under the plaza) used to line the two imports up.

## 2. Import steps

1. Keep `HEX_Cyberpunk_City_A.fbx`, `HEX_Cyberpunk_City_B.fbx` and the `textures/` folder together (the FBX files reference `textures/<name>.png` relatively).
2. **File → Import 3D** → `HEX_Cyberpunk_City_A.fbx`. Use the same import options as for your original map (no rescale; keep the file's scene position if your Studio version offers it; Anchored). File A already contains the park, so remove the old `HEX_City_00_FULL_CITY` model to avoid a duplicate.
3. **File → Import 3D** → `HEX_Cyberpunk_City_B.fbx` with the same options.
4. In the Importer, check that materials show textures. If a texture is missing, upload the PNG from `textures/` (Asset Manager → Bulk Import) and assign it (section 4), or fill the ids into `CyberpunkConfig.SurfaceTextures` and let the setup script apply them.
5. Right-click **Workspace → Insert from File…** → `roblox/CyberpunkCityV2.rbxmx`.
6. Paste into the **command bar** and press Enter: `require(workspace.CyberpunkCityV2.CyberpunkSetup).run()`  
   This (a) moves model B so its marker sits exactly on A's marker and warns if either import was rescaled, (b) turns every `__NEON_*` / `__WIN_*` / `__SHOP_LIT` part into **Neon** with its colour, (c) builds a self-lit SurfaceGui on every screen, (d) places the court flood SpotLights, shop/beacon PointLights and screen SurfaceLights, (e) sets the night Lighting (Future, Atmosphere, Bloom, ColorCorrection). Running it from the command bar bakes the result into the place; otherwise `RunSetup` does it at game start.
7. Press **Play** to see the client animation (scan lines, rotating billboards, blinking beacons, a few buzzing neon tubes).

The setup script reports how many parts got Neon, kept textures, or fell back to plain Roblox materials, so you can see at a glance whether textures came through.

## 3. How the scene is organised

* **One material per object.** Every Blender object (= one Roblox MeshPart) has exactly one material; its name ends with `__<KEY>` (e.g. `A_N_05_Zakkyo__GLS`, `B_Mega_03__NEON_MAG`). The largest single mesh is 6,600 triangles (anything over 18,000 would be split into `__KEY_2`, staying under Roblox's per-mesh limit).
* **Naming:** `A_<row>_<lot>_<type>` foreground (row N/S/E/W = plaza side), `A_Corner_NE/NW/SE/SW` landmarks, `A_Gate_*` side-street gates, `B_<row>_<lot>` midground, `B_Sky_<sector>` skyline (merged per 400-stud sector), `B_Mega_<n>` megatowers, `*_P<n>_<PROP>` instanced rooftop machinery, `*_V<n>_VEND_*` vending machines, `SCR_*` screens, `HEX_ALIGN_*` markers.
* **Instancing:** rooftop machinery uses 11 shared meshes (HVAC, cooling towers, tanks, vents, dishes, stacks, fan boxes, generators, vending machines) placed hundreds of times; the FBX stores each mesh once.
* **Three levels of detail:** foreground = full facades, storefronts, signage, screens, machinery; midground = simplified facades with lit windows, crowns, rooftop/facade screens; skyline = merged silhouette towers (10 shape families), lit-window bands, crown neon, beacons; megatowers 900–1,700 studs tall.
* **Scale:** upper floors are 12 studs, ground-floor shops 16 studs with 10-stud glazing, doors ~8 studs, railings 3.4 studs — sized for R15 avatars. Nothing was globally scaled; the preserved park is geometrically identical to the original, every vertex within 0.01 studs (see VERIFICATION.md).

## 4. Textured PBR materials → SurfaceAppearance

All maps are 1024 × 1024 PNG (Roblox stores uploaded images at most 1024 px, so larger maps would only be downscaled). Normal maps are tangent-space **OpenGL (Y+)**, which is what SurfaceAppearance expects. Roughness / Metalness are greyscale. UVs are world-scaled: one texture tile covers the stud size in the table, so textures never stretch, and glass mullions line up with the floor/bay grid of the lit-window meshes.

| Key (name suffix) | Material in FBX | SurfaceAppearance maps (in `textures/`) | Tile (studs) | Meshes A / B | Triangles | Used for |
|---|---|---|---|---|---|---|
| `__GLS` | `CP_GlassCurtain` | Color: `T_GlassCurtain_Color.png` (99 KB)<br>Normal: `T_GlassCurtain_Normal.png` (6 KB)<br>Roughness: `T_GlassCurtain_Roughness.png` (94 KB)<br>Metalness: `T_GlassCurtain_Metalness.png` (2 KB) | 32 x 48 | 99 / 68 | 4,210 | curtain-wall glazing, mullion grid matches 5.33-stud bays / 12-stud floors |
| `__RIB` | `CP_GlassRibbon` | Color: `T_GlassRibbon_Color.png` (112 KB)<br>Normal: `T_GlassRibbon_Normal.png` (5 KB)<br>Roughness: `T_GlassRibbon_Roughness.png` (47 KB)<br>Metalness: `T_GlassRibbon_Metalness.png` (2 KB) | 32 x 24 | 47 / 23 | 328 | ribbon windows with concrete spandrels |
| `__PNL` | `CP_PanelMetal` | Color: `T_PanelMetal_Color.png` (169 KB)<br>Normal: `T_PanelMetal_Normal.png` (63 KB)<br>Roughness: `T_PanelMetal_Roughness.png` (135 KB)<br>Metalness: `T_PanelMetal_Metalness.png` (2 KB) | 24 x 24 | 172 / 152 | 20,692 | gunmetal cladding, fascias, screen backs, recess linings |
| `__CON` | `CP_ConcreteDark` | Color: `T_ConcreteDark_Color.png` (399 KB)<br>Normal: `T_ConcreteDark_Normal.png` (496 KB)<br>Roughness: `T_ConcreteDark_Roughness.png` (178 KB)<br>Metalness: `T_ConcreteDark_Metalness.png` (1 KB) | 32 x 32 | 110 / 112 | 22,628 | board-formed concrete: party walls, pilasters, slabs, parapets |
| `__TEC` | `CP_TechPanel` | Color: `T_TechPanel_Color.png` (236 KB)<br>Normal: `T_TechPanel_Normal.png` (74 KB)<br>Roughness: `T_TechPanel_Roughness.png` (165 KB)<br>Metalness: `T_TechPanel_Metalness.png` (5 KB) | 16 x 16 | 64 / 85 | 5,776 | sci-fi panelling, crown blocks, balustrades |
| `__MEC` | `CP_Mechanical` | Color: `T_Mechanical_Color.png` (324 KB)<br>Normal: `T_Mechanical_Normal.png` (17 KB)<br>Roughness: `T_Mechanical_Roughness.png` (169 KB)<br>Metalness: `T_Mechanical_Metalness.png` (13 KB) | 8 x 8 | 1212 / 674 | 114,802 | HVAC, ducts, vents, cooling towers, generators, AC units |
| `__ROF` | `CP_RoofDeck` | Color: `T_RoofDeck_Color.png` (319 KB)<br>Normal: `T_RoofDeck_Normal.png` (281 KB)<br>Roughness: `T_RoofDeck_Roughness.png` (6 KB)<br>Metalness: `T_RoofDeck_Metalness.png` (1 KB) | 32 x 32 | 109 / 198 | 8,328 | roof membranes |
| `__STL` | `CP_Steel` | Color: `T_Steel_Color.png` (245 KB)<br>Normal: `T_Steel_Normal.png` (334 KB)<br>Roughness: `T_Steel_Roughness.png` (161 KB)<br>Metalness: `T_Steel_Metalness.png` (30 KB) | 8 x 8 | 113 / 193 | 156,118 | trusses, exoskeletons, frames, catwalks, pipes, railings, antennas |
| `__LOU` | `CP_Louver` | Color: `T_Louver_Color.png` (6 KB)<br>Normal: `T_Louver_Normal.png` (5 KB)<br>Roughness: `T_Louver_Roughness.png` (2 KB)<br>Metalness: `T_Louver_Metalness.png` (2 KB) | 8 x 12 | 0 / 22 | 84 | louvred midground facades |
| `__TWN` | `CP_TowerNight` | Color: `T_TowerNight_Color.png` (10 KB)<br>Normal: `T_TowerNight_Normal.png` (5 KB)<br>Roughness: `T_TowerNight_Roughness.png` (2 KB)<br>Metalness: `T_TowerNight_Metalness.png` (2 KB) | 32 x 48 | 0 / 198 | 17,344 | midground / skyline glazing (pale windows baked into the colour map) |

If the 3D Importer created the SurfaceAppearance for you, nothing else is needed. To assign by hand: select the MeshParts whose names end in the key (Explorer filter, e.g. `__GLS`), insert a **SurfaceAppearance**, set ColorMap / NormalMap / RoughnessMap / MetalnessMap to the uploaded ids. SurfaceAppearance maps can only be set in Studio (Properties or command bar), not by game scripts at runtime — that is why `CyberpunkSetup` only fills them when run from the command bar. If you would rather not use textures for some keys, `CyberpunkConfig.Fallback` gives each key a plain Roblox Material + Color (Glass, Metal, Concrete, DiamondPlate, Slate).

## 5. Emissive materials → Material.Neon (no texture)

Blender emission and bloom do not transfer to Roblox, so every glowing surface is its own mesh that becomes **Neon** in Roblox (glows at its Color under any lighting). The `F_<KEY>.png` 16-px swatches only exist so the FBX material previews in the right colour; they are not needed in Roblox. Lit-window colours are deliberately darker than the accents so windows read as interiors, not as neon.

| Key | Roblox Color (Neon) | Meshes A / B | Used for |
|---|---|---|---|
| `__NEON_CYN` | 0, 230, 255 | 72 / 83 | cyan accent strips / outlines |
| `__NEON_MAG` | 255, 25, 175 | 77 / 65 | magenta accent strips / outlines |
| `__NEON_VIO` | 150, 45, 255 | 50 / 54 | violet accents |
| `__NEON_BLU` | 30, 95, 255 | 38 / 46 | electric blue accents |
| `__NEON_RED` | 255, 32, 45 | 82 / 142 | aircraft beacons, occasional red accents, lanterns |
| `__NEON_AMB` | 255, 150, 25 | 53 / 0 | occasional amber (lanterns, a few signs) |
| `__NEON_WHT` | 200, 215, 255 | 63 / 34 | LED strips under canopies, billboard flood bars |
| `__WIN_WRM` | 150, 110, 70 | 78 / 138 | lit windows, warm |
| `__WIN_COL` | 80, 115, 160 | 69 / 131 | lit windows, cool |
| `__WIN_PNK` | 160, 70, 125 | 52 / 82 | lit windows, pink |
| `__WIN_VIO` | 105, 80, 165 | 57 / 97 | lit windows, violet; skybridge glow |
| `__SHOP_LIT` | 175, 160, 140 | 139 / 0 | storefront glass, vending machine fronts |

Lighting hierarchy: landmark buildings (4 corner landmarks + 4 mega ad towers) carry full outlines, exoskeleton ribs and the biggest screens; about a quarter of the other buildings get two accents, a third one accent, the rest stay dark so the lit ones stand out.

## 6. Signs (texture atlases from the original map)

| Key | Texture | Meshes A / B | Notes |
|---|---|---|---|
| `__SGH` | `signs_h.png` (370 KB, 2048²) | 105 / 0 | horizontal shop signs, floor directories, noren curtains; UVs point into the atlas cells |
| `__SGV` | `signs_v.png` (501 KB, 2048²) | 103 / 0 | vertical blade signs (both faces), A-frame sidewalk signs |

These are your original map's sign atlases (2048 px; Roblox will store them at 1024 px, which is enough for sign text at street distance). Apply as MeshPart **TextureID** or SurfaceAppearance ColorMap. They sit next to Neon frames and shop lights, so they read at night without extra setup.

## 7. Screens (separate meshes, animation-ready)

492 screens, every one a separate MeshPart named `SCR_*` with its own `AD_*` material and 0–1 UVs across the display surface. Kinds: holo 77, stack 75, storefront 64, arcade 59, rooftop 52, skyline 45, mg_facade 34, giant 25, crown 17, mega 12, cantilever 10, suspended 8, layered 4, sky 4, curved 3, ticker 3.

* **Static look:** the MeshPart's TextureID / ColorMap shows the ad (a placeholder until you animate it).
* **Self-lit + animated:** `CyberpunkSetup` adds an invisible anchor Part per flat panel with a **SurfaceGui** (`LightInfluence = 0`, Brightness from config) holding an ImageLabel. Curved screens (corner landmarks, modern towers) are made of flat facets; each facet gets its own SurfaceGui showing its slice of the artwork via `ImageRectOffset/ImageRectSize`, so the picture wraps the corner continuously. Anchors are tagged `HEX_Screen` with attributes `Ad`, `Kind`, `Screen`, `Panel`.
* **Video:** put `["SCR_name"] = "rbxassetid://<video>"` into `CyberpunkConfig.Videos` and the screen gets a looping **VideoFrame** instead (curved screens too, sliced per facet).
* **Rotating billboards:** screen kinds in `CyberpunkConfig.RotateKinds` cycle between ads of the same aspect ratio (client script). Swap or add images any time — layouts are in the formats below.
* Nothing depends on Blender shader animation.

| Ad texture | Size (px) | Format | Screens using it |
|---|---|---|---|
| `AD_AikoLive.png` | 512 × 1024 | T | 5 |
| `AD_AkaiMotors.png` | 1024 × 512 | W | 25 |
| `AD_ArashiSec.png` | 512 × 1024 | T | 5 |
| `AD_BladeEdge.png` | 256 × 1024 | S | 15 |
| `AD_CourtKings.png` | 1024 × 1024 | Q | 2 |
| `AD_Cyber.png` | 256 × 1024 | S | 14 |
| `AD_DataStream.png` | 1024 × 256 | X | 11 |
| `AD_DenkiCola.png` | 512 × 1024 | T | 5 |
| `AD_Hanabi.png` | 1024 × 1024 | Q | 2 |
| `AD_HexLeague.png` | 1024 × 512 | W | 25 |
| `AD_HexLeagueTall.png` | 512 × 1024 | T | 5 |
| `AD_HoloDancer.png` | 256 × 1024 | S | 15 |
| `AD_HoloKoi.png` | 256 × 1024 | S | 15 |
| `AD_Karaoke24.png` | 1024 × 1024 | Q | 2 |
| `AD_KirinDeck.png` | 1024 × 512 | W | 25 |
| `AD_KitsuneMask.png` | 1024 × 1024 | Q | 1 |
| `AD_KoiAir.png` | 1024 × 256 | X | 9 |
| `AD_MatchaPlus.png` | 256 × 1024 | S | 15 |
| `AD_MegaSale.png` | 1024 × 512 | W | 25 |
| `AD_MindUpload.png` | 1024 × 512 | W | 25 |
| `AD_MiraiBank.png` | 1024 × 256 | X | 9 |
| `AD_NanoMed.png` | 1024 × 256 | X | 10 |
| `AD_NekoNet.png` | 512 × 1024 | T | 5 |
| `AD_NeoShibuya.png` | 1024 × 384 |  | 0 |
| `AD_NeonNoodle.png` | 1024 × 1024 | Q | 1 |
| `AD_NewsTicker.png` | 1024 × 256 | X | 9 |
| `AD_NexusAndroids.png` | 512 × 1024 | T | 5 |
| `AD_NoirParfum.png` | 512 × 1024 | T | 3 |
| `AD_OkamiArms.png` | 512 × 1024 | T | 5 |
| `AD_Onigiri24.png` | 1024 × 1024 | Q | 2 |
| `AD_OrbitalResorts.png` | 1024 × 1024 | Q | 2 |
| `AD_Pachinko.png` | 512 × 1024 | T | 4 |
| `AD_PlayHex.png` | 1024 × 512 | W | 25 |
| `AD_RamenIchiban.png` | 1024 × 256 | X | 10 |
| `AD_RyuGames.png` | 1024 × 1024 | Q | 2 |
| `AD_SakuraLink.png` | 1024 × 512 | W | 24 |
| `AD_ScanMe.png` | 1024 × 1024 | Q | 2 |
| `AD_ShibuyaKanji.png` | 1024 × 384 | P | 1 |
| `AD_SushiSpeed.png` | 1024 × 512 | W | 25 |
| `AD_SynthFM.png` | 1024 × 512 | W | 25 |
| `AD_TipOff.png` | 1024 × 256 | X | 11 |
| `AD_Titan3.png` | 1024 × 384 | P | 2 |
| `AD_Tokyo2099.png` | 256 × 1024 | S | 16 |
| `AD_VoltRunner.png` | 1024 × 512 | W | 23 |
| `AD_YumeOptics.png` | 1024 × 512 | W | 25 |

Formats: W 2:1 facade / rooftop billboards, X 4:1 banners / tickers, P 8:3 curved corner wraps, T 1:2 tall facade screens, S 1:4 holo strips / blades, Q 1:1 square. All artwork is original (fictional brands) — drawn by `blender/cp2_ads.py`, so you can edit text/colours and regenerate.

## 8. Lights (from `CityData.lights`)

* **Court floods:** a shadow-casting SpotLight at the top of each `LightMast_*`, aimed at the courts (Brightness `CourtFloodBrightness`). Together with `OutdoorAmbient` this keeps both courts clearly playable.
* **Screen spill:** SurfaceLights in front of the big screens (magenta/cyan tint, range ≤ 60).
* **Street level:** PointLights inside every second shop; red PointLights on antenna beacons.
* Total is capped by `MaxLights`; set `ShopLights = false` or `ScreenSurfaceLights = false` on low-end targets.

## 9. Performance notes

* FBX size is not runtime cost. Runtime totals: 6,197 MeshParts, 565,706 triangles, 10 PBR texture sets + 45 ad images + 2 sign atlases.
* File B (midground/skyline) is unreachable: the setup turns off its collisions (`CollideFileB = false`). For StreamingEnabled places, set model B's `ModelStreamingMode = Persistent` so the skyline never pops out, and keep `RenderFidelity = Automatic` on its MeshParts.
* Small details (neon, windows, signs, screens, small props) have CanCollide / CanQuery / CastShadow off.
* Instanced props share one mesh asset each, so Roblox can batch them.

## 10. What does not transfer automatically

* Blender bloom, emission strength, volumetric haze and the preview renders' area lights: replaced in Roblox by Neon parts, SurfaceGuis, Lights and the Lighting effects from `CyberpunkSetup`.
* Whether the 3D Importer auto-creates SurfaceAppearances from the FBX texture references depends on your Studio version; section 4 covers the manual path.
* Animated screens only animate through the included scripts (or your own VideoFrames / SurfaceGuis) — not from anything inside the FBX.
