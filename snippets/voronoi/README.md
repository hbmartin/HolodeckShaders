# Voronoi F1/F2

Animated Voronoi (Worley) noise returning the distances to the nearest (F1) and second-nearest (F2) feature points. F1 gives cell shading; F2 − F1 gives a clean edge network for cracks, membranes and water caustics.

## Interface

```metal
float2 hdVoronoiF1F2(float2 p, float phase, float jitter);   // returns (F1, F2)
float2 hdVoronoiHash22(float2 p);                            // helper: two hashes in [0, 1)
```

Returns distances in cell units (F1 is at most about 1.1, F2 ≥ F1), not colors. No common helpers are required.

Edge mask: `edge = F2 - F1` is 0 on the cell borders. A pixel-stable line is `w = max(width, fwidth(edge)); exp(-edge / w) * (width / w)`; this widens lines that would be thinner than a pixel and dims them instead, so distant or minified lines fade rather than shimmer.

Caustics: warp `p` with a couple of low-frequency sines, evaluate two layers at different scales and opposite phases, and combine the line masks with `max(la, lb) + 0.6 * la * lb` (union plus a bright crossing term). Modulate by a slow noise "focus" field for patches of stronger light. See `hdShallowsCaustics` in `shaders/sunlit-shallows/body.metal`.

Canonical source: `snippets/voronoi/code.metal`. Example: `snippets/voronoi/example.metal`.

## Coordinates

`p` is in cell units: multiply aspect-correct screen coordinates by the desired cells per unit (for example `p * 6.0` for six cells per screen height). `phase` is an angle in radians; each feature point circles its cell center as it advances, so wrap it as `6.2831853 * fract(t / period)` for a seamless, precision-safe loop. `jitter` 0 gives a regular square grid; 1 gives fully irregular cells.

## Tuning

- Scale 3–10 cells per screen height for caustics; 15–40 for fine crackle.
- `jitter` 0.7–1.0 for organic cells; lower values make tiling more visible.
- Line width 0.03–0.08 cell units for caustic strands.

## Limitations

The search covers only the 3×3 neighborhood, which is exact while each point stays within 0.35 × jitter of its cell center (the radius used here). Larger custom offsets can produce small seam errors. F2 − F1 is a cell-space measure, so edge width varies slightly with cell size. No cell ID is returned; hash `floor(p)` plus the winning offset if you need one.

## Cost

Measured: in `shaders/sunlit-shallows` two evaluations per floor pixel (about 60% of the screen) cost about 1.1 ms at 3840×2160 on an Apple M2 Pro, versus 2.1 ms with the original per-cell `sin` animation. Each call runs nine hashes, nine 2D rotations and nine distances.

## Reuse and origin

Adapted from SwiftShaders by Muhittin Camdali (https://github.com/muhittincamdali/SwiftShaders, commit 4acb3a91, `Sources/SwiftShaders/Shaders/Voronoi/VoronoiShader.metal`; reference copy in `references/swiftshaders/`), MIT License, Copyright (c) 2024 Muhittin Camdali. That upstream code was never verified to build. Changes: the sin-based hash was replaced with a Hoskins hash, jitter is centered on the cell, the per-cell `sin` animation became a rotation of a random vector, and the scale and time arguments were folded into the inputs. Keep the MIT notice when adapting. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
