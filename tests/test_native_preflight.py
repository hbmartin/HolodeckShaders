import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "tools/checker_bootstrap.py"
spec = importlib.util.spec_from_file_location("native_bootstrap", SCRIPT)
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class NativePreflightTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="native checker ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.pin = dict(version="1.1.1", interfaceVersion=1, repository="hbmartin/HolodeckShaderCheck",
                        sourceCommit="a" * 40, sha256="b" * 64)
        self.lock = self.root / "library lock.json"
        self.lock.write_text(json.dumps(self.pin))
        self.config_file = self.root / "responses.json"
        self.log = self.root / "arguments.jsonl"
        self.python = self.root / "selected python"
        self.python.symlink_to(sys.executable)
        self.tool = self.root / "native tool"
        self.tool.write_text(f"#!{sys.executable}\n" + r'''
import json, os, pathlib, sys
with pathlib.Path(os.environ['NATIVE_LOG']).open('a') as stream:
    stream.write(json.dumps(sys.argv[1:]) + '\n')
config = json.loads(pathlib.Path(os.environ['NATIVE_CONFIG']).read_text())
if sys.argv[1:] == ['library', 'artifact-info', '--json']:
    label = 'artifact'
    value = config['identity']
else:
    assert sys.argv[1:4] == ['library', 'info', '--json'], sys.argv
    assert sys.argv[4] == '--python' and len(sys.argv) == 6, sys.argv
    label = 'info'
    value = config['info']
print(config.get(label + '_stdout', json.dumps(value)))
if config.get(label + '_stderr'):
    print(config[label + '_stderr'], file=sys.stderr)
raise SystemExit(config.get(label + '_status', 0))
''')
        self.tool.chmod(0o755)
        self.config = dict(identity=dict(self.pin), info=dict(checkerVersion="1.1.1", interfaceVersion=1))
        self.env = dict(os.environ, NATIVE_LOG=str(self.log), NATIVE_CONFIG=str(self.config_file))

    def arguments(self, tool=None, python=None, default_python=False):
        args = ["verify-native", "--lock", str(self.lock), "--tool", str(tool if tool is not None else self.tool)]
        if not default_python:
            args += ["--python", str(python if python is not None else self.python)]
        return args

    def cli(self, **kwargs):
        self.config_file.write_text(json.dumps(self.config))
        return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *self.arguments(**kwargs)],
                              env=self.env, cwd=self.root, capture_output=True, text=True)

    def assert_failure(self, result, message):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn(message, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_semantic_identity_and_exact_interpreter_forwarding(self):
        self.config["identity"] = dict(reversed(list(self.pin.items())), additional="supported")
        self.config["artifact_stdout"] = json.dumps(self.config["identity"]).replace("/", r"\/")
        self.config["info"]["additional"] = "supported"
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")
        commands = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(commands, [["library", "artifact-info", "--json"],
                                    ["library", "info", "--json", "--python", str(self.python)]])

    def test_default_interpreter_matches_native_default(self):
        args = bootstrap.parser().parse_args(self.arguments(default_python=True))
        self.assertEqual(args.python, Path("/usr/bin/python3"))
        result = self.cli(default_python=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(commands[-1][-1], "/usr/bin/python3")

    def test_each_identity_field_is_required_and_strictly_typed(self):
        alternatives = dict(repository="other/repository", version="1.1.2", interfaceVersion=2,
                            sourceCommit="c" * 40, sha256="d" * 64)
        for field, other in alternatives.items():
            for value in (other, None, True, 1.0):
                with self.subTest(field=field, value=value):
                    self.config["identity"] = dict(self.pin, **{field: value})
                    self.assert_failure(self.cli(), field)
            with self.subTest(missing=field):
                self.config["identity"] = {key: value for key, value in self.pin.items() if key != field}
                self.assert_failure(self.cli(), field)

    def test_nonobject_and_malformed_native_json_fail(self):
        for label in ("artifact", "info"):
            for raw in ("[]", "null", "not JSON"):
                with self.subTest(command=label, raw=raw):
                    self.config[label + "_stdout"] = raw
                    self.assert_failure(self.cli(), "JSON")
            self.config.pop(label + "_stdout")

    def test_info_version_and_interface_must_match(self):
        for info in (dict(checkerVersion="1.1.2", interfaceVersion=1),
                     dict(checkerVersion="1.1.1", interfaceVersion=True),
                     dict(checkerVersion="1.1.1", interfaceVersion=1.0)):
            with self.subTest(info=info):
                self.config["info"] = info
                self.assert_failure(self.cli(), "does not match the lock")

    def test_old_native_tool_has_update_guidance_and_keeps_diagnostics(self):
        self.config.update(artifact_status=2, artifact_stdout="partial native output",
                           artifact_stderr="argparse: invalid choice: artifact-info")
        result = self.cli()
        self.assert_failure(result, "bd006a0")
        self.assertIn("resource bundle", result.stderr)
        self.assertIn("stdout:\npartial native output", result.stderr)
        self.assertIn("stderr:\nargparse: invalid choice", result.stderr)

    def test_failed_info_keeps_its_command_and_captured_output(self):
        self.config.update(info_status=23, info_stdout="partial info", info_stderr="interpreter failure")
        result = self.cli()
        self.assert_failure(result, "checker info check")
        self.assertIn("exit status 23", result.stderr)
        self.assertIn("stdout:\npartial info", result.stderr)
        self.assertIn("stderr:\ninterpreter failure", result.stderr)

    def test_paths_must_be_absolute_and_executable(self):
        invalid_paths = (Path("relative"), self.root / "absent", self.config_file)
        self.config_file.write_text("{}")
        for option in ("tool", "python"):
            for path in invalid_paths:
                with self.subTest(option=option, path=path):
                    self.assert_failure(self.cli(**{option: path}), "--" + option + " requires an absolute executable path")
        self.assertFalse(self.log.exists())

    def test_timeouts_disconnect_stdin_and_keep_partial_output(self):
        for label in ("artifact", "info"):
            with self.subTest(command=label):
                error = subprocess.TimeoutExpired([str(self.tool), "library", label], 5,
                                                   output=b"partial output\xff\n", stderr=b"partial error\xff\n")
                responses = [error] if label == "artifact" else [
                    subprocess.CompletedProcess([], 0, json.dumps(self.pin).encode(), b""), error]
                with mock.patch.object(bootstrap.subprocess, "run", side_effect=responses) as run, \
                        contextlib.redirect_stdout(io.StringIO()) as stdout, \
                        contextlib.redirect_stderr(io.StringIO()) as stderr:
                    status = bootstrap.main(self.arguments())
                self.assertEqual(status, 2)
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn("timed out after 5 seconds", stderr.getvalue())
                self.assertIn("stdout:\npartial output\ufffd", stderr.getvalue())
                self.assertIn("stderr:\npartial error\ufffd", stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())
                for call in run.call_args_list:
                    self.assertEqual(call.kwargs["stdin"], subprocess.DEVNULL)
                    self.assertEqual(call.kwargs["timeout"], 5)

    def test_preflight_never_prepares_or_downloads_an_artifact(self):
        responses = [subprocess.CompletedProcess([], 0, json.dumps(self.pin).encode(), b""),
                     subprocess.CompletedProcess([], 0, json.dumps(self.config["info"]).encode(), b"")]
        with mock.patch.object(bootstrap.subprocess, "run", side_effect=responses), \
                mock.patch.object(bootstrap, "prepare", side_effect=AssertionError("No preparation during native preflight")):
            self.assertEqual(bootstrap.main(self.arguments()), 0)
