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
| dot-curtain | Polka-dot and diamond halftone sweeps |
| sine-warp | Seamless sinusoidal domain warp |
| color-ramps | Heat ramp and HSL/HSV conversion |
| rain-ripples | Expanding raindrop rings |
| crt-overlay | Shadow mask, scanlines and grain over scene colour |

Shared-helper snippets link to the existing implementation. Recipe snippets have copyable `code.metal` functions. Every snippet includes a machine-readable specification, a contract and a working example. The example harness concatenates declared existing helpers, recipe code if applicable, the example body and the standard fragment wrapper. It is a validation harness, not a production dependency assembler.

## References and provenance

Add references manually:

1. Run `python3 tools/library.py new reference my-source`.
2. Fill in language, source URL, author, license, requirements, and adaptation notes. Optional `notes` contains longer Markdown guidance, credits, and tables; `show reference <id>` renders these fields directly. Per-reference `README.md` files are rejected: migrate their guidance into `notes`. The root `references/README.md` and inventoried upstream READMEs inside `original/` remain valid. Keep unknown provenance explicitly unknown. Do not record local input paths.
3. For a permissively licensed original, copy the selected files unchanged into `references/my-source/original/`. Keep required upstream license files. Do not copy repository metadata or editor/cache files. Symlinks are forbidden at the reference asset directory and throughout its contents, including metadata, notices and originals; broken links are also rejected. Other licenses and unlicensed inspiration use metadata only with an empty inventory.
4. Record each original-relative filename and its SHA-256 in `reference.json`'s `files` object. On Mac, `shasum -a 256 <file>` prints the checksum.
5. Run library validation, then stage reference metadata and originals together with `git add references/my-source`. Inspect `git diff --cached --name-status -- references/my-source` and confirm every inventoried original is staged or already tracked with the expected bytes. If an intended original is missing, use `git check-ignore -v -- references/my-source/original/filename` to check ignore rules; remove environment artifacts rather than adding them. Validation rejects symlinks, missing/extra original files and changed bytes on disk; it does not inspect the Git index or ignore rules, import files, or stage anything. PR CI validates a fresh checkout and can catch omitted originals before merge.

Originals remain unchanged; adapt into a separate shader or snippet. Legacy `origin.importedFrom` values remain ignored without rewriting metadata. Validation requires no Git checkout.

The eight original canonical shaders under `shaders/` have no separate originals in `references/`. Later scenes adapted from external work link their provenance through `metadata.reuse.references`.

## Licensing

Check `origin.license` before copying a snippet and the reference before adapting an original. Adapted catalog bodies start with an attribution comment (title, author, URL, license, changes) because published sources travel to the app. Share-alike terms propagate: code derived from a CC BY-NC-SA snippet or reference keeps that license, so prefer permissive snippets when a choice exists. Sources without a license are clean-room inspiration only: record them as metadata-only references and never copy their code. `references/` preserves original files only for permissive licenses (MIT, CC0, CC BY, Unlicense); non-commercial, share-alike or unlicensed sources keep URL, author, license and notes with an empty file inventory.

Keep required license notices inside every copyable recipe and adapted shader body. MIT-derived code includes the complete upstream copyright, permission and warranty notice; a license name or repository URL alone is insufficient. CC BY and CC BY-NC-SA adaptations retain their credits and change descriptions and include the applicable canonical license URI (for example, `https://creativecommons.org/licenses/by/3.0/` or `https://creativecommons.org/licenses/by-nc-sa/3.0/`). Preserve relevant notices for each source when combining adaptations. Reference originals, recipe metadata and documentation are authoring-only, so notices there do not accompany a published Metal source. Copy the notices along with the recipe functions when adapting them.

The test-only notice inventory in `tools/test_licenses.py` records every shader body, recipe, example and declared shared component, with explicit empty records for original sources and multiple upstream IDs for combined adaptations. Register new sources and MIT/CC references there, and run `python3 -m unittest discover -s tools -p 'test_*.py'`. Tests compare independent source notices and inherited assembly notices and cross-check declared MIT/CC metadata; they do not infer undeclared provenance from code or treat `reuse` links as dependencies. Normal library validation does not enforce this inventory. Keep file-level notices above function-specific documentation so the documentation remains next to its function.

## Specifications

`snippet.json` schema 1 requires id/name/summary, tags/searchTerms, kind (`shared-helper` or `recipe`), source `{path, symbols}`, requiredShared (`["common"]` or `["common","material"]`), examplePath and origin `{shaderIDs, attribution, license}`. Paths are repository-relative. Shared sources must be declared helpers; recipe source and example must be inside their own asset directory. Documents specify Interface, Coordinates, Tuning, Limitations and Cost. Estimates must be labeled; measured results must name device, resolution and configuration.

`reference.json` schema 1 requires id/name/summary/language, tags/searchTerms, origin `{url, author, license}`, requirements, adaptationNotes and files `{original-relative-path: sha256}`. Optional `notes` is a nonempty Markdown string for longer prose with no length cap; it does not change search ranking. `show` checks metadata shape and generates reference documentation; `--json` retains the complete specification and generated documentation. Missing or changed originals do not prevent inspection with `show`; full validation checks their inventory and bytes. An empty original inventory is allowed for a newly scaffolded or metadata-only reference.

Shader metadata may include authoring-only `reuse: {snippets: [ids], references: [ids]}`. These are related assets, not build dependencies. They are validated but never copied into the published manifest.
