# Dot Curtain

Polka-dot or diamond halftone wipe mask that grows diagonally from the top-left as amount goes from 0 to 1.

## Interface

```metal
float hdDotCurtain(float2 cellPos, float2 uv01, float amount, bool diamond, float aa);
```

Returns a 0..1 mask: 0 shows the outgoing content, 1 the incoming. A pixel is revealed when its distance to its dot centre (Euclidean, or L1 when `diamond` is true) plus `uv01.x + uv01.y` falls below the sweep reach. amount is clamped to [0, 1]; the reach is scaled so the mask is exactly 0 everywhere at amount 0 and exactly 1 at amount 1. No helper dependencies.

Canonical source: `snippets/dot-curtain/code.metal`. Example: `snippets/dot-curtain/example.metal`.

## Coordinates

- cellPos: position in dot-cell units; each unit square holds one dot centred at its middle. The example uses `p * 14.0` (14 dots per screen height).
- uv01: the sweep coordinate, 0..1 across the screen with (0, 0) at the top-left, as in SwiftUI. From the runtime's p this is `float2(p.x / aspect + 0.5, 0.5 - p.y)`; the example assumes 16:9 (`p.x * 0.5625`). Flip or swap components to change the sweep direction.
- aa: edge softness in cell units; pass `fwidth(cellPos.y)` for one-pixel anti-aliasing at any resolution.

## Tuning

- Dot density 8–30 cells per screen height; larger dots read as a curtain, smaller ones as halftone.
- Ease amount (for example with `smoothstep`) for a calmer reveal; 4–8 seconds per sweep suits a TV.
- Increase aa (for example `0.08`) for soft, glowing dot edges.

## Limitations

The sweep is a fixed diagonal sum, so the reveal front is always at 45° in uv01 space (steeper or shallower on screen, depending on aspect). With non-16:9 screens the example's uv01 approximation reveals the far corner slightly early or late. Without the aa term the original hard threshold aliases badly on moving dots.

## Cost

Estimate: one fract, one length (or two abs), one smoothstep per call.

## Reuse and origin

Adapted from Inferno's Circle Wave transition (`Transition/CircleWave.metal`) and its Diamond Wave variant by Paul Hudson and other authors (MIT, Copyright (c) 2023), both based on gl-transitions PolkaDotsCurtain by bobylito (MIT). The circle source is preserved in `references/inferno`; the diamond variant uses the L1 distance as Inferno's Diamond transitions do (not imported here). Changes: anti-aliased mask output, selectable diamond metric and an exact 0/1 reach. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.

The secondary MIT notice is preserved in `references/gl-transitions-polka`; copy it alongside the Inferno notice.
