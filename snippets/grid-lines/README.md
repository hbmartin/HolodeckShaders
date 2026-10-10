# Grid Lines

Box-filtered grid line mask that stays stable from close-up to grazing distance.

## Interface

```metal
float hdGridLine(float2 coord, float spacing, float thickness, float2 footprint);
float hdGridLine(float2 coord, float spacing, float thickness, float footprint);
```

Returns 0–1 line coverage (not RGB) for lines every `spacing` units along both axes. Coverage is the exact box-filter integral of the line pulse train over the pixel footprint, so distant lines converge to their mean coverage instead of shimmering. The float overload uses an isotropic footprint. No helper dependencies.

Canonical source: `snippets/grid-lines/code.metal`. Example: `snippets/grid-lines/example.metal`.

## Coordinates

`coord`, `spacing`, `thickness` and `footprint` share units (for example world units on a wall). `footprint` is the size of one pixel along each axis: `fwidth(coord)` in uniform control flow, or `fwidth(hitPosition)` components for ray-traced surfaces, which stays continuous across room corners where per-face coordinates would jump.

## Tuning

Thickness 2–4% of the spacing for fine lines, 1.5–2% of a coarse spacing that is a multiple of the fine one. Combine a dim fine grid with a bright coarse grid, then fade with distance.

## Limitations

Box filtering is not a perfect low-pass, so faint moiré can remain at extreme grazing angles. Line centres are at integer multiples of `spacing`; offset `coord` to shift them. Derivative-based footprints are undefined inside non-uniform branches.

## Cost

Estimate: per call two floor/fract pairs per axis and a division; no loops or textures. holodeck-grid calls it twice per pixel.

Measured in context: the complete `holodeck-grid` scene took 1.15 ms median / 1.14 ms minimum GPU time on an Apple M2 Pro at 3840×2160, t = 3 s, 120 frames, local `bench` harness. Apple TV hardware was not measured.

## Reuse and origin

Original Holodeck implementation of the box-filtered pulse-train technique, used by `shaders/holodeck-grid/body.metal`; inspired by the amber grid walls of holodeck-scene by Chris Lane Jones (reference `holodeck-scene`), no code copied. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
