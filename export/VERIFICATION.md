# Export verification

Overall: **PASS** (re-imported both FBX files into a clean Blender scene)

| File | Size | Objects | Triangles | Bounds min | Bounds max |
|---|---|---|---|---|---|
| `HEX_Cyberpunk_City_A.fbx` | 12.8 MB (< 20 MB) | 3411 | 317434 | [-1500.0, -1500.0, -62.0] | [1500.0, 1500.0, 534.0] |
| `HEX_Cyberpunk_City_B.fbx` | 12.97 MB (< 20 MB) | 2788 | 248296 | [-1420.0, -1496.4, -62.0] | [1499.4, 1482.0, 1789.1] |

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

## Materials after re-import

| Material | Objects | Triangles | In file | Textures |
|---|---|---|---|---|
| `AD_AikoLive` | 5 | 10 | A, B | AD_AikoLive.png |
| `AD_AkaiMotors` | 25 | 50 | A, B | AD_AkaiMotors.png |
| `AD_ArashiSec` | 5 | 10 | A, B | AD_ArashiSec.png |
| `AD_BladeEdge` | 15 | 30 | A, B | AD_BladeEdge.png |
| `AD_CourtKings` | 2 | 4 | A | AD_CourtKings.png |
| `AD_Cyber` | 14 | 28 | A, B | AD_Cyber.png |
| `AD_DataStream` | 11 | 52 | A | AD_DataStream.png |
| `AD_DenkiCola` | 5 | 10 | A, B | AD_DenkiCola.png |
| `AD_Hanabi` | 2 | 4 | A | AD_Hanabi.png |
| `AD_HexLeague` | 25 | 50 | A, B | AD_HexLeague.png |
| `AD_HexLeagueTall` | 5 | 10 | A, B | AD_HexLeagueTall.png |
| `AD_HoloDancer` | 15 | 30 | A, B | AD_HoloDancer.png |
| `AD_HoloKoi` | 15 | 30 | A, B | AD_HoloKoi.png |
| `AD_Karaoke24` | 2 | 4 | A | AD_Karaoke24.png |
| `AD_KirinDeck` | 25 | 50 | A, B | AD_KirinDeck.png |
| `AD_KitsuneMask` | 1 | 2 | B | AD_KitsuneMask.png |
| `AD_KoiAir` | 9 | 18 | A | AD_KoiAir.png |
| `AD_MatchaPlus` | 15 | 30 | A, B | AD_MatchaPlus.png |
| `AD_MegaSale` | 25 | 50 | A, B | AD_MegaSale.png |
| `AD_MindUpload` | 25 | 50 | A, B | AD_MindUpload.png |
| `AD_MiraiBank` | 9 | 18 | A | AD_MiraiBank.png |
| `AD_NanoMed` | 10 | 20 | A | AD_NanoMed.png |
| `AD_NekoNet` | 5 | 10 | A, B | AD_NekoNet.png |
| `AD_NeonNoodle` | 1 | 2 | B | AD_NeonNoodle.png |
| `AD_NewsTicker` | 9 | 18 | A | AD_NewsTicker.png |
| `AD_NexusAndroids` | 5 | 10 | A, B | AD_NexusAndroids.png |
| `AD_NoirParfum` | 3 | 6 | A, B | AD_NoirParfum.png |
| `AD_OkamiArms` | 5 | 10 | A, B | AD_OkamiArms.png |
| `AD_Onigiri24` | 2 | 4 | A | AD_Onigiri24.png |
| `AD_OrbitalResorts` | 2 | 4 | B | AD_OrbitalResorts.png |
| `AD_Pachinko` | 4 | 8 | A, B | AD_Pachinko.png |
| `AD_PlayHex` | 25 | 50 | A, B | AD_PlayHex.png |
| `AD_RamenIchiban` | 10 | 20 | A | AD_RamenIchiban.png |
| `AD_RyuGames` | 2 | 4 | A | AD_RyuGames.png |
| `AD_SakuraLink` | 24 | 48 | A, B | AD_SakuraLink.png |
| `AD_ScanMe` | 2 | 4 | A | AD_ScanMe.png |
| `AD_ShibuyaKanji` | 1 | 36 | A | AD_ShibuyaKanji.png |
| `AD_SushiSpeed` | 25 | 50 | A, B | AD_SushiSpeed.png |
| `AD_SynthFM` | 25 | 50 | A, B | AD_SynthFM.png |
| `AD_TipOff` | 11 | 22 | A | AD_TipOff.png |
| `AD_Titan3` | 2 | 42 | A, B | AD_Titan3.png |
| `AD_Tokyo2099` | 16 | 32 | A, B | AD_Tokyo2099.png |
| `AD_VoltRunner` | 23 | 46 | A, B | AD_VoltRunner.png |
| `AD_YumeOptics` | 25 | 50 | A, B | AD_YumeOptics.png |
| `CP_ConcreteDark` | 224 | 22652 | A, B | T_ConcreteDark_Color.png, T_ConcreteDark_Metalness.png, T_ConcreteDark_Normal.png, T_ConcreteDark_Roughness.png |
| `CP_GlassCurtain` | 167 | 4210 | A, B | T_GlassCurtain_Color.png, T_GlassCurtain_Metalness.png, T_GlassCurtain_Normal.png, T_GlassCurtain_Roughness.png |
| `CP_GlassRibbon` | 70 | 328 | A, B | T_GlassRibbon_Color.png, T_GlassRibbon_Metalness.png, T_GlassRibbon_Normal.png, T_GlassRibbon_Roughness.png |
| `CP_Louver` | 22 | 84 | B | T_Louver_Color.png, T_Louver_Metalness.png, T_Louver_Normal.png, T_Louver_Roughness.png |
| `CP_Mechanical` | 1886 | 114802 | A, B | T_Mechanical_Color.png, T_Mechanical_Metalness.png, T_Mechanical_Normal.png, T_Mechanical_Roughness.png |
| `CP_NEON_AMB` | 53 | 1208 | A |  |
| `CP_NEON_BLU` | 84 | 9190 | A, B |  |
| `CP_NEON_CYN` | 155 | 21944 | A, B |  |
| `CP_NEON_MAG` | 142 | 15858 | A, B |  |
| `CP_NEON_RED` | 224 | 12224 | A, B |  |
| `CP_NEON_VIO` | 104 | 11272 | A, B |  |
| `CP_NEON_WHT` | 97 | 4836 | A, B |  |
| `CP_PanelMetal` | 324 | 20692 | A, B | T_PanelMetal_Color.png, T_PanelMetal_Metalness.png, T_PanelMetal_Normal.png, T_PanelMetal_Roughness.png |
| `CP_RoofDeck` | 307 | 8328 | A, B | T_RoofDeck_Color.png, T_RoofDeck_Metalness.png, T_RoofDeck_Normal.png, T_RoofDeck_Roughness.png |
| `CP_SHOP_LIT` | 139 | 410 | A |  |
| `CP_SignsH` | 105 | 1406 | A | signs_h.png |
| `CP_SignsV` | 103 | 1020 | A | signs_v.png |
| `CP_Steel` | 306 | 156118 | A, B | T_Steel_Color.png, T_Steel_Metalness.png, T_Steel_Normal.png, T_Steel_Roughness.png |
| `CP_TechPanel` | 149 | 5776 | A, B | T_TechPanel_Color.png, T_TechPanel_Metalness.png, T_TechPanel_Normal.png, T_TechPanel_Roughness.png |
| `CP_TowerNight` | 198 | 17344 | B | T_TowerNight_Color.png, T_TowerNight_Metalness.png, T_TowerNight_Normal.png, T_TowerNight_Roughness.png |
| `CP_WIN_COL` | 200 | 35510 | A, B |  |
| `CP_WIN_PNK` | 134 | 10410 | A, B |  |
| `CP_WIN_VIO` | 154 | 13210 | A, B |  |
| `CP_WIN_WRM` | 216 | 50332 | A, B |  |
| `HEX_Palette` | 144 | 25480 | A | palette.png |
