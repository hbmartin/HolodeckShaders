float3 shade(float2 p, float t, float2 pixel) {
    float3 color = float3(0.005, 0.008, 0.025);
    float nebula = fbm(p * 3.5 + float2(t * 0.01, 0.0));
    color += float3(0.06, 0.025, 0.12) * pow(nebula, 3.0);
    for (int i = 0; i < 3; ++i) {
        float layer = float(i);
        float scale = 22.0 + layer * 14.0;
        float2 q = p * scale + float2(t * (0.18 + layer * 0.13), t * 0.025);
        float2 cell = floor(q), local = fract(q) - 0.5;
        float seed = hash21(cell + layer * 19.0);
        float2 offset = float2(hash21(cell + 8.3), hash21(cell + 3.1)) * 0.6 - 0.3;
        float distance = length(local - offset);
        float star = exp(-distance * distance * 1800.0) * step(0.78, seed);
        float twinkle = 0.65 + 0.35 * sin(t * 0.8 + seed * 50.0);
        color += mix(float3(0.55, 0.70, 1.0), float3(1.0, 0.76, 0.48), seed) * star * twinkle;
    }
    return color;
}
