"""Resolve the installed Holodeck GPU CLI. Static authoring needs no CLI."""
import os
import re
import shutil
import subprocess

INSTALL = "Build holodeck-shader-tool from HolodeckCore and install it on PATH, or set HOLODECK_SHADER_TOOL to its executable path."
VERSION_TIMEOUT_SECONDS = 5


def command(*arguments):
    override = os.environ.get("HOLODECK_SHADER_TOOL")
    executable = override if override is not None else shutil.which("holodeck-shader-tool")
    if not executable:
        raise ValueError("Holodeck shader tool is unavailable. " + INSTALL)
    try:
        result = subprocess.run([executable, "--version"], check=True, capture_output=True, text=True,
                                timeout=VERSION_TIMEOUT_SECONDS, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise ValueError("Cannot run Holodeck shader tool. " + INSTALL) from error
    if re.fullmatch(r"holodeck-shader-tool 1\.\d+\.\d+", result.stdout.strip()) is None:
        raise ValueError("Holodeck shader tool requires major version 1. " + INSTALL)
    return [executable, *arguments]
