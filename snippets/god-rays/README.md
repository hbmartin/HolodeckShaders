# God Rays

Soft light shafts fanning out from a point above the frame, for underwater scenes, forests or dusty interiors. The shafts drift and sway slowly and loop seamlessly every 600 seconds.

## Interface

```metal
float hdGodRays(float2 p, float2 source, float t);
```

Returns a scalar mask in [0, 1] (most of the screen is 0; shaft cores approach 1). Multiply by a light color and add it. Requires `noise2` from common.

Canonical source: `snippets/god-rays/code.metal`. Example: `snippets/god-rays/example.metal`. Finished scene: `shaders/sunlit-shallows/body.metal`.

## Coordinates

`p` is centered, height-normalized and Y-up. `source` is the point the shafts converge on, in the same units, normally above the top edge (y > 0.5). An x offset slants the shafts. The pattern is a function of the angle from `source`, so shafts stay straight and widen with distance. `t` is seconds; the function wraps it internally.

## Tuning

- Move `source` higher (y 1.2–2.5) for more parallel shafts, lower (0.6–1.0) for a stronger fan.
- The noise frequencies 9 and 23 set shaft count and width; the `smoothstep(0.42, 0.85, …)` thresholds set coverage and softness.
- Fade with depth by multiplying by `smoothstep(bottom, top, p.y)`, and skip the region above a water surface.

## Limitations

Screen-space only: shafts do not respond to occluders or scene depth. The pattern is periodic in time (600 s), and its angle-based coordinate becomes singular at `source`, so keep the source off-screen.

## Cost

Estimate: two `noise2` evaluations, one division and one `sin` per pixel. It is a small share of `shaders/sunlit-shallows` (whole scene about 2.6 ms at 3840×2160 on an Apple M2 Pro).

## Reuse and origin

Original Holodeck implementation written for `shaders/sunlit-shallows`. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
