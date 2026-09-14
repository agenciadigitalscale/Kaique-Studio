"""Perfis de exportação — cada um ajusta proporção+resolução para um destino."""
import unittest
import core, native


class ExportProfileTests(unittest.TestCase):
    def test_profiles_map_to_valid_aspect_and_quality(self):
        for name, (aspect, quality) in core.EXPORT_PROFILES.items():
            self.assertIn(aspect, core.ASPECT_CHOICES, name)
            self.assertIn(quality, core.QUALITY_CHOICES, name)

    def test_apply_sets_fields_without_mutating(self):
        style = native.project()['style']
        out = core.apply_export_profile(style, 'Reels / TikTok / Story (9:16)')
        self.assertEqual((out['aspect'], out['quality']), ('9:16', 'Alta (1080p)'))
        self.assertEqual(style['aspect'], 'Original')  # original intacto

    def test_youtube_4k(self):
        out = core.apply_export_profile(native.project()['style'], 'YouTube 4K (16:9)')
        self.assertEqual((out['aspect'], out['quality']), ('16:9', 'Máxima (4K)'))

    def test_applied_profile_passes_validation(self):
        flat = core.project()
        flat.update(source='x', duration=3, width=1080, height=1920,
                    ranges=[{'start': 0, 'end': 3, 'enabled': True}])
        for name in core.EXPORT_PROFILES:
            core.validate(core.apply_export_profile(flat, name), files=False)

    def test_unknown_raises(self):
        with self.assertRaises(ValueError):
            core.apply_export_profile(native.project()['style'], 'Cinema IMAX')


if __name__ == '__main__':
    unittest.main()
