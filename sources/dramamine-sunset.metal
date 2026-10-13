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
// Dramamine Sunset: original composition inspired by the supplied image.
// Ribbon falloff adapted from Holodeck's Glowing Ribbons recipe (repository
// provenance; no additional license inferred). Changes: elliptical distance,
// separate pastel halo, travelling flare, and display-to-linear colour.
float sunsetRibbon(float distance, float width) {
    float d = abs(distance) / max(width, 0.0001);
    return exp(-d) + 0.18 * exp(-d * (12.0 / 55.0));
}

float3 shade(float2 p, float time, float2 pixel) {
    float phase = fmod(time * 0.08, 6.2831853);
    float2 q = p + 0.012 * float2(sin(phase), cos(phase) - 1.0);
    float horizon = q.y - 0.16 * q.x;
    float3 color = mix(float3(0.015, 0.19, 0.68), float3(0.46, 0.0, 0.79),
                       smoothstep(-0.18, 0.19, horizon));
    float seaDistance = (horizon + 0.42) / 0.085;
    float sea = exp(-(seaDistance * seaDistance));
    color = mix(color, float3(0.0, 0.64, 0.65), sea * 0.84);

    const float2 ellipseCentre = float2(-0.80, 0.30);
    const float2 ellipseRadii = float2(1.12, 0.49);
    float2 ellipse = (q - ellipseCentre) / ellipseRadii;
    float radius = length(ellipse);
    float distance = (radius - 1.0) * ellipseRadii.y;
    float haloDistance = distance / 0.062;
    float coralDistance = (distance - 0.092) / 0.049;
    float troughDistance = (distance - 0.038) / 0.021;
    float halo = exp(-(haloDistance * haloDistance));
    float coral = exp(-(coralDistance * coralDistance));
    float trough = exp(-(troughDistance * troughDistance));
    color = mix(color, float3(0.79, 0.47, 0.79), halo * 0.68);
    color = mix(color, float3(0.86, 0.35, 0.44), coral * 0.73);
    color *= 1.0 - trough * 0.44;
    float core = sunsetRibbon(distance, max(0.0024, fwidth(distance)));
    color = mix(color, float3(1.0, 0.84, 0.83), core * 0.52);

    // The flare stays attached to the lower arc as it glides back and forth.
    float flareAngle = -1.13 + 0.12 * sin(phase);
    float2 flare = ellipseCentre
                 + float2(ellipseRadii.x * cos(flareAngle), ellipseRadii.y * sin(flareAngle));
    float2 delta = q - flare;
    float bloom = exp(-dot(delta, delta) / 0.012);
    float hot = exp(-dot(delta, delta) / 0.0018);
    color = mix(color, float3(0.99, 0.66, 0.83), bloom * 0.8);
    color = mix(color, float3(1.0, 0.94, 1.0), hot * 0.92);
    float2 hazeDelta = q - float2(-0.49, 0.13);
    float haze = exp(-dot(hazeDelta, hazeDelta) / 0.018);
    color += float3(0.09, 0.015, 0.04) * haze;
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
