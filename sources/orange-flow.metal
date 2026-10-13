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
// Orange Flow: original translucent amber folds inspired by the supplied image.
// Uses canonical value noise; no external shader source is copied.
float3 shade(float2 p, float time, float2 pixel) {
    float phase = fmod(time * 0.07, 6.2831853);
    float2 q = p;
    q.x += 0.025 * sin(phase + q.y * 2.0);
    float lower = 1.0 - smoothstep(-0.5, 0.32, q.y);
    float3 color = mix(float3(0.96, 0.49, 0.0), float3(0.78, 0.70, 0.0), lower);
    color += (noise2(q * 4.0 + float2(sin(phase), cos(phase)) * 0.12) - 0.5)
           * float3(0.05, 0.034, 0.0);

    // A broad sheet turns from an upper-right lip into a flowing lower fold.
    float drop = max(0.13 - q.y, 0.0);
    float edge = -0.045 + 1.0 * drop * drop
               + 0.055 * sin(q.y * 6.0 + phase);
    float lip = 0.19 + 0.16 * smoothstep(-0.1, 0.62, q.x)
              + 0.013 * sin(q.x * 12.0 - phase);
    float sheet = smoothstep(-0.009, 0.012, q.x - edge)
                * (1.0 - smoothstep(-0.01, 0.013, q.y - lip));
    float3 silk = mix(float3(1.0, 0.78, 0.075), float3(0.91, 0.86, 0.0), lower);
    color = mix(color, silk, sheet * 0.80);
    float lipDistance = (q.y - lip + 0.025) / 0.057;
    float lipGlow = exp(-(lipDistance * lipDistance)) * sheet;
    color = mix(color, float3(1.0, 0.77, 0.22), lipGlow * 0.42);
    float turnDistance = (q.x - edge + 0.055) / 0.084;
    float turn = exp(-(turnDistance * turnDistance));
    color *= 1.0 - turn * 0.10;

    // Overlapping, low-contrast translucent ribbons keep the image airy.
    float backEdge = -0.28 + 0.22 * cos(q.y * 4.0 + phase);
    float back = smoothstep(-0.012, 0.015, q.x - backEdge)
               * (1.0 - smoothstep(0.12, 0.25, q.x - backEdge));
    color = mix(color, float3(0.61, 0.57, 0.005), back * lower * 0.38);
    float veilEdge = -0.03 + 0.12 * sin(q.y * 7.0 - phase);
    float veilDistance = (q.x - veilEdge) / 0.08;
    float veil = exp(-(veilDistance * veilDistance));
    color = mix(color, float3(1.0, 0.68, 0.04), veil * 0.17);
    float frontEdge = -0.16 + 0.15 * sin(q.y * 5.0 - phase) + lower * 0.22;
    float front = smoothstep(-0.004, 0.008, q.x - frontEdge)
                * (1.0 - smoothstep(0.10, 0.17, q.x - frontEdge))
                * (1.0 - smoothstep(0.17, 0.26, q.y));
    color = mix(color, float3(0.95, 0.70, 0.02), front * 0.27);
    float diagonal = q.y + 0.52 * q.x + 0.02 + 0.11 * sin(q.x * 4.0 + phase);
    float overlapDistance = diagonal / 0.048;
    float overlap = exp(-(overlapDistance * overlapDistance));
    color *= 1.0 - overlap * sheet * 0.045;
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
