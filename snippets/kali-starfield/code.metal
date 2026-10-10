// Derived from "Warp Speed 2" by Dave Hoskins (https://www.shadertoy.com/view/4tjSDt), CC BY-NC-SA 3.0.
// Adaptations of this function must keep CC BY-NC-SA 3.0 and credit Dave Hoskins.
// License terms: https://creativecommons.org/licenses/by-nc-sa/3.0/

float3 hdKaliStarfield(float2 uv, float travel, int steps, float jitter) {
    float ds = 2.5 / float(steps), weight = ds * 40.0;
    float3 origin = float3(0.3 * sin(travel * 1.5707963), 0.35 - 0.3 * cos(travel * 2.4166097), travel);
    float s = ds * jitter, v = 0.0;
    float3 light = float3(0.0);
    for (int r = 0; r < steps; ++r) {
        float3 q = origin + s * float3(uv, 0.05);
        q.z = fract(q.z);
        for (int i = 0; i < 10; ++i) q = abs(q) * (2.04 / max(dot(q, q), 1e-4)) - 0.9;
        v += pow(dot(q, q), 0.7) * 0.06 * weight;
        light += float3(v * 0.2 + 0.4, 12.0 - s * 2.0, 0.1 + v) * (v * 0.00003 * weight);
        s += ds;
    }
    return light;
}
