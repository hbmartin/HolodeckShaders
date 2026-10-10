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
float3 studioEnvironment(float3 direction, float t, float roughness) {
    float3 color = mix(float3(0.018, 0.026, 0.045), float3(0.32, 0.40, 0.52),
                       smoothstep(-0.4, 0.9, direction.y));
    float3 light = normalize(float3(-0.65 + 0.3 * sin(t * 0.3), 0.7, 0.8));
    float exponent = mix(180.0, 12.0, roughness);
    color += float3(3.2, 3.0, 2.8) * pow(max(dot(direction, light), 0.0), exponent);
    color += float3(0.65, 1.1, 1.8) * pow(max(dot(direction, normalize(float3(0.9, 0.2, -0.6))), 0.0), exponent * 0.5);
    color += float3(0.8) * exp(-abs(direction.x + 0.35) * mix(60.0, 8.0, roughness))
             * smoothstep(-0.1, 0.3, direction.y);
    return color;
}

float sceneDistance(float3 p) {
    return length(p) - 0.85;
}

float3 shadeMaterial(float2 p, float t, int kind) {
    float3 origin = float3(0.0, 0.15, 3.4);
    float3 ray = normalize(float3(p * 2.0, -1.8));
    float distance = 0.0;
    bool hit = false;
    for (int stepIndex = 0; stepIndex < 64; ++stepIndex) {
        float stepDistance = sceneDistance(origin + ray * distance);
        if (stepDistance < 0.001) { hit = true; break; }
        distance += stepDistance;
        if (distance > 12.0) break;
    }
    float3 background = float3(0.018, 0.026, 0.045) + float3(0.035, 0.045, 0.065) * exp(-length(p) * 2.0);
    // Intersect the studio floor analytically so the marching limit cannot distort its horizon.
    float floorDistance = ray.y < -0.0001 ? (-1.02 - origin.y) / ray.y : 1e10;
    if (!hit || floorDistance < distance) {
        if (floorDistance >= 12.0) return background;
        float3 position = origin + ray * floorDistance;
        float contact = 0.35 + 0.65 * smoothstep(0.0, 1.8, length(position.xz));
        float grid = 0.5 + 0.5 * cos(position.x * 3.0) * cos(position.z * 3.0);
        float3 floorColor = float3(0.06, 0.075, 0.10) * (0.85 + grid * 0.15) * contact;
        return mix(floorColor, background, smoothstep(3.0, 12.0, floorDistance));
    }

    float3 position = origin + ray * distance;
    float3 normal = normalize(position);
    float facing = max(dot(normal, -ray), 0.0);
    float roughness = kind == 1 ? 0.30 : 0.075;
    float3 base = kind == 1 ? float3(1.0, 0.64, 0.19) : float3(0.72, 0.80, 0.88);
    if (kind == 1) {
        float grain = sin(position.y * 650.0 + noise2(position.xz * 90.0) * 4.0);
        normal = normalize(normal + float3(0.0, grain * 0.018, 0.0));
        base *= 0.93 + grain * 0.07;
    } else if (kind == 2) {
        base = 0.45 + 0.45 * cos(float3(0.0, 2.1, 4.2) + facing * 13.0 + position.y * 3.0);
        roughness = 0.14;
    }
    float3 fresnel = base + (1.0 - base) * pow(1.0 - facing, 5.0);
    float3 reflection = studioEnvironment(reflect(ray, normal), t, roughness);
    float3 lightDirection = normalize(float3(-0.6, 0.8, 1.0));
    float diffuse = max(dot(normal, lightDirection), 0.0);
    float3 color = reflection * fresnel + base * (0.06 + diffuse * 0.12);
    return color / (1.0 + color);
}

float3 shade(float2 p, float t, float2 pixel) {
    return shadeMaterial(p, t, 0);
}

fragment float4 fragmentShader(RasterData in [[stage_in]],
                               constant ShaderUniforms &u [[buffer(0)]]) {
    float2 p = (in.position.xy - u.resolution * 0.5) / max(u.resolution.y, 1.0);
    p.y = -p.y;
    float3 color = shade(p, u.time, in.position.xy);
    return float4(clamp(color, 0.0, 1.0), 1.0);
}
