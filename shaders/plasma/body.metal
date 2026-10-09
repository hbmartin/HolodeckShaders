float3 shade(float2 p, float t, float2 pixel) {
    float2 q = p * 5.0;
    float field = sin(q.x + t * 0.7) + sin(q.y * 1.3 - t * 0.5);
    field += sin((q.x + q.y) * 0.8 + t * 0.4);
    field += sin(length(q + float2(sin(t * 0.3), cos(t * 0.4))) * 2.0 - t);
    float3 color = palette(field * 0.14 + t * 0.025);
    return color * (0.55 + 0.45 * smoothstep(-3.0, 3.0, field));
}
