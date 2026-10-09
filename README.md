# HolodeckShaders

Public source of truth for Holodeck's runtime Metal shaders. `main` contains authoring files; `published` contains a complete validated catalog, full Metal libraries and PNG previews. The app pins every download to one published commit. No backend or login is needed.

## Authoring

Requires a Mac with Xcode and a Metal device for rendering previews. Python 3 uses only its standard library.

1. Create `shaders/<id>/metadata.json` and `body.metal`. IDs are stable lowercase words separated by hyphens. Metadata includes `id`, `name`, `description`, `category` (`PROCEDURAL` or `3D MATERIAL`), two RGB colors with values in 0...1, and `shared`: `["common", "fragment"]` or `["common", "material", "fragment"]`.
2. Add the ID to the ordered `shaders` array in `index.json`. Its `defaultShaderID` must exist. Bodies implement `float3 shade(float2 p, float time, float2 pixel)`; shared helpers supply the vertex, fragment and buffer-0 uniform contract.
3. Run `python3 tools/catalog.py generate`. This renders every preview at 1280×720, time 3 seconds, to an sRGB Metal target, and writes the source/render-settings fingerprint and PNG hash. Commit source, metadata, `preview.png` and `preview.json` together. Shared helper edits require regenerating dependent previews.
4. Commit changes, then run `python3 tools/catalog.py validate`. This verifies metadata and previews, derives update dates from Git, assembles full sources and compiles them for tvOS. It writes `dist/catalog.json`, `dist/sources/` and `dist/previews/`.
5. Merge to `main`. GitHub Actions repeats validation before replacing `published` with one complete commit. Pull requests validate without publishing. Failed validation leaves the previous publication available; GitHub Actions can be rerun with workflow_dispatch.

`updatedAt` is the committer date of the latest commit affecting that shader's metadata, body or shared helpers. Initial dates come from the migration commit. Preview-only regeneration does not change the date. The manifest records the authoring commit as `sourceRevision`; the app separately records the publication commit.

## Offline app snapshot

From the Holodeck checkout, run `python3 tools/update-bundled-catalog.py`. It fetches the public published ref, verifies metadata and all source/image hashes, then exports the bundled JSON and PNGs. Commit those resources with the app. Ordinary Xcode builds and tests never fetch content.

For local export after building this repository:

```sh
python3 tools/catalog.py export-bundle --app ../Holodeck/Holodeck/BundledCatalog --publication-revision <published-commit-sha>
```

## Contract

`catalog.json` schema version 1 contains `defaultShaderID`, `sourceRevision`, and ordered `shaders` entries: `id`, `name`, `category`, `description`, `colors`, UTC ISO-8601 `updatedAt`, `sourcePath`, `sourceSHA256`, `previewPath`, `previewSHA256`. Paths are `sources/<id>.metal` and `previews/<id>.png`; hashes are lowercase SHA-256. Each source is a complete runtime library exposing `vertexShader` and `fragmentShader` with the 16-byte `ShaderUniforms` layout. Keep this contract compatible with released apps; incompatible formats require a new schema version.
