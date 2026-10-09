float3 shade(float2 p, float t, float2 pixel) {
    float radius = length(p);
    float angle = atan2(p.y, p.x) + t * 0.12;
    float sector = 6.2831853 / 10.0;
    angle = abs(fract(angle / sector + 0.5) - 0.5) * sector;
    float2 q = float2(cos(angle), sin(angle)) * radius;
    q = q * 7.0 + float2(t * 0.12, t * -0.08);
    float pattern = sin(q.x * 3.0 + sin(q.y * 4.0)) * cos(q.y * 3.0 - t * 0.5);
    float edges = pow(1.0 - abs(sin(pattern * 4.0 + radius * 12.0)), 5.0);
    return palette(pattern * 0.25 + radius * 0.6 + t * 0.025) * (0.20 + edges * 0.8);
}
