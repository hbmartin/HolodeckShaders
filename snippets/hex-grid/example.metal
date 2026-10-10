float3 shade(float2 p, float t, float2 pixel) {
    float4 flat = hdHexCell(p * 12.0 + float2(fmod(t * 0.3, 1.0) * 2.0, 0.0));
    float3 color = float3(0.02, 0.12, 0.2) * hdHexEdge(flat.xy, 0.05);
    float r = length(p) / 0.42;
    float a = fmod(t * 0.2, 6.2831853);
    float3 n = normalize(float3(p / 0.42, sqrt(max(1.0 - r * r, 0.0))));
    n = float3(n.x * cos(a) + n.z * sin(a), n.y, n.z * cos(a) - n.x * sin(a));
    float4 cell = hdSphereHexCell(n, 6.0);
    float shell = hdHexEdge(cell.xy, 0.04) * 0.8 + hdCellFlash(cell.zw, t, 0.5) * 0.5 + 0.03;
    float coverage = saturate((1.0 - r) / max(fwidth(r), 1e-5));
    return mix(color, float3(0.15, 0.68, 1.0) * shell, coverage);
}
