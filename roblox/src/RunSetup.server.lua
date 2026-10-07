-- Builds the cyberpunk look when the game starts, unless it was already baked
-- into the place from the command bar.
if workspace:FindFirstChild("CyberpunkFX") then
	return
end
require(script.Parent.CyberpunkSetup).run()
