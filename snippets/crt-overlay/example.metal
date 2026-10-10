float3 shade(float2 p, float t, float2 pixel) {
    const float aspect = 16.0 / 9.0;
    float height = 1.0 / fwidth(p.y);

    // Tube warp (stronger than Lottes' default so it reads in a preview).
    float2 c = float2(p.x / (0.5 * aspect), p.y * 2.0);
    float2 w = hdCrtWarp(c, float2(1.0 / (50.0 * aspect), 1.0 / 50.0) * 3.0);
    float2 aaEdge = fwidth(w);
    float tube = smoothstep(1.0, 1.0 - 2.0 * aaEdge.x, abs(w.x)) * smoothstep(1.0, 1.0 - 2.0 * aaEdge.y, abs(w.y));
    float2 uv = float2(w.x * 0.5 + 0.5, 0.5 - w.y * 0.5);

    // Tracking band nudges the picture sideways.
    float band = hdTrackingBand(uv.y, t);
    uv.x += band * 0.006 * sin(uv.y * 400.0 + fract(t * 3.0) * 6.2831853);

    // Procedural picture: 75% colour bars over a drifting palette sweep.
    const float3 bars[7] = {float3(0.75), float3(0.75, 0.75, 0.0), float3(0.0, 0.75, 0.75), float3(0.0, 0.75, 0.0),
                            float3(0.75, 0.0, 0.75), float3(0.75, 0.0, 0.0), float3(0.0, 0.0, 0.75)};
    float3 picture = uv.y < 0.62 ? bars[int(clamp(uv.x * 7.0, 0.0, 6.0))] : palette(uv.x * 0.8 + fract(t * 0.05)) * 0.8;
    picture *= picture;

    // Scanlines follow the warped picture; mask and grain stay on the glass.
    float scale = max(1.0, floor(height / 1080.0 + 0.5));
    float lines = min(360.0, height / 3.0);
    float3 color = picture * hdScanlines(uv.y * lines, 0.9) * hdCrtShadowMask(floor(pixel / scale), 0.6);
    color *= 1.9;  // restore the average brightness the mask and scanlines remove
    color += hdFilmGrain(floor(pixel / scale), t) * 0.05 + band * 0.04;
    return color * tube;
}
