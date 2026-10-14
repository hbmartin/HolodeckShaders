# Shader authoring

Read `docs/shader-library.md` and `docs/shader-authoring.md` before creating or adapting shaders. Use `python3 tools/library.py search` to find techniques, then inspect their specifications and examples with `show`.

Respect the runtime coordinate/uniform contract. Compose documented recipes deliberately; `reuse` links describe related techniques, not executable dependencies. Check snippet and reference licenses before copying code (see Licensing in `docs/shader-library.md`). Keep production shared helpers canonical and preserve original reference files.

Run library validation, compile relevant examples for macOS and tvOS, render samples, and inspect motion in the app. Report the assets reused and any unverified requirements. Only IDs explicitly listed in `index.json` enter the local app catalog; technical verification does not imply editorial selection.

Holodeck owns generated previews and GPU tooling. Use the installed `holodeck-shader-tool` for sample rendering and probes; static library validation needs no CLI. Do not commit previews, publication output, or historical verification reports. Add references manually with explicit provenance and checksum inventory; preserve originals.
