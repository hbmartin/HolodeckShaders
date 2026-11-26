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
        self.env.pop(bootstrap.NATIVE_TIMEOUT_ENV, None)

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

    def main_result(self, arguments=None):
        self.config_file.write_text(json.dumps(self.config))
        args = arguments if arguments is not None else self.arguments()
        with mock.patch.dict(os.environ, self.env, clear=True), \
                contextlib.redirect_stdout(io.StringIO()) as stdout, \
                contextlib.redirect_stderr(io.StringIO()) as stderr:
            status = bootstrap.main(args)
        return subprocess.CompletedProcess(args, status, stdout.getvalue(), stderr.getvalue())

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

    def test_default_interpreter_is_forwarded_without_requiring_it_on_the_test_host(self):
        responses = [subprocess.CompletedProcess([], 0, json.dumps(self.pin).encode(), b""),
                     subprocess.CompletedProcess([], 0, json.dumps(self.config["info"]).encode(), b"")]
        with mock.patch.object(Path, "is_file", return_value=True), mock.patch.object(os, "access", return_value=True), \
                mock.patch.object(bootstrap.subprocess, "run", side_effect=responses) as run:
            result = self.main_result(self.arguments(default_python=True))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(run.call_args_list[-1].args[0][-1], "/usr/bin/python3")

    def test_absent_default_interpreter_fails_without_falling_back(self):
        original_is_file = Path.is_file

        def absent_system_python(path):
            return False if path == Path("/usr/bin/python3") else original_is_file(path)

        with mock.patch.object(Path, "is_file", new=absent_system_python), \
                mock.patch.object(bootstrap.subprocess, "run", side_effect=AssertionError("No native launch")):
            result = self.main_result(self.arguments(default_python=True))
        self.assert_failure(result, "--python requires an absolute executable path: /usr/bin/python3")

    def test_each_identity_field_is_required_and_strictly_typed(self):
        alternatives = dict(repository="other/repository", version="1.1.2", interfaceVersion=2,
                            sourceCommit="c" * 40, sha256="d" * 64)
        for field, other in alternatives.items():
            for value in (other, None, True, 1.0):
                with self.subTest(field=field, value=value):
                    self.config["identity"] = dict(self.pin, **{field: value})
                    result = self.cli()
                    self.assert_failure(result, field)
                    self.assertIn("expected", result.stderr)
                    self.assertIn("got", result.stderr)
                    self.assertNotIn("Checker lock", result.stderr)
            with self.subTest(missing=field):
                self.config["identity"] = {key: value for key, value in self.pin.items() if key != field}
                result = self.cli()
                self.assert_failure(result, field)
                self.assertIn("got <missing>", result.stderr)
                self.assertIn("Native artifact identity", result.stderr)

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
                result = self.cli()
                self.assert_failure(result, "Native checker info field")
                self.assertIn("expected", result.stderr)
                self.assertIn("got", result.stderr)

    def test_old_native_tool_has_update_guidance_and_keeps_diagnostics(self):
        self.config.update(artifact_status=2, artifact_stdout="partial native output",
                           artifact_stderr="argparse: invalid choice: artifact-info")
        result = self.cli()
        self.assert_failure(result, "bd006a0")
        self.assertIn("resource bundle", result.stderr)
        self.assertIn("stdout:\npartial native output", result.stderr)
        self.assertIn("stderr:\nargparse: invalid choice", result.stderr)
        self.assertNotIn("status 2..", result.stderr)

    def test_top_level_usage_identifies_the_legacy_native_tool(self):
        usage = ("Usage: holodeck-shader-tool --version | {library}render SOURCE OUTPUT "
                 "[--width N --height N --time SECONDS] | probe render|compute SOURCE SAMPLES_JSON RESULT_JSON")
        for library in ("", "library info|artifact-info|validate|assemble|render ... [--python ABSOLUTE_PATH] | "):
            with self.subTest(library=library):
                response = usage.format(library=library)
                self.config.update(artifact_status=1, artifact_stdout="", artifact_stderr=response)
                result = self.cli()
                self.assert_failure(result, "exit status 1")
                self.assertIn(response, result.stderr)
                self.assertEqual("bd006a0" in result.stderr, not library)

    def test_nonjson_success_has_conditional_compatibility_guidance(self):
        self.config["artifact_stdout"] = "usage: old native tool"
        result = self.cli()
        self.assert_failure(result, "invalid JSON")
        self.assertIn("If this build does not support", result.stderr)
        self.assertIn("bd006a0", result.stderr)
        self.assertIn("stdout:\nusage: old native tool", result.stderr)

    def test_unrelated_failures_and_crashes_do_not_get_upgrade_advice(self):
        self.config.update(artifact_status=23, artifact_stderr="checksum read failure")
        result = self.cli()
        self.assert_failure(result, "exit status 23")
        self.assertIn("checksum read failure", result.stderr)
        self.assertNotIn("bd006a0", result.stderr)
        for error, message in ((subprocess.CalledProcessError(-11, [str(self.tool)],
                                                            output=b"artifact-info invalid choice", stderr=b"crash"), "failed"),
                               (OSError("Exec format error"), "could not be launched")):
            with self.subTest(error=type(error).__name__):
                with mock.patch.object(bootstrap.subprocess, "run", side_effect=error):
                    result = self.main_result()
                self.assert_failure(result, message)
                self.assertNotIn("bd006a0", result.stderr)

    def test_timeout_override_applies_to_both_native_calls(self):
        for value in ("0.125", "2000000"):
            with self.subTest(timeout=value):
                self.env[bootstrap.NATIVE_TIMEOUT_ENV] = value
                responses = [subprocess.CompletedProcess([], 0, json.dumps(self.pin).encode(), b""),
                             subprocess.CompletedProcess([], 0, json.dumps(self.config["info"]).encode(), b"")]
                with mock.patch.object(bootstrap.subprocess, "run", side_effect=responses) as run:
                    result = self.main_result()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual([call.kwargs["timeout"] for call in run.call_args_list], [float(value)] * 2)

    def test_invalid_timeout_overrides_fail_before_launch(self):
        for value in ("", "0", "-1", "nan", "inf", "-inf", "1e999", "not a number", "1e9", "2000000.1"):
            with self.subTest(timeout=value):
                self.env[bootstrap.NATIVE_TIMEOUT_ENV] = value
                result = self.cli()
                self.assert_failure(result, f"{bootstrap.NATIVE_TIMEOUT_ENV} must be a positive finite number "
                                            f"of seconds no greater than 2,000,000 (got {value!r})")
                self.assertFalse(self.log.exists())

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
        for label, seconds in (("artifact", 30.0), ("info", 100000.5)):
            with self.subTest(command=label, seconds=seconds):
                if label == "info":
                    self.env[bootstrap.NATIVE_TIMEOUT_ENV] = str(seconds)
                error = subprocess.TimeoutExpired([str(self.tool), "library", label], seconds,
                                                   output=b"partial output\xff\n", stderr=b"partial error\xff\n")
                responses = [error] if label == "artifact" else [
                    subprocess.CompletedProcess([], 0, json.dumps(self.pin).encode(), b""), error]
                with mock.patch.object(bootstrap.subprocess, "run", side_effect=responses) as run:
                    result = self.main_result()
                self.assert_failure(result, f"timed out after {seconds} seconds")
                self.assertIn(str(self.tool), result.stderr)
                self.assertIn("stdout:\npartial output\ufffd", result.stderr)
                self.assertIn("stderr:\npartial error\ufffd", result.stderr)
                self.assertNotIn("bd006a0", result.stderr)
                for call in run.call_args_list:
                    self.assertEqual(call.kwargs["stdin"], subprocess.DEVNULL)
                    self.assertEqual(call.kwargs["timeout"], seconds)

    def test_preflight_never_prepares_or_downloads_an_artifact(self):
        responses = [subprocess.CompletedProcess([], 0, json.dumps(self.pin).encode(), b""),
                     subprocess.CompletedProcess([], 0, json.dumps(self.config["info"]).encode(), b"")]
        with mock.patch.object(bootstrap.subprocess, "run", side_effect=responses), \
                mock.patch.object(bootstrap, "prepare", side_effect=AssertionError("No preparation during native preflight")):
            result = self.main_result()
        self.assertEqual(result.returncode, 0, result.stderr)
