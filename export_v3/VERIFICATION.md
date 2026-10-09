# HEX! City v3 - verification (re-import of the exported FBX files)

- [x] file A has the same 4097 mesh objects as the original
- [x] file A geometry identical to the original (vertex/face counts and bounds) - 0 differ
- [x] file B re-imports: 2125 mesh objects
- [x] nothing new inside the plaza / courts / practice area (|x|<484, |y|<399, below 60 studs)
- [x] HEX_City_v3_A.fbx is 18.30 MB (< 20 MB)
- [x] HEX_City_v3_B.fbx is 8.68 MB (< 20 MB)
- [x] HEX_City_v3_A.fbx: texture paths are bare file names (4 referenced)
- [x] HEX_City_v3_A.fbx: every referenced PNG is in textures/
- [x] HEX_City_v3_B.fbx: texture paths are bare file names (67 referenced)
- [x] HEX_City_v3_B.fbx: every referenced PNG is in textures/
- [x] all 1214 screens in CityData exist as meshes
- [x] all 980 glow signs in CityData exist as meshes
- [x] every screen's ad PNG exists
- [x] 35 different ads in use, all rotating (RotateAll)

All checks passed.
