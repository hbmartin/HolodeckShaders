float3 shade(float2 p, float t, float2 pixel) {
    float2 grid = (p + float2(0.9, 0.5)) * float2(12.0, 8.0);
    float2 cell = floor(grid), uv = fract(grid) * float2(1.25, 1.1) - float2(0.125, 0.05);
    // 8192*1.5 is exactly 3*4096, so wrapping before multiplication preserves the seed sequence.
    float tick = floor(fmod(t, 8192.0) * 1.5 + hash21(cell) * 8.0);
    float2 seed = float2(cell.x + 31.0 * cell.y, tick - 4096.0 * floor(tick / 4096.0));
    float d = hdRuneDistance(uv, seed);
    float glow = hdRuneGlyph(uv, seed) + 0.2 * smoothstep(0.4, 0.0, d);
    float3 c = float3(0.25, 0.8, 0.4) * glow;
    return c * c;
}
