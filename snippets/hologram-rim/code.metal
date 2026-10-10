// Blueprint hologram light (RGB, not a complete colour): translucent deep-blue body with a soft key highlight,
// a crisp amber fresnel outline and light-blue contour slices drifting along position.y.
// footprint is one pixel in position units, for anti-aliasing the contours.
float3 hdHologramRim(float3 n, float3 v, float3 position, float t, float footprint) {
    float facing = saturate(abs(dot(n, v)));
    float fresnel = 1.0 - facing;
    float key = saturate(dot(n, float3(0.27, 0.89, 0.36)));
    float key2 = key * key;
    float3 body = float3(0.012, 0.02, 0.32) * (0.25 + 0.75 * facing) + float3(0.5, 0.46, 1.0) * (key2 * key2 * key2) * 0.25;
    float phase = position.y * 5.0 - fract(t * 0.15) * 2.0;
    float aa = max(footprint * 5.0, 1e-4);
    float contour = 1.0 - smoothstep(0.04, 0.04 + 1.5 * aa, abs(fract(phase) - 0.5));
    contour *= 0.25 + 0.75 * facing;
    float outline = smoothstep(0.66, 0.86, fresnel);
    float3 rim = float3(1.0, 0.5, 0.03) * 1.2 * outline;
    return (body + float3(0.17, 0.38, 1.0) * contour * 0.22) * (1.0 - outline) + rim;
}

// Derivative-based variant; call it in uniform control flow.
float3 hdHologramRim(float3 n, float3 v, float3 position, float t) {
    return hdHologramRim(n, v, position, t, fwidth(position.y));
}
