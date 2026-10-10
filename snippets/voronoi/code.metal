// Adapted from SwiftShaders (https://github.com/muhittincamdali/SwiftShaders, commit 4acb3a91,
// Sources/SwiftShaders/Shaders/Voronoi/VoronoiShader.metal), MIT License, Copyright (c) 2024
// Muhittin Camdali. Changes: sin-based hash replaced by a Hoskins hash; jitter centered on the cell;
// points circle their cell centers (rotation of a random vector, no per-cell trig); the caller
// supplies an already wrapped animation phase.
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

float2 hdVoronoiHash22(float2 p) {
    float3 p3 = fract(float3(p.xyx) * float3(0.1031, 0.1030, 0.0973));
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.xx + p3.yz) * p3.zy);
}

// Distances to the nearest (F1) and second-nearest (F2) feature point, in cell units.
// phase: animation angle in radians (wrap it); jitter: 0 = regular grid, 1 = fully random.
float2 hdVoronoiF1F2(float2 p, float phase, float jitter) {
    float2 ip = floor(p), fp = p - ip;
    float s = sin(phase) * 0.35 * jitter, c = cos(phase) * 0.35 * jitter;
    float f1 = 8.0, f2 = 8.0;
    for (int y = -1; y <= 1; ++y) {
        for (int x = -1; x <= 1; ++x) {
            float2 n = float2(float(x), float(y));
            float2 v = hdVoronoiHash22(ip + n) * 2.0 - 1.0;
            // Each feature point circles its cell center; the random vector v sets radius and start angle.
            float2 diff = n + 0.5 + float2(c * v.x - s * v.y, s * v.x + c * v.y) - fp;
            float d = dot(diff, diff);
            f2 = d < f1 ? f1 : min(f2, d);
            f1 = min(f1, d);
        }
    }
    return sqrt(float2(f1, f2));
}
