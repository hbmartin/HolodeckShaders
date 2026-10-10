// "Inside the Matrix" (ghostty-shaders "inside-the-matrix.glsl", modified for Ghostty by @pkazmier)
// https://github.com/0xhckr/ghostty-shaders/blob/85898f08fcf4a9274e418912098e99e00a5f8350/inside-the-matrix.glsl
// The original Shadertoy author is not named in that file. Its header states:
//   "Feel free to do anything you want with this code."
// It uses "runes" code by FabriceNeyret2 (https://www.shadertoy.com/view/4ltyDM), which is based on
// "runes" by otaviogood (https://shadertoy.com/view/MsXSRn); the segment distance is from
// https://www.shadertoy.com/view/4dcfW8. Those Shadertoy sources carry Shadertoy's default
// CC BY-NC-SA 3.0, so this whole adaptation is treated as CC BY-NC-SA 3.0.
// Adapted for Holodeck: terminal blending and mouse look removed; aspect-correct view rays; the
// 300 s time reset (which made the camera jump) replaced by a wrap at the full 1920 s route period,
// with fall speeds quantized to 0.1, z-cell hashes wrapped mod 16 and symbol indices wrapped mod 640
// so camera and rain positions repeat; glyphs use an independent clock across route wraps;
// sin hashes replaced by Hoskins hashes on bounded inputs; one
// strip line per column instead of one per z-cell; 16 branchless DDA steps (was 40) with distance
// fog; route start offset 100 s; full brightness (was 0.25) with an sRGB-style decode.
// This adaptation is licensed CC BY-NC-SA 3.0.

// License terms: https://creativecommons.org/licenses/by-nc-sa/3.0/

constant float hdMxCharH = 0.15;                     // STRIP_CHAR_HEIGHT
constant float hdMxCharW = 0.10;                     // STRIP_CHAR_WIDTH
constant float hdMxZCell = 0.15 * 40.0;              // ZCELL_SIZE
constant float hdMxXYCell = 12.0 * 0.10;             // XYCELL_SIZE
constant float hdMxPI = 3.14159265;

// Hashes after Dave Hoskins ("Hash without Sine"); inputs are kept small and bounded.
float2 hdMxHash22(float2 p) {
    float3 p3 = fract(float3(p.xyx) * float3(0.1031, 0.1030, 0.0973));
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.xx + p3.yz) * p3.zy);
}

float4 hdMxHash43(float3 p) {
    float4 p4 = fract(float4(p.xyzx) * float4(0.1031, 0.1030, 0.0973, 0.1099));
    p4 += dot(p4, p4.wzxy + 33.33);
    return fract((p4.xxyz + p4.yzzw) * p4.zywx);
}

float4 hdRuneHash42(float2 p) {
    float4 p4 = fract(float4(p.xyxy) * float4(0.1031, 0.1030, 0.0973, 0.1099));
    p4 += dot(p4, p4.wzxy + 33.33);
    return fract((p4.xxyz + p4.yzzw) * p4.zywx);
}

// Recipe: snippets/rune-glyph. Distance to a random 4-stroke rune in the unit box (strokes snapped to a
// 2x3 grid, each rune touching all four sides of its box).
float hdRuneDistance(float2 uv, float2 seed) {
    float d = 1e5;
    for (int i = 0; i < 4; ++i) {
        float4 pos = hdRuneHash42(seed);
        seed += 1.0;
        if (i == 0) pos.y = 0.0;
        if (i == 1) pos.x = 0.999;
        if (i == 2) pos.x = 0.0;
        if (i == 3) pos.y = 0.999;
        pos = (floor(pos * float4(2.0, 3.0, 2.0, 3.0)) + 0.5) / float4(2.0, 3.0, 2.0, 3.0);
        if (any(pos.xy != pos.zw)) {
            float2 pa = uv - pos.xy, ba = pos.zw + 0.001 - pos.xy;
            float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
            d = min(d, length(pa - ba * h));
        }
    }
    return d;
}

// Digital rain seen along a ray. xy horizontal, z vertical. time wraps the rain positions;
// glyphTime continues across route wraps, with only the hash seed reduced below 4096.
float3 hdMxRain(float3 ro, float3 rd, float time, float glyphTime) {
    float4 result = float4(0.0);
    float2 ro2 = ro.xy;
    float t3ToT2 = max(length(rd.xy), 1e-4);
    float2 rd2 = rd.xy / t3ToT2;
    rd2 = select(rd2, float2(1e-5), abs(rd2) < 1e-5);
    float2 stepDir = sign(rd2);
    float2 invD = 1.0 / rd2;
    float2 cell = floor(ro2 / hdMxXYCell);
    float2 tMax = ((cell + step(0.0, rd2)) * hdMxXYCell - ro2) * invD;
    float2 tDelta = hdMxXYCell * abs(invD);
    const float rad = hdMxCharW * 0.5;
    float t2 = 0.0;
    for (int i = 0; i < 16; ++i) {
        float2 c = cell;
        float t2s = t2;
        float2 m = tMax.x < tMax.y ? float2(1.0, 0.0) : float2(0.0, 1.0);   // branchless DDA step
        t2 = min(tMax.x, tMax.y);
        tMax += m * tDelta;
        cell += m * stepDir;

        // Streets: 2-cell gaps every 10 cells, with cut corners.
        float2 inBlock = fract(c * 0.1);
        if (inBlock.x < 0.2 || inBlock.y < 0.2 || (inBlock.x < 0.3 && inBlock.y < 0.3)) continue;

        // One strip line per column; nearest approach of the 2D ray to it.
        float2 hc = hdMxHash22(c);
        float2 target = c * hdMxXYCell + rad + hc * (hdMxXYCell - 2.0 * rad);
        float2 s = target - ro2;
        float tmin = dot(s, rd2);
        if (tmin < t2s || tmin > t2) continue;
        float u = s.x * rd2.y - s.y * rd2.x;
        if (abs(u) >= rad) continue;
        u = (u / rad + 1.0) * 0.5;

        float z = ro.z + rd.z * tmin / t3ToT2;
        // Fall speed quantized to 0.1 so the rain repeats exactly over the 960-unit scene loop.
        float speed = max(1.0, floor((0.5 + hc.y + hc.y * hc.y + pow(hc.y, 16.0) * 3.0) * 10.0 + 0.5)) * 0.1;
        float zShift = hc.x * 11.0 - time * speed;
        float charShift = floor(zShift / hdMxCharH);
        zShift = charShift * hdMxCharH;
        float zcell = floor((z - zShift) / hdMxZCell);
        float4 ch = hdMxHash43(float3(c, zcell - 16.0 * floor(zcell / 16.0)));
        float4 ch2 = fract(ch * float4(127.1, 311.7, 271.9, 124.6));
        float count = ch.w * 33.0 + 7.0;
        float len = count * hdMxCharH;
        float targetZ = zcell * hdMxZCell + zShift + ch.z * (hdMxZCell - len);
        float v = (z - targetZ) / len;
        if (v < 0.0 || v >= 1.0) continue;
        float k = floor(v * count);
        float q = fract(v * count);
        float idx = k + charShift;
        float2 charHash = hdMxHash22(float2(idx - 640.0 * floor(idx / 640.0), ch2.x * 97.0));
        if (charHash.x < 0.1 && k != 0.0) continue;   // 10% missing symbols
        float rate = k == 0.0 ? 1.0 : ch2.z + ch2.w * ch2.w * 4.0 * pow(charHash.y, 4.0);
        float tf = floor(glyphTime * rate);
        float d = hdRuneDistance(float2(u, q), float2(floor(charHash.x * 1024.0), tf - 4096.0 * floor(tf / 4096.0)));
        float highlight = max(1.0, 3.0 - k * 0.5) * 0.2;
        float a = smoothstep(0.1, 0.0, d) + highlight * smoothstep(0.4, 0.0, d);
        a = min(a * clamp((count - 0.5 - k) * 0.5, 0.0, 1.0), 1.0);
        if (a <= 0.0) continue;
        float dist = tmin / t3ToT2;
        float att = 1.0 + (0.06 * dist) * (0.06 * dist);
        float fog = smoothstep(18.0, 18.0 * 0.55, dist);
        float3 col = (k == 0.0 ? float3(0.67, 1.0, 0.82) : float3(0.25, 0.80, 0.40)) * (fog / att);
        float a1 = result.a;
        result.a = a1 + (1.0 - a1) * a;
        result.rgb = (result.rgb * a1 + col * (1.0 - a1) * a) / result.a;
        if (result.a > 0.98) return result.rgb;
    }
    return result.rgb * result.a;
}

float2 hdMxRotate(float2 v, float a) {
    float s = sin(a), c = cos(a);
    return float2(c * v.x + s * v.y, -s * v.x + c * v.y);
}

float3 hdMxRotateX(float3 v, float a) { float s = sin(a), c = cos(a); return float3(v.x, c * v.y + s * v.z, -s * v.y + c * v.z); }
float3 hdMxRotateY(float3 v, float a) { float s = sin(a), c = cos(a); return float3(c * v.x + s * v.z, v.y, -s * v.x + c * v.z); }
float3 hdMxRotateZ(float3 v, float a) { float s = sin(a), c = cos(a); return float3(c * v.x + s * v.y, -s * v.x + c * v.y, v.z); }

float3 shade(float2 p, float t, float2 pixel) {
    const float period = 1920.0;                     // seconds for one full walk of the route
    float tw = t + 100.0;                            // start somewhere scenic
    float time = (tw - period * floor(tw / period)) * 0.5;   // SPEED
    float glyphTime = tw * 0.5;                      // glyph updates continue across route wraps

    const float turnRad = 0.25 / 3.0;
    const float turnAbsTime = (hdMxPI / 2.0 * turnRad) * 1.5;
    const float turnTime = turnAbsTime / (1.0 - 2.0 * turnRad + turnAbsTime);
    const float level1 = 10.0 * 3.0 * hdMxXYCell;
    const float level2 = 4.0 * level1;
    const float gapSize = 2.0 * hdMxXYCell;

    float3 ro = float3(gapSize * 0.5, gapSize * 0.5, 0.0);
    float3 rd = float3(0.5 + p.x, 2.0, 0.5 + p.y);

    float tq = fract(time / (level2 * 4.0) * 0.5 * hdMxXYCell);
    float t8 = fract(tq * 4.0);
    float t1 = fract(t8 * 8.0);

    float2 prev, dir;
    if (tq < 0.25)      { prev = float2(0.0, 0.0); dir = float2(0.0, 1.0); }
    else if (tq < 0.5)  { prev = float2(0.0, 1.0); dir = float2(1.0, 0.0); }
    else if (tq < 0.75) { prev = float2(1.0, 1.0); dir = float2(0.0, -1.0); }
    else                { prev = float2(1.0, 0.0); dir = float2(-1.0, 0.0); }
    float angle = floor(tq * 4.0);
    prev *= 4.0;

    const float firstLook = 0.4, secondDrift = 0.5, fifthDrift = 0.25;
    float2 turn = float2(0.0);
    float turnSign = 0.0;
    float2 dirL = hdMxRotate(dir, -hdMxPI / 2.0);
    float2 dirR = -dirL;
    float upDown = 0.0, rotateOnTurns = 1.0, rollOnTurns = 1.0, addAngle = 0.0;
    if (t8 < 0.125) {
        turn = dirL; turnSign = -1.0;
        angle -= firstLook * (max(0.0, t1 - (1.0 - turnTime * 2.0)) / turnTime - max(0.0, t1 - (1.0 - turnTime)) / turnTime * 2.5);
        rollOnTurns = 0.0;
    } else if (t8 < 0.25) {
        prev += dir; turn = dir; dir = dirL; angle -= 1.0; turnSign = 1.0;
        addAngle += firstLook * 0.5 + (-firstLook * 0.5 + 1.0 + secondDrift) * t1;
        rotateOnTurns = 0.0; rollOnTurns = 0.0;
    } else if (t8 < 0.375) {
        prev += dir + dirL; turn = dirR; turnSign = 1.0;
        addAngle += secondDrift * sqrt(1.0 - t1);
    } else if (t8 < 0.5) {
        prev += dir + dir + dirL; turn = dirR; dir = dirR; angle += 1.0; turnSign = 0.0;
        upDown = sin(t1 * hdMxPI) * 0.37;
    } else if (t8 < 0.625) {
        prev += dir + dir; turn = dir; dir = dirR; angle += 1.0; turnSign = -1.0;
        upDown = sin(-min(1.0, t1 / (1.0 - turnTime)) * hdMxPI) * 0.37;
    } else if (t8 < 0.75) {
        prev += dir + dir + dirR; turn = dirL; turnSign = -1.0;
        addAngle -= (fifthDrift + 1.0) * smoothstep(0.0, 1.0, t1);
        rotateOnTurns = 0.0; rollOnTurns = 0.0;
    } else if (t8 < 0.875) {
        prev += dir + dir + dir + dirR; turn = dir; dir = dirL; angle -= 1.0; turnSign = 1.0;
        addAngle -= fifthDrift - smoothstep(0.0, 1.0, t1) * (fifthDrift * 2.0 + 1.0);
        rotateOnTurns = 0.0; rollOnTurns = 0.0;
    } else {
        prev += dir + dir + dir; turn = dirR; turnSign = 1.0;
        angle += fifthDrift * (1.5 * min(1.0, (1.0 - t1) / turnTime) - 0.5 * smoothstep(0.0, 1.0, 1.0 - min(1.0, t1 / (1.0 - turnTime))));
    }
    angle += addAngle;

    rd = hdMxRotateX(rd, upDown);
    float2 pos;
    if (turnSign == 0.0) {
        pos = prev + dir * (turnRad + t1);
    } else if (t1 > 1.0 - turnTime) {
        float tr = (t1 - (1.0 - turnTime)) / turnTime;
        float2 c = prev + dir * (1.0 - turnRad) + turn * turnRad;
        pos = c + turnRad * hdMxRotate(dir, (tr - 1.0) * turnSign * hdMxPI / 2.0);
        angle += tr * turnSign * rotateOnTurns;
        rd = hdMxRotateY(rd, sin(tr * turnSign * hdMxPI) * 0.2 * rollOnTurns);
    } else {
        pos = prev + dir * (turnRad + (1.0 - turnRad * 2.0) * (t1 / (1.0 - turnTime)));
    }
    rd = hdMxRotateZ(rd, angle * hdMxPI / 2.0);
    ro.xy += level1 * pos;
    rd = normalize(rd);
    ro += rd * 0.2;

    float3 col = hdMxRain(ro, rd, time, glyphTime);
    return col * col;
}
