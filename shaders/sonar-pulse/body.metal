// Sonar Pulse
// Original: "CircleWave" (Transformation) from Inferno by Paul Hudson and other authors
// https://github.com/twostraws/Inferno (Sources/Inferno/Shaders/Transformation/CircleWaveTransformation.metal)
// Copyright (c) 2023 Paul Hudson and other authors (Inferno), MIT License — https://github.com/twostraws/Inferno
// Adapted for Holodeck: float instead of half; aspect-correct distance from
// the screen centre; wrapped wave phases; colour drifts through the shared
// palette; sharper crests, hot core, slow secondary ring set and faint haze;
// exposure tonemap.

// MIT notice for inferno (preserved from upstream):
// Copyright (c) 2023 Paul Hudson and other authors.
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

float3 shade(float2 p, float t, float2 pixel) {
    const float tau = 6.2831853;
    const float brightness = 0.5;
    const float speed = 0.25;
    const float strength = 2.0;
    const float density = 70.0;

    float d = length(p);
    float hue = fract(t * 0.01);
    float3 tint = palette(hue);
    float3 accent = palette(fract(hue + 0.17));
    tint *= tint;
    accent *= accent;

    // Original falloff: cubic from the centre, forced to zero near the edge.
    float falloff = pow(max(1.0 - d, 0.0), 3.0) * max(1.0 - d * 1.75, 0.0);

    float wave = fmod(t * speed * 10.0, tau);
    float crest = 0.5 * cos(density * d - wave) + 0.5;
    crest *= crest * crest;
    float luma = falloff * strength * (strength * 0.5 + 2.6 * crest);

    // A slower, wider ring set in a neighbouring hue.
    float wave2 = fmod(t * 0.8, tau);
    float crest2 = 0.5 * cos(17.0 * d - wave2) + 0.5;
    float luma2 = falloff * crest2 * crest2 * 1.3;

    float core = exp(-d * d * 90.0) * 2.5;

    // Faint haze circling slowly behind the orb.
    float drift = fmod(t * 0.03, tau);
    float haze = fbm(p * 2.4 + 1.5 * float2(cos(drift), sin(drift)));
    float3 light = tint * brightness * luma + accent * brightness * luma2;
    light += (tint + 0.25) * brightness * core;
    light += tint * haze * haze * haze * 0.05 * (0.3 + d);

    return 1.0 - exp(-1.3 * light);
}
