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
// Apollonian Twist
// Original: "Apollian with a twist" by mrange — https://www.shadertoy.com/view/Wl3fzM (CC0)
// Metal port: "Apollonian Gasket" by Astemir Eleev, swiftui-new-metal-shaders
// https://github.com/eleev/swiftui-new-metal-shaders (SUIMetal/Shaders/ApollonianGasket.metal)
// Copyright (c) 2023 Astemir Eleev, MIT License
// Adapted for Holodeck: float throughout; Y-up framing of the Shadertoy
// original (p * 2); half speed with per-term wrapped time phases; rotations
// hoisted out of the distance field; fewer folds for the soft shadow lookups;
// resolution-independent line core with derivative anti-aliasing; guarded
// inversion and pow; the gamma-space grade is decoded back to linear for the
// sRGB target; vignette uses the aspect ratio recovered from raster position.

// MIT notice for swiftui-new-metal-shaders (preserved from upstream):
// Copyright (c) 2023 Astemir Eleev
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

float hdApollonianDf(float2 p, float2x2 spin, float2x2 rotYZ, float2x2 rotXZ, float3 offset, int iterations) {
    const float zoom = 0.5;
    const float z = 4.0;
    p /= zoom;
    p = p * spin;

    float4 pp = float4(p.x + offset.x, p.y + offset.y, offset.z, 0.0);
    pp.w = 0.125 * (1.0 - tanh(length(pp.xyz)));
    pp.yz = pp.yz * rotYZ;
    pp.xz = pp.xz * rotXZ;
    pp /= z;

    float scale = 1.0;
    for (int i = 0; i < iterations; ++i) {
        pp = -1.0 + 2.0 * fract(0.5 * pp + 0.5);
        float k = 1.2 / max(dot(pp, pp), 1e-6);
        pp *= k;
        scale *= k;
    }
    return abs(pp.y) / scale * z * zoom;
}

float2x2 hdApollonianRotation(float angle) {
    float c = cos(angle), s = sin(angle);
    return float2x2(c, s, -s, c);
}

float3 hdHsvToRgb(float3 hsv) {
    const float4 K = float4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    float3 q = clamp(abs(fract(hsv.xxx + K.xyz) * 6.0 - K.www) - K.xxx, 0.0, 1.0);
    return hsv.z * mix(K.xxx, q, hsv.y);
}

float3 shade(float2 p, float t, float2 pixel) {
    const float tau = 6.2831853;
    const float contrast = 0.6;
    const float saturation = 0.33;
    const float vignetting = 0.5;

    // Shadertoy framing: p in [-1, 1] vertically, Y up.
    float2 sp = p * 2.0;
    float aa = 2.0 * fwidth(p.y);

    // Half the original pace for a slow screensaver. Each phase is wrapped at
    // its own period (the offset frequencies are mutually irrational).
    float time = t * 0.5;
    float2x2 spin = hdApollonianRotation(fmod(time * 0.1, tau));
    float2x2 rotYZ = hdApollonianRotation(fmod(time * 0.2, tau));
    float2x2 rotXZ = hdApollonianRotation(fmod(time * 0.2 * sqrt(0.5), tau));
    const float r = 0.5;
    float3 offset = r * (0.5 + 0.5 * sin(float3(fmod(time * 0.2 * sqrt(3.0), tau),
                                                 fmod(time * 0.2 * sqrt(1.5), tau),
                                                 fmod(time * 0.2 * sqrt(2.0), tau))));

    const float lh = 1.25;
    const float3 lp1 = float3(0.5, lh, 0.5);
    const float3 lp2 = float3(-0.5, lh, 0.5);

    float d = hdApollonianDf(sp, spin, rotYZ, rotXZ, offset, 7);

    // Ground plane below the pattern; trace shadow rays toward two lights.
    const float b = -0.125;
    const float camera = 10.0;
    float3 ro = float3(0.0, camera, 0.0);
    float3 rd = normalize(float3(sp.x, 0.0, sp.y) - ro);
    float bt = -(camera - b) / rd.y;
    float3 bp = ro + bt * rd;
    float3 srd1 = normalize(lp1 - bp);
    float3 srd2 = normalize(lp2 - bp);
    float bl21 = dot(lp1 - bp, lp1 - bp);
    float bl22 = dot(lp2 - bp, lp2 - bp);
    float st1 = (0.0 - b) / srd1.y;
    float3 sp1 = bp + srd1 * st1;
    float3 sp2 = bp + srd2 * st1;  // as in the original
    // Soft shadows hide the finest circles, so their lookups fold fewer times.
    float sd1 = hdApollonianDf(sp1.xz, spin, rotYZ, rotXZ, offset, 4);
    float sd2 = hdApollonianDf(sp2.xz, spin, rotYZ, rotXZ, offset, 4);

    const float ss = 15.0;
    float3 col = float3(0.0);
    col += float3(1.0) * (1.0 - exp(-ss * max(sd1, 0.0))) / bl21;
    col += float3(0.5) * (1.0 - exp(-ss * max(sd2, 0.0))) / bl22;

    float l = length(sp);
    float hue = fract(0.75 * l - fract(0.3 * time)) + 0.45;
    float sat = 0.75 * tanh(2.0 * l);
    float3 bcol = hdHsvToRgb(float3(hue, sat, 1.0));

    col *= (1.0 - tanh(0.75 * l)) * 0.5;
    // Line core has a fixed screen-relative half-width so 4K matches the preview.
    const float lineWidth = 0.0012;
    col = mix(col, bcol, smoothstep(-aa, aa, lineWidth - d));
    col += 0.5 * sqrt(bcol.zxy) * exp(-(10.0 + 100.0 * tanh(l)) * max(d, 0.0));

    // Display-space grade from the original.
    col = pow(clamp(col, 0.0, 1.0), float3(1.0 / 2.2));
    col = col * contrast + 0.4 * col * col * (3.0 - 2.0 * col);
    col = mix(col, float3(dot(col, float3(saturation))), -0.4);

    // Vignette in 0..1 screen space; aspect recovered from raster position.
    float aspect = 2.0 * (pixel.x * fwidth(p.y) - p.x);
    float2 q = float2(p.x / aspect + 0.5, 0.5 - p.y);
    col *= 0.5 + 0.5 * pow(max(19.0 * q.x * q.y * (1.0 - q.x) * (1.0 - q.y), 0.0), vignetting);

    // Back to linear for the sRGB render target.
    return pow(max(col, 0.0), float3(2.2));
}

fragment float4 fragmentShader(RasterData in [[stage_in]],
                               constant ShaderUniforms &u [[buffer(0)]]) {
    float2 p = (in.position.xy - u.resolution * 0.5) / max(u.resolution.y, 1.0);
    p.y = -p.y;
    float3 color = shade(p, u.time, in.position.xy);
    return float4(clamp(color, 0.0, 1.0), 1.0);
}
