// Harvest Sunset: original Dramamine Sunset composition recolored for Thanksgiving.
// Ribbon falloff adapted from Holodeck's Glowing Ribbons recipe (repository
// provenance; no additional license inferred). Changes: elliptical distance,
// separate harvest-gold halo, travelling cream flare, and display-to-linear colour.
float sunsetRibbon(float distance, float width) {
    float d = abs(distance) / max(width, 0.0001);
    return exp(-d) + 0.18 * exp(-d * (12.0 / 55.0));
}

float3 shade(float2 p, float time, float2 pixel) {
    float phase = fmod(time * 0.08, 6.2831853);
    float2 q = p + 0.012 * float2(sin(phase), cos(phase) - 1.0);
    float horizon = q.y - 0.16 * q.x;
    float3 color = mix(float3(0.34, 0.12, 0.045), float3(0.55, 0.06, 0.13),
                       smoothstep(-0.18, 0.19, horizon));
    float seaDistance = (horizon + 0.42) / 0.085;
    float sea = exp(-(seaDistance * seaDistance));
    color = mix(color, float3(0.85, 0.48, 0.08), sea * 0.84);

    const float2 ellipseCentre = float2(-0.80, 0.30);
    const float2 ellipseRadii = float2(1.12, 0.49);
    float2 ellipse = (q - ellipseCentre) / ellipseRadii;
    float radius = length(ellipse);
    float distance = (radius - 1.0) * ellipseRadii.y;
    float haloDistance = distance / 0.062;
    float coralDistance = (distance - 0.092) / 0.049;
    float troughDistance = (distance - 0.038) / 0.021;
    float halo = exp(-(haloDistance * haloDistance));
    float coral = exp(-(coralDistance * coralDistance));
    float trough = exp(-(troughDistance * troughDistance));
    color = mix(color, float3(0.95, 0.50, 0.14), halo * 0.68);
    color = mix(color, float3(0.80, 0.25, 0.055), coral * 0.73);
    color *= 1.0 - trough * 0.44;
    float core = sunsetRibbon(distance, max(0.0024, fwidth(distance)));
    color = mix(color, float3(1.0, 0.88, 0.58), core * 0.52);

    // The flare stays attached to the lower arc as it glides back and forth.
    float flareAngle = -1.13 + 0.12 * sin(phase);
    float2 flare = ellipseCentre
                 + float2(ellipseRadii.x * cos(flareAngle), ellipseRadii.y * sin(flareAngle));
    float2 delta = q - flare;
    float bloom = exp(-dot(delta, delta) / 0.012);
    float hot = exp(-dot(delta, delta) / 0.0018);
    color = mix(color, float3(1.0, 0.68, 0.28), bloom * 0.8);
    color = mix(color, float3(1.0, 0.96, 0.80), hot * 0.92);
    float2 hazeDelta = q - float2(-0.49, 0.13);
    float haze = exp(-dot(hazeDelta, hazeDelta) / 0.018);
    color += float3(0.09, 0.045, 0.006) * haze;
    color += (hash21(pixel) - 0.5) / 255.0;
    return pow(clamp(color, 0.0, 1.0), float3(2.2));
}
