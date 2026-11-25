#!/usr/bin/env python3
"""Require discovery links to cover every local and vendored skill."""
import argparse
import os
from pathlib import Path
import sys


def expected_skills(root):
    expected = {}
    for folder in (root / "skills", root / "vendor/metal-skills/skills"):
        for skill in folder.iterdir():
            if skill.is_dir() and (skill / "SKILL.md").is_file():
                if skill.name in expected:
                    raise ValueError(f"Duplicate local/vendor skill name: {skill.name}")
                expected[skill.name] = skill.resolve()
    return expected


def check(root):
    root = Path(root).resolve()
    expected = expected_skills(root)
    discovery = root / ".agents/skills"
    if discovery.is_symlink() or not discovery.is_dir():
        raise ValueError(".agents/skills must be a real directory of individual skill links")
    actual = {entry.name: entry for entry in discovery.iterdir() if entry.name != ".DS_Store"}
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    if missing or extra:
        raise ValueError(f"Skill discovery inventory differs: missing={missing}, unexpected={extra}; update .agents/skills links")
    for name, target in expected.items():
        link = actual[name]
        label = f".agents/skills/{name}"
        stored = os.readlink(link) if link.is_symlink() else None
        canonical = os.path.relpath(target, link.parent)
        if stored is None:
            raise ValueError(f"Skill discovery entry is not a symlink: {label}")
        if Path(stored).is_absolute():
            raise ValueError(f"Absolute skill link: {label}; expected relative target {canonical}")
        if not link.exists():
            raise ValueError(f"Broken skill link: {label}; stored target {stored}")
        if link.resolve() != target:
            raise ValueError(f"Wrong skill link target: {label}; expected {target}, resolved to {link.resolve()}")
        if stored != canonical:
            raise ValueError(f"Noncanonical relative skill link: {label}; expected {canonical}, got {stored}")
        if not (link / "SKILL.md").is_file():
            raise ValueError(f"Missing SKILL.md through skill link: {label}")
    return len(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        print(f"Verified {check(args.root)} skill discovery links")
        return 0
    except (ValueError, OSError) as error:
        print(f"skill-links: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
