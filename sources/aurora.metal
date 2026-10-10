#include <metal_stdlib>
using namespace metal;

struct ShaderUniforms {
    float2 resolution;
    float time;
    float padding;
};

struct RasterData { float4 position [[position]]; };

vertex RasterData vertexShader(uint id [[vertex_id]]) {
    const float2 positions[3] = {float2(-1, -1), float2(3, -1), float2(-1, 3)};
    RasterData out;
    out.position = float4(positions[id], 0, 1);
    return out;
}

float hash21(float2 p) {
    float3 q = fract(float3(p.x, p.y, p.x) * 0.1031);
    q += dot(q, q.yzx + 33.33);
    return fract((q.x + q.y) * q.z);
}

float noise2(float2 p) {
    float2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash21(i), hash21(i + float2(1, 0)), f.x),
               mix(hash21(i + float2(0, 1)), hash21(i + 1.0), f.x), f.y);
}

float fbm(float2 p) {
    float result = 0.0, amplitude = 0.5;
    for (int i = 0; i < 4; ++i) {
        result += amplitude * noise2(p);
        p = float2(p.x * 1.6 - p.y * 1.2, p.x * 1.2 + p.y * 1.6) + 5.7;
        amplitude *= 0.5;
    }
    return result;
}

float3 palette(float x) {
    return 0.5 + 0.5 * cos(6.2831853 * (x + float3(0.0, 0.33, 0.67)));
}
float3 shade(float2 p, float t, float2 pixel) {
    float3 sky = mix(float3(0.004, 0.008, 0.035), float3(0.018, 0.045, 0.10), p.y + 0.5);
    float stars = pow(hash21(floor(pixel / 3.0)), 120.0);
    sky += stars * (0.18 + 0.12 * sin(t + hash21(floor(pixel / 3.0)) * 20.0));
    for (int i = 0; i < 3; ++i) {
        float layer = float(i);
        float drift = fbm(float2(p.x * 3.0 + t * 0.06 + layer * 7.0, t * 0.04));
        float center = 0.05 + layer * 0.09 + 0.18 * sin(p.x * 3.0 + drift * 5.0);
        float curtain = exp(-abs(p.y - center) * (9.0 + layer * 3.0));
        float rays = 0.35 + 0.65 * fbm(float2(p.x * 35.0 + layer * 9.0, p.y * 2.0 - t * 0.25));
        float3 tint = mix(float3(0.02, 0.85, 0.38), float3(0.34, 0.10, 0.85), p.y + 0.4);
        sky += tint * curtain * rays * 0.55;
    }
    return sky;
}

fragment float4 fragmentShader(RasterData in [[stage_in]],
                               constant ShaderUniforms &u [[buffer(0)]]) {
    float2 p = (in.position.xy - u.resolution * 0.5) / max(u.resolution.y, 1.0);
    p.y = -p.y;
    float3 color = shade(p, u.time, in.position.xy);
    return float4(clamp(color, 0.0, 1.0), 1.0);
}
