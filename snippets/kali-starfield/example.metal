float3 shade(float2 p, float t, float2 pixel) {
    float travel = 0.45 + (t - 1300.0 * floor(t / 1300.0)) * 0.04;
    float jitter = fract(52.9829189 * fract(dot(pixel, float2(0.06711056, 0.00583715))));
    float3 c = clamp(hdKaliStarfield(p * 2.0, travel, 10, jitter), 0.0, 1.0);
    return c * c;
}
