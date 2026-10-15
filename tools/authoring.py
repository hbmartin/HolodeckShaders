"""Validate and assemble authoring sources without previews or Git history."""
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
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


def shader_entry(shader_id, *, metadata=None):
    if not valid_id(shader_id):
        raise ValueError("Invalid shader ID")
    directory = ROOT / "shaders" / shader_id
    if metadata is None:
        metadata = read_json(directory / "metadata.json")
    validate_metadata(metadata, shader_id)
    shared = metadata["shared"]
    # Preserve the runtime assembly bytes.
    components = [ROOT / "shared" / f"{part}.metal" for part in shared[:-1]]
    components.extend([directory / "body.metal", ROOT / "shared" / "fragment.metal"])
    source = "".join(read_source(component) for component in components)
    if not source:
        raise ValueError(f"Empty source for {shader_id}")
    return metadata, source


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_source(path):
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"Invalid UTF-8 source {path}: {error}") from error


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def entries():
    index = read_json(ROOT / "index.json")
    ids = index["shaders"]
    if not isinstance(ids, list) or not 1 <= len(ids) <= 500 or any(not valid_id(i) for i in ids) or len(ids) != len(set(ids)) or index["defaultShaderID"] not in ids:
        raise ValueError("Catalog must be nonempty with unique IDs and an existing default")
    if "collections" in index:
        validate_collections(index["collections"], ids)
    result = [shader_entry(shader_id) for shader_id in ids]
    return index, result
