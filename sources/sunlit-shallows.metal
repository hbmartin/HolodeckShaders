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

// Sunlit Shallows: original Holodeck implementation; inspired by the Ghostty underwater/water shaders
// (no code copied). Voronoi adapted from SwiftShaders (MIT, Copyright (c) 2024 Muhittin Camdali,
// https://github.com/muhittincamdali/SwiftShaders, commit 4acb3a91).
// Every animation wraps on its own period (caustics 18 s, swell 40 s, focus 240 s, rays 600 s,
// marine snow 1280 s), so the scene stays precise at large times.

// Recipe: snippets/voronoi (MIT, adapted from SwiftShaders by Muhittin Camdali).
// MIT notice for swiftshaders (preserved from upstream):
// Copyright (c) 2024 Muhittin Camdali
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

float2 hdVoronoiHash22(float2 p) {
    float3 p3 = fract(float3(p.xyx) * float3(0.1031, 0.1030, 0.0973));
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.xx + p3.yz) * p3.zy);
}

float2 hdVoronoiF1F2(float2 p, float phase, float jitter) {
    float2 ip = floor(p), fp = p - ip;
    float s = sin(phase) * 0.35 * jitter, c = cos(phase) * 0.35 * jitter;
    float f1 = 8.0, f2 = 8.0;
    for (int y = -1; y <= 1; ++y) {
        for (int x = -1; x <= 1; ++x) {
            float2 n = float2(float(x), float(y));
            float2 v = hdVoronoiHash22(ip + n) * 2.0 - 1.0;
            // Each feature point circles its cell center; the random vector v sets radius and start angle.
            float2 diff = n + 0.5 + float2(c * v.x - s * v.y, s * v.x + c * v.y) - fp;
            float d = dot(diff, diff);
            f2 = d < f1 ? f1 : min(f2, d);
            f1 = min(f1, d);
        }
    }
    return sqrt(float2(f1, f2));
}

// Recipe: snippets/god-rays (original).
float hdGodRays(float2 p, float2 source, float t) {
    float2 d = p - source;
    float k = d.x / max(-d.y, 1e-3);
    float a = 6.2831853 * fract(t * (1.0 / 600.0));
    float2 drift = 9.5 * float2(cos(a), sin(a));
    k += 0.035 * sin(7.0 * a);
    float n = 0.65 * noise2(float2(k * 9.0, 0.0) + drift) + 0.35 * noise2(float2(k * 23.0, 5.0) - 1.7 * drift);
    float shafts = smoothstep(0.42, 0.85, n);
    return shafts * shafts;
}

// Caustic net: union of two warped Voronoi edge networks (F2 - F1) with soft exponential line
// profiles; line width never drops below a pixel (fwidth), and sub-pixel lines fade instead of aliasing.
float hdShallowsCaustics(float2 q, float phase) {
    q += 0.30 * float2(sin(q.y * 1.3 + phase), sin(q.x * 1.1 - phase))
       + 0.18 * float2(sin(q.y * 2.9 - 2.0 * phase + 1.0), sin(q.x * 3.1 + 2.0 * phase));
    float2 a = hdVoronoiF1F2(q, phase, 0.9);
    float2 b = hdVoronoiF1F2(q * 1.37 + float2(3.7, 1.9), 1.3 - phase, 0.9);
    float ea = a.y - a.x, eb = b.y - b.x;
    float wa = max(0.05, fwidth(ea)), wb = max(0.05, fwidth(eb));
    float la = exp(-ea / wa) * (0.05 / wa), lb = exp(-eb / wb) * (0.05 / wb);
    return max(la, lb) + 0.6 * la * lb;
}

float3 shade(float2 p, float t, float2 pixel) {
    const float loop = 6.2831853 / 0.35;                 // caustic phase loop (rad / speed)
    float phase = 6.2831853 * fract(t / loop);

    // Open water: dim blue depths below, bright green-cyan toward the surface.
    float up = smoothstep(-0.5, 0.5, p.y);
    float3 water = mix(float3(0.002, 0.016, 0.030), float3(0.010, 0.120, 0.150), up * up);
    water += float3(0.020, 0.110, 0.110) * smoothstep(0.15, 0.48, p.y);

    // Rippled surface seen from below: a bright plane receding toward the top edge.
    float swell = 6.2831853 * fract(t / 40.0);
    float ys = 0.405 + 0.010 * sin(p.x * 7.0 + swell) + 0.006 * sin(p.x * 17.0 - 2.0 * swell + 1.3);
    float aa = fwidth(p.y) * 1.5;
    float surface = smoothstep(ys - aa, ys + aa, p.y);
    float3 col = water;
    if (p.y > ys - 0.02) {
        float zs = 0.12 / max(p.y - 0.30, 0.02);
        float2 sq = float2(p.x * zs, zs) * 11.0;
        float rip = sin(sq.x * 1.7 + sin(sq.y * 1.3 + swell) * 1.5 + swell) * sin(sq.y * 2.3 - swell + sin(sq.x * 0.9));
        float glint = smoothstep(0.55, 1.0, rip);
        float3 sky = float3(0.22, 0.50, 0.50) * (0.8 + 0.25 * smoothstep(0.42, 0.5, p.y)) + float3(0.30, 0.45, 0.40) * glint;
        col = mix(water, sky, surface);
    }
    col += float3(0.25, 0.45, 0.42) * exp(-abs(p.y - ys) * 60.0) * (1.0 - surface * 0.5);   // bright edge

    // Sandy floor in perspective below the horizon, lit by caustics and fogged with distance.
    const float horizon = 0.04;
    if (p.y < horizon - 0.002) {
        float z = 0.22 / (horizon - p.y);
        float2 fq = float2(p.x * z, z) * 5.0;
        float fog = exp(-z * 0.55);
        float sand = 0.85 + 0.15 * noise2(fq * 3.0);
        float3 floorCol = float3(0.075, 0.090, 0.065) * sand;
        float slow = 6.2831853 * fract(t / 240.0);
        float focus = 0.45 + 1.1 * noise2(fq * 0.45 + 3.0 * float2(cos(slow), sin(slow)));
        float c = hdShallowsCaustics(fq, phase) * focus;
        floorCol += float3(0.22, 0.34, 0.26) * c;
        col = mix(col, floorCol, fog);
    }

    // Light shafts from above, strongest near the surface.
    float rays = hdGodRays(p, float2(0.25, 1.4), t);
    col += float3(0.10, 0.22, 0.20) * rays * smoothstep(-0.55, 0.42, p.y) * (1.0 - surface);

    // Marine snow: two layers slowly sinking and drifting on 64-cell periodic lattices (loop 1280 s).
    float snowPhase = fract(t / 1280.0);
    for (int i = 0; i < 2; ++i) {
        float layer = float(i);
        float2 q = p * (16.0 + 10.0 * layer) + 64.0 * fract(snowPhase * 4.0 * (1.0 + layer) * float2(1.0, 2.0)) + layer * 17.0;
        float2 cell = floor(q);
        float2 h = hdVoronoiHash22(cell - 64.0 * floor(cell / 64.0) + layer * 64.0);
        float2 o = 0.2 + 0.6 * h;
        float r = length(q - cell - o);
        float speck = smoothstep(0.07, 0.0, r) * step(0.82, h.x * 0.6 + h.y * 0.4 + 0.15);
        col += float3(0.10, 0.16, 0.15) * speck * (0.5 + 0.5 * up) * (1.0 - surface);
    }
    return col;
}

fragment float4 fragmentShader(RasterData in [[stage_in]],
                               constant ShaderUniforms &u [[buffer(0)]]) {
    float2 p = (in.position.xy - u.resolution * 0.5) / max(u.resolution.y, 1.0);
    p.y = -p.y;
    float3 color = shade(p, u.time, in.position.xy);
    return float4(clamp(color, 0.0, 1.0), 1.0);
}
