float3 shade(float2 p, float t, float2 pixel) {
    float phase = (t - hdEmberPeriod * floor(t / hdEmberPeriod)) / hdEmberPeriod;
    float2 uv = p * 2.8125;
    float3 light = float3(0.0);
    for (int i = 0; i < 4; ++i) light += hdEmberLayer(uv * (1.4 + 0.07 * float(i)), uv, phase, float(i)) * (1.0 - 0.15 * float(i));
    float3 c = clamp(float3(0.03, 0.008, 0.002) + light * 2.0, 0.0, 1.0);
    return c * c;
}
