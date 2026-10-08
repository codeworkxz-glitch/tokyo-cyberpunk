-- HEX! Cyberpunk City v2 - settings. Edit freely; re-run CyberpunkSetup.run() after changes.
return {
	-- Lighting --------------------------------------------------------------------------
	ApplyLighting = true, -- night sky, blue/purple haze, bloom, colour grading
	ClockTime = 0.2,
	Ambient = Color3.fromRGB(58, 56, 88),
	OutdoorAmbient = Color3.fromRGB(92, 88, 140), -- keeps the courts readable at night
	CourtFloodBrightness = 2.4, -- SpotLights on the plaza light masts (gameplay visibility)

	-- Neon / lit materials (part name suffix -> colour). Neon glows at full colour,
	-- so the lit-window colours are deliberately darker than the neon accents.
	NeonColors = {
		NEON_CYN = Color3.fromRGB(0, 230, 255),
		NEON_MAG = Color3.fromRGB(255, 25, 175),
		NEON_VIO = Color3.fromRGB(150, 45, 255),
		NEON_BLU = Color3.fromRGB(30, 95, 255),
		NEON_RED = Color3.fromRGB(255, 32, 45),
		NEON_AMB = Color3.fromRGB(255, 150, 25),
		NEON_WHT = Color3.fromRGB(200, 215, 255),
		WIN_WRM = Color3.fromRGB(150, 110, 70),
		WIN_COL = Color3.fromRGB(80, 115, 160),
		WIN_PNK = Color3.fromRGB(160, 70, 125),
		WIN_VIO = Color3.fromRGB(105, 80, 165),
		SHOP_LIT = Color3.fromRGB(175, 160, 140),
	},
	WindowTransparency = 0.05,

	-- Fallback look when a textured part has no SurfaceAppearance / TextureID
	-- (e.g. the importer did not pick up the PNGs and no asset ids are filled in below).
	Fallback = {
		GLS = { Enum.Material.Glass, Color3.fromRGB(28, 34, 58), 0.15 },
		RIB = { Enum.Material.Glass, Color3.fromRGB(40, 44, 62), 0.1 },
		PNL = { Enum.Material.Metal, Color3.fromRGB(70, 74, 88), 0 },
		CON = { Enum.Material.Concrete, Color3.fromRGB(86, 86, 96), 0 },
		TEC = { Enum.Material.Metal, Color3.fromRGB(56, 60, 78), 0 },
		MEC = { Enum.Material.DiamondPlate, Color3.fromRGB(78, 84, 88), 0 },
		ROF = { Enum.Material.Slate, Color3.fromRGB(60, 62, 70), 0 },
		STL = { Enum.Material.Metal, Color3.fromRGB(64, 68, 80), 0 },
		LOU = { Enum.Material.Metal, Color3.fromRGB(70, 76, 92), 0 },
		TWN = { Enum.Material.Glass, Color3.fromRGB(30, 34, 56), 0.1 },
	},

	-- Optional: asset ids after uploading export/textures (Asset Manager > Bulk Import).
	-- Fill these only if the 3D Importer did not create SurfaceAppearances for you.
	-- Example: T_GlassCurtain = { Color = "rbxassetid://123", Normal = "...", Roughness = "...", Metalness = "..." },
	SurfaceTextures = {},
	-- Optional: AD_* image ids, only needed if a screen MeshPart lost its texture on import.
	AdImages = {},

	-- Screens ---------------------------------------------------------------------------
	ScreenBrightness = 2.2, -- SurfaceGui brightness (LightInfluence 0 = self-lit)
	HoloTransparency = 0.18,
	ScreenSurfaceLights = true, -- coloured spill from big screens
	-- Videos: ["SCR_A_N_17_LMStacked_04"] = "rbxassetid://<video id>"
	Videos = {},
	-- Screens whose ad rotates between artworks of the same aspect ratio (needs the ids of
	-- the other ads: they are collected automatically from all imported screens).
	RotateAll = true, -- every screen rotates; set false to rotate only the kinds below
	RotateKinds = { sky = true, rooftop = true, mg_facade = true, skyline = true, mega = true, giant = true },
	RotateSeconds = { 6, 10 }, -- each screen shows an ad for 6-10 s (random per screen)
	FadeSeconds = 0.35,

	-- Lights ------------------------------------------------------------------------------
	MaxLights = 450,
	ShopLights = true,
	Beacons = true,

	-- Collisions: midground / skyline (file B) cannot be reached by players.
	CollideFileB = false,
}
