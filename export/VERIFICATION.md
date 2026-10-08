# Export verification

Overall: **PASS** (re-imported both FBX files into a clean Blender scene)

| File | Size | Objects | Triangles | Bounds min | Bounds max |
|---|---|---|---|---|---|
| `HEX_Cyberpunk_City_A.fbx` | 18.01 MB (< 20 MB) | 3657 | 509776 | [-1500.0, -1500.0, -62.0] | [1500.0, 1500.0, 543.1] |
| `HEX_Cyberpunk_City_B.fbx` | 14.05 MB (< 20 MB) | 2860 | 297308 | [-1420.0, -1496.4, -62.0] | [1499.4, 1482.0, 1789.1] |

| Check | Result |
|---|---|
| Alignment markers (both at 0, 0, -60) | same origin: A ([0.0, -0.0, -60.0], [4.0, 4.0, 4.0]), B ([0.0, -0.0, -60.0], [4.0, 4.0, 4.0]) |
| Preserved basketball-map objects identical to the original FBX | 144 / 144 identical, changed 0, missing 0 |
| Preserved map included only once (not in B) | yes |
| New geometry inside the plaza / practice area (below 60 studs) | 0 vertices |
| Objects present in both files | 0 |
| Meshes without UVs / non-finite UVs | 0 / 0 |
| Meshes with other than exactly one material | 0 |
| Referenced texture files missing on disk | 0 |
| Texture references containing folders (must be bare file names) | 0 |

## Materials after re-import

| Material | Objects | Triangles | In file | Textures |
|---|---|---|---|---|
| `AD_AikoTour` | 7 | 28 | A, B | AD_AikoTour.png |
| `AD_AkaiMotors` | 22 | 44 | A, B | AD_AkaiMotors.png |
| `AD_Aquarium` | 2 | 4 | A | AD_Aquarium.png |
| `AD_ArashiWatch` | 7 | 14 | A, B | AD_ArashiWatch.png |
| `AD_ClubVoid` | 3 | 6 | A | AD_ClubVoid.png |
| `AD_CourtKings` | 2 | 4 | A | AD_CourtKings.png |
| `AD_Cyber` | 1 | 2 | A | AD_Cyber.png |
| `AD_DenkiCola` | 7 | 14 | A, B | AD_DenkiCola.png |
| `AD_Eterna` | 21 | 42 | A, B | AD_Eterna.png |
| `AD_Hanabi` | 3 | 6 | A, B | AD_Hanabi.png |
| `AD_HexLeague` | 21 | 42 | A, B | AD_HexLeague.png |
| `AD_HexLeague23` | 6 | 12 | A, B | AD_HexLeague23.png |
| `AD_HexNews` | 13 | 26 | A | AD_HexNews.png |
| `AD_Karaoke` | 2 | 4 | A, B | AD_Karaoke.png |
| `AD_Katana` | 3 | 6 | A | AD_Katana.png |
| `AD_Kirin` | 21 | 42 | A, B | AD_Kirin.png |
| `AD_KitsuneCafe` | 2 | 4 | A | AD_KitsuneCafe.png |
| `AD_KoiAir` | 13 | 26 | A | AD_KoiAir.png |
| `AD_Konbini` | 1 | 2 | A | AD_Konbini.png |
| `AD_Matcha` | 3 | 6 | A | AD_Matcha.png |
| `AD_MiraiBank` | 15 | 30 | A | AD_MiraiBank.png |
| `AD_NeoShibuya` | 1 | 36 | A | AD_NeoShibuya.png |
| `AD_NeonNoodle` | 1 | 2 | A | AD_NeonNoodle.png |
| `AD_Nexus` | 6 | 12 | A, B | AD_Nexus.png |
| `AD_NightMarket` | 21 | 42 | A, B | AD_NightMarket.png |
| `AD_NoirParfum` | 6 | 12 | A, B | AD_NoirParfum.png |
| `AD_Okami` | 8 | 16 | A, B | AD_Okami.png |
| `AD_Orbital` | 2 | 4 | A | AD_Orbital.png |
| `AD_RamenIchiban` | 15 | 30 | A | AD_RamenIchiban.png |
| `AD_RyuGames` | 1 | 2 | A | AD_RyuGames.png |
| `AD_SakuraAir` | 22 | 44 | A, B | AD_SakuraAir.png |
| `AD_ShibuyaKanji` | 1 | 40 | A | AD_ShibuyaKanji.png |
| `AD_SynthWave` | 21 | 42 | A, B | AD_SynthWave.png |
| `AD_TipOff` | 14 | 58 | A | AD_TipOff.png |
| `AD_Titan3` | 2 | 4 | B | AD_Titan3.png |
| `AD_Tokyo2099` | 3 | 6 | A | AD_Tokyo2099.png |
| `AD_Volt` | 21 | 42 | A, B | AD_Volt.png |
| `AD_YumeOptics` | 22 | 44 | A, B | AD_YumeOptics.png |
| `CP_ConcreteDark` | 224 | 60236 | A, B | T_ConcreteDark_Color.png, T_ConcreteDark_Metalness.png, T_ConcreteDark_Normal.png, T_ConcreteDark_Roughness.png |
| `CP_GlassCurtain` | 259 | 27650 | A, B | T_GlassCurtain_Color.png, T_GlassCurtain_Metalness.png, T_GlassCurtain_Normal.png, T_GlassCurtain_Roughness.png |
| `CP_Louver` | 19 | 74 | B | T_Louver_Color.png, T_Louver_Metalness.png, T_Louver_Normal.png, T_Louver_Roughness.png |
| `CP_Mechanical` | 1905 | 115476 | A, B | T_Mechanical_Color.png, T_Mechanical_Metalness.png, T_Mechanical_Normal.png, T_Mechanical_Roughness.png |
| `CP_NEON_AMB` | 53 | 1152 | A |  |
| `CP_NEON_BLU` | 68 | 7654 | A, B |  |
| `CP_NEON_CYN` | 125 | 17558 | A, B |  |
| `CP_NEON_MAG` | 110 | 11568 | A, B |  |
| `CP_NEON_RED` | 230 | 10422 | A, B |  |
| `CP_NEON_VIO` | 80 | 8552 | A, B |  |
| `CP_NEON_WHT` | 137 | 6560 | A, B |  |
| `CP_PanelMetal` | 339 | 34930 | A, B | T_PanelMetal_Color.png, T_PanelMetal_Metalness.png, T_PanelMetal_Normal.png, T_PanelMetal_Roughness.png |
| `CP_RoofDeck` | 307 | 8328 | A, B | T_RoofDeck_Color.png, T_RoofDeck_Metalness.png, T_RoofDeck_Normal.png, T_RoofDeck_Roughness.png |
| `CP_SHOP_LIT` | 135 | 396 | A |  |
| `CP_SignsH` | 105 | 1386 | A | signs_h.png |
| `CP_SignsV` | 104 | 1026 | A | signs_v.png |
| `CP_Steel` | 299 | 244082 | A, B | T_Steel_Color.png, T_Steel_Metalness.png, T_Steel_Normal.png, T_Steel_Roughness.png |
| `CP_TechPanel` | 182 | 94090 | A, B | T_TechPanel_Color.png, T_TechPanel_Metalness.png, T_TechPanel_Normal.png, T_TechPanel_Roughness.png |
| `CP_TowerNight` | 305 | 18514 | A, B | T_TowerNight_Color.png, T_TowerNight_Metalness.png, T_TowerNight_Normal.png, T_TowerNight_Roughness.png |
| `CP_WIN_COL` | 281 | 37338 | A, B |  |
| `CP_WIN_PNK` | 233 | 9148 | A, B |  |
| `CP_WIN_VIO` | 246 | 12498 | A, B |  |
| `CP_WIN_WRM` | 285 | 52166 | A, B |  |
| `HEX_Palette` | 144 | 25480 | A | palette.png |
