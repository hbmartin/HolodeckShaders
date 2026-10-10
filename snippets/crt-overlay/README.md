# CRT Overlay

Shadow mask, scanline, grain, tracking-band and tube-warp overlays that give procedural colour a CRT or VHS look.

## Interface

```metal
float3 hdCrtShadowMask(float2 pixel, float dark);   // RGB multiplier, dark..1 per channel
float hdScanlines(float y, float strength);         // brightness factor, 0.29..1 at strength 1
float hdFilmGrain(float2 pixel, float t);           // signed grain in [-0.5, 0.5]
float hdTrackingBand(float y01, float t);           // 0..1 band mask
float2 hdCrtWarp(float2 c, float2 warp);            // warped centred coordinates
```

These are overlays, not a filter: the runtime has no texture to resample, so evaluate your procedural picture at the (optionally warped) coordinate, then multiply by the mask and scanline factors and add grain. `hdFilmGrain` depends on `hash21` from `shared/common.metal`; the others have no dependencies.

- `hdCrtShadowMask`: Lottes' shadow mask, a 6-pixel triad (2 pixels per channel) with each row offset by half a triad. The lit channel is 1 and the others are `dark`. The phase is computed with integer maths, avoiding the float `fract(n / 6) < 1/3` comparisons of the original, which depend on rounding.
- `hdScanlines`: Lottes' scanline beam profile (thinness 0.75): the sum of the beams above and below. At strength 1 its mean is 0.667.
- `hdFilmGrain`: Brinsmead's per-pixel colour noise, reseeded every frame.
- `hdTrackingBand`: Brinsmead's rolling tracking bar (5% of the height, one pass every 25 s).
- `hdCrtWarp`: Lottes' tube warp `c * (1 + (c.y², c.x²) * warp)`; Lottes uses `warp = (1 / (50 * aspect), 1 / 50)`.

Canonical source: `snippets/crt-overlay/code.metal`. Example: `snippets/crt-overlay/example.metal`.

## Coordinates

- pixel (mask, grain): runtime raster coordinates, Y down. Pass `floor(pixel / k)` to scale the pattern by an integer k.
- y (scanlines): scanline units, one per line. Use the picture coordinate, for example `uv.y * lines` with uv in 0..1, so scanlines bend with the tube warp.
- y01 (tracking band): 0 at the top, 1 at the bottom.
- c (warp): centred screen space, -1..1 on both axes, for example `float2(p.x / (0.5 * aspect), p.y * 2.0)`. Points with `max(abs(w)) > 1` after warping lie outside the tube.
- The screen height in pixels is available as `1.0 / fwidth(p.y)`.

## Tuning

- Mask `dark` 0.5–0.8 (Lottes recommends 0.5–0.65). The mask removes about `(2 - 2 * dark) / 3` of the light and the scanlines a third, so scale the result back up (the example uses ×1.9) or accept a dimmer image.
- Scanlines: keep at least 3 pixels per line: `lines = min(360.0, height / 3.0)`.
- Grain amplitude 0.02–0.06; enlarge grains with `k` on 4K.
- Warp: 1–3 × Lottes' default; anti-alias the tube edge with `fwidth` of the warped coordinate (example).
- The tracking band is meant to drive effects: a horizontal offset, extra noise or a brightness lift.

## Limitations

Pixel scale at 4K: the shadow mask and grain are defined per raster pixel, so a 3840×2160 output shows 2-pixel phosphors and single-pixel grain that are nearly invisible from a sofa, while the 1280×720 preview looks much coarser. The example derives `k = round(height / 1080)` to keep a 1080p-like pitch; use an integer k, because fractional scales give uneven stripes. If the system scales the app's output (for example a 1080p render upscaled by the TV), the mask will beat against the panel and show moiré; this was not checked on hardware. Scanlines under about 3 pixels per line alias into slow beat patterns. Grain changes every frame and reads as fizz on large flat areas; keep it subtle for long viewing. These overlays cannot reproduce Lottes' horizontal resampling blur or Brinsmead's chroma bleed, both of which need neighbouring picture samples; evaluate the picture several times if you need them.

## Cost

Estimate: the mask is integer arithmetic; scanlines are two cosines; grain is one `hash21`; band and warp are a few ALU operations. The example adds two `fwidth` calls and a palette evaluation; the overlays are negligible beside most pictures.

## Reuse and origin

Mask, scanline profile and warp adapted from "[CRTS] Public domain CRT-styled scalar" by Timothy Lottes (Unlicense / public domain; after FixingPixelArtFast, https://www.shadertoy.com/view/MtSfRK) as adapted for Ghostty by Qwerasd, preserved in `references/crt-lottes`. Grain and tracking band adapted from "Degraded VHS tape + CRT monitor effect" by Alex Brinsmead (MIT, Copyright (c) 2026 Alex Brinsmead), preserved in `references/vhs-overlay`. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
