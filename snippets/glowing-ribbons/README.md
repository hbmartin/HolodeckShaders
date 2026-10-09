# Glowing Ribbons

A soft luminous ribbon mask with a tight core and broad halo.

## Interface

```metal
float hdGlowingRibbon(float y, float center, float width);
```

Returns scalar intensity, not RGB. Intensity is 1.18 at the ribbon center and decays toward zero. No helper dependencies in the function itself.

Canonical source: `snippets/glowing-ribbons/code.metal`. Example: `snippets/glowing-ribbons/example.metal`.

## Coordinates

y and center must use the same units; example uses height-normalized screen coordinates. width is the core falloff length in those units.

## Tuning

Width 0.005–0.05; sinusoidal center amplitude 0.05–0.3. Multiply the mask by a color and sum several independently offset ribbons.

## Limitations

Very narrow cores can alias; summed layers can exceed 1 and clip. Width is clamped to 0.0001.

## Cost

Estimate: two exponential evaluations per ribbon. Example has one ribbon.

## Reuse and origin

Derived from `shaders/waves/body.metal`. Copy and adapt recipe functions; shared helpers remain canonical. Compile and render the example after changes. See `docs/shader-authoring.md` for the runtime and publication contract.
