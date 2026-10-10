float3 shade(float2 p, float t, float2 pixel) {
    // Alternate circle and diamond sweeps between two procedural scenes.
    float cycle = fmod(t, 16.0);
    float amount = smoothstep(0.5, 7.5, fmod(cycle, 8.0));
    bool diamond = cycle >= 8.0;
    float2 uv01 = float2(p.x * 0.5625 + 0.5, 0.5 - p.y);
    float2 cellPos = p * 14.0;
    float mask = hdDotCurtain(cellPos, uv01, amount, diamond, fwidth(cellPos.y));
    float3 from = diamond ? palette(0.62 + p.x * 0.1) : float3(0.03, 0.04, 0.08);
    float3 to = diamond ? float3(0.03, 0.04, 0.08) : palette(0.62 + p.x * 0.1);
    float3 color = mix(from, to, mask);
    return color * color;
}
