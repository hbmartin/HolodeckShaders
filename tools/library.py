#!/usr/bin/env python3
"""Discover and verify authoring assets. Holodeck loads the indexed shader sources."""
import argparse
import json
import math
import pathlib
import shutil
import subprocess
import tempfile
import authoring
import shader_tool

KINDS = {"shader": ("shaders", "metadata.json"), "snippet": ("snippets", "snippet.json"), "reference": ("references", "reference.json")}


def path(relative):
    if not isinstance(relative, str) or pathlib.PurePosixPath(relative).is_absolute() or ".." in pathlib.PurePosixPath(relative).parts:
        raise ValueError(f"Invalid asset path: {relative}")
    value = authoring.ROOT / relative
    if not value.resolve().is_relative_to(authoring.ROOT.resolve()) or not value.is_file():
        raise ValueError(f"Missing or external asset: {relative}")
    return value


def assets(kind=None, *, shader_metadata=None):
    result = []
    for asset_kind, (folder, filename) in KINDS.items():
        if kind and asset_kind != kind:
            continue
        for directory in sorted((authoring.ROOT / folder).iterdir()):
            if not directory.is_dir() or directory.name.startswith("."):
                continue
            file = path(f"{folder}/{directory.name}/{filename}")
            spec = shader_metadata.get(directory.name) if asset_kind == "shader" and shader_metadata is not None else None
            if spec is None:
                spec = authoring.read_json(file)
            if not isinstance(spec, dict) or not authoring.valid_id(spec.get("id")) or spec["id"] != file.parent.name:
                raise ValueError(f"Invalid or duplicate asset ID: {file}")
            result.append({"kind": asset_kind, "id": spec["id"], "name": spec.get("name", ""),
                           "summary": spec.get("summary", spec.get("description", "")),
                           "path": str(file.parent.relative_to(authoring.ROOT)), "specification": spec})
    return sorted(result, key=lambda item: (item["id"], item["kind"]))


def find(kind, asset_id):
    if kind not in KINDS or not authoring.valid_id(asset_id):
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
    readme = authoring.ROOT / item["path"] / "README.md"
    item["documentation"] = readme.read_text() if readme.is_file() else (authoring.ROOT / "docs/shader-authoring.md").read_text()
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
        if not authoring.text_field(spec.get(field)):
            raise ValueError(f"Missing snippet {field}: {item['id']}")
    for field in ("tags", "searchTerms"):
        if not authoring.string_list(spec.get(field)):
            raise ValueError(f"Invalid snippet {field}: {item['id']}")
    shared = spec.get("requiredShared")
    if shared not in (["common"], ["common", "material"]):
        raise ValueError(f"Invalid snippet helpers: {item['id']}")
    source = spec.get("source")
    if not isinstance(source, dict) or not authoring.string_list(source.get("symbols")) or not source["symbols"]:
        raise ValueError(f"Missing snippet symbols: {item['id']}")
    allowed = [f"shared/{part}.metal" for part in shared] if spec["kind"] == "shared-helper" else [item["path"] + "/code.metal"]
    if source.get("path") not in allowed:
        raise ValueError(f"Invalid canonical source: {item['id']}")
    code = authoring.read_source(path(source["path"]))
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
    if not isinstance(origin, dict) or not authoring.string_list(origin.get("shaderIDs")) or any(not authoring.text_field(origin.get(field)) for field in ("attribution", "license")):
        raise ValueError(f"Invalid snippet origin: {item['id']}")
    for shader_id in origin["shaderIDs"]:
        if not authoring.valid_id(shader_id):
            raise ValueError("Invalid origin shader ID")
        path(f"shaders/{shader_id}/body.metal")


def snippet_source(item):
    validate_snippet(item)
    spec = item["specification"]
    parts = [authoring.read_source(path(f"shared/{part}.metal")) for part in spec["requiredShared"]]
    if spec["kind"] == "recipe":
        parts.append(authoring.read_source(path(spec["source"]["path"])))
    parts.extend([authoring.read_source(path(spec["examplePath"])), authoring.read_source(path("shared/fragment.metal"))])
    return "\n".join(parts)


def validate_reference(item):
    spec = item["specification"]
    if not isinstance(spec, dict) or not authoring.valid_id(item["id"]) or spec.get("id") != item["id"] or spec.get("schemaVersion") != 1 or any(not authoring.text_field(spec.get(field)) for field in ("name", "summary", "language", "adaptationNotes")):
        raise ValueError(f"Invalid reference: {item['id']}")
    for field in ("tags", "searchTerms", "requirements"):
        if not authoring.string_list(spec.get(field)):
            raise ValueError(f"Invalid reference {field}: {item['id']}")
    if not isinstance(spec.get("origin"), dict) or any(not authoring.text_field(spec["origin"].get(field)) for field in ("author", "license")):
        raise ValueError(f"Missing reference provenance: {item['id']}")
    path(item["path"] + "/README.md")
    files = spec.get("files")
    if not isinstance(files, dict):
        raise ValueError(f"Invalid reference files: {item['id']}")
    original = authoring.ROOT / item["path"] / "original"
    if original.is_symlink():
        raise ValueError(f"Reference symlink forbidden: {item['id']}/original")
    # rglob does not descend into directory symlinks; reject them along with file links.
    original_paths = list(original.rglob("*")) if original.exists() else []
    for entry in original_paths:
        if entry.is_symlink():
            raise ValueError(f"Reference symlink forbidden: {item['id']}/original/{entry.relative_to(original)}")
    actual = {str(p.relative_to(original)) for p in original_paths if p.is_file()}
    if actual != set(files):
        raise ValueError(f"Reference file inventory changed: {item['id']}")
    for filename, sha in files.items():
        if not isinstance(sha, str) or len(sha) != 64 or authoring.digest(path(item["path"] + "/original/" + filename).read_bytes()) != sha:
            raise ValueError(f"Reference checksum mismatch: {item['id']}/{filename}")


def compile_source(source, label):
    with tempfile.TemporaryDirectory() as temp:
        file = pathlib.Path(temp) / "example.metal"
        file.write_bytes(source.encode("utf-8"))
        for sdk in ("macosx", "appletvos"):
            subprocess.run(["xcrun", "-sdk", sdk, "metal", "-c", str(file), "-o", str(pathlib.Path(temp) / f"{sdk}.air")], check=True)
    print(f"Compiled {label} for macOS and tvOS")


def validate(compile_metal=False):
    _, shaders = authoring.entries()
    shader_metadata = {entry[0]["id"]: entry[0] for entry in shaders}
    shader_sources = {entry[0]["id"]: entry[1] for entry in shaders}
    items = assets(shader_metadata=shader_metadata)
    for item in items:
        if item["kind"] == "shader":
            source = authoring.shader_entry(item["id"], metadata=item["specification"])[1] if item["id"] not in shader_metadata else shader_sources[item["id"]]
            if compile_metal:
                compile_source(source, item["id"])
        elif item["kind"] == "snippet":
            source = snippet_source(item)
            if compile_metal:
                compile_source(source, item["id"])
        else:
            validate_reference(item)
    return items


def populate_template(kind, asset_id, destination):
    shutil.copytree(authoring.ROOT / "templates" / kind, destination)
    for file in destination.rglob("*"):
        if file.is_file():
            file.write_text(file.read_text().replace("__ID__", asset_id).replace("__NAME__", asset_id.replace("-", " ").title()))


def scaffold(kind, asset_id):
    if kind not in KINDS or not authoring.valid_id(asset_id):
        raise ValueError("Invalid kind or ID")
    folder, _ = KINDS[kind]
    destination = authoring.ROOT / folder / asset_id
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


def render(kind, asset_id, times, width=1280, height=720):
    if kind not in ("shader", "snippet"):
        raise ValueError("Only Metal shaders and snippet examples can be rendered")
    samples = [float(t) for t in times.split(",")]
    if not samples or any(not math.isfinite(t) or t < 0 for t in samples) or not 1 <= width <= 8192 or not 1 <= height <= 8192 or width * height > 16_777_216:
        raise ValueError("Invalid render settings")
    source = authoring.shader_entry(asset_id)[1] if kind == "shader" else snippet_source(find(kind, asset_id))
    renderer = shader_tool.command("render")
    output = authoring.ROOT / ".cache/library" / f"{kind}-{asset_id}"
    output.mkdir(parents=True, exist_ok=True)
    file = output / "source.metal"
    file.write_bytes(source.encode("utf-8"))
    for sample in samples:
        image = output / f"{width}x{height}-t{sample:g}.png"
        subprocess.run([*renderer, str(file), str(image), "--width", str(width), "--height", str(height), "--time", str(sample)], check=True)
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
    command = commands.add_parser("validate")
    command.add_argument("--compile", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "list": emit(assets(args.kind), args.json)
        elif args.command == "search": emit(search(args.query, args.kind), args.json)
        elif args.command == "show": emit(show(args.kind, args.id), args.json)
        elif args.command == "new": print(scaffold(args.kind, args.id))
        elif args.command == "render": render(args.kind, args.id, args.times, args.width, args.height)
        else: print(f"Validated {len(validate(args.compile))} authoring assets")
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"library: {error}\n")


if __name__ == "__main__":
    main()
