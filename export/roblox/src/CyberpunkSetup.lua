-- HEX! Cyberpunk City v2 - configures the two imported FBX models in Roblox Studio.
--
-- Run once from the Studio command bar (bakes the result into the place, enables Future lighting):
--     require(workspace.CyberpunkCityV2.CyberpunkSetup).run()
-- RunSetup (server Script) also runs it at game start if it has not been baked yet.
--
-- What it does (all driven by part names written by blender/cp2_build.py):
--   1. finds HEX_ALIGN_A / HEX_ALIGN_B and moves model B so both files share one origin;
--      measures the marker size to detect any import rescale.
--   2. `__NEON_*`, `__WIN_*`, `__SHOP_LIT`  -> Material.Neon + colour (self-lit, no texture).
--      textured keys (`__GLS`, `__PNL`, ...) keep their SurfaceAppearance; if the importer
--      dropped it, ids from Config.SurfaceTextures or a Roblox material fallback are used.
--   3. every `SCR_*` screen gets a self-lit SurfaceGui (ImageLabel, or VideoFrame from
--      Config.Videos) on an invisible anchor part, one per flat panel (curved screens are
--      split into panels showing their slice of the artwork). Tagged "HEX_Screen".
--   4. PointLights / SpotLights / SurfaceLights from CityData (court floods, shops, beacons).
--   5. night Lighting: Atmosphere, Bloom, ColorCorrection.

local CollectionService = game:GetService("CollectionService")
local Lighting = game:GetService("Lighting")

local Config = require(script.Parent.CyberpunkConfig)
local Data = require(script.Parent.CityData)

local Setup = {}

local TEXKEY = {
	GLS = "T_GlassCurtain", RIB = "T_GlassRibbon", PNL = "T_PanelMetal", CON = "T_ConcreteDark",
	TEC = "T_TechPanel", MEC = "T_Mechanical", ROF = "T_RoofDeck", STL = "T_Steel", LOU = "T_Louver",
	TWN = "T_TowerNight",
}

local function v3(t): Vector3
	return Vector3.new(t[1], t[2], t[3])
end

local function keyOf(name: string): string?
	-- "A_N_05_Zakkyo__GLS_2" -> "GLS", "..__NEON_CYN" -> "NEON_CYN"
	local k = string.match(name, "__([%u_]+)$")
	if not k then
		return nil
	end
	k = string.gsub(k, "_%d+$", "")
	return k
end

local function findPart(pattern: string): BasePart?
	for _, d in ipairs(workspace:GetDescendants()) do
		if d:IsA("BasePart") and string.find(d.Name, pattern, 1, true) then
			return d
		end
	end
	return nil
end

local function topModel(inst: Instance): Instance
	local m = inst
	while m.Parent and m.Parent ~= workspace do
		m = m.Parent :: Instance
	end
	return m
end

local function textureOf(p: BasePart): string?
	if p:IsA("MeshPart") and p.TextureID ~= "" then
		return p.TextureID
	end
	local sa = p:FindFirstChildOfClass("SurfaceAppearance")
	if sa then
		local ok, map = pcall(function()
			return (sa :: any).ColorMap
		end)
		if ok and map and map ~= "" then
			return map
		end
	end
	return nil
end

-- 1. alignment -------------------------------------------------------------------------
local function align()
	local mA = findPart("HEX_ALIGN_A")
	local mB = findPart("HEX_ALIGN_B")
	if not mA then
		warn("[HEX] HEX_ALIGN_A not found - import HEX_Cyberpunk_City_A.fbx first")
		return nil
	end
	local k = mA.Size.Y / Data.markerSize
	if mB then
		local modelB = topModel(mB)
		local delta = mA.Position - mB.Position
		if delta.Magnitude > 0.01 and modelB:IsA("PVInstance") then
			(modelB :: any):PivotTo((modelB :: any):GetPivot() + delta)
			print(string.format("[HEX] moved city B by %.2f studs to share city A's origin", delta.Magnitude))
		end
		if math.abs(mB.Size.Y / Data.markerSize - k) > 0.01 then
			warn("[HEX] A and B were imported with different scales - re-import both with the same settings")
		end
	else
		warn("[HEX] HEX_ALIGN_B not found - import HEX_Cyberpunk_City_B.fbx for the midground and skyline")
	end
	if math.abs(k - 1) > 0.01 then
		warn(string.format("[HEX] the import was rescaled x%.3f (expected 1 stud = 1 unit); data positions follow it", k))
	end
	for _, m in ipairs({ mA, mB }) do
		if m then
			m.Transparency = 1
			m.CanCollide = false
			m.CanQuery = false
			m.CanTouch = false
		end
	end
	local origin = mA.Position
	local expected = v3(Data.markerA)
	return function(p: Vector3): Vector3
		return origin + (p - expected) * k
	end, k, topModel(mA), mB and topModel(mB) or nil
end

-- 2. materials --------------------------------------------------------------------------
local function styleParts(root: Instance, isB: boolean)
	local counts = { neon = 0, textured = 0, fallback = 0 }
	for _, d in ipairs(root:GetDescendants()) do
		if not d:IsA("BasePart") then
			continue
		end
		local p = d :: BasePart
		p.Anchored = true
		local key = keyOf(p.Name)
		if isB and not Config.CollideFileB then
			p.CanCollide = false
		end
		if key == nil then
			continue
		end
		local neon = Config.NeonColors[key]
		if neon then
			if p:IsA("MeshPart") then
				pcall(function()
					(p :: MeshPart).TextureID = ""
				end)
			end
			local sa = p:FindFirstChildOfClass("SurfaceAppearance")
			if sa then
				sa:Destroy()
			end
			p.Material = Enum.Material.Neon
			p.Color = neon
			p.CastShadow = false
			p.CanCollide = false
			p.CanTouch = false
			p.CanQuery = false
			if string.sub(key, 1, 4) == "WIN_" then
				p.Transparency = Config.WindowTransparency
			end
			if string.sub(key, 1, 5) == "NEON_" then
				CollectionService:AddTag(p, "HEX_Neon")
			end
			counts.neon += 1
		elseif key == "SGH" or key == "SGV" then
			p.CanCollide = false
			p.CastShadow = false
			p.Material = Enum.Material.SmoothPlastic
		elseif TEXKEY[key] then
			local hasTex = textureOf(p) ~= nil
			local ids = Config.SurfaceTextures[TEXKEY[key]]
			if not hasTex and ids and p:IsA("MeshPart") then
				local ok = pcall(function()
					local sa = Instance.new("SurfaceAppearance")
					sa.ColorMap = ids.Color
					sa.NormalMap = ids.Normal
					sa.RoughnessMap = ids.Roughness
					sa.MetalnessMap = ids.Metalness
					sa.Parent = p
				end)
				hasTex = ok
			end
			if hasTex then
				counts.textured += 1
			else
				local fb = Config.Fallback[key]
				if fb then
					p.Material = fb[1]
					p.Color = fb[2]
					p.Reflectance = fb[3]
				end
				counts.fallback += 1
			end
			if key == "MEC" or key == "STL" then
				p.CanCollide = p.CanCollide and p.Size.Magnitude > 6
			end
		end
	end
	return counts
end

-- 3. screens ----------------------------------------------------------------------------
local function makeScreens(T: (Vector3) -> Vector3, k: number, folder: Folder)
	local parts: { [string]: BasePart } = {}
	for _, d in ipairs(workspace:GetDescendants()) do
		if d:IsA("BasePart") and string.sub(d.Name, 1, 4) == "SCR_" then
			parts[d.Name] = d
		end
	end
	-- image id per ad (from any screen showing it, or Config.AdImages)
	local adImage: { [string]: string } = {}
	for name, rec in pairs(Data.screens) do
		local p = parts[name]
		local img = p and textureOf(p)
		if img then
			adImage[rec.ad] = img
		end
	end
	for ad, id in pairs(Config.AdImages) do
		adImage[ad] = id
	end
	local made, missing = 0, 0
	for name, rec in pairs(Data.screens) do
		local img = adImage[rec.ad]
		local video = Config.Videos[name]
		if not img and not video then
			missing += 1
			continue
		end
		local size = Data.ads[rec.ad] or { 1024, 512 }
		local p = parts[name]
		if p then
			p.CanCollide = false
			p.CastShadow = false
		end
		for i, pd in ipairs(rec.panels) do
			local n = v3(pd.n).Unit
			local right = v3(pd.r).Unit
			local up = right:Cross(n).Unit * -1
			if up.Y < 0 then
				up = -up
			end
			local pos = T(v3(pd.c)) + n * 0.08 * k
			local anchor = Instance.new("Part")
			anchor.Name = name .. "_gui" .. i
			anchor.Anchored = true
			anchor.CanCollide = false
			anchor.CanTouch = false
			anchor.CanQuery = false
			anchor.CastShadow = false
			anchor.Transparency = 1
			anchor.Size = Vector3.new(pd.w * k, pd.h * k, 0.05)
			-- LookVector = n (Front faces outwards); GUI +X runs along the screen's right
			anchor.CFrame = CFrame.fromMatrix(pos, -right, up)
			local gui = Instance.new("SurfaceGui")
			gui.Face = Enum.NormalId.Front
			gui.LightInfluence = 0
			gui.Brightness = Config.ScreenBrightness
			gui.SizingMode = Enum.SurfaceGuiSizingMode.FixedSize
			local pw = math.max(64, math.floor(size[1] * (pd.u1 - pd.u0)))
			gui.CanvasSize = Vector2.new(pw, math.floor(pw * pd.h / pd.w))
			gui.ClipsDescendants = true
			if video then
				local vf = Instance.new("VideoFrame")
				vf.Size = UDim2.fromScale(1 / (pd.u1 - pd.u0), 1)
				vf.Position = UDim2.fromScale(-pd.u0 / (pd.u1 - pd.u0), 0)
				vf.Video = video
				vf.Looped = true
				vf.Playing = true
				vf.BackgroundTransparency = 1
				vf.Parent = gui
			else
				local il = Instance.new("ImageLabel")
				il.Name = "Ad"
				il.Size = UDim2.fromScale(1, 1)
				il.BackgroundColor3 = Color3.new(0, 0, 0)
				il.BorderSizePixel = 0
				il.Image = img :: string
				il.ImageRectOffset = Vector2.new(size[1] * pd.u0, 0)
				il.ImageRectSize = Vector2.new(size[1] * (pd.u1 - pd.u0), size[2])
				if rec.kind == "holo" then
					il.BackgroundTransparency = 1
					il.ImageTransparency = Config.HoloTransparency
				end
				il.Parent = gui
				local scan = Instance.new("Frame")
				scan.Name = "Scan"
				scan.BorderSizePixel = 0
				scan.BackgroundColor3 = Color3.new(1, 1, 1)
				scan.BackgroundTransparency = 0.88
				scan.Size = UDim2.fromScale(1, 0.035)
				scan.ZIndex = 2
				scan.Parent = gui
			end
			gui.Parent = anchor
			anchor:SetAttribute("Ad", rec.ad)
			anchor:SetAttribute("Kind", rec.kind)
			anchor:SetAttribute("Screen", name)
			anchor:SetAttribute("Panel", i)
			anchor:SetAttribute("Panels", #rec.panels)
			anchor:SetAttribute("Rotate", Config.RotateKinds[rec.kind] == true)
			CollectionService:AddTag(anchor, "HEX_Screen")
			anchor.Parent = folder
			made += 1
		end
	end
	-- pool of ad images per aspect ratio (for rotating billboards)
	local pool = Instance.new("Folder")
	pool.Name = "AdPool"
	for ad, id in pairs(adImage) do
		local sv = Instance.new("StringValue")
		sv.Name = ad
		sv.Value = id
		local sz = Data.ads[ad]
		if sz then
			sv:SetAttribute("Aspect", math.floor(sz[1] / sz[2] * 100 + 0.5) / 100)
			sv:SetAttribute("W", sz[1])
			sv:SetAttribute("H", sz[2])
		end
		sv.Parent = pool
	end
	pool.Parent = folder
	return made, missing
end

-- 4. lights -----------------------------------------------------------------------------
local function makeLights(T: (Vector3) -> Vector3, k: number, folder: Folder)
	local n = 0
	for _, L in ipairs(Data.lights) do
		if n >= Config.MaxLights then
			break
		end
		local isShop = string.find(L.name or "", "_shop", 1, true) ~= nil
		if (isShop and not Config.ShopLights) or (L.kind == "surface" and not Config.ScreenSurfaceLights) then
			continue
		end
		local a = Instance.new("Part")
		a.Name = "HEX_Light"
		a.Anchored = true
		a.CanCollide = false
		a.CanTouch = false
		a.CanQuery = false
		a.CastShadow = false
		a.Transparency = 1
		a.Size = Vector3.one * 0.4
		local pos = T(v3(L.pos))
		local color = Color3.fromRGB(L.color[1], L.color[2], L.color[3])
		if L.dir then
			a.CFrame = CFrame.lookAt(pos, pos + v3(L.dir))
		else
			a.CFrame = CFrame.new(pos)
		end
		local light: Light
		if L.kind == "spot" then
			local s = Instance.new("SpotLight")
			s.Face = Enum.NormalId.Front
			s.Angle = L.angle or 70
			s.Shadows = true
			light = s
		elseif L.kind == "surface" then
			local s = Instance.new("SurfaceLight")
			s.Face = Enum.NormalId.Front
			s.Angle = 90
			light = s
		else
			light = Instance.new("PointLight")
		end
		light.Color = color
		light.Brightness = if L.kind == "spot" then Config.CourtFloodBrightness else L.brightness;
		(light :: any).Range = math.min(60, L.range * k)
		light.Parent = a
		a.Parent = folder
		n += 1
	end
	return n
end

-- 5. lighting ---------------------------------------------------------------------------
local function setupLighting()
	Lighting.ClockTime = Config.ClockTime
	Lighting.Brightness = 1.2
	Lighting.Ambient = Config.Ambient
	Lighting.OutdoorAmbient = Config.OutdoorAmbient
	Lighting.EnvironmentDiffuseScale = 0.45
	Lighting.EnvironmentSpecularScale = 1
	Lighting.GlobalShadows = true
	Lighting.ExposureCompensation = 0.15
	pcall(function()
		(Lighting :: any).Technology = Enum.Technology.Future -- settable from Studio / command bar only
	end)
	for _, c in ipairs(Lighting:GetChildren()) do
		if c.Name == "HEX_Atmosphere" or c.Name == "HEX_Bloom" or c.Name == "HEX_Color" or c:IsA("Atmosphere") then
			c:Destroy()
		end
	end
	local atm = Instance.new("Atmosphere")
	atm.Name = "HEX_Atmosphere"
	atm.Density = 0.3
	atm.Offset = 0.12
	atm.Color = Color3.fromRGB(96, 92, 170)
	atm.Decay = Color3.fromRGB(80, 40, 120)
	atm.Glare = 0
	atm.Haze = 1.8
	atm.Parent = Lighting
	local bloom = Instance.new("BloomEffect")
	bloom.Name = "HEX_Bloom"
	bloom.Intensity = 0.9
	bloom.Size = 28
	bloom.Threshold = 0.92
	bloom.Parent = Lighting
	local cc = Instance.new("ColorCorrectionEffect")
	cc.Name = "HEX_Color"
	cc.Contrast = 0.12
	cc.Saturation = 0.18
	cc.TintColor = Color3.fromRGB(235, 232, 255)
	cc.Parent = Lighting
	local sky = Lighting:FindFirstChildOfClass("Sky")
	if sky then
		sky.CelestialBodiesShown = false
		sky.StarCount = 400
	end
end

function Setup.run()
	local T, k, modelA, modelB = align()
	if not T then
		return
	end
	local old = workspace:FindFirstChild("HEX_CityFX")
	if old then
		old:Destroy()
	end
	local fx = Instance.new("Folder")
	fx.Name = "HEX_CityFX"
	fx.Parent = workspace
	local cA = styleParts(modelA, false)
	local cB = modelB and styleParts(modelB, true) or { neon = 0, textured = 0, fallback = 0 }
	local screens = Instance.new("Folder")
	screens.Name = "Screens"
	screens.Parent = fx
	local made, missing = makeScreens(T, k, screens)
	local lights = Instance.new("Folder")
	lights.Name = "Lights"
	lights.Parent = fx
	local nl = makeLights(T, k, lights)
	if Config.ApplyLighting then
		setupLighting()
	end
	print(string.format(
		"[HEX] neon parts %d, textured %d, fallback-material %d | screen panels %d (%d screens without image) | lights %d",
		cA.neon + cB.neon, cA.textured + cB.textured, cA.fallback + cB.fallback, made, missing, nl))
end

return Setup
