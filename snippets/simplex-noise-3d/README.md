# Simplex Noise 3D

Textureless 3D simplex noise returning roughly -1 to 1.

## Interface

```metal
float hdSimplex3(float3 v);
```

Returns a smooth scalar noise value in approximately -1..1 (not RGB). Internal helpers `hdMod289`, `hdPermute` and `hdTaylorInvSqrt` are part of the recipe and must be copied with it. No common helpers required.

Canonical source: `snippets/simplex-noise-3d/code.metal`. Example: `snippets/simplex-noise-3d/example.metal`.

## Coordinates

Any 3D domain; one feature is roughly one unit. The lattice repeats every 289 units along the (1,1,1) diagonal, so animating with `v - fmod(t * speed, 289.0)` (subtracting a scalar from all components) wraps seamlessly and keeps long-running inputs small. Rotate the domain to choose which world direction that drift follows (see `shaders/force-shield/body.metal`).

## Tuning

Scale the input by 1–10 for feature size; sum two or three octaves with halving amplitude; use `1 - abs(n)` for ridged filaments or `smoothstep` for soft shimmer.

## Limitations

Gradient noise, not tileable along arbitrary axes. Precision degrades for large inputs; wrap time as described above. Output may slightly exceed ±1.

## Cost

Estimate: roughly 80–100 ALU operations per call (three permutation rounds, four corner contributions), no textures or loops. force-shield uses two calls on the front face and one on the back face of each covered pixel.

Measured in context: the complete `force-shield` scene (four reuse recipes plus two 3D simplex octaves on the front face and one on the back) took 1.94 ms median / 1.76 ms minimum GPU time on an Apple M2 Pro at 3840×2160, t = 3 s, 120 frames, local `bench` harness. Apple TV hardware was not measured.

## Reuse and origin

Metal port of `src/noise3D.glsl` from Ashima Arts webgl-noise by Ian McEwan and Stefan Gustavson (MIT; preserved under `references/ashima-webgl-noise`). Keep the attribution comment wherever the code is copied: `// Simplex noise: Copyright (C) 2011 Ashima Arts (Ian McEwan, Stefan Gustavson). MIT License: https://github.com/ashima/webgl-noise`. Used by `shaders/force-shield/body.metal`. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
