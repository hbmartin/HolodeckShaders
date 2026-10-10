# Shader library

The app catalog is an editorial selection of finished experiences. The authoring library stores reusable techniques and complete references. One finished shader can be both a catalog entry and a useful example.

## Discovery

Run `python3 tools/library.py list`, `search "flowing ribbons"`, or `show snippet glowing-ribbons`. Add `--kind snippet` to searches or `--json` to discovery commands for machine-readable results. Search matches every query term, case-insensitively, and ranks names/symbols before tags and descriptive terms. Paths are relative to this repository.

| Snippet | Use |
| --- | --- |
| value-noise | Smooth random fields, grain, mist |
| fbm | Clouds, nebulae, domain warping |
| cosine-palette | Continuous color cycles |
| studio-material | Sphere, floor and studio metal reflections |
| glowing-ribbons | Soft luminous trails |
| polar-fold | Mirrored radial patterns |
| layered-stars | Drifting star layers |
| aurora-curtains | Noise-modulated curtains of light |

Shared-helper snippets link to the existing implementation. Recipe snippets have copyable `code.metal` functions. Every snippet includes a machine-readable specification, a contract and a working example. The example harness concatenates declared existing helpers, recipe code if applicable, the example body and the standard fragment wrapper. It is a validation harness, not a production dependency assembler.

## References and provenance

Use `python3 tools/library.py import-reference my-source --source ./source --language GLSL` to preserve a local file or directory. Relative and absolute source paths work. Imports require Git and a working checkout, reject symlinks and overwrites, and preserve accepted file names and bytes. They record the public reference ID as `origin.importedFrom`, UTC import time and every original file's SHA-256, and never convert source or add it to the app. A reference becomes visible only after its staged files and metadata pass validation.

Imports reject selected source entries named `.git`, `.DS_Store`, `__pycache__`, `.idea`, `.vscode` or `xcuserdata`, including entries nested inside directories. Other hidden files and `.gitignore` files are allowed. Imports also reject files ordinary Git staging would omit at the intended destination, using repository ignore rules, imported nested `.gitignore` files, and local/global excludes. Rejections list repository-relative paths and reasons; prepare a clean source or adjust ignore rules, then retry. Files are never silently excluded. Copied directory permissions are made writable for staging and cleanup; source permissions and copied file executable bits are preserved. If cleanup fails, the original import error is retained and the remaining hidden staging location is reported separately.

Successful imports do not record the local source location in generated provenance metadata or a separate local record. File names, original contents and error diagnostics may contain identifying information; imports do not anonymize them. Fill in the original URL, author, license, requirements and adaptation notes. Unknown provenance stays explicitly unknown. `validate` checks the inventory and bytes against recorded checksums and requires `origin.importedFrom`, when present, to equal the public reference ID. Replace legacy local paths in that field with the ID; validation does not rewrite metadata or Git history. Keep originals unchanged and adapt into a separate finished shader or snippet.

Initial examples are the eight canonical shaders under `shaders/`; their originals are not duplicated in `references/`.

## Specifications

`snippet.json` schema 1 requires id/name/summary, tags/searchTerms, kind (`shared-helper` or `recipe`), source `{path, symbols}`, requiredShared (`["common"]` or `["common","material"]`), examplePath and origin `{shaderIDs, attribution, license}`. Paths are repository-relative. Shared sources must be declared helpers; recipe source and example must be inside their own asset directory. Documents specify Interface, Coordinates, Tuning, Limitations and Cost. Estimates must be labeled; measured results must name device, resolution and configuration.

`reference.json` schema 1 requires id/name/summary/language, tags/searchTerms, origin `{url, author, license}`, requirements, adaptationNotes and files `{original-relative-path: sha256}`. An empty original inventory is allowed for a newly scaffolded reference, but an import must contain files.

Shader metadata may include authoring-only `reuse: {snippets: [ids], references: [ids]}`. These are related assets, not build dependencies. They are validated but never copied into the published manifest.
