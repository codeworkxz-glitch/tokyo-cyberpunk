-- HEX! City v3 - settings. Edit freely, then run require(workspace.HEXCityV3.HEXCitySetup).run() again.
return {
	-- Lighting ----------------------------------------------------------------------------
	-- "Night" (city lights, screens and signs glow), "Dusk" (blue hour) or "Keep" (leave your Lighting alone)
	TimeOfDay = "Night",
	CourtFloodBrightness = 2.2,

	-- Lit parts of the new detail (file B): part name suffix -> Neon colour
	NeonColors = {
		LAMP = Color3.fromRGB(255, 236, 205), -- street lamp globes, gate lamps, kerb bollard rings
		BULB = Color3.fromRGB(255, 205, 140), -- string lights over the side streets
		SIG_RED = Color3.fromRGB(255, 40, 40), -- antenna beacons, pedestrian signals
		SIG_GRN = Color3.fromRGB(40, 255, 150),
	},

	-- Fallback look for textured parts of file B if the importer did not keep the PNG
	Fallback = {
		PNL = { Enum.Material.Metal, Color3.fromRGB(196, 198, 204) },
		CON = { Enum.Material.Concrete, Color3.fromRGB(150, 150, 152) },
		TEC = { Enum.Material.Metal, Color3.fromRGB(90, 94, 104) },
		MEC = { Enum.Material.DiamondPlate, Color3.fromRGB(170, 172, 176) },
		STL = { Enum.Material.Metal, Color3.fromRGB(70, 74, 82) },
	},

	-- Screens -----------------------------------------------------------------------------
	ScreenBrightness = 1.8, -- SurfaceGui brightness (LightInfluence 0 = self-lit)
	ScanLine = true,
	RotateAll = true, -- every screen rotates between the ads of its shape
	RotateSeconds = { 6, 10 }, -- each ad stays 6-10 s (random per screen)
	FadeSeconds = 0.35,
	-- Optional: AD_* image ids, only needed if a screen MeshPart lost its texture on import.
	AdImages = {},
	-- Optional videos: ["SCR_Billboard_..."] = "rbxassetid://<video id>"
	Videos = {},

	-- Lit signs: a self-lit copy of each sign face so the original signs glow at night
	SignGlow = true,
	SignBrightness = 1.15,
	-- Optional ids if a sign atlas lost its texture: { H = "rbxassetid://..", V = "rbxassetid://.." }
	SignAtlas = {},

	-- Lights --------------------------------------------------------------------------------
	MaxLights = 600, -- street lamps first, then gates / vending machines, then screen spill

	-- File B is decoration merged into large meshes; with collisions on, Roblox's approximate
	-- collision hulls of those meshes could block streets, so it is non-collidable by default.
	CollideDetail = false,
}
