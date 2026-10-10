"""License notices must survive the same assembly paths used for delivery and reuse."""
import re
import unittest

import catalog
import library


MIT_SCENES = {
    "force-shield": "ashima-webgl-noise",
    "apollonian-twist": "swiftui-new-metal-shaders",
    "light-grid": "inferno",
    "sonar-pulse": "inferno",
    "sunlit-shallows": "swiftshaders",
}
MIT_RECIPES = {
    "simplex-noise-3d": "ashima-webgl-noise",
    "color-ramps": "inferno",
    "dot-curtain": "inferno",
    "sine-warp": "inferno",
    "sinebow-lines": "inferno",
    "gradient-noise": "swiftshaders",
    "rain-ripples": "swiftshaders",
    "voronoi": "swiftshaders",
    "crt-overlay": "vhs-overlay",
}
CC_SCENES = {
    "ember-drift": "by",
    "warp-speed": "by-nc-sa",
    "matrix-corridor": "by-nc-sa",
    "fireworks": "by-nc-sa",
}
CC_RECIPES = {"ember-sparks": "by", "kali-starfield": "by-nc-sa", "rune-glyph": "by-nc-sa"}


def normalized(text):
    return " ".join(re.sub(r"^\s*// ?", "", text, flags=re.MULTILINE).split())


def upstream_mit_notice(reference):
    filename = "vhs.glsl" if reference == "vhs-overlay" else "LICENSE"
    text = normalized((catalog.ROOT / "references" / reference / "original" / filename).read_text())
    start = text.index("Copyright")
    end = text.index("SOFTWARE.", start) + len("SOFTWARE.")
    return text[start:end]


class LicenseDeliveryTests(unittest.TestCase):
    def test_complete_mit_notices_in_published_sources(self):
        for shader_id, reference in MIT_SCENES.items():
            with self.subTest(shader=shader_id):
                source = catalog.shader_entry(shader_id)[1]
                self.assertIn(upstream_mit_notice(reference), normalized(source))

    def test_complete_mit_notices_in_copyable_recipes_and_examples(self):
        for snippet_id, reference in MIT_RECIPES.items():
            item = library.find("snippet", snippet_id)
            recipe = library.path(item["specification"]["source"]["path"]).read_text()
            for label, source in (("recipe", recipe), ("example", library.snippet_source(item))):
                with self.subTest(snippet=snippet_id, form=label):
                    self.assertIn(upstream_mit_notice(reference), normalized(source))

    def test_cc_license_uris_in_published_sources(self):
        for shader_id, license_id in CC_SCENES.items():
            with self.subTest(shader=shader_id):
                self.assertIn(f"https://creativecommons.org/licenses/{license_id}/3.0/",
                              catalog.shader_entry(shader_id)[1])

    def test_cc_license_uris_in_copyable_recipes_and_examples(self):
        for snippet_id, license_id in CC_RECIPES.items():
            item = library.find("snippet", snippet_id)
            recipe = library.path(item["specification"]["source"]["path"]).read_text()
            for label, source in (("recipe", recipe), ("example", library.snippet_source(item))):
                with self.subTest(snippet=snippet_id, form=label):
                    self.assertIn(f"https://creativecommons.org/licenses/{license_id}/3.0/", source)


if __name__ == "__main__":
    unittest.main()
