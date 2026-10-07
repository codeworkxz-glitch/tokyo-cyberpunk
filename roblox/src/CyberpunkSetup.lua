-- Turns the imported HEX City into a cyberpunk city. Safe to run more than once.
--
-- Runs automatically when the game starts (RunSetup). To bake the result into the
-- place so you can see it while editing, paste this into the Studio command bar:
--   require(workspace.CyberpunkCity.CyberpunkSetup).run()

local Lighting = game:GetService("Lighting")
local CollectionService = game:GetService("CollectionService")

local Config = require(script.Parent.CyberpunkConfig)
local Data = require(script.Parent.BillboardData)

local CARRIER = "CP_TextureCarrier_Windows"
local SIDE_FACES = { Enum.NormalId.Front, Enum.NormalId.Back, Enum.NormalId.Left, Enum.NormalId.Right }

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

local function fxPart(size: Vector3, cf: CFrame, color: Color3?): Part
	local p = Instance.new("Part")
	p.Anchored = true
	p.CanCollide = false
	p.CanTouch = false
	p.CanQuery = false
	p.CastShadow = false
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	p.Size = size
	p.CFrame = cf
	if color then
		p.Material = Enum.Material.Neon
		p.Color = color
	else
		p.Transparency = 1
	end
	return p
end

local function collect(root: Instance)
	local byTag = { bld = {}, street = {}, concrete = {}, led = {}, screen = {}, sign = {}, signlit = {} }
	local carrier
	for _, d in ipairs(root:GetDescendants()) do
		if d:IsA("BasePart") then
			if d.Name == CARRIER then
				carrier = d
			else
				local tag = string.match(d.Name, "__(%a+)$")
				if tag and byTag[tag] then
					d.Anchored = true -- imported parts may come in unanchored
					table.insert(byTag[tag], d)
				end
			end
		end
	end
	return byTag, carrier
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
	Lighting.Ambient = Color3.fromRGB(45, 35, 75)
	Lighting.OutdoorAmbient = Color3.fromRGB(75, 60, 125)
	Lighting.EnvironmentDiffuseScale = 0.4
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
	local atm = Instance.new("Atmosphere")
	atm.Name = "CP_Atmosphere"
	atm.Density = 0.32
	atm.Offset = 0.15
	atm.Color = Color3.fromRGB(110, 80, 170)
	atm.Decay = Color3.fromRGB(40, 20, 90)
	atm.Glare = 0
	atm.Haze = 2.2
	atm.Parent = Lighting
	local bloom = Instance.new("BloomEffect")
	bloom.Name = "CP_Bloom"
	bloom.Intensity = 1.1
	bloom.Size = 28
	bloom.Threshold = 0.85
	bloom.Parent = Lighting
	local cc = Instance.new("ColorCorrectionEffect")
	cc.Name = "CP_Color"
	cc.Contrast = 0.12
	cc.Saturation = 0.25
	cc.TintColor = Color3.fromRGB(235, 228, 255)
	cc.Parent = Lighting
end

local function styleSurfaces(byTag)
	for _, p in ipairs(byTag.bld) do
		local r = Random.new(hash(p.Name))
		p.Material = Enum.Material.Concrete
		p.Color = Color3.fromHSV(r:NextNumber(), r:NextNumber(0.03, 0.12), r:NextNumber(0.16, 0.26))
	end
	for _, p in ipairs(byTag.street) do
		if string.find(p.Name, "Street") then
			p.Material = Enum.Material.Asphalt
			p.Color = Color3.fromRGB(28, 28, 32)
		else
			p.Material = Enum.Material.Concrete
			p.Color = Color3.fromRGB(88, 86, 86)
		end
		p.Reflectance = 0.05 -- a hint of wet street
	end
	for _, p in ipairs(byTag.concrete) do
		local r = Random.new(hash(p.Name))
		p.Material = Enum.Material.Concrete
		p.Color = Color3.fromHSV(0.08, 0.04, r:NextNumber(0.36, 0.5))
	end
	for _, p in ipairs(byTag.led) do
		local r = Random.new(hash(p.Name))
		local accent = Config.Accents[r:NextInteger(1, #Config.Accents)]
		p.Material = Enum.Material.Neon
		p.Color = accent
		p:SetAttribute("Accent", accent)
		CollectionService:AddTag(p, "CP_LED")
	end
	for _, p in ipairs(byTag.signlit) do
		local r = Random.new(hash(p.Name))
		if r:NextNumber() < Config.FaultySignChance then
			CollectionService:AddTag(p, "CP_FaultySign")
		end
	end
end

local function ring(p: BasePart, y: number, thick: number, color: Color3, tag: string?, folder: Instance)
	local s = p.Size
	local hx, hz = s.X / 2 + thick / 2, s.Z / 2 + thick / 2
	local segments = {
		{ Vector3.new(0, y, hz), Vector3.new(s.X + thick * 2, thick, thick) },
		{ Vector3.new(0, y, -hz), Vector3.new(s.X + thick * 2, thick, thick) },
		{ Vector3.new(hx, y, 0), Vector3.new(thick, thick, s.Z) },
		{ Vector3.new(-hx, y, 0), Vector3.new(thick, thick, s.Z) },
	}
	for _, seg in ipairs(segments) do
		local n = fxPart(seg[2], p.CFrame * CFrame.new(seg[1]), color)
		n.Name = "NeonRing"
		if tag then
			n:SetAttribute("Accent", color)
			n:SetAttribute("Phase", (hash(p.Name) % 1000) / 1000 * 2 * math.pi)
			CollectionService:AddTag(n, tag)
		end
		n.Parent = folder
	end
end

local function decorateBuildings(buildings, windowImage: string?, M: number, folder: Instance)
	local thick = Config.NeonThicknessMeters * M
	local cellPx = 16
	for _, p in ipairs(buildings) do
		for _, c in ipairs(p:GetChildren()) do
			if c.Name == "CP_Windows" then
				c:Destroy()
			end
		end
		local s = p.Size
		if math.max(s.X, s.Z) <= Config.MaxRingFootprintMeters * M then
			local r = Random.new(hash(p.Name))
			local accent = Config.Accents[r:NextInteger(1, #Config.Accents)]

			if Config.NeonRings then
				ring(p, s.Y / 2 - thick * 1.5, thick * 1.5, accent, "CP_Crown", folder)
				if r:NextNumber() < Config.BandChance then
					local spacing = r:NextNumber(Config.BandSpacingMeters[1], Config.BandSpacingMeters[2]) * M
					local y = spacing
					while y < s.Y - spacing * 0.5 do
						ring(p, y - s.Y / 2, thick, accent, nil, folder)
						y += spacing
					end
				end
			end

			if Config.Windows and windowImage then
				-- texture tile = 4 windows x 4 floors, one window cell = 1.8 m x 3.6 m
				local pps = cellPx / (1.8 * M)
				for _, face in ipairs(SIDE_FACES) do
					local gui = Instance.new("SurfaceGui")
					gui.Name = "CP_Windows"
					gui.Face = face
					gui.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
					gui.PixelsPerStud = pps
					gui.LightInfluence = 0
					gui.Brightness = 1.3
					gui.ClipsDescendants = true
					local img = Instance.new("ImageLabel")
					img.BackgroundTransparency = 1
					img.Image = windowImage
					img.ScaleType = Enum.ScaleType.Tile
					img.TileSize = UDim2.fromOffset(cellPx * 4, cellPx * 8)
					img.Size = UDim2.new(1, cellPx * 4, 1, cellPx * 8)
					img.Position = UDim2.fromOffset(-r:NextInteger(0, 3) * cellPx, -r:NextInteger(0, 3) * cellPx * 2)
					img.Parent = gui
					gui.Parent = p
				end
			end
		end
	end
end

local function buildScreens(screens, M: number, folder: Instance): number
	local S = Config.AtlasPixels
	local made = 0
	for _, p in ipairs(screens) do
		local d = Data.screens[p.Name]
		local image = textureOf(p)
		if d and image then
			local dataSize = Vector3.new(d.size[1], d.size[2], d.size[3])
			local k = if dataSize.Magnitude > 0 then p.Size.Magnitude / dataSize.Magnitude else M
			local r = Random.new(hash(p.Name))
			local phases = {}
			for gi = 1, #d.groups do
				phases[gi] = r:NextNumber()
			end
			for _, pd in ipairs(d.panels) do
				local g = d.groups[pd.g]
				local n = Vector3.new(pd.n[1], pd.n[2], pd.n[3]).Unit
				local right = Vector3.new(pd.r[1], pd.r[2], pd.r[3]).Unit
				local up = n:Cross(right)
				local pos = p.Position + Vector3.new(pd.o[1], pd.o[2], pd.o[3]) * k + n * 0.06
				local panel = fxPart(Vector3.new(pd.w * k, pd.h * k, 0.05), CFrame.fromMatrix(pos, n:Cross(up), up, -n))
				panel.Name = "CP_Screen"

				local fw, fh = pd.f[2] - pd.f[1], pd.f[4] - pd.f[3]
				panel:SetAttribute("FX", pd.f[1])
				panel:SetAttribute("FY", pd.f[3])
				panel:SetAttribute("FW", fw)
				panel:SetAttribute("FH", fh)
				panel:SetAttribute("Speed", g.s)
				panel:SetAttribute("Axis", g.ax)
				panel:SetAttribute("Phase", phases[pd.g])

				local gui = Instance.new("SurfaceGui")
				gui.Face = Enum.NormalId.Front
				gui.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
				gui.PixelsPerStud = math.clamp(Config.ScreenPixelsPerMeter / M, 0.5, 50)
				gui.LightInfluence = 0
				gui.Brightness = Config.ScreenBrightness
				local clip = Instance.new("Frame")
				clip.Name = "Clip"
				clip.Size = UDim2.fromScale(1, 1)
				clip.BackgroundColor3 = Color3.new(0, 0, 0)
				clip.BorderSizePixel = 0
				clip.ClipsDescendants = true
				clip.Parent = gui
				for i, name in ipairs({ "A", "B" }) do
					local img = Instance.new("ImageLabel")
					img.Name = name
					img.BackgroundTransparency = 1
					img.Image = image
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
				local scan = Instance.new("Frame")
				scan.Name = "Scan"
				scan.Size = UDim2.fromScale(1, 0.04 / fh)
				scan.BackgroundColor3 = Color3.new(1, 1, 1)
				scan.BackgroundTransparency = 0.8
				scan.BorderSizePixel = 0
				scan.ZIndex = 2
				scan.Parent = clip
				gui.Parent = panel
				CollectionService:AddTag(panel, "CP_Screen")
				panel.Parent = folder
				made += 1
			end
		end
	end
	return made
end

function Setup.run()
	local root = Config.CityRoot or workspace
	local byTag, carrier = collect(root)
	local M = studsPerMeter(carrier, byTag.screen)

	local windowImage = Config.WindowImage
	if carrier then
		carrier.Transparency = 1
		carrier.CanCollide = false
		carrier.Anchored = true
		windowImage = windowImage or textureOf(carrier)
	end
	if Config.Windows and not windowImage then
		warn("[Cyberpunk] window texture not found; set CyberpunkConfig.WindowImage")
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
	styleSurfaces(byTag)
	decorateBuildings(byTag.bld, windowImage, M, fx)
	local screens = buildScreens(byTag.screen, M, fx)

	fx.Parent = workspace
	workspace:SetAttribute("CyberpunkStudsPerMeter", M)
	workspace:SetAttribute("CyberpunkReady", true)
	print(
		string.format(
			"[Cyberpunk] %d buildings, %d streets, %d props, %d LED strips, %d billboard screens (%.3f studs/m)",
			#byTag.bld,
			#byTag.street,
			#byTag.concrete,
			#byTag.led,
			screens,
			M
		)
	)
end

return Setup
