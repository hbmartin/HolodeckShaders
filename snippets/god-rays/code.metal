// Original Holodeck implementation.
// Soft light shafts radiating from a point above the frame. Returns a mask in [0, 1].
// source: the shafts' convergence point (usually above the top edge, y > 0.5); t: seconds.
// The pattern drifts on a circular path through noise space, so it loops seamlessly every 600 s
// and stays precise at large t.
float hdGodRays(float2 p, float2 source, float t) {
    float2 d = p - source;
    float k = d.x / max(-d.y, 1e-3);                     // tangent of the angle from vertical
    float a = 6.2831853 * fract(t * (1.0 / 600.0));
    float2 drift = 9.5 * float2(cos(a), sin(a));          // about 0.1 noise units per second
    k += 0.035 * sin(7.0 * a);                            // slow sway, 7 swings per loop
    float n = 0.65 * noise2(float2(k * 9.0, 0.0) + drift) + 0.35 * noise2(float2(k * 23.0, 5.0) - 1.7 * drift);
    float shafts = smoothstep(0.42, 0.85, n);
    return shafts * shafts;
}
