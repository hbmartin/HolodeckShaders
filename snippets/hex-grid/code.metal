// Pointy-top hexagonal lattice, neighbour spacing 1. xy = offset from the cell centre, zw = integer cell id.
float4 hdHexCell(float2 p) {
    const float2 s = float2(1.0, 1.7320508);
    float2 a = p - s * floor(p / s) - 0.5 * s;
    float2 q = p - 0.5 * s;
    float2 b = q - s * floor(q / s) - 0.5 * s;
    float2 local = dot(a, a) < dot(b, b) ? a : b;
    float2 centre = p - local;
    return float4(local, round(centre.x * 2.0), round(centre.y * 1.1547005));
}

// 1 on cell borders. width and footprint are in lattice units; footprint is the anti-aliasing width per pixel.
float hdHexEdge(float2 local, float width, float footprint) {
    float2 q = abs(local);
    float d = 0.5 - max(q.x, dot(q, float2(0.5, 0.8660254)));
    float aa = max(footprint, 1e-4);
    float line = 1.0 - smoothstep(width - aa, width + aa, d);
    float mean = 1.0 - (1.0 - 2.0 * width) * (1.0 - 2.0 * width);
    return mix(line, mean, smoothstep(0.12, 0.3, aa));
}

// Derivative-based variant; call it in uniform control flow (not inside a per-pixel hit branch).
float hdHexEdge(float2 local, float width) {
    float2 q = abs(local);
    float d = 0.5 - max(q.x, dot(q, float2(0.5, 0.8660254)));
    return hdHexEdge(local, width, fwidth(d));
}

// Sparse, smooth 0..1 twinkle per cell; rate is chances per second.
float hdCellFlash(float2 cellId, float t, float rate) {
    float seed = hash21(cellId);
    float local = t * rate + seed * 17.0;
    float cycle = floor(local);
    float f = local - cycle;
    float on = step(0.93, hash21(cellId + fmod(cycle, 509.0) * float2(1.37, 0.71)));
    float pulse = 4.0 * f * (1.0 - f);
    return on * pulse * pulse;
}

// Seamless hex lattice on a unit sphere: angle-weighted octahedral mapping whose triangle edges are lattice
// mirror lines. Use an integer cellsPerEdge (cells per quarter great circle); six square cells sit on the axes.
// zw is a cell key shared by both halves of cells cut by octant seams.
float4 hdSphereHexCell(float3 n, float cellsPerEdge) {
    float3 w = asin(min(abs(n), 1.0));
    w /= w.x + w.y + w.z;
    float2 plane = cellsPerEdge * float2(w.y + 0.5 * w.z, 0.8660254 * w.z);
    float4 cell = hdHexCell(plane);
    float c = cell.w;
    float b = (cell.z - c) * 0.5;
    float3 k = float3(cellsPerEdge - b - c, b, c) * select(float3(-1.0), float3(1.0), n >= 0.0);
    return float4(cell.xy, k.x + 37.0 * k.z, k.y - 53.0 * k.z);
}
