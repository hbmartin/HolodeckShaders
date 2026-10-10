// Adapted from Inferno "Sinebow" (Generation/Sinebow.metal), https://github.com/twostraws/Inferno
// Copyright (c) 2023 Paul Hudson and other authors (Inferno), MIT License.
// Changes: float maths, height-relative scales, lines re-centred on screen,
// clamped inverse-distance glow, time wrapped at the 20π-second period.
float3 hdSinebowLines(float2 p, float t) {
    // Inferno measures x across the width and divides it by the aspect ratio;
    // these are its 16:9 scales expressed in height units. Y is flipped back
    // to the original top-down sense and offset so the lines centre on screen.
    float2 uv = float2(p.x * 0.6328, -p.y * 1.125 - 0.25);
    float time = fmod(t, 62.831853);
    float wave = sin(uv.x + time);
    wave *= wave * 50.0;
    float bend = sin(time);
    float greenShift = sin(time * 0.3) * 2.0;
    float3 light = float3(0.0);
    for (int i = 0; i < 10; ++i) {
        float n = float(i);
        float luma = 1.0 / max(abs(100.0 * uv.y + wave), 0.04);
        uv.y += 0.05 * sin(uv.x * bend + n * 0.2 + time);
        float3 rainbow = 0.5 + 0.5 * sin(float3(n * 0.3 + time, n * 0.3 + 2.0 + greenShift, n * 0.3 + 4.0));
        light += rainbow * luma;
    }
    return light;
}
