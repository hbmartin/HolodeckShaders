# Aurora Curtains

Three moving bands of colored light modulated by layered noise.

## Interface

```metal
float3 hdAuroraCurtains(float2 p, float t);
```

Returns additive RGB light. Requires fbm, noise2 and hash21 from common.

Canonical source: `snippets/aurora-curtains/code.metal`. Example: `snippets/aurora-curtains/example.metal`.

## Coordinates

p is centered and height-normalized, Y upward; t is seconds.

## Tuning

Multiply t by 0.25–2 for movement. Adapt band falloff 9–15 and the x ray frequency 35 to change softness and detail.

## Limitations

Tint interpolation can extrapolate at extreme aspect ratios; layered light can clip. Fine rays may alias.

## Cost

Estimate: six fbm evaluations per pixel (24 noise2 calls) plus three exponential evaluations. No measured performance claim.

## Reuse and origin

Derived from `shaders/aurora/body.metal`. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
