"""Theme behavior: legible neutral copy and one coherent pink appearance."""

import unittest

from piggyplan.tokens import FONT_TABLE, NEUTRAL, THEME_KEYS, THEMES, contrast, palette


class ThemeTests(unittest.TestCase):
    def test_only_pink_is_available(self):
        self.assertEqual(THEME_KEYS, ("pink",))
        self.assertEqual(set(THEMES), {"pink"})

    def test_body_text_keeps_neutral_ink_separate_from_action_color(self):
        colors = palette("pink")
        self.assertEqual(colors["ink"], NEUTRAL["ink"])
        self.assertEqual(colors["text"], NEUTRAL["ink"])
        self.assertNotEqual(colors["text"], colors["strong"])

    def test_legacy_or_unknown_themes_render_as_pink(self):
        expected = palette("pink")
        for old_key in ("peach", "mint", "lavender", "missing", ""):
            with self.subTest(theme=old_key):
                self.assertEqual(palette(old_key), expected)

    def test_all_text_roles_are_legible_on_actual_light_surfaces(self):
        colors = palette("pink")
        for foreground in ("text", "text_soft", "text_faint", "strong", "high_ink", "success_ink", "warning_ink"):
            for background in ("bg", "surface", "soft", "soft_surface", "surface_soft"):
                with self.subTest(foreground=foreground, background=background):
                    self.assertGreaterEqual(contrast(colors[foreground], colors[background]), 4.5)
        self.assertGreaterEqual(contrast("#FFFFFF", colors["strong"]), 4.5)

    def test_small_copy_uses_a_readable_size_and_normal_weight(self):
        for family, roles in FONT_TABLE.items():
            for role in ("body", "meta", "micro"):
                font = roles[role]
                with self.subTest(family=family, role=role):
                    self.assertGreaterEqual(font[1], 9)
                    self.assertEqual(font[2] if len(font) > 2 else "normal", "normal")


if __name__ == "__main__":
    unittest.main()
