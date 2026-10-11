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

// Derived from "Sparks from fire" by Jan Mróz (jaszunio15), https://www.shadertoy.com/view/wl2Gzc, CC BY 3.0.
// Keep this attribution when adapting.

// License terms: https://creativecommons.org/licenses/by/3.0/

constant float hdEmberPeriod = 7680.0;   // seconds; every motion completes whole cycles over this

// Hashes on a 256-cell periodic lattice (cells are wrapped before hashing).
float2 hdEmberWrap(float2 cell) { return cell - 256.0 * floor(cell * (1.0 / 256.0)); }

float4 hdEmberHash4(float2 cell) {
    float4 p4 = fract(hdEmberWrap(floor(cell)).xyxy * float4(0.1031, 0.1030, 0.0973, 0.1099));
    p4 += dot(p4, p4.wzxy + 33.33);
    return fract((p4.xxyz + p4.yzzw) * p4.zywx);
}

// Sampling offset at n/3 lattice cells per second along (0.7, -1.0), wrapped to the 256-cell lattice.
// Adding this to Y-up coordinates moves the visible field in the opposite direction: left and upward.
float2 hdEmberDrift(float phase, float n) { return 256.0 * fract(phase * n * float2(7.0, -10.0)); }

float2 hdEmberRotate(float2 v, float a) {
    float s = sin(a), c = cos(a);
    return float2(s * v.x - c * v.y, c * v.x + s * v.y);
}

// One layer of drifting sparks (one per lattice cell): elongated core plus bloom, RGB light.
// uv is in lattice cells, screen is the original-scale screen position used for per-spark fade
// in/out, phase is the 7680 s loop fraction, layerSeed decorrelates layers.
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
