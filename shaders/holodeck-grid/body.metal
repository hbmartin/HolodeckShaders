// Holodeck Grid — original Holodeck implementation inspired by "holodeck-scene" by Chris Lane Jones (https://github.com/chrislanejones/holodeck-scene) and the "Blueprint Mode" starship breakdown by Allen White (https://www.artstation.com/artwork/XABr3). No code copied.

// --- grid-lines recipe ---
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

// --- box-room recipe ---
float4 hdRoomHit(float3 ro, float3 rd, float3 halfExtents) {
    float3 s = select(float3(-1.0), float3(1.0), rd >= 0.0);
    float3 tExit = (s * halfExtents - ro) / (s * max(abs(rd), 1e-6));
    float3 n = float3(0.0, 0.0, -s.z);
    float t = tExit.z;
    if (tExit.x < t) { t = tExit.x; n = float3(-s.x, 0.0, 0.0); }
    if (tExit.y < t) { t = tExit.y; n = float3(0.0, -s.y, 0.0); }
    return float4(n, t);
}

float3 hdBounceInBox(float3 start, float3 velocity, float3 halfExtents, float t) {
    float3 rate = velocity / (4.0 * halfExtents);
    float whole = floor(t);
    float3 phase = fract(fract(rate * whole) + rate * (t - whole) + start / (4.0 * halfExtents) + 0.25);
    return halfExtents * (1.0 - 4.0 * abs(phase - 0.5));
}

// --- hologram-rim recipe ---
float3 hdHologramRim(float3 n, float3 v, float3 position, float t, float footprint) {
    float facing = saturate(abs(dot(n, v)));
    float fresnel = 1.0 - facing;
    float key = saturate(dot(n, float3(0.27, 0.89, 0.36)));
    float key2 = key * key;
    float3 body = float3(0.012, 0.02, 0.32) * (0.25 + 0.75 * facing) + float3(0.5, 0.46, 1.0) * (key2 * key2 * key2) * 0.25;
    float phase = position.y * 5.0 - fract(t * 0.15) * 2.0;
    float aa = max(footprint * 5.0, 1e-4);
    float contour = 1.0 - smoothstep(0.04, 0.04 + 1.5 * aa, abs(fract(phase) - 0.5));
    contour *= 0.25 + 0.75 * facing;
    float outline = smoothstep(0.66, 0.86, fresnel);
    float3 rim = float3(1.0, 0.5, 0.03) * 1.2 * outline;
    return (body + float3(0.17, 0.38, 1.0) * contour * 0.22) * (1.0 - outline) + rim;
}

// --- scene ---
constant float3 kRoomHalf = float3(15.0, 10.0, 25.0);
constant float3 kAmber = float3(1.0, 0.48, 0.035);

// Ray against a convex polytope made of up to four symmetric slabs; returns tNear, tFar and the entry slab index.
float3 hdSlabs(float3 ro, float3 rd, float3 normals[4], float extent, int count) {
    float tNear = -1e5, tFar = 1e5, index = 0.0;
    for (int i = 0; i < count; ++i) {
        float denominator = dot(rd, normals[i]);
        float origin = dot(ro, normals[i]);
        float safe = abs(denominator) < 1e-6 ? 1e-6 : denominator;
        float t1 = (-extent - origin) / safe, t2 = (extent - origin) / safe;
        float enter = min(t1, t2), leave = max(t1, t2);
        if (enter > tNear) { tNear = enter; index = float(i); }
        tFar = min(tFar, leave);
    }
    return float3(tNear, tFar, index);
}

float3x3 hdRotation(float yaw, float pitch) {
    float cy = cos(yaw), sy = sin(yaw), cp = cos(pitch), sp = sin(pitch);
    float3x3 ry = float3x3(float3(cy, 0.0, -sy), float3(0.0, 1.0, 0.0), float3(sy, 0.0, cy));
    float3x3 rx = float3x3(float3(1.0, 0.0, 0.0), float3(0.0, cp, sp), float3(0.0, -sp, cp));
    return ry * rx;
}

float3 hdRoomGrid(float3 hit, float3 n, float travel, float t) {
    float3 footprint = fwidth(hit);
    float2 uv = abs(n.x) > 0.5 ? hit.yz : (abs(n.y) > 0.5 ? hit.xz : hit.xy);
    float2 fp = abs(n.x) > 0.5 ? footprint.yz : (abs(n.y) > 0.5 ? footprint.xz : footprint.xy);
    float fine = hdGridLine(uv, 1.0, 0.035, fp);
    float coarse = hdGridLine(uv, 5.0, 0.09, fp);
    float2 offset = abs(fract(uv * 0.2 + 0.5) - 0.5) * 5.0;
    float glow = exp(-min(offset.x, offset.y) * 4.0);
    float lines = fine * 0.24 + coarse * 0.9 + glow * 0.035;
    float fade = 0.15 + 0.85 * exp(-max(travel - 8.0, 0.0) / 9.0);
    float sweep = mix(-kRoomHalf.z - 12.0, kRoomHalf.z + 12.0, fract(t / 26.0));
    float pulse = exp(-(hit.z - sweep) * (hit.z - sweep) / 18.0);
    return kAmber * lines * fade * (0.8 + 1.4 * pulse);
}

float3 shade(float2 p, float t, float2 pixel) {
    float a1 = fmod(t * 0.043, 6.2831853), a2 = fmod(t * 0.031, 6.2831853);
    float3 ro = float3(3.0 * sin(a1), -4.5 + 0.7 * sin(a2), 18.5);
    float3 target = float3(1.2 * sin(a1 + 1.3), -2.8 + 0.5 * sin(a2 + 0.7), 0.0);
    float3 forward = normalize(target - ro);
    float3 right = normalize(cross(forward, float3(0.0, 1.0, 0.0)));
    float3 up = cross(right, forward);
    float3 rd = normalize(p.x * right + p.y * up + 1.25 * forward);

    float4 room = hdRoomHit(ro, rd, kRoomHalf);
    float3 hit = ro + rd * room.w;
    float3 color = float3(0.0012, 0.0009, 0.0016) + hdRoomGrid(hit, room.xyz, room.w, t);

    // floating holograms: sphere, cube, octahedron, small sphere
    float3 laneCentres[4] = {float3(-3.0, -3.0, -7.0), float3(3.0, -3.2, -2.0), float3(2.0, -3.0, -9.0), float3(-2.5, -3.4, 0.5)};
    float3 laneHalves[4] = {float3(8.0, 4.0, 4.0), float3(7.5, 4.0, 3.5), float3(9.0, 4.0, 3.0), float3(7.0, 3.8, 3.0)};
    float3 starts[4] = {float3(-2.0, 1.0, 0.0), float3(2.0, -1.0, 1.0), float3(1.0, 2.5, -1.0), float3(-4.0, -2.0, 1.0)};
    float3 speeds[4] = {float3(0.31, 0.17, 0.23), float3(-0.26, 0.21, -0.19), float3(0.2, -0.16, 0.28), float3(-0.33, 0.24, -0.17)};
    float sizes[4] = {2.1, 1.45, 1.9, 1.2};

    // Anti-aliasing for the holograms uses an analytic footprint (pixel angle x distance / facing),
    // so the per-object work can stay behind a cheap bounding-sphere test.
    float pixelAngle = fwidth(p.y) / 1.25;
    float layerT[4];
    float3 layerLight[4];
    float layerAlpha[4];
    int layers = 0;
    for (int k = 0; k < 4; ++k) {
        float bound = (k == 1 || k == 2) ? sizes[k] * 1.7320508 : sizes[k];
        // Keep the entire rotated object inside the room, with a small clearance from every wall.
        float3 bounceHalf = min(laneHalves[k], kRoomHalf - abs(laneCentres[k]) - bound - 0.05);
        float3 centre = laneCentres[k] + hdBounceInBox(starts[k], speeds[k], bounceHalf, t);
        float3 local = ro - centre;
        float b = dot(local, rd);
        float h = b * b - dot(local, local) + bound * bound;
        if (h <= 0.0 || -b + sqrt(h) <= 0.0) continue;
        if (k == 0 || k == 3) {
            float tn = -b - sqrt(h);
            if (tn <= 0.0 || tn >= room.w) continue;
            float3 pos = local + rd * tn;
            float3 n = pos / sizes[k];
            float facing = saturate(dot(n, -rd));
            float miss = sqrt(max(dot(local, local) - b * b, 0.0));
            float coverage = saturate((sizes[k] - miss) / max(tn * pixelAngle, 1e-5));
            layerT[layers] = tn;
            layerLight[layers] = hdHologramRim(n, -rd, pos, t + float(k) * 3.0, tn * pixelAngle / max(facing, 0.2)) * coverage;
            layerAlpha[layers] = (0.74 + 0.24 * (1.0 - facing) * (1.0 - facing)) * coverage;
            layers++;
        } else {
            float spin = fmod(t * (0.13 + 0.05 * float(k)) + float(k), 6.2831853);
            float3x3 rot = hdRotation(spin, 0.6 + 0.4 * sin(spin * 2.0 + float(k)));
            float3x3 inv = transpose(rot);
            float3 lro = inv * local, lrd = inv * rd;
            float3 normals[4];
            int count;
            float extent = sizes[k];
            if (k == 1) {
                normals[0] = float3(1.0, 0.0, 0.0); normals[1] = float3(0.0, 1.0, 0.0);
                normals[2] = float3(0.0, 0.0, 1.0); normals[3] = float3(0.0);
                count = 3;
            } else {
                normals[0] = float3(0.5773503, 0.5773503, 0.5773503); normals[1] = float3(0.5773503, 0.5773503, -0.5773503);
                normals[2] = float3(0.5773503, -0.5773503, 0.5773503); normals[3] = float3(-0.5773503, 0.5773503, 0.5773503);
                count = 4;
            }
            float3 slab = hdSlabs(lro, lrd, normals, extent, count);
            if (slab.x >= slab.y || slab.x <= 0.0 || slab.x >= room.w) continue;
            float3 pos = lro + lrd * slab.x;
            float3 faceNormal = normals[int(slab.z)];
            float3 ln = faceNormal * (dot(pos, faceNormal) < 0.0 ? -1.0 : 1.0);
            float facing = saturate(abs(dot(ln, lrd)));
            float footprint = slab.x * pixelAngle / max(facing, 0.2);
            float first = 0.0, second = 0.0;
            for (int i = 0; i < count; ++i) {
                float s = abs(dot(pos, normals[i])) / extent;
                second = max(second, min(first, s));
                first = max(first, s);
            }
            float edgeAA = 0.75 * footprint / extent;
            float edge = smoothstep(1.0 - 0.035 - edgeAA, 1.0 - 0.035 + edgeAA, second);
            float3 light = hdHologramRim(rot * ln, -rd, pos, t + float(k) * 3.0, footprint);
            layerT[layers] = slab.x;
            float coverage = saturate((slab.y - slab.x) / max(1.5 * slab.x * pixelAngle, 1e-5));
            layerLight[layers] = mix(light, float3(1.0, 0.5, 0.03) * 1.25, edge) * coverage;
            layerAlpha[layers] = (0.76 + 0.22 * edge) * coverage;
            layers++;
        }
    }

    // composite translucent layers far to near
    for (int pass = 0; pass < layers; ++pass) {
        int pick = 0;
        float farthest = -1.0;
        for (int i = 0; i < layers; ++i) {
            if (layerT[i] > farthest) { farthest = layerT[i]; pick = i; }
        }
        color = color * (1.0 - layerAlpha[pick]) + layerLight[pick];
        layerT[pick] = -2.0;
    }

    color *= 1.0 - 0.3 * dot(p, p);
    color = 1.0 - exp(-color * 1.15);
    float grain = hash21(pixel + fract(t) * 97.0) - 0.5;
    color += grain * (2.2 / 255.0) * sqrt(max(color, 1e-4));
    return color;
}
