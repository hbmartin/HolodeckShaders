# Color Ramps

Heat-map ramp plus HSL and HSV conversions for remapping scalars and adjusting hue, saturation or lightness.

## Interface

```metal
float3 hdHeatRamp(float x);       // blue -> yellow -> red
float3 hdRgbToHsl(float3 rgb);    // returns (hue 0..1, saturation, lightness)
float3 hdHslToRgb(float3 hsl);    // hue wraps, so cycling hues need no fmod
float3 hdHsvToRgb(float3 hsv);    // (hue 0..1 wrapping, saturation, value)
```

All four return or accept RGB in [0,1] for in-range inputs. `hdHeatRamp` clamps x to [0,1] and is linear between the three stops (0 blue, 0.5 yellow, 1 red), matching Inferno's Infrared mapping of luminance. No helper dependencies.

Canonical source: `snippets/color-ramps/code.metal`. Example: `snippets/color-ramps/example.metal`.

## Coordinates

Scalar and colour-space only; independent of the screen coordinate convention. The ramps and conversions treat RGB as display-referred values, as the Inferno originals did. The runtime writes to an sRGB target, so a ramp that should look as it would in SwiftUI can be decoded with `c * c` (cheap) or `pow(c, 2.2)` before returning, as the example does.

## Tuning

- Feed `hdHeatRamp` a luminance (`dot(rgb, float3(0.2125, 0.7154, 0.0721))`), a distance or any 0..1 field for a thermal-camera look.
- Shimmer: convert to HSL, raise lightness with `l += amount * (1 - l) * sweep`, convert back (bottom band of the example).
- HSV: saturation 0.6–0.9 and value 1 give clean rainbows; the hue argument may grow without bound, but wrap time-driven hues yourself (`fract(t * rate)`) to keep precision.

## Limitations

`hdRgbToHsl` and `hdHslToRgb` branch per pixel; prefer `hdHsvToRgb` (branchless) for full-screen hue sweeps. Out-of-range inputs (negative or above 1) give out-of-range outputs. The heat ramp has hard slope changes at its stops, which can band on smooth gradients. The original Shimmer `rgbToHSL` could return a negative hue for magenta-red colours; this version wraps hue into [0,1).

## Cost

Estimate: `hdHeatRamp` is two mixes; `hdHsvToRgb` is one fract/abs/clamp/mix chain; the HSL pair costs a few compares and a division each. All negligible beside noise or loops.

## Reuse and origin

Heat ramp adapted from Inferno `Transformation/Infrared.metal`; HSL conversions from Inferno `Transformation/Shimmer.metal` (Shimmer by bwhtmn, after markiv/SwiftUI-Shimmer); both by Paul Hudson and other authors (MIT, Copyright (c) 2023), preserved in `references/inferno`. `hdHsvToRgb` is the common branchless conversion, also used by the Apollonian Gasket port (`shaders/apollonian-twist`). Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
