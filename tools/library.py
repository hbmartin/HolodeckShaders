#!/usr/bin/env python3
"""Discover and verify authoring assets. Only catalog.py publishes app content."""
import argparse
import datetime
import json
import math
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile
import catalog

KINDS = {"shader": ("shaders", "metadata.json"), "snippet": ("snippets", "snippet.json"), "reference": ("references", "reference.json")}
IMPORT_ARTIFACTS = {".git", ".DS_Store", "__pycache__", ".idea", ".vscode", "xcuserdata"}


def path(relative):
    if not isinstance(relative, str) or pathlib.PurePosixPath(relative).is_absolute() or ".." in pathlib.PurePosixPath(relative).parts:
        raise ValueError(f"Invalid asset path: {relative}")
    value = catalog.ROOT / relative
    if not value.resolve().is_relative_to(catalog.ROOT.resolve()) or not value.is_file():
        raise ValueError(f"Missing or external asset: {relative}")
    return value


def assets(kind=None):
    result = []
    for asset_kind, (folder, filename) in KINDS.items():
        if kind and asset_kind != kind:
            continue
        for directory in sorted((catalog.ROOT / folder).iterdir()):
            if not directory.is_dir() or directory.name.startswith("."):
                continue
            file = path(f"{folder}/{directory.name}/{filename}")
            spec = catalog.read_json(file)
            if not isinstance(spec, dict) or not catalog.valid_id(spec.get("id")) or spec["id"] != file.parent.name:
                raise ValueError(f"Invalid or duplicate asset ID: {file}")
            result.append({"kind": asset_kind, "id": spec["id"], "name": spec.get("name", ""),
                           "summary": spec.get("summary", spec.get("description", "")),
                           "path": str(file.parent.relative_to(catalog.ROOT)), "specification": spec})
    return sorted(result, key=lambda item: (item["id"], item["kind"]))


def find(kind, asset_id):
    if kind not in KINDS or not catalog.valid_id(asset_id):
        raise ValueError("Invalid kind or ID")
    for item in assets(kind):
        if item["id"] == asset_id:
            return item
    raise ValueError(f"Unknown {kind}: {asset_id}")


def search(query, kind=None):
    terms = query.casefold().split()
    ranked = []
    for item in assets(kind):
        spec = item["specification"]
        symbols = spec.get("source", {}).get("symbols", [])
        tags = spec.get("tags", []) + spec.get("searchTerms", []) + spec.get("discovery", {}).get("tags", [])
        primary = " ".join([item["id"], item["name"]] + symbols).casefold()
        tagged = " ".join(tags).casefold()
        description = item["summary"].casefold()
        corpus = " ".join([primary, tagged, description])
        if all(term in corpus for term in terms):
            primary_matches = sum(term in primary for term in terms)
            tag_matches = sum(term in tagged and term not in primary for term in terms)
            ranked.append((-primary_matches, -tag_matches, item["id"], item["kind"], item))
    return [value[4] for value in sorted(ranked, key=lambda value: value[:4])]


def show(kind, asset_id):
    item = dict(find(kind, asset_id))
    readme = catalog.ROOT / item["path"] / "README.md"
    item["documentation"] = readme.read_text() if readme.is_file() else (catalog.ROOT / "docs/shader-authoring.md").read_text()
    if kind == "shader":
        item["sourcePath"] = item["path"] + "/body.metal"
        item["sourceLocations"] = [item["sourcePath"]] + [f"shared/{part}.metal" for part in item["specification"]["shared"]]
        item["examplePath"] = item["sourcePath"]
        item["example"] = path(item["examplePath"]).read_text()
    else:
        item["source"] = item["specification"].get("source", {"files": item["specification"].get("files", {})})
        item["examplePath"] = item["specification"].get("examplePath")
        item["example"] = path(item["examplePath"]).read_text() if item["examplePath"] else None
        item["sourceLocations"] = [item["source"]["path"]] if kind == "snippet" else [item["path"] + "/original/" + file for file in sorted(item["specification"]["files"])]
    return item


def validate_snippet(item):
    spec = item["specification"]
    if spec.get("schemaVersion") != 1 or spec.get("kind") not in ("shared-helper", "recipe"):
        raise ValueError(f"Invalid snippet kind/schema: {item['id']}")
    for field in ("name", "summary"):
        if not catalog.text_field(spec.get(field)):
            raise ValueError(f"Missing snippet {field}: {item['id']}")
    for field in ("tags", "searchTerms"):
        if not catalog.string_list(spec.get(field)):
            raise ValueError(f"Invalid snippet {field}: {item['id']}")
    shared = spec.get("requiredShared")
    if shared not in (["common"], ["common", "material"]):
        raise ValueError(f"Invalid snippet helpers: {item['id']}")
    source = spec.get("source")
    if not isinstance(source, dict) or not catalog.string_list(source.get("symbols")) or not source["symbols"]:
        raise ValueError(f"Missing snippet symbols: {item['id']}")
    allowed = [f"shared/{part}.metal" for part in shared] if spec["kind"] == "shared-helper" else [item["path"] + "/code.metal"]
    if source.get("path") not in allowed:
        raise ValueError(f"Invalid canonical source: {item['id']}")
    code = path(source["path"]).read_text()
    if any(symbol not in code for symbol in source["symbols"]):
        raise ValueError(f"Missing declared symbol: {item['id']}")
    if spec.get("examplePath") != item["path"] + "/example.metal":
        raise ValueError(f"Invalid example path: {item['id']}")
    path(spec["examplePath"])
    docs = path(item["path"] + "/README.md").read_text()
    for heading in ("Interface", "Coordinates", "Tuning", "Limitations", "Cost"):
        if heading not in docs:
            raise ValueError(f"Missing {heading} contract: {item['id']}")
    origin = spec.get("origin")
    if not isinstance(origin, dict) or not catalog.string_list(origin.get("shaderIDs")) or any(not catalog.text_field(origin.get(field)) for field in ("attribution", "license")):
        raise ValueError(f"Invalid snippet origin: {item['id']}")
    for shader_id in origin["shaderIDs"]:
        if not catalog.valid_id(shader_id):
            raise ValueError("Invalid origin shader ID")
        path(f"shaders/{shader_id}/body.metal")


def snippet_source(item):
    validate_snippet(item)
    spec = item["specification"]
    parts = [path(f"shared/{part}.metal").read_text() for part in spec["requiredShared"]]
    if spec["kind"] == "recipe":
        parts.append(path(spec["source"]["path"]).read_text())
    parts.extend([path(spec["examplePath"]).read_text(), path("shared/fragment.metal").read_text()])
    return "\n".join(parts)


def validate_reference(item):
    spec = item["specification"]
    if not isinstance(spec, dict) or not catalog.valid_id(item["id"]) or spec.get("id") != item["id"] or spec.get("schemaVersion") != 1 or any(not catalog.text_field(spec.get(field)) for field in ("name", "summary", "language", "adaptationNotes")):
        raise ValueError(f"Invalid reference: {item['id']}")
    for field in ("tags", "searchTerms", "requirements"):
        if not catalog.string_list(spec.get(field)):
            raise ValueError(f"Invalid reference {field}: {item['id']}")
    if not isinstance(spec.get("origin"), dict) or any(not catalog.text_field(spec["origin"].get(field)) for field in ("author", "license")):
        raise ValueError(f"Missing reference provenance: {item['id']}")
    if "importedFrom" in spec["origin"] and spec["origin"]["importedFrom"] != item["id"]:
        raise ValueError(f"Invalid reference importedFrom: {item['id']}; replace origin.importedFrom with the public reference ID")
    path(item["path"] + "/README.md")
    files = spec.get("files")
    if not isinstance(files, dict):
        raise ValueError(f"Invalid reference files: {item['id']}")
    original = catalog.ROOT / item["path"] / "original"
    actual = {str(p.relative_to(original)) for p in original.rglob("*") if p.is_file()} if original.exists() else set()
    if actual != set(files):
        raise ValueError(f"Reference file inventory changed: {item['id']}")
    for filename, sha in files.items():
        if not isinstance(sha, str) or len(sha) != 64 or catalog.digest(path(item["path"] + "/original/" + filename).read_bytes()) != sha:
            raise ValueError(f"Reference checksum mismatch: {item['id']}/{filename}")


def compile_source(source, label):
    with tempfile.TemporaryDirectory() as temp:
        file = pathlib.Path(temp) / "example.metal"
        file.write_text(source)
        for sdk in ("macosx", "appletvos"):
            subprocess.run(["xcrun", "-sdk", sdk, "metal", "-c", str(file), "-o", str(pathlib.Path(temp) / f"{sdk}.air")], check=True)
    print(f"Compiled {label} for macOS and tvOS")


def validate(compile_metal=False):
    catalog.entries()
    items = assets()
    for item in items:
        if item["kind"] == "shader":
            catalog.shader_entry(item["id"])
        elif item["kind"] == "snippet":
            source = snippet_source(item)
            if compile_metal:
                compile_source(source, item["id"])
        else:
            validate_reference(item)
    return items


def populate_template(kind, asset_id, destination):
    shutil.copytree(catalog.ROOT / "templates" / kind, destination)
    for file in destination.rglob("*"):
        if file.is_file():
            file.write_text(file.read_text().replace("__ID__", asset_id).replace("__NAME__", asset_id.replace("-", " ").title()))


def scaffold(kind, asset_id):
    if kind not in KINDS or not catalog.valid_id(asset_id):
        raise ValueError("Invalid kind or ID")
    folder, _ = KINDS[kind]
    destination = catalog.ROOT / folder / asset_id
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"Refusing to overwrite: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        stage = pathlib.Path(temp) / asset_id
        populate_template(kind, asset_id, stage)
        if destination.exists() or destination.is_symlink():
            raise ValueError(f"Refusing to overwrite: {destination}")
        stage.rename(destination)
    return destination


def import_checkout():
    command = ["git", "-C", str(catalog.ROOT)]
    try:
        checkout = pathlib.Path(subprocess.check_output(command + ["rev-parse", "--show-toplevel"], stderr=subprocess.PIPE, text=True).rstrip("\n")).resolve()
        git_dir = subprocess.check_output(command + ["rev-parse", "--absolute-git-dir"], stderr=subprocess.PIPE, text=True).rstrip("\n")
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("Reference imports require Git and a working checkout") from error
    return checkout, git_dir


def make_directories_writable(directory):
    # Work top-down so a partially copied directory is traversable before listing it.
    directory.chmod(stat.S_IMODE(directory.stat().st_mode) | stat.S_IRWXU)
    for child in directory.iterdir():
        if not child.is_symlink() and child.is_dir():
            make_directories_writable(child)


def check_import_ignored(stage_root, stage, checkout, git_dir):
    # Reuse local/global excludes, resolving a configured relative path before changing worktrees.
    excludes = subprocess.run(["git", "-C", str(checkout), "config", "--path", "--get", "core.excludesFile"], capture_output=True, text=True)
    options = []
    if excludes.returncode == 0:
        exclude_file = excludes.stdout.rstrip("\n")
        if exclude_file and not pathlib.Path(exclude_file).is_absolute():
            exclude_file = checkout / exclude_file
        options = ["-c", f"core.excludesFile={exclude_file}"]
    elif excludes.returncode != 1:
        excludes.check_returncode()
    files = sorted(p.relative_to(stage_root).as_posix() for p in stage.rglob("*") if p.is_file())
    result = subprocess.run(["git", *options, f"--git-dir={git_dir}", f"--work-tree={stage_root}",
                             "check-ignore", "--no-index", "--stdin", "-z"],
                            input=b"".join(os.fsencode(file) + b"\0" for file in files), capture_output=True, cwd=stage_root)
    if result.returncode not in (0, 1):
        result.check_returncode()
    if result.stdout:
        omitted = [os.fsdecode(file) for file in result.stdout.rstrip(b"\0").split(b"\0")]
        raise ValueError("Import contains files Git would omit:\n" + "\n".join(f"  {file} (ignored by Git)" for file in omitted)
                         + "\nPrepare a clean source or adjust ignore rules before importing")


def import_reference(asset_id, source, language):
    if not catalog.valid_id(asset_id):
        raise ValueError("Invalid kind or ID")
    source = pathlib.Path(source).expanduser().absolute()
    entries = [source, *sorted(source.rglob("*"))]
    if not source.exists() or any(p.is_symlink() for p in entries):
        raise ValueError("Import requires a local file/directory without symlinks")
    if not catalog.text_field(language, 100):
        raise ValueError("Missing source language")
    if source.is_dir() and (catalog.ROOT / "references").resolve().is_relative_to(source.resolve()):
        raise ValueError("Import source must not contain the reference destination")
    destination = catalog.ROOT / "references" / asset_id
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"Refusing to overwrite: {destination}")
    checkout, git_dir = import_checkout()
    relative = destination.resolve().relative_to(checkout)
    artifacts = []
    for entry in entries:
        if entry.name in IMPORT_ARTIFACTS:
            name = entry.relative_to(source) if source.is_dir() else pathlib.Path(source.name)
            label = (relative / "original" / name).as_posix()
            artifacts.append(f"  {label} (environment artifact: {entry.name})")
    if artifacts:
        raise ValueError("Import contains environment artifacts:\n" + "\n".join(artifacts) + "\nPrepare a clean source before importing")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage_root = pathlib.Path(tempfile.mkdtemp(prefix=".import-", dir=destination.parent))
    try:
        # Mirror the final path so anchored ignore rules never see the temporary prefix.
        stage = stage_root / relative
        stage.parent.mkdir(parents=True, exist_ok=True)
        populate_template("reference", asset_id, stage)
        ancestor = destination.parent.resolve()
        while ancestor.is_relative_to(checkout):
            ignore = ancestor / ".gitignore"
            if ignore.is_file():
                mirror = stage_root / ignore.relative_to(checkout)
                mirror.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ignore, mirror)
            if ancestor == checkout:
                break
            ancestor = ancestor.parent
        original = stage / "original"
        original.mkdir()
        if source.is_dir():
            shutil.copytree(source, original, dirs_exist_ok=True)
        else:
            shutil.copy2(source, original / source.name)
        make_directories_writable(stage_root)
        spec = catalog.read_json(stage / "reference.json")
        spec["language"] = language
        spec["origin"]["importedFrom"] = asset_id
        spec["origin"]["importedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        spec["files"] = {str(p.relative_to(original)): catalog.digest(p.read_bytes()) for p in sorted(original.rglob("*")) if p.is_file()}
        if not spec["files"]:
            raise ValueError("Import contains no files")
        catalog.write_json(stage / "reference.json", spec)
        check_import_ignored(stage_root, stage, checkout, git_dir)
        validate_reference({"id": asset_id, "path": stage.relative_to(catalog.ROOT).as_posix(), "specification": spec})
        if destination.exists() or destination.is_symlink():
            raise ValueError(f"Refusing to overwrite: {destination}")
        stage.rename(destination)
    finally:
        try:
            make_directories_writable(stage_root)
            shutil.rmtree(stage_root)
        except Exception as error:
            print(f"library: Could not remove import staging {stage_root.relative_to(catalog.ROOT)}: {error}", file=sys.stderr)
    return destination


def render(kind, asset_id, times, width=1280, height=720):
    if kind not in ("shader", "snippet"):
        raise ValueError("Only Metal shaders and snippet examples can be rendered")
    samples = [float(t) for t in times.split(",")]
    if not samples or any(not math.isfinite(t) or t < 0 for t in samples) or not 1 <= width <= 8192 or not 1 <= height <= 8192 or width * height > 16_777_216:
        raise ValueError("Invalid render settings")
    source = catalog.shader_entry(asset_id)[1] if kind == "shader" else snippet_source(find(kind, asset_id))
    output = catalog.ROOT / ".cache/library" / f"{kind}-{asset_id}"
    output.mkdir(parents=True, exist_ok=True)
    renderer = catalog.ROOT / ".cache/render-preview"
    subprocess.run(["xcrun", "swiftc", str(catalog.ROOT / "tools/render-preview.swift"), "-o", str(renderer)], check=True)
    file = output / "source.metal"
    file.write_text(source)
    for sample in samples:
        image = output / f"{width}x{height}-t{sample:g}.png"
        subprocess.run([str(renderer), str(file), str(image), "--width", str(width), "--height", str(height), "--time", str(sample)], check=True)
        print(image)
    return output


def emit(items, as_json=False):
    if as_json:
        print(json.dumps(items, indent=2, sort_keys=True))
    elif isinstance(items, list):
        for item in items:
            print(f"{item['kind']}\t{item['id']}\t{item['name']}\t{item['summary']}\t{item['path']}")
    else:
        print(json.dumps(items["specification"], indent=2, sort_keys=True))
        print(items["documentation"])
        print("Source locations: " + ", ".join(items["sourceLocations"]))
        if items["example"] is not None:
            print("Example: " + items["examplePath"])
            print(items["example"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("list", "search"):
        command = commands.add_parser(name)
        command.add_argument("--kind", choices=KINDS)
        command.add_argument("--json", action="store_true")
        if name == "search":
            command.add_argument("query")
    for name in ("show", "new", "render"):
        command = commands.add_parser(name)
        command.add_argument("kind", choices=KINDS)
        command.add_argument("id")
        if name == "show":
            command.add_argument("--json", action="store_true")
        if name == "render":
            command.add_argument("--times", default="0,3,10")
            command.add_argument("--width", type=int, default=1280)
            command.add_argument("--height", type=int, default=720)
    command = commands.add_parser("import-reference")
    command.add_argument("id")
    command.add_argument("--source", required=True)
    command.add_argument("--language", required=True)
    command = commands.add_parser("validate")
    command.add_argument("--compile", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "list": emit(assets(args.kind), args.json)
        elif args.command == "search": emit(search(args.query, args.kind), args.json)
        elif args.command == "show": emit(show(args.kind, args.id), args.json)
        elif args.command == "new": print(scaffold(args.kind, args.id))
        elif args.command == "import-reference": print(import_reference(args.id, args.source, args.language))
        elif args.command == "render": render(args.kind, args.id, args.times, args.width, args.height)
        else: print(f"Validated {len(validate(args.compile))} authoring assets")
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"library: {error}\n")


if __name__ == "__main__":
    main()
