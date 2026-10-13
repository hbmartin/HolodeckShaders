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
// Green Caresses: original blurred mint folds inspired by the supplied image.
// Broad fields use the canonical value-noise helper; curves are analytic.
float3 shade(float2 p, float time, float2 pixel) {
    float phase = fmod(time * 0.075, 6.2831853);
    float2 q = p + float2(0.018 * sin(phase), 0.02 * (cos(phase) - 1.0));
    float2 upper = (q - float2(-0.43, 0.28)) / float2(0.43, 0.53);
    float2 lower = (q - float2(-0.06, -0.42)) / float2(0.31, 0.30);
    float lime = clamp(1.05 * exp(-dot(upper, upper))
                     + 0.90 * exp(-dot(lower, lower)), 0.0, 1.0);
    float3 color = mix(float3(0.69, 1.0, 0.74), float3(0.24, 0.98, 0.27), lime);
    float cloud = noise2(q * 2.8 + float2(sin(phase), cos(phase)) * 0.18);
    color = mix(color, float3(0.68, 1.0, 0.76), cloud * 0.23);

    // A hanging U-shaped fold, open above the screen, and a diagonal caress.
    float bendCoordinate = q.x * 1.6;
    float bend = -0.19 + 0.54 * (bendCoordinate * bendCoordinate);
    float2 bowl = (q - float2(0.01, 0.41)) / float2(0.26, 0.60);
    float fold = (length(bowl) - 1.0) * 0.23;
    float rimDistance = fold / 0.020;
    float rimHaloDistance = fold / 0.060;
    float rim = exp(-(rimDistance * rimDistance));
    float rimHalo = exp(-(rimHaloDistance * rimHaloDistance));
    color = mix(color, float3(0.58, 0.99, 1.0), rimHalo * 0.25 + rim * 0.66);
    float insideDistance = (q.y - bend) / 0.11;
    float insideCoordinate = q.x / 0.27;
    float insideSquare = insideCoordinate * insideCoordinate;
    float inside = exp(-(insideDistance * insideDistance))
                 * exp(-(insideSquare * insideSquare));
    color = mix(color, float3(0.72, 1.0, 0.89), inside * 0.44);

    float diagonal = q.y - 0.75 * q.x - 0.08
                   - 0.04 * sin(q.x * 4.0 + phase);
    float sweepDistance = diagonal / 0.092;
    float sweep = exp(-(sweepDistance * sweepDistance));
    color = mix(color, float3(0.49, 1.0, 1.0), sweep * 0.70);
    float rightFold = q.x - 0.39 - 0.12 * sin(q.y * 4.0 - phase);
    float rightFoldDistance = rightFold / 0.075;
    color = mix(color, float3(0.58, 0.99, 0.98),
                exp(-(rightFoldDistance * rightFoldDistance)) * 0.48);
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
