// Light Grid
// Original: "LightGrid" from Inferno by Paul Hudson and other authors
// https://github.com/twostraws/Inferno (Sources/Inferno/Shaders/Generation/LightGrid.metal)
// Copyright (c) 2023 Paul Hudson and other authors (Inferno), MIT License — https://github.com/twostraws/Inferno
// Adapted for Holodeck: float instead of half; grid centred on screen in
// height units; per-cell phase from shared hash21; slowed, 2π-wrapped time;
// colours decoded for the sRGB target; soft exposure tonemap instead of hard
// clipping; faint in-cell halo and slow per-lamp breathing added.

float3 shade(float2 p, float t, float2 pixel) {
    const float density = 9.0;      // rows per screen height
    const float speed = 3.0;        // colour variance per cell
    const float groupSize = 1.0;    // lights per colour group (per axis)
    const float brightness = 3.0;
    const float tau = 6.2831853;

    // Original: uv = position/size with x scaled by aspect (height units).
    // Cell edges sit on the vertical centre line and rows fill the height,
    // so nine rows give an exact 16 x 9 wall at 16:9.
    float2 point = float2(p.x, -p.y) * density + float2(0.0, 0.5 * density);
    float2 cell = floor(point);

    // The source is exactly 2π-periodic in time; slow it and wrap seamlessly.
    float time = fmod(t * 0.25, tau);

    float variance = 0.5 * sin(time + hash21(cell + 17.0) * tau) + 0.5;
    float3 color = 0.5 + 0.5 * sin(float3(3.0, 1.5, 0.0) + speed * variance + time);

    // The source colours are display-referred; decode for the sRGB target.
    color = color * color;

    float2 groupSine = 0.5 * sin(tau * groupSize * (point - 0.25 / groupSize)) + 0.5;
    float2 pulse = smoothstep(0.0, 1.0, groupSine);
    float lamp = pulse.x * pulse.y;
    float halo = sqrt(groupSine.x * groupSine.y);

    // Gentle per-lamp breathing; also 2π-periodic in the wrapped time.
    float breathe = 0.82 + 0.18 * sin(time + hash21(cell + 71.0) * tau);

    float3 light = color * (lamp * brightness * breathe + halo * 0.12);
    return 1.0 - exp(-1.6 * light);
}
