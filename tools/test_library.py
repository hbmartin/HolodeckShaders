import contextlib
import io
import json
import os
import pathlib
import shutil
import tempfile
import unittest
from unittest.mock import patch
import catalog
import library


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        for folder in ("shaders", "shared", "snippets", "references", "templates", "docs", "tools"):
            shutil.copytree(catalog.ROOT / folder, self.root / folder, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copyfile(catalog.ROOT / "index.json", self.root / "index.json")
        self.root_patch = patch.object(catalog, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.addCleanup(self.temp.cleanup)

    def test_library_and_search_output(self):
        self.assertEqual(len(library.validate()), 16)
        matches = library.search("FLOWING ribbons", "snippet")
        self.assertEqual([v["id"] for v in matches], ["glowing-ribbons"])
        self.assertEqual(library.search("hdPolarFold")[0]["id"], "polar-fold")
        self.assertEqual(library.search("noise")[0]["id"], "value-noise")
        text, machine = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(text): library.emit(matches)
        with contextlib.redirect_stdout(machine): library.emit(matches, True)
        self.assertEqual([v.split("\t")[1] for v in text.getvalue().splitlines()], [v["id"] for v in json.loads(machine.getvalue())])
        self.assertIn("Interface", library.show("snippet", "fbm")["documentation"])

    def test_primary_search_matches_precede_descriptive_matches(self):
        primary_path = self.root / "snippets/value-noise/snippet.json"
        primary = catalog.read_json(primary_path)
        primary.update(name="Quasar", summary="Ellipse spiral", tags=[], searchTerms=[])
        catalog.write_json(primary_path, primary)
        tags_path = self.root / "snippets/fbm/snippet.json"
        tagged = catalog.read_json(tags_path)
        tagged.update(tags=["quasar", "ellipse", "spiral"], searchTerms=[])
        catalog.write_json(tags_path, tagged)
        self.assertEqual([v["id"] for v in library.search("quasar ellipse spiral")], ["value-noise", "fbm"])

    def test_scaffold_is_unlisted_and_refuses_overwrite(self):
        original = (self.root / "index.json").read_bytes()
        library.scaffold("shader", "new-scene")
        self.assertEqual((self.root / "index.json").read_bytes(), original)
        self.assertEqual(len(library.validate()), 17)
        self.assertNotIn("new-scene", [v[0]["id"] for v in catalog.entries()[1]])
        with self.assertRaises(ValueError): library.scaffold("shader", "new-scene")
        with self.assertRaises(ValueError): library.scaffold("shader", "../escape")

    def test_import_bytes_checksums_and_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp)
            (source / "nested").mkdir()
            original = b"\x00\xff\noriginal shader bytes"
            (source / "nested/input.frag").write_bytes(original)
            destination = library.import_reference("test-source", source, "GLSL")
            self.assertEqual((destination / "original/nested/input.frag").read_bytes(), original)
            spec = catalog.read_json(destination / "reference.json")
            self.assertEqual(spec["origin"]["importedFrom"], str(source))
            self.assertTrue(spec["origin"]["importedAt"].endswith("Z"))
            library.validate()
            with self.assertRaises(ValueError): library.import_reference("test-source", source, "GLSL")
            (destination / "original/nested/input.frag").write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError, "checksum"): library.validate()

    def test_broken_specs_links_and_paths(self):
        file = self.root / "snippets/polar-fold/snippet.json"
        original = catalog.read_json(file)
        for value in ("../escape", "shared/common.metal", "snippets/missing/code.metal"):
            spec = dict(original, source={"path": value, "symbols": ["hdPolarFold"]})
            catalog.write_json(file, spec)
            with self.assertRaises(ValueError): library.validate()
        catalog.write_json(file, original)
        (self.root / "snippets/polar-fold/example.metal").unlink()
        with self.assertRaises(ValueError): library.validate()

    def test_missing_specification_and_duplicate_id_are_rejected(self):
        directory = self.root / "snippets/copy"
        shutil.copytree(self.root / "snippets/fbm", directory)
        with self.assertRaisesRegex(ValueError, "ID"): library.validate()
        shutil.rmtree(directory)
        (self.root / "snippets/fbm/snippet.json").unlink()
        with self.assertRaisesRegex(ValueError, "asset"): library.assets("snippet")

    def test_reference_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp) / "input.frag"
            source.symlink_to(self.root / "shared/common.metal")
            with self.assertRaises(ValueError): library.import_reference("linked", source, "Metal")

    @unittest.skipUnless(os.environ.get("HOLODECK_GPU_TESTS") == "1", "Opt in to Metal compilation and rendering")
    def test_combined_unlisted_recipe_compiles_and_renders(self):
        destination = library.scaffold("shader", "combined-recipe")
        code = (self.root / "snippets/glowing-ribbons/code.metal").read_text()
        code += "\nfloat3 shade(float2 p, float t, float2 pixel) { float center = (noise2(float2(p.x * 3, t * 0.2)) - 0.5) * 0.4; return palette(p.x + t * 0.05) * hdGlowingRibbon(p.y, center, 0.02); }\n"
        (destination / "body.metal").write_text(code)
        library.compile_source(catalog.shader_entry("combined-recipe")[1], "combined-recipe")
        output = library.render("shader", "combined-recipe", "0,3,10", 320, 180)
        images = sorted(output.glob("*.png"))
        self.assertEqual(len(images), 3)
        self.assertTrue(all(p.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") for p in images))
        self.assertEqual(len({p.read_bytes() for p in images}), 3)
        self.assertNotIn("combined-recipe", catalog.entries()[0]["shaders"])
