# Sine Warp

Sine and cosine domain warp that wobbles coordinates like a water surface, with a seamless wrapped phase.

## Interface

```metal
float2 hdSineWarp(float2 uv, float t, float strength, float frequency);
```

Returns warped coordinates (not a colour or mask): `uv + (sin(f·uv.y + φ), cos(f·uv.x + φ)) · strength`, where the phase φ = `fmod(t · 0.05 · f, 2π)`. Sample any procedural pattern with the result. No helper dependencies.

Canonical source: `snippets/sine-warp/code.metal`. Example: `snippets/sine-warp/example.metal`.

## Coordinates

uv may be any planar coordinate; the example passes the runtime's height-normalised p. strength is the peak displacement in the same units as uv; frequency is radians per uv unit. t is seconds multiplied by a speed factor (Inferno's `speed` parameter: pass `t * speed`).

## Tuning

- Inferno defaults on 0..1 UVs (speed 3, strength 3, frequency 10) map to `hdSineWarp(uv01, t * 3.0, 0.03, 10.0)`. On height-normalised p, strength 0.005–0.02 and frequency 8–20 read as water.
- Keep `strength * frequency` below about 0.5, or the warp folds back on itself and patterns tear.
- Chain two calls with different frequencies for less regular ripples.

## Limitations

The warp is periodic and regular, so it reads as a gentle wobble rather than turbulent water; combine it with noise for organic motion. Warping a hard-edged pattern stretches its edges, so derivative-based anti-aliasing should use the warped coordinate. The phase wraps at a period that depends on frequency, so it stays exact only while frequency is constant.

## Cost

Estimate: one fmod, one sine and one cosine per call.

## Reuse and origin

Adapted from Inferno `Transformation/Water.metal` by Paul Hudson and other authors (MIT, Copyright (c) 2023), preserved in `references/inferno`. Changes: returns coordinates rather than a SwiftUI distortion position; strength in coordinate units; each axis is displaced by a wave along the other axis (the original used the same axis, which only varies spacing and leaves straight lines straight). Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
