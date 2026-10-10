float3 shade(float2 p, float t, float2 pixel) {
    float reveal = 0.5 + 0.5 * sin(fmod(t * 0.6, 6.2831853));
    float2 mask = hdDissolve(saturate(fbm(p * 5.0 + 3.0) * 1.1), reveal, 0.05);
    float3 image = palette(p.x * 0.4 + p.y * 0.2 + 0.55) * 0.6;
    return image * mask.x + float3(1.0, 0.65, 0.25) * mask.y;
}
