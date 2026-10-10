# Hex Grid

Hexagonal cell lookup, anti-aliased borders, sparse per-cell twinkles and a seamless hex lattice on a sphere.

## Interface

```metal
float4 hdHexCell(float2 p);
float hdHexEdge(float2 local, float width, float footprint);
float hdHexEdge(float2 local, float width);
float hdCellFlash(float2 cellId, float t, float rate);
float4 hdSphereHexCell(float3 n, float cellsPerEdge);
```

`hdHexCell` returns `xy` = offset from the cell centre and `zw` = an integer cell id (twice the centre x, row index). `hdHexEdge` returns a 0–1 mask that is 1 on cell borders; the three-argument form takes an explicit anti-aliasing footprint, the two-argument form derives it with `fwidth`. `hdCellFlash` returns a sparse, smooth 0–1 twinkle per cell. `hdSphereHexCell` returns the same layout as `hdHexCell` for a unit direction, with `zw` a cell key that both halves of seam-crossing cells share. Requires `hash21` from common.

Canonical source: `snippets/hex-grid/code.metal`. Example: `snippets/hex-grid/example.metal`.

## Coordinates

Planar lattice units: neighbouring centres are 1 apart (pointy-top cells, inradius 0.5). Scale your coordinates to set the cell size. `width` and `footprint` are in lattice units; `footprint` is the size of one pixel. `hdSphereHexCell` takes a unit vector (rotate it to spin the lattice) and `cellsPerEdge` cells per quarter great circle. `t` is seconds and `rate` is twinkle chances per second.

## Tuning

Border width 0.02–0.06. Twinkle rate 0.1–0.5; edit the 0.93 threshold in `hdCellFlash` for density. Use integer `cellsPerEdge` 6–16 on spheres. For a footprint on a sphere viewed from distance `d`, use `d * pixelAngle * cellsPerEdge / (pi / 2) / max(facing, 0.12)` (see `shaders/force-shield/body.metal`).

## Limitations

The sphere mapping is an angle-weighted octahedral projection; its triangle edges are lattice mirror lines, so the lattice is continuous, but six square cells sit on the coordinate axes, cell size varies by up to about 25%, and cells near those axis points stretch up to about 1.7:1 (measured numerically over the octant). Non-integer `cellsPerEdge` creates seams. The two-argument `hdHexEdge` uses screen-space derivatives and must run in uniform control flow (not inside a per-pixel hit branch). When the footprint approaches a cell, borders fade to their mean coverage instead of aliasing.

## Cost

Estimate: `hdHexCell` is two floor/fract pairs and a compare; `hdHexEdge` a few ALU operations; `hdCellFlash` two hashes; `hdSphereHexCell` adds three `asin` calls. No textures or loops.

Measured in context: the complete `force-shield` scene (four reuse recipes plus two 3D simplex octaves on the front face and one on the back) took 1.94 ms median / 1.76 ms minimum GPU time on an Apple M2 Pro at 3840×2160, t = 3 s, 120 frames, local `bench` harness. Apple TV hardware was not measured.

## Reuse and origin

Original Holodeck implementation used by `shaders/force-shield/body.metal`; the energy-shield idea was inspired by flow-shield-effect by Christian Ortiz (reference `flow-shield-effect`), but no code was copied. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
