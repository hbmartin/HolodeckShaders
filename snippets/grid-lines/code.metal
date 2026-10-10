// Box-filtered grid: lines of width thickness every spacing units in coord. footprint is the size of one pixel
// in coord units (per axis, e.g. fwidth(coord) or an analytic estimate). Returns a 0..1 coverage mask.
float hdGridLine(float2 coord, float spacing, float thickness, float2 footprint) {
    float2 x = coord / spacing;
    float w = thickness / spacing;
    float2 fp = max(footprint / spacing, 1e-4);
    float2 a = x - 0.5 * fp + 0.5 * w;
    float2 b = x + 0.5 * fp + 0.5 * w;
    float2 coverage = (floor(b) - floor(a)) * w + min(fract(b), w) - min(fract(a), w);
    coverage = saturate(coverage / fp);
    return 1.0 - (1.0 - coverage.x) * (1.0 - coverage.y);
}

// Isotropic footprint convenience overload.
float hdGridLine(float2 coord, float spacing, float thickness, float footprint) {
    return hdGridLine(coord, spacing, thickness, float2(footprint));
}
