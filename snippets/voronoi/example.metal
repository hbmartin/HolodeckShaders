float3 shade(float2 p, float t, float2 pixel) {
    float phase = 6.2831853 * fract(t / 18.0);
    float2 f = hdVoronoiF1F2(p * 6.0, phase, 0.9);
    float edge = f.y - f.x;
    float w = max(0.05, fwidth(edge));
    float lines = exp(-edge / w) * (0.05 / w);
    float3 c = float3(0.02, 0.08, 0.12) * (1.0 - f.x) + float3(0.6, 0.9, 0.85) * lines;
    return c;
}
