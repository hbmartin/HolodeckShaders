// Mutara Veil — original Holodeck nebula composition, inspired by cinematic
// exploration of the Mutara Nebula in Star Trek. No film imagery or code used.
// Stars adapted from Holodeck's Layered Stars recipe (repository provenance):
// slower bounded drift, footprint-filtered cores, softer twinkle and gas extinction.
// Uses canonical fbm / hash21 in shared/common.metal; that component preserves
// David Hoskins' complete MIT notice for "Hash without Sine" (4djSRW).
// Single-pass layered emission / absorption approximates gaseous depth; no textures.

float3 mutaraStars(float2 p, float phase, float footprint) {
    float3 light = float3(0.0);
    for (int i = 0; i < 3; ++i) {
        float layer = float(i);
        float scale = 24.0 + layer * 17.0;
        float2 drift = (0.09 + layer * 0.04)
                     * float2(sin(phase), cos(phase));
        float2 q = p * scale + drift;
        float2 cell = floor(q);
        float2 local = fract(q) - 0.5;
        float seed = hash21(cell + layer * 19.0);
        float2 offset = float2(hash21(cell + 8.3), hash21(cell + 3.1)) * 0.6 - 0.3;
        float2 delta = local - offset;
        float nativeVariance = 0.00045 + 0.0006 * seed * seed;
        float variance = nativeVariance + pow(footprint * scale, 2.0) * 0.3;
        float core = exp(-dot(delta, delta) / variance) * nativeVariance / variance;
        float halo = exp(-dot(delta, delta) * 110.0) * 0.045;
        // Centers stay at least 0.2 cells from a boundary; halo is negligible there.
        float twinkle = 0.86 + 0.14 * sin(phase * 4.0 + seed * 50.0);
        float3 tint = mix(float3(0.45, 0.65, 1.0), float3(1.0, 0.78, 0.61), seed);
        light += tint * (core + halo) * step(0.91, seed) * twinkle;
    }
    return light;
}

float3 shade(float2 p, float time, float2 pixel) {
    // Every moving coordinate is bounded and continuous at its phase wrap.
    float phase = fmod(time * 0.055, 6.28318530718);
    float evolution = fmod(time * 0.034, 6.28318530718);
    float footprint = max(length(dfdx(p)), length(dfdy(p)));
    float3 color = float3(0.0015, 0.0025, 0.009);
    color += mutaraStars(p, phase + 0.15 * sin(phase), footprint) * 0.8;

    // Broad, offset gas banks cross the frame, with separate depth and flow.
    // Each layer uses two low-frequency noise warps and two four-octave fields.
    for (int i = 0; i < 3; ++i) {
        float layer = float(i);
        float2 drift = float2(0.14 * sin(phase + layer * 1.9),
                              0.09 * cos(evolution + layer * 2.1));
        float2 q = p * (1.0 + layer * 0.18) + drift;
        float2 flow = float2(cos(evolution + layer), sin(evolution + layer));
        float2 warp = float2(noise2(q * 2.3 + flow * 0.6 + layer * 13.7),
                             noise2(q * 2.3 - flow * 0.5 + layer * 9.1 + 31.0)) - 0.5;
        float2 gas = q * 3.8 + warp * 2.6 + layer * 17.3;
        float billow = fbm(gas + flow * 0.25);
        float detail = fbm(gas * 3.1 + float2(-flow.y, flow.x) * 0.8);

        float lane = q.y - 0.24 * q.x + 0.13 * sin(q.x * 3.2 + layer)
                   + 0.23 * warp.y + (layer - 1.0) * 0.21;
        float envelope = exp(-pow(lane / (0.23 + layer * 0.025), 2.0));
        float cloud = smoothstep(0.27, 0.69, billow + 0.12 * (detail - 0.5));
        float density = envelope * cloud * (0.38 + 1.25 * detail);

        float hue = smoothstep(0.29, 0.69, billow + 0.20 * q.x - layer * 0.055);
        float3 tint = mix(float3(0.018, 0.38, 0.44), float3(0.40, 0.035, 0.64), hue);
        float warmth = smoothstep(0.52, 0.76, detail + 0.10 * billow);
        tint = mix(tint, float3(0.72, 0.16, 0.15), warmth * 0.52);

        // Filter narrow wisps using the actual warped field's pixel footprint.
        float filamentWidth = max(0.022, fwidth(detail) * 1.5);
        float filaments = exp(-abs(detail - 0.48) / filamentWidth);
        float knots = smoothstep(0.50, 0.70, billow) * smoothstep(0.44, 0.65, detail);
        float illumination = 0.38 + 1.3 * billow + 1.8 * knots;
        float opacity = 1.0 - exp(-density * 1.45);
        color *= 1.0 - opacity * 0.57;
        color += tint * opacity * illumination * 0.75;
        color += mix(float3(0.08, 0.42, 0.50), float3(0.53, 0.24, 0.64), hue)
               * filaments * density * 0.24;

        // A different part of the turbulent field forms opaque foreground dust.
        float dust = smoothstep(0.48, 0.68, billow - 0.30 * detail + 0.13);
        color *= exp(-dust * envelope * (0.8 + layer * 0.25));
    }

    // A faint blue scattering glow deep inside the bank, with a pearl-sized star.
    float2 beacon = p - float2(0.34, 0.09);
    float radius2 = dot(beacon, beacon);
    color += float3(0.028, 0.075, 0.12) * exp(-radius2 / 0.018);
    float coreWidth = 0.0000018 + footprint * footprint * 0.3;
    color += float3(0.65, 0.80, 1.0) * exp(-radius2 / coreWidth)
           * (0.0000018 / coreWidth);
    return 1.0 - exp(-color * 1.3);
}
