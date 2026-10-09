# Layered Stars

Three independently drifting star layers with seeded colors and twinkle.

## Interface

```metal
float3 hdLayeredStars(float2 p, float t);
```

Returns additive RGB light, potentially above 1 where layers overlap. Requires hash21 from common.

Canonical source: `snippets/layered-stars/code.metal`. Example: `snippets/layered-stars/example.metal`.

## Coordinates

p is centered and height-normalized, Y upward; t is seconds.

## Tuning

Multiply p by 0.5–2 for density/scale and t by 0.25–2 for drift/twinkle speed. Adapt seed threshold 0.78 for density.

## Limitations

Subpixel stars can flicker at low resolution; cell-based points are not a physical star catalog.

## Cost

Estimate: three layers, each with three hashes and an exponential. No textures.

## Reuse and origin

Derived from `shaders/starfield/body.metal`. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
