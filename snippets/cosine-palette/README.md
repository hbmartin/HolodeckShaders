# Cosine Palette

A periodic RGB palette for vivid continuous color transitions.

## Interface

```metal
float3 palette(float x);
```

Returns RGB in [0,1]. x is a phase in cycles; palette(x+1) equals palette(x).

Canonical source: `shared/common.metal`. Example: `snippets/cosine-palette/example.metal`.

## Coordinates

Scalar phase is independent of coordinate convention. Convert a distance or noise field into phase.

## Tuning

Multiply phase by 0.1–2 to control color frequency; time * 0.005–0.1 controls cycling.

## Limitations

This fixed palette is saturated and may be unsuitable for restrained colors; adapt its amplitude/offset explicitly.

## Cost

Estimate: three cosine evaluations per call; no textures or loops.

## Reuse and origin

Derived from `shaders/plasma/body.metal`, `shaders/waves/body.metal`, `shaders/kaleidoscope/body.metal`. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
