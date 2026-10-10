# Warp Speed 2

Shadertoy 4tjSDt by Dave Hoskins, CC BY-NC-SA 3.0. Originals are preserved only for permissive licenses. NC/SA or unlicensed sources are recorded here as metadata only (no files); see docs/shader-library.md.

Single pass, no buffers. The algorithm marches 100 samples along each ray through a z-repeating slab of Kali's fold `p = abs(p*2.04)/dot(p,p) - 0.9`, accumulating `pow(dot(p,p), 0.7)` into a teal/blue colour ramp. Time runs at 58x; drift periods are roughly 22–34 s.
