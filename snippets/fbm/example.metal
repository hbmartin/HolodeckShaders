float3 shade(float2 p, float t, float2 pixel) { float n = fbm(p * 4 + float2(t * 0.05, 0)); return mix(float3(0.02,0.04,0.10), float3(0.4,0.7,0.9), n); }
