float3 shade(float2 p, float t, float2 pixel) {
    float3 extents = float3(6.0, 4.0, 8.0);
    float3 ro = float3(0.0, 0.0, 6.5);
    float3 rd = normalize(float3(p, -1.0));
    float4 room = hdRoomHit(ro, rd, extents);
    float3 hit = ro + rd * room.w;
    float2 uv = abs(room.x) > 0.5 ? hit.yz : (abs(room.y) > 0.5 ? hit.xz : hit.xy);
    float2 cell = floor(uv);
    float3 color = (abs(room.xyz) * 0.12 + 0.02) * (0.6 + 0.4 * fmod(abs(cell.x + cell.y), 2.0));
    float3 ball = hdBounceInBox(float3(1.0, -2.0, 0.0), float3(1.3, 0.9, 1.1), extents - 0.6, t);
    float3 local = ro - ball;
    float b = dot(local, rd);
    float h = b * b - dot(local, local) + 0.36;
    if (h > 0.0) {
        float tn = -b - sqrt(h);
        float3 n = (local + rd * tn) / 0.6;
        if (tn > 0.0 && tn < room.w) color = float3(1.0, 0.48, 0.035) * (0.25 + 0.75 * saturate(dot(n, float3(0.36, 0.8, 0.48))));
    }
    return color;
}
