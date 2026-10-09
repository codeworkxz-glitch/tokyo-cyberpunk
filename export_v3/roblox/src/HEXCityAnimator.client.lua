-- HEX! City v3 - client-side screen animation (RunContext = Client).
-- Works on the SurfaceGui overlays created by HEXCitySetup (tag "HEX_Screen"):
--   * every screen rotates through the ads of its shape with a fade (Config.RotateAll)
--   * rolling scan line + subtle brightness breathing near the camera
--   * rooftop antenna beacons blink

local CollectionService = game:GetService("CollectionService")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local root = script.Parent
local Config = require(root:WaitForChild("HEXCityConfig"))

local AnimateDistance = 1500

local fx = workspace:WaitForChild("HEX_CityFX", 60)
if not fx then
	return
end
local pool = fx:WaitForChild("Screens"):WaitForChild("AdPool", 30)

local byAspect = {}
if pool then
	for _, sv in ipairs(pool:GetChildren()) do
		local a = sv:GetAttribute("Aspect")
		if a then
			byAspect[a] = byAspect[a] or {}
			table.insert(byAspect[a], sv)
		end
	end
end

local screens = {}
local function add(anchor)
	local gui = anchor:FindFirstChildOfClass("SurfaceGui")
	if not gui then
		return
	end
	table.insert(screens, {
		anchor = anchor,
		gui = gui,
		ad = gui:FindFirstChild("Ad"),
		scan = gui:FindFirstChild("Scan"),
		phase = math.random() * 10,
		speed = 0.12 + math.random() * 0.25,
		base = gui.Brightness,
	})
end
for _, a in ipairs(CollectionService:GetTagged("HEX_Screen")) do
	add(a)
end
CollectionService:GetInstanceAddedSignal("HEX_Screen"):Connect(add)

local fade = TweenInfo.new(Config.FadeSeconds or 0.35, Enum.EasingStyle.Quad, Enum.EasingDirection.InOut)

-- all panels of one screen (curved screens have several) swap together
local function swap(panels)
	local first = panels[1]
	local list = byAspect[first.anchor:GetAttribute("Aspect")]
	if not list or #list < 2 then
		return
	end
	local pick
	for _ = 1, 8 do
		pick = list[math.random(1, #list)]
		if pick.Value ~= first.ad.Image then
			break
		end
	end
	if pick.Value == first.ad.Image then
		return
	end
	for _, s in ipairs(panels) do
		TweenService:Create(s.ad, fade, { ImageTransparency = 1 }):Play()
	end
	task.wait(fade.Time)
	local W, H = pick:GetAttribute("W"), pick:GetAttribute("H")
	for _, s in ipairs(panels) do
		local u0, u1 = s.anchor:GetAttribute("U0") or 0, s.anchor:GetAttribute("U1") or 1
		s.ad.Image = pick.Value
		s.ad.ImageRectOffset = Vector2.new(W * u0, 0)
		s.ad.ImageRectSize = Vector2.new(W * (u1 - u0), H)
		TweenService:Create(s.ad, fade, { ImageTransparency = 0 }):Play()
		s.gui.Brightness = s.base * 1.5 -- small flash as the new ad appears
	end
end

task.spawn(function()
	local nextSwap = {}
	while true do
		local groups = {}
		for _, s in ipairs(screens) do
			if s.ad and s.anchor.Parent and s.anchor:GetAttribute("Rotate") then
				local name = s.anchor:GetAttribute("Screen")
				groups[name] = groups[name] or {}
				table.insert(groups[name], s)
			end
		end
		local now = os.clock()
		local lo, hi = Config.RotateSeconds[1], Config.RotateSeconds[2]
		for name, panels in pairs(groups) do
			nextSwap[name] = nextSwap[name] or now + math.random() * hi
			if now >= nextSwap[name] then
				nextSwap[name] = now + lo + math.random() * (hi - lo)
				task.spawn(swap, panels)
			end
		end
		task.wait(0.25)
	end
end)

local beacons = CollectionService:GetTagged("HEX_Beacon")
local cam = workspace.CurrentCamera
RunService.RenderStepped:Connect(function()
	local t = os.clock()
	local cpos = cam and cam.CFrame.Position or Vector3.zero
	for _, s in ipairs(screens) do
		if (s.anchor.Position - cpos).Magnitude < AnimateDistance then
			if s.scan then
				s.scan.Position = UDim2.fromScale(0, ((t * s.speed + s.phase) % 1.2) - 0.1)
			end
			local target = s.base * (1 + 0.05 * math.sin(t * 1.7 + s.phase))
			s.gui.Brightness = s.gui.Brightness + (target - s.gui.Brightness) * 0.08
		end
	end
	local on = (t % 1.6) < 0.8
	for _, p in ipairs(beacons) do
		p.Transparency = on and 0 or 0.85
	end
end)
