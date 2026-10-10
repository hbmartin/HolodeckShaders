// Adapted from Inferno "Water" (Transformation/Water.metal), https://github.com/twostraws/Inferno
// Copyright (c) 2023 Paul Hudson and other authors (Inferno), MIT License.
// Changes: returns warped coordinates instead of a layer position; strength
// is given directly in coordinate units; each axis is displaced by a wave
// along the other axis (the original used its own axis, which only stretches
// spacing and keeps straight lines straight).
float2 hdSineWarp(float2 uv, float t, float strength, float frequency) {
    // Wrapping the phase at 2π keeps sin/cos arguments small for long runs;
    // the warp is identical before and after each wrap.
    float phase = fmod(t * 0.05 * frequency, 6.2831853);
    return uv + float2(sin(frequency * uv.y + phase), cos(frequency * uv.x + phase)) * strength;
}
