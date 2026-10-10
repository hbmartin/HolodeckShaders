# Sinebow Lines

Ten undulating neon lines with inverse-distance glow and a rainbow colour drift, returned as additive light.

## Interface

```metal
float3 hdSinebowLines(float2 p, float t);
```

Returns unbounded RGB light (not a mask and not a finished colour). Values reach about 25 per line at a line centre and fall off as 1/distance, so tonemap the result, for example `1.0 - exp(-0.35 * light * light)` as in the example, or `1.0 - exp(-k * light)` for softer cores. No helper dependencies.

Canonical source: `snippets/sinebow-lines/code.metal`. Example: `snippets/sinebow-lines/example.metal`.

## Coordinates

p is the runtime's height-normalised, Y-up coordinate (vertical range about -0.5 to 0.5). The function converts it to the original Inferno UV space using fixed 16:9 scales (x × 0.6328, y × 1.125), so the shape is aspect-independent and the line bundle is centred vertically. t is seconds; it is wrapped internally at 20π seconds, the exact period of every time term, so long runs stay precise and loop seamlessly.

## Tuning

- Speed: pass `t * 0.3`–`t * 1.0`; the example uses 0.5 for a calmer drift.
- Glow width: the constant `100.0` scales distance; lower values widen the halo.
- Core clamp: `0.04` caps the peak at 25 per line; raise it to soften the hot cores.
- Spread: `0.05` per-line offset controls how far the bundle fans out.
- Scale p before calling to zoom the bundle.

## Limitations

Lines can drift partly off the top or bottom edge at the wave peaks. Inverse-distance glow never reaches zero, so the background is faintly tinted near the bundle. The cores are thinner than a pixel at 4K before tonemapping; the clamp keeps them from flickering. Too close to the existing `waves` scene to publish as its own catalog entry.

## Cost

Estimate: a ten-iteration loop with one division, two scalar sines and one vector sine per line; no textures or noise. Comparable to the `waves` body.

## Reuse and origin

Adapted from Inferno `Generation/Sinebow.metal` by Paul Hudson and other authors (MIT, Copyright (c) 2023), preserved in `references/inferno`. Changes: float maths, height-relative scales, re-centred lines, clamped 1/|d| glow and a wrapped time phase. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
