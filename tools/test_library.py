import contextlib
import io
import json
import os
import pathlib
import shutil
import stat
import subprocess
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
        shutil.copyfile(catalog.ROOT / ".gitignore", self.root / ".gitignore")
        self.git_environment = patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_COUNT": "0"})
        self.git_environment.start()
        self.addCleanup(self.git_environment.stop)
        self.git("init", "--quiet")
        self.git("config", "core.excludesFile", os.devnull)
        self.root_patch = patch.object(catalog, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.addCleanup(self.temp.cleanup)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.PIPE, text=True)

    def assert_import_absent(self, asset_id):
        destination = self.root / "references" / asset_id
        self.assertFalse(destination.exists() or destination.is_symlink())
        self.assertEqual(list((self.root / "references").glob(".import-*")), [])

    def metadata_strings(self, value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for key, item in value.items():
                yield key
                yield from self.metadata_strings(item)
        elif isinstance(value, list):
            for item in value:
                yield from self.metadata_strings(item)

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
        detail = library.show("snippet", "fbm")
        self.assertIn("Interface", detail["documentation"])
        self.assertIn("float3 shade", detail["example"])
        self.assertEqual(detail["sourceLocations"], ["shared/common.metal"])
        with contextlib.redirect_stdout(text): library.emit(detail)
        self.assertIn(detail["example"], text.getvalue())

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
            self.assertEqual(spec["origin"]["importedFrom"], "test-source")
            self.assertTrue(spec["origin"]["importedAt"].endswith("Z"))
            library.validate()
            with self.assertRaises(ValueError): library.import_reference("test-source", source, "GLSL")
            (destination / "original/nested/input.frag").write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError, "checksum"): library.validate()

    def test_import_metadata_uses_public_label_without_private_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            private = pathlib.Path(temp) / "private-contributor-José/private-project-雪"
            directory = private / "private-reference-directory-é"
            (directory / "nested").mkdir(parents=True)
            original = b"\x00\xff\noriginal shader bytes"
            file = private / "input.frag"
            file.write_bytes(original)
            (directory / "nested/input.frag").write_bytes(original)
            for kind, source, filename in (("file", file, "input.frag"), ("directory", directory, "nested/input.frag")):
                for form in ("absolute", "relative"):
                    with self.subTest(kind=kind, form=form):
                        asset_id = f"test-{kind}-{form}"
                        argument = source if form == "absolute" else os.path.relpath(source)
                        destination = library.import_reference(asset_id, argument, "GLSL")
                        metadata = (destination / "reference.json").read_text()
                        spec = json.loads(metadata)
                        self.assertEqual(spec["origin"]["importedFrom"], asset_id)
                        for value in self.metadata_strings(spec):
                            self.assertNotIn(str(source), value)
                            self.assertNotIn(str(source.parent), value)
                            for marker in (private.parent.name, private.name, directory.name):
                                self.assertNotIn(marker, value)
                        self.assertEqual((destination / "original" / filename).read_bytes(), original)
                        self.assertEqual(spec["files"], {filename: catalog.digest(original)})
            library.validate()

    def test_import_rejects_environment_artifacts(self):
        for name in (".git", ".DS_Store", "__pycache__", ".idea", ".vscode", "xcuserdata"):
            for nested in (False, True):
                with self.subTest(name=name, nested=nested), tempfile.TemporaryDirectory() as temp:
                    source = pathlib.Path(temp) / "source"
                    source.mkdir()
                    (source / "input.frag").write_bytes(b"shader")
                    artifact = source / "nested" / name if nested else source / name
                    artifact.parent.mkdir(parents=True, exist_ok=True)
                    if name == ".DS_Store":
                        artifact.write_bytes(b"private")
                    else:
                        artifact.mkdir()
                    with self.assertRaisesRegex(ValueError, "environment artifacts") as raised:
                        library.import_reference("rejected", source, "GLSL")
                    self.assertIn(name, str(raised.exception))
                    self.assertIn("references/rejected/original/", str(raised.exception))
                    self.assertNotIn(str(source), str(raised.exception))
                    self.assert_import_absent("rejected")
                    with self.assertRaisesRegex(ValueError, "environment artifacts"):
                        library.import_reference("selected-artifact", artifact, "GLSL")
                    self.assert_import_absent("selected-artifact")

    def test_import_hidden_files_survive_tracked_file_checkout(self):
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp)
            originals = {".config": b"configuration", ".gitignore": b"*.tmp\n",
                         "nested/.hidden.frag": b"\x00\xff shader", "input.frag": b"shader"}
            for name, data in originals.items():
                file = source / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(data)
            destination = library.import_reference("hidden-files", source, "GLSL")
            self.assertEqual(catalog.read_json(destination / "reference.json")["files"],
                             {name: catalog.digest(data) for name, data in originals.items()})
            self.git("add", ".")
            tracked = self.git("ls-files", "-z").rstrip("\0").split("\0")
            with tempfile.TemporaryDirectory() as checkout:
                fresh = pathlib.Path(checkout)
                for name in tracked:
                    file = fresh / name
                    file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(self.root / name, file)
                with patch.object(catalog, "ROOT", fresh):
                    self.assertEqual(len(library.validate()), 17)
                for name, data in originals.items():
                    self.assertEqual((fresh / "references/hidden-files/original" / name).read_bytes(), data)
            self.assertEqual(list((self.root / "references").glob(".import-*")), [])

    def test_import_rejects_destination_and_ancestor_ignore_rules(self):
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp) / "input.frag"
            source.write_bytes(b"shader")
            root_ignore = self.root / ".gitignore"
            root_ignore.write_text(root_ignore.read_text() + ".import-*/\n/references/blocked/original/*.frag\n/references/metadata-blocked/reference.json\n")
            (self.root / "references/.gitignore").write_text("ancestor-blocked/original/*.frag\n")
            for asset_id, omitted in (("blocked", "original/input.frag"), ("metadata-blocked", "reference.json"),
                                      ("ancestor-blocked", "original/input.frag")):
                with self.subTest(asset_id=asset_id), self.assertRaisesRegex(ValueError, "Git would omit") as raised:
                    library.import_reference(asset_id, source, "GLSL")
                self.assertIn(f"references/{asset_id}/{omitted} (ignored by Git)", str(raised.exception))
                self.assert_import_absent(asset_id)
            # The root rule for hidden staging names must not affect the final destination.
            library.import_reference("allowed", source, "GLSL")

    def test_import_honors_nested_ignore_and_negation(self):
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp)
            (source / "nested").mkdir()
            (source / "nested/.gitignore").write_text("*.frag\n!keep.frag\n")
            (source / "nested/keep.frag").write_bytes(b"keep")
            excluded = source / "nested/private.frag"
            excluded.write_bytes(b"private")
            with self.assertRaisesRegex(ValueError, "Git would omit") as raised:
                library.import_reference("nested-ignore", source, "GLSL")
            self.assertIn("references/nested-ignore/original/nested/private.frag", str(raised.exception))
            self.assertNotIn("keep.frag (ignored", str(raised.exception))
            self.assert_import_absent("nested-ignore")
            excluded.unlink()
            destination = library.import_reference("nested-ignore", source, "GLSL")
            self.assertEqual(set(catalog.read_json(destination / "reference.json")["files"]),
                             {"nested/.gitignore", "nested/keep.frag"})

    def test_import_honors_checkout_excludes(self):
        (self.root / ".git/info/exclude").write_text("references/info-excluded/original/input.frag\n")
        (self.root / "local-excludes").write_text("references/config-excluded/original/input.frag\n")
        self.git("config", "core.excludesFile", "local-excludes")
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp) / "input.frag"
            source.write_bytes(b"shader")
            for asset_id in ("info-excluded", "config-excluded"):
                with self.subTest(asset_id=asset_id), self.assertRaisesRegex(ValueError, "Git would omit"):
                    library.import_reference(asset_id, source, "GLSL")
                self.assert_import_absent(asset_id)

    def test_import_honors_global_and_explicitly_empty_excludes(self):
        excludes = self.root / "global-excludes"
        excludes.write_text("references/global-excluded/original/input.frag\n")
        config = self.root / "global-config"
        config.write_text(f"[core]\n\texcludesFile = {excludes}\n")
        self.git("config", "--unset", "core.excludesFile")
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config)}):
            source = pathlib.Path(temp) / "input.frag"
            source.write_bytes(b"shader")
            with self.assertRaisesRegex(ValueError, "Git would omit"):
                library.import_reference("global-excluded", source, "GLSL")
            self.assert_import_absent("global-excluded")
            self.git("config", "core.excludesFile", "")
            library.import_reference("global-excluded", source, "GLSL")

    def test_import_requires_git_and_checkout_before_staging(self):
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp) / "input.frag"
            source.write_bytes(b"shader")
            with patch.object(library.subprocess, "check_output", side_effect=FileNotFoundError("git")):
                with self.assertRaisesRegex(ValueError, "require Git and a working checkout"):
                    library.import_reference("missing-git", source, "GLSL")
            self.assert_import_absent("missing-git")
            (self.root / ".git").rename(self.root / "saved-git")
            try:
                with self.assertRaisesRegex(ValueError, "require Git and a working checkout"):
                    library.import_reference("missing-checkout", source, "GLSL")
                self.assert_import_absent("missing-checkout")
            finally:
                (self.root / "saved-git").rename(self.root / ".git")

    def test_import_git_check_failure_is_not_an_acceptance(self):
        run = subprocess.run
        def fail_check(command, **kwargs):
            if "check-ignore" in command:
                return subprocess.CompletedProcess(command, 128, b"", b"Git check failed")
            return run(command, **kwargs)
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp) / "input.frag"
            source.write_bytes(b"shader")
            with patch.object(library.subprocess, "run", side_effect=fail_check):
                with self.assertRaises(subprocess.CalledProcessError) as raised:
                    library.import_reference("git-error", source, "GLSL")
            self.assertEqual(raised.exception.returncode, 128)
            self.assert_import_absent("git-error")

    def test_readonly_import_is_validated_before_becoming_visible(self):
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp)
            (source / "nested").mkdir()
            file = source / "nested/input.frag"
            file.write_bytes(b"\x00\xff shader")
            file.chmod(0o555)
            (source / "nested").chmod(0o555)
            source.chmod(0o555)
            validate_reference = library.validate_reference
            def inspect_stage(item):
                self.assertFalse((self.root / "references/readonly").exists())
                self.assertEqual(library.assets("reference"), [])
                validate_reference(item)
            try:
                with patch.object(library, "validate_reference", side_effect=inspect_stage):
                    destination = library.import_reference("readonly", source, "GLSL")
                copied = destination / "original/nested/input.frag"
                self.assertEqual(copied.read_bytes(), file.read_bytes())
                self.assertEqual(stat.S_IMODE(copied.stat().st_mode), 0o555)
                for directory in (source, source / "nested"):
                    self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o555)
                self.assertEqual(list((self.root / "references").glob(".import-*")), [])
            finally:
                source.chmod(0o755)
                (source / "nested").chmod(0o755)

    def test_readonly_failure_preserves_error_cleans_stage_and_allows_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp)
            (source / "nested").mkdir()
            (source / "nested/input.frag").write_bytes(b"shader")
            (source / "nested").chmod(0o555)
            source.chmod(0o555)
            failure = ValueError("original validation failure")
            try:
                with patch.object(library, "validate_reference", side_effect=failure):
                    with self.assertRaises(ValueError) as raised:
                        library.import_reference("retryable", source, "GLSL")
                self.assertIs(raised.exception, failure)
                self.assert_import_absent("retryable")
                self.assertEqual(stat.S_IMODE(source.stat().st_mode), 0o555)
                self.assertEqual(stat.S_IMODE((source / "nested").stat().st_mode), 0o555)
                library.import_reference("retryable", source, "GLSL")
                library.validate()
            finally:
                source.chmod(0o755)
                (source / "nested").chmod(0o755)

    def test_partial_readonly_copy_failure_is_cleaned(self):
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp)
            (source / "input.frag").write_bytes(b"shader")
            copytree = shutil.copytree
            failure = PermissionError("original copy failure")
            def partial_copy(src, dst, *args, **kwargs):
                if pathlib.Path(src) == source:
                    copied = pathlib.Path(dst)
                    (copied / "nested").mkdir()
                    shutil.copy2(source / "input.frag", copied / "nested/input.frag")
                    (copied / "nested").chmod(0o555)
                    copied.chmod(0o555)
                    raise failure
                return copytree(src, dst, *args, **kwargs)
            with patch.object(library.shutil, "copytree", side_effect=partial_copy):
                with self.assertRaises(PermissionError) as raised:
                    library.import_reference("partial-copy", source, "GLSL")
            self.assertIs(raised.exception, failure)
            self.assert_import_absent("partial-copy")
            library.import_reference("partial-copy", source, "GLSL")

    def test_cleanup_failure_preserves_original_error_and_reports_hidden_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp) / "input.frag"
            source.write_bytes(b"shader")
            failure = ValueError("original validation failure")
            diagnostics = io.StringIO()
            with patch.object(library, "validate_reference", side_effect=failure), \
                    patch.object(library.shutil, "rmtree", side_effect=PermissionError("cleanup failed")), \
                    contextlib.redirect_stderr(diagnostics):
                with self.assertRaises(ValueError) as raised:
                    library.import_reference("cleanup-failure", source, "GLSL")
            self.assertIs(raised.exception, failure)
            self.assertFalse((self.root / "references/cleanup-failure").exists())
            stages = list((self.root / "references").glob(".import-*"))
            self.assertEqual(len(stages), 1)
            self.assertIn("Could not remove import staging " + str(stages[0].relative_to(self.root)), diagnostics.getvalue())
            self.assertEqual(library.assets("reference"), [])
            self.assertEqual(len(library.validate()), 16)
            shutil.rmtree(stages[0])

    def test_import_is_independent_of_unrelated_broken_reference(self):
        broken = self.root / "references/broken"
        broken.mkdir()
        (broken / "reference.json").write_text("{")
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp) / "input.frag"
            source.write_bytes(b"shader")
            destination = library.import_reference("valid-reference", source, "GLSL")
            self.assertEqual((destination / "original/input.frag").read_bytes(), b"shader")
            with self.assertRaises(json.JSONDecodeError):
                library.validate()

    def test_import_rejects_mismatched_template_id_without_scanning_library(self):
        template = self.root / "templates/reference/reference.json"
        spec = catalog.read_json(template)
        spec["id"] = "wrong-template-id"
        catalog.write_json(template, spec)
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp) / "input.frag"
            source.write_bytes(b"shader")
            with self.assertRaisesRegex(ValueError, "Invalid reference"):
                library.import_reference("valid-id", source, "GLSL")
            self.assert_import_absent("valid-id")

    def test_reference_imported_from_must_match_public_id_when_present(self):
        destination = library.scaffold("reference", "public-reference")
        spec = catalog.read_json(destination / "reference.json")
        spec["origin"]["url"] = "https://example.invalid/shader"
        catalog.write_json(destination / "reference.json", spec)
        library.validate()
        for value in ("/Users/José/private/input.frag", "relative/input.frag", "wrong-label", None, 42, {}, []):
            with self.subTest(value=value):
                spec["origin"]["importedFrom"] = value
                catalog.write_json(destination / "reference.json", spec)
                with self.assertRaisesRegex(ValueError, "replace origin.importedFrom with the public reference ID"):
                    library.validate()
        spec["origin"]["importedFrom"] = "public-reference"
        catalog.write_json(destination / "reference.json", spec)
        library.validate()
        self.assertEqual(catalog.read_json(destination / "reference.json")["origin"]["url"], "https://example.invalid/shader")

    def test_destination_created_during_import_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp) / "input.frag"
            source.write_bytes(b"shader")
            destination = self.root / "references/occupied"
            validate_reference = library.validate_reference
            def occupy(item):
                validate_reference(item)
                destination.mkdir()
                (destination / "sentinel").write_bytes(b"existing")
            with patch.object(library, "validate_reference", side_effect=occupy):
                with self.assertRaisesRegex(ValueError, "Refusing to overwrite"):
                    library.import_reference("occupied", source, "GLSL")
            self.assertEqual((destination / "sentinel").read_bytes(), b"existing")
            self.assertEqual(list((self.root / "references").glob(".import-*")), [])

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
