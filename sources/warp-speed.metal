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
// "Warp Speed 2" by Dave Hoskins (2015)
// https://www.shadertoy.com/view/4tjSDt (fork of his "Warp speed", https://www.shadertoy.com/view/Msl3WH;
// fractal after Kali's star nest folding)
// License: Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported (CC BY-NC-SA 3.0)
// Adapted for Holodeck: aspect-correct coordinates; travel slowed to ~1/3 of the original speed and
// wrapped on a seamless 52-unit period (wander frequencies rounded to 2pi/4 and 2pi/2.6) so large
// times stay precise; 10 ray steps (was 100) with a per-pixel, per-frame jitter to hide step banding;
// guarded fold division; sRGB-style decode and a soft highlight shoulder instead of a hard clamp;
// unused music channel removed.
// This adaptation is licensed CC BY-NC-SA 3.0.

// Recipe: snippets/kali-starfield (RGB light, unbounded).
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

float3 shade(float2 p, float t, float2 pixel) {
    const float speed = 0.04;              // travel units per second (original: 0.116)
    const float period = 52.0 / speed;     // seamless loop of the travel path (1300 s)
    float travel = 0.45 + (t - period * floor(t / period)) * speed;
    // Interleaved gradient noise, offset every frame so step banding reads as fine film grain rather than a fixed pattern.
    float frame = t * 60.0 - 64.0 * floor(t * 60.0 / 64.0);
    float jitter = fract(52.9829189 * fract(dot(pixel + 5.588238 * floor(frame), float2(0.06711056, 0.00583715))));
    float3 c = hdKaliStarfield(p * 2.0, travel, 10, jitter);
    c = select(c, 0.6 + 0.4 * (1.0 - exp(-(c - 0.6) / 0.4)), c > 0.6);
    return c * c;
}

fragment float4 fragmentShader(RasterData in [[stage_in]],
                               constant ShaderUniforms &u [[buffer(0)]]) {
    float2 p = (in.position.xy - u.resolution * 0.5) / max(u.resolution.y, 1.0);
    p.y = -p.y;
    float3 color = shade(p, u.time, in.position.xy);
    return float4(clamp(color, 0.0, 1.0), 1.0);
}
