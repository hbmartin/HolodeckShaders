# Value Noise

Smooth deterministic 2D value noise for grain, mist and surface variation.

## Interface

```metal
float hash21(float2 p); float noise2(float2 p);
```

hash21 returns a deterministic scalar in [0,1). noise2 smoothly interpolates four cell hashes, returning [0,1].

Canonical source: `shared/common.metal`. Example: `snippets/value-noise/example.metal`.

## Coordinates

Input p is in noise-cell units; noise has no built-in time or pixel dependence.

## Tuning

Scale normalized coordinates by 2–40 for broad clouds through fine grain. Add time * 0.01–0.2 for drift.

## Limitations

Value noise is not gradient or simplex noise. Cell interpolation can show grid structure at low frequencies.

## Cost

Estimate: four hash evaluations per noise2 call; no textures or loops.

## Reuse and origin

Derived from `shaders/aurora/body.metal`, `shaders/starfield/body.metal`. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
