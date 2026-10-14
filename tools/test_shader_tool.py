import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import shader_tool


class ShaderToolResolutionTests(unittest.TestCase):
    def run_fake_tool(self, body):
        with tempfile.TemporaryDirectory() as temp:
            tool = pathlib.Path(temp) / "fake-tool"
            tool.write_text(f"#!{sys.executable}\n" + body, encoding="utf-8")
            tool.chmod(0o700)
            driver = """
import shader_tool
shader_tool.VERSION_TIMEOUT_SECONDS = 0.25
try:
    shader_tool.command("render")
except ValueError as error:
    print(type(error.__cause__).__name__)
    print(error)
    raise SystemExit(1)
print("OK")
"""
            env = dict(os.environ, HOLODECK_SHADER_TOOL=str(tool), PYTHONPATH=str(pathlib.Path(__file__).resolve().parent))
            # Keep the parent's pipe open: inherited stdin must not look like EOF.
            process = subprocess.Popen([sys.executable, "-c", driver], env=env, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                self.fail("Version resolution exceeded its bounded subprocess backstop")
            stdout, stderr = process.communicate()
            return process.returncode, stdout.decode(), stderr.decode()

    @unittest.skipUnless(os.name == "posix", "Executable fixtures require POSIX shebangs")
    def test_hanging_version_probe_reports_installation_error(self):
        code, stdout, stderr = self.run_fake_tool("import time\ntime.sleep(30)\n")
        self.assertEqual(code, 1, stderr)
        self.assertIn("TimeoutExpired", stdout)
        self.assertIn(shader_tool.INSTALL, stdout)

    @unittest.skipUnless(os.name == "posix", "Executable fixtures require POSIX shebangs")
    def test_version_probe_disconnects_inherited_stdin(self):
        code, stdout, stderr = self.run_fake_tool('import sys\nassert sys.stdin.read() == ""\nprint("holodeck-shader-tool 1.0.0")\n')
        self.assertEqual(code, 0, stdout + stderr)
        self.assertEqual(stdout.strip(), "OK")

    def test_empty_explicit_override_does_not_fall_back_to_path(self):
        with patch.dict(os.environ, {"HOLODECK_SHADER_TOOL": ""}), patch.object(shader_tool.shutil, "which") as which:
            with self.assertRaisesRegex(ValueError, "unavailable"):
                shader_tool.command("render")
            which.assert_not_called()

    def test_override_is_used_without_path_fallback(self):
        version = subprocess.CompletedProcess([], 0, "holodeck-shader-tool 1.0.0\n", "")
        with patch.dict(os.environ, {"HOLODECK_SHADER_TOOL": "/explicit/tool"}), \
             patch.object(shader_tool.shutil, "which") as which, \
             patch.object(shader_tool.subprocess, "run", return_value=version) as run:
            self.assertEqual(shader_tool.command("probe"), ["/explicit/tool", "probe"])
            which.assert_not_called()
            self.assertEqual(run.call_args.args[0], ["/explicit/tool", "--version"])

    def test_missing_invalid_and_incompatible_tools_report_installation(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(shader_tool.shutil, "which", return_value=None):
            with self.assertRaisesRegex(ValueError, "install"): shader_tool.command("render")
        with patch.dict(os.environ, {"HOLODECK_SHADER_TOOL": "/invalid/tool"}), \
             patch.object(shader_tool.shutil, "which") as which, \
             patch.object(shader_tool.subprocess, "run", side_effect=FileNotFoundError):
            with self.assertRaisesRegex(ValueError, "install"): shader_tool.command("render")
            which.assert_not_called()
        for output in ("holodeck-shader-tool 2.0.0", "unexpected output"):
            with patch.dict(os.environ, {}, clear=True), patch.object(shader_tool.shutil, "which", return_value="/tool"), \
                 patch.object(shader_tool.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, output, "")):
                with self.assertRaisesRegex(ValueError, "major version 1"): shader_tool.command("render")
