// Evening and Morning: original warm/cool colour study of the supplied image.
// Uses canonical value noise from shared/common.metal; no external source code.
float3 shade(float2 p, float time, float2 pixel) {
    float phase = fmod(time * 0.12, 6.2831853);
    float2 center = float2(0.014 * sin(phase), 0.015 * (cos(phase) - 1.0));
    float2 q = p - center;
    float lower = 1.0 - smoothstep(-0.48, 0.24, q.y);
    float split = smoothstep(-0.095, 0.16, q.x + 0.028 * sin(q.y * 4.0 + phase));
    float3 warm = mix(float3(0.81, 0.025, 0.01), float3(1.0, 0.79, 0.015), lower);
    float3 cool = mix(float3(0.045, 0.79, 0.70), float3(0.02, 0.27, 0.85), lower);
    float3 color = mix(warm, cool, split);
    float seamDistance = (q.x - 0.025) / (0.047 + lower * 0.016);
    float seam = exp(-(seamDistance * seamDistance));
    color = mix(color, float3(0.51, 0.025, 0.29), seam * (0.5 + lower * 0.35));

    float radius = length(q * float2(1.0, 1.13));
    // Soft, slightly uneven rings: finite at the origin, no angular seam.
    float distortion = 0.011 * sin(q.x * 7.0 + phase)
                     * sin(q.y * 6.0 - phase);
    float rings = sin((radius + distortion) * 132.0 - phase * 2.0);
    float second = sin(radius * 189.0 + q.x * 4.0 - phase * 2.0);
    float envelope = smoothstep(0.025, 0.10, radius)
                   * (1.0 - smoothstep(0.43, 0.69, radius));
    float aa = 1.0 - smoothstep(0.7, 2.8, fwidth(radius) * 189.0);
    color *= 1.0 + (rings * 0.055 + second * 0.022) * envelope * aa;
    color = mix(color, float3(0.64, 0.1, 0.28), exp(-radius * radius / 0.006) * 0.40);

    float mist = smoothstep(0.32, 0.64, radius + q.y * 0.16);
    mist *= smoothstep(-0.12, 0.42, q.y) * 0.57;
    float cloud = noise2(q * 3.0 + float2(sin(phase), cos(phase)) * 0.15);
    color = mix(color, float3(0.52, 0.52, 0.40), mist * (0.82 + cloud * 0.18));
    float sideDistance = (abs(q.x) - 0.72) / 0.10;
    float side = exp(-(sideDistance * sideDistance));
    color = mix(color, float3(0.53, 0.045, 0.24), side * 0.42);
    color += (hash21(pixel) - 0.5) / 255.0;
    return pow(clamp(color, 0.0, 1.0), float3(2.2));
}
