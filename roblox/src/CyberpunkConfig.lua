-- Settings for the cyberpunk city. Distances are in metres of the original map;
-- the scripts convert them to studs by measuring the imported carrier part.
return {
	-- Model/folder that holds the imported city. nil = search all of Workspace.
	CityRoot = nil,

	-- Roblox stores uploaded textures at most 1024x1024; billboard atlas cells use this.
	AtlasPixels = 1024,

	-- Window texture asset. nil = read it from the imported CP_TextureCarrier_Windows part.
	WindowImage = nil,

	Lighting = true, -- night sky, haze, bloom, colour grading
	Windows = false, -- extra glowing window overlay (facades already have windows baked in)
	NeonRings = true, -- neon floor bands and roof crowns around buildings

	MaxRingFootprintMeters = 160, -- skip rings/windows on huge background blocks
	BandSpacingMeters = { 14, 36 },
	BandChance = 0.7, -- share of buildings that get floor bands (all get a crown)
	NeonThicknessMeters = 0.35,

	ScreenPixelsPerMeter = 10,
	ScreenBrightness = 2.5,
	AnimateDistanceStuds = 2500, -- billboards farther than this from the camera pause

	FaultySignChance = 0.18,

	Accents = {
		Color3.fromRGB(0, 217, 255), -- cyan
		Color3.fromRGB(255, 13, 140), -- magenta
		Color3.fromRGB(140, 26, 255), -- purple
		Color3.fromRGB(255, 115, 5), -- amber
		Color3.fromRGB(51, 255, 89), -- acid green
		Color3.fromRGB(255, 20, 26), -- red
	},
}
