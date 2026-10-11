# Rune Glyph

Random four-stroke "runes" that read convincingly as alien or Matrix-style symbols. Each stroke joins two points snapped to a 2×3 grid, and the four strokes are forced to touch the four sides of the glyph box so every symbol fills its cell.

## Interface

```metal
float hdRuneGlyph(float2 uv, float2 seed);      // stroke mask in [0, 1]
float hdRuneDistance(float2 uv, float2 seed);   // distance to the nearest stroke, box units
float4 hdRuneHash42(float2 p);                  // helper: four hashes in [0, 1)
```

`hdRuneGlyph` returns a scalar mask (stroke half-width 0.1 of the box), not RGB. Use `hdRuneDistance` for custom stroke widths or glows; the Matrix scene adds `0.2 * smoothstep(0.4, 0.0, d)` as a halo for the leading symbols. No common helpers are required.

Canonical source: `snippets/rune-glyph/code.metal`. Example: `snippets/rune-glyph/example.metal`. Finished scene: `shaders/matrix-corridor/body.metal`.

## Coordinates

`uv` is the position inside the glyph box, 0–1 on both axes (the box may be any aspect; the Matrix strips use 0.10 × 0.15 units). `seed` selects the symbol: strokes use `seed`, `seed + 1`, `seed + 2` and `seed + 3`. Keep seeds small and integral (for example a symbol index and a time tick, both wrapped below 4096); huge or fractional seeds reduce hash quality.

## Tuning

- Change the stroke width with `smoothstep(w, 0.0, d)`; 0.06–0.15 reads well.
- Animate by bumping the seed on a bounded timer for flickering code. Wrap time before multiplying; choose a period whose product with the rate is a multiple of the 4096-seed period. The example's 1.5 Hz rate wraps at 8192 seconds. Matrix Corridor uses rates quantized to 1/32 Hz and a 131072-second clock independent of its camera route, with integer whole-tick arithmetic.
- Change `float4(2, 3, 2, 3)` to snap to a different grid (for example 3×3 for denser symbols); remove the forced edges for sparser, smaller glyphs.

## Limitations

Point-sampled: glyphs smaller than about 8 pixels alias and shimmer. Strokes can coincide, and about 1 in 50 seeds produces a sparse glyph. The glyph set is random, not a designed alphabet. Bounded timer arithmetic cannot restore precision already lost in the incoming float time uniform; long-uptime samples do not establish smooth continuous playback.

## Cost

Estimate: four 4-output hashes and four segment distances per evaluation (about 130 ALU operations). In `shaders/matrix-corridor` glyphs are evaluated only for ray hits on rain strips, a few times per pixel. Measured at 3840×2160 on an Apple M2 Pro in a 20-step version of that scene: replacing the glyph with a constant saved about 0.6 ms of 4.9 ms.

## Reuse and origin

Derived from "runes" by FabriceNeyret2 (https://www.shadertoy.com/view/4ltyDM), based on "runes" by otaviogood (https://shadertoy.com/view/MsXSRn), with the segment distance from https://www.shadertoy.com/view/4dcfW8, as modified in the ghostty-shaders `inside-the-matrix.glsl` (@pkazmier). Licensed CC BY-NC-SA 3.0 (Shadertoy default for this lineage): adaptations must keep that license and these credits. The sin-based hash was replaced with a Hoskins hash. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.

The hash adaptation also uses David Hoskins' "Hash without Sine", MIT, Copyright (c) 2014 David Hoskins; see `references/hoskins-hash`. Retain its complete notice with the hash code.
