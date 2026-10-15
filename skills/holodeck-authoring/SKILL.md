---
name: holodeck-authoring
description: "Create, adapt, inspect, and verify assets in a Holodeck shader library checkout. Use for Holodeck's shade contract, reusable snippets, reference provenance, and catalog selection; generic Metal integration belongs to the existing Metal skills."
---

# Holodeck authoring

Locate the library checkout from the user's request or working directory. Confirm its `index.json`, `authoring.json`, `shared/`, and asset folders. An installed copy of this skill is not the library root. Use the chosen root explicitly in all tool commands.

Read `docs/shader-library.md` and `docs/shader-authoring.md` in that checkout before creating or adapting a shader. They own the runtime, licensing, reference-inventory, and editorial contracts; do not duplicate or infer a different contract.

## Find and compose

Search names, tags, search terms and declared symbols with `rg` in `snippets/`, `references/`, and `shaders/`. Read relevant JSON specifications, snippet contracts and complete examples directly. Reference guidance is in `reference.json` fields, including optional Markdown `notes`. Read originals only when needed and permitted by their recorded license.

For new assets, copy the matching directory from `templates/` into a new, valid unused ID directory. Check that the destination does not exist or resolve through a symlink before copying; refuse overwrites. Replace `__ID__` and `__NAME__` in all template files and refine the code, metadata and contract. Leave a new shader unlisted until selected. References are added manually with explicit provenance and SHA-256 inventories; preserve upstream bytes and notices.

Use canonical shared helpers. `reuse` links identify related assets and never assemble dependencies. Preserve each copied source's required notices independently, even if the same notice occurs in a shared helper. Register every new copyable source deliberately in `authoring.json`'s `sourceRequirements`; an original source uses an explicit empty list. Do not generate empty provenance records from discovery. Add supported upstream notice requirements when needed. Preserve existing obligations and regression profiles.

## Verify

Use the installed `holodeck-shader-tool` version 1.1.0 or later with its matching resource bundle:

```sh
holodeck-shader-tool library info --json
holodeck-shader-tool library validate /absolute/library/root --compile
holodeck-shader-tool library validate /absolute/library/root --gpu
holodeck-shader-tool library render /absolute/library/root shader my-scene --times 0,3,10
```

For snippets, replace `shader my-scene` with `snippet my-technique`. A standalone verified `holodeck-shader-check` wheel or zipapp can run portable `validate ROOT` without the native tool, Git, Xcode or Metal. Use an absolute `--python` interpreter on native library commands when the default system Python is unsuitable. See the root README for installation and checksum verification.

Inspect rendered samples and actual animation in Holodeck. Compilation, GPU probes, visual review, and target-device performance are separate evidence. Only IDs in `index.json` enter the app catalog. Add editorially selected shaders to its ordered list and appropriate collections, then reload the folder in HolodeckMac to verify delivery limits and previews.

Keep generated renders in ignored cache or explicit scratch output. Never commit previews, publication output, historical reports, or upstream cache/editor artifacts. Report reused assets, checks performed, and unavailable physical-device or minimum-OS verification accurately.

When Holodeck's managed request worker owns a checkout, follow its narrower request scope and host verification instructions. The host performs GPU tests, review, commits and publication; do not run a competing authoring workflow in its leased checkout.
