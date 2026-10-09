import copy
import json
import pathlib
import shutil
import tempfile
import unittest
from unittest.mock import patch
import catalog


class CatalogValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        shutil.copytree(catalog.ROOT / "shaders", self.root / "shaders")
        shutil.copytree(catalog.ROOT / "shared", self.root / "shared")
        shutil.copytree(catalog.ROOT / "snippets", self.root / "snippets")
        shutil.copytree(catalog.ROOT / "references", self.root / "references")
        (self.root / "tools").mkdir()
        shutil.copyfile(catalog.ROOT / "tools/render-preview.swift", self.root / "tools/render-preview.swift")
        shutil.copyfile(catalog.ROOT / "index.json", self.root / "index.json")
        self.root_patch = patch.object(catalog, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.addCleanup(self.temp.cleanup)

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value))

    def test_duplicate_id_and_missing_default_are_rejected(self):
        index = catalog.read_json(self.root / "index.json")
        index["shaders"].append(index["shaders"][0])
        self.write("index.json", index)
        with self.assertRaises(ValueError):
            catalog.entries()
        index["shaders"].pop()
        index["defaultShaderID"] = "missing"
        self.write("index.json", index)
        with self.assertRaises(ValueError):
            catalog.entries()

    def test_invalid_metadata_and_paths_are_rejected(self):
        original = catalog.read_json(self.root / "shaders/plasma/metadata.json")
        for key, value in [("colors", [[0, 1]]), ("category", "UNKNOWN"), ("id", "other"), ("shared", ["../secret", "fragment"])]:
            metadata = copy.deepcopy(original)
            metadata[key] = value
            self.write("shaders/plasma/metadata.json", metadata)
            with self.assertRaises(ValueError):
                catalog.entries()

    def test_stale_source_and_renderer_fingerprints_block_publication(self):
        for path in ("shaders/plasma/body.metal", "shared/common.metal", "tools/render-preview.swift"):
            original = (self.root / path).read_text()
            (self.root / path).write_text(original + "\n// changed\n")
            with patch.object(catalog, "git", return_value="a" * 40), self.assertRaisesRegex(ValueError, "Stale preview"):
                catalog.build(self.root / "dist")
            (self.root / path).write_text(original)

    def test_corrupt_png_blocks_publication(self):
        (self.root / "shaders/plasma/preview.png").write_bytes(b"broken")
        with patch.object(catalog, "git", return_value="a" * 40), self.assertRaisesRegex(ValueError, "Stale preview"):
            catalog.build(self.root / "dist")

    def test_publication_dates_and_complete_artifact(self):
        def git(*args):
            return "a" * 40 if args[0] == "rev-parse" else "2026-10-09T12:30:00-07:00"
        with patch.object(catalog, "git", side_effect=git):
            output = self.root / "dist"
            manifest = catalog.build(output)
        self.assertEqual(len(manifest["shaders"]), 8)
        self.assertEqual(manifest["collections"][0]["shaderIDs"], ["aurora", "waves", "kaleidoscope", "chrome"])
        self.assertEqual(manifest["shaders"][0]["discovery"]["moods"], ["energetic"])
        self.assertTrue(all("reuse" not in entry for entry in manifest["shaders"]))
        self.assertEqual(set(p.name for p in output.iterdir()), {"catalog.json", "sources", "previews"})
        self.assertEqual(manifest["shaders"][0]["updatedAt"], "2026-10-09T19:30:00Z")
        for entry in manifest["shaders"]:
            self.assertEqual(catalog.digest((output / entry["sourcePath"]).read_bytes()), entry["sourceSHA256"])
            self.assertEqual(catalog.digest((output / entry["previewPath"]).read_bytes()), entry["previewSHA256"])
        self.assertEqual(catalog.read_json(output / "catalog.json"), manifest)

    def test_collections_and_discovery_are_checked(self):
        original = catalog.read_json(self.root / "index.json")
        for mutation in ("reserved", "duplicate", "unpublished", "empty"):
            index = copy.deepcopy(original)
            collection = index["collections"][0]
            if mutation == "reserved": collection["id"] = "all"
            if mutation == "duplicate": collection["shaderIDs"].append(collection["shaderIDs"][0])
            if mutation == "unpublished": collection["shaderIDs"].append("unknown")
            if mutation == "empty": collection["shaderIDs"] = []
            self.write("index.json", index)
            with self.assertRaises(ValueError): catalog.entries()
        self.write("index.json", original)
        metadata = catalog.read_json(self.root / "shaders/plasma/metadata.json")
        metadata["discovery"]["motion"] = "instant"
        self.write("shaders/plasma/metadata.json", metadata)
        with self.assertRaises(ValueError): catalog.entries()

    def test_rebuild_removes_old_assets_and_failure_preserves_snapshot(self):
        output = self.root / "dist"
        with patch.object(catalog, "git", side_effect=lambda *a: "a" * 40 if a[0] == "rev-parse" else "2026-10-09T12:30:00Z"):
            catalog.build(output)
            (output / "sources/obsolete.metal").write_text("old")
            (output / ".DS_Store").write_bytes(b"incidental")
            catalog.build(output)
            self.assertFalse((output / "sources/obsolete.metal").exists())
            self.assertEqual(set(p.name for p in output.iterdir()), {"catalog.json", "sources", "previews"})
            previous = (output / "catalog.json").read_bytes()
            (self.root / "shaders/plasma/body.metal").write_text("changed")
            with self.assertRaisesRegex(ValueError, "Stale preview"): catalog.build(output)
            self.assertEqual((output / "catalog.json").read_bytes(), previous)


if __name__ == "__main__":
    unittest.main()
