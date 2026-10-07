-- Client-side animation: scrolling screens and holograms, faulty signs, neon pulse,
-- LED chase, blinking beacons and flying cars. Runs as a Script with RunContext = Client.
local RunService = game:GetService("RunService")
local CollectionService = game:GetService("CollectionService")

local Config = require(script.Parent.CyberpunkConfig)

while not workspace:GetAttribute("CyberpunkReady") do
	task.wait(0.5)
end
local M = workspace:GetAttribute("CyberpunkStudsPerMeter") or 1

-- Screens and holograms ----------------------------------------------------
local screens = {}
local function addScreen(panel: Instance)
	local gui = panel:FindFirstChildOfClass("SurfaceGui")
	local clip = gui and gui:FindFirstChild("Clip")
	if not clip or not clip:FindFirstChild("B") then
		return
	end
	local phase = panel:GetAttribute("Phase") or 0
	table.insert(screens, {
		panel = panel,
		gui = gui,
		A = clip.A,
		B = clip.B,
		scan = clip:FindFirstChild("Scan"),
		fx = panel:GetAttribute("FX") or 0,
		fy = panel:GetAttribute("FY") or 0,
		fw = panel:GetAttribute("FW") or 1,
		fh = panel:GetAttribute("FH") or 1,
		speed = panel:GetAttribute("Speed") or 0.1,
		horizontal = panel:GetAttribute("Axis") ~= "Y",
		holo = panel:GetAttribute("Holo") == true,
		base = panel:GetAttribute("BaseBrightness") or Config.ScreenBrightness,
		phase = phase,
		seed = phase * 100,
	})
end
for _, p in ipairs(CollectionService:GetTagged("CP_Screen")) do
	addScreen(p)
end

local active = {}
local function refreshActive()
	local cam = workspace.CurrentCamera
	if not cam then
		return
	end
	local origin = cam.CFrame.Position
	table.clear(active)
	for _, s in ipairs(screens) do
		if s.panel.Parent and (s.panel.Position - origin).Magnitude < Config.AnimateDistanceStuds then
			table.insert(active, s)
		end
	end
end

local function updateScreens(t: number)
	for _, s in ipairs(active) do
		local off = (t * s.speed + s.phase) % 1
		local jitter = 0
		local glitchLevel = if s.holo then 0.25 else 0.32
		if math.noise(t * 1.7, s.seed) > glitchLevel then
			jitter = math.noise(t * 40, s.seed, 3) * (if s.holo then 0.25 else 0.15)
		end
		if s.horizontal then
			local y = -s.fy / s.fh
			s.A.Position = UDim2.fromScale((-off - s.fx + jitter) / s.fw, y)
			s.B.Position = UDim2.fromScale((1 - off - s.fx + jitter) / s.fw, y)
		else
			local x = (-s.fx + jitter) / s.fw
			s.A.Position = UDim2.fromScale(x, (-off - s.fy) / s.fh)
			s.B.Position = UDim2.fromScale(x, (1 - off - s.fy) / s.fh)
		end
		local blackout = math.noise(t * 0.9, s.seed, 13) < -0.38
		local flicker = 0.85 + (if s.holo then 0.5 else 0.3) * math.noise(t * 6, s.seed, 7)
		s.gui.Brightness = if blackout then 0.15 else s.base * flicker
		if s.scan then
			local scanY = ((t * (if s.holo then 0.5 else 0.25) + s.phase) % 1.2) - 0.1
			s.scan.Position = UDim2.fromScale(0, (scanY - s.fy) / s.fh)
		end
	end
end

-- Neon, LEDs, beacons, faulty signs ----------------------------------------
local function tagged(tag: string)
	local list = {}
	for _, p in ipairs(CollectionService:GetTagged(tag)) do
		table.insert(list, {
			part = p,
			gui = p:FindFirstChildOfClass("SurfaceGui"),
			base = p:GetAttribute("Accent") or p.Color,
			phase = p:GetAttribute("Phase") or (p.Position.X + p.Position.Z) / M,
		})
	end
	return list
end
local neon = tagged("CP_Neon")
local leds = tagged("CP_LED")
local beacons = tagged("CP_Beacon")
local faulty = tagged("CP_FaultySign")

local function scaled(c: Color3, k: number): Color3
	return Color3.new(c.R * k, c.G * k, c.B * k)
end

local function updateNeon(t: number)
	for _, n in ipairs(neon) do
		n.part.Color = scaled(n.base, 0.75 + 0.25 * math.sin(t * 1.5 + n.phase))
	end
	for _, l in ipairs(leds) do
		local k = (0.5 + 0.5 * math.sin(l.phase * 0.4 - t * 5)) ^ 6
		l.part.Color = l.base:Lerp(Color3.new(1, 1, 1), k * 0.6)
	end
	for _, b in ipairs(beacons) do
		local on = (t * 0.8 + b.phase) % 1 < 0.15
		b.part.Color = if on then b.base else scaled(b.base, 0.15)
	end
	for _, f in ipairs(faulty) do
		local off = math.noise(t * 9, f.phase * 37.3) > 0.12
		if f.gui then
			f.gui.Enabled = not off
		else
			f.part.Transparency = if off then 0.75 else 0
		end
	end
end

-- Flying cars ----------------------------------------------------------------
local traffic = Instance.new("Folder")
traffic.Name = "CP_Traffic"
traffic.Parent = workspace
local cars = {}

local function makeCar(rng: Random, accent: Color3): Model
	local body = Instance.new("Part")
	body.Anchored = true
	body.CanCollide = false
	body.CanQuery = false
	body.CanTouch = false
	body.Size = Vector3.new(2.4, 1.0, 5.0) * M
	body.Material = Enum.Material.Metal
	body.Color = Color3.fromRGB(25, 27, 35)
	local strip = Instance.new("Part")
	strip.Anchored = true
	strip.CanCollide = false
	strip.CanQuery = false
	strip.CanTouch = false
	strip.Size = Vector3.new(2.5, 0.15, 5.1) * M
	strip.Material = Enum.Material.Neon
	strip.Color = accent
	strip.Name = "Strip"
	strip.Parent = body
	local a0 = Instance.new("Attachment")
	a0.Position = Vector3.new(-1.0, 0, 2.5) * M
	a0.Parent = body
	local a1 = Instance.new("Attachment")
	a1.Position = Vector3.new(1.0, 0, 2.5) * M
	a1.Parent = body
	local trail = Instance.new("Trail")
	trail.Attachment0 = a0
	trail.Attachment1 = a1
	trail.Lifetime = 0.5
	trail.LightEmission = 1
	trail.LightInfluence = 0
	trail.Color = ColorSequence.new(Color3.fromRGB(255, 40, 60), accent)
	trail.Transparency = NumberSequence.new(0.1, 1)
	trail.Parent = body
	local light = Instance.new("PointLight")
	light.Color = accent
	light.Range = 12 * M
	light.Brightness = 2
	light.Parent = body
	body.Parent = traffic
	return body
end

local function spawnTraffic()
	local lo = workspace:GetAttribute("CyberpunkCityMin")
	local hi = workspace:GetAttribute("CyberpunkCityMax")
	if not lo or not hi or Config.FlyingCars <= 0 then
		return
	end
	local rng = Random.new(2077)
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = { traffic }
	for _ = 1, Config.FlyingCars do
		for _ = 1, 60 do
			local alongX = rng:NextNumber() < 0.5
			local y = lo.Y + rng:NextNumber(Config.FlyingCarAltitude[1], Config.FlyingCarAltitude[2]) * M
			local a = if alongX then rng:NextNumber(lo.Z, hi.Z) else rng:NextNumber(lo.X, hi.X)
			local start = if alongX then Vector3.new(lo.X, y, a) else Vector3.new(a, y, lo.Z)
			local finish = if alongX then Vector3.new(hi.X, y, a) else Vector3.new(a, y, hi.Z)
			if rng:NextNumber() < 0.5 then
				start, finish = finish, start
			end
			local dir = finish - start
			local side = dir.Unit:Cross(Vector3.yAxis) * 2 * M
			if
				not workspace:Raycast(start, dir, params)
				and not workspace:Raycast(start + side, dir, params)
				and not workspace:Raycast(start - side + Vector3.yAxis * M, dir, params)
			then
				local accent = Config.Accents[rng:NextInteger(1, #Config.Accents)]
				local body = makeCar(rng, accent)
				table.insert(cars, {
					body = body,
					trail = body:FindFirstChildOfClass("Trail"),
					start = start,
					dir = dir.Unit,
					length = dir.Magnitude,
					speed = rng:NextNumber(Config.FlyingCarSpeed[1], Config.FlyingCarSpeed[2]) * M,
					dist = rng:NextNumber() * dir.Magnitude,
				})
				break
			end
		end
	end
end

local function updateCars(dt: number, t: number)
	for i, c in ipairs(cars) do
		local before = c.dist
		c.dist = (c.dist + c.speed * dt) % c.length
		if c.dist < before then
			c.trail:Clear() -- wrapped back to the start of the lane
		end
		local pos = c.start + c.dir * c.dist + Vector3.yAxis * math.sin(t * 1.3 + i) * 0.3 * M
		local cf = CFrame.lookAt(pos, pos + c.dir)
		c.body.CFrame = cf
		c.body.Strip.CFrame = cf * CFrame.new(0, -0.5 * M, 0)
	end
end

-- Main loop --------------------------------------------------------------------
spawnTraffic()
refreshActive()
local refreshTimer, neonTimer = 0, 0
RunService.RenderStepped:Connect(function(dt)
	local t = os.clock()
	refreshTimer += dt
	if refreshTimer > 1 then
		refreshTimer = 0
		refreshActive()
	end
	updateScreens(t)
	updateCars(dt, t)
	neonTimer += dt
	if neonTimer > 0.05 then
		neonTimer = 0
		updateNeon(t)
	end
end)
