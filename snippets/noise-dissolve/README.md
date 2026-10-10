# Noise Dissolve

Threshold a noise value into a visibility mask with a bright burning edge for materialize and dissolve effects.

## Interface

```metal
float2 hdDissolve(float noiseValue, float reveal, float width);
```

Returns `x` = visibility mask (0–1) and `y` = edge glow mask on the visible side of the threshold. Multiply your light by `x` and add an edge colour times `y`. No helper dependencies.

Canonical source: `snippets/noise-dissolve/code.metal`. Example: `snippets/noise-dissolve/example.metal`.

## Coordinates

`noiseValue` must be in 0–1 (any smooth field works: `fbm`, `noise2`, a height gradient or a blend of them). `reveal` 0 hides everything and 1 shows everything; both ends are exact because the threshold range is padded by `width`. `width` is in noise units.

## Tuning

Width 0.02–0.08. Mix a spatial gradient into the noise (for example 0.55 × height + 0.45 × noise) to sweep the effect in one direction. Drive `reveal` with smoothstep ramps of a wrapped time (`fmod(t, period)`) for long-running cycles.

## Limitations

Edge thickness depends on the noise gradient: flat noise regions produce wide bands. The mask is not anti-aliased beyond the smoothstep; very small widths can alias on high-frequency noise.

## Cost

Estimate: two smoothsteps and a mix, plus whatever noise you supply. force-shield only evaluates it during the dissolve part of its 67-second cycle.

## Reuse and origin

Original Holodeck implementation used by `shaders/force-shield/body.metal`; inspired by the materialize effect of flow-shield-effect by Christian Ortiz (reference `flow-shield-effect`), no code copied. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
