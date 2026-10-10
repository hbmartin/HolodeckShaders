float3 shade(float2 p, float t, float2 pixel) {
    float3 rd = normalize(float3(p.x, p.y - 0.15, -1.0));
    float distance = 1.5 / max(-rd.y, 1e-3);
    float2 coord = rd.xz * distance + float2(0.0, fmod(t * 0.8, 5.0));
    float2 footprint = fwidth(coord);
    float lines = hdGridLine(coord, 1.0, 0.03, footprint) * 0.3 + hdGridLine(coord, 5.0, 0.08, footprint);
    float fade = exp(-distance * 0.04) * step(rd.y, 0.0);
    return float3(1.0, 0.48, 0.035) * lines * fade;
}
