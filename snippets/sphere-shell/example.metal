float3 shade(float2 p, float t, float2 pixel) {
    float3 ro = float3(0.0, 0.0, 3.5);
    float3 rd = normalize(float3(p, -1.6));
    float3 cyan = float3(0.15, 0.68, 1.0);
    float3 color = cyan * hdSphereHalo(ro, rd, 1.0, 6.0) * 0.05;
    float2 hit = hdRaySphere(ro, rd, 1.0);
    if (hit.y > 0.0) {
        float pulse = 0.85 + 0.15 * sin(fmod(t * 1.3, 6.2831853));
        float rim = hdFresnel(ro + rd * hit.x, -rd, 2.0) + 0.35 * hdFresnel(ro + rd * hit.y, -rd, 2.0);
        color += cyan * rim * pulse;
    }
    return 1.0 - exp(-color);
}
