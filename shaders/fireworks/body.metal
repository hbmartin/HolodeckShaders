// "Fireworks" by Martijn Steinrucken aka BigWings (2015)
// https://www.shadertoy.com/view/lscGRl (via the ghostty-shaders "fireworks.glsl" port)
// Original header: "License Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License."
// Hash functions after Dave Hoskins ("Hash without Sine").
// Adapted for Holodeck: terminal blending removed; Y-up height-normalized coordinates; two staggered
// burst streams of 36 particles (was three of 42) with directions from a golden-angle rotation and
// radii from a cheap chaotic map; per-burst values hoisted out of the particle loop; glows cut
// smoothly to zero at 12 particle sizes so pixels outside a burst skip its loop; pow-free sparkle;
// saturated hue per burst; rainbow cycling kept but applied to firework light only (no sky cast),
// with time wrapped on its exact 20*pi period; night-sky gradient, faint stars and burst flashes
// on the horizon haze; exponential tone mapping.
// This adaptation is licensed CC BY-NC-SA 3.0.

// License terms: https://creativecommons.org/licenses/by-nc-sa/3.0/

float3 hdFwHash31(float p) {
    float3 p3 = fract(float3(p) * float3(0.1031, 0.11369, 0.13787));
    p3 += dot(p3, p3.yzx + 19.19);
    return fract(float3((p3.x + p3.y) * p3.z, (p3.x + p3.z) * p3.y, (p3.y + p3.z) * p3.x));
}

// Saturated rainbow hue without trig.
float3 hdFwHue(float h) {
    return clamp(abs(fract(h + float3(0.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0) - 1.0, 0.0, 1.0);
}

// One burst at local time t in [0, 1): scalar glow (unbounded, size^2/d^2 per particle, cut to zero
// at 12.0 sizes so pixels outside the burst's bounding circle skip all particle work).
float hdFireworkBurst(float2 uv, float2 center, float3 en, float t) {
    float pt = 1.0 - (t - 1.0) * (t - 1.0);
    float2 d0 = uv - center + pt * float2(0.0, 0.1 * t * t + 0.2 * t);
    float size = mix(0.01, 0.005, smoothstep(0.0, 0.1, pt)) * smoothstep(1.0, 0.1, pt) * 1.4;
    float band = smoothstep(en.x - en.z, en.x + en.z, t) * smoothstep(en.y + en.z, en.y - en.z, t) * 0.01 * 1.4;
    float glowR = 12.0 * (size + band);
    float reach = 0.42 * pt + glowR;
    if (dot(d0, d0) > reach * reach) return 0.0;
    float cut = 1.0 / (glowR * glowR + 1e-8);
    float sharp = en.x * en.x * en.x * 25.0;
    float spread = pt * 0.42;
    float2 dir = float2(cos(en.y * 6.2831853), sin(en.y * 6.2831853));
    const float2x2 golden = float2x2(float2(-0.7373688, 0.6754903), float2(-0.6754903, -0.7373688));
    float r = fract(en.x * 91.7 + en.y * 13.3);
    float glow = 0.0;
    for (int i = 0; i < 36; ++i) {
        r = fract(r * 3.7319 + 0.3713);               // chaotic shift map: cheap per-particle random
        float nz = r * 2.0 - 1.0;
        float2 d = d0 - (spread * nz) * dir;
        float s = size;
        if (band > 0.0) {
            float sparkle = max(1.0 - sharp * (0.5 - 0.5 * sin((pt + nz) * 21.0)), 0.0);
            s += sparkle * sparkle * band;
        }
        float q = max(dot(d, d), 1e-6);
        glow += s * s * max(1.0 / q - cut, 0.0) * max(1.0 - q * cut, 0.0);   // C1 cut-off at glowR
        dir = golden * dir;
    }
    return glow;
}

// The original's rainbow cycling: per-channel saturation swing plus a slow color cast,
// written with angle-addition identities (4 trig calls instead of 6).
float3 hdFwRainbow(float3 c, float phase) {
    float avg = (c.r + c.g + c.b) / 3.0;
    float s1 = sin(phase), c1 = cos(phase);
    float3 swing = s1 * float3(1.0, 0.9451, 0.7863) + c1 * float3(0.0, 0.3269, 0.6178);   // sin(phase + {0, .333, .666})
    c = avg + (c - avg) * swing;
    float s3 = sin(0.3 * phase), c3 = cos(0.3 * phase);
    float3 cast = float3(sin(0.4 * phase + 1.1244), s3 * -0.9581 + c3 * -0.2865, s3 * 0.9885 + c3 * 0.1512);
    return c * (1.0 + cast * float3(0.4, 0.1, 0.5) * 1.0);
}

float3 hdFwSky(float2 p, float t) {
    float3 sky = mix(float3(0.0035, 0.0045, 0.0140), float3(0.0004, 0.0005, 0.0020), smoothstep(-0.5, 0.5, p.y));
    sky += float3(0.010, 0.006, 0.012) * exp(-(p.y + 0.5) * 8.0);   // haze near the horizon
    float2 q = p * 90.0, cell = floor(q);
    float h = hash21(cell);
    if (h > 0.93) {
        float2 o = fract(h * float2(97.31, 61.17)) * 0.6 + 0.2;
        float star = smoothstep(0.09, 0.0, length(q - cell - o));
        float twinkle = 0.6 + 0.4 * sin(6.2831853 * fract(t * (0.05 + 0.1 * fract(h * 37.0))) + h * 40.0);
        sky += float3(0.6, 0.65, 0.8) * star * twinkle * smoothstep(-0.3, 0.2, p.y) * 0.25;
    }
    return sky;
}

float3 shade(float2 p, float t, float2 pixel) {
    float2 uv = p + float2(0.0, 0.5);
    float3 c = float3(0.0);
    float3 flash = float3(0.0);
    float clock = t * 0.5 + 0.85;
    for (int i = 0; i < 2; ++i) {
        float et = clock + float(i) / float(2);
        float id = floor(et);
        float seed = id * float(2) + float(i);
        float3 en = hdFwHash31(seed);
        float2 center = float2((fract(en.x * 17.31 + en.z * 3.7) - 0.5) * 1.6, 0.45 + 0.33 * fract(en.y * 23.17 + en.x * 5.3));
        float lt = et - id;
        float3 color = mix(hdFwHue(en.z), float3(1.0), 0.15);
        c += color * hdFireworkBurst(uv, center, en, lt);
        float fade = max(1.0 - lt * 2.857, 0.0);
        flash += color * (fade * fade * min(lt * 50.0, 1.0));
    }
    const float loop = 20.0 * 3.14159265;
    c = max(hdFwRainbow(c, 1.6 + t - loop * floor(t / loop)), 0.0);
    float3 sky = hdFwSky(p, t) + flash * 0.005 * exp(-(p.y + 0.5) * 2.0);
    return sky + 1.0 - exp(-c);
}
