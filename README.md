# HolodeckShaders

Shader sources, skills and authoring assets for Holodeck. HolodeckMac loads this folder, generates previews, and serves the selected catalog to Apple TV over the local network. Shader edits require reload, not an app rebuild.

## Authoring

Use [the Holodeck authoring skill](skills/holodeck-authoring/SKILL.md), [reuse library](docs/shader-library.md), and [authoring workflow](docs/shader-authoring.md). The skill locates the requested library checkout explicitly; its installation directory is not assumed to contain the assets. Generic Metal technique skills remain under `vendor/metal-skills`.

1. Search assets with `rg` and read their specifications, contracts and examples directly.
2. Copy a matching template into an unused asset directory, refuse overwrites, replace all placeholders, and refine the source and metadata. Bodies implement `float3 shade(float2 p, float time, float2 pixel)`.
3. Register every new copyable source and its upstream notice obligations in `authoring.json`.
4. Run `holodeck-shader-tool library validate ROOT --compile`; use `--gpu` locally for actual regression probes. Validation includes unlisted shaders and temporary template instances; local compilation covers every complete shader, snippet example, and shader/snippet template for macOS and tvOS.
5. Render with `holodeck-shader-tool library render ROOT shader my-scene --times 0,3,10`. Inspect samples, motion and target-device performance in Holodeck.
6. When selected, add the stable ID to the ordered `shaders` array in `index.json` and appropriate collections. Commit source and metadata, select this folder in **HolodeckMac → Settings → Shader Library**, then press **Reload Shaders**.

Only indexed shaders enter the app catalog. Snippets, originals, templates, documentation, provenance, and `reuse` links remain authoring assets. Original references and required source license notices must be preserved. Technical verification does not imply editorial selection.

## External tooling

[HolodeckShaderCheck](https://github.com/hbmartin/HolodeckShaderCheck) owns Python assembly, validation, license checks, CPU regressions, and GPU-profile orchestration. It has no runtime dependencies beyond Python 3.9 or later. This repository keeps only tooling bootstrap and skill-discovery checks with their tests; shader-authoring implementation and tests remain external.

For portable static validation, run this from the library root with Python 3.9 or later and curl. The committed `shader_checker.lock.json` pins the release, source commit, interface and SHA-256 independently of the downloaded release inventory. The shared bootstrap validates the lock, downloads to a temporary file, checks its checksum and reported version/interface, then atomically replaces the ignored cache. Failed downloads preserve the previous cache and fail without executing it. The command can be repeated without GitHub CLI authentication:

```sh
python3 -I tools/checker_bootstrap.py run -- validate "$PWD" --json
```

The helper resolves its default lock and cache beside this checkout even when called from another working directory. `prepare` emits validated pin metadata and an absolute `artifactPath`; `prepare` and `run` accept `--lock` and `--cache-dir` overrides. Bootstrap failures exit 2, while `run` preserves checker output and exit status. The committed lock is the trust anchor; checksums do not authenticate edits to that lock.

Static checks require no Git checkout, Xcode, Metal, native CLI, or sibling repository. Explicit roots allow checking unpacked libraries too. Linux CI selects Python 3.15, uses this same bootstrap, and validates the library before fetching test source. It verifies the source HEAD and every packaged file against the locked artifact before running CPU unit, real-library and license integration tests. Required CPU integration tests cannot silently skip. Existing integration tests depend on specific library asset IDs; deliberate changes to those IDs may require coordinated checker test updates. CI also checks that every local and vendor skill has the correct discovery link. CI performs no macOS/tvOS compilation, GPU execution or combined-recipe rendering, so it cannot establish Metal syntax correctness; run those checks explicitly on a Mac. Update this lock and Holodeck's bundled checker lock together when adopting a checker release.

For compilation, rendering, and GPU profiles, install `holodeck-shader-tool` **1.1.0 or later with its resource bundle and the checker version recorded in this library's lock** using [Holodeck's tooling instructions](https://github.com/hbmartin/Holodeck#shader-tooling). The native CLI bundles a checksum-pinned checker zipapp and runs it through isolated Python; runtime operation performs no downloads or package installation. Before native checks, inspect `library info --json` and require `checkerVersion` and the integer `interfaceVersion` to match the library lock. The native executable's version alone does not identify its bundled checker. Native library commands accept `--python /absolute/interpreter`, defaulting to `/usr/bin/python3`.

The standalone checker finds its native GPU backend through `--shader-tool /absolute/tool`, `HOLODECK_SHADER_TOOL`, or PATH when neither override is set. Invalid explicit overrides, including empty environment values, never fall back. The backend must report major version 1. Version checks have a five-second timeout and disconnected stdin. Render and probe calls also disconnect stdin and use 120/300-second deadlines. Positive finite `HOLODECK_RENDER_TIMEOUT_SECONDS` and `HOLODECK_PROBE_TIMEOUT_SECONDS` override operation deadlines; invalid values fail before execution.

Checker exit codes are 0 (success), 1 (failed checks), and 2 (usage or unavailable tooling). `validate --json` emits one structured result on stdout. Render samples default to ignored `.cache/library/`; they never alter app caches or source assets.

## Delivery and cutover

Holodeck owns previews, caching, publication and delivery. See its [local library workflow](https://github.com/hbmartin/Holodeck/blob/main/docs/shader-catalog-workflow.md). Do not commit generated previews, publication output, or historical verification reports. The legacy `published` branch remains frozen; CI validates without publishing.

Authoring validation and compilation preserve raw UTF-8 assembly bytes and accept oversized sources. Holodeck enforces delivery limits of 1 MiB per assembled source, 16 MiB across indexed sources, and 2 MiB per manifest. Reload in HolodeckMac to verify delivery; rejected candidates report byte counts and limits while preserving the previous publication.

The script-free authoring cutover requires the updated Holodeck build for automated shader requests. Its worker verifies the checker interface and schema, permits only scoped provenance additions, and independently performs technical/GPU/image verification. Older builds that invoke local Python scripts cannot manage requests against this checkout. Ordinary catalog loading remains compatible with builds that generate their own previews (commit `93ec2ee` or later). Drain active requests before switching a managed checkout.
