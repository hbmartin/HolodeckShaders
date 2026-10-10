float3 shade(float2 p, float t, float2 pixel) {
    float radius = 0.38;
    float r = length(p) / radius;
    float3 n = normalize(float3(p / radius, sqrt(max(1.0 - r * r, 0.0))));
    float3 light = hdHologramRim(n, float3(0.0, 0.0, 1.0), n * 1.6, t);
    float coverage = saturate((1.0 - r) / max(fwidth(r), 1e-5));
    float3 background = float3(0.0012, 0.0009, 0.0016);
    return 1.0 - exp(-mix(background, light, coverage * 0.95));
}
