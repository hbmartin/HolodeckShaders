float3 shade(float2 p, float t, float2 pixel) {
    float a = fmod(t * 0.05, 6.2831853);
    float2 drift = 2.0 * float2(cos(a), sin(a));
    float n = 0.65 * hdGradientNoise2(p * 4.0 + drift) + 0.35 * hdGradientNoise2(p * 9.0 - drift * 1.7);
    float veins = 1.0 - abs(sin((p.x + n * 1.6) * 9.0));
    float3 stone = mix(float3(0.06, 0.07, 0.12), float3(0.55, 0.6, 0.72), n);
    return stone * stone + float3(0.9, 0.75, 0.5) * pow(veins, 12.0) * 0.6;
}
