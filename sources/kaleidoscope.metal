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

fragment float4 fragmentShader(RasterData in [[stage_in]],
                               constant ShaderUniforms &u [[buffer(0)]]) {
    float2 p = (in.position.xy - u.resolution * 0.5) / max(u.resolution.y, 1.0);
    p.y = -p.y;
    float3 color = shade(p, u.time, in.position.xy);
    return float4(clamp(color, 0.0, 1.0), 1.0);
}
