import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
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
if '--silent' not in sys.argv:
    print('curl progress table', file=sys.stderr)
target = pathlib.Path(sys.argv[sys.argv.index('--output') + 1])
if os.environ.get('BOOTSTRAP_DOWNLOAD_FAILURE'):
    target.write_bytes(b'partial download')
    if '--silent' not in sys.argv or '--show-error' in sys.argv:
        print('curl: simulated download failure', file=sys.stderr)
    raise SystemExit(22)
target.write_bytes(pathlib.Path(os.environ['BOOTSTRAP_DOWNLOAD']).read_bytes())
""")
        curl.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ.get("PATH", ""),
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
        self.assertIn("--silent", curl)
        self.assertIn("--show-error", curl)
        self.assertEqual(curl[curl.index("--proto") + 1], "=https")
        self.assertEqual(curl[curl.index("--proto-redir") + 1], "=https")
        self.assertIn("https://github.com/hbmartin/HolodeckShaderCheck/releases/download/v1.1.0/holodeck-shader-check-1.1.0.pyz", curl)
        self.assertEqual(len(list(self.cache.iterdir())), 1)

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
        for command in (["git", "init", "--quiet", str(self.root)], ["git", "-C", str(self.root), "add", "src", "tools", "tests"],
                        ["git", "-C", str(self.root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "fixture"]):
            subprocess.run(command, check=True, capture_output=True)
        self.pin = {"sourceCommit": subprocess.check_output(["git", "-C", str(self.root), "rev-parse", "HEAD"], text=True).strip()}
        self.entries = {"holodeck_shader_check/" + p.name: p.read_bytes() for p in self.package.iterdir()}
        self.entries["__main__.py"] = bootstrap.ENTRY_POINT
        self.artifact = self.root / "checker.pyz"

    def archive(self, entries=None):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.artifact, "w", compression=zipfile.ZIP_STORED) as archive:
                for name, value in (entries if entries is not None else reversed(list(self.entries.items()))):
                    archive.writestr(name, value)
        self.pin["sha256"] = hashlib.sha256(self.artifact.read_bytes()).hexdigest()

    def cli(self, source=None):
        lock = self.root / "lock.json"
        lock.write_text(json.dumps(dict(self.pin, version="1.1.0", interfaceVersion=1,
                                        repository="hbmartin/HolodeckShaderCheck")))
        return subprocess.run(
            [sys.executable, "-I", str(SCRIPT), "verify-source", "--lock", str(lock),
             "--source", str(source if source is not None else self.root), "--artifact", str(self.artifact)],
            capture_output=True, text=True, env=dict(os.environ, LC_ALL="C"),
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
                        subprocess.run(["git", "-C", str(self.root), "add", relative], check=True, capture_output=True)
                    try:
                        result = self.cli()
                        self.assertEqual(result.returncode, 2, result.stderr)
                        self.assertEqual(result.stdout, "")
                        self.assertIn("tracked changes", result.stderr)
                        self.assertIn(relative, result.stderr)
                        self.assertNotIn("Traceback", result.stderr)
                    finally:
                        subprocess.run(["git", "-C", str(self.root), "restore", "--staged", "--worktree", "--", relative],
                                       check=True, capture_output=True)

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
        lock = self.root / "lock.json"
        lock.write_text(json.dumps(dict(self.pin, version="1.1.0", interfaceVersion=1,
                                        repository="hbmartin/HolodeckShaderCheck")))
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

    def test_source_failure_is_reported_as_bootstrap_exit_two(self):
        self.archive()
        lock = self.root / "lock.json"
        lock.write_text(json.dumps(dict(self.pin, version="1.1.0", interfaceVersion=1,
                                        repository="hbmartin/HolodeckShaderCheck", sourceCommit="b" * 40)))
        with contextlib.redirect_stderr(io.StringIO()) as output:
            status = bootstrap.main(["verify-source", "--lock", str(lock), "--source", str(self.root), "--artifact", str(self.artifact)])
        self.assertEqual(status, 2)
        self.assertIn("HEAD", output.getvalue())
