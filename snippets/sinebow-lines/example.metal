float3 shade(float2 p, float t, float2 pixel) {
    float3 light = hdSinebowLines(p, t * 0.5);
    return 1.0 - exp(-0.35 * light * light);
}
