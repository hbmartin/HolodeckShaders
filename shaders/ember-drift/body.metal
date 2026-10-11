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

// "Sparks from fire" by Jan Mróz (jaszunio15)
// https://www.shadertoy.com/view/wl2Gzc
// License: Creative Commons Attribution 3.0 (CC BY 3.0)
// Ghostty adaptation by Alex Sherwin (ghostty-shaders "sparks-from-fire.glsl").
// Adapted for Holodeck: terminal blending removed; height-normalized coordinates; sin-based hashes
// replaced by fract-based hashes on a 256-cell periodic lattice, and every drift, spin and flutter
// rate quantized so the scene loops seamlessly every 7680 s (precision-safe at large times); four
// denser spark layers with an early-out instead of eight; per-layer noise offsets replaced by one
// static wobble field; smoke reduced to 4 + 2 octaves; uninitialized offsets zeroed; larger sparks
// and bloom, a faint under-glow, exposure, dither and sRGB-style decode for the sRGB render target.

// License terms: https://creativecommons.org/licenses/by/3.0/

constant float hdEmberPeriod = 7680.0;   // seconds; every motion completes whole cycles over this

// Hashes on a 256-cell periodic lattice (cells are wrapped before hashing).
float2 hdEmberWrap(float2 cell) { return cell - 256.0 * floor(cell * (1.0 / 256.0)); }

float4 hdEmberHash4(float2 cell) {
    float4 p4 = fract(hdEmberWrap(floor(cell)).xyxy * float4(0.1031, 0.1030, 0.0973, 0.1099));
    p4 += dot(p4, p4.wzxy + 33.33);
    return fract((p4.xxyz + p4.yzzw) * p4.zywx);
}

// Value noise with smoothstep interpolation; the four corners are hashed together
// (Hoskins hash12, vectorized over corners).
float hdEmberNoise(float2 uv) {
    float2 i = floor(uv), f = smoothstep(0.0, 1.0, uv - i);
    float2 i0 = hdEmberWrap(i), i1 = select(i0 + 1.0, float2(0.0), i0 > 254.5);
    float4 a = fract(float4(i0.x, i1.x, i0.x, i1.x) * 0.1031);
    float4 b = fract(float4(i0.y, i0.y, i1.y, i1.y) * 0.1031);
    float4 d = 2.0 * a * b + a * a + 66.66 * a + 33.33 * b;
    a += d;
    float4 h = fract((a + b + d) * a);
    return mix(mix(h.x, h.y, f.x), mix(h.z, h.w, f.x), f.y);
}

// Sampling offset at n/3 lattice cells per second along (0.7, -1.0), wrapped to the 256-cell lattice.
// Adding this to Y-up coordinates moves the visible field in the opposite direction: left and upward.
float2 hdEmberDrift(float phase, float n) { return 256.0 * fract(phase * n * float2(7.0, -10.0)); }

// Layered value noise; drift[i] are per-octave speeds in thirds of a cell per second.
float hdEmberSmoke(float2 uv, float phase) {
    const float drift[4] = {6.0, 8.0, 13.0, 21.0};
    const float2 offsets[4] = {float2(3.1, 7.4), float2(11.6, 2.9), float2(5.3, 17.8), float2(23.4, 9.1)};
    float noise = 0.0, alpha = 1.0, size = 1.0, total = 0.0;
    for (int i = 0; i < 4; ++i) {
        noise += hdEmberNoise(uv * size + hdEmberDrift(phase, drift[i]) + offsets[i]) * alpha;
        total += alpha;
        alpha *= 0.7;
        size *= 1.7;
    }
    return noise / total;
}

float hdEmberHoles(float2 uv, float phase) {
    float noise = hdEmberNoise(uv + hdEmberDrift(phase, 2.0) + float2(8.3, 1.7));
    noise += 0.5 * hdEmberNoise(uv * 1.8 + hdEmberDrift(phase, 2.0) + float2(19.2, 13.5));
    return noise / 1.5;
}

float2 hdEmberRotate(float2 v, float a) {
    float s = sin(a), c = cos(a);
    return float2(s * v.x - c * v.y, c * v.x + s * v.y);
}

// Recipe: snippets/ember-sparks. One layer of drifting sparks (one per lattice cell): elongated
// core plus bloom, RGB light. uv is in lattice cells, screen is the original-scale screen position
// used for per-spark fade in/out, phase is the 7680 s loop fraction, layerSeed decorrelates layers.
float3 hdEmberLayer(float2 uv, float2 screen, float phase, float layerSeed) {
    const float size = 0.0035;                       // core length scale in cells (original 0.0025)
    const float bloomRadius = size * 9.0;            // original size * 6
    const float reach = bloomRadius / 0.35 + 0.05;   // widest bloom extent plus flutter amplitude
    uv += hdEmberDrift(phase, 1.0) + float2(37.31, 61.77) * layerSeed;
    float2 root = floor(uv);
    float4 h = hdEmberHash4(root);
    float turns = floor((h.x - 0.5) * 2.0 * hdEmberPeriod / 6.2831853 + 0.5);   // spin within [-1, 1] rad/s
    float2 point = root + 0.5 + hdEmberRotate(h.yz - 0.5, 6.2831853 * fract(turns * phase)) * 0.5;
    float2 d = uv - point;
    if (dot(d, d) > reach * reach) return float3(0.0);
    // Flutter: per-cell value noise in time, about 1.4 changes per second.
    float tau = 256.0 * fract(phase * 42.0), n0 = floor(tau);
    float2 flutter = mix(hdEmberHash4(float2(h.w * 251.0, n0)).xy, hdEmberHash4(float2(h.w * 251.0, n0 + 1.0)).xy,
                         smoothstep(0.0, 1.0, tau - n0));
    float2 local = hdEmberRotate(d - (flutter - 0.5) * 0.07, 0.7);
    float dist = length(local * (float2(0.5, 1.6) + (h.yz - 0.5) * float2(0.25, 0.2)));
    float distBloom = length(local * (float2(0.5, 0.8) + (h.yz - 0.5) * float2(0.3, 0.1)));
    float3 light = (1.0 - smoothstep(size * 0.6, size * 3.0, dist)) * float3(1.0, 0.4, 0.05) * 1.5;
    float bloom = 1.0 - smoothstep(0.0, bloomRadius, distBloom);
    light += bloom * bloom * bloom * float3(1.0, 0.4, 0.05) * 0.6;
    float border = (h.x - 0.5) * 2.0;
    float disappear = 1.0 - smoothstep(border, border + 0.5, screen.y);
    border = (h.w - 1.8) * 0.7;
    return light * disappear * smoothstep(border, border + 0.4, screen.y);
}

float3 shade(float2 p, float t, float2 pixel) {
    float phase = (t - hdEmberPeriod * floor(t / hdEmberPeriod)) / hdEmberPeriod;
    float vignette = 1.3 - smoothstep(0.4, 1.4, length(p * 1.125 + float2(0.0, 0.3)));
    float2 uv = p * 2.8125;   // the original's width-normalized coordinates (x1.125) times its 2.5 zoom
    const float3 smokeColor = float3(1.0, 0.43, 0.1) * 0.8;

    float smokeIntensity = hdEmberSmoke(uv * 10.0, phase);
    float rise = smoothstep(-1.0, 1.6, uv.y);
    smokeIntensity *= rise * rise;
    float holes = hdEmberHoles(uv * 4.0, phase);
    float3 smoke = smokeIntensity * smokeColor * vignette * 0.45 * holes * holes * 1.5;

    // Static wobble field bends spark paths (stands in for the original per-layer noise offset).
    float2 wobble = 0.075 * float2(sin(uv.y * 1.9 + sin(uv.x * 1.3)), sin(uv.x * 1.7 + 2.0 + sin(uv.y * 1.1)));
    float3 particles = float3(0.0);
    float size = 1.4, alpha = 1.0, thin = smoothstep(0.0, 1.0, smokeIntensity);
    for (int i = 0; i < 4; ++i) {
        particles += hdEmberLayer(uv * size + wobble, uv, phase, float(i)) * alpha * (1.0 - thin * float(i) * 0.25);
        alpha *= 0.85;
        size *= 1.05;
    }

    float glow = smoothstep(0.75, -0.6, p.y) * 0.05;   // faint fire light from below the frame
    float3 col = (particles + smoke * 1.4 + smokeColor * (0.02 + glow)) * vignette * 2.0;
    col = smoothstep(-0.08, 1.0, col) + (hash21(pixel) - 0.5) / 255.0;
    col = max(col, 0.0);
    return col * col;
}
