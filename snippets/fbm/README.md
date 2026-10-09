# Fractal Brownian Motion

Four-octave layered noise for clouds, nebulae and domain warping.

## Interface

```metal
float fbm(float2 p);
```

Returns scalar layered noise in [0,0.9375]; four octave amplitudes are 0.5, 0.25, 0.125, 0.0625. Requires noise2 and hash21 in common.

Canonical source: `shared/common.metal`. Example: `snippets/fbm/example.metal`.

## Coordinates

Input uses noise-cell units; transform height-normalized coordinates before calling.

## Tuning

Scale 1–10 for clouds; time drift 0.01–0.1. For domain warping offset p by two independently sampled fbm values.

## Limitations

Fixed octave count and internal transform. Domain warping multiplies the number of evaluations.

## Cost

Estimate: four noise2 calls, each evaluating four hashes.

## Reuse and origin

Derived from `shaders/aurora/body.metal`, `shaders/starfield/body.metal`. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
