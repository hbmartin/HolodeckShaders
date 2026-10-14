import os
import subprocess
import unittest
from unittest.mock import patch

import shader_tool


class ShaderToolResolutionTests(unittest.TestCase):
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
