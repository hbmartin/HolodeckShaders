import copy
import json
import pathlib
import shutil
import tempfile
import unittest
from unittest.mock import patch
import authoring


class AuthoringValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        shutil.copytree(authoring.ROOT / "shaders", self.root / "shaders")
        shutil.copytree(authoring.ROOT / "shared", self.root / "shared")
        shutil.copytree(authoring.ROOT / "snippets", self.root / "snippets")
        shutil.copytree(authoring.ROOT / "references", self.root / "references")
        shutil.copyfile(authoring.ROOT / "index.json", self.root / "index.json")
        self.root_patch = patch.object(authoring, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.addCleanup(self.temp.cleanup)

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value))

    def test_duplicate_id_and_missing_default_are_rejected(self):
        index = authoring.read_json(self.root / "index.json")
        index["shaders"].append(index["shaders"][0])
        self.write("index.json", index)
        with self.assertRaises(ValueError):
            authoring.entries()
        index["shaders"].pop()
        index["defaultShaderID"] = "missing"
        self.write("index.json", index)
        with self.assertRaises(ValueError):
            authoring.entries()

    def test_invalid_metadata_and_paths_are_rejected(self):
        original = authoring.read_json(self.root / "shaders/plasma/metadata.json")
        for key, value in [("colors", [[0, 1]]), ("category", "UNKNOWN"), ("id", "other"), ("shared", ["../secret", "fragment"])]:
            metadata = copy.deepcopy(original)
            metadata[key] = value
            self.write("shaders/plasma/metadata.json", metadata)
            with self.assertRaises(ValueError):
                authoring.entries()

    def test_collections_and_discovery_are_checked(self):
        original = authoring.read_json(self.root / "index.json")
        for mutation in ("reserved", "duplicate", "unpublished", "empty"):
            index = copy.deepcopy(original)
            collection = index["collections"][0]
            if mutation == "reserved": collection["id"] = "all"
            if mutation == "duplicate": collection["shaderIDs"].append(collection["shaderIDs"][0])
            if mutation == "unpublished": collection["shaderIDs"].append("unknown")
            if mutation == "empty": collection["shaderIDs"] = []
            self.write("index.json", index)
            with self.assertRaises(ValueError): authoring.entries()
        self.write("index.json", original)
        metadata = authoring.read_json(self.root / "shaders/plasma/metadata.json")
        metadata["discovery"]["motion"] = "instant"
        self.write("shaders/plasma/metadata.json", metadata)
        with self.assertRaises(ValueError): authoring.entries()


if __name__ == "__main__":
    unittest.main()
