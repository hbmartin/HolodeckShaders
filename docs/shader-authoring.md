# Authoring and selection

1. Search the library and inspect relevant contracts and complete shaders.
2. Use the authoring skill to copy a matching template into a valid unused asset directory. Check for existing files and symlinks, refuse overwrites, and replace all ID/name placeholders. Refine names, descriptions, code and contracts before reuse.
3. Copy and adapt recipe functions and their required license notices into the shader body; use canonical shared helpers where appropriate. Retain attribution and describe changes. Follow the Licensing section of `docs/shader-library.md`; metadata and references do not accompany published sources. Record related snippet/reference IDs in metadata.reuse.
4. Run `holodeck-shader-tool library validate ROOT --compile` with an explicit library root. This validates all authoring assets, including temporary template instances, and locally compiles every complete shader, snippet example and shader/snippet template for macOS and tvOS.
   Register new copyable source paths and MIT/CC provenance in `authoring.json`. Portable `holodeck-shader-check validate ROOT` performs static and CPU profile checks without the native CLI. Before native checks, require `holodeck-shader-tool library info --json` to report the checker version and integer interface recorded in the library's `shader_checker.lock.json`. Run `holodeck-shader-tool library validate ROOT --gpu` locally for actual shared-source uniform/clamp, scene geometry/seed, and long-uptime GPU probes. Checker implementation and integration tests live in HolodeckShaderCheck. Linux CI requires the CPU library and license tests; the GPU-only combined-recipe composition test remains explicit local verification. Use the exact locked source checkout as described below.
5. Render samples with `holodeck-shader-tool library render ROOT shader my-scene --times 0,3,10` (or `library render ROOT snippet my-technique`). Optional `--width`/`--height` select dimensions. Artifacts go to ignored `.cache/library/`. Review actual animation and target-device performance in the app before selecting a scene.
6. When editorially ready, add the finished shader ID to the ordered index.shaders array and any appropriate collections. Commit source and metadata, then reload the selected folder in an updated HolodeckMac. The app generates previews; do not add preview files to this repo.

## Runtime contract

Bodies implement `float3 shade(float2 p, float time, float2 pixel)`. p is `(pixel-resolution/2)/resolution.y` with Y flipped upward; its vertical range is approximately -0.5 to 0.5 and horizontal range depends on aspect ratio. pixel uses Metal raster coordinates, with Y downward. time is seconds. Return RGB; the wrapper clamps to [0,1], returns alpha 1 and renders to an sRGB target. The 16-byte buffer-0 layout is float2 resolution, float time, float padding. Existing vertexShader/fragmentShader names must remain compatible.

The current renderer supplies no texture channels, pointer/audio input, previous-frame buffers or additional passes. References requiring those features need explicit integration rather than a silent approximation. Helpers should state whether they return masks, distances, RGB light or complete colors.

## Discovery and curation

Optional discovery is `{tags: [strings], moods: [strings], motion: string}`. Initial moods are calm, dreamy, energetic; motion is slow, steady, fast. These describe the experience, not performance. Vocabulary additions require updating producer validation and these instructions; apps preserve open string values.

Optional index.collections entries contain id/name/description and ordered shaderIDs. IDs are lowercase hyphen-separated and `all` is reserved. Members must be published shader IDs, unique within each collection and nonempty; collections may overlap. All uses index.shaders order. Plasma remains the initial default.

Select scenes for distinctive visual experience, sustained motion quality, representative previews and acceptable measured performance at target resolution. Compile success alone does not select a shader for the catalog. Record device-specific performance evidence without claiming measurements on untested devices.

## Validation and delivery

To run checker integration/GPU tests locally, prepare the artifact from this library root and save its validated metadata in ignored storage:

```sh
mkdir -p .cache
python3 -I tools/checker_bootstrap.py prepare > .cache/checker-pin.json
```

Read `repository`, `sourceCommit` and `artifactPath` from that JSON. Fetch `https://github.com/<repository>.git` into an unused scratch checkout, check out exactly `sourceCommit` with a detached HEAD, then verify it before running tests:

```sh
python3 -I tools/checker_bootstrap.py verify-source --source /absolute/checker/checkout --artifact /absolute/prepared/checker.pyz
HOLODECK_LIBRARY_ROOT=/absolute/library/root HOLODECK_SHADER_TOOL=/absolute/holodeck-shader-tool python3 -I /absolute/checker/checkout/tools/run_tests.py --gpu
```

Use the selected native executable's `library info --json` to confirm its checker version and integer interface match this library's lock. These integration tests retain specific asset-ID assumptions; use a coordinated library/checker pair when intentionally changing those assets. Generated renders stay in ignored storage.

Library validation includes unlisted shaders. HolodeckMac loads only index.shaders; snippets, originals, documentation and reuse links remain authoring-only. Reload the selected folder after edits. Holodeck's [local library workflow](https://github.com/hbmartin/Holodeck/blob/main/docs/shader-catalog-workflow.md) owns preview generation, caching, publication, and delivery guidance.

External authoring validation checks structure and preserves raw UTF-8 source bytes, including line endings. It does not enforce source or catalog byte-size budgets. Holodeck enforces its runtime limits (2 MiB manifest, 1 MiB per assembled source, 16 MiB total indexed sources), so successful authoring validation or compilation does not guarantee that the app can load a catalog. Reload in HolodeckMac to verify delivery. Size-limit failures identify the file or shader, actual bytes and allowed bytes, and preserve the previous publication. Preview generation requires a HolodeckMac build from commit `93ec2ee` or later; older builds require preview files this repo no longer stores.

Sample renders stay in ignored `.cache/library/` and never alter the app cache or source folder. Do not commit generated previews or publication output.

The installed `holodeck-shader-tool` owns sample rendering and GPU probes. The external checker disconnects interactive input and bounds each sample render to 120 seconds and each probe batch to 300 seconds. Positive finite `HOLODECK_RENDER_TIMEOUT_SECONDS` and `HOLODECK_PROBE_TIMEOUT_SECONDS` values override those deadlines; version checks retain five seconds. See the root README for CLI resolution requirements and Holodeck's [tooling guide](https://github.com/hbmartin/Holodeck#shader-tooling) for installation and generic probe tests. Portable static validation needs no native CLI; Linux CI verifies the checker artifact against the committed lock and runs CPU unit, real-library and license integration tests from its exact source commit. Native compilation, GPU profiles and composition rendering run only during explicit local verification. Checker code and tests live in the independent HolodeckShaderCheck repository. Shared-source contract and shader-specific regressions are selected by declarative profiles here. Check physical TV and minimum supported OS versions before release and report unavailable checks.
