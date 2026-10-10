# Gradient Noise

Perlin-style 2D gradient noise in 0..1 with a quintic fade, built on the shared hash21.

## Interface

```metal
float2 hdGradientNoiseDir(float2 cell);   // unit gradient for an integer lattice cell
float hdGradientNoise2(float2 p);         // scalar field in [0, 1], mean 0.5
```

`hdGradientNoise2` returns a scalar field, not RGB. Each lattice corner gets a random unit gradient (angle from the shared `hash21`); the four corner dot products are blended with the quintic fade `6f^5 - 15f^4 + 10f^3`, so the field and its first and second derivatives are continuous. The raw ±sqrt(0.5) range is rescaled to exactly [0, 1]; most samples fall between 0.25 and 0.75. Depends on `hash21` from `shared/common.metal`.

Canonical source: `snippets/gradient-noise/code.metal`. Example: `snippets/gradient-noise/example.metal`.

## Coordinates

p is in lattice units: one unit is one noise cell. Scale the runtime's height-normalised p by 2–12 for broad to fine features. Zero crossings of the raw noise lie on lattice points, so the field is exactly 0.5 at every integer coordinate.

## Tuning

- Frequency: multiply p; sum two or three octaves (weights 0.5, 0.25, …) for richer detail, as the example does with two.
- Animation: add a circular drift `R * float2(cos(a), sin(a))` with `a = fmod(t * rate, 2π)` rather than an unbounded `t` offset, so long runs stay precise and loop seamlessly.
- Marble and veins: feed the noise into `sin()` of a coordinate and sharpen with `pow` (example).

## Limitations

The field is grid-aligned: the value is pinned to 0.5 on lattice points, which can show faint regularity in single-octave use. Rotate or offset octaves to hide it. It is not tileable. For a 3D or less grid-aligned field, see `simplex-noise-3d`; for cheaper hash-blended noise, the shared `noise2`.

## Cost

Estimate: four `hash21` calls and four sine/cosine pairs plus a quintic blend per sample, roughly twice the shared `noise2`. The example uses two samples per pixel.

## Reuse and origin

Adapted from `perlinNoise` in SwiftShaders `Noise/NoiseShader.metal` by Muhittin Camdali (MIT, Copyright (c) 2024, commit 4acb3a91), preserved in `references/swiftshaders`. Changes: the shared `hash21` replaces the sine hash, a quintic fade replaces the cubic one, and the output is rescaled to 0..1. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
