-- Turns the imported HEX City into a neon cyberpunk city. Safe to run more than once.
--
-- Runs automatically when the game starts (RunSetup). To bake the result into the
-- place so you can see it while editing, paste this into the Studio command bar:
--   require(workspace.CyberpunkCity.CyberpunkSetup).run()
--
-- Imported parts are recognised by their name suffix (written by export_roblox.py):
--   __bld __roof __street __concrete __paint __rig   textured surfaces (left as imported)
--   __neon (_N<k>)  __led  __glow (_G<k>)  __beacon     become Neon
--   __screen __holo __blade __signlit                  get a glowing SurfaceGui overlay

local Lighting = game:GetService("Lighting")
local CollectionService = game:GetService("CollectionService")

local Config = require(script.Parent.CyberpunkConfig)
local Data = require(script.Parent.BillboardData)

local CARRIER = "CP_TextureCarrier_Windows"
local TAGS = {
	"bld", "roof", "street", "concrete", "paint", "rig", "neon", "led", "glow", "beacon",
	"screen", "holo", "blade", "sign", "signlit",
}

local Setup = {}

local function hash(s: string): number
	local h = 5381
	for i = 1, #s do
		h = (h * 33 + string.byte(s, i)) % 2147483647
	end
	return h
end

local function textureOf(part: BasePart): string?
	if part:IsA("MeshPart") and part.TextureID ~= "" then
		return part.TextureID
	end
	local sa = part:FindFirstChildOfClass("SurfaceAppearance")
	if sa then
		local ok, map = pcall(function()
			return sa.ColorMap
		end)
		if ok and map ~= "" then
			return map
		end
	end
	return nil
end

local function makeNeon(p: BasePart, color: Color3)
	if p:IsA("MeshPart") then
		pcall(function()
			p.TextureID = "" -- Neon glows with the part colour
		end)
	end
	local sa = p:FindFirstChildOfClass("SurfaceAppearance")
	if sa then
		sa:Destroy()
	end
	p.Material = Enum.Material.Neon
	p.Color = color
	p.CastShadow = false
	p:SetAttribute("Accent", color)
end

local function collect(root: Instance)
	local byTag = {}
	for _, t in ipairs(TAGS) do
		byTag[t] = {}
	end
	local carrier
	local lo, hi = Vector3.one * math.huge, -Vector3.one * math.huge
	for _, d in ipairs(root:GetDescendants()) do
		if d:IsA("BasePart") then
			if d.Name == CARRIER then
				carrier = d
			else
				local tag = string.match(d.Name, "__(%a+)$")
				if tag and byTag[tag] then
					d.Anchored = true -- imported parts may come in unanchored
					table.insert(byTag[tag], d)
					if tag == "bld" then
						lo = lo:Min(d.Position - d.Size / 2)
						hi = hi:Max(d.Position + d.Size / 2)
					end
				end
			end
		end
	end
	return byTag, carrier, lo, hi
end

local function studsPerMeter(carrier: BasePart?, screens: { BasePart }): number
	if carrier then
		return math.max(carrier.Size.X, carrier.Size.Z) / Data.carrierMeters
	end
	for _, p in ipairs(screens) do
		local d = Data.screens[p.Name]
		if d then
			return p.Size.Magnitude / Vector3.new(d.size[1], d.size[2], d.size[3]).Magnitude
		end
	end
	return 1
end

local function setupLighting()
	Lighting.ClockTime = 0
	Lighting.Brightness = 1
	Lighting.Ambient = Color3.fromRGB(30, 32, 60)
	Lighting.OutdoorAmbient = Color3.fromRGB(55, 60, 110)
	Lighting.EnvironmentDiffuseScale = 0.35
	Lighting.EnvironmentSpecularScale = 1
	Lighting.GlobalShadows = true
	pcall(function()
		Lighting.Technology = Enum.Technology.Future -- only settable from Studio / command bar
	end)
	for _, c in ipairs(Lighting:GetChildren()) do
		if c:IsA("Atmosphere") or c.Name == "CP_Bloom" or c.Name == "CP_Color" then
			c:Destroy()
		end
	end
	local sky = Lighting:FindFirstChildOfClass("Sky")
	if sky then
		sky.CelestialBodiesShown = false
		sky.StarCount = 300
	end
	local atm = Instance.new("Atmosphere")
	atm.Name = "CP_Atmosphere"
	atm.Density = 0.38
	atm.Offset = 0.1
	atm.Color = Color3.fromRGB(80, 95, 160)
	atm.Decay = Color3.fromRGB(70, 40, 120)
	atm.Glare = 0
	atm.Haze = 2.4
	atm.Parent = Lighting
	local bloom = Instance.new("BloomEffect")
	bloom.Name = "CP_Bloom"
	bloom.Intensity = 1.3
	bloom.Size = 30
	bloom.Threshold = 0.8
	bloom.Parent = Lighting
	local cc = Instance.new("ColorCorrectionEffect")
	cc.Name = "CP_Color"
	cc.Contrast = 0.15
	cc.Saturation = 0.3
	cc.TintColor = Color3.fromRGB(225, 230, 255)
	cc.Parent = Lighting
end

local function styleParts(byTag)
	for _, p in ipairs(byTag.street) do
		if string.find(p.Name, "Street") then
			p.Reflectance = Config.WetStreetReflectance
		end
		if not textureOf(p) then
			p.Material = Enum.Material.Asphalt
			p.Color = Color3.fromRGB(28, 28, 32)
		end
	end
	for _, list in ipairs({ byTag.bld, byTag.roof, byTag.concrete, byTag.rig }) do
		for _, p in ipairs(list) do
			if not textureOf(p) then -- fallback if the importer dropped the texture
				local r = Random.new(hash(p.Name))
				p.Material = Enum.Material.Concrete
				p.Color = Color3.fromHSV(0.62, 0.08, r:NextNumber(0.14, 0.24))
			end
		end
	end

	for _, p in ipairs(byTag.neon) do
		local k = tonumber(string.match(p.Name, "_N(%d+)__neon")) or 1
		makeNeon(p, Config.Accents[math.clamp(k, 1, #Config.Accents)])
		p:SetAttribute("Phase", (hash(p.Name) % 1000) / 1000 * 2 * math.pi)
		CollectionService:AddTag(p, "CP_Neon")
	end
	for _, p in ipairs(byTag.led) do
		local r = Random.new(hash(p.Name))
		makeNeon(p, Config.Accents[r:NextInteger(1, #Config.Accents)])
		CollectionService:AddTag(p, "CP_LED")
	end
	for _, p in ipairs(byTag.glow) do
		local k = tonumber(string.match(p.Name, "_G(%d+)W")) or 0
		local color = Config.WindowWarm
		if k > 0 then
			color = Config.Accents[math.clamp(k, 1, #Config.Accents)]:Lerp(Color3.new(1, 1, 1), 0.45)
		end
		makeNeon(p, color)
		p.Transparency = Config.WindowGlowTransparency
		p.CanCollide = false
		p.CanQuery = false
	end
	for _, p in ipairs(byTag.beacon) do
		makeNeon(p, Color3.fromRGB(255, 20, 20))
		p:SetAttribute("Phase", (hash(p.Name) % 1000) / 1000)
		CollectionService:AddTag(p, "CP_Beacon")
	end
end

local KIND = {
	screen = { brightness = "ScreenBrightness", scroll = true, holo = false },
	holo = { brightness = "HoloBrightness", scroll = true, holo = true },
	sign = { brightness = "SignBrightness", scroll = false, holo = false },
}

local function overlay(p: BasePart, d, M: number, folder: Instance): number
	local image = textureOf(p)
	if not image then
		return 0
	end
	local style = KIND[d.kind] or KIND.screen
	local S = Config.AtlasPixels
	local dataSize = Vector3.new(d.size[1], d.size[2], d.size[3])
	local k = if dataSize.Magnitude > 0 then p.Size.Magnitude / dataSize.Magnitude else M
	local r = Random.new(hash(p.Name))
	local faulty = d.kind == "sign" and r:NextNumber() < Config.FaultySignChance
	local phases = {}
	for gi = 1, #d.groups do
		phases[gi] = r:NextNumber()
	end
	local made = 0
	for _, pd in ipairs(d.panels) do
		local g = d.groups[pd.g]
		local n = Vector3.new(pd.n[1], pd.n[2], pd.n[3]).Unit
		local right = Vector3.new(pd.r[1], pd.r[2], pd.r[3]).Unit
		local up = n:Cross(right)
		local pos = p.Position + Vector3.new(pd.o[1], pd.o[2], pd.o[3]) * k + n * 0.06
		local panel = Instance.new("Part")
		panel.Name = "CP_Overlay"
		panel.Anchored = true
		panel.CanCollide = false
		panel.CanTouch = false
		panel.CanQuery = false
		panel.CastShadow = false
		panel.Transparency = 1
		panel.Size = Vector3.new(pd.w * k, pd.h * k, 0.05)
		panel.CFrame = CFrame.fromMatrix(pos, n:Cross(up), up, -n)

		local fw, fh = pd.f[2] - pd.f[1], pd.f[4] - pd.f[3]
		panel:SetAttribute("FX", pd.f[1])
		panel:SetAttribute("FY", pd.f[3])
		panel:SetAttribute("FW", fw)
		panel:SetAttribute("FH", fh)
		panel:SetAttribute("Speed", g.s)
		panel:SetAttribute("Axis", g.ax)
		panel:SetAttribute("Phase", phases[pd.g])
		panel:SetAttribute("Holo", style.holo)
		panel:SetAttribute("BaseBrightness", Config[style.brightness])

		local gui = Instance.new("SurfaceGui")
		gui.Face = Enum.NormalId.Front
		gui.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
		gui.PixelsPerStud = math.clamp(Config.ScreenPixelsPerMeter / M, 0.5, 50)
		gui.LightInfluence = 0
		gui.Brightness = Config[style.brightness]
		local clip = Instance.new("Frame")
		clip.Name = "Clip"
		clip.Size = UDim2.fromScale(1, 1)
		clip.BackgroundColor3 = Color3.new(0, 0, 0)
		clip.BackgroundTransparency = if style.holo then 1 else 0
		clip.BorderSizePixel = 0
		clip.ClipsDescendants = true
		clip.Parent = gui
		for i, name in ipairs(if style.scroll then { "A", "B" } else { "A" }) do
			local img = Instance.new("ImageLabel")
			img.Name = name
			img.BackgroundTransparency = 1
			img.Image = image
			img.ImageTransparency = if style.holo then Config.HoloTransparency else 0
			img.ImageRectOffset = Vector2.new(g.uv[1] * S, (1 - g.uv[2] - g.uv[4]) * S)
			img.ImageRectSize = Vector2.new(g.uv[3] * S, g.uv[4] * S)
			img.Size = UDim2.fromScale(1 / fw, 1 / fh)
			local shift = i - 1
			if g.ax == "X" then
				img.Position = UDim2.fromScale((shift - pd.f[1]) / fw, -pd.f[3] / fh)
			else
				img.Position = UDim2.fromScale(-pd.f[1] / fw, (shift - pd.f[3]) / fh)
			end
			img.Parent = clip
		end
		if style.scroll then
			local scan = Instance.new("Frame")
			scan.Name = "Scan"
			scan.Size = UDim2.fromScale(1, 0.04 / fh)
			scan.BackgroundColor3 = if style.holo then Color3.fromRGB(120, 230, 255) else Color3.new(1, 1, 1)
			scan.BackgroundTransparency = if style.holo then 0.6 else 0.8
			scan.BorderSizePixel = 0
			scan.ZIndex = 3
			scan.Parent = clip
		end
		if style.holo then -- cyan hologram tint + scanline texture
			local tint = Instance.new("Frame")
			tint.Size = UDim2.fromScale(1, 1)
			tint.BackgroundColor3 = Color3.fromRGB(60, 200, 255)
			tint.BackgroundTransparency = 0.88
			tint.BorderSizePixel = 0
			tint.ZIndex = 2
			tint.Parent = clip
			local lines = Instance.new("UIGradient")
			lines.Rotation = 90
			lines.Transparency = NumberSequence.new({
				NumberSequenceKeypoint.new(0, 0.6),
				NumberSequenceKeypoint.new(0.5, 0.95),
				NumberSequenceKeypoint.new(1, 0.6),
			})
			lines.Parent = tint
		end
		gui.Parent = panel
		if style.scroll then
			CollectionService:AddTag(panel, "CP_Screen")
		elseif faulty then
			CollectionService:AddTag(panel, "CP_FaultySign")
		end
		panel.Parent = folder
		made += 1
	end
	return made
end

function Setup.run()
	local root = Config.CityRoot or workspace
	local byTag, carrier, lo, hi = collect(root)
	local M = studsPerMeter(carrier, byTag.screen)
	if carrier then
		carrier.Transparency = 1
		carrier.CanCollide = false
		carrier.Anchored = true
	end

	local old = workspace:FindFirstChild("CyberpunkFX")
	if old then
		old:Destroy()
	end
	local fx = Instance.new("Folder")
	fx.Name = "CyberpunkFX"

	if Config.Lighting then
		setupLighting()
	end
	styleParts(byTag)

	local overlays = 0
	for _, tag in ipairs({ "screen", "holo", "blade", "signlit" }) do
		for _, p in ipairs(byTag[tag]) do
			local d = Data.screens[p.Name]
			if d then
				overlays += overlay(p, d, M, fx)
			end
		end
	end

	fx.Parent = workspace
	workspace:SetAttribute("CyberpunkStudsPerMeter", M)
	if lo.X < math.huge then
		workspace:SetAttribute("CyberpunkCityMin", lo)
		workspace:SetAttribute("CyberpunkCityMax", hi)
	end
	workspace:SetAttribute("CyberpunkReady", true)
	print(
		string.format(
			"[Cyberpunk] %d buildings, %d neon frames, %d window glow meshes, %d holograms, %d blade signs, %d glowing overlays (%.3f studs/m)",
			#byTag.bld,
			#byTag.neon,
			#byTag.glow,
			#byTag.holo,
			#byTag.blade,
			overlays,
			M
		)
	)
end

return Setup
