// Prismatic Meadow — original Holodeck composition. Analytic, layered geometry:
// faceted terrain, crystal-petal flowers and rooted, phase-coherent wind motion.
// Reuses canonical hash21/noise2 from shared/common.metal and the original
// Holodeck Grid Lines recipe, adapted here as fine terrain inlays.
// No external imagery, textures, temporal buffers or additional passes.
//
// Hash provenance: Dave Hoskins, "Hash without Sine"
// https://www.shadertoy.com/view/4djSRW
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

// Original Holodeck box-filtered grid recipe. Units are terrain coordinates;
// returns coverage, with unresolved lines converging to their mean coverage.
float hdGridLine(float2 coord, float spacing, float thickness, float2 footprint) {
    float2 x = coord / spacing;
    float w = thickness / spacing;
    float2 fp = max(footprint / spacing, 1e-4);
    float2 a = x - 0.5 * fp + 0.5 * w;
    float2 b = x + 0.5 * fp + 0.5 * w;
    float2 coverage = (floor(b) - floor(a)) * w + min(fract(b), w) - min(fract(a), w);
    coverage = saturate(coverage / fp);
    return 1.0 - (1.0 - coverage.x) * (1.0 - coverage.y);
}

float pmCover(float d, float aa) {
    return 1.0 - smoothstep(-aa, aa, d);
}

float pmHex(float2 q) {
    q = abs(q);
    return max(q.x * 0.8660254 + q.y * 0.5, q.y);
}

float pmTriangleWave(float x) {
    return abs(fract(x) * 2.0 - 1.0);
}

// Composite one rooted plant. q uses plant-height units, not pixels. Every
// coverage width comes from a coherent screen footprint supplied by shade().
float3 pmPlant(float3 under, float2 q, float seed, float wind,
               float aa, float haze) {
    float h = 1.45 + 0.55 * seed;
    // Root displacement is identically zero. Both harmonics are periodic.
    float bend = 0.23 * sin(wind) + 0.08 * sin(2.0 * wind + seed * 5.0);
    float u = saturate(q.y / h);
    float stemX = bend * u * u;
    float stemD = max(abs(q.x - stemX) - (0.022 - 0.008 * u),
                     max(-q.y, q.y - h));
    float3 air = float3(0.48, 0.73, 0.49);
    float3 stemColor = mix(float3(0.025, 0.26, 0.18), float3(0.30, 0.76, 0.35),
                          smoothstep(-0.02, 0.02, stemX - q.x));
    stemColor += float3(0.08, 0.31, 0.24)
               * pmCover(abs(q.x - stemX + 0.006) - 0.0025, aa);
    under = mix(under, mix(stemColor, air, haze), pmCover(stemD, aa));

    // Two opposing, angular leaves. Split faces catch the upper-left sun.
    for (int leaf = 0; leaf < 2; ++leaf) {
        float side = leaf == 0 ? -1.0 : 1.0;
        float level = h * (0.31 + 0.22 * float(leaf));
        float attachX = bend * pow(level / h, 2.0);
        float2 v = q - float2(attachX, level);
        float2 axis = float2(side * 0.85, 0.53);
        float2 l = float2(dot(v, axis), dot(v, float2(-axis.y, axis.x)));
        float d = (abs(l.x - 0.22) / 0.25 + abs(l.y) / 0.085 - 1.0) * 0.075;
        float3 leafColor = l.y > 0.0 ? float3(0.47, 0.78, 0.23)
                                            : float3(0.055, 0.43, 0.29);
        leafColor += float3(0.13, 0.42, 0.26)
                   * pmCover(abs(l.y) - 0.005, aa) * step(0.0, l.x);
        under = mix(under, mix(leafColor, air, haze), pmCover(d, aa));
    }

    // Three slender crystal grass blades around the stem's base.
    for (int blade = 0; blade < 3; ++blade) {
        float b = float(blade) - 1.0;
        float bladeH = 0.46 + 0.12 * sin(seed * 19.0 + b);
        float v = saturate(q.y / bladeH);
        float x = b * 0.15 + (b * 0.20 + bend * 0.45) * v * v;
        float d = max(abs(q.x - x) - 0.026 * (1.0 - v),
                      max(-q.y, q.y - bladeH));
        float3 grass = mix(float3(0.055, 0.35, 0.23), float3(0.48, 0.69, 0.18), v);
        under = mix(under, mix(grass, air, haze), pmCover(d, aa));
    }

    // Fold into a single angular petal sector. The diamonds have planar light
    // and shade faces, pale bevels, and a contrasting hexagonal pollen jewel.
    float2 head = q - float2(bend, h);
    float tilt = 0.15 * sin(wind + 0.7);
    float ct = cos(tilt), st = sin(tilt);
    head = float2(ct * head.x + st * head.y, -st * head.x + ct * head.y);
    head /= float2(0.39, 0.31);
    float petals = 5.0 + floor(seed * 3.0);
    float sector = 6.28318530718 / petals;
    float angle = atan2(head.y, head.x);
    float a = floor(angle / sector + 0.5) * sector;
    float2 axis = float2(cos(a), sin(a));
    float2 petal = float2(dot(head, axis), dot(head, float2(-axis.y, axis.x)));
    float pd = (abs(petal.x - 0.57) / 0.49 + abs(petal.y) / 0.27 - 1.0) * 0.24;
    float pa = aa / 0.31;
    float3 pigment = seed < 0.34 ? float3(0.93, 0.29, 0.32)
                    : (seed < 0.69 ? float3(0.56, 0.37, 0.88)
                                   : float3(1.0, 0.73, 0.18));
    float facing = 0.80 + 0.16 * dot(axis, normalize(float2(-0.5, 1.0)));
    float3 crystal = pigment * facing * (petal.y > 0.0 ? 1.10 : 0.69);
    crystal = mix(crystal, float3(0.95, 0.93, 0.83),
                  0.28 * smoothstep(0.30, 1.02, petal.x));
    float bevel = pmCover(abs(pd + 0.012) - 0.009, pa);
    crystal += bevel * float3(0.21, 0.24, 0.22);
    float vein = pmCover(abs(petal.y) - 0.007, pa) * smoothstep(0.25, 0.8, petal.x);
    crystal += vein * float3(0.17, 0.24, 0.23);
    under = mix(under, mix(crystal, air, haze), pmCover(pd, pa));
    float centerD = pmHex(head) - 0.225;
    float3 centerColor = head.x + head.y > 0.0 ? float3(1.0, 0.81, 0.24)
                                                     : float3(0.56, 0.29, 0.065);
    float ring = pmCover(abs(pmHex(head) - 0.19) - 0.014, pa);
    centerColor = mix(centerColor, float3(0.94, 1.0, 0.75), ring * 0.8);
    centerColor = mix(centerColor, float3(0.20, 0.22, 0.12),
                      pmCover(pmHex(head) - 0.085, pa));
    return mix(under, mix(centerColor, air, haze), pmCover(centerD, pa));
}

float3 shade(float2 p, float time, float2 pixel) {
    // All derivative evaluation is outside divergent plant / terrain branches.
    float aa = max(length(dfdx(p)), length(dfdy(p))) * 0.8;
    aa = max(aa, 0.00001);
    float phase = fmod(time * 0.72, 6.28318530718);
    float skyHeight = saturate((p.y - 0.04) * 2.3);
    float3 color = mix(float3(0.71, 0.89, 0.79), float3(0.12, 0.62, 0.86), skyHeight);

    // A sunny, nearly white disk with delicate orbital architecture.
    float2 sun = p - float2(-0.48, 0.32);
    float sunR = length(sun);
    color += float3(0.22, 0.16, 0.055) * exp(-dot(sun, sun) / 0.034);
    color = mix(color, float3(1.0, 0.98, 0.79), pmCover(sunR - 0.047, aa));
    float orbit = pmCover(abs(sunR - 0.067) - 0.0007, aa);
    orbit += pmCover(abs(sunR - 0.074) - 0.00035, aa) * 0.45;
    color = mix(color, float3(0.91, 0.99, 0.87), saturate(orbit) * 0.62);

    // Thin, faceted cloud ribbons. Motion stays bounded and continuous.
    for (int i = 0; i < 3; ++i) {
        float f = float(i);
        float2 q = p - float2(-0.14 + f * 0.47 + 0.016 * sin(phase + f),
                              0.30 + 0.095 * sin(f * 2.6));
        q.x += q.y * 1.7;
        float cloudD = max(abs(q.y) - 0.014,
                           abs(q.x) * 0.14 + abs(q.y) * 0.4 - 0.027);
        color = mix(color, float3(0.91, 0.98, 0.92), pmCover(cloudD, aa) * 0.43);
    }

    // A distant open hexagonal conservatory frame, occluded by the hills.
    // Its two pale structural rails reinforce the futuristic silhouette.
    float2 arch = float2((p.x - 0.43) * 0.83, p.y - 0.045);
    float archD = pmHex(arch);
    float frame = pmCover(abs(archD - 0.158) - 0.0015, aa);
    float innerRail = pmCover(abs(archD - 0.150) - 0.00055, aa);
    color = mix(color, float3(0.87, 0.98, 0.86), frame * 0.73);
    color = mix(color, float3(0.48, 0.91, 0.84), innerRail * 0.65);

    // Distant polygonal hills soften into daylight haze.
    for (int i = 0; i < 3; ++i) {
        float f = float(i);
        float ridge = 0.045 + (2.0 - f) * 0.031
                    + 0.037 * pmTriangleWave(p.x * (0.72 + f * 0.20) + f * 0.39)
                    + 0.017 * pmTriangleWave(p.x * 2.4 + f * 0.2);
        float face = step(0.5, fract(p.x * (0.72 + f * 0.20) + f * 0.39));
        float3 hill = mix(float3(0.38, 0.63, 0.46), float3(0.57, 0.76, 0.44), face);
        hill = mix(hill, float3(0.69, 0.85, 0.71), 0.6 - f * 0.16);
        color = mix(color, hill, pmCover(p.y - ridge, aa));
    }

    // Static perspective facets and restrained turquoise inlays establish a
    // constructed meadow without hiding its daylight greens and flowers.
    float groundY = 0.035 + 0.018 * sin(p.x * 3.2);
    float depth = max(0.13 - p.y, 0.035);
    float2 ground = float2(p.x, 0.8) / depth;
    float2 footprint = fwidth(ground);
    float2 tile = ground * 2.1;
    float2 cell = floor(tile);
    float face = step(fract(tile).x, fract(tile).y);
    float facet = hash21(cell + face * float2(27.3, 13.7));
    float nearMix = saturate((0.08 - p.y) * 2.2);
    float3 green = mix(float3(0.49, 0.70, 0.29), float3(0.055, 0.31, 0.21), nearMix);
    green *= 0.88 + facet * 0.23;
    green += float3(0.13, 0.15, 0.025) * noise2(ground * 0.75);
    float grid = hdGridLine(ground, 1.0, 0.008, footprint);
    green += float3(0.12, 0.49, 0.33) * grid * 0.25 * smoothstep(0.01, 0.19, depth - 0.1);
    color = mix(color, green, pmCover(p.y - groundY, aa));

    // Sixteen back-to-front rows. Each row tests just three adjacent cells;
    // height culling is analytic and contains no fragment derivatives.
    for (int row = 0; row < 16; ++row) {
        float r = float(row) / 15.0;
        float scale = 0.007 + 0.111 * r * r;
        float rootY = 0.037 - 0.76 * r * r;
        float spacing = scale * 1.37;
        float offset = hash21(float2(float(row), 53.2));
        float cellX = floor(p.x / spacing + offset);
        if (p.y < rootY - scale * 0.28 || p.y > rootY + scale * 2.58) continue;
        for (int n = -1; n <= 1; ++n) {
            float id = cellX + float(n);
            float seed = hash21(float2(id, float(row) + 31.8));
            float x = (id + 0.5 - offset + (seed - 0.5) * 0.52) * spacing;
            float y = rootY + scale * (hash21(float2(id + 4.2, float(row))) - 0.5) * 0.28;
            float2 q = (p - float2(x, y)) / scale;
            if (abs(q.x) > 0.85 || q.y < -0.04 || q.y > 2.5) continue;
            float wind = phase + x * 3.3 + float(row) * 0.43;
            color = pmPlant(color, q, seed, wind, aa / scale, 0.46 * pow(1.0 - r, 2.0));
        }
    }

    // Soft directional sunlight keeps crystal facets warm in the foreground.
    color += float3(0.027, 0.019, 0.004) * exp(-dot(sun, sun) * 1.8);
    return clamp(color, 0.0, 1.0);
}
