float3 shade(float2 p, float t, float2 pixel) {
    float3 color = float3(0.005, 0.012, 0.035);
    for (int i = 0; i < 7; ++i) {
        float n = float(i);
        float y = 0.22 * sin(p.x * (3.0 + n * 0.35) + t * 0.65 + n * 0.7);
        y += 0.07 * sin(p.x * 8.0 - t * 0.35 + n) + (n - 3.0) * 0.065;
        float distance = abs(p.y - y);
        float ribbon = exp(-distance * 55.0) + 0.18 * exp(-distance * 12.0);
        color += palette(n * 0.08 + t * 0.015 + p.x * 0.08) * ribbon * 0.55;
    }
    return color;
}
