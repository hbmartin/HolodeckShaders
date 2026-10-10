// n: unit surface direction; hitDir: unit impact direction; age and duration in seconds.
// x = expanding ring mask, y = flash mask around the impact point. Zero outside 0 <= age < duration.
float2 hdImpact(float3 n, float3 hitDir, float age, float duration) {
    float life = age / duration;
    if (life < 0.0 || life >= 1.0) return float2(0.0);
    float g = acos(clamp(dot(n, hitDir), -1.0, 1.0));
    float2 q = float2(dot(n, float3(2.7, 1.3, -1.9)), dot(n, float3(-1.4, 2.2, 2.9)));
    float wobble = noise2(q * 1.5 + age * 0.9) - 0.5;
    float ease = 1.0 - (1.0 - life) * (1.0 - life);
    float width = 0.03 + 0.06 * life;
    float d = (g - 2.4 * ease + wobble * 0.35 * ease) / width;
    float fade = (1.0 - life) * (1.0 - life) * smoothstep(0.0, 0.04, life);
    float ring = (exp(-d * d) + 0.2 * exp(-d * d * 0.12) * step(d, 0.0)) * fade;
    float zone = exp(-g * g * 8.0) * (1.0 - life) * (1.0 - life) * (1.0 - life);
    return float2(ring, zone);
}

// Deterministic impact schedule: one hit per period per slot, directions biased toward +z (the camera side).
// xyz = unit direction, w = age in seconds within the current period.
float4 hdScheduledHit(float t, float slot, float period) {
    float local = t / period + slot * 0.618034;
    float cycle = floor(local);
    float age = (local - cycle) * period;
    float key = fmod(cycle, 997.0);
    float azimuth = (hash21(float2(key, slot * 7.3 + 1.0)) - 0.5) * 1.9;
    float elevation = (hash21(float2(key * 1.37 + 4.1, slot + 2.2)) - 0.35) * 1.2;
    float3 direction = float3(sin(azimuth) * cos(elevation), sin(elevation), cos(azimuth) * cos(elevation));
    return float4(direction, age);
}
