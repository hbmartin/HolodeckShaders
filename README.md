# HolodeckShaders

Shader sources and authoring assets for Holodeck. HolodeckMac loads this folder, generates previews, and serves a complete catalog to Apple TV over the local network. Shader edits require reload, not an app rebuild.

## Authoring

See [the reuse library](docs/shader-library.md) and [authoring workflow](docs/shader-authoring.md). Python uses only its standard library. SDK compilation requires Xcode; sample rendering and GPU regression tests use the installed Holodeck CLI on a Mac with Metal.

1. Search techniques with `python3 tools/library.py search "flowing ribbons"` and inspect contracts with `show`.
2. Create `shaders/<id>/metadata.json` and `body.metal`, or scaffold with `python3 tools/library.py new shader my-scene`. Bodies implement `float3 shade(float2 p, float time, float2 pixel)`.
3. Run `python3 tools/library.py validate --compile` and `python3 -m unittest discover -s tools -p 'test_*.py'`. Validation includes unlisted shaders; compilation covers every complete shader and snippet example for macOS and tvOS.
4. Render samples with `python3 tools/library.py render shader my-scene --times 0,3,10`. Inspect motion and target-device performance in Holodeck.
5. When selected, add the stable ID to the ordered `shaders` array in `index.json` and any collections. Commit source and metadata. In HolodeckMac, select this folder under **Settings → Shader Library**, then press **Reload Shaders**.

Only indexed shaders enter the app catalog. Snippets, reference originals, templates, documentation, and `reuse` links remain authoring assets. Original references and required source license notices must be preserved.

## GPU tooling

Follow Holodeck's [CLI installation instructions](https://github.com/hbmartin/Holodeck#shader-tooling). This repo resolves the installed executable through `PATH`, or `HOLODECK_SHADER_TOOL` set to its absolute path. `holodeck-shader-tool --version` must report major version 1; the version check has a five-second timeout and receives no interactive input. An invalid explicit override, including an empty value, does not fall back to another executable.

Run `HOLODECK_GPU_TESTS=1 python3 -m unittest discover -s tools -p 'test_*.py'` for shader-specific geometry, seed, parser, and long-uptime probes. Generic GPU probe tests live in HolodeckCore; see the same tooling guide. Static validation and CI require no installed CLI or sibling checkout.

## Delivery and previews

Use an updated HolodeckMac that generates previews, then choose this folder under **Settings → Shader Library** and press **Reload Shaders** after edits. Holodeck owns previews, caches, and local publications; do not commit generated images here. See its [local library workflow](https://github.com/hbmartin/Holodeck/blob/main/docs/shader-catalog-workflow.md) for preview behavior and TV setup, and its [technical reference](https://github.com/hbmartin/Holodeck/blob/main/docs/local-shader-serving.md) for serving and app behavior.

GitHub publication is retired. The existing `published` branch remains frozen for older clients; CI validates authoring assets without publishing. No committed previews, generated publication directory, or historical verification reports are needed for authoring.
