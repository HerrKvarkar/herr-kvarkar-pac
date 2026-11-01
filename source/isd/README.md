# ISD source draft — not ready to wear

Selected donor: `models/frostbyte/ia/internalsecurity_mike.mdl`, Kevlar material only. The donor's head, arms, trousers, belt, mask, glasses and ammunition pouches are excluded. Armour is retargeted to the existing character skeleton and stored as a separate optional bodygroup.

The draft uses the original light-blue ISD shirt atlas and vest diffuse/normal maps. Only the existing red coat accents/lining islands become muted ISD blue; the black leather exterior is retained. The V2 leather coat opening is adjusted to make room for armour, the tie sits behind the collar and armour, and the DEA back emboss is being removed for department neutrality.

The DEA PAC and its hosted runtime files are unchanged. No ISD PAC has been worn. The model viewer remains closed; the noninteractive model compiler was used to build native game files. The r4 model is compiled and loaded locally through the client MCP. Live checks confirmed visible armour, all material dependencies, 61 face controls, a recessed tie knot, narrower shoulder straps, and a stable 64-unit view offset. It has not been broadcast. Broader animation fit remains subject to review.

`prepare_isd.py` reads the preserved V2 source and the inspected Workshop donor extracted to `G:/ChatGPT/kvarkar_pac_research/isd_reference`. Generated SMD/QC/VTA files and original donor material dependencies are retained here for continuation. Upstream meshes and textures retain their original authors' rights.

## Department controls

`department_profiles.json` is the editable department configuration. Shirt and coat materials/colour masters, optional tie, armour, identification and accessory choices are kept apart from the shared face, hair, physique and fitted equipment.

The draft model source now has a **Department colours** skin family and independent **Department armour** and **Tie** bodygroups. The base costume contains no tie triangles. The separate Tie bodygroup has off, full-length and tucked variants. ISD defaults are blue, armour on and tucked tie; DEA defaults are red, armour off and full-length tie. `pac_department_defaults.json` records the settings for each eventual PAC save. These are source-level settings until compilation and PAC wiring are verified; the published DEA runtime is unchanged.

The separate accessory choices are declared in the profile and still need wiring to named PAC groups during the live preview step. Do not describe this draft as a finished runtime PAC.
