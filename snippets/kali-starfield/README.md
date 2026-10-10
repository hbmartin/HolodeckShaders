# Kali Starfield

Radial warp-speed streaks from a Kali-style fractal fold (`p = abs(p) / dot(p, p) * k - c`) integrated along a short ray. Returns additive RGB light in blue, violet and teal.

## Interface

```metal
float3 hdKaliStarfield(float2 uv, float travel, int steps, float jitter);
```

Returns unbounded RGB light (typically 0–1.5, with brief brighter flashes when the path crosses dense fold regions). It is light, not a finished color: clamp or tone-map, then square (or apply another sRGB-style decode) to match the original Shadertoy look on Holodeck's sRGB target. No common helpers are needed by the function itself.

Canonical source: `snippets/kali-starfield/code.metal`. Example: `snippets/kali-starfield/example.metal`. Finished scene: `shaders/warp-speed/body.metal`.

## Coordinates

`uv` is centered and aspect-correct; `p * 2.0` reproduces the original framing (vertical range about -1 to 1). `travel` is the camera's distance along z in fold units. The internal wander path is periodic in `travel` with period 52 (x wander period 4, y wander period 2.6, z repeat 1), so wrap time as `travel = offset + (t - P * floor(t / P)) * speed` with `P = 52 / speed` for a seamless, precision-safe loop. `jitter` in [0, 1) offsets the first ray sample; pass a per-pixel value such as interleaved gradient noise of `pixel`, offset per frame (as `shaders/warp-speed` does) so the residual grain does not sit as a fixed pattern over moving imagery.

## Tuning

- `speed` 0.03–0.06 travel units per second reads as brisk ambient travel; the original ran at 0.116.
- `steps` 8–12 with jitter is the practical range; 100 unjittered steps match the original exactly but cost about 10 times more. Fewer steps add grain; no jitter turns grain into dotted streaks.
- The inner fold count (10) defines the fractal's character. Changing it (for example to 8) produces a visibly different, more symmetric pattern.
- Start `travel` near 0.45 to avoid opening on the bright flash around travel 0.

## Limitations

The fold is chaotic, so reduced steps cannot reproduce the original's fine sparkle; it becomes static-pattern grain that shimmers as the field moves. Dense regions overexpose briefly. The output is radially symmetric around the screen center only; there is no camera steering.

## Cost

Measured: about 4.2 ms per frame at 3840×2160 on an Apple M2 Pro with `steps = 10` (the `shaders/warp-speed` configuration); 8 steps measured about 3.4 ms. Cost scales with `steps × 10` fold iterations per pixel plus one `pow` per step. Apple TV performance is unverified.

## Reuse and origin

Derived from Dave Hoskins' "Warp Speed 2" (https://www.shadertoy.com/view/4tjSDt, 2015), itself a fork of his "Warp speed" (https://www.shadertoy.com/view/Msl3WH) using Kali's fractal folding. Licensed CC BY-NC-SA 3.0: anything adapted from this function must keep that license and attribution. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
