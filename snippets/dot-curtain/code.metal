// Adapted from Inferno's Circle Wave / Diamond Wave transitions
// (Transition/CircleWave.metal), https://github.com/twostraws/Inferno
// Copyright (c) 2023 Paul Hudson and other authors (Inferno), MIT License.
// Based on gl-transitions PolkaDotsCurtain by bobylito (MIT),
// https://gl-transitions.com/editor/PolkaDotsCurtain
// Changes: returns an anti-aliased 0..1 mask instead of choosing a layer
// colour; diamond (L1) dots selectable; reach scaled so 0 and 1 are exact.
float hdDotCurtain(float2 cellPos, float2 uv01, float amount, bool diamond, float aa) {
    float2 f = fract(cellPos) - 0.5;
    float d = diamond ? abs(f.x) + abs(f.y) : length(f);
    float reach = clamp(amount, 0.0, 1.0) * (3.0 + 2.0 * aa) - aa;
    return smoothstep(-aa, aa, reach - (d + uv01.x + uv01.y));
}
