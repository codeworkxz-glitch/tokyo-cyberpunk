-- Builds the HEX! City v3 effects when the game starts, unless they were already baked into the
-- place from the command bar (require(workspace.HEXCityV3.HEXCitySetup).run()).
if workspace:FindFirstChild("HEX_CityFX") then
	return
end
require(script.Parent.HEXCitySetup).run()
