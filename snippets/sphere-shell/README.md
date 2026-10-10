# Sphere Shell

Analytic ray–sphere intersection, view fresnel and a closest-approach halo for translucent bubbles.

## Interface

```metal
float2 hdRaySphere(float3 ro, float3 rd, float radius);
float hdFresnel(float3 n, float3 v, float power);
float hdSphereHalo(float3 ro, float3 rd, float radius, float falloff);
```

`hdRaySphere` returns `(tNear, tFar)` along the ray, or `float2(-1.0)` when the ray misses; test `tFar > 0`. `tNear` is negative when the origin is inside the sphere. `hdFresnel` returns 0 when facing the viewer and 1 at grazing angles; it uses `abs(dot(n, v))`, so back faces seen from inside also work. `hdSphereHalo` returns 1 where the ray passes through the sphere and decays exponentially with the closest-approach distance outside it. All return scalars, not RGB. No helper dependencies.

Canonical source: `snippets/sphere-shell/code.metal`. Example: `snippets/sphere-shell/example.metal`.

## Coordinates

World space with the sphere centred at the origin: pass `ro - centre`. `rd` must be normalised. `n` is the unit surface normal (`hit / radius` for a centred sphere) and `v` the unit direction toward the viewer (`-rd`). Halo distance is measured in radii.

## Tuning

Fresnel power 1.5–3 for soft energy shells, 5–8 for thin rims. Halo falloff 5–8 for a tight bloom, 1.5–3 for a wide glow; combine two and multiply by a small intensity (0.01–0.05) before tonemapping.

## Limitations

The single-sample intersection has a hard silhouette; multiply by an analytic coverage such as `saturate((radius - closest) / (distance * pixelAngle))` for anti-aliasing (see `shaders/force-shield/body.metal`). The halo ignores occluders and is not a physical bloom.

## Cost

Estimate: `hdRaySphere` is two dot products and one square root; `hdFresnel` one `pow`; `hdSphereHalo` one length and one `exp`.

Measured in context: the complete `force-shield` scene (four reuse recipes plus two 3D simplex octaves on the front face and one on the back) took 1.94 ms median / 1.76 ms minimum GPU time on an Apple M2 Pro at 3840×2160, t = 3 s, 120 frames, local `bench` harness. Apple TV hardware was not measured.

## Reuse and origin

Original Holodeck implementation of widely known techniques, used by `shaders/force-shield/body.metal`; inspired by flow-shield-effect by Christian Ortiz (reference `flow-shield-effect`), no code copied. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
