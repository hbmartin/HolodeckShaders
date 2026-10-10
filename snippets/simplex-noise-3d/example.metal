float3 shade(float2 p, float t, float2 pixel) {
    // The noise repeats every 289 units along (1,1,1), so a drift along that diagonal can wrap seamlessly.
    float drift = fmod(t * 0.25, 289.0);
    float n = hdSimplex3(float3(p * 4.0, 0.0) - drift);
    float m = hdSimplex3(float3(p * 9.0, 5.0) + drift);
    float v = saturate(0.5 + 0.35 * n + 0.15 * m);
    return float3(0.1, 0.45, 0.9) * v * v * v;
}
