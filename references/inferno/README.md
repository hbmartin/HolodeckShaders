# Inferno

MIT-licensed SwiftUI Metal shaders by Paul Hudson and contributors (https://github.com/twostraws/Inferno, pinned to `a40c7a0`). The upstream LICENSE (kept in `original/`) credits ports: Circle/Circle Wave/Diamond/Diamond Wave after bobylito's gl-transitions PolkaDotsCurtain; Crosswarp (Eke Péter); Radial (Xaychru/gre); Swirl (Sergey Kosarevsky/gre); Wind (gre); Genie (altaha-ansari, port by Zachary Gorak). The README additionally credits Shimmer to @bwhtmn after markiv/SwiftUI-Shimmer.

Only the files used for adaptation are preserved. Classification of the full upstream tree (33 shaders):

| Class | Shaders | Use here |
| --- | --- | --- |
| Generator | LightGrid, Sinebow, CircleWaveTransformation | `light-grid`, `sinebow-lines` snippet, `sonar-pulse` |
| Generator (thin) | AnimatedGradientFill, RainbowNoise, WhiteNoise, GradientFill | Not adapted; shared `hash21`/`palette` cover them |
| Color transform | Checkerboard, Interlace, Infrared, Shimmer, Recolor, InvertAlpha, Passthrough | `color-ramps` snippet (Infrared, Shimmer HSL) |
| Distortion | Water, Wave, RelativeWave | `sine-warp` snippet (Water) |
| Layer effect | Emboss, ColorPlanes, SimpleLoupe, WarpingLoupe, Bubble, VariableGaussianBlur | Not portable: needs layer sampling |
| Transition | Circle, CircleWave, Diamond, DiamondWave, Crosswarp, Radial, Swirl, Wind, Pixellate, Genie | `dot-curtain` snippet (polka-dot family); others need two images |

Porting notes: SwiftUI `position` matches Holodeck `pixel` orientation (y down) but is in points; convert sizes to height-relative units. Port `half` math to `float` — half precision steps visibly after roughly 30 minutes of `time`. Drop `color.a` masks.
