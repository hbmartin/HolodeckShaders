# Box Room

Ray exit intersection with an axis-aligned room and triangle-wave bounce paths inside it.

## Interface

```metal
float4 hdRoomHit(float3 ro, float3 rd, float3 halfExtents);
float3 hdBounceInBox(float3 start, float3 velocity, float3 halfExtents, float t);
```

`hdRoomHit` returns `xyz` = inward unit normal of the face the ray leaves through and `w` = distance to that exit point. `hdBounceInBox` returns a position inside ±`halfExtents` that moves at constant speed and reflects off the walls. No helper dependencies.

Canonical source: `snippets/box-room/code.metal`. Example: `snippets/box-room/example.metal`.

## Coordinates

Room space: the box is centred at the origin, so pass `ro - roomCentre`. `ro` must be inside the box and `rd` normalised; zero direction components are guarded. For a face with normal on axis i, use the other two components of the hit point as grid coordinates. `start` is the position at t = 0 and must lie inside the box; `velocity` is in units per second; `t` is seconds.

## Tuning

Shrink `halfExtents` by an object's radius so it never clips the walls. Give each object its own lane (centre plus extents) and different per-axis speeds (0.15–0.35 units/s reads as calm) to avoid clustering.

## Limitations

The exit test assumes the origin is inside the room. Bounces are mirror reflections with no collisions between objects. `hdBounceInBox` wraps whole and fractional seconds separately; the residual error at one day of runtime is about 0.003 units for typical speeds, below the visible threshold.

## Cost

Estimate: `hdRoomHit` is one vector division and two compares; `hdBounceInBox` two `fract` calls and an `abs` per axis.

Measured in context: the complete `holodeck-grid` scene took 1.15 ms median / 1.14 ms minimum GPU time on an Apple M2 Pro at 3840×2160, t = 3 s, 120 frames, local `bench` harness. Apple TV hardware was not measured.

## Reuse and origin

Original Holodeck implementation used by `shaders/holodeck-grid/body.metal`; inspired by the room and floating objects of holodeck-scene by Chris Lane Jones (reference `holodeck-scene`), no code copied. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
