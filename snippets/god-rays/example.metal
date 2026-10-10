float3 shade(float2 p, float t, float2 pixel) {
    float3 water = mix(float3(0.002, 0.02, 0.04), float3(0.02, 0.15, 0.18), smoothstep(-0.5, 0.5, p.y));
    float rays = hdGodRays(p, float2(0.25, 1.4), t);
    return water + float3(0.12, 0.26, 0.24) * rays * smoothstep(-0.55, 0.5, p.y);
}
