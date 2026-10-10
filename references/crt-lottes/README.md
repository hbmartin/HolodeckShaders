# CRT (Lottes)

[CRTS] public-domain CRT-styled scalar by Timothy Lottes (Unlicense), adapted for Ghostty by Qwerasd (gist c3da6c610c8ffe17d6d2d3cc7068f17f), preserved from 0xhckr/ghostty-shaders `85898f0`.

Post-process shader: warps and re-samples the terminal texture, then applies scanlines and an aperture/shadow mask. Not portable as a scene; mask and scanline math are reusable as overlays.
