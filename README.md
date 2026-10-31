# Herr Kvarkar — External Affairs

PAC3 outfit for Herr Kvarkar: platinum hair, custom clean-shaven fair face with blue eyes, red DEA shirt, full black tie, long dark overcoat, black trousers and gloves. No scarf. The character is compiled into one MDL; sunglasses, fitted earpiece and the retained laser pointer remain separate accessories.

Copy `herr_kvarkar_ea_field_agent.txt` into `garrysmod/data/pac3/`, then load **herr_kvarkar_ea_field_agent** in PAC3. The PAC downloads its custom visual content from this repository. It uses the game's existing player skeleton and PAC3 marker model.

- `assets/herr_kvarkar_character_v4.zip`: complete character and textures, including the animated male07 face.
- `assets/kvarkar_earpiece_fitted_v2.zip`: fitted accessory mesh and charcoal material.
- `assets/kvarkar_sunglasses.zip`: source aviator model and dependencies, masked to the glasses in PAC.
- `assets/kvarkar_laser_pointer.zip`: retained base-outfit laser model and dependencies.
- `assets/kvarkar_face_final.png`, `assets/kvarkar_dea_red_diffuse_final.png`: generated texture masters.
- `source/`: final SMD, VTA and QC files for recompilation. Compile `kvarkar_animated.qc` and `kvarkar_earpiece.qc` with Garry's Mod's `bin/studiomdl.exe`, using `-game` to point at the game directory.

The face retains 61 animation controls. PAC voice proxies drive jaw and lip movement, and a blink proxy provides occasional blinking. A hidden eye target holds a forward gaze. The player-scale setting is 74/72 for the requested approximate 6'2" height; server collision and view height are controlled by the server.

Client checks covered front/profile/rear views, the feet, shirt/coat overlap, complete tie, and open/closed mouth controls. Screenshots in `previews/` show the in-game result.

See [CREDITS.md](CREDITS.md) for upstream assets and [source/texture-generation.md](source/texture-generation.md) for the generated texture briefs. Upstream content retains its original authors' rights.
