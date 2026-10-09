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
