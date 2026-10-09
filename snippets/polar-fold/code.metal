float2 hdPolarFold(float2 p, float sectors, float rotation) {
    float radius = length(p);
    float angle = atan2(p.y, p.x) + rotation;
    float sector = 6.2831853 / max(sectors, 1.0);
    angle = abs(fract(angle / sector + 0.5) - 0.5) * sector;
    return float2(cos(angle), sin(angle)) * radius;
}
