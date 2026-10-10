// Adapted from SwiftShaders Noise/NoiseShader.metal perlinNoise,
// https://github.com/muhittincamdali/SwiftShaders (commit 4acb3a91)
// Copyright (c) 2024 Muhittin Camdali, MIT License.
// Changes: shared hash21 for the gradient angle, quintic fade, output
// rescaled from the theoretical ±sqrt(0.5) range to 0..1.

// MIT notice for swiftshaders (preserved from upstream):
// Copyright (c) 2024 Muhittin Camdali
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

float2 hdGradientNoiseDir(float2 cell) {
    float angle = hash21(cell) * 6.2831853;
    return float2(cos(angle), sin(angle));
}

float hdGradientNoise2(float2 p) {
    float2 i = floor(p), f = fract(p);
    float2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
    float a = dot(hdGradientNoiseDir(i), f);
    float b = dot(hdGradientNoiseDir(i + float2(1.0, 0.0)), f - float2(1.0, 0.0));
    float c = dot(hdGradientNoiseDir(i + float2(0.0, 1.0)), f - float2(0.0, 1.0));
    float d = dot(hdGradientNoiseDir(i + 1.0), f - 1.0);
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y) * 0.70710678 + 0.5;
}
