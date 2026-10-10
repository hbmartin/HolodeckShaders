// Adapted from SwiftShaders Noise/NoiseShader.metal perlinNoise,
// https://github.com/muhittincamdali/SwiftShaders (commit 4acb3a91)
// Copyright (c) 2024 Muhittin Camdali, MIT License.
// Changes: shared hash21 for the gradient angle, quintic fade, output
// rescaled from the theoretical ±sqrt(0.5) range to 0..1.

float2 hdGradientNoiseDir(float2 cell) {
    float angle = hash21(cell) * 6.2831853;
    return float2(cos(angle), sin(angle));
}

float hdGradientNoise2(float2 p) {
    float2 i = floor(p), f = fract(p);
    float2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
    float a = dot(hdGradientNoiseDir(i), f);
    float b = dot(hdGradientNoiseDir(i + float2(1.0, 0.0)), f - float2(1.0, 0.0));
    float c = dot(hdGradientNoiseDir(i + float2(0.0, 1.0)), f - float2(0.0, 1.0));
    float d = dot(hdGradientNoiseDir(i + 1.0), f - 1.0);
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y) * 0.70710678 + 0.5;
}
