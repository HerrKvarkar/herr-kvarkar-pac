# ISD source draft — not ready to wear

Selected donor: `models/frostbyte/ia/internalsecurity_mike.mdl`, Kevlar material only. The donor's head, arms, trousers, belt, mask, glasses and ammunition pouches are excluded. Armour is retargeted to the existing character skeleton and stored as a separate optional bodygroup.

The draft uses the original light-blue ISD shirt atlas and vest diffuse/normal maps. Only the existing red coat accents/lining islands become muted ISD blue; the black leather exterior is retained. The V2 leather coat opening is adjusted to make room for armour, the tie is removed entirely, and the DEA back emboss is being removed for department neutrality.

The DEA PAC and its hosted runtime files are unchanged. No ISD PAC has been worn. No Source tools were launched for this draft; only source mesh preparation and offline reference rendering were used. Compilation, coat fit through animations, accessory positioning and live material checks remain pending while the client MCP is unavailable.

`prepare_isd.py` reads the preserved V2 source and the inspected Workshop donor extracted to `G:/ChatGPT/kvarkar_pac_research/isd_reference`. Generated SMD/QC/VTA files and original donor material dependencies are retained here for continuation. Upstream meshes and textures retain their original authors' rights.

## Department controls

`department_profiles.json` is the editable department configuration. Shirt and coat materials/colour masters, optional tie, armour, identification and accessory choices are kept apart from the shared face, hair, physique and fitted equipment.

The draft model source now has a **Department colours** skin family and independent **Department armour** and **Tie** bodygroups. The base costume contains no tie triangles. ISD defaults are blue, armour on and tie off; DEA defaults are red, armour off and tie on. `pac_department_defaults.json` records the settings for each eventual PAC save. These are source-level settings until compilation and PAC wiring are verified; the published DEA runtime is unchanged.

The separate accessory choices are declared in the profile and still need wiring to named PAC groups during the live preview step. Do not describe this draft as a finished runtime PAC.
