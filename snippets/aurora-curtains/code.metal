float3 hdAuroraCurtains(float2 p, float t) {
    float3 color = float3(0.0);
    for (int i = 0; i < 3; ++i) {
        float layer = float(i);
        float drift = fbm(float2(p.x * 3.0 + t * 0.06 + layer * 7.0, t * 0.04));
        float center = 0.05 + layer * 0.09 + 0.18 * sin(p.x * 3.0 + drift * 5.0);
        float curtain = exp(-abs(p.y - center) * (9.0 + layer * 3.0));
        float rays = 0.35 + 0.65 * fbm(float2(p.x * 35.0 + layer * 9.0, p.y * 2.0 - t * 0.25));
        float3 tint = mix(float3(0.02,0.85,0.38),float3(0.34,0.10,0.85),p.y + 0.4);
        color += tint * curtain * rays * 0.55;
    }
    return color;
}
