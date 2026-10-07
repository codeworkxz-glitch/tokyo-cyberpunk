-- Builds the HEX! cyberpunk look when the game starts, unless it was already baked into the
-- place from the command bar (require(workspace.CyberpunkCityV2.CyberpunkSetup).run()).
if workspace:FindFirstChild("HEX_CityFX") then
	return
end
require(script.Parent.CyberpunkSetup).run()
