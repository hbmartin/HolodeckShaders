// noiseValue in 0..1; reveal 0 = fully hidden, 1 = fully visible; width = edge band in noise units.
// x = visibility mask, y = edge glow mask (inside the visible side of the threshold).
float2 hdDissolve(float noiseValue, float reveal, float width) {
    float d = mix(-width, 1.0 + width, saturate(reveal)) - noiseValue;
    float visible = smoothstep(-0.15 * width, 0.15 * width, d);
    float edge = visible * (1.0 - smoothstep(0.0, width, d));
    return float2(visible, edge);
}
