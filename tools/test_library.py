import contextlib
from collections import Counter
import io
import json
import os
import pathlib
import shutil
import tempfile
import unittest
from unittest.mock import patch
import authoring
import library
from authoring_test_support import fixture_root

class LibraryTests(unittest.TestCase):
    def setUp(self):
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        self.root = stack.enter_context(fixture_root("shaders", "shared", "snippets", "references", "templates", "docs"))
        self.asset_count = len(library.assets())

    def test_library_and_search_output(self):
        self.assertEqual(len(library.validate()), self.asset_count)
        matches = library.search("FLOWING ribbons", "snippet")
        self.assertEqual([v["id"] for v in matches], ["glowing-ribbons"])
        self.assertEqual(library.search("hdPolarFold")[0]["id"], "polar-fold")
        self.assertEqual(library.search("value noise")[0]["id"], "value-noise")
        text, machine = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(text): library.emit(matches)
        with contextlib.redirect_stdout(machine): library.emit(matches, True)
        self.assertEqual([v.split("\t")[1] for v in text.getvalue().splitlines()], [v["id"] for v in json.loads(machine.getvalue())])
        detail = library.show("snippet", "fbm")
        self.assertIn("Interface", detail["documentation"])
        self.assertIn("float3 shade", detail["example"])
        self.assertEqual(detail["sourceLocations"], ["shared/common.metal"])
        with contextlib.redirect_stdout(text): library.emit(detail)
        self.assertIn(detail["example"], text.getvalue())

    def test_primary_search_matches_precede_descriptive_matches(self):
        primary_path = self.root / "snippets/value-noise/snippet.json"
        primary = authoring.read_json(primary_path)
        primary.update(name="Quasar", summary="Ellipse spiral", tags=[], searchTerms=[])
        authoring.write_json(primary_path, primary)
        tags_path = self.root / "snippets/fbm/snippet.json"
        tagged = authoring.read_json(tags_path)
        tagged.update(tags=["quasar", "ellipse", "spiral"], searchTerms=[])
        authoring.write_json(tags_path, tagged)
        self.assertEqual([v["id"] for v in library.search("quasar ellipse spiral")], ["value-noise", "fbm"])

    def test_scaffold_is_unlisted_and_refuses_overwrite(self):
        original = (self.root / "index.json").read_bytes()
        library.scaffold("shader", "new-scene")
        self.assertEqual((self.root / "index.json").read_bytes(), original)
        self.assertEqual(len(library.validate()), self.asset_count + 1)
        self.assertNotIn("new-scene", [v[0]["id"] for v in authoring.entries()[1]])
        with self.assertRaises(ValueError): library.scaffold("shader", "new-scene")
        with self.assertRaises(ValueError): library.scaffold("shader", "../escape")

    def test_reference_scaffold_and_display_use_metadata_without_readme(self):
        destination = library.scaffold("reference", "documented-reference")
        self.assertFalse((destination / "README.md").exists())
        metadata = destination / "reference.json"
        spec = authoring.read_json(metadata)
        self.assertNotIn("notes", spec)
        library.validate()
        detail = library.show("reference", "documented-reference")
        self.assertEqual(detail["specification"], spec)
        self.assertEqual(detail["sourceLocations"], [])
        self.assertIsNone(detail["example"])
        self.assertIn(spec["summary"], detail["documentation"])
        self.assertIn(spec["adaptationNotes"], detail["documentation"])

        spec["requirements"] = ["A source texture"]
        spec["origin"]["url"] = "https://example.invalid/reference"
        spec["notes"] = "A unique résumé note.\n\n| Technique | Detail |\n| --- | --- |\n| Warp | " + "x" * 2100 + " |\n"
        authoring.write_json(metadata, spec)
        # A leftover document cannot override metadata, which is now authoritative.
        (destination / "README.md").write_text("stale external documentation")
        library.validate()
        detail = library.show("reference", "documented-reference")
        for text in (spec["notes"], spec["requirements"][0], spec["origin"]["url"]):
            self.assertIn(text, detail["documentation"])
        self.assertNotIn("stale external documentation", detail["documentation"])
        self.assertEqual(library.search("unique résumé note", "reference"), [])
        text, machine = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(text): library.emit(detail)
        with contextlib.redirect_stdout(machine): library.emit(detail, True)
        self.assertEqual(text.getvalue().count("A unique résumé note."), 1)
        self.assertNotIn('"schemaVersion"', text.getvalue())
        self.assertEqual(json.loads(machine.getvalue()), detail)

    def test_reference_notes_must_be_nonempty_markdown_strings(self):
        destination = library.scaffold("reference", "invalid-notes")
        metadata = destination / "reference.json"
        spec = authoring.read_json(metadata)
        for notes in (None, 42, True, [], {}, "", " \n\t"):
            with self.subTest(notes=notes):
                spec["notes"] = notes
                authoring.write_json(metadata, spec)
                with self.assertRaisesRegex(ValueError, "Invalid reference notes: invalid-notes"):
                    library.validate()
        del spec["notes"]
        authoring.write_json(metadata, spec)
        library.validate()

    def test_reference_display_includes_original_inventory(self):
        item = library.find("reference", "inferno")
        self.assertFalse((self.root / item["path"] / "README.md").exists())
        detail = library.show("reference", "inferno")
        for filename, checksum in item["specification"]["files"].items():
            self.assertIn(filename, detail["documentation"])
            self.assertIn(checksum, detail["documentation"])
            self.assertIn(item["path"] + "/original/" + filename, detail["sourceLocations"])

    def test_validation_reuses_shader_inputs(self):
        library.scaffold("shader", "unlisted-scene")
        shader_ids = {item["id"] for item in library.assets("shader")}
        shader_reads = Counter()
        read_json = authoring.read_json

        def count_read(path):
            if path.name == "metadata.json" and path.parent.parent == self.root / "shaders":
                shader_reads[path.parent.name] += 1
            return read_json(path)

        with patch.object(authoring, "shader_entry", wraps=authoring.shader_entry) as entry, \
             patch.object(authoring, "read_json", side_effect=count_read):
            items = library.validate()
        self.assertEqual(len(items), self.asset_count + 1)
        self.assertEqual(Counter(call.args[0] for call in entry.call_args_list), Counter({shader_id: 1 for shader_id in shader_ids}))
        self.assertEqual(shader_reads, Counter({shader_id: 1 for shader_id in shader_ids}))
        for call in entry.call_args_list:
            shader_id = call.args[0]
            self.assertEqual(authoring.shader_entry(shader_id, **call.kwargs)[1], authoring.shader_entry(shader_id)[1])

    def test_validation_observes_later_changes_and_checks_unpublished_shaders(self):
        library.scaffold("shader", "unlisted-scene")
        library.validate()
        metadata_path = self.root / "shaders/unlisted-scene/metadata.json"
        metadata = authoring.read_json(metadata_path)
        original_category = metadata["category"]
        metadata["category"] = "UNKNOWN"
        authoring.write_json(metadata_path, metadata)
        with self.assertRaises(ValueError):
            library.validate()
        metadata["category"] = original_category
        authoring.write_json(metadata_path, metadata)
        (metadata_path.parent / "body.metal").unlink()
        with self.assertRaises(FileNotFoundError):
            library.validate()

    def test_reference_legacy_imported_from_is_ignored_without_rewriting(self):
        destination = library.scaffold("reference", "public-reference")
        metadata = destination / "reference.json"
        spec = authoring.read_json(metadata)
        spec["origin"]["url"] = "https://example.invalid/shader"
        authoring.write_json(metadata, spec)
        library.validate()
        for value in ("public-reference", "/Users/private/input.frag", "relative/input.frag",
                      "/Users/José/雪/input.frag", "wrong-label", None, 42,
                      {"source": "private/input.frag"}, ["private/input.frag"]):
            with self.subTest(value=value):
                spec["origin"]["importedFrom"] = value
                authoring.write_json(metadata, spec)
                before = metadata.read_bytes()
                library.validate()
                self.assertEqual(metadata.read_bytes(), before)
        self.assertEqual(authoring.read_json(metadata)["origin"]["url"], "https://example.invalid/shader")

    def test_broken_specs_links_and_paths(self):
        file = self.root / "snippets/polar-fold/snippet.json"
        original = authoring.read_json(file)
        for value in ("../escape", "shared/common.metal", "snippets/missing/code.metal"):
            spec = dict(original, source={"path": value, "symbols": ["hdPolarFold"]})
            authoring.write_json(file, spec)
            with self.assertRaises(ValueError): library.validate()
        authoring.write_json(file, original)
        (self.root / "snippets/polar-fold/example.metal").unlink()
        with self.assertRaises(ValueError): library.validate()

    def test_reference_internal_directory_and_broken_symlinks_are_rejected(self):
        for case in ("file", "directory", "broken", "root", "broken-root"):
            with self.subTest(case=case):
                reference_id = "linked-" + case
                destination = library.scaffold("reference", reference_id)
                original = destination / "original"
                if case in ("root", "broken-root"):
                    target = self.root / ("shared" if case == "root" else "missing")
                    original.symlink_to(target, target_is_directory=True)
                    relative = "original"
                else:
                    original.mkdir()
                    nested = original / "nested"
                    nested.mkdir()
                    target = {"file": self.root / "shared/common.metal",
                              "directory": self.root / "shared", "broken": self.root / "missing"}[case]
                    (nested / "link").symlink_to(target, target_is_directory=case == "directory")
                    relative = "original/nested/link"
                with self.assertRaisesRegex(ValueError, reference_id + "/" + relative):
                    library.validate()
                # Remove each rejected asset so the next case reaches its own link.
                if original.is_symlink():
                    original.unlink()
                shutil.rmtree(destination)

    def test_reference_alias_to_an_original_file_is_rejected(self):
        destination = library.scaffold("reference", "aliased")
        original = destination / "original"
        original.mkdir()
        (original / "real.frag").write_bytes(b"original bytes")
        (original / "alias.frag").symlink_to("real.frag")
        spec = authoring.read_json(destination / "reference.json")
        spec["files"] = {name: authoring.digest(b"original bytes") for name in ("real.frag", "alias.frag")}
        authoring.write_json(destination / "reference.json", spec)
        with self.assertRaisesRegex(ValueError, "aliased/original/alias.frag"):
            library.validate()

    def test_snippet_sources_preserve_component_bytes_and_harness_separators(self):
        for snippet_id in ("value-noise", "glowing-ribbons"):
            with self.subTest(snippet_id=snippet_id):
                item = library.find("snippet", snippet_id)
                spec = item["specification"]
                components = [self.root / "shared" / f"{part}.metal" for part in spec["requiredShared"]]
                if spec["kind"] == "recipe":
                    components.append(self.root / spec["source"]["path"])
                components.extend([self.root / spec["examplePath"], self.root / "shared/fragment.metal"])
                expected = []
                for path in components:
                    data = b"// caf\xc3\xa9\r\n" + path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
                    path.write_bytes(data)
                    expected.append(data)
                self.assertEqual(library.snippet_source(item).encode("utf-8"), b"\n".join(expected))

    def test_compile_and_render_inputs_preserve_assembled_source_bytes(self):
        components = [self.root / "shared/common.metal", self.root / "shaders/plasma/body.metal",
                      self.root / "shared/fragment.metal"]
        expected = b""
        for path in components:
            data = b"// caf\xc3\xa9\r\n" + path.read_bytes().replace(b"\n", b"\r\n")
            path.write_bytes(data)
            expected += data
        observed = []

        def inspect_source(args, check):
            source_path = pathlib.Path(args[5] if args[0] == "xcrun" else args[2])
            observed.append(source_path.read_bytes())

        with patch.object(library.subprocess, "run", side_effect=inspect_source), \
             patch.object(library.shader_tool, "command", return_value=["renderer", "render"]), \
             contextlib.redirect_stdout(io.StringIO()):
            library.compile_source(authoring.shader_entry("plasma")[1], "plasma")
            library.render("shader", "plasma", "0,3,10")
        self.assertEqual(observed, [expected] * 5)

    def test_missing_specification_and_duplicate_id_are_rejected(self):
        directory = self.root / "snippets/copy"
        shutil.copytree(self.root / "snippets/fbm", directory)
        with self.assertRaisesRegex(ValueError, "ID"): library.validate()
        shutil.rmtree(directory)
        (self.root / "snippets/fbm/snippet.json").unlink()
        with self.assertRaisesRegex(ValueError, "asset"): library.assets("snippet")

    def test_reference_external_symlinks_rejected(self):
        destination = library.scaffold("reference", "linked")
        original = destination / "original"
        original.mkdir()
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp) / "input.frag"
            source.write_bytes(b"original bytes")
            (original / "input.frag").symlink_to(source)
            spec = authoring.read_json(destination / "reference.json")
            spec["files"] = {"input.frag": authoring.digest(source.read_bytes())}
            authoring.write_json(destination / "reference.json", spec)
            with self.assertRaisesRegex(ValueError, "linked/original/input.frag"): library.validate()

    def test_manual_reference_inventory_and_checksums(self):
        destination = library.scaffold("reference", "manual")
        original = destination / "original"
        original.mkdir()
        source = original / "input.frag"
        source.write_bytes(b"original bytes")
        spec = authoring.read_json(destination / "reference.json")
        spec["files"] = {"input.frag": authoring.digest(source.read_bytes())}
        authoring.write_json(destination / "reference.json", spec)
        library.validate()
        source.write_bytes(b"changed bytes")
        with self.assertRaisesRegex(ValueError, "checksum"): library.validate()
        source.unlink()
        with self.assertRaisesRegex(ValueError, "inventory"): library.validate()

    @unittest.skipUnless(os.environ.get("HOLODECK_GPU_TESTS") == "1", "Opt in to Metal compilation and rendering")
    def test_combined_unlisted_recipe_compiles_and_renders(self):
        destination = library.scaffold("shader", "combined-recipe")
        code = (self.root / "snippets/glowing-ribbons/code.metal").read_text()
        code += "\nfloat3 shade(float2 p, float t, float2 pixel) { float center = (noise2(float2(p.x * 3, t * 0.2)) - 0.5) * 0.4; return palette(p.x + t * 0.05) * hdGlowingRibbon(p.y, center, 0.02); }\n"
        (destination / "body.metal").write_text(code)
        library.compile_source(authoring.shader_entry("combined-recipe")[1], "combined-recipe")
        output = library.render("shader", "combined-recipe", "0,3,10", 320, 180)
        images = sorted(output.glob("*.png"))
        self.assertEqual(len(images), 3)
        self.assertTrue(all(p.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") for p in images))
        self.assertEqual(len({p.read_bytes() for p in images}), 3)
        self.assertNotIn("combined-recipe", authoring.entries()[0]["shaders"])
