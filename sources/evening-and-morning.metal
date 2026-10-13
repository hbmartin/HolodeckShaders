// MIT notice for Dave Hoskins, "Hash without Sine" (https://www.shadertoy.com/view/4djSRW):
// MIT License
//
// Copyright (c) 2014 David Hoskins.
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

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
// Evening and Morning: original warm/cool colour study of the supplied image.
// Uses canonical value noise from shared/common.metal; no external source code.
float3 shade(float2 p, float time, float2 pixel) {
    float phase = fmod(time * 0.12, 6.2831853);
    float2 center = float2(0.014 * sin(phase), 0.015 * (cos(phase) - 1.0));
    float2 q = p - center;
    float lower = 1.0 - smoothstep(-0.48, 0.24, q.y);
    float split = smoothstep(-0.095, 0.16, q.x + 0.028 * sin(q.y * 4.0 + phase));
    float3 warm = mix(float3(0.81, 0.025, 0.01), float3(1.0, 0.79, 0.015), lower);
    float3 cool = mix(float3(0.045, 0.79, 0.70), float3(0.02, 0.27, 0.85), lower);
    float3 color = mix(warm, cool, split);
    float seamDistance = (q.x - 0.025) / (0.047 + lower * 0.016);
    float seam = exp(-(seamDistance * seamDistance));
    color = mix(color, float3(0.51, 0.025, 0.29), seam * (0.5 + lower * 0.35));

    float radius = length(q * float2(1.0, 1.13));
    // Soft, slightly uneven rings: finite at the origin, no angular seam.
    float distortion = 0.011 * sin(q.x * 7.0 + phase)
                     * sin(q.y * 6.0 - phase);
    float rings = sin((radius + distortion) * 132.0 - phase * 2.0);
    float second = sin(radius * 189.0 + q.x * 4.0 - phase * 2.0);
    float envelope = smoothstep(0.025, 0.10, radius)
                   * (1.0 - smoothstep(0.43, 0.69, radius));
    float aa = 1.0 - smoothstep(0.7, 2.8, fwidth(radius) * 189.0);
    color *= 1.0 + (rings * 0.055 + second * 0.022) * envelope * aa;
    color = mix(color, float3(0.64, 0.1, 0.28), exp(-radius * radius / 0.006) * 0.40);

    float mist = smoothstep(0.32, 0.64, radius + q.y * 0.16);
    mist *= smoothstep(-0.12, 0.42, q.y) * 0.57;
    float cloud = noise2(q * 3.0 + float2(sin(phase), cos(phase)) * 0.15);
    color = mix(color, float3(0.52, 0.52, 0.40), mist * (0.82 + cloud * 0.18));
    float sideDistance = (abs(q.x) - 0.72) / 0.10;
    float side = exp(-(sideDistance * sideDistance));
    color = mix(color, float3(0.53, 0.045, 0.24), side * 0.42);
    color += (hash21(pixel) - 0.5) / 255.0;
    return pow(clamp(color, 0.0, 1.0), float3(2.2));
}

fragment float4 fragmentShader(RasterData in [[stage_in]],
                               constant ShaderUniforms &u [[buffer(0)]]) {
    float2 p = (in.position.xy - u.resolution * 0.5) / max(u.resolution.y, 1.0);
    p.y = -p.y;
    float3 color = shade(p, u.time, in.position.xy);
    return float4(clamp(color, 0.0, 1.0), 1.0);
}
