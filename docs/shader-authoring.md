# Authoring and selection

1. Search the library and inspect relevant contracts and complete shaders.
2. Scaffold with `python3 tools/library.py new shader my-scene` or `new snippet my-technique`. Commands refuse overwrites. Refine names, descriptions, code and contracts before reuse.
3. Copy and adapt recipe functions and their required license notices into the shader body; use canonical shared helpers where appropriate. Retain attribution and describe changes. Follow the Licensing section of `docs/shader-library.md`; metadata and references do not accompany published sources. Record related snippet/reference IDs in metadata.reuse.
4. Run `python3 tools/library.py validate --compile`. This validates all authoring assets and compiles every complete shader and snippet example for macOS and tvOS.
   Register new copyable source paths and MIT/CC provenance in the test-only notice inventory, then run `python3 -m unittest discover -s tools -p 'test_*.py'`. Set `HOLODECK_GPU_TESTS=1` locally to include actual Metal timing and geometry regression probes.
5. Render samples with `python3 tools/library.py render shader my-scene --times 0,3,10` (or `render snippet my-technique`). Optional `--width`/`--height` select dimensions. Artifacts go to ignored `.cache/library/`. Review actual animation and target-device performance in the app before selecting a scene.
6. When editorially ready, add the finished shader ID to the ordered index.shaders array and any appropriate collections. Commit source and metadata, then reload the selected folder in an updated HolodeckMac. The app generates previews; do not add preview files to this repo.

## Runtime contract

Bodies implement `float3 shade(float2 p, float time, float2 pixel)`. p is `(pixel-resolution/2)/resolution.y` with Y flipped upward; its vertical range is approximately -0.5 to 0.5 and horizontal range depends on aspect ratio. pixel uses Metal raster coordinates, with Y downward. time is seconds. Return RGB; the wrapper clamps to [0,1], returns alpha 1 and renders to an sRGB target. The 16-byte buffer-0 layout is float2 resolution, float time, float padding. Existing vertexShader/fragmentShader names must remain compatible.

The current renderer supplies no texture channels, pointer/audio input, previous-frame buffers or additional passes. References requiring those features need explicit integration rather than a silent approximation. Helpers should state whether they return masks, distances, RGB light or complete colors.

## Discovery and curation

Optional discovery is `{tags: [strings], moods: [strings], motion: string}`. Initial moods are calm, dreamy, energetic; motion is slow, steady, fast. These describe the experience, not performance. Vocabulary additions require updating producer validation and these instructions; apps preserve open string values.

Optional index.collections entries contain id/name/description and ordered shaderIDs. IDs are lowercase hyphen-separated and `all` is reserved. Members must be published shader IDs, unique within each collection and nonempty; collections may overlap. All uses index.shaders order. Plasma remains the initial default.

Select scenes for distinctive visual experience, sustained motion quality, representative previews and acceptable measured performance at target resolution. Compile success alone does not select a shader for the catalog. Record device-specific performance evidence without claiming measurements on untested devices.

## Validation and delivery

Library validation includes unlisted shaders. HolodeckMac's local publication includes only index.shaders and serves assembled sources and app-generated PNG previews plus optional discovery/collections; snippets, originals, documentation and reuse links remain authoring-only. Schema version stays 1 because additions are optional. Older clients ignore additions; new clients read older snapshots with missing discovery.

Python validation checks structure and preserves raw UTF-8 source bytes, including line endings. It does not enforce source or catalog byte-size budgets. Holodeck enforces its runtime limits (2 MiB manifest, 1 MiB per assembled source, 16 MiB total sources), so successful Python validation or compilation does not guarantee that the app can load a catalog. Reload in HolodeckMac to verify delivery.

Holodeck generates previews at 1280×720 and three seconds using the sRGB render target. Successful renders are cached outside this repo by source hash, render settings, and renderer version. Failures use metadata-color gradients and produce per-shader diagnostics; reload retries them. Sample renders stay in ignored `.cache/library/` and never alter the app cache or source folder.

The installed `holodeck-shader-tool` in Holodeck owns offscreen drawing, PNG rendering, and GPU render/compute probes, using the runtime uniform and pipeline contracts. See the root README for installation. Static validation needs no CLI; CI runs Python tests and compiles all complete shaders and examples for macOS and tvOS. GitHub publication is retired and `published` remains frozen. Check physical TV and minimum supported OS versions before release and report unavailable checks.
