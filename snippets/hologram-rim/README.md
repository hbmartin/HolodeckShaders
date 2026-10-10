# Hologram Rim

Blueprint hologram light: translucent deep-blue body, crisp amber fresnel outline and drifting contour lines.

## Interface

```metal
float3 hdHologramRim(float3 n, float3 v, float3 position, float t, float footprint);
float3 hdHologramRim(float3 n, float3 v, float3 position, float t);
```

Returns RGB light, not a complete colour or coverage. Composite it over the background with an opacity of about 0.75 (`background * (1 - alpha) + light`); peaks stay near 1.2 so a `1 - exp(-x)` tonemap keeps the amber saturated. The four-argument form derives the contour anti-aliasing width from `fwidth(position.y)` and must run in uniform control flow; inside per-pixel hit branches pass `footprint` explicitly. No helper dependencies.

Canonical source: `snippets/hologram-rim/code.metal`. Example: `snippets/hologram-rim/example.metal`.

## Coordinates

`n` is the unit surface normal, `v` the unit direction toward the viewer, `position` the shading point in the space where contour slices should stay fixed (object-local space makes them rotate with the object), `t` seconds and `footprint` one pixel in `position` units (for example `distance * pixelAngle / max(facing, 0.2)`).

## Tuning

Contour spacing is 0.2 units (`position.y * 5.0`); the outline band is `smoothstep(0.66, 0.86, fresnel)`. Values are linear light for an sRGB target: blue body (0.012, 0.02, 0.32), amber outline (1.0, 0.5, 0.03). Darken the body at grazing angles to keep the amber/blue boundary from reading pink.

## Limitations

Fresnel outlines suit curved surfaces; flat faces have constant fresnel, so add explicit edge lines for polytopes (as `holodeck-grid` does). There is no lighting model beyond one fixed key direction.

## Cost

Estimate: one `smoothstep` for the outline, one for the contours, a `fract` and a handful of multiplies; no `pow` or textures.

Measured in context: the complete `holodeck-grid` scene took 1.15 ms median / 1.14 ms minimum GPU time on an Apple M2 Pro at 3840×2160, t = 3 s, 120 frames, local `bench` harness. Apple TV hardware was not measured.

## Reuse and origin

Original Holodeck implementation used by `shaders/holodeck-grid/body.metal`. The look was inspired by Allen White's "Blueprint Mode" starship breakdown on ArtStation (reference `starship-blueprint-artstation`, viewed for mood only); no code, imagery or ship designs were copied. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
