# Shader authoring

Read `docs/shader-library.md` and `docs/shader-authoring.md` before creating or adapting shaders. Follow `skills/holodeck-authoring/SKILL.md`: search assets with `rg`, read specifications/contracts/examples directly, and scaffold from templates without overwrites.

Respect the runtime coordinate/uniform contract. Compose documented recipes deliberately; `reuse` links describe related techniques, not executable dependencies. Check snippet and reference licenses before copying code (see Licensing in `docs/shader-library.md`). Keep production shared helpers canonical and preserve original reference files.

Run `holodeck-shader-tool library validate ROOT --compile` (or `--gpu` for actual regression probes), render samples with `library render ROOT`, and inspect motion in the app. Use an explicit library root. Report the assets reused and any unverified requirements. Only IDs explicitly listed in `index.json` enter the local app catalog; technical verification does not imply editorial selection.

Holodeck owns generated previews and GPU tooling. Use the installed `holodeck-shader-tool` for sample rendering and probes; portable static checks use the independent `holodeck-shader-check` package without the native CLI. Register copyable sources and upstream obligations in `authoring.json`; preserve the schema and versioned regression profiles. Do not commit previews, publication output, or historical verification reports. Add references manually with explicit provenance and checksum inventory; preserve originals.
