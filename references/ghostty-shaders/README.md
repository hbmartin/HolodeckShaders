# Ghostty Shaders

Survey of https://github.com/0xhckr/ghostty-shaders at `85898f0`. No repository license: rights exist only where a file header grants them. Unattributed Shadertoy ports default to CC BY-NC-SA 3.0. Originals are preserved only for permissive licenses. NC/SA or unlicensed sources are recorded here as metadata only (no files); see docs/shader-library.md.

| File | Class | Provenance / license | Use here |
| --- | --- | --- | --- |
| animated-gradient-shader | Generator | unkn0wncode; none | — |
| auto-tracking-spotlight | Cursor + post | anonymous; none | — |
| bettercrt | Post | Shadertoy WsVSzV via m-ahdal, April Hall; CC BY-NC-SA 3.0 | — |
| bloom | Post | qwerasd205 gist; none | — |
| cineShader-Lava | Generator | Shadertoy 3sySRK port; default NC | — |
| crt | Post | Timothy Lottes, Qwerasd; Unlicense | `crt-lottes` → `crt-overlay` |
| cubes | Generator | rymdlego; none | — |
| cursor_blaze | Cursor | chardskarth gist, iq SDFs; none | — |
| cursor_lightning | Cursor | Ricefrog; none | — |
| dither | Post | moni-dz; CC BY-NC-SA 4.0 | — |
| drunkard | Post | moni-dz; CC BY-NC-SA 4.0 | — |
| fireworks-rockets | Generator | Shadertoy 4dBGRw port; default NC | — |
| fireworks | Generator | BigWings lscGRl; CC BY-NC-SA 3.0 | `bigwings-fireworks` → `fireworks` |
| galaxy | Generator | Star Nest (Kali) + "Simplicity" field, unattributed | — |
| gears-and-belts | Generator | Shadertoy DsVSDV; default NC | — |
| glitchy | Post | wld3WN-derived; default NC; uses iFrame | — |
| glow-rgbsplit-twitchy | Post | mixed (kalgynirae, NickWest, Ottosson) | — |
| gradient-background | Generator | unkn0wncode; none | — |
| in-game-crt-cursor | Cursor | sarphiv; CC BY-NC-SA 4.0 | — |
| in-game-crt | Post | sarphiv; CC BY-NC-SA 4.0 | — |
| inside-the-matrix | Generator | pkazmier et al.; see reference | `inside-the-matrix` → `matrix-corridor` |
| just-snow | Generator | Andrew Baldwin; CC BY-NC-SA 3.0 | — |
| matrix-hallway | Generator | Reinder Nijhoff ldjBW1; CC BY-NC-SA 4.0 | — |
| mnoise | Generator | plyght, unattributed Ashima noise; none | — |
| negative | Post | rhodes-b; none | — |
| retro-terminal | Post | WsVSzV; CC BY-NC-SA 3.0 | — |
| sin-interference | Generator | docbobo after ms3cWn; default NC | — |
| smear_cursor_blocks | Cursor | krbylit; none | — |
| smoke-and-ghost | Post | Stixx55; none | — |
| sparks-from-fire | Generator | Jan Mróz wl2Gzc; CC BY 3.0 | `sparks-from-fire` → `ember-drift` |
| spotlight | Post | Paul Robello; none | — |
| starfield-colors | Generator | phillip-hirsch; none | — (overlaps `starfield`) |
| starfield | Generator | phillip-hirsch; none | — (overlaps `starfield`) |
| tft | Post | Greger Olsson; none | — |
| underwater | Generator | lljGDt-derived, Alex Sherwin; default NC | Clean-room inspiration for `sunlit-shallows` |
| vhs | Post | Alex Brinsmead; MIT | `vhs-overlay` → `crt-overlay` |
| water | Hybrid | Dave Hoskins caustic (MdlXz8)-derived; default NC | Clean-room inspiration for `sunlit-shallows` |

Post-process and cursor shaders need the terminal texture or cursor uniforms and are not portable to the Holodeck runtime. Generators port by deleting the final terminal blend.
