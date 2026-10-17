import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest


spec = importlib.util.spec_from_file_location("skill_links", Path(__file__).resolve().parents[1] / "tools/check_skill_links.py")
skills = importlib.util.module_from_spec(spec)
spec.loader.exec_module(skills)


class SkillLinkTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.links = self.root / ".agents/skills"
        self.links.mkdir(parents=True)
        self.local = self.root / "skills/holodeck-authoring"
        self.vendor = self.root / "vendor/metal-skills/skills/metal-compute"
        for target in (self.local, self.vendor):
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("Fixture skill")
            self.link(self.links / target.name, target)

    def link(self, path, target):
        path.symlink_to(os.path.relpath(target, path.parent), target_is_directory=True)

    def test_all_local_and_vendor_skills_are_discoverable(self):
        self.assertEqual(skills.check(self.root), 2)

    def test_relative_links_survive_checkout_relocation(self):
        with tempfile.TemporaryDirectory() as temporary:
            relocated = Path(temporary) / "relocated checkout"
            shutil.copytree(self.root, relocated, symlinks=True)
            shutil.rmtree(self.root)
            self.assertEqual(skills.check(relocated), 2)

    def test_ds_store_is_ignored_but_other_extra_entries_fail(self):
        (self.links / ".DS_Store").write_bytes(b"Finder metadata")
        self.assertEqual(skills.check(self.root), 2)
        for name in (".unexpected", "unexpected-skill"):
            with self.subTest(name=name):
                extra = self.links / name
                extra.touch()
                with self.assertRaisesRegex(ValueError, "unexpected="):
                    skills.check(self.root)
                extra.unlink()

    def test_discovery_directory_must_not_be_a_symlink(self):
        target = self.links.with_name("linked-skills")
        self.links.rename(target)
        self.link(self.links, target)
        with self.assertRaisesRegex(ValueError, "must be a real directory"):
            skills.check(self.root)

    def test_duplicate_local_and_vendor_skill_names_fail(self):
        duplicate = self.vendor.parent / self.local.name
        duplicate.mkdir()
        (duplicate / "SKILL.md").write_text("Duplicate skill")
        with self.assertRaisesRegex(ValueError, "Duplicate local/vendor skill name: holodeck-authoring"):
            skills.check(self.root)

    def test_absolute_links_to_the_correct_target_fail(self):
        for target in (self.local, self.vendor):
            with self.subTest(skill=target.name):
                link = self.links / target.name
                link.unlink()
                link.symlink_to(target.resolve(), target_is_directory=True)
                with self.assertRaisesRegex(ValueError, "expected a relative link"):
                    skills.check(self.root)
                link.unlink()
                self.link(link, target)

    def test_real_directory_cannot_replace_a_skill_link(self):
        link = self.links / self.vendor.name
        link.unlink()
        shutil.copytree(self.vendor, link)
        with self.assertRaisesRegex(ValueError, "Broken or incorrectly targeted"):
            skills.check(self.root)

    def test_vendor_addition_removal_and_rename_require_link_updates(self):
        new = self.vendor.parent / "new-skill"
        new.mkdir()
        (new / "SKILL.md").write_text("New skill")
        with self.assertRaisesRegex(ValueError, "missing=.*new-skill"):
            skills.check(self.root)
        self.link(self.links / new.name, new)
        self.assertEqual(skills.check(self.root), 3)
        self.vendor.rename(self.vendor.with_name("renamed-skill"))
        with self.assertRaisesRegex(ValueError, "missing=.*renamed-skill.*unexpected=.*metal-compute"):
            skills.check(self.root)
        (self.links / self.vendor.name).unlink()
        self.link(self.links / "renamed-skill", self.vendor.with_name("renamed-skill"))
        self.assertEqual(skills.check(self.root), 3)
        (new / "SKILL.md").unlink()
        with self.assertRaisesRegex(ValueError, "unexpected=.*new-skill"):
            skills.check(self.root)

    def test_missing_broken_and_wrong_target_links_fail(self):
        link = self.links / self.vendor.name
        for target in (self.root / "missing", self.local):
            link.unlink()
            self.link(link, target)
            with self.assertRaisesRegex(ValueError, "Broken or incorrectly targeted"):
                skills.check(self.root)
        link.unlink()
        with self.assertRaisesRegex(ValueError, "missing=.*metal-compute"):
            skills.check(self.root)
