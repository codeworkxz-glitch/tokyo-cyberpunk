-- HEX! City v3 - sets up the two imported FBX models in Roblox Studio.
--
-- Run once from the Studio command bar (bakes the result into the place):
--     require(workspace.HEXCityV3.HEXCitySetup).run()
-- RunSetup (server Script) also runs it at game start if it has not been baked yet.
--
--   1. File A is your original map and is never modified. File B (the new detail) is moved so
--      it lines up with A, using three reference parts of the original map (Plaza_Curb and two
--      plaza light masts) - works even if A was imported at another position or rotation.
--   2. File B parts: `__LAMP`, `__BULB`, `__SIG_*` -> Neon; everything else keeps its texture.
--   3. every `SCR_*` screen gets a self-lit SurfaceGui showing its ad (tag "HEX_Screen");
--      HEXCityAnimator rotates them all with a fade.
--   4. every lit sign (original signs, new blade signs, gateway arches) gets a self-lit copy of
--      its artwork so it glows at night (tag "HEX_SignGlow").
--   5. street lamp / vending / screen lights, and a neutral night Lighting setup.

local CollectionService = game:GetService("CollectionService")
local Lighting = game:GetService("Lighting")

local Config = require(script.Parent.HEXCityConfig)
local Data = require(script.Parent.CityData)

local Setup = {}

local function v3(t): Vector3
	return Vector3.new(t[1], t[2], t[3])
end

local function keyOf(name: string): string?
	-- "B_Streetscape__LAMP" -> "LAMP", "B_Roof_FG_N_01__MEC_2" (split mesh) -> "MEC"
	local k = string.match(name, "__([%w_]+)$")
	if not k then
		return nil
	end
	k = string.gsub(k, "_%d+$", "")
	return k
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

local function hide(p: BasePart)
	p.Transparency = 1
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.CastShadow = false
end

-- 1. alignment -------------------------------------------------------------------------
local function basis(c: Vector3, a: Vector3, b: Vector3)
	local u = (a - b).Unit
	local w = u:Cross(a - c).Unit
	local v = w:Cross(u).Unit
	return u, v, w
end

local function align(parts: { [string]: { BasePart } })
	local function first(name: string): BasePart?
		local l = parts[name]
		return l and l[1] or nil
	end
	local mB = first("HEX_ALIGN_B")
	if not mB then
		warn("[HEX] HEX_ALIGN_B not found - import HEX_City_v3_B.fbx (the new detail) first")
		return nil
	end
	local modelB = topModel(mB)
	local refs = {}
	for _, r in ipairs(Data.refs) do
		local p = first(r.name)
		if p and topModel(p) ~= modelB then
			table.insert(refs, { data = v3(r.pos), world = p.Position })
		end
	end
	local T, R, k
	if #refs == 3 then
		local c, a, b = refs[1], refs[2], refs[3]
		k = (a.world - b.world).Magnitude / (a.data - b.data).Magnitude
		local du, dv, dw = basis(c.data, a.data, b.data)
		local wu, wv, ww = basis(c.world, a.world, b.world)
		R = function(v: Vector3): Vector3
			return wu * v:Dot(du) + wv * v:Dot(dv) + ww * v:Dot(dw)
		end
		T = function(p: Vector3): Vector3
			return c.world + R(p - c.data) * k
		end
		-- move file B so its marker lands where the data says (same rotation as A assumed)
		local delta = T(v3(Data.markerB)) - mB.Position
		if delta.Magnitude > 0.01 and modelB:IsA("PVInstance") then
			(modelB :: any):PivotTo((modelB :: any):GetPivot() + delta)
			print(string.format("[HEX] moved file B by %.2f studs to line up with your original map", delta.Magnitude))
		end
		if math.abs(k - 1) > 0.01 then
			warn(string.format("[HEX] the original map was imported at scale x%.3f; file B must use the same scale", k))
		end
	else
		warn("[HEX] Plaza_Curb / LightMast_Plaza_11 / LightMast_Plaza_02 of the original map not found - "
			.. "assuming both files were imported at the file origin")
		k = mB.Size.Y / Data.markerSize
		R = function(v: Vector3): Vector3
			return v
		end
		local origin = mB.Position - v3(Data.markerB) * k
		T = function(p: Vector3): Vector3
			return origin + p * k
		end
	end
	hide(mB)
	return T, R, k, modelB
end

-- 2. materials of file B ------------------------------------------------------------------
local function styleB(modelB: Instance)
	local counts = { neon = 0, textured = 0, fallback = 0 }
	for _, d in ipairs(modelB:GetDescendants()) do
		if not d:IsA("BasePart") then
			continue
		end
		local p = d :: BasePart
		p.Anchored = true
		p.CanCollide = Config.CollideDetail and p.CanCollide
		local key = keyOf(p.Name)
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
			if key == "SIG_RED" and string.find(p.Name, "B_Roof_", 1, true) then
				CollectionService:AddTag(p, "HEX_Beacon")
			end
			counts.neon += 1
		elseif Config.Fallback[key] then
			if textureOf(p) then
				counts.textured += 1
			else
				local fb = Config.Fallback[key]
				p.Material = fb[1]
				p.Color = fb[2]
				counts.fallback += 1
			end
		else -- picture keys (signs, banners, vending fronts, screens)
			p.CanCollide = false
			p.CastShadow = false
		end
	end
	return counts
end

-- self-lit picture on an invisible anchor part in front of a face
local function panelGui(T, R, k, pd, name: string, folder: Instance, brightness: number, canvasW: number)
	local n = R(v3(pd.n)).Unit
	local right = R(v3(pd.r)).Unit
	local up = n:Cross(right).Unit
	local anchor = Instance.new("Part")
	anchor.Name = name
	anchor.Anchored = true
	anchor.CanCollide = false
	anchor.CanTouch = false
	anchor.CanQuery = false
	anchor.CastShadow = false
	anchor.Transparency = 1
	anchor.Size = Vector3.new(pd.w * k, pd.h * k, 0.05)
	-- LookVector = n (Front faces outwards); GUI +X runs along the face's right
	anchor.CFrame = CFrame.fromMatrix(T(v3(pd.c)) + n * 0.08 * k, -right, up)
	local gui = Instance.new("SurfaceGui")
	gui.Face = Enum.NormalId.Front
	gui.LightInfluence = 0
	gui.Brightness = brightness
	gui.SizingMode = Enum.SurfaceGuiSizingMode.FixedSize
	local cw = math.max(32, math.floor(canvasW))
	gui.CanvasSize = Vector2.new(cw, math.max(8, math.floor(cw * pd.h / pd.w)))
	gui.ClipsDescendants = true
	gui.Parent = anchor
	anchor.Parent = folder
	return anchor, gui
end

-- 3. screens ----------------------------------------------------------------------------
local function makeScreens(T, R, k, parts: { [string]: { BasePart } }, folder: Folder)
	local adImage: { [string]: string } = {}
	for name, rec in pairs(Data.screens) do
		local l = parts[name]
		local img = l and textureOf(l[1])
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
		for _, p in ipairs(parts[name] or {}) do
			p.CanCollide = false
			p.CastShadow = false
		end
		for i, pd in ipairs(rec.panels) do
			local anchor, gui = panelGui(T, R, k, pd, name .. "_gui" .. i, folder, Config.ScreenBrightness,
				size[1] * (pd.u1 - pd.u0))
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
				il.Parent = gui
				if Config.ScanLine then
					local scan = Instance.new("Frame")
					scan.Name = "Scan"
					scan.BorderSizePixel = 0
					scan.BackgroundColor3 = Color3.new(1, 1, 1)
					scan.BackgroundTransparency = 0.9
					scan.Size = UDim2.fromScale(1, 0.03)
					scan.ZIndex = 2
					scan.Parent = gui
				end
			end
			anchor:SetAttribute("Ad", rec.ad)
			anchor:SetAttribute("Kind", rec.kind)
			anchor:SetAttribute("Screen", name)
			anchor:SetAttribute("Aspect", math.floor(size[1] / size[2] * 100 + 0.5) / 100)
			anchor:SetAttribute("U0", pd.u0)
			anchor:SetAttribute("U1", pd.u1)
			anchor:SetAttribute("Rotate", Config.RotateAll == true and video == nil)
			CollectionService:AddTag(anchor, "HEX_Screen")
			made += 1
		end
	end
	-- every ad image, grouped by shape in the animator
	local pool = Instance.new("Folder")
	pool.Name = "AdPool"
	for ad, id in pairs(adImage) do
		local sz = Data.ads[ad]
		if sz then
			local sv = Instance.new("StringValue")
			sv.Name = ad
			sv.Value = id
			sv:SetAttribute("Aspect", math.floor(sz[1] / sz[2] * 100 + 0.5) / 100)
			sv:SetAttribute("W", sz[1])
			sv:SetAttribute("H", sz[2])
			sv.Parent = pool
		end
	end
	pool.Parent = folder
	return made, missing
end

-- 4. sign glow --------------------------------------------------------------------------
local function makeSignGlow(T, R, k, parts: { [string]: { BasePart } }, folder: Folder)
	local atlasTex: { [string]: string } = {}
	for a, id in pairs(Config.SignAtlas) do
		atlasTex[a] = id
	end
	for _, s in ipairs(Data.signs) do
		if s.atlas ~= "self" and not atlasTex[s.atlas] then
			local l = parts[s.name]
			local tex = l and textureOf(l[1])
			if tex then
				atlasTex[s.atlas] = tex
			end
		end
	end
	local made = 0
	for _, s in ipairs(Data.signs) do
		local l = parts[s.name]
		local tex = (l and textureOf(l[1])) or atlasTex[s.atlas]
		if not tex then
			continue
		end
		local pw, ph = s.px[1], s.px[2]
		for i, pd in ipairs(s.panels) do
			local u0, v0, u1, v1 = pd.uv[1], pd.uv[2], pd.uv[3], pd.uv[4]
			local anchor, gui = panelGui(T, R, k, pd, "Glow_" .. s.name .. "_" .. i, folder, Config.SignBrightness,
				(u1 - u0) * pw)
			local il = Instance.new("ImageLabel")
			il.Size = UDim2.fromScale(1, 1)
			il.BackgroundTransparency = 1
			il.Image = tex
			il.ImageRectOffset = Vector2.new(u0 * pw, (1 - v1) * ph)
			il.ImageRectSize = Vector2.new((u1 - u0) * pw, (v1 - v0) * ph)
			il.Parent = gui
			CollectionService:AddTag(anchor, "HEX_SignGlow")
			made += 1
		end
	end
	return made
end

-- 5. lights -----------------------------------------------------------------------------
local PRIORITY = { lamp = 1, gate = 2, signal = 2, vending = 3 }

local function makeLights(T, R, k, folder: Folder)
	local list = table.clone(Data.lights)
	table.sort(list, function(a, b)
		local pa, pb = PRIORITY[a.name] or 4, PRIORITY[b.name] or 4
		if pa ~= pb then
			return pa < pb
		end
		return a.range > b.range
	end)
	local n = 0
	for _, L in ipairs(list) do
		if n >= Config.MaxLights then
			break
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
		a.CFrame = if L.dir then CFrame.lookAt(pos, pos + R(v3(L.dir))) else CFrame.new(pos)
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
		light.Color = Color3.fromRGB(L.color[1], L.color[2], L.color[3])
		light.Brightness = if L.kind == "spot" then Config.CourtFloodBrightness else L.brightness;
		(light :: any).Range = math.min(60, L.range * k)
		light.Parent = a
		a.Parent = folder
		n += 1
	end
	return n
end

-- 6. lighting ---------------------------------------------------------------------------
local function setupLighting()
	if Config.TimeOfDay == "Keep" then
		return
	end
	local dusk = Config.TimeOfDay == "Dusk"
	Lighting.ClockTime = if dusk then 18.6 else 0.5
	Lighting.Brightness = if dusk then 1.6 else 1.0
	Lighting.Ambient = if dusk then Color3.fromRGB(70, 72, 84) else Color3.fromRGB(52, 54, 62)
	Lighting.OutdoorAmbient = if dusk then Color3.fromRGB(120, 124, 140) else Color3.fromRGB(96, 100, 114)
	Lighting.EnvironmentDiffuseScale = 0.4
	Lighting.EnvironmentSpecularScale = 0.8
	Lighting.GlobalShadows = true
	Lighting.ExposureCompensation = 0.1
	pcall(function()
		(Lighting :: any).Technology = Enum.Technology.Future -- settable from Studio / command bar only
	end)
	for _, c in ipairs(Lighting:GetChildren()) do
		if string.sub(c.Name, 1, 4) == "HEX_" or c:IsA("Atmosphere") then
			c:Destroy()
		end
	end
	local atm = Instance.new("Atmosphere")
	atm.Name = "HEX_Atmosphere"
	atm.Density = 0.28
	atm.Offset = 0.1
	atm.Color = if dusk then Color3.fromRGB(150, 160, 190) else Color3.fromRGB(110, 116, 132)
	atm.Decay = if dusk then Color3.fromRGB(120, 100, 120) else Color3.fromRGB(60, 62, 74)
	atm.Glare = 0
	atm.Haze = 1.4
	atm.Parent = Lighting
	local bloom = Instance.new("BloomEffect")
	bloom.Name = "HEX_Bloom"
	bloom.Intensity = 0.7
	bloom.Size = 24
	bloom.Threshold = 0.95
	bloom.Parent = Lighting
	local cc = Instance.new("ColorCorrectionEffect")
	cc.Name = "HEX_Color"
	cc.Contrast = 0.08
	cc.Saturation = 0.08
	cc.Parent = Lighting
end

function Setup.run()
	if Data.version ~= 3 then
		warn("[HEX] CityData is not the v3 data - use the HEXCityV3.rbxmx from the v3 zip")
		return
	end
	local parts: { [string]: { BasePart } } = {}
	for _, d in ipairs(workspace:GetDescendants()) do
		if d:IsA("BasePart") then
			parts[d.Name] = parts[d.Name] or {}
			table.insert(parts[d.Name], d)
		end
	end
	local T, R, k, modelB = align(parts)
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
	local cB = styleB(modelB)
	local screens = Instance.new("Folder")
	screens.Name = "Screens"
	screens.Parent = fx
	local made, missing = makeScreens(T, R, k, parts, screens)
	local ng = 0
	if Config.SignGlow then
		local glow = Instance.new("Folder")
		glow.Name = "SignGlow"
		glow.Parent = fx
		ng = makeSignGlow(T, R, k, parts, glow)
	end
	local lights = Instance.new("Folder")
	lights.Name = "Lights"
	lights.Parent = fx
	local nl = makeLights(T, R, k, lights)
	setupLighting()
	print(string.format(
		"[HEX] v3: neon parts %d, textured %d, fallback %d | screen panels %d (%d screens without image) | sign glow %d | lights %d",
		cB.neon, cB.textured, cB.fallback, made, missing, ng, nl))
end

return Setup
