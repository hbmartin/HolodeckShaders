# Ember Sparks

One layer of orange sparks, one per lattice cell, drifting diagonally upward. Each spark spins slowly around its cell center, flutters, has an elongated hot core plus a soft bloom, and fades in and out at its own random heights. Sum a few layers at slightly different scales for depth.

## Interface

```metal
constant float hdEmberPeriod;   // 7680 s loop
float3 hdEmberLayer(float2 uv, float2 screen, float phase, float layerSeed);
```

Returns additive RGB light (core peaks at about 1.5 in red; bloom up to 0.6). Helpers in the same file: `hdEmberWrap`, `hdEmberHash4` (four random values per cell on a 256-cell periodic lattice), `hdEmberDrift` and `hdEmberRotate`. No common helpers are required.

Canonical source: `snippets/ember-sparks/code.metal`. Example: `snippets/ember-sparks/example.metal`. Finished scene: `shaders/ember-drift/body.metal`.

## Coordinates

`uv` is in lattice cells (one spark per cell): the example uses `p * 2.8125 * 1.4`, which gives about 4 cells per screen height. `screen` is the original sketch's screen position (`p * 2.8125`, vertical range about -1.4 to 1.4) and only drives the per-spark appear/disappear heights. `phase = (t mod 7680) / 7680` is the loop fraction: every sampling drift (`n/3 * (0.7, -1.0)` lattice cells per second), spin (whole turns per loop, within ±1 rad/s) and flutter (about 1.4 changes per second) completes whole cycles per loop, so the motion is seamless and stays precise at large `t`. The drift is added to Y-up sampling coordinates, so visible sparks move in the opposite direction, left and upward. `layerSeed` is any small number (layer index) that offsets the lattice.

## Tuning

- Layer scale 1.0–1.6 sets density and spark size together; 4 layers at 1.4 × 1.05^i approximate the original's 8 layers.
- `size` (0.0025 in the original, 0.0035 here) and `bloomRadius` set spark and halo size; keep `reach` below about 0.14 cells or sparks near cell edges get clipped (the spin radius is 0.5 × the hash offset for this reason).
- Change the drift by passing other integer `n` to `hdEmberDrift`; speed is n/3 cells per second.
- Multiply the result by exposure, then tone-map or clamp. Square the clamped result to match the sRGB-display look of the original.

## Limitations

Only the spark's own cell is evaluated, so sparks cannot cross cell borders; the spin radius and bloom limits keep them inside. Drift speeds are quantized to thirds of a cell per second and spins to whole turns per 7680 s loop. The spark color is fixed orange; tint the result for other palettes.

## Cost

Measured: the four-layer spark loop in `shaders/ember-drift` costs about 1.8 ms per frame at 3840×2160 on an Apple M2 Pro (whole scene 3.6 ms, scene without sparks 1.8 ms; the split is approximate because it comes from disabling parts). Each layer is one 4-output hash and a sincos for every pixel; pixels farther than `reach` from the cell's spark exit early, so the flutter hashes and distance math run on only a few percent of pixels.

## Reuse and origin

Derived from "Sparks from fire" by Jan Mróz (jaszunio15), https://www.shadertoy.com/view/wl2Gzc, CC BY 3.0, via Alex Sherwin's Ghostty adaptation (`sparks-from-fire.glsl`). Keep the attribution when adapting. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
