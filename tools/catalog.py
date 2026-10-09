#!/usr/bin/env python3
"""Build, render and validate the Holodeck publication using only the standard library."""
import argparse
import datetime
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SETTINGS = {"width": 1280, "height": 720, "time": 3, "pixelFormat": "bgra8Unorm_srgb"}
MOODS = {"calm", "dreamy", "energetic"}
MOTIONS = {"slow", "steady", "fast"}


def valid_id(value):
    return isinstance(value, str) and len(value) <= 100 and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) is not None


def text_field(value, limit=2000):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit


def string_list(value, limit=32):
    return isinstance(value, list) and len(value) <= limit and all(text_field(v, 100) for v in value) and len(value) == len(set(value))


def validate_metadata(metadata, shader_id):
    if not isinstance(metadata, dict) or not valid_id(shader_id) or metadata.get("id") != shader_id or metadata.get("category") not in ("PROCEDURAL", "3D MATERIAL"):
        raise ValueError(f"Invalid metadata for {shader_id}")
    if not text_field(metadata.get("name"), 200) or not text_field(metadata.get("description")):
        raise ValueError(f"Missing name/description for {shader_id}")
    colors = metadata.get("colors")
    if not isinstance(colors, list) or len(colors) != 2 or any(not isinstance(c, list) or len(c) != 3 or any(type(v) not in (int, float) or not 0 <= v <= 1 for v in c) for c in colors):
        raise ValueError(f"Invalid colors for {shader_id}")
    if metadata.get("shared") not in (["common", "fragment"], ["common", "material", "fragment"]):
        raise ValueError("Shared files must declare common, optional material, then fragment")
    if "discovery" in metadata:
        discovery = metadata["discovery"]
        if not isinstance(discovery, dict) or not string_list(discovery.get("tags")) or not string_list(discovery.get("moods"), 8) or not set(discovery["moods"]) <= MOODS or discovery.get("motion") not in MOTIONS:
            raise ValueError(f"Invalid discovery for {shader_id}")
    if "reuse" in metadata:
        reuse = metadata["reuse"]
        if not isinstance(reuse, dict) or set(reuse) != {"snippets", "references"}:
            raise ValueError(f"Invalid reuse for {shader_id}")
        for kind, filename in (("snippets", "snippet.json"), ("references", "reference.json")):
            ids = reuse[kind]
            if not string_list(ids) or any(not valid_id(i) or not (ROOT / kind / i / filename).is_file() for i in ids):
                raise ValueError(f"Broken {kind} reuse link for {shader_id}")


def validate_collections(collections, shader_ids):
    if not isinstance(collections, list) or len(collections) > 100:
        raise ValueError("Invalid collections")
    seen = set()
    for collection in collections:
        if not isinstance(collection, dict):
            raise ValueError("Invalid collection")
        cid = collection.get("id")
        members = collection.get("shaderIDs")
        if not valid_id(cid) or cid == "all" or cid in seen or not text_field(collection.get("name"), 200) or not text_field(collection.get("description")) or not string_list(members, 500) or not members or not set(members) <= set(shader_ids):
            raise ValueError(f"Invalid collection: {cid}")
        seen.add(cid)


def shader_entry(shader_id):
    if not valid_id(shader_id):
        raise ValueError("Invalid shader ID")
    directory = ROOT / "shaders" / shader_id
    metadata = read_json(directory / "metadata.json")
    validate_metadata(metadata, shader_id)
    shared = metadata["shared"]
    dependencies = [directory / "metadata.json", directory / "body.metal"] + [ROOT / "shared" / f"{part}.metal" for part in shared]
    # Preserve the original assembly bytes for existing publications.
    source = "".join((ROOT / "shared" / f"{part}.metal").read_text() for part in shared[:-1]) + (directory / "body.metal").read_text() + (ROOT / "shared" / "fragment.metal").read_text()
    fingerprint = digest(source.encode() + (ROOT / "tools/render-preview.swift").read_bytes() + json.dumps(SETTINGS, sort_keys=True).encode())
    if not source or len(source.encode()) > 1_048_576:
        raise ValueError(f"Invalid source size for {shader_id}")
    return metadata, source, fingerprint, dependencies, directory


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def entries():
    index = read_json(ROOT / "index.json")
    ids = index["shaders"]
    if not isinstance(ids, list) or not 1 <= len(ids) <= 500 or any(not valid_id(i) for i in ids) or len(ids) != len(set(ids)) or index["defaultShaderID"] not in ids:
        raise ValueError("Catalog must be nonempty with unique IDs and an existing default")
    if "collections" in index:
        validate_collections(index["collections"], ids)
    result = [shader_entry(shader_id) for shader_id in ids]
    if sum(len(entry[1].encode()) for entry in result) > 16_777_216:
        raise ValueError("Catalog sources exceed 16 MiB")
    return index, result


def generate():
    _, shaders = entries()
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    renderer = cache / "render-preview"
    subprocess.run(["xcrun", "swiftc", str(ROOT / "tools/render-preview.swift"), "-o", str(renderer)], check=True)
    for metadata, source, fingerprint, _, directory in shaders:
        source_path = cache / f"{metadata['id']}.metal"
        source_path.write_text(source)
        image = directory / "preview.png"
        subprocess.run([str(renderer), str(source_path), str(image)], check=True)
        write_json(directory / "preview.json", {"fingerprint": fingerprint, "sha256": digest(image.read_bytes()), "settings": SETTINGS})
        print(f"Rendered {metadata['id']}")


def build(output, compile_metal=False):
    output = pathlib.Path(output)
    if output.is_symlink() or (output.exists() and (not output.is_dir() or any(p.name not in {"catalog.json", "sources", "previews", ".DS_Store"} for p in output.iterdir()))):
        raise ValueError("Publication output contains non-generated files; choose an empty output directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".catalog-", dir=output.parent) as temp:
        stage = pathlib.Path(temp) / "publication"
        manifest = _build(stage, compile_metal)
        backup = pathlib.Path(temp) / "previous"
        if output.exists():
            output.rename(backup)
        try:
            stage.rename(output)
        except OSError:
            if backup.exists():
                backup.rename(output)
            raise
    return manifest


def _build(output, compile_metal=False):
    index, shaders = entries()
    manifest = {"schemaVersion": 1, "defaultShaderID": index["defaultShaderID"], "sourceRevision": git("rev-parse", "HEAD"), "shaders": []}
    if "collections" in index:
        manifest["collections"] = index["collections"]
    output.mkdir(parents=True, exist_ok=True)
    for metadata, source, fingerprint, dependencies, directory in shaders:
        preview = read_json(directory / "preview.json")
        image = (directory / "preview.png").read_bytes()
        if preview != {"fingerprint": fingerprint, "sha256": digest(image), "settings": SETTINGS}:
            raise ValueError(f"Stale preview for {metadata['id']}; run generate")
        if len(image) > 8_388_608 or image[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Preview is not PNG")
        shader_id = metadata["id"]
        source_path = f"sources/{shader_id}.metal"
        preview_path = f"previews/{shader_id}.png"
        (output / "sources").mkdir(exist_ok=True)
        (output / "previews").mkdir(exist_ok=True)
        (output / source_path).write_text(source)
        (output / preview_path).write_bytes(image)
        # Git committer timestamps include shared helper changes; full history is required in CI.
        paths = [str(p.relative_to(ROOT)) for p in dependencies]
        timestamp = git("log", "-1", "--format=%cI", "--", *paths)
        if not timestamp:
            raise ValueError(f"Commit shader source before building: {shader_id}")
        timestamp = datetime.datetime.fromisoformat(timestamp).astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        entry = {k: metadata[k] for k in ("id", "name", "description", "category", "colors")}
        if "discovery" in metadata:
            entry["discovery"] = metadata["discovery"]
        entry.update(updatedAt=timestamp, sourcePath=source_path, sourceSHA256=digest(source.encode()), previewPath=preview_path, previewSHA256=digest(image))
        manifest["shaders"].append(entry)
        if compile_metal:
            with tempfile.TemporaryDirectory() as temp:
                subprocess.run(["xcrun", "-sdk", "appletvos", "metal", "-c", str(output / source_path), "-o", str(pathlib.Path(temp) / "shader.air")], check=True)
    if len((json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()) > 2_097_152:
        raise ValueError("Catalog manifest exceeds the app's 2 MiB download limit")
    write_json(output / "catalog.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["generate", "validate", "build"])
    parser.add_argument("--output", type=pathlib.Path, default=ROOT / "dist")
    args = parser.parse_args()
    if args.command == "generate":
        generate()
    else:
        build(args.output, compile_metal=args.command == "validate")
        print(f"Validated publication at {args.output}")


if __name__ == "__main__":
    main()
