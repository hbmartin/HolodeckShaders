// Adapted from SwiftShaders Water/WaterShader.metal rainDrops,
// https://github.com/muhittincamdali/SwiftShaders (commit 4acb3a91)
// Copyright (c) 2024 Muhittin Camdali, MIT License.
// Changes: returns a ring mask; shared hash21; each drop cycle picks a new
// position (kept inside its cell) and may skip; faint inner ring; fade-in;
// time wrapped at a whole number of drop cycles.
float hdRainRipples(float2 p, float t, float density) {
    // 1024 s holds exactly 512 drop cycles, and the per-cycle hash repeats
    // with it, so the wrap is invisible while numbers stay small.
    float time = fmod(t, 1024.0);
    float result = 0.0;
    for (int layer = 0; layer < 3; ++layer) {
        float n = float(layer);
        float2 q = p * density + n * 1.33;
        float2 cell = floor(q);
        float2 local = fract(q);
        float clock = time * 0.5 + hash21(cell + n * 17.0);
        float cycle = fmod(floor(clock), 512.0);
        float age = fract(clock);

        float2 seed = cell + float2(cycle * 1.618, n * 7.31 + cycle * 0.73);
        float2 centre = 0.3 + 0.4 * float2(hash21(seed), hash21(seed + 3.7));
        float present = step(0.25, hash21(seed + 11.3));

        // Centre margin 0.3 >= max radius 0.27 + ring width 0.03: rings never cross cells.
        float radius = age * 0.27;
        float inner = radius * 0.6;
        float dist = length(local - centre);
        float ring = smoothstep(radius - 0.03, radius, dist) * smoothstep(radius + 0.03, radius, dist);
        float echo = smoothstep(inner - 0.025, inner, dist) * smoothstep(inner + 0.025, inner, dist);
        float fade = (1.0 - age) * smoothstep(0.0, 0.08, age) * present;
        result += (ring * 0.75 + echo * 0.35) * fade;
    }
    return min(result, 1.0);
}
