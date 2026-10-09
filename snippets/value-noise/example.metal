float3 shade(float2 p, float t, float2 pixel) { return float3(noise2(p * 8.0 + float2(t * 0.1, 0))); }
