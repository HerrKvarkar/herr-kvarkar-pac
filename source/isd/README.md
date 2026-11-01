# ISD source draft â€” not ready to wear

Selected donor: `models/frostbyte/ia/internalsecurity_mike.mdl`, Kevlar material only. The donor's head, arms, trousers, belt, mask, glasses and ammunition pouches are excluded. Armour is retargeted to the existing character skeleton and stored as a separate optional bodygroup.

The draft uses the original light-blue ISD shirt atlas and vest diffuse/normal maps. Only the existing red coat accents/lining islands become muted ISD blue; the black leather exterior is retained. The V2 leather coat opening is adjusted to make room for armour, the tie sits behind the collar and armour, and the DEA back emboss is being removed for department neutrality.

The DEA PAC and its hosted runtime files are unchanged. ISD was approved and worn on 1 November 2026; all four server confirmations succeeded. The model viewer remains closed; the noninteractive model compiler was used to build native game files. The r4 model is compiled and loaded locally through the client MCP. Live checks confirmed visible armour, all material dependencies, 61 face controls, a recessed tie knot, narrower shoulder straps, and a stable 64-unit view offset. It has been worn after explicit user approval. Broader animation fit remains subject to review.

`prepare_isd.py` reads the preserved V2 source and the inspected Workshop donor extracted to `G:/ChatGPT/kvarkar_pac_research/isd_reference`. Generated SMD/QC/VTA files and original donor material dependencies are retained here for continuation. Upstream meshes and textures retain their original authors' rights.

## Department controls

`department_profiles.json` is the editable department configuration. Shirt and coat materials/colour masters, optional tie, armour, identification and accessory choices are kept apart from the shared face, hair, physique and fitted equipment.

The draft model source now has a **Department colours** skin family and independent **Department armour** and **Tie** bodygroups. The base costume contains no tie triangles. The separate Tie bodygroup has off, full-length and tucked variants. ISD defaults are blue, armour on and tucked tie; DEA defaults are red, armour off and full-length tie. `pac_department_defaults.json` records the settings for each eventual PAC save. These defaults are wired into the saved ISD preview and shared base. The published DEA runtime is unchanged.

The saved preview has separately named eyewear, earpiece and laser equipment parts. Toggle their Hide setting in PAC3. The model colour/armour/tie controls are exposed on the main character part. The ISD preset is approved; organised PAC saves are under `pacs/herr_kvarkar/`.

## r6 movement and insignia update

Upper shoulder straps and the vest back panel now follow the coat surface's skin weights with inward clearance, addressing shoulder/back protrusions during running. Separate native standing and running renders were checked with an invalidated bone cache. No game camera override is used for this verification.

The exact scales-of-justice ISD emblem from the supplied sheet is a shallow conforming upper-back relief. The optional **Department insignia** bodygroup is 0 off, 1 ISD scales, 2 DEA handshake. Its surface and weights are copied from the coat so it bends with the same panel. The shared base defaults to no emblem.
