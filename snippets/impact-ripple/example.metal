float3 shade(float2 p, float t, float2 pixel) {
    float r2 = dot(p, p) / 0.16;
    if (r2 >= 1.0) return float3(0.002, 0.004, 0.01);
    float3 n = float3(p / 0.4, sqrt(1.0 - r2));
    float3 light = float3(0.01, 0.03, 0.06) + float3(0.15, 0.68, 1.0) * (1.0 - n.z) * (1.0 - n.z) * 0.6;
    for (int k = 0; k < 2; ++k) {
        float4 hit = hdScheduledHit(t, float(k), 3.5 + float(k));
        float2 impact = hdImpact(n, hit.xyz, hit.w, 3.0);
        light += float3(0.6, 0.9, 1.0) * impact.x + float3(0.15, 0.68, 1.0) * impact.y * 0.4;
    }
    return 1.0 - exp(-light);
}
