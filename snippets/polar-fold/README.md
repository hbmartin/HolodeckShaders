# Polar Fold

Fold a plane into mirrored angular sectors for kaleidoscope patterns.

## Interface

```metal
float2 hdPolarFold(float2 p, float sectors, float rotation);
```

Returns a folded float2 at the same radius. sectors is a sector count (use integer-valued floats); rotation is radians.

Canonical source: `snippets/polar-fold/code.metal`. Example: `snippets/polar-fold/example.metal`.

## Coordinates

Input p is centered on the symmetry origin, in any consistent planar units.

## Tuning

Sectors 3–16; rotation speed 0.01–0.3 radians/second. Sample a pattern using the returned coordinates.

## Limitations

Derivatives are discontinuous on fold seams and at the origin; fine patterns can alias.

## Cost

Estimate: one atan2, one sine and one cosine plus length/fract operations.

## Reuse and origin

Derived from `shaders/kaleidoscope/body.metal`. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
