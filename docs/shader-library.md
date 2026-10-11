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
| simplex-noise-3d | Smooth 3D noise for animated surfaces and volumes |
| gradient-noise | 2D gradient (Perlin-style) noise |
| voronoi | Cell distances for cells, edges and caustics |
| hex-grid | Hexagonal tiling, cell edges and twinkling cells |
| grid-lines | Antialiased grid masks for surfaces |
| box-room | Ray–room intersection and bounce paths |
| sphere-shell | Ray–sphere hits, fresnel and halo glow |
| hologram-rim | Blue translucent body with amber fresnel rim |
| impact-ripple | Scheduled impact rings on a sphere |
| noise-dissolve | Noise-threshold dissolve with glowing edge |
| kali-starfield | Volumetric Kali-fractal star cloud (CC BY-NC-SA) |
| ember-sparks | Rising spark particles (CC BY) |
| rune-glyph | Procedural glyphs for digital rain (CC BY-NC-SA) |
| god-rays | Swaying light shafts |
| sinebow-lines | Neon inverse-distance glow lines |
| dot-curtain | Polka-dot and diamond halftone sweeps |
| sine-warp | Seamless sinusoidal domain warp |
| color-ramps | Heat ramp and HSL/HSV conversion |
| rain-ripples | Expanding raindrop rings |
| crt-overlay | Shadow mask, scanlines and grain over scene colour |

Shared-helper snippets link to the existing implementation. Recipe snippets have copyable `code.metal` functions. Every snippet includes a machine-readable specification, a contract and a working example. The example harness concatenates declared existing helpers, recipe code if applicable, the example body and the standard fragment wrapper. It is a validation harness, not a production dependency assembler.

## References and provenance

Use `python3 tools/library.py import-reference my-source --source ./source --language GLSL` to preserve a local file or directory. Relative and absolute source paths work. Imports require Git and a working checkout, reject symlinks and overwrites, and preserve accepted file names and bytes. They record UTC import time and every original file's SHA-256, and never convert source or add it to the app. A reference becomes visible only after its staged files and metadata pass validation.

Imports reject selected source entries named `.git`, `.DS_Store`, `__pycache__`, `.idea`, `.vscode` or `xcuserdata`, including entries nested inside directories. Other hidden files and `.gitignore` files are allowed. Imports also reject files ordinary Git staging would omit at the intended destination, using repository ignore rules, imported nested `.gitignore` files, and local/global excludes. Rejections list repository-relative paths and reasons; prepare a clean source or adjust ignore rules, then retry. Files are never silently excluded. Copied directory permissions are made writable for staging and cleanup; source permissions and copied file executable bits are preserved. If cleanup fails, the original import error is retained and the remaining hidden staging location is reported separately.

Successful imports do not record the local source location in generated provenance metadata or a separate local record. New imports omit `origin.importedFrom`, including when it is present in the reference template. File names, original contents and error diagnostics may contain identifying information; imports do not anonymize them. Fill in the original URL, author, license, requirements and adaptation notes. Unknown provenance stays explicitly unknown. `validate` checks the inventory and bytes against recorded checksums. Legacy `origin.importedFrom` values are ignored without checking or rewriting them; authors can delete the field manually. Validation does not rewrite metadata or Git history. Keep originals unchanged and adapt into a separate finished shader or snippet.

The eight original canonical shaders under `shaders/` have no separate originals in `references/`. Later scenes adapted from external work link their provenance through `metadata.reuse.references`.

## Licensing

Check `origin.license` before copying a snippet and the reference before adapting an original. Adapted catalog bodies start with an attribution comment (title, author, URL, license, changes) because published sources travel to the app. Share-alike terms propagate: code derived from a CC BY-NC-SA snippet or reference keeps that license, so prefer permissive snippets when a choice exists. Sources without a license are clean-room inspiration only: record them as metadata-only references and never copy their code. `references/` preserves original files only for permissive licenses (MIT, CC0, CC BY, Unlicense); non-commercial, share-alike or unlicensed sources keep URL, author, license and notes with an empty file inventory.

Keep required license notices inside every copyable recipe and adapted shader body. MIT-derived code includes the complete upstream copyright, permission and warranty notice; a license name or repository URL alone is insufficient. CC BY and CC BY-NC-SA adaptations retain their credits and change descriptions and include the applicable canonical license URI (for example, `https://creativecommons.org/licenses/by/3.0/` or `https://creativecommons.org/licenses/by-nc-sa/3.0/`). Preserve relevant notices for each source when combining adaptations. Reference originals, recipe metadata and documentation are authoring-only, so notices there do not accompany a published Metal source. Copy the notices along with the recipe functions when adapting them.

The test-only notice inventory in `tools/test_licenses.py` records every shader body, recipe, example and declared shared component, with explicit empty records for original sources and multiple upstream IDs for combined adaptations. Register new sources and MIT/CC references there, and run `python3 -m unittest discover -s tools -p 'test_*.py'`. Tests compare independent source notices and inherited assembly notices and cross-check declared MIT/CC metadata; they do not infer undeclared provenance from code or treat `reuse` links as dependencies. Normal library and publication validation do not enforce this inventory. Keep file-level notices above function-specific documentation so the documentation remains next to its function.

## Specifications

`snippet.json` schema 1 requires id/name/summary, tags/searchTerms, kind (`shared-helper` or `recipe`), source `{path, symbols}`, requiredShared (`["common"]` or `["common","material"]`), examplePath and origin `{shaderIDs, attribution, license}`. Paths are repository-relative. Shared sources must be declared helpers; recipe source and example must be inside their own asset directory. Documents specify Interface, Coordinates, Tuning, Limitations and Cost. Estimates must be labeled; measured results must name device, resolution and configuration.

`reference.json` schema 1 requires id/name/summary/language, tags/searchTerms, origin `{url, author, license}`, requirements, adaptationNotes and files `{original-relative-path: sha256}`. An empty original inventory is allowed for a newly scaffolded reference, but an import must contain files.

Shader metadata may include authoring-only `reuse: {snippets: [ids], references: [ids]}`. These are related assets, not build dependencies. They are validated but never copied into the published manifest.
