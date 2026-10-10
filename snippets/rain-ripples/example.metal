float3 shade(float2 p, float t, float2 pixel) {
    float ripples = hdRainRipples(p, t, 4.0);
    float3 water = mix(float3(0.002, 0.008, 0.02), float3(0.012, 0.04, 0.075), 0.5 - p.y);
    return water + float3(0.3, 0.5, 0.65) * ripples;
}
