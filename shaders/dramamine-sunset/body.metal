// Dramamine Sunset: original composition inspired by the supplied image.
// Ribbon falloff adapted from Holodeck's Glowing Ribbons recipe (repository
// provenance; no additional license inferred). Changes: elliptical distance,
// separate pastel halo, travelling flare, and display-to-linear colour.
float sunsetRibbon(float distance, float width) {
    float d = abs(distance) / max(width, 0.0001);
    return exp(-d) + 0.18 * exp(-d * (12.0 / 55.0));
}

float3 shade(float2 p, float time, float2 pixel) {
    float phase = fmod(time * 0.08, 6.2831853);
    float2 q = p + 0.012 * float2(sin(phase), cos(phase) - 1.0);
    float horizon = q.y - 0.16 * q.x;
    float3 color = mix(float3(0.015, 0.19, 0.68), float3(0.46, 0.0, 0.79),
                       smoothstep(-0.18, 0.19, horizon));
    float sea = exp(-pow((horizon + 0.42) / 0.085, 2.0));
    color = mix(color, float3(0.0, 0.64, 0.65), sea * 0.84);

    float2 ellipse = (q - float2(-0.80, 0.30)) / float2(1.12, 0.49);
    float radius = length(ellipse);
    float distance = (radius - 1.0) * 0.49;
    float halo = exp(-pow(distance / 0.062, 2.0));
    float coral = exp(-pow((distance - 0.092) / 0.049, 2.0));
    float trough = exp(-pow((distance - 0.038) / 0.021, 2.0));
    color = mix(color, float3(0.79, 0.47, 0.79), halo * 0.68);
    color = mix(color, float3(0.86, 0.35, 0.44), coral * 0.73);
    color *= 1.0 - trough * 0.44;
    float core = sunsetRibbon(distance, max(0.0024, fwidth(distance)));
    color = mix(color, float3(1.0, 0.84, 0.83), clamp(core * 0.52, 0.0, 0.8));

    // The flare stays attached to the lower arc as it glides back and forth.
    float flareAngle = -1.13 + 0.12 * sin(phase);
    float2 flare = float2(-0.80, 0.30)
                 + float2(1.12 * cos(flareAngle), 0.49 * sin(flareAngle));
    float2 delta = q - flare;
    float bloom = exp(-dot(delta, delta) / 0.012);
    float hot = exp(-dot(delta, delta) / 0.0018);
    color = mix(color, float3(0.99, 0.66, 0.83), bloom * 0.8);
    color = mix(color, float3(1.0, 0.94, 1.0), hot * 0.92);
    float haze = exp(-dot(q - float2(-0.49, 0.13), q - float2(-0.49, 0.13)) / 0.018);
    color += float3(0.09, 0.015, 0.04) * haze;
    color += (hash21(pixel) - 0.5) / 255.0;
    return pow(clamp(color, 0.0, 1.0), float3(2.2));
}
