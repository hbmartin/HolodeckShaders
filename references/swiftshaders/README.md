# SwiftShaders

MIT-licensed SwiftUI shaders by Muhittin Camdali (https://github.com/muhittincamdali/SwiftShaders). Upstream HEAD contains no shaders; this reference pins commit `4acb3a91`. The code appears machine-generated and was never verified to build upstream (duplicate stitchable names, Swift modifiers calling undefined functions), so treat it as technique material, not working code.

| Area | Class | Use here |
| --- | --- | --- |
| Voronoi (Cells, EdgeGlow, Crystal, Caustics, …) | Generators over input color | `voronoi` snippet |
| Noise (perlinNoise, fbmNoise, voronoiNoise) | Generators | `gradient-noise` snippet |
| Water (rainDrops, caustics, oceanWaves, …) | Generators/distortions | `rain-ripples` snippet |
| Raymarching (infiniteGrid, blackHole, tunnel, metaballs, clouds, terrain) | Generators | Not adapted (bugs, heavy, or covered by the studio raymarcher) |
| Fire, Particles, Electric, Hologram, Frost | Generators blending over input color | Not adapted |
| Blur, ChromaticAberration | Fake (color-only, cannot sample) | Not portable |
| Displacement, Barrel, Ripple, Wave, Pixelate, Glitch | Distortions | Not portable without a source image |
| Emboss, Mosaic, Neon, Sharpen, Sketch, Swirl, Kaleidoscope | Layer effects | Not portable |
