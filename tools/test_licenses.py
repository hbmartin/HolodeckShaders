"""Test-only license coverage for independent sources and their delivery assemblies."""
import copy
import re
import shutil
import unittest

import authoring
import library
from authoring_test_support import fixture_root

# Source obligations are independent of informational metadata.reuse links.
UPSTREAM_REQUIREMENTS = {
    "ashima-webgl-noise": {"license": "MIT", "noticePath": "references/ashima-webgl-noise/original/LICENSE"},
    "swiftui-new-metal-shaders": {"license": "MIT", "noticePath": "references/swiftui-new-metal-shaders/original/LICENSE"},
    "inferno": {"license": "MIT", "noticePath": "references/inferno/original/LICENSE"},
    "swiftshaders": {"license": "MIT", "noticePath": "references/swiftshaders/original/LICENSE"},
    "vhs-overlay": {"license": "MIT", "noticePath": "references/vhs-overlay/original/vhs.glsl"},
    "hoskins-hash": {"license": "MIT", "noticePath": "references/hoskins-hash/NOTICE"},
    "gl-transitions-polka": {"license": "MIT", "noticePath": "references/gl-transitions-polka/original/LICENSE"},
    "sparks-from-fire": {"license": "CC BY 3.0", "uri": "https://creativecommons.org/licenses/by/3.0/"},
    "warp-speed-2": {"license": "CC BY-NC-SA 3.0", "uri": "https://creativecommons.org/licenses/by-nc-sa/3.0/"},
    "inside-the-matrix": {"license": "CC BY-NC-SA 3.0", "uri": "https://creativecommons.org/licenses/by-nc-sa/3.0/"},
    "bigwings-fireworks": {"license": "CC BY-NC-SA 3.0", "uri": "https://creativecommons.org/licenses/by-nc-sa/3.0/"},
}

# Every discovered source needs a deliberate record, including [] for original code.
# Never generate empty entries from inventory: that would hide new omissions.
SOURCE_REQUIREMENTS = {
    'shaders/apollonian-twist/body.metal': ['swiftui-new-metal-shaders'],
    'shaders/aurora/body.metal': [],
    'shaders/brushed-gold/body.metal': [],
    'shaders/chrome/body.metal': [],
    'shaders/dramamine-sunset/body.metal': [],
    'shaders/ember-drift/body.metal': ['sparks-from-fire', 'hoskins-hash'],
    'shaders/evening-and-morning/body.metal': [],
    'shaders/fireworks/body.metal': ['bigwings-fireworks', 'hoskins-hash'],
    'shaders/force-shield/body.metal': ['ashima-webgl-noise'],
    'shaders/green-caresses/body.metal': [],
    'shaders/holodeck-grid/body.metal': [],
    'shaders/iridescent/body.metal': [],
    'shaders/kaleidoscope/body.metal': [],
    'shaders/light-grid/body.metal': ['inferno'],
    'shaders/matrix-corridor/body.metal': ['inside-the-matrix', 'hoskins-hash'],
    'shaders/orange-flow/body.metal': [],
    'shaders/plasma/body.metal': [],
    'shaders/side-view-of-the-ocean/body.metal': [],
    'shaders/sonar-pulse/body.metal': ['inferno'],
    'shaders/starfield/body.metal': [],
    'shaders/sunlit-shallows/body.metal': ['swiftshaders', 'hoskins-hash'],
    'shaders/warp-speed/body.metal': ['warp-speed-2'],
    'shaders/waves/body.metal': [],
    'shared/common.metal': ['hoskins-hash'],
    'shared/fragment.metal': [],
    'shared/material.metal': [],
    'snippets/aurora-curtains/code.metal': [],
    'snippets/aurora-curtains/example.metal': [],
    'snippets/box-room/code.metal': [],
    'snippets/box-room/example.metal': [],
    'snippets/color-ramps/code.metal': ['inferno'],
    'snippets/color-ramps/example.metal': [],
    'snippets/cosine-palette/example.metal': [],
    'snippets/crt-overlay/code.metal': ['vhs-overlay'],
    'snippets/crt-overlay/example.metal': [],
    'snippets/dot-curtain/code.metal': ['inferno', 'gl-transitions-polka'],
    'snippets/dot-curtain/example.metal': [],
    'snippets/ember-sparks/code.metal': ['sparks-from-fire', 'hoskins-hash'],
    'snippets/ember-sparks/example.metal': [],
    'snippets/fbm/example.metal': [],
    'snippets/glowing-ribbons/code.metal': [],
    'snippets/glowing-ribbons/example.metal': [],
    'snippets/god-rays/code.metal': [],
    'snippets/god-rays/example.metal': [],
    'snippets/gradient-noise/code.metal': ['swiftshaders'],
    'snippets/gradient-noise/example.metal': [],
    'snippets/grid-lines/code.metal': [],
    'snippets/grid-lines/example.metal': [],
    'snippets/hex-grid/code.metal': [],
    'snippets/hex-grid/example.metal': [],
    'snippets/hologram-rim/code.metal': [],
    'snippets/hologram-rim/example.metal': [],
    'snippets/impact-ripple/code.metal': [],
    'snippets/impact-ripple/example.metal': [],
    'snippets/kali-starfield/code.metal': ['warp-speed-2'],
    'snippets/kali-starfield/example.metal': [],
    'snippets/layered-stars/code.metal': [],
    'snippets/layered-stars/example.metal': [],
    'snippets/noise-dissolve/code.metal': [],
    'snippets/noise-dissolve/example.metal': [],
    'snippets/polar-fold/code.metal': [],
    'snippets/polar-fold/example.metal': [],
    'snippets/rain-ripples/code.metal': ['swiftshaders'],
    'snippets/rain-ripples/example.metal': [],
    'snippets/rune-glyph/code.metal': ['inside-the-matrix', 'hoskins-hash'],
    'snippets/rune-glyph/example.metal': [],
    'snippets/simplex-noise-3d/code.metal': ['ashima-webgl-noise'],
    'snippets/simplex-noise-3d/example.metal': [],
    'snippets/sine-warp/code.metal': ['inferno'],
    'snippets/sine-warp/example.metal': [],
    'snippets/sphere-shell/code.metal': [],
    'snippets/sphere-shell/example.metal': [],
    'snippets/studio-material/example.metal': [],
    'snippets/value-noise/example.metal': [],
    'snippets/voronoi/code.metal': ['swiftshaders', 'hoskins-hash'],
    'snippets/voronoi/example.metal': [],
}


def normalized(text):
    return " ".join(re.sub(r"^\s*// ?", "", text, flags=re.MULTILINE).split())


def mit_notices(text):
    """Retain every complete block, including multiple copyrights within a block."""
    text = normalized(text)
    matches = list(re.finditer(r"\bCopyright\b.*?\bSOFTWARE\.", text))
    if not matches:
        raise ValueError("No complete MIT notice")
    for match in matches:
        if "Permission is hereby granted" not in match.group() or "THE SOFTWARE IS PROVIDED" not in match.group():
            raise ValueError("Incomplete MIT notice")
    remaining = re.sub(r"\bCopyright\b.*?\bSOFTWARE\.", "", text)
    if re.search(r"\bCopyright\b", remaining):
        raise ValueError("Incomplete trailing MIT notice")
    return [match.group() for match in matches]


def license_kinds(label):
    kinds = set()
    if re.search(r"\bMIT\b", label):
        kinds.add("MIT")
    if "CC BY-NC-SA" in label:
        kinds.add("CC BY-NC-SA 3.0")
    if re.search(r"CC BY(?!-NC-SA)\b", label):
        kinds.add("CC BY 3.0")
    return kinds


def source_inventory(items):
    paths = set()
    for item in items:
        spec = item["specification"]
        if item["kind"] == "shader":
            paths.add(item["path"] + "/body.metal")
            paths.update(f"shared/{part}.metal" for part in spec["shared"])
        elif item["kind"] == "snippet":
            paths.update((spec["source"]["path"], spec["examplePath"]))
            paths.update(f"shared/{part}.metal" for part in spec["requiredShared"])
    return paths


def check_coverage(items, records, upstreams):
    inventory = source_inventory(items)
    missing, stale = inventory - records.keys(), records.keys() - inventory
    if missing:
        raise ValueError(f"Unregistered sources: {sorted(missing)}")
    if stale:
        raise ValueError(f"Stale source records: {sorted(stale)}")
    references = {item["id"]: item for item in items if item["kind"] == "reference"}
    for reference, requirement in upstreams.items():
        if reference not in references:
            raise ValueError(f"Stale upstream record: {reference}")
        declared = license_kinds(references[reference]["specification"]["origin"]["license"])
        if requirement["license"] not in declared:
            raise ValueError(f"Upstream license disagrees with reference: {reference}")
    for source, required in records.items():
        if len(required) != len(set(required)):
            raise ValueError(f"Duplicate source requirement: {source}")
        for reference in required:
            if reference not in upstreams:
                raise ValueError(f"Unregistered upstream {reference} in {source}")
    for item in items:
        spec = item["specification"]
        if item["kind"] == "reference":
            if license_kinds(spec["origin"]["license"]) and item["id"] not in upstreams:
                raise ValueError(f"Unregistered licensed reference: {item['id']}")
        elif item["kind"] == "snippet":
            expected = license_kinds(spec["origin"]["license"])
            registered = {upstreams[ref]["license"] for ref in records[spec["source"]["path"]]}
            if not expected <= registered:
                raise ValueError(f"Unregistered declared snippet licenses: {item['id']}")


def require_notices(label, text, references, upstreams):
    text = normalized(text)
    for reference in sorted(set(references)):
        requirement = upstreams[reference]
        if requirement["license"] == "MIT":
            notices = mit_notices(library.path(requirement["noticePath"]).read_text())
            if any(notice not in text for notice in notices):
                raise ValueError(f"Missing {reference} MIT notice in {label}")
        elif requirement["uri"] not in text:
            raise ValueError(f"Missing {reference} CC URI in {label}")


def audit_notices(records=None, upstreams=None):
    """Called by tests only; production validators do not import this module."""
    records = SOURCE_REQUIREMENTS if records is None else records
    upstreams = UPSTREAM_REQUIREMENTS if upstreams is None else upstreams
    items = library.assets()
    check_coverage(items, records, upstreams)
    for source, references in records.items():
        require_notices(source, library.path(source).read_text(), references, upstreams)
    for item in items:
        if item["kind"] != "snippet":
            continue
        spec = item["specification"]
        paths = [spec["source"]["path"], spec["examplePath"]]
        paths.extend(f"shared/{part}.metal" for part in spec["requiredShared"])
        references = [ref for path in paths for ref in records[path]]
        require_notices("example " + item["id"], library.snippet_source(item), references, upstreams)
    for metadata, source, *_ in authoring.entries()[1]:
        paths = [f"shaders/{metadata['id']}/body.metal"]
        paths.extend(f"shared/{part}.metal" for part in metadata["shared"])
        references = [ref for path in paths for ref in records[path]]
        require_notices("assembled " + metadata["id"], source, references, upstreams)


def remove_mit_notice(path, holder):
    pattern = r"// Copyright \(c\) " + re.escape(holder) + r".*?// (?:THE )?SOFTWARE\.\n"
    text, count = re.subn(pattern, "", path.read_text(), count=1, flags=re.DOTALL)
    if count != 1:
        raise AssertionError(f"Fixture did not remove the expected notice: {holder}")
    path.write_text(text)


class LicenseDeliveryTests(unittest.TestCase):
    def test_complete_coverage_and_delivery(self):
        audit_notices()

    def test_missing_and_stale_source_records_are_rejected(self):
        for missing in (True, False):
            with self.subTest(missing=missing):
                records = copy.deepcopy(SOURCE_REQUIREMENTS)
                if missing:
                    del records["snippets/value-noise/example.metal"]
                else:
                    records["snippets/obsolete/code.metal"] = []
                with self.assertRaisesRegex(ValueError, "Unregistered sources" if missing else "Stale source records"):
                    audit_notices(records)

    def test_unregistered_licensed_references_are_rejected(self):
        for original in ("inferno", "sparks-from-fire"):
            with self.subTest(original=original), fixture_root("shaders", "shared", "snippets", "references") as root:
                destination = root / "references/unregistered"
                shutil.copytree(root / "references" / original, destination)
                spec = authoring.read_json(destination / "reference.json")
                spec["id"] = "unregistered"
                authoring.write_json(destination / "reference.json", spec)
                with self.assertRaisesRegex(ValueError, "Unregistered licensed reference"):
                    audit_notices()

    def test_declared_mit_cc_and_mixed_snippets_cannot_have_empty_requirements(self):
        for original in ("color-ramps", "kali-starfield", "rune-glyph"):
            with self.subTest(original=original), fixture_root("shaders", "shared", "snippets", "references") as root:
                destination = root / "snippets/unregistered"
                shutil.copytree(root / "snippets" / original, destination)
                spec = authoring.read_json(destination / "snippet.json")
                spec.update(id="unregistered", examplePath="snippets/unregistered/example.metal")
                spec["source"]["path"] = "snippets/unregistered/code.metal"
                authoring.write_json(destination / "snippet.json", spec)
                records = dict(SOURCE_REQUIREMENTS, **{
                    "snippets/unregistered/code.metal": [],
                    "snippets/unregistered/example.metal": [],
                })
                with self.assertRaisesRegex(ValueError, "Unregistered declared snippet licenses"):
                    audit_notices(records)

    def test_secondary_notice_is_required_independently(self):
        with fixture_root("shaders", "shared", "snippets", "references") as root:
            remove_mit_notice(root / "snippets/dot-curtain/code.metal", "2017-present gl-transitions contributors")
            with self.assertRaisesRegex(ValueError, "Missing gl-transitions-polka MIT notice"):
                audit_notices()

    def test_shared_notice_is_required(self):
        with fixture_root("shaders", "shared", "snippets", "references") as root:
            remove_mit_notice(root / "shared/common.metal", "2014 David Hoskins")
            with self.assertRaisesRegex(ValueError, "Missing hoskins-hash MIT notice in shared/common"):
                audit_notices()

    def test_assembled_common_notice_cannot_hide_missing_body_notice(self):
        with fixture_root("shaders", "shared", "snippets", "references") as root:
            remove_mit_notice(root / "shaders/matrix-corridor/body.metal", "2014 David Hoskins")
            with self.assertRaisesRegex(ValueError, "Missing hoskins-hash MIT notice in shaders/matrix"):
                audit_notices()

    def test_missing_cc_uri_is_rejected(self):
        with fixture_root("shaders", "shared", "snippets", "references") as root:
            path = root / "snippets/rune-glyph/code.metal"
            path.write_text(path.read_text().replace(UPSTREAM_REQUIREMENTS["inside-the-matrix"]["uri"], ""))
            with self.assertRaisesRegex(ValueError, "Missing inside-the-matrix CC URI"):
                audit_notices()

    def test_every_mit_block_is_required_and_incomplete_blocks_are_rejected(self):
        with fixture_root("shaders", "shared", "snippets", "references") as root:
            path = root / "references/inferno/original/LICENSE"
            first = mit_notices(path.read_text())[0]
            second = first.replace("2023 Paul Hudson and other authors.", "2001 Fixture Author.")
            self.assertEqual(len(mit_notices(first + "\n" + second)), 2)
            path.write_text(first + "\n" + second)
            with self.assertRaisesRegex(ValueError, "Missing inferno MIT notice"):
                audit_notices()
            with self.assertRaisesRegex(ValueError, "Incomplete trailing MIT notice"):
                mit_notices(first + "\nCopyright 2001 incomplete")


if __name__ == "__main__":
    unittest.main()
