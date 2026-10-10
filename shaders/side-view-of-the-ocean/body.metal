// Side View of the Ocean: original soft depth study of the supplied image.
// Canonical value noise supplies slow diffuse currents, without textures.
float3 shade(float2 p, float time, float2 pixel) {
    float phase = fmod(time * 0.065, 6.2831853);
    float current = 0.021 * sin(p.x * 4.0 + phase)
                  + 0.012 * sin(p.x * 7.0 - phase);
    float depth = 0.5 - p.y + current;
    float3 color = mix(float3(0.82, 0.87, 1.0), float3(0.34, 0.67, 0.99),
                       smoothstep(0.0, 0.48, depth));
    color = mix(color, float3(0.025, 0.59, 0.76), smoothstep(0.39, 0.77, depth));
    color = mix(color, float3(0.025, 0.47, 0.59), smoothstep(0.72, 1.02, depth));
    float mist = noise2(p * 3.2 + float2(sin(phase), cos(phase)) * 0.23);
    float hazeDistance = (depth - 0.48) / 0.20;
    float haze = exp(-(hazeDistance * hazeDistance));
    color += float3(0.03, 0.025, 0.025) * (mist - 0.5) * haze;
    color += (hash21(pixel) - 0.5) / 255.0;
    return pow(clamp(color, 0.0, 1.0), float3(2.2));
}
