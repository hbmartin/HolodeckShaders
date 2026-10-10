float3 shade(float2 p, float t, float2 pixel) {
    // Pool tiles seen through a rippling surface.
    float2 q = hdSineWarp(p, t * 3.0, 0.012, 14.0);
    float2 tile = abs(fract(q * 7.0) - 0.5);
    float grout = smoothstep(0.43, 0.48, max(tile.x, tile.y));
    float3 water = mix(float3(0.02, 0.22, 0.42), float3(0.05, 0.45, 0.6), 0.5 + 0.5 * q.y);
    float3 color = mix(water, float3(0.75, 0.9, 0.95), grout * 0.6);
    return color * color;
}
