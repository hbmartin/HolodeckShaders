#!/usr/bin/env python3
"""Prepare and verify the locked checker without importing authoring implementation."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
import zlib

try:
    import lzma
except ImportError:
    lzma = None
try:
    from compression import zstd
except ImportError:
    zstd = None


ROOT = Path(__file__).resolve().parents[1]
APPROVED_REPOSITORY = "hbmartin/HolodeckShaderCheck"
SUPPORTED_INTERFACE = 1
ENTRY_POINT = b"from holodeck_shader_check.cli import main\nraise SystemExit(main())\n"
ARCHIVE_ERRORS = (zipfile.BadZipFile, RuntimeError, zlib.error, EOFError, OSError, UnicodeDecodeError)
if lzma is not None:
    ARCHIVE_ERRORS += (lzma.LZMAError,)
if zstd is not None:
    ARCHIVE_ERRORS += (zstd.ZstdError,)


class BootstrapError(Exception):
    pass


def read_lock(path):
    return validate_lock(json.loads(Path(path).read_text(encoding="utf-8")))


def validate_lock(pin):
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
    validate_info(json.loads(result.stdout), pin)


def validate_info(info, pin):
    if not isinstance(info, dict):
        raise BootstrapError("Checker info must be a JSON object")
    if type(info.get("checkerVersion")) is not str or info["checkerVersion"] != pin["version"]:
        raise BootstrapError("Checker reported version does not match the lock")
    if type(info.get("interfaceVersion")) is not int or info["interfaceVersion"] != pin["interfaceVersion"]:
        raise BootstrapError("Checker reported interface does not match the lock")


def captured_output(result):
    lines = []
    for stream, output in (("stdout", result.stdout), ("stderr", result.stderr)):
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        if output and output.strip():
            lines.append(f"{stream}:\n{output.rstrip()}")
    return "\n".join(lines)


def native_json(tool, arguments, label):
    try:
        result = subprocess.run([str(tool), "library", *arguments], check=True, capture_output=True,
                                stdin=subprocess.DEVNULL, timeout=5)
    except (OSError, subprocess.SubprocessError) as error:
        guidance = (" Require a Holodeck build containing bd006a0 or later and its matching resource bundle."
                    if arguments[0] == "artifact-info" else "")
        raise BootstrapError(f"Native {label} failed: {error}.{guidance}") from error
    try:
        return json.loads(result.stdout)
    except ValueError as error:
        raise BootstrapError(f"Native {label} returned invalid JSON: {error}\n{captured_output(result)}") from error


def verify_native(pin, tool, python):
    for label, path in (("--tool", tool), ("--python", python)):
        if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
            raise BootstrapError(f"{label} requires an absolute executable path: {path}")
    try:
        identity = validate_lock(native_json(tool, ["artifact-info", "--json"], "artifact identity check"))
    except BootstrapError as error:
        raise BootstrapError(f"Cannot verify native checker identity: {error}") from error
    mismatches = [f"{field}: expected {expected!r}, got {identity[field]!r}"
                  for field, expected in pin.items() if identity[field] != expected]
    if mismatches:
        raise BootstrapError("Native checker identity differs from the library lock:\n" + "\n".join(mismatches))
    validate_info(native_json(tool, ["info", "--json", "--python", str(python)], "checker info check"), pin)


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
            ["curl", "--no-progress-meter", "--fail", "--location", "--proto", "=https", "--proto-redir", "=https",
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


def source_git(source, *arguments, input=None):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_NO_REPLACE_OBJECTS="1", GIT_OPTIONAL_LOCKS="0",
                       GIT_CEILING_DIRECTORIES=str(source.parent))
    return subprocess.run(
        ["git", "-C", str(source), *arguments], env=environment,
        check=True, capture_output=True, input=input,
        stdin=subprocess.DEVNULL if input is None else None, timeout=10,
    ).stdout


def committed_files(source):
    entries = {}
    for entry in source_git(source, "ls-tree", "-r", "-z", "--full-tree", "HEAD").split(b"\0"):
        if not entry:
            continue
        header, name = entry.split(b"\t", 1)
        mode, kind, object_id = header.split()
        relative = os.fsdecode(name)
        if kind != b"blob" or mode not in (b"100644", b"100755", b"120000"):
            raise BootstrapError(f"Unsupported checker source entry: {relative}")
        entries[relative] = (mode, object_id)
    object_ids = list(dict.fromkeys(object_id for _, object_id in entries.values()))
    stream = io.BytesIO(source_git(source, "cat-file", "--batch", input=b"\n".join(object_ids) + b"\n"))
    blobs = {}
    for object_id in object_ids:
        header = stream.readline().split()
        if len(header) != 3 or header[:2] != [object_id, b"blob"] or not header[2].isdigit():
            raise BootstrapError("Cannot read checker source blobs from Git")
        size = int(header[2])
        content = stream.read(size)
        if len(content) != size or stream.read(1) != b"\n":
            raise BootstrapError("Truncated checker source blob output from Git")
        blobs[object_id] = content
    if stream.read():
        raise BootstrapError("Unexpected checker source blob output from Git")
    return {name: (mode, blobs[object_id]) for name, (mode, object_id) in entries.items()}


def matches_text_or_bytes(actual, expected, relative):
    if actual == expected:
        return True
    # Packaged Python remains byte-exact. Other UTF-8 text may differ only in LF/CRLF.
    if relative.startswith("src/") and relative.endswith(".py"):
        return False
    if b"\0" in actual or b"\0" in expected:
        return False
    try:
        actual.decode("utf-8")
        expected.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return actual.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n")


def verify_checkout(pin, source):
    checkout = Path(os.fsdecode(source_git(source, "rev-parse", "--show-toplevel").rstrip(b"\n"))).resolve()
    if checkout != source:
        raise BootstrapError("Checker source must be the Git checkout root")
    head = source_git(source, "rev-parse", "--verify", "HEAD^{commit}").decode("ascii").strip()
    if head != pin["sourceCommit"]:
        raise BootstrapError("Checker source HEAD does not match the locked sourceCommit")
    staged = source_git(source, "diff", "--cached", "--no-ext-diff", "--no-textconv",
                        "--name-only", "-z", "HEAD", "--")
    if staged:
        names = "\n".join(os.fsdecode(name) for name in staged.split(b"\0") if name)
        raise BootstrapError(f"Checker source has tracked changes in the index:\n{names}")
    for name in ("src", "tests", "tools"):
        folder = source / name
        if folder.is_symlink() or not folder.is_dir():
            raise BootstrapError(f"Checker source requires a real {name}/ directory: {folder}")

    tracked = committed_files(source)
    directories = {parent for relative in tracked for parent in (source / relative).parents
                   if source in parent.parents}
    invalid_directories = {parent for parent in directories if parent.is_symlink() or not parent.is_dir()}
    file_mode = source_git(source, "config", "--type=bool", "--default=true", "--get", "core.fileMode").strip() == b"true"
    changed = []
    for relative, (mode, expected) in tracked.items():
        path = source / relative
        if invalid_directories.intersection(path.parents):
            changed.append(relative)
            continue
        try:
            info = path.lstat()
        except FileNotFoundError:
            changed.append(relative)
            continue
        if mode == b"120000":
            valid_type = stat.S_ISLNK(info.st_mode)
            matches = valid_type and os.fsencode(os.readlink(path)) == expected
        else:
            valid_type = stat.S_ISREG(info.st_mode)
            valid_mode = not file_mode or bool(info.st_mode & stat.S_IXUSR) == (mode == b"100755")
            matches = valid_type and valid_mode and matches_text_or_bytes(path.read_bytes(), expected, relative)
        if not matches:
            changed.append(relative)
    if changed:
        raise BootstrapError("Checker source has tracked changes:\n" + "\n".join(sorted(changed)))

    unexpected = []
    pending = [source / name for name in ("src", "tests", "tools")]
    while pending:
        folder = pending.pop()
        for path in folder.iterdir():
            relative = path.relative_to(source).as_posix()
            if path.is_dir() and not path.is_symlink():
                if path in directories:
                    pending.append(path)
                else:
                    unexpected.append(relative + "/")
            elif relative not in tracked:
                if path.name != ".DS_Store" or not stat.S_ISREG(path.lstat().st_mode):
                    unexpected.append(relative)
    if unexpected:
        raise BootstrapError("Unexpected checker execution files (including ignored files):\n" +
                             "\n".join(sorted(unexpected)) +
                             "\nUse a fresh checkout or remove these files; keep scratch storage outside src/, tests/ and tools/.")


def verify_source(pin, source, artifact):
    source = Path(source).resolve()
    verify_checkout(pin, source)
    verify_hash(artifact, pin)
    package = source / "src"
    expected = {path.relative_to(package).as_posix(): path.read_bytes()
                for path in package.rglob("*.py") if path.is_file()}
    if not expected or "holodeck_shader_check/__init__.py" not in expected:
        raise BootstrapError("Checker source package is missing")
    expected["__main__.py"] = ENTRY_POINT
    try:
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
    except ARCHIVE_ERRORS as error:
        raise BootstrapError(f"Cannot read checker archive {artifact}: {error}") from error


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for command in ("prepare", "run", "verify-source", "verify-native"):
        child = commands.add_parser(command)
        child.add_argument("--lock", type=Path, default=ROOT / "shader_checker.lock.json")
        if command in ("prepare", "run"):
            child.add_argument("--cache-dir", type=Path, default=ROOT / ".cache/checker")
        if command == "prepare":
            child.add_argument("--github-output", type=Path)
        elif command == "run":
            child.add_argument("arguments", nargs=argparse.REMAINDER, help="Checker arguments after --")
        elif command == "verify-source":
            child.add_argument("--source", required=True, type=Path)
            child.add_argument("--artifact", required=True, type=Path)
        else:
            child.add_argument("--tool", required=True, type=Path)
            child.add_argument("--python", type=Path, default=Path("/usr/bin/python3"))
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
        if args.command == "verify-native":
            verify_native(pin, args.tool, args.python)
            return 0
        metadata = prepare(pin, args.cache_dir)
        if args.command == "prepare":
            if args.github_output:
                github_outputs(args.github_output, metadata)
            print(json.dumps(metadata))
            return 0
        os.execv(sys.executable, [sys.executable, "-I", metadata["artifactPath"], *checker_args])
    except (BootstrapError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"checker-bootstrap: {error}", file=sys.stderr)
        cause = error
        while cause is not None and not isinstance(cause, (subprocess.CalledProcessError, subprocess.TimeoutExpired)):
            cause = cause.__cause__
        if cause is not None:
            details = captured_output(cause)
            if details:
                print(details, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
