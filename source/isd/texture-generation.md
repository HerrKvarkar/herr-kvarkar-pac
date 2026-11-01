# ISD coat accent texture

Mode: built-in OpenAI image generation/editing tool; precise-object-edit.

Edit target: `assets/kvarkar_leather_coat_v2_fine.png`.

Saved master: `assets/kvarkar_leather_coat_isd_blue_accents.png`.

Runtime encoding: `source/isd/materials/coat_isd_blue_accents.vtf` (512 x 512 DXT5). The original master remains at its full 1254 x 1254 resolution.

Prompt: Change ONLY the existing dark red accent/lining UV islands to a muted ISD steel blue (blue hue around #54718a, with the original shading and darkness). These are the upper-left round patch, thin strip on right, and right-middle rectangular patch, plus any other red pixels. Keep ALL black leather exterior areas, grain size, seams, buttons, pockets, highlights, island positions, edges and padding unchanged. No new design, no logos, no text, no added islands, no global recolouring. This is a drop-in alternate department skin for an existing model, so preserve the precise atlas layout.

Checks: same atlas dimensions; no remaining red-dominant pixels in the edited coat master; visual inspection of UV island placement. Live shader appearance and animation fit remain untested.
