-- Client-side animation: scrolling billboards, LED chase, pulsing roof crowns and
-- faulty neon signs. Runs as a Script with RunContext = Client.
local RunService = game:GetService("RunService")
local CollectionService = game:GetService("CollectionService")

local Config = require(script.Parent.CyberpunkConfig)

while not workspace:GetAttribute("CyberpunkReady") do
	task.wait(0.5)
end
local M = workspace:GetAttribute("CyberpunkStudsPerMeter") or 1

local screens = {}
local function addScreen(panel: Instance)
	local gui = panel:FindFirstChildOfClass("SurfaceGui")
	local clip = gui and gui:FindFirstChild("Clip")
	if not clip then
		return
	end
	local phase = panel:GetAttribute("Phase") or 0
	table.insert(screens, {
		panel = panel,
		gui = gui,
		A = clip:FindFirstChild("A"),
		B = clip:FindFirstChild("B"),
		scan = clip:FindFirstChild("Scan"),
		fx = panel:GetAttribute("FX") or 0,
		fy = panel:GetAttribute("FY") or 0,
		fw = panel:GetAttribute("FW") or 1,
		fh = panel:GetAttribute("FH") or 1,
		speed = panel:GetAttribute("Speed") or 0.1,
		horizontal = panel:GetAttribute("Axis") ~= "Y",
		phase = phase,
		seed = phase * 100,
	})
end
for _, p in ipairs(CollectionService:GetTagged("CP_Screen")) do
	addScreen(p)
end
CollectionService:GetInstanceAddedSignal("CP_Screen"):Connect(addScreen)

local function tagged(tag: string)
	local list = {}
	for _, p in ipairs(CollectionService:GetTagged(tag)) do
		table.insert(list, { part = p, base = p:GetAttribute("Accent") or p.Color, phase = p:GetAttribute("Phase") or (p.Position.X + p.Position.Z) / M })
	end
	return list
end
local leds = tagged("CP_LED")
local crowns = tagged("CP_Crown")
local faulty = tagged("CP_FaultySign")

-- Only animate billboards near the camera
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
		if math.noise(t * 1.7, s.seed) > 0.32 then -- brief glitch tearing
			jitter = math.noise(t * 40, s.seed, 3) * 0.15
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
		local flicker = 0.85 + 0.3 * math.noise(t * 6, s.seed, 7)
		s.gui.Brightness = if blackout then 0.15 else Config.ScreenBrightness * flicker
		local scanY = ((t * 0.25 + s.phase) % 1.2) - 0.1
		s.scan.Position = UDim2.fromScale(0, (scanY - s.fy) / s.fh)
	end
end

local function scaled(c: Color3, k: number): Color3
	return Color3.new(c.R * k, c.G * k, c.B * k)
end

local function updateNeon(t: number)
	for _, l in ipairs(leds) do
		local k = (0.5 + 0.5 * math.sin(l.phase * 0.4 - t * 5)) ^ 6
		l.part.Color = l.base:Lerp(Color3.new(1, 1, 1), k * 0.6)
		l.part.Transparency = 0.35 * (1 - k)
	end
	for _, c in ipairs(crowns) do
		c.part.Color = scaled(c.base, 0.65 + 0.35 * math.sin(t * 1.5 + c.phase))
	end
	for _, f in ipairs(faulty) do
		f.part.Transparency = if math.noise(t * 9, f.phase) > 0.12 then 0.75 else 0
	end
end

local refreshTimer, neonTimer = 0, 0
refreshActive()
RunService.RenderStepped:Connect(function(dt)
	local t = os.clock()
	refreshTimer += dt
	if refreshTimer > 1 then
		refreshTimer = 0
		refreshActive()
	end
	updateScreens(t)
	neonTimer += dt
	if neonTimer > 0.05 then
		neonTimer = 0
		updateNeon(t)
	end
end)
