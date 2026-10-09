#!/usr/bin/env python3
"""Build, render and validate the Holodeck publication using only the standard library."""
import argparse
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SETTINGS = {"width": 1280, "height": 720, "time": 3, "pixelFormat": "bgra8Unorm_srgb"}


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
    if not 1 <= len(ids) <= 500 or len(ids) != len(set(ids)) or index["defaultShaderID"] not in ids:
        raise ValueError("Catalog must be nonempty with unique IDs and an existing default")
    result = []
    for shader_id in ids:
        if len(shader_id) > 100 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", shader_id):
            raise ValueError("Invalid shader ID")
        directory = ROOT / "shaders" / shader_id
        metadata = read_json(directory / "metadata.json")
        if metadata["id"] != shader_id or metadata["category"] not in ("PROCEDURAL", "3D MATERIAL"):
            raise ValueError(f"Invalid metadata for {shader_id}")
        if not metadata["name"].strip() or not metadata["description"].strip() or len(metadata["name"]) > 200 or len(metadata["description"]) > 2000:
            raise ValueError(f"Missing name/description for {shader_id}")
        colors = metadata["colors"]
        if len(colors) != 2 or any(len(c) != 3 or any(type(v) not in (int, float) or not 0 <= v <= 1 for v in c) for c in colors):
            raise ValueError(f"Invalid colors for {shader_id}")
        shared = metadata["shared"]
        if shared not in (["common", "fragment"], ["common", "material", "fragment"]):
            raise ValueError("Shared files must declare common, optional material, then fragment")
        dependencies = [directory / "metadata.json", directory / "body.metal"] + [ROOT / "shared" / f"{part}.metal" for part in shared]
        source = "".join((ROOT / "shared" / f"{part}.metal").read_text() for part in shared[:-1])
        source += (directory / "body.metal").read_text() + (ROOT / "shared" / "fragment.metal").read_text()
        fingerprint = digest(source.encode() + (ROOT / "tools/render-preview.swift").read_bytes() + json.dumps(SETTINGS, sort_keys=True).encode())
        if not source or len(source.encode()) > 1_048_576:
            raise ValueError(f"Invalid source size for {shader_id}")
        result.append((metadata, source, fingerprint, dependencies, directory))
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
    index, shaders = entries()
    manifest = {"schemaVersion": 1, "defaultShaderID": index["defaultShaderID"], "sourceRevision": git("rev-parse", "HEAD"), "shaders": []}
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
        entry.update(updatedAt=timestamp, sourcePath=source_path, sourceSHA256=digest(source.encode()), previewPath=preview_path, previewSHA256=digest(image))
        manifest["shaders"].append(entry)
        if compile_metal:
            with tempfile.TemporaryDirectory() as temp:
                subprocess.run(["xcrun", "-sdk", "appletvos", "metal", "-c", str(output / source_path), "-o", str(pathlib.Path(temp) / "shader.air")], check=True)
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
