float3 shade(float2 p, float t, float2 pixel) { float2 q = hdPolarFold(p, 10, t * 0.12) * 7; return palette(sin(q.x * 3 + sin(q.y * 4)) * 0.3 + length(p)); }
