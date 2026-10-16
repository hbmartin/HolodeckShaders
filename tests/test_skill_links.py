import importlib.util
from pathlib import Path
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
            (self.links / target.name).symlink_to(target, target_is_directory=True)

    def test_all_local_and_vendor_skills_are_discoverable(self):
        self.assertEqual(skills.check(self.root), 2)

    def test_vendor_addition_removal_and_rename_require_link_updates(self):
        new = self.vendor.parent / "new-skill"
        new.mkdir()
        (new / "SKILL.md").write_text("New skill")
        with self.assertRaisesRegex(ValueError, "missing=.*new-skill"):
            skills.check(self.root)
        (self.links / new.name).symlink_to(new, target_is_directory=True)
        self.assertEqual(skills.check(self.root), 3)
        self.vendor.rename(self.vendor.with_name("renamed-skill"))
        with self.assertRaisesRegex(ValueError, "missing=.*renamed-skill.*unexpected=.*metal-compute"):
            skills.check(self.root)
        (self.links / self.vendor.name).unlink()
        (self.links / "renamed-skill").symlink_to(self.vendor.with_name("renamed-skill"), target_is_directory=True)
        self.assertEqual(skills.check(self.root), 3)
        (new / "SKILL.md").unlink()
        with self.assertRaisesRegex(ValueError, "unexpected=.*new-skill"):
            skills.check(self.root)

    def test_missing_broken_and_wrong_target_links_fail(self):
        link = self.links / self.vendor.name
        for target in (self.root / "missing", self.local):
            link.unlink()
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "Broken or incorrectly targeted"):
                skills.check(self.root)
        link.unlink()
        with self.assertRaisesRegex(ValueError, "missing=.*metal-compute"):
            skills.check(self.root)
