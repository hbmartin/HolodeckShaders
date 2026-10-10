// Exit intersection of a ray starting inside an axis-aligned box centred at the origin.
// xyz = inward face normal, w = distance to the exit point.
float4 hdRoomHit(float3 ro, float3 rd, float3 halfExtents) {
    float3 s = select(float3(-1.0), float3(1.0), rd >= 0.0);
    float3 tExit = (s * halfExtents - ro) / (s * max(abs(rd), 1e-6));
    float3 n = float3(0.0, 0.0, -s.z);
    float t = tExit.z;
    if (tExit.x < t) { t = tExit.x; n = float3(-s.x, 0.0, 0.0); }
    if (tExit.y < t) { t = tExit.y; n = float3(0.0, -s.y, 0.0); }
    return float4(n, t);
}

// Triangle-wave bounce path inside +/-halfExtents. start is the position at t = 0 (inside the box), velocity in
// units per second. Whole and fractional seconds are wrapped separately to keep long-running phases precise.
float3 hdBounceInBox(float3 start, float3 velocity, float3 halfExtents, float t) {
    float3 rate = velocity / (4.0 * halfExtents);
    float whole = floor(t);
    float3 phase = fract(fract(rate * whole) + rate * (t - whole) + start / (4.0 * halfExtents) + 0.25);
    return halfExtents * (1.0 - 4.0 * abs(phase - 0.5));
}
