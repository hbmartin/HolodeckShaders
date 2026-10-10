// Orange Flow: original translucent amber folds inspired by the supplied image.
// Uses canonical value noise; no external shader source is copied.
float3 shade(float2 p, float time, float2 pixel) {
    float phase = fmod(time * 0.07, 6.2831853);
    float2 q = p;
    q.x += 0.025 * sin(phase + q.y * 2.0);
    float lower = 1.0 - smoothstep(-0.5, 0.32, q.y);
    float3 color = mix(float3(0.96, 0.49, 0.0), float3(0.78, 0.70, 0.0), lower);
    color += (noise2(q * 4.0 + float2(sin(phase), cos(phase)) * 0.12) - 0.5)
           * float3(0.05, 0.034, 0.0);

    // A broad sheet turns from an upper-right lip into a flowing lower fold.
    float drop = max(0.13 - q.y, 0.0);
    float edge = -0.045 + 1.0 * drop * drop
               + 0.055 * sin(q.y * 6.0 + phase);
    float lip = 0.19 + 0.16 * smoothstep(-0.1, 0.62, q.x)
              + 0.013 * sin(q.x * 12.0 - phase);
    float sheet = smoothstep(-0.009, 0.012, q.x - edge)
                * (1.0 - smoothstep(-0.01, 0.013, q.y - lip));
    float3 silk = mix(float3(1.0, 0.78, 0.075), float3(0.91, 0.86, 0.0), lower);
    color = mix(color, silk, sheet * 0.80);
    float lipDistance = (q.y - lip + 0.025) / 0.057;
    float lipGlow = exp(-(lipDistance * lipDistance)) * sheet;
    color = mix(color, float3(1.0, 0.77, 0.22), lipGlow * 0.42);
    float turnDistance = (q.x - edge + 0.055) / 0.084;
    float turn = exp(-(turnDistance * turnDistance));
    color *= 1.0 - turn * 0.10;

    // Overlapping, low-contrast translucent ribbons keep the image airy.
    float backEdge = -0.28 + 0.22 * cos(q.y * 4.0 + phase);
    float back = smoothstep(-0.012, 0.015, q.x - backEdge)
               * (1.0 - smoothstep(0.12, 0.25, q.x - backEdge));
    color = mix(color, float3(0.61, 0.57, 0.005), back * lower * 0.38);
    float veilEdge = -0.03 + 0.12 * sin(q.y * 7.0 - phase);
    float veilDistance = (q.x - veilEdge) / 0.08;
    float veil = exp(-(veilDistance * veilDistance));
    color = mix(color, float3(1.0, 0.68, 0.04), veil * 0.17);
    float frontEdge = -0.16 + 0.15 * sin(q.y * 5.0 - phase) + lower * 0.22;
    float front = smoothstep(-0.004, 0.008, q.x - frontEdge)
                * (1.0 - smoothstep(0.10, 0.17, q.x - frontEdge))
                * (1.0 - smoothstep(0.17, 0.26, q.y));
    color = mix(color, float3(0.95, 0.70, 0.02), front * 0.27);
    float diagonal = q.y + 0.52 * q.x + 0.02 + 0.11 * sin(q.x * 4.0 + phase);
    float overlapDistance = diagonal / 0.048;
    float overlap = exp(-(overlapDistance * overlapDistance));
    color *= 1.0 - overlap * sheet * 0.045;
    color += (hash21(pixel) - 0.5) / 255.0;
    return pow(clamp(color, 0.0, 1.0), float3(2.2));
}
