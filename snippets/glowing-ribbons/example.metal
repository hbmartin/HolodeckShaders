float3 shade(float2 p, float t, float2 pixel) { float center = 0.22 * sin(p.x * 4 + t * 0.65); return palette(p.x * 0.1 + t * 0.02) * hdGlowingRibbon(p.y, center, 1.0/55.0); }
