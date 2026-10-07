-- HEX! Cyberpunk City v2 - client-side screen / neon animation (RunContext = Client).
-- Works on the SurfaceGui overlays created by CyberpunkSetup (tag "HEX_Screen"):
--   * rolling scan line + subtle brightness breathing on every screen
--   * billboards of kinds listed in Config.RotateKinds cycle between ads of the same aspect
--   * NEON_RED beacons blink, a few neon strips buzz like faulty tubes
-- Screens farther than AnimateDistance from the camera are left static (cheap).

local CollectionService = game:GetService("CollectionService")
local RunService = game:GetService("RunService")

local root = script.Parent
local Config = require(root:WaitForChild("CyberpunkConfig"))

local AnimateDistance = 1800

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

-- rotating billboards: group panels by screen so curved screens change together
local groups = {}
for _, s in ipairs(screens) do
	if s.anchor:GetAttribute("Rotate") and s.ad then
		local name = s.anchor:GetAttribute("Screen")
		groups[name] = groups[name] or {}
		table.insert(groups[name], s)
	end
end
task.spawn(function()
	while true do
		for _, panels in pairs(groups) do
			local first = panels[1]
			local now = os.clock()
			first.nextSwap = first.nextSwap or now + math.random(Config.RotateSeconds[1], Config.RotateSeconds[2])
			if now >= first.nextSwap then
				first.nextSwap = now + math.random(Config.RotateSeconds[1], Config.RotateSeconds[2])
				local cur = first.ad.Image
				local w, h = first.ad.ImageRectSize.X, first.ad.ImageRectSize.Y
				local aspect = math.floor((w * #panels) / h * 100 + 0.5) / 100
				local list = byAspect[aspect]
				if list and #list > 1 then
					local pick = list[math.random(1, #list)]
					if pick.Value ~= cur then
						for _, s in ipairs(panels) do
							s.ad.Image = pick.Value
							s.ad.ImageRectSize = Vector2.new(pick:GetAttribute("W") / #panels, pick:GetAttribute("H"))
							s.ad.ImageRectOffset = Vector2.new(pick:GetAttribute("W") * (s.anchor:GetAttribute("Panel") - 1) / #panels, 0)
							s.gui.Brightness = s.base * 2.2 -- flash on change
						end
					end
				end
			end
		end
		task.wait(0.5)
	end
end)

-- beacons + faulty neon
local beacons, buzz = {}, {}
for _, p in ipairs(CollectionService:GetTagged("HEX_Neon")) do
	if string.find(p.Name, "NEON_RED", 1, true) then
		table.insert(beacons, p)
	elseif math.random() < 0.04 then
		table.insert(buzz, p)
	end
end

local cam = workspace.CurrentCamera
RunService.RenderStepped:Connect(function()
	local t = os.clock()
	local cpos = cam and cam.CFrame.Position or Vector3.zero
	for _, s in ipairs(screens) do
		local a = s.anchor
		if (a.Position - cpos).Magnitude < AnimateDistance then
			if s.scan then
				local y = ((t * s.speed + s.phase) % 1.2) - 0.1
				s.scan.Position = UDim2.fromScale(0, y)
			end
			local target = s.base * (1 + 0.06 * math.sin(t * 1.7 + s.phase))
			s.gui.Brightness = s.gui.Brightness + (target - s.gui.Brightness) * 0.08
		end
	end
	local on = (t % 1.6) < 0.8
	for _, p in ipairs(beacons) do
		p.Transparency = on and 0 or 0.85
	end
	for i, p in ipairs(buzz) do
		local f = math.noise(t * 6, i) > 0.35
		p.Transparency = f and 0.7 or 0
	end
end)
