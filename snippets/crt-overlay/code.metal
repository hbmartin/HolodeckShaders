// MIT notice for vhs-overlay (preserved from upstream):
// Copyright (c) 2026 Alex Brinsmead
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

// CRT and VHS overlays for procedural colour (no texture is sampled).
// Shadow mask, scanline beam profile and tube warp after "[CRTS] Public domain
// CRT-styled scalar" by Timothy Lottes (Unlicense / public domain), as adapted
// for Ghostty by Qwerasd (https://gist.github.com/qwerasd205/c3da6c610c8ffe17d6d2d3cc7068f17f).
// Grain and tracking band after "Degraded VHS tape + CRT monitor effect" by
// Alex Brinsmead (https://gist.github.com/abrinsmead/be7d2d2209d0dd3097000af369867927),
// Copyright (c) 2026 Alex Brinsmead, MIT License.
// Changes: overlay factors instead of filtered texture fetches; integer mask
// phase; scanlines in caller-chosen units; shared hash21 for grain.

// Lottes shadow mask: 6-pixel RGB triads, alternate rows offset by half a
// triad. Multiply onto linear RGB. dark is the level of the unlit channels.
float3 hdCrtShadowMask(float2 pixel, float dark) {
    uint2 cell = uint2(max(floor(pixel), 0.0));
    uint channel = ((cell.x + 3u * cell.y) % 6u) / 2u;
    float3 lit = float3(channel == 0u, channel == 1u, channel == 2u);
    return mix(float3(dark), float3(1.0), lit);
}

// Lottes scanline beam profile (thin 0.75). y is in scanline units, one unit
// per scanline. Returns a brightness factor: 1 at a beam centre, 0.29 between
// beams, 0.667 on average at strength 1.
float hdScanlines(float y, float strength) {
    const float thin = 0.75;
    float off = fract(y - 0.5);
    float beamA = 0.5 + 0.5 * cos(min(0.5, off * thin) * 6.2831853);
    float beamB = 0.5 + 0.5 * cos(min(0.5, (1.0 - off) * thin) * 6.2831853);
    return mix(1.0, beamA + beamB, strength);
}

// Per-pixel grain in [-0.5, 0.5], new every frame. Pass floor(pixel / k) to
// enlarge grains.
float hdFilmGrain(float2 pixel, float t) {
    float seed = fract(t * 0.618034) * 1000.0;
    return hash21(floor(pixel) + float2(seed, seed * 0.731)) - 0.5;
}

// VHS tracking band: a soft bar rolling down the screen every 25 seconds.
// y01 is 0 at the top and 1 at the bottom. Returns 0..1.
float hdTrackingBand(float y01, float t) {
    float distance = abs(y01 - fract(t * 0.04));
    return smoothstep(0.05, 0.0, min(distance, 1.0 - distance));
}

// Lottes tube warp. c is centred screen space in [-1, 1] on both axes; the
// result exceeds that range near the corners (outside the tube).
float2 hdCrtWarp(float2 c, float2 warp) {
    return c * (1.0 + c.yx * c.yx * warp);
}
