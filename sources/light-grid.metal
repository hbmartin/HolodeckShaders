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
// Light Grid
// Original: "LightGrid" from Inferno by Paul Hudson and other authors
// https://github.com/twostraws/Inferno (Sources/Inferno/Shaders/Generation/LightGrid.metal)
// Copyright (c) 2023 Paul Hudson and other authors (Inferno), MIT License — https://github.com/twostraws/Inferno
// Adapted for Holodeck: float instead of half; grid centred on screen in
// height units; per-cell phase from shared hash21; slowed, 2π-wrapped time;
// colours decoded for the sRGB target; soft exposure tonemap instead of hard
// clipping; faint in-cell halo and slow per-lamp breathing added.

// MIT notice for inferno (preserved from upstream):
// Copyright (c) 2023 Paul Hudson and other authors.
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

float3 shade(float2 p, float t, float2 pixel) {
    const float density = 9.0;      // rows per screen height
    const float speed = 3.0;        // colour variance per cell
    const float groupSize = 1.0;    // lights per colour group (per axis)
    const float brightness = 3.0;
    const float tau = 6.2831853;

    // Original: uv = position/size with x scaled by aspect (height units).
    // Cell edges sit on the vertical centre line and rows fill the height,
    // so nine rows give an exact 16 x 9 wall at 16:9.
    float2 point = float2(p.x, -p.y) * density + float2(0.0, 0.5 * density);
    float2 cell = floor(point);

    // The source is exactly 2π-periodic in time; slow it and wrap seamlessly.
    float time = fmod(t * 0.25, tau);

    float variance = 0.5 * sin(time + hash21(cell + 17.0) * tau) + 0.5;
    float3 color = 0.5 + 0.5 * sin(float3(3.0, 1.5, 0.0) + speed * variance + time);

    // The source colours are display-referred; decode for the sRGB target.
    color = color * color;

    float2 groupSine = 0.5 * sin(tau * groupSize * (point - 0.25 / groupSize)) + 0.5;
    float2 pulse = smoothstep(0.0, 1.0, groupSine);
    float lamp = pulse.x * pulse.y;
    float halo = sqrt(groupSine.x * groupSine.y);

    // Gentle per-lamp breathing; also 2π-periodic in the wrapped time.
    float breathe = 0.82 + 0.18 * sin(time + hash21(cell + 71.0) * tau);

    float3 light = color * (lamp * brightness * breathe + halo * 0.12);
    return 1.0 - exp(-1.6 * light);
}

fragment float4 fragmentShader(RasterData in [[stage_in]],
                               constant ShaderUniforms &u [[buffer(0)]]) {
    float2 p = (in.position.xy - u.resolution * 0.5) / max(u.resolution.y, 1.0);
    p.y = -p.y;
    float3 color = shade(p, u.time, in.position.xy);
    return float4(clamp(color, 0.0, 1.0), 1.0);
}
