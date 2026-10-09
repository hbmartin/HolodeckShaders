# Studio Material

Ray-marched sphere, analytical floor and studio reflections for metal finishes.

## Interface

```metal
float3 shadeMaterial(float2 p, float t, int kind);
```

Returns tone-mapped RGB. kind 0 is chrome, 1 brushed gold, 2 iridescent. Requires common and material.

Canonical source: `shared/material.metal`. Example: `snippets/studio-material/example.metal`.

## Coordinates

p is centered and height-normalized, Y upward. t is seconds. Camera, sphere and floor are built in.

## Tuning

Use kinds 0–2. Multiply t by 0.25–2 to change studio light motion; adapt code for geometry or roughness.

## Limitations

A complete scene recipe with fixed camera and geometry; it is not a general physically based material function.

## Cost

Estimate: up to 64 distance steps, plus exponential/power lighting calculations; no measured device benchmark.

## Reuse and origin

Derived from `shaders/chrome/body.metal`, `shaders/brushed-gold/body.metal`, `shaders/iridescent/body.metal`. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
