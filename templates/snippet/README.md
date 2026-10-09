# __NAME__

Draft recipe. Complete these details before reuse.

## Interface

`float3 hdRecipe(float2 p, float t)` returns grayscale RGB in [0,1]. No extra dependencies. Rename the symbol when composing multiple recipes.

## Coordinates

p is centered, height-normalized and Y upward; t is seconds.

## Tuning

Scale p and t to control spatial frequency and speed.

## Limitations

Starter sine pattern; inspect the adapted result at target resolution.

## Cost

Estimate: one sine per pixel; no measured benchmark.
