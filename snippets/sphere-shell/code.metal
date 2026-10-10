// Sphere centred at the origin (offset ro by the centre). rd must be normalised.
// Returns (tNear, tFar); float2(-1.0) on a miss. tNear is negative when ro is inside the sphere.
float2 hdRaySphere(float3 ro, float3 rd, float radius) {
    float b = dot(ro, rd);
    float h = b * b - (dot(ro, ro) - radius * radius);
    if (h < 0.0) return float2(-1.0);
    h = sqrt(h);
    return float2(-b - h, -b + h);
}

// 0 facing the viewer, 1 at grazing angles; abs() makes it work for back faces too.
float hdFresnel(float3 n, float3 v, float power) {
    return pow(1.0 - saturate(abs(dot(n, v))), power);
}

// 1 where the ray passes through the sphere, exponential falloff with closest-approach distance outside it.
float hdSphereHalo(float3 ro, float3 rd, float radius, float falloff) {
    float along = max(dot(-ro, rd), 0.0);
    float d = length(ro + rd * along);
    return exp(-falloff * max(d - radius, 0.0) / radius);
}
