# Rain Ripples

Expanding raindrop rings from three offset cell layers, with drops that move and skip from cycle to cycle.

## Interface

```metal
float hdRainRipples(float2 p, float t, float density);
```

Returns a 0..1 ring mask (not RGB). Each of three cell layers (offset by 1.33 cells) holds at most one drop per cell. A drop lives for two seconds: its ring grows to 0.27 cells, a faint inner echo follows at 60% of the radius, and both fade in over the first 8% of the cycle and out linearly. Every cycle a drop takes a new position and is skipped one time in four. Depends on `hash21` from `shared/common.metal`.

Canonical source: `snippets/rain-ripples/code.metal`. Example: `snippets/rain-ripples/example.metal`.

## Coordinates

p is any planar coordinate; the example passes the runtime's height-normalised p. density is cells per p unit, so `density = 4` gives four cells per screen height in each layer. Drop centres stay 0.3 cells from their cell edges and rings never exceed that margin, so no ring is clipped at a cell boundary. t is seconds. It is wrapped at 1024 s, exactly 512 drop cycles, and the cycle index used for hashing repeats at the same period, so the wrap is seamless.

## Tuning

- density 2–8 for a puddle seen from above; above 10 the rings get thin (see Limitations).
- Ring speed: scale t (for example `t * 0.7`) for slower drops; each layer's lifetime is 2 s at t scale 1.
- Use the mask as highlight light (example), as a height for normal perturbation, or to drive a small `hdSineWarp`-style displacement.
- Change `step(0.25, …)` to skip more or fewer drops.

## Limitations

Ring and echo widths (0.03 and 0.025 cells) shrink in screen space as density grows; at density 20 on a 720p preview they are under two pixels and start to alias. Overlapping rings from different layers sum and are clamped at 1. Drops are on a lattice, so very low densities can show a faint grid rhythm. The pattern cannot react to scene geometry; it is a flat surface mask.

## Cost

Estimate: three layers, each with four `hash21` calls, one length and four smoothsteps; no textures.

## Reuse and origin

Adapted from `rainDrops` in SwiftShaders `Water/WaterShader.metal` by Muhittin Camdali (MIT, Copyright (c) 2024, commit 4acb3a91), preserved in `references/swiftshaders`. Changes: ring mask output; shared `hash21`; per-cycle drop positions and skips; rings kept inside cells; inner echo ring; fade-in; seamless time wrap. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
