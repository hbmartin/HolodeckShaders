// Green Caresses: original blurred mint folds inspired by the supplied image.
// Broad fields use the canonical value-noise helper; curves are analytic.
float3 shade(float2 p, float time, float2 pixel) {
    float phase = fmod(time * 0.075, 6.2831853);
    float2 q = p + float2(0.018 * sin(phase), 0.02 * (cos(phase) - 1.0));
    float2 upper = (q - float2(-0.43, 0.28)) / float2(0.43, 0.53);
    float2 lower = (q - float2(-0.06, -0.42)) / float2(0.31, 0.30);
    float lime = clamp(1.05 * exp(-dot(upper, upper))
                     + 0.90 * exp(-dot(lower, lower)), 0.0, 1.0);
    float3 color = mix(float3(0.69, 1.0, 0.74), float3(0.24, 0.98, 0.27), lime);
    float cloud = noise2(q * 2.8 + float2(sin(phase), cos(phase)) * 0.18);
    color = mix(color, float3(0.68, 1.0, 0.76), cloud * 0.23);

    // A hanging U-shaped fold, open above the screen, and a diagonal caress.
    float bend = -0.19 + 0.54 * pow(q.x * 1.6, 2.0);
    float2 bowl = (q - float2(0.01, 0.41)) / float2(0.26, 0.60);
    float fold = (length(bowl) - 1.0) * 0.23;
    float rim = exp(-pow(fold / 0.020, 2.0));
    float rimHalo = exp(-pow(fold / 0.060, 2.0));
    color = mix(color, float3(0.58, 0.99, 1.0), rimHalo * 0.25 + rim * 0.66);
    float inside = exp(-pow((q.y - bend) / 0.11, 2.0))
                 * exp(-pow(q.x / 0.27, 4.0));
    color = mix(color, float3(0.72, 1.0, 0.89), inside * 0.44);

    float diagonal = q.y - 0.75 * q.x - 0.08
                   - 0.04 * sin(q.x * 4.0 + phase);
    float sweep = exp(-pow(diagonal / 0.092, 2.0));
    color = mix(color, float3(0.49, 1.0, 1.0), sweep * 0.70);
    float rightFold = q.x - 0.39 - 0.12 * sin(q.y * 4.0 - phase);
    color = mix(color, float3(0.58, 0.99, 0.98), exp(-pow(rightFold / 0.075, 2.0)) * 0.48);
    color += (hash21(pixel) - 0.5) / 255.0;
    return pow(clamp(color, 0.0, 1.0), float3(2.2));
}
