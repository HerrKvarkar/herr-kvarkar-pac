## RSD researcher preview

Load **PAC3 > Load > herr_kvarkar > rsd_preview** to review the separate white researcher variant. It has not been worn or sent to the server. The existing ISD and DEA saves are unchanged.

The long coat and shirt are white, taking their colour and matte finish from the current `models/sanctum/research/researcher/researcher_male_02.mdl` researcher model. The shared face, platinum hair, opaque aviators, leather gloves, trousers and boots are retained. The tie uses the existing atlas’s grey fabric with a charcoal shader; the narrow knot sits between the collar points, with the side band recessed beneath them. There is no armour; the microscope emblem is a shallow same-cloth relief. The optional tie is bodygroup 2 (0 off, 1 on); the emblem is bodygroup 3 (0 plain, 1 RSD). The original researcher belt pager is bodygroup 4 (0 off, 1 on), enabled by default; RSD has no earpiece. The native Researcher ID and clip are fitted to the left breast, using the original donor card/clip geometry, normals and skin weights, with only a small translation onto the broader coat breast: bodygroup 5, ID badge (0 off, 1 on). The separate donor lanyard is bodygroup 6 (0 off, 1 on), disabled by default. The inherited laser equipment is disabled but remains available as a named optional group.

RSD runtime content is a separate 15,345,233-byte pack so unused ISD armour/skins do not consume the server's 15 MiB budget. Character geometry remains one MDL with 61 facial controls. It uses the same visual scale and Size 1 camera-safe settings. `department_profiles.json` holds the RSD material and accessory defaults.

Native offscreen front/back and running checks left the player camera unchanged. RSD now retains the same unmodified lower-coat geometry and independent damped tail weights as DEA/ISD. The extra RSD thigh pinning and skirt inflation have been removed to restore the requested loose movement. **Known preview limitation:** a raised boot can still intersect the rear hem during a full running stride; the long coat has no physical leg collision. This preview needs fit review before approval.

Build: `python source/rsd/prepare_rsd.py`, compile `source/rsd/kvarkar_rsd.qc` with the game's noninteractive `studiomdl.exe`, then `python source/rsd/package_rsd.py`. The scripts require the same Python dependencies as the shared build. New texture masters and generation briefs are documented in `source/texture-generation.md`. The supplied RSD microscope emblem is preserved from the user-confirmed roster image; no roster contents are published.

# ISD and shared department base � local review

ISD was approved and worn on 1 November 2026. Both departments are organised in **PAC3 > Load > herr_kvarkar**:

- **isd** - blue accents, ISD Kevlar and tucked tie.
- **dea** - approved red-shirt DEA V2.
- **shared_base** - reusable character without armour or tie.
- **archive/dea_v1** - original DEA backup.

The folder is `garrysmod/data/pac3/herr_kvarkar/` in the game and `pacs/herr_kvarkar/` in this repository. Load the desired outfit and choose Wear. Legacy names remain as compatible aliases. All four ISD roots were accepted by the server. The temporary preview camera has been removed from the game's separate VWAR camera registry.


Select **Character | Department colours and armour** in PAC3. Skin 0 selects ISD blue; Skin 1 selects DEA red. **Department armour** is 0 off or 1 on. **Tie** is 0 off, 1 full length, or 2 tucked beneath armour. **Department insignia** is 0 off, 1 ISD scales-of-justice, or 2 DEA handshake. The current ISD save uses skin 0, armour 1 and tie 2. Eyewear, fitted earpiece and laser equipment have named parts that can be hidden independently. The editable profile definitions are in `department_profiles.json`.

The hosted r7 pack is 15,320,852 bytes, below the verified 15 MiB PAC limit. Native client checks confirmed all 18 materials loaded, 61 facial controls, visible armour, revised collar/strap clearance and a 64-unit view offset. The shoulder straps and tucked tie were fitted in the running game; further pose-specific feedback can be addressed before approval. The DEA back emboss has been removed from this shared coat geometry.

# Herr Kvarkar — V2

V2 was approved and worn on 31 October 2026. Load `herr_kvarkar_ea_field_agent.txt` or the versioned `herr_kvarkar_ea_field_agent_v2.txt`. The V1 save remains available for rollback.

The hidden player entity uses Size 1 and a uniform visual Scale of 79/72. This replaces the previous Size multiplier, which caused stationary camera jitter during live use; the user confirmed the changed settings resolved it.

V2 has a taller 6'7" visual scale, a stronger upper-body silhouette and a naturally tapered face. The fine-grain black leather coat reaches below the knee and has two independent, damped coat-tail bones. Matching black field trousers and lace-up boots retain their original ankle joins. Pocket panels sit on the outer thighs; the belt stays at the waist. The gloves are black leather, the complete shirt collar is retained, and the tie uses the shirt's front-surface skinning and clearance. The provided External Affairs handshake emblem is shallow geometry relief on the upper back. The third coat button keeps its original round geometry.

The visible character is still one compiled MDL, with the existing opaque aviators and earpiece as separate accessories. Runtime content is in `assets/herr_kvarkar_character_v2_preview_r7_waistfix.zip` (13,800,674 bytes, below the verified 15 MiB server download limit). The full-resolution shirt uses DXT5 compression; the face texture remains unchanged. Final V2 model source and reproducible build/package scripts are under `source/v2/`; the texture masters and prompts are documented in [source/texture-generation.md](source/texture-generation.md).

Build geometry with `python source/v2/build_v2.py --revision 7`, compile `source/v2/kvarkar_animated.qc` with the game's `studiomdl.exe`, then run `python source/v2/package_v2.py --game <garrysmod-directory> --revision 7`. The scripts use NumPy, Pillow and srctools. The package checks that it contains one model and every referenced texture, and stays within the PAC download size budget.

## V1

PAC3 outfit for Herr Kvarkar: platinum hair, custom clean-shaven fair face with blue eyes, red DEA shirt, full black tie, long dark overcoat, black trousers and gloves. No scarf. The character is compiled into one MDL; sunglasses, fitted earpiece and the retained laser pointer remain separate accessories.

Copy `herr_kvarkar_ea_field_agent.txt` into `garrysmod/data/pac3/`, then load **herr_kvarkar_ea_field_agent** in PAC3. The PAC downloads its custom visual content from this repository. It uses the game's existing player skeleton and PAC3 marker model.

The versioned save is `herr_kvarkar_ea_field_agent_v1.txt`. The latest v1 GitHub release includes that PAC and a complete archive of the content and model sources.

- `assets/herr_kvarkar_character_v4.zip`: complete character and textures, including the animated male07 face.
- `assets/kvarkar_earpiece_fitted_v4.zip`: fitted accessory mesh and charcoal material.
- `assets/kvarkar_aviators_v2.zip`: aviator glasses compiled as a standalone accessory.
- `assets/kvarkar_laser_pointer.zip`: retained base-outfit laser model and dependencies.
- `assets/kvarkar_face_final.png`, `assets/kvarkar_dea_red_diffuse_final.png`: generated texture masters.
- `source/`: final SMD, VTA and QC files for recompilation. Compile `kvarkar_animated.qc` and `kvarkar_earpiece.qc` with Garry's Mod's `bin/studiomdl.exe`, using `-game` to point at the game directory.

The face retains 61 animation controls. PAC voice proxies drive jaw and lip movement, and a blink proxy provides occasional blinking. A hidden eye target holds a forward gaze. The player-scale setting is 74/72 for the requested approximate 6'2" height; server collision and view height are controlled by the server.

Client checks covered front/profile/rear views, the feet, shirt/coat overlap, complete tie, and open/closed mouth controls. Screenshots in `previews/` show the in-game result.

See [CREDITS.md](CREDITS.md) for upstream assets and [source/texture-generation.md](source/texture-generation.md) for the generated texture briefs. Upstream content retains its original authors' rights.


The ISD save includes the original roster emblem on the upper back. Upper straps and the vest back panel follow coat skin weights to maintain clearance during running. Standing and running front/side/back test renders were checked without changing the player camera.

The worn ISD emblem is now a subtle 0.025-unit leather relief using the original coat UVs, grain and normal map, rather than a black alpha mark. The update was saved and all four server confirmations succeeded.
