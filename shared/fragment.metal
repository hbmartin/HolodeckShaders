
fragment float4 fragmentShader(RasterData in [[stage_in]],
                               constant ShaderUniforms &u [[buffer(0)]]) {
    float2 p = (in.position.xy - u.resolution * 0.5) / max(u.resolution.y, 1.0);
    p.y = -p.y;
    float3 color = shade(p, u.time, in.position.xy);
    return float4(clamp(color, 0.0, 1.0), 1.0);
}
