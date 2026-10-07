-- Settings for the cyberpunk city. Distances are in metres of the original map;
-- the scripts convert them to studs by measuring the imported carrier part.
return {
	-- Model/folder that holds the imported city. nil = search all of Workspace.
	CityRoot = nil,

	-- Roblox stores uploaded textures at most 1024x1024; atlas cells use this.
	AtlasPixels = 1024,

	Lighting = true, -- night sky, blue-purple haze, bloom, colour grading
	WetStreetReflectance = 0.15,

	-- Lit windows (Neon panes on the facades)
	WindowWarm = Color3.fromRGB(255, 205, 150),
	WindowGlowTransparency = 0.2,

	-- Glowing overlays on screens, holograms and signs
	ScreenPixelsPerMeter = 10,
	ScreenBrightness = 2.5,
	HoloBrightness = 3,
	HoloTransparency = 0.15,
	SignBrightness = 1.8,
	FaultySignChance = 0.15,
	AnimateDistanceStuds = 2500, -- screens farther than this from the camera pause

	-- Flying cars with light trails (client side)
	FlyingCars = 28,
	FlyingCarSpeed = { 25, 45 }, -- metres per second
	FlyingCarAltitude = { 18, 80 }, -- metres above the lowest building base

	Accents = {
		Color3.fromRGB(0, 217, 255), -- cyan
		Color3.fromRGB(255, 13, 140), -- magenta
		Color3.fromRGB(140, 26, 255), -- purple
		Color3.fromRGB(255, 115, 5), -- amber
		Color3.fromRGB(51, 255, 89), -- acid green
		Color3.fromRGB(255, 20, 26), -- red
	},
}
