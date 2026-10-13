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
// Force Shield — original Holodeck implementation inspired by "flow-shield-effect" by Christian Ortiz (https://github.com/cortiz2894/flow-shield-effect). No code copied.
// Simplex noise: Copyright (C) 2011 Ashima Arts (Ian McEwan, Stefan Gustavson). MIT License: https://github.com/ashima/webgl-noise

// --- simplex-noise-3d recipe (port of Ashima noise3D.glsl) ---
// MIT notice for ashima-webgl-noise (preserved from upstream):
// Copyright (C) 2011 by Ashima Arts (Simplex noise)
// Copyright (C) 2011-2016 by Stefan Gustavson (Classic noise and others)
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
// THE SOFTWARE.

float3 hdMod289(float3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
float4 hdMod289(float4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
float4 hdPermute(float4 x) { return hdMod289(((x * 34.0) + 10.0) * x); }
float4 hdTaylorInvSqrt(float4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float hdSimplex3(float3 v) {
    const float2 C = float2(1.0 / 6.0, 1.0 / 3.0);
    const float4 D = float4(0.0, 0.5, 1.0, 2.0);
    float3 i = floor(v + dot(v, C.yyy));
    float3 x0 = v - i + dot(i, C.xxx);
    float3 g = step(x0.yzx, x0.xyz);
    float3 l = 1.0 - g;
    float3 i1 = min(g.xyz, l.zxy);
    float3 i2 = max(g.xyz, l.zxy);
    float3 x1 = x0 - i1 + C.xxx;
    float3 x2 = x0 - i2 + C.yyy;
    float3 x3 = x0 - D.yyy;
    i = hdMod289(i);
    float4 p = hdPermute(hdPermute(hdPermute(i.z + float4(0.0, i1.z, i2.z, 1.0))
                                   + i.y + float4(0.0, i1.y, i2.y, 1.0))
                         + i.x + float4(0.0, i1.x, i2.x, 1.0));
    float n_ = 0.142857142857;
    float3 ns = n_ * D.wyz - D.xzx;
    float4 j = p - 49.0 * floor(p * ns.z * ns.z);
    float4 x_ = floor(j * ns.z);
    float4 y_ = floor(j - 7.0 * x_);
    float4 x = x_ * ns.x + ns.yyyy;
    float4 y = y_ * ns.x + ns.yyyy;
    float4 h = 1.0 - abs(x) - abs(y);
    float4 b0 = float4(x.xy, y.xy);
    float4 b1 = float4(x.zw, y.zw);
    float4 s0 = floor(b0) * 2.0 + 1.0;
    float4 s1 = floor(b1) * 2.0 + 1.0;
    float4 sh = -step(h, float4(0.0));
    float4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
    float4 a1 = b1.xzyw + s1.xzyw * sh.zzww;
    float3 p0 = float3(a0.xy, h.x);
    float3 p1 = float3(a0.zw, h.y);
    float3 p2 = float3(a1.xy, h.z);
    float3 p3 = float3(a1.zw, h.w);
    float4 norm = hdTaylorInvSqrt(float4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
    p0 *= norm.x;
    p1 *= norm.y;
    p2 *= norm.z;
    p3 *= norm.w;
    float4 m = max(0.5 - float4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)), 0.0);
    m = m * m;
    return 105.0 * dot(m * m, float4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3)));
}

// --- hex-grid recipe ---
float4 hdHexCell(float2 p) {
    const float2 s = float2(1.0, 1.7320508);
    float2 a = p - s * floor(p / s) - 0.5 * s;
    float2 q = p - 0.5 * s;
    float2 b = q - s * floor(q / s) - 0.5 * s;
    float2 local = dot(a, a) < dot(b, b) ? a : b;
    float2 centre = p - local;
    return float4(local, round(centre.x * 2.0), round(centre.y * 1.1547005));
}

float hdHexEdge(float2 local, float width, float footprint) {
    float2 q = abs(local);
    float d = 0.5 - max(q.x, dot(q, float2(0.5, 0.8660254)));
    float aa = max(footprint, 1e-4);
    float line = 1.0 - smoothstep(width - aa, width + aa, d);
    float mean = 1.0 - (1.0 - 2.0 * width) * (1.0 - 2.0 * width);
    return mix(line, mean, smoothstep(0.12, 0.3, aa));
}

float hdCellFlash(float2 cellId, float t, float rate) {
    float seed = hash21(cellId);
    float local = t * rate + seed * 17.0;
    float cycle = floor(local);
    float f = local - cycle;
    float on = step(0.93, hash21(cellId + fmod(cycle, 509.0) * float2(1.37, 0.71)));
    float pulse = 4.0 * f * (1.0 - f);
    return on * pulse * pulse;
}

float4 hdSphereHexCell(float3 n, float cellsPerEdge) {
    float3 w = asin(min(abs(n), 1.0));
    w /= w.x + w.y + w.z;
    float2 plane = cellsPerEdge * float2(w.y + 0.5 * w.z, 0.8660254 * w.z);
    float4 cell = hdHexCell(plane);
    float c = cell.w;
    float b = (cell.z - c) * 0.5;
    float3 k = float3(cellsPerEdge - b - c, b, c) * select(float3(-1.0), float3(1.0), n >= 0.0);
    return float4(cell.xy, k.x + 37.0 * k.z, k.y - 53.0 * k.z);
}

// --- sphere-shell recipe ---
float2 hdRaySphere(float3 ro, float3 rd, float radius) {
    float b = dot(ro, rd);
    float h = b * b - (dot(ro, ro) - radius * radius);
    if (h < 0.0) return float2(-1.0);
    h = sqrt(h);
    return float2(-b - h, -b + h);
}

float hdFresnel(float3 n, float3 v, float power) {
    return pow(1.0 - saturate(abs(dot(n, v))), power);
}

float hdSphereHalo(float3 ro, float3 rd, float radius, float falloff) {
    float along = max(dot(-ro, rd), 0.0);
    float d = length(ro + rd * along);
    return exp(-falloff * max(d - radius, 0.0) / radius);
}

// --- impact-ripple recipe ---
float2 hdImpact(float3 n, float3 hitDir, float age, float duration) {
    float life = age / duration;
    if (life < 0.0 || life >= 1.0) return float2(0.0);
    float g = acos(clamp(dot(n, hitDir), -1.0, 1.0));
    float2 q = float2(dot(n, float3(2.7, 1.3, -1.9)), dot(n, float3(-1.4, 2.2, 2.9)));
    float wobble = noise2(q * 1.5 + age * 0.9) - 0.5;
    float ease = 1.0 - (1.0 - life) * (1.0 - life);
    float width = 0.03 + 0.06 * life;
    float d = (g - 2.4 * ease + wobble * 0.35 * ease) / width;
    float fade = (1.0 - life) * (1.0 - life) * smoothstep(0.0, 0.04, life);
    float ring = (exp(-d * d) + 0.2 * exp(-d * d * 0.12) * step(d, 0.0)) * fade;
    float zone = exp(-g * g * 8.0) * (1.0 - life) * (1.0 - life) * (1.0 - life);
    return float2(ring, zone);
}

float4 hdScheduledHit(float t, float slot, float period) {
    float local = t / period + slot * 0.618034;
    float cycle = floor(local);
    float age = (local - cycle) * period;
    float key = fmod(cycle, 997.0);
    float azimuth = (hash21(float2(key, slot * 7.3 + 1.0)) - 0.5) * 1.9;
    float elevation = (hash21(float2(key * 1.37 + 4.1, slot + 2.2)) - 0.35) * 1.2;
    float3 direction = float3(sin(azimuth) * cos(elevation), sin(elevation), cos(azimuth) * cos(elevation));
    return float4(direction, age);
}

// --- noise-dissolve recipe ---
float2 hdDissolve(float noiseValue, float reveal, float width) {
    float d = mix(-width, 1.0 + width, saturate(reveal)) - noiseValue;
    float visible = smoothstep(-0.15 * width, 0.15 * width, d);
    float edge = visible * (1.0 - smoothstep(0.0, width, d));
    return float2(visible, edge);
}

// --- scene ---
constant float3 kShieldCyan = float3(0.149, 0.682, 1.0);
constant float kFloorY = -0.62;
constant float kImpactDuration = 3.2;

float hdShieldReveal(float t) {
    float c = fmod(t, 67.0);
    float down = smoothstep(52.0, 56.0, c);
    float up = smoothstep(57.0, 61.5, c);
    return 1.0 - down + up;
}

float3 hdShieldSurface(float3 n, float3 v, float distance, float pixelAngle, float t, float3x3 latticeFrame,
                       float2 flowPhase, float4 hits[3], float reveal, bool backFace) {
    float fres = hdFresnel(n, v, 1.8);

    // analytic pixel footprint in lattice units (12 cells per quarter great circle)
    float footprint = distance * pixelAngle * (12.0 / 1.5707963) / max(abs(dot(n, v)), 0.12);
    float4 cell = hdSphereHexCell(latticeFrame * n, 12.0);
    float2 hq = abs(cell.xy);
    float border = 0.5 - max(hq.x, dot(hq, float2(0.5, 0.8660254)));
    float edge = hdHexEdge(cell.xy, 0.03, footprint);
    float panel = smoothstep(0.02, 0.09, border);
    float cellSeed = hash21(cell.zw);

    // drifting two-octave flow shimmer, upward across the shell
    const float3x3 flowFrame = float3x3(float3(0.7071068, -0.7071068, 0.0),
                                        float3(0.5773503, 0.5773503, 0.5773503),
                                        float3(0.4082483, 0.4082483, -0.8164966));
    float3 q = flowFrame * n;
    float f = hdSimplex3(q * 1.7 - flowPhase.x);
    f = backFace ? f : 0.65 * f + 0.35 * hdSimplex3(q * 3.9 - flowPhase.y + 17.0);
    float filament = pow(saturate(1.0 - abs(f)), 6.0);
    float shimmer = smoothstep(-0.35, 0.65, f);

    float energy = 0.006 + edge * 0.13 * (0.2 + 3.0 * fres) * (0.35 + 1.9 * shimmer);
    energy += filament * (0.03 + 0.5 * fres) * 0.5;
    energy += fres * 0.55 + pow(fres, 6.0) * 1.2;
    energy += hdCellFlash(cell.zw, t, 0.3) * panel * 0.22;

    float ring = 0.0;
    for (int k = 0; k < 3; ++k) {
        if (hits[k].w < kImpactDuration) {
            float2 impact = hdImpact(n, hits[k].xyz, hits[k].w, kImpactDuration);
            ring += impact.x;
            energy += impact.y * panel * step(cellSeed, impact.y * 1.4) * 0.5 + impact.y * 0.12;
        }
    }

    float3 light = kShieldCyan * energy + mix(kShieldCyan, float3(0.85, 0.97, 1.0), 0.4) * ring * 0.9;

    if (reveal < 0.999) {
        float2 dq = float2(dot(n, float3(0.8, 0.15, 0.55)), dot(n, float3(-0.35, 0.85, 0.4)));
        float detail = 0.65 * noise2(dq * 3.2 + 4.0) + 0.35 * noise2(dq * 8.5 - 2.0);
        float noiseValue = saturate(0.55 * (n.y * 0.5 + 0.5) + 0.45 * detail);
        float2 dissolve = hdDissolve(noiseValue, reveal, 0.035);
        light = light * dissolve.x + float3(0.45, 0.85, 1.0) * dissolve.y * 0.9;
    }
    return light;
}

float3 shade(float2 p, float t, float2 pixel) {
    float3 ro = float3(0.0, 0.45, 4.3);
    float3 forward = normalize(float3(0.0, -0.08, 0.0) - ro);
    float3 right = normalize(cross(forward, float3(0.0, 1.0, 0.0)));
    float3 up = cross(right, forward);
    float3 rd = normalize(p.x * right + p.y * up + 1.45 * forward);

    float reveal = hdShieldReveal(t);
    float pixelAngle = fwidth(p.y) / 1.45;

    // background: deep blue-black with a faint vertical gradient
    float3 color = mix(float3(0.0003, 0.0006, 0.0016), float3(0.0012, 0.0026, 0.0060), smoothstep(-0.6, 0.6, p.y));

    // floor glow where the shield meets the ground
    float tFloor = rd.y < 0.0 ? (kFloorY - ro.y) / rd.y : 1e5;
    if (tFloor < 1e4) {
        float3 fp = ro + rd * tFloor;
        float radius = length(fp.xz);
        float contact = sqrt(1.0 - kFloorY * kFloorY);
        float glow = exp(-abs(radius - contact) * 9.0) * 0.07 + exp(-radius * 1.6) * 0.015;
        color += kShieldCyan * glow * (0.25 + 0.75 * reveal) * exp(-tFloor * 0.08);
    }

    // soft halo in place of bloom
    float along = max(dot(-ro, rd), 0.0);
    float closest = length(ro + rd * along);
    float halo = hdSphereHalo(ro, rd, 1.0, 7.0) * 0.05 + hdSphereHalo(ro, rd, 1.0, 2.0) * 0.012;
    halo *= smoothstep(0.55, 1.0, closest);
    halo *= smoothstep(kFloorY - 0.15, kFloorY + 0.45, ro.y + rd.y * along);
    color += kShieldCyan * halo * (0.05 + 0.95 * reveal);

    float2 hit = hdRaySphere(ro, rd, 1.0);
    if (hit.y > 0.0) {
        float4 hits[3];
        for (int k = 0; k < 3; ++k) hits[k] = hdScheduledHit(t + 13.4, float(k), 8.5 + float(k) * 3.1);
        float spin = fmod(t * 0.035, 6.2831853);
        float cs = cos(spin), sn = sin(spin);
        const float3x3 tilt = float3x3(float3(0.7071068, -0.7071068, 0.0),
                                       float3(0.4082483, 0.4082483, -0.8164966),
                                       float3(0.5773503, 0.5773503, 0.5773503));
        float3x3 latticeFrame = tilt * float3x3(float3(cs, 0.0, -sn), float3(0.0, 1.0, 0.0), float3(sn, 0.0, cs));
        float2 flowPhase = float2(fmod(t * 0.09, 289.0), fmod(t * 0.14, 289.0));
        float3 v = -rd;
        float coverage = saturate((1.0 - closest) / max(along * pixelAngle, 1e-5));

        float3 back = ro + rd * hit.y;
        if (back.y > kFloorY) {
            float fade = smoothstep(kFloorY, kFloorY + 0.55, back.y);
            color += hdShieldSurface(back, v, hit.y, pixelAngle, t, latticeFrame, flowPhase, hits, reveal, true) * 0.35 * fade * coverage;
        }
        float3 front = ro + rd * hit.x;
        if (front.y > kFloorY) {
            float fade = smoothstep(kFloorY, kFloorY + 0.55, front.y);
            color += hdShieldSurface(front, v, hit.x, pixelAngle, t, latticeFrame, flowPhase, hits, reveal, false) * fade * coverage;
        }
    }

    color *= 1.0 - 0.35 * dot(p, p);
    color = 1.0 - exp(-color * 1.1);
    float grain = hash21(pixel + fract(t) * 97.0) - 0.5;
    color += grain * (2.2 / 255.0) * sqrt(max(color, 1e-4));
    return color;
}

fragment float4 fragmentShader(RasterData in [[stage_in]],
                               constant ShaderUniforms &u [[buffer(0)]]) {
    float2 p = (in.position.xy - u.resolution * 0.5) / max(u.resolution.y, 1.0);
    p.y = -p.y;
    float3 color = shade(p, u.time, in.position.xy);
    return float4(clamp(color, 0.0, 1.0), 1.0);
}
