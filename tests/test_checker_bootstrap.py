import contextlib
import hashlib
import importlib.util
import importlib.machinery
import io
import json
import marshal
import os
from pathlib import Path
import shutil
import shlex
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "tools/checker_bootstrap.py"
spec = importlib.util.spec_from_file_location("checker_bootstrap", SCRIPT)
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def fixture_environment():
    return dict({key: value for key, value in os.environ.items() if not key.startswith("GIT_")}, LC_ALL="C")


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="checker bootstrap ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.lock = self.root / "checker.lock.json"
        self.artifact = self.root / "download.pyz"
        self.cache = self.root / "cache"
        self.marker = self.root / "executed"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        curl = self.bin / "curl"
        curl.write_text(f"#!{sys.executable}\n" + """
import json, os, pathlib, sys
pathlib.Path(os.environ['BOOTSTRAP_CURL_ARGUMENTS']).write_text(json.dumps(sys.argv[1:]))
if '--silent' not in sys.argv and '--no-progress-meter' not in sys.argv:
    print('curl progress table', file=sys.stderr)
if os.environ.get('BOOTSTRAP_DOWNLOAD_RETRY') and '--silent' not in sys.argv:
    print('Warning: simulated retry, 1 retries left', file=sys.stderr)
target = pathlib.Path(sys.argv[sys.argv.index('--output') + 1])
if os.environ.get('BOOTSTRAP_DOWNLOAD_FAILURE'):
    target.write_bytes(b'partial download')
    if '--silent' not in sys.argv or '--show-error' in sys.argv:
        print('curl: simulated download failure', file=sys.stderr)
    raise SystemExit(22)
target.write_bytes(pathlib.Path(os.environ['BOOTSTRAP_DOWNLOAD']).read_bytes())
""")
        curl.chmod(0o755)
        self.env = dict(fixture_environment(), PATH=str(self.bin) + os.pathsep + os.environ.get("PATH", ""),
                        BOOTSTRAP_DOWNLOAD=str(self.artifact), BOOTSTRAP_TEST_MARKER=str(self.marker),
                        BOOTSTRAP_CURL_ARGUMENTS=str(self.root / "curl.json"))
        self.pin = {"version": "1.1.0", "interfaceVersion": 1,
                    "repository": "hbmartin/HolodeckShaderCheck", "sourceCommit": "a" * 40}
        self.make_checker()

    def write_pin(self):
        self.pin["sha256"] = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        self.lock.write_text(json.dumps(self.pin))

    def make_checker(self, info=None):
        info = info if info is not None else {"checkerVersion": "1.1.0", "interfaceVersion": 1, "additional": "supported"}
        code = """
import json, os, pathlib, sys
pathlib.Path(os.environ['BOOTSTRAP_TEST_MARKER']).touch()
if sys.argv[1:] == ['info', '--json']:
    print(INFO)
else:
    print(json.dumps(sys.argv[1:]))
    print('checker diagnostic', file=sys.stderr)
    raise SystemExit(int(sys.argv[-1]))
""".replace("INFO", repr(json.dumps(info)))
        with zipfile.ZipFile(self.artifact, "w") as archive:
            archive.writestr("__main__.py", code)
        self.write_pin()

    def cli(self, *args):
        return subprocess.run([sys.executable, "-I", str(SCRIPT), *args], cwd=self.root,
                              env=self.env, capture_output=True, text=True)

    def prepare(self):
        return self.cli("prepare", "--lock", str(self.lock), "--cache-dir", str(self.cache))

    def assert_cache_preserved(self, result):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual((self.cache / "holodeck-shader-check-1.1.0.pyz").read_bytes(), self.previous_bytes)
        self.assertEqual(sorted(p.name for p in self.cache.iterdir()), ["holodeck-shader-check-1.1.0.pyz"])

    def previous_cache(self):
        self.cache.mkdir()
        self.previous_bytes = self.artifact.read_bytes()
        (self.cache / "holodeck-shader-check-1.1.0.pyz").write_bytes(self.previous_bytes)

    def test_lock_rejects_invalid_fields_and_exact_interface_types(self):
        cases = {"version": [None, 1, "../escape", "1.1.0\nextra=value", "1.01.0", "2.0.0"],
                 "sourceCommit": [None, "x" * 40, "a" * 39],
                 "sha256": [None, "A" * 64, "a" * 63],
                 "repository": [None, "other/repository"],
                 "interfaceVersion": [None, True, 1.0, "1", 2]}
        valid = dict(self.pin)
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    self.lock.write_text(json.dumps(dict(valid, **{field: value})))
                    with self.assertRaises(bootstrap.BootstrapError):
                        bootstrap.read_lock(self.lock)
        for content in ("{", "[]"):
            self.lock.write_text(content)
            with self.assertRaises((ValueError, bootstrap.BootstrapError)):
                bootstrap.read_lock(self.lock)

    def test_prepare_repeats_and_accepts_additional_info_fields(self):
        for _ in range(2):
            result = self.prepare()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            metadata = json.loads(result.stdout)
            self.assertEqual(metadata["sourceCommit"], self.pin["sourceCommit"])
            self.assertEqual(Path(metadata["artifactPath"]).read_bytes(), self.artifact.read_bytes())
        curl = json.loads((self.root / "curl.json").read_text())
        self.assertIn("--no-progress-meter", curl)
        self.assertNotIn("--silent", curl)
        self.assertEqual(curl[curl.index("--proto") + 1], "=https")
        self.assertEqual(curl[curl.index("--proto-redir") + 1], "=https")
        self.assertIn("https://github.com/hbmartin/HolodeckShaderCheck/releases/download/v1.1.0/holodeck-shader-check-1.1.0.pyz", curl)
        self.assertEqual(len(list(self.cache.iterdir())), 1)

    def test_retry_notices_are_preserved_without_progress(self):
        self.env["BOOTSTRAP_DOWNLOAD_RETRY"] = "1"
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "Warning: simulated retry, 1 retries left\n")
        self.assertEqual(json.loads(result.stdout)["sourceCommit"], self.pin["sourceCommit"])

    def test_bad_hash_preserves_cache_and_does_not_execute_download(self):
        self.previous_cache()
        self.pin["sha256"] = "0" * 64
        self.lock.write_text(json.dumps(self.pin))
        result = self.prepare()
        self.assert_cache_preserved(result)
        self.assertIn("SHA-256", result.stderr)
        self.assertFalse(self.marker.exists())

    def test_interrupted_download_preserves_cache_without_fallback(self):
        self.previous_cache()
        self.env["BOOTSTRAP_DOWNLOAD_FAILURE"] = "1"
        result = self.prepare()
        self.assert_cache_preserved(result)
        self.assertEqual(result.stdout, "")
        self.assertIn("curl: simulated download failure", result.stderr)
        self.assertFalse(self.marker.exists())

    def test_failed_checker_info_keeps_captured_diagnostics_on_stderr(self):
        self.previous_cache()
        with zipfile.ZipFile(self.artifact, "w") as archive:
            archive.writestr("__main__.py", r"""
import sys
sys.stdout.buffer.write(b'checker info output\xff\n')
sys.stderr.buffer.write(b'checker info failure\xff\n')
raise SystemExit(23)
""")
        self.write_pin()
        result = self.prepare()
        self.assert_cache_preserved(result)
        self.assertEqual(result.stdout, "")
        self.assertIn("info", result.stderr)
        self.assertIn("exit status 23", result.stderr)
        self.assertIn("stdout:\nchecker info output\ufffd", result.stderr)
        self.assertIn("stderr:\nchecker info failure\ufffd", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_incompatible_info_preserves_cache(self):
        self.previous_cache()
        for info in ({"checkerVersion": "1.0.2", "interfaceVersion": 1},
                     {"checkerVersion": 1.1, "interfaceVersion": 1},
                     {"checkerVersion": "1.1.0", "interfaceVersion": True},
                     {"checkerVersion": "1.1.0", "interfaceVersion": 1.0},
                     {"checkerVersion": "1.1.0", "interfaceVersion": 2}, [], {}):
            with self.subTest(info=info):
                self.make_checker(info)
                self.assert_cache_preserved(self.prepare())

    def test_run_preserves_checker_arguments_streams_and_exit_status(self):
        for status in (0, 1, 2):
            result = self.cli("run", "--lock", str(self.lock), "--cache-dir", str(self.cache),
                              "--", "validate", "/a library/root", "--json", str(status))
            self.assertEqual(result.returncode, status, result.stderr)
            self.assertEqual(json.loads(result.stdout), ["validate", "/a library/root", "--json", str(status)])
            self.assertEqual(result.stderr, "checker diagnostic\n")

    def test_prepare_emits_validated_github_outputs(self):
        output = self.root / "outputs"
        result = self.cli("prepare", "--lock", str(self.lock), "--cache-dir", str(self.cache),
                          "--github-output", str(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        values = dict(line.split("=", 1) for line in output.read_text().splitlines())
        self.assertEqual(values["repository"], self.pin["repository"])
        self.assertEqual(values["interfaceVersion"], "1")
        self.assertEqual(Path(values["artifactPath"]), (self.cache / "holodeck-shader-check-1.1.0.pyz").resolve())

    def test_defaults_do_not_depend_on_working_directory(self):
        args = bootstrap.parser().parse_args(["prepare"])
        self.assertEqual(args.lock, SCRIPT.parents[1] / "shader_checker.lock.json")
        self.assertEqual(args.cache_dir, SCRIPT.parents[1] / ".cache/checker")


class SourceVerificationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="checker source ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package = self.root / "src/holodeck_shader_check"
        self.package.mkdir(parents=True)
        (self.package / "__init__.py").write_text('__version__ = "1.1.0"\n')
        (self.package / "cli.py").write_text("raise AssertionError('Source must never be imported')\n")
        for relative in ("tools/run_tests.py", "tests/test_checker.py"):
            path = self.root / relative
            path.parent.mkdir()
            path.write_text("raise SystemExit(1)\n")
        (self.root / ".gitignore").write_text("__pycache__/\n*.so\nignored.bin\n")
        (self.root / "README.md").write_text("Fixture checkout\n")
        self.git("init", "--quiet")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "core.fsmonitor", "")
        self.git("add", "src", "tools", "tests", ".gitignore", "README.md")
        self.commit()
        self.pin = {"sourceCommit": self.git("rev-parse", "HEAD").decode().strip()}
        self.entries = {"holodeck_shader_check/" + p.name: p.read_bytes() for p in self.package.iterdir()}
        self.entries["__main__.py"] = bootstrap.ENTRY_POINT
        self.artifact = self.root / "checker.pyz"

    def git(self, *arguments):
        environment = dict(fixture_environment(), GIT_CEILING_DIRECTORIES=str(self.root.parent))
        return subprocess.run(["git", "-C", str(self.root), *arguments], env=environment,
                              check=True, capture_output=True).stdout

    def commit(self):
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "fixture")

    def commit_source(self, *paths):
        self.git("add", *paths)
        self.commit()
        self.pin["sourceCommit"] = self.git("rev-parse", "HEAD").decode().strip()
        self.archive()

    def write_lock(self, **overrides):
        lock = self.root / "lock.json"
        lock.write_text(json.dumps(dict(self.pin, version="1.1.0", interfaceVersion=1,
                                        repository="hbmartin/HolodeckShaderCheck") | overrides))
        return lock

    def archive(self, entries=None):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.artifact, "w", compression=zipfile.ZIP_STORED) as archive:
                for name, value in (entries if entries is not None else reversed(list(self.entries.items()))):
                    archive.writestr(name, value)
        self.pin["sha256"] = hashlib.sha256(self.artifact.read_bytes()).hexdigest()

    def cli(self, source=None, env=None):
        lock = self.write_lock()
        return subprocess.run(
            [sys.executable, "-I", str(SCRIPT), "verify-source", "--lock", str(lock),
             "--source", str(source if source is not None else self.root), "--artifact", str(self.artifact)],
            capture_output=True, text=True, env=env if env is not None else fixture_environment(),
        )

    def test_matches_sources_independently_of_archive_encoding_without_imports(self):
        self.archive()
        bootstrap.verify_source(self.pin, self.root, self.artifact)

    def test_wrong_source_commit_fails(self):
        self.archive()
        self.pin["sourceCommit"] = "b" * 40
        with self.assertRaisesRegex(bootstrap.BootstrapError, "HEAD"):
            bootstrap.verify_source(self.pin, self.root, self.artifact)

    def test_clean_checkout_allows_untracked_scratch_files(self):
        self.archive()
        scratch = self.root / ".cache/scratch.json"
        scratch.parent.mkdir()
        scratch.write_text("{}")
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_index_flags_do_not_hide_edits_to_any_tracked_file(self):
        self.archive()
        for flag in ("assume-unchanged", "skip-worktree"):
            for relative in ("tools/run_tests.py", "tests/test_checker.py", "src/holodeck_shader_check/cli.py", "README.md"):
                with self.subTest(flag=flag, path=relative):
                    path = self.root / relative
                    original = path.read_bytes()
                    self.git("update-index", "--" + flag, relative)
                    try:
                        self.assertEqual(self.cli().returncode, 0)
                        path.write_text("raise SystemExit(0)\n")
                        self.assertEqual(self.git("status", "--porcelain", "--untracked-files=no"), b"")
                        result = self.cli()
                        self.assertEqual(result.returncode, 2, result.stderr)
                        self.assertIn("tracked changes", result.stderr)
                        self.assertIn(relative, result.stderr)
                    finally:
                        path.write_bytes(original)
                        self.git("update-index", "--no-" + flag, relative)

    def test_hidden_deletions_and_file_type_substitutions_fail(self):
        self.archive()
        relative = "tools/run_tests.py"
        path = self.root / relative
        original = path.read_bytes()
        target = self.root / "same-bytes.py"
        target.write_bytes(original)
        self.git("update-index", "--assume-unchanged", relative)
        try:
            for kind in ("deleted", "symlink", "directory", "executable"):
                with self.subTest(kind=kind):
                    path.unlink()
                    if kind == "symlink":
                        path.symlink_to(target)
                    elif kind == "directory":
                        path.mkdir()
                    elif kind == "executable":
                        path.write_bytes(original)
                        path.chmod(0o755)
                    try:
                        result = self.cli()
                        self.assertEqual(result.returncode, 2, result.stderr)
                        self.assertIn(relative, result.stderr)
                    finally:
                        if path.is_dir() and not path.is_symlink():
                            path.rmdir()
                        elif path.exists() or path.is_symlink():
                            path.unlink()
                        path.write_bytes(original)
        finally:
            self.git("update-index", "--no-assume-unchanged", relative)

    def test_tracked_parent_directory_cannot_be_replaced_by_a_symlink(self):
        self.archive()
        tools = self.root / "tools"
        saved = self.root / "saved-tools"
        self.git("update-index", "--assume-unchanged", "tools/run_tests.py")
        tools.rename(saved)
        tools.symlink_to(saved, target_is_directory=True)
        result = self.cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("requires a real tools/ directory", result.stderr)

    def test_nested_tracked_package_cannot_be_replaced_by_an_identical_symlink(self):
        self.archive()
        saved = self.root / "saved package"
        self.package.rename(saved)
        self.package.symlink_to(saved, target_is_directory=True)
        original = (saved / "cli.py").read_bytes()
        result = self.cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("tracked changes", result.stderr)
        self.assertIn("src/holodeck_shader_check/cli.py", result.stderr)
        self.assertTrue(self.package.is_symlink())
        self.assertEqual((saved / "cli.py").read_bytes(), original)

    def test_staged_changes_fail_even_when_working_bytes_match_head(self):
        self.archive()
        path = self.root / "tools/run_tests.py"
        original = path.read_bytes()
        path.write_text("raise SystemExit(0)\n")
        self.git("add", "tools/run_tests.py")
        path.write_bytes(original)
        result = self.cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("tracked changes", result.stderr)

    def test_extra_execution_files_fail_even_when_ignored(self):
        self.archive()
        suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
        for relative in ("tests/test_zz.py", "src/holodeck_shader_check/scratch.py",
                         "src/holodeck_shader_check/cli" + suffix, "tools/ignored.bin"):
            with self.subTest(path=relative):
                path = self.root / relative
                path.write_text("raise SystemExit(0)\n")
                try:
                    result = self.cli()
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("Unexpected checker execution files", result.stderr)
                    self.assertIn(relative, result.stderr)
                    self.assertTrue(path.exists(), "Verification must not delete unexpected files")
                finally:
                    path.unlink()
        (self.root / "tests/empty-directory").mkdir()
        result = self.cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("tests/empty-directory/", result.stderr)

    def test_forged_matching_bytecode_is_rejected(self):
        self.archive()
        source = self.package / "cli.py"
        info = source.stat()
        cache = Path(importlib.util.cache_from_source(str(source)))
        cache.parent.mkdir()
        code = compile("raise SystemExit(0)\n", str(source), "exec")
        cache.write_bytes(importlib.util.MAGIC_NUMBER + struct.pack("<III", 0, int(info.st_mtime), info.st_size) +
                          marshal.dumps(code))
        result = self.cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(cache.parent.relative_to(self.root).as_posix() + "/", result.stderr)
        self.assertTrue(cache.exists(), "Verification must not delete bytecode")
        self.assertNotIn("Traceback", result.stderr)

    def test_untracked_directory_links_are_rejected_without_following_them(self):
        self.archive()
        for target in (self.root / "absent", self.package, self.root / "tests"):
            with self.subTest(target=target):
                link = self.root / "tests/extra"
                link.symlink_to(target, target_is_directory=True)
                try:
                    result = self.cli()
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("tests/extra", result.stderr)
                finally:
                    link.unlink()

    def test_git_environment_cannot_redirect_verification(self):
        self.archive()
        invalid = dict(fixture_environment(), GIT_DIR=str(self.root / "absent-git"),
                       GIT_WORK_TREE=str(self.root / "absent-worktree"), GIT_INDEX_FILE=str(self.root / "absent-index"))
        result = self.cli(env=invalid)
        self.assertEqual(result.returncode, 0, result.stderr)
        with tempfile.TemporaryDirectory(prefix="foreign checker ") as temporary:
            foreign = Path(temporary) / "clean"
            shutil.copytree(self.root, foreign)
            index = (foreign / ".git/index").read_bytes()
            environment = dict(fixture_environment(), GIT_DIR=str(foreign / ".git"),
                               GIT_WORK_TREE=str(foreign), GIT_INDEX_FILE=str(foreign / ".git/index"))
            (self.root / "tools/run_tests.py").write_text("raise SystemExit(0)\n")
            result = self.cli(env=environment)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("tools/run_tests.py", result.stderr)
            self.assertEqual((foreign / ".git/index").read_bytes(), index)

    def test_git_replacement_refs_cannot_change_the_verified_commit(self):
        self.archive()
        (self.root / "tools/run_tests.py").write_text("raise SystemExit(0)\n")
        self.git("add", "tools/run_tests.py")
        self.commit()
        replacement = self.git("rev-parse", "HEAD").decode().strip()
        self.git("checkout", "--quiet", "--detach", self.pin["sourceCommit"])
        self.git("replace", self.pin["sourceCommit"], replacement)
        self.git("reset", "--hard", "HEAD")
        result = self.cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("tools/run_tests.py", result.stderr)

    def test_nested_source_directory_is_not_a_checkout_root(self):
        self.archive()
        result = self.cli(self.root / "src")
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_root_guard_rejects_an_explicit_alternate_worktree(self):
        self.archive()
        alternate = self.root / "alternate worktree"
        alternate.mkdir()
        self.git("config", "core.worktree", str(alternate))
        result = self.cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("Checker source must be the Git checkout root", result.stderr)

    def test_crlf_readme_is_accepted_without_refreshing_the_index(self):
        self.archive()
        self.git("config", "core.autocrlf", "true")
        readme = self.root / "README.md"
        readme.unlink()
        self.git("checkout-index", "--force", "--index", "--", "README.md")
        self.assertIn(b"\r\n", readme.read_bytes())
        self.assertEqual(self.git("status", "--porcelain", "--untracked-files=no"), b"")
        index = (self.root / ".git/index").read_bytes()
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual((self.root / ".git/index").read_bytes(), index)

    def test_only_documentation_may_change_utf8_line_endings(self):
        cases = [("docs/nested/guide.md", b"caf\xc3\xa9\nsecond\r\n", b"caf\xc3\xa9\r\nsecond\n", 0),
                 ("docs/nul.md", b"data\0\n", b"data\0\r\n", 2),
                 ("docs/nonutf8.md", b"\xff\n", b"\xff\r\n", 2),
                 ("docs/barecr.md", b"line\n", b"line\r", 2),
                 ("docs/content.md", b"line\n", b"changed\r\n", 2),
                 ("tests/fixture.txt", b"line\r\n", b"line\n", 2),
                 ("tests/fixture.md", b"line\r\n", b"line\n", 2),
                 ("configuration.toml", b"number = 1\n", b"number = 1\r\n", 2),
                 ("tools/sample.py", b"# sample\n", b"# sample\r\n", 2),
                 ("notes.md", b"line\n", b"line\r\n", 2)]
        for name, original, changed, status in cases:
            with self.subTest(path=name):
                path = self.root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(original)
                self.commit_source(path.relative_to(self.root).as_posix())
                path.write_bytes(changed)
                try:
                    result = self.cli()
                    self.assertEqual(result.returncode, status, result.stderr)
                    if status:
                        self.assertIn(path.name, result.stderr)
                finally:
                    path.write_bytes(original)
        package_file = self.package / "cli.py"
        package_file.write_bytes(package_file.read_bytes().replace(b"\n", b"\r\n"))
        result = self.cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("src/holodeck_shader_check/cli.py", result.stderr)

    def test_executable_bit_follows_owner_bit_and_core_filemode(self):
        self.archive()
        self.git("config", "core.fileMode", "true")
        readme = self.root / "README.md"
        readme.chmod(0o645)
        self.assertEqual(self.cli().returncode, 0)
        readme.chmod(0o755)
        result = self.cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("README.md", result.stderr)
        self.git("config", "core.fileMode", "false")
        for name in self.git("ls-files", "-z").split(b"\0"):
            if name:
                (self.root / os.fsdecode(name)).chmod(0o777)
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_finder_exception_is_only_for_regular_untracked_files(self):
        self.archive()
        for directory in (self.package, self.root / "tools", self.root / "tests"):
            (directory / ".DS_Store").write_bytes(b"Finder metadata")
        self.assertEqual(self.cli().returncode, 0)
        metadata = self.package / ".DS_Store"
        metadata.unlink()
        metadata.mkdir()
        result = self.cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(".DS_Store/", result.stderr)
        metadata.rmdir()
        metadata.symlink_to(self.package / "cli.py")
        result = self.cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(".DS_Store", result.stderr)

    def test_empty_import_namespace_is_rejected(self):
        self.archive()
        (self.root / "src/tomllib").mkdir()
        result = self.cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("src/tomllib/", result.stderr)

    def test_missing_required_roots_have_context_even_when_absent_from_head(self):
        for name in ("src", "tests", "tools"):
            with self.subTest(directory=name):
                nested = SourceVerificationTests()
                try:
                    nested.setUp()
                    shutil.rmtree(nested.root / name)
                    nested.commit_source("-u")
                    result = nested.cli()
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn(f"requires a real {name}/ directory", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                finally:
                    nested.doCleanups()

    def test_custom_filter_cannot_hide_a_changed_runner_or_run_during_verification(self):
        (self.root / ".gitattributes").write_text("tools/run_tests.py filter=mask\n")
        self.commit_source(".gitattributes")
        marker = self.root / "filter executed"
        script = self.root / "filter command.py"
        script.write_text("import pathlib,sys\npathlib.Path(" + repr(str(marker)) + ").touch()\n"
                          "sys.stdout.write('raise SystemExit(1)\\n')\n")
        self.git("config", "filter.mask.clean", shlex.quote(sys.executable) + " " + shlex.quote(str(script)))
        (self.root / "tools/run_tests.py").write_text("raise SystemExit(0)\n")
        result = self.cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("tools/run_tests.py", result.stderr)
        self.assertFalse(marker.exists(), "Verification must not execute custom filters")

    def test_fsmonitor_hook_cannot_run_during_clean_or_modified_verification(self):
        self.archive()
        marker = self.root / "fsmonitor executed"
        hook = self.root / "fsmonitor hook"
        hook.write_text(f"#!{sys.executable}\nimport pathlib,sys\n"
                        f"pathlib.Path({str(marker)!r}).touch()\n"
                        "sys.stdout.buffer.write(b'review-token\\0')\n")
        hook.chmod(0o755)
        self.git("config", "core.fsmonitor", shlex.quote(str(hook)))
        self.git("update-index", "--fsmonitor")
        self.git("diff", "--cached", "--name-only")
        self.assertTrue(marker.exists(), "The hook must be active for this regression fixture")
        marker.unlink()
        index = (self.root / ".git/index").read_bytes()
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())
        self.assertEqual((self.root / ".git/index").read_bytes(), index)
        (self.root / "tools/run_tests.py").write_text("raise SystemExit(0)\n")
        result = self.cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("tools/run_tests.py", result.stderr)
        self.assertFalse(marker.exists())
        self.assertEqual((self.root / ".git/index").read_bytes(), index)

    def test_git_process_count_does_not_grow_per_tracked_file(self):
        self.archive()
        with mock.patch.object(bootstrap.subprocess, "run", wraps=subprocess.run) as run:
            bootstrap.verify_source(self.pin, self.root, self.artifact)
            small_count = run.call_count
        for number in range(40):
            (self.root / "tests" / f"fixture-{number}.txt").write_text(f"Fixture {number}\n")
        self.commit_source("tests")
        with mock.patch.object(bootstrap.subprocess, "run", wraps=subprocess.run) as run:
            bootstrap.verify_source(self.pin, self.root, self.artifact)
            self.assertEqual(run.call_count, small_count)

    def test_fixtures_are_isolated_inside_an_outer_repo_with_git_environment(self):
        original_head = self.git("rev-parse", "HEAD")
        original_index = (self.root / ".git/index").read_bytes()
        original_runner = (self.root / "tools/run_tests.py").read_bytes()
        environment = dict(GIT_DIR=str(self.root / ".git"), GIT_WORK_TREE=str(self.root),
                           GIT_INDEX_FILE=str(self.root / ".git/index"))
        with mock.patch.dict(os.environ, environment), mock.patch.object(tempfile, "tempdir", str(self.root)):
            nested = SourceVerificationTests()
            try:
                nested.setUp()
                nested.archive()
                self.assertEqual(nested.cli().returncode, 0)
                nested.test_failed_git_keeps_its_diagnostic()
            finally:
                nested.doCleanups()
        self.assertEqual(self.git("rev-parse", "HEAD"), original_head)
        self.assertEqual((self.root / ".git/index").read_bytes(), original_index)
        self.assertEqual((self.root / "tools/run_tests.py").read_bytes(), original_runner)

    def test_modified_staged_and_deleted_tracked_tests_fail(self):
        self.archive()
        for relative in ("tools/run_tests.py", "tests/test_checker.py"):
            for state in ("modified", "staged", "deleted", "staged deletion"):
                with self.subTest(path=relative, state=state):
                    path = self.root / relative
                    if "delet" in state:
                        path.unlink()
                    else:
                        path.write_text("raise SystemExit(0)\n")
                    if state.startswith("staged"):
                        self.git("add", relative)
                    try:
                        result = self.cli()
                        self.assertEqual(result.returncode, 2, result.stderr)
                        self.assertEqual(result.stdout, "")
                        self.assertIn("tracked changes", result.stderr)
                        self.assertIn(relative, result.stderr)
                        self.assertNotIn("Traceback", result.stderr)
                    finally:
                        self.git("restore", "--staged", "--worktree", "--", relative)

    def test_failed_git_keeps_its_diagnostic(self):
        self.archive()
        with tempfile.TemporaryDirectory(prefix="not a git checkout ") as source:
            result = self.cli(source)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("rev-parse", result.stderr)
        self.assertIn("exit status 128", result.stderr)
        self.assertIn("fatal: not a git repository", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_timeout_keeps_partial_output_without_a_traceback(self):
        self.archive()
        lock = self.write_lock()
        for output, diagnostic in ((b"partial output\xff\n", b"partial error\xff\n"),
                                   ("partial output\n", "partial error\n")):
            with self.subTest(output_type=type(output).__name__):
                error = subprocess.TimeoutExpired(["git", "rev-parse"], 10, output=output, stderr=diagnostic)
                with mock.patch.object(bootstrap.subprocess, "run", side_effect=error), \
                        contextlib.redirect_stdout(io.StringIO()) as stdout, \
                        contextlib.redirect_stderr(io.StringIO()) as stderr:
                    status = bootstrap.main(["verify-source", "--lock", str(lock), "--source", str(self.root),
                                             "--artifact", str(self.artifact)])
                self.assertEqual(status, 2)
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn("git", stderr.getvalue())
                self.assertIn("timed out after 10 seconds", stderr.getvalue())
                self.assertIn("stdout:\npartial output", stderr.getvalue())
                self.assertIn("stderr:\npartial error", stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_batch_failures_never_log_data_stdout_even_through_a_cause(self):
        self.archive()
        lock = self.write_lock()
        original_run = subprocess.run
        original_git = bootstrap.source_git
        payload = b"RAW_BLOB_PAYLOAD\0\xff"
        for failure in ("timeout", "exit"):
            for wrapped in (False, True):
                with self.subTest(failure=failure, wrapped=wrapped):
                    def fail_batch(command, *args, **kwargs):
                        if "cat-file" in command:
                            if failure == "timeout":
                                raise subprocess.TimeoutExpired(command, 10, output=payload, stderr=b"git read diagnostic\n")
                            raise subprocess.CalledProcessError(23, command, output=payload, stderr=b"git read diagnostic\n")
                        return original_run(command, *args, **kwargs)

                    def source_git(source, *arguments, **kwargs):
                        try:
                            return original_git(source, *arguments, **kwargs)
                        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
                            if wrapped:
                                raise bootstrap.BootstrapError(f"Cannot read source objects: {error}") from error
                            raise

                    with mock.patch.object(bootstrap.subprocess, "run", side_effect=fail_batch), \
                            mock.patch.object(bootstrap, "source_git", side_effect=source_git), \
                            contextlib.redirect_stdout(io.StringIO()) as stdout, \
                            contextlib.redirect_stderr(io.StringIO()) as stderr:
                        status = bootstrap.main(["verify-source", "--lock", str(lock), "--source", str(self.root),
                                                 "--artifact", str(self.artifact)])
                    self.assertEqual(status, 2)
                    self.assertEqual(stdout.getvalue(), "")
                    self.assertIn("cat-file", stderr.getvalue())
                    self.assertIn("timed out after 10 seconds" if failure == "timeout" else "exit status 23", stderr.getvalue())
                    self.assertIn("stderr:\ngit read diagnostic", stderr.getvalue())
                    self.assertNotIn("RAW_BLOB_PAYLOAD", stderr.getvalue())
                    self.assertNotIn("stdout:", stderr.getvalue())
                    self.assertNotIn("Traceback", stderr.getvalue())

    def test_missing_additional_duplicate_and_changed_entries_fail(self):
        entries = list(self.entries.items())
        cases = [entries[1:], entries + [("unexpected.py", b"extra")], entries + [entries[0]],
                 [(name, b"changed" if name == "__main__.py" else data) for name, data in entries],
                 [(name, b"changed" if name.endswith("cli.py") else data) for name, data in entries]]
        for case in cases:
            with self.subTest(names=[name for name, _ in case]):
                self.archive(case)
                with self.assertRaises(bootstrap.BootstrapError):
                    bootstrap.verify_source(self.pin, self.root, self.artifact)

    def test_artifact_hash_and_modified_checkout_fail(self):
        self.archive()
        self.pin["sha256"] = "0" * 64
        with self.assertRaisesRegex(bootstrap.BootstrapError, "SHA-256"):
            bootstrap.verify_source(self.pin, self.root, self.artifact)
        self.archive()
        (self.package / "cli.py").write_text("changed source\n")
        with self.assertRaisesRegex(bootstrap.BootstrapError, "tracked changes"):
            bootstrap.verify_source(self.pin, self.root, self.artifact)

    def test_unreadable_archives_report_bootstrap_failures(self):
        cases = {"encrypted": "encrypted", "unsupported": "compression", "deflate": "decompressing",
                 "invalid": "not a zip file"}
        for kind, message in cases.items():
            with self.subTest(kind=kind):
                self.archive()
                data = bytearray(self.artifact.read_bytes())
                # archive() writes __main__.py first; edit its local and central headers together.
                central = data.index(b"PK\x01\x02")
                if kind == "encrypted":
                    for offset in (6, central + 8):
                        struct.pack_into("<H", data, offset, struct.unpack_from("<H", data, offset)[0] | 1)
                elif kind in ("unsupported", "deflate"):
                    for offset in (8, central + 10):
                        struct.pack_into("<H", data, offset, 99 if kind == "unsupported" else zipfile.ZIP_DEFLATED)
                    if kind == "deflate":
                        name_size, extra_size = struct.unpack_from("<HH", data, 26)
                        data[30 + name_size + extra_size] = 0x07  # Reserved deflate block type.
                else:
                    data = bytearray(b"not a zip file")
                self.artifact.write_bytes(data)
                self.pin["sha256"] = hashlib.sha256(data).hexdigest()
                result = self.cli()
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn("Cannot read checker archive", result.stderr)
                self.assertIn(str(self.artifact), result.stderr)
                self.assertIn(message, result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_archive_eof_is_normalized_at_the_read_boundary(self):
        self.archive()
        with mock.patch.object(bootstrap.zipfile, "ZipFile", side_effect=EOFError("truncated archive")):
            with self.assertRaisesRegex(bootstrap.BootstrapError, "Cannot read checker archive.*truncated archive"):
                bootstrap.verify_source(self.pin, self.root, self.artifact)

    def test_corrupt_optional_compression_and_unicode_filenames_have_archive_context(self):
        methods = []
        if zipfile.bz2 is not None:
            methods.append(("bzip2", zipfile.ZIP_BZIP2, 0))
        if bootstrap.lzma is not None:
            methods.append(("lzma", zipfile.ZIP_LZMA, 9))
        if bootstrap.zstd is not None:
            methods.append(("zstandard", zipfile.ZIP_ZSTANDARD, 0))
        for kind, method, preserved in methods + [("unicode", zipfile.ZIP_STORED, 0)]:
            with self.subTest(kind=kind):
                with zipfile.ZipFile(self.artifact, "w", compression=method) as archive:
                    for name, content in reversed(list(self.entries.items())):
                        archive.writestr(name, content)
                data = bytearray(self.artifact.read_bytes())
                if kind == "unicode":
                    central = data.index(b"PK\x01\x02")
                    for offset in (6, central + 8):
                        struct.pack_into("<H", data, offset, struct.unpack_from("<H", data, offset)[0] | 0x800)
                    data[30] = data[central + 46] = 0xff
                else:
                    name_size, extra_size = struct.unpack_from("<HH", data, 26)
                    start = 30 + name_size + extra_size
                    size = struct.unpack_from("<I", data, 18)[0]
                    data[start + preserved:start + size] = b"\xff" * (size - preserved)
                self.artifact.write_bytes(data)
                self.pin["sha256"] = hashlib.sha256(data).hexdigest()
                result = self.cli()
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn("Cannot read checker archive", result.stderr)
                self.assertIn(str(self.artifact), result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_archive_cases_run_without_optional_bzip2(self):
        with mock.patch.object(zipfile, "bz2", None):
            self.test_corrupt_optional_compression_and_unicode_filenames_have_archive_context()

    def test_source_failure_is_reported_as_bootstrap_exit_two(self):
        self.archive()
        lock = self.write_lock(sourceCommit="b" * 40)
        with contextlib.redirect_stderr(io.StringIO()) as output:
            status = bootstrap.main(["verify-source", "--lock", str(lock), "--source", str(self.root), "--artifact", str(self.artifact)])
        self.assertEqual(status, 2)
        self.assertIn("HEAD", output.getvalue())
