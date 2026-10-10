// Random "rune" glyphs: "runes" by FabriceNeyret2 (https://www.shadertoy.com/view/4ltyDM), based on
// "runes" by otaviogood (https://shadertoy.com/view/MsXSRn), as modified in the ghostty-shaders
// "inside-the-matrix.glsl" (@pkazmier); segment distance from https://www.shadertoy.com/view/4dcfW8.
// CC BY-NC-SA 3.0 lineage: adaptations must keep CC BY-NC-SA 3.0 and these credits.
// Hash after Dave Hoskins ("Hash without Sine").
// License terms: https://creativecommons.org/licenses/by-nc-sa/3.0/

float4 hdRuneHash42(float2 p) {
    float4 p4 = fract(float4(p.xyxy) * float4(0.1031, 0.1030, 0.0973, 0.1099));
    p4 += dot(p4, p4.wzxy + 33.33);
    return fract((p4.xxyz + p4.yzzw) * p4.zywx);
}

// Distance to a random 4-stroke rune in the unit box (strokes snapped to a 2x3 grid, each rune
// touching all four sides of its box).
float hdRuneDistance(float2 uv, float2 seed) {
    float d = 1e5;
    for (int i = 0; i < 4; ++i) {
        float4 pos = hdRuneHash42(seed);
        seed += 1.0;
        if (i == 0) pos.y = 0.0;
        if (i == 1) pos.x = 0.999;
        if (i == 2) pos.x = 0.0;
        if (i == 3) pos.y = 0.999;
        pos = (floor(pos * float4(2.0, 3.0, 2.0, 3.0)) + 0.5) / float4(2.0, 3.0, 2.0, 3.0);
        if (any(pos.xy != pos.zw)) {
            float2 pa = uv - pos.xy, ba = pos.zw + 0.001 - pos.xy;
            float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
            d = min(d, length(pa - ba * h));
        }
    }
    return d;
}

// Glyph mask in [0, 1]: stroke half-width 0.1 of the box.
float hdRuneGlyph(float2 uv, float2 seed) {
    return smoothstep(0.1, 0.0, hdRuneDistance(uv, seed));
}
