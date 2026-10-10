// "Warp Speed 2" by Dave Hoskins (2015)
// https://www.shadertoy.com/view/4tjSDt (fork of his "Warp speed", https://www.shadertoy.com/view/Msl3WH;
// fractal after Kali's star nest folding)
// License: Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported (CC BY-NC-SA 3.0)
// Adapted for Holodeck: aspect-correct coordinates; travel slowed to ~1/3 of the original speed and
// wrapped on a seamless 52-unit period (wander frequencies rounded to 2pi/4 and 2pi/2.6) so large
// times stay precise; 10 ray steps (was 100) with a per-pixel, per-frame jitter to hide step banding;
// guarded fold division; sRGB-style decode and a soft highlight shoulder instead of a hard clamp;
// unused music channel removed.
// This adaptation is licensed CC BY-NC-SA 3.0.

// Recipe: snippets/kali-starfield (RGB light, unbounded).
float3 hdKaliStarfield(float2 uv, float travel, int steps, float jitter) {
    float ds = 2.5 / float(steps), weight = ds * 40.0;
    float3 origin = float3(0.3 * sin(travel * 1.5707963), 0.35 - 0.3 * cos(travel * 2.4166097), travel);
    float s = ds * jitter, v = 0.0;
    float3 light = float3(0.0);
    for (int r = 0; r < steps; ++r) {
        float3 q = origin + s * float3(uv, 0.05);
        q.z = fract(q.z);
        for (int i = 0; i < 10; ++i) q = abs(q) * (2.04 / max(dot(q, q), 1e-4)) - 0.9;
        v += pow(dot(q, q), 0.7) * 0.06 * weight;
        light += float3(v * 0.2 + 0.4, 12.0 - s * 2.0, 0.1 + v) * (v * 0.00003 * weight);
        s += ds;
    }
    return light;
}

float3 shade(float2 p, float t, float2 pixel) {
    const float speed = 0.04;              // travel units per second (original: 0.116)
    const float period = 52.0 / speed;     // seamless loop of the travel path (1300 s)
    float travel = 0.45 + (t - period * floor(t / period)) * speed;
    // Interleaved gradient noise, offset every frame so step banding reads as fine film grain rather than a fixed pattern.
    float frame = t * 60.0 - 64.0 * floor(t * 60.0 / 64.0);
    float jitter = fract(52.9829189 * fract(dot(pixel + 5.588238 * floor(frame), float2(0.06711056, 0.00583715))));
    float3 c = hdKaliStarfield(p * 2.0, travel, 10, jitter);
    c = select(c, 0.6 + 0.4 * (1.0 - exp(-(c - 0.6) / 0.4)), c > 0.6);
    return c * c;
}
