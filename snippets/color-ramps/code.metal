// Heat ramp after Inferno "Infrared"; HSL conversions after Inferno "Shimmer"
// (bwhtmn, after markiv/SwiftUI-Shimmer), https://github.com/twostraws/Inferno
// Copyright (c) 2023 Paul Hudson and other authors (Inferno), MIT License.
// Changes: float maths, branchless heat ramp, hue wrapped into [0, 1).
// hdHsvToRgb is the widely used branchless HSV conversion.

// Blue (0) -> yellow (0.5) -> red (1). Input is clamped to [0, 1].
float3 hdHeatRamp(float x) {
    float s = clamp(x, 0.0, 1.0) * 2.0;
    float3 cold = float3(0.0, 0.0, 1.0), medium = float3(1.0, 1.0, 0.0), hot = float3(1.0, 0.0, 0.0);
    return mix(mix(cold, medium, min(s, 1.0)), hot, max(s - 1.0, 0.0));
}

float3 hdRgbToHsl(float3 rgb) {
    float lo = min(rgb.r, min(rgb.g, rgb.b));
    float hi = max(rgb.r, max(rgb.g, rgb.b));
    float delta = hi - lo;
    float3 hsl = float3(0.0, 0.0, 0.5 * (hi + lo));
    if (delta > 0.0) {
        if (hi == rgb.r) {
            hsl.x = (rgb.g - rgb.b) / delta;
        } else if (hi == rgb.g) {
            hsl.x = (rgb.b - rgb.r) / delta + 2.0;
        } else {
            hsl.x = (rgb.r - rgb.g) / delta + 4.0;
        }
        hsl.x = fract(hsl.x / 6.0);
        if (hsl.z > 0.0 && hsl.z < 1.0) {
            hsl.y = delta / (1.0 - abs(2.0 * hsl.z - 1.0));
        }
    }
    return hsl;
}

float3 hdHslToRgb(float3 hsl) {
    float c = (1.0 - abs(2.0 * hsl.z - 1.0)) * hsl.y;
    float h = fract(hsl.x) * 6.0;
    float x = c * (1.0 - abs(fmod(h, 2.0) - 1.0));
    float3 rgb;
    if (h < 1.0) {
        rgb = float3(c, x, 0.0);
    } else if (h < 2.0) {
        rgb = float3(x, c, 0.0);
    } else if (h < 3.0) {
        rgb = float3(0.0, c, x);
    } else if (h < 4.0) {
        rgb = float3(0.0, x, c);
    } else if (h < 5.0) {
        rgb = float3(x, 0.0, c);
    } else {
        rgb = float3(c, 0.0, x);
    }
    return rgb + (hsl.z - 0.5 * c);
}

float3 hdHsvToRgb(float3 hsv) {
    const float4 K = float4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    float3 q = clamp(abs(fract(hsv.xxx + K.xyz) * 6.0 - K.www) - K.xxx, 0.0, 1.0);
    return hsv.z * mix(K.xxx, q, hsv.y);
}
