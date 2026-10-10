float3 shade(float2 p, float t, float2 pixel) {
    float x = fract(p.x * 0.55 + 0.5 + t * 0.03);
    float ramp = abs(x * 2.0 - 1.0);
    float3 color;
    if (p.y > 0.17) {
        color = hdHeatRamp(ramp);
    } else if (p.y > -0.17) {
        color = hdHsvToRgb(float3(x, 0.8, 1.0));
    } else {
        // Shimmer: brighten HSL lightness along a moving diagonal sweep.
        float3 hsl = hdRgbToHsl(palette(ramp * 0.5 + 0.2));
        float sweep = sin(clamp(fract(t * 0.2) * 3.0 - 1.0 - p.x - p.y, 0.0, 1.0) * 3.1415927);
        hsl.z += 0.5 * (1.0 - hsl.z) * sweep;
        color = hdHslToRgb(hsl);
    }
    return color * color;
}
