# Impact Ripple

Noisy rings expanding along a sphere surface from deterministic impact points.

## Interface

```metal
float2 hdImpact(float3 n, float3 hitDir, float age, float duration);
float4 hdScheduledHit(float t, float slot, float period);
```

`hdImpact` returns `x` = ring mask (thin bright front with a short faint inner wake) and `y` = flash mask around the impact point; both are 0 outside `0 <= age < duration`. `hdScheduledHit` returns `xyz` = unit impact direction and `w` = age in seconds within the slot's current period, giving one hit per period per slot without input events. Requires `noise2` and `hash21` from common.

Canonical source: `snippets/impact-ripple/code.metal`. Example: `snippets/impact-ripple/example.metal`.

## Coordinates

`n` and `hitDir` are unit directions from the sphere centre. The ring radius is a geodesic angle (`acos(dot(n, hitDir))`) that eases out to about 2.4 radians. Scheduled directions are biased toward +z (the camera side when the camera looks down -z) and slightly upward. `t`, `age`, `period` and `duration` are seconds.

## Tuning

Duration 2–4 s; period at least the duration. Use two or three slots with different periods (for example 8.5, 11.6, 14.7 s) and add a time offset to choose which hit appears in a preview frame. Use the zone mask to light whole cells (threshold it against a per-cell hash) and the ring mask for additive light. Edit the 2.4 radian reach, width and wobble constants for other shells.

## Limitations

Not a physical wave; rings pass through the back of the sphere and are visible through translucent fronts. `acos` loses precision very close to the impact point, which is hidden by the flash. Direction bias is fixed to +z; rotate the result for other cameras.

## Cost

Estimate: `hdImpact` is one `acos`, one value-noise lookup and three `exp` calls per active impact; skip inactive slots with a branch on the age, which is uniform across the frame. `hdScheduledHit` is two hashes and four trigonometric calls, independent of the pixel.

Measured in context: the complete `force-shield` scene (four reuse recipes plus two 3D simplex octaves on the front face and one on the back) took 1.94 ms median / 1.76 ms minimum GPU time on an Apple M2 Pro at 3840×2160, t = 3 s, 120 frames, local `bench` harness. Apple TV hardware was not measured.

## Reuse and origin

Original Holodeck implementation used by `shaders/force-shield/body.metal`; the click-to-impact idea of flow-shield-effect by Christian Ortiz (reference `flow-shield-effect`) was replaced with a deterministic schedule. No code copied. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
