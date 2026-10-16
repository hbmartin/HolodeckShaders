#!/usr/bin/env python3
"""Prepare the locked checker without importing shader-authoring implementation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
APPROVED_REPOSITORY = "hbmartin/HolodeckShaderCheck"
SUPPORTED_INTERFACE = 1
ENTRY_POINT = b"from holodeck_shader_check.cli import main\nraise SystemExit(main())\n"


class BootstrapError(Exception):
    pass


def read_lock(path):
    pin = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(pin, dict):
        raise BootstrapError("Checker lock must be a JSON object")
    patterns = {
        "version": r"1\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)",
        "sourceCommit": r"[0-9a-f]{40}",
        "sha256": r"[0-9a-f]{64}",
    }
    for field, pattern in patterns.items():
        value = pin.get(field)
        if type(value) is not str or not re.fullmatch(pattern, value):
            raise BootstrapError(f"Invalid checker lock field: {field}")
    if type(pin.get("repository")) is not str or pin["repository"] != APPROVED_REPOSITORY:
        raise BootstrapError("Checker lock repository is not approved")
    if type(pin.get("interfaceVersion")) is not int or pin["interfaceVersion"] != SUPPORTED_INTERFACE:
        raise BootstrapError("Checker lock interfaceVersion is unsupported or not an integer")
    return {field: pin[field] for field in (*patterns, "repository", "interfaceVersion")}


def verify_hash(artifact, pin):
    if hashlib.sha256(Path(artifact).read_bytes()).hexdigest() != pin["sha256"]:
        raise BootstrapError("Checker artifact SHA-256 does not match the lock")


def verify_info(artifact, pin):
    result = subprocess.run(
        [sys.executable, "-I", str(artifact), "info", "--json"],
        check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=5,
    )
    info = json.loads(result.stdout)
    if not isinstance(info, dict):
        raise BootstrapError("Checker info must be a JSON object")
    if type(info.get("checkerVersion")) is not str or info["checkerVersion"] != pin["version"]:
        raise BootstrapError("Checker reported version does not match the lock")
    if type(info.get("interfaceVersion")) is not int or info["interfaceVersion"] != pin["interfaceVersion"]:
        raise BootstrapError("Checker reported interface does not match the lock")


def prepare(pin, cache):
    cache = Path(cache).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    name = f"holodeck-shader-check-{pin['version']}.pyz"
    artifact = cache / name
    url = f"https://github.com/{pin['repository']}/releases/download/v{pin['version']}/{name}"
    descriptor, filename = tempfile.mkstemp(prefix=".checker-download-", suffix=".pyz", dir=cache)
    os.close(descriptor)
    temporary = Path(filename)
    try:
        subprocess.run(
            ["curl", "--fail", "--location", "--proto", "=https", "--proto-redir", "=https",
             "--tlsv1.2", "--retry", "3", "--connect-timeout", "15", "--max-time", "120",
             "--output", str(temporary), url],
            check=True, stdin=subprocess.DEVNULL, timeout=540,
        )
        verify_hash(temporary, pin)
        verify_info(temporary, pin)
        os.replace(temporary, artifact)
    finally:
        temporary.unlink(missing_ok=True)
    return dict(pin, artifactPath=str(artifact))


def github_outputs(path, metadata):
    if any("\n" in str(value) or "\r" in str(value) for value in metadata.values()):
        raise BootstrapError("Checker metadata cannot contain newlines in GitHub outputs")
    with Path(path).open("a", encoding="utf-8") as output:
        for key, value in metadata.items():
            print(f"{key}={value}", file=output)


def verify_source(pin, source, artifact):
    source = Path(source).resolve()
    head = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "--verify", "HEAD^{commit}"],
        check=True, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=10,
    ).stdout.strip()
    if head != pin["sourceCommit"]:
        raise BootstrapError("Checker source HEAD does not match the locked sourceCommit")
    verify_hash(artifact, pin)
    package = source / "src"
    expected = {path.relative_to(package).as_posix(): path.read_bytes()
                for path in package.rglob("*.py") if path.is_file()}
    if not expected or "holodeck_shader_check/__init__.py" not in expected:
        raise BootstrapError("Checker source package is missing")
    expected["__main__.py"] = ENTRY_POINT
    with zipfile.ZipFile(artifact) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise BootstrapError("Checker archive contains duplicate entries")
        if set(names) != set(expected):
            missing = sorted(set(expected) - set(names))
            extra = sorted(set(names) - set(expected))
            raise BootstrapError(f"Checker archive inventory differs from source: missing={missing}, extra={extra}")
        for name in names:
            if archive.read(name) != expected[name]:
                raise BootstrapError(f"Checker archive bytes differ from source: {name}")


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for command in ("prepare", "run", "verify-source"):
        child = commands.add_parser(command)
        child.add_argument("--lock", type=Path, default=ROOT / "shader_checker.lock.json")
        if command != "verify-source":
            child.add_argument("--cache-dir", type=Path, default=ROOT / ".cache/checker")
        if command == "prepare":
            child.add_argument("--github-output", type=Path)
        elif command == "run":
            child.add_argument("arguments", nargs=argparse.REMAINDER, help="Checker arguments after --")
        else:
            child.add_argument("--source", required=True, type=Path)
            child.add_argument("--artifact", required=True, type=Path)
    return result


def main(arguments=None):
    args = parser().parse_args(arguments)
    try:
        if args.command == "run":
            checker_args = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
            if not checker_args:
                raise BootstrapError("Pass checker arguments after run --")
        pin = read_lock(args.lock)
        if args.command == "verify-source":
            verify_source(pin, args.source, args.artifact)
            return 0
        metadata = prepare(pin, args.cache_dir)
        if args.command == "prepare":
            if args.github_output:
                github_outputs(args.github_output, metadata)
            print(json.dumps(metadata))
            return 0
        os.execv(sys.executable, [sys.executable, "-I", metadata["artifactPath"], *checker_args])
    except (BootstrapError, OSError, ValueError, subprocess.SubprocessError, zipfile.BadZipFile) as error:
        print(f"checker-bootstrap: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
