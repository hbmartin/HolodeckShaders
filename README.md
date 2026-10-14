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

Build and install from the Holodeck checkout:

```sh
swift build --package-path HolodeckCore -c release --product holodeck-shader-tool
mkdir -p "$HOME/.local/bin"
install HolodeckCore/.build/release/holodeck-shader-tool "$HOME/.local/bin/holodeck-shader-tool"
```

Add that directory to `PATH`, or set `HOLODECK_SHADER_TOOL` to the executable's absolute path. `holodeck-shader-tool --version` must report major version 1; the version check has a five-second timeout and receives no interactive input. An invalid explicit override, including an empty value, does not fall back to another executable. Run `HOLODECK_GPU_TESTS=1 python3 -m unittest discover -s tools -p 'test_*.py'` for actual GPU regression probes. Static validation and CI do not require this executable or a sibling checkout.

## Delivery and previews

Use an updated HolodeckMac that generates previews; older Mac builds require preview files that this repo no longer stores. The app reads source and metadata without Git commits, Python scripts, or Xcode. It renders previews at 1280×720 and three seconds, caches successful images in app-owned storage, and serves them with hash-verified sources in immutable local publications. Failed preview renders use metadata-color gradients and show diagnostics in Settings; reload retries them. Invalid authoring files retain the last valid publication. The source folder stays read-only.

Apple TV pairs with the Mac and uses its downloaded cache offline. The app's catalog schema, source entry points, 16-byte uniform layout, ordered collections, and discovery fields remain compatible. See Holodeck's [local library workflow](https://github.com/hbmartin/Holodeck/blob/main/docs/shader-catalog-workflow.md).

GitHub publication is retired. The existing `published` branch remains frozen for older clients; CI validates authoring assets without publishing. No committed previews, generated publication directory, or historical verification reports are needed for authoring.
