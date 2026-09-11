"""Modelos prontos de legenda — cada um tem de gerar um projeto que o core aceita,
senão o 'escolher um estilo pronto' quebraria só na hora de exportar."""
import unittest
import core, native, library


class CaptionTemplateTests(unittest.TestCase):
    def test_all_templates_are_valid_presets(self):
        for t in library.CAPTION_TEMPLATES:
            library.validate_preset(t)  # não estoura

    def test_apply_sets_expected_fields_without_mutating(self):
        style = native.project()['style']
        before = style['caption_mode']
        out = library.apply_caption_template(style, 'TikTok Pop')
        self.assertEqual(out['caption_mode'], 'Palavra ativa')
        self.assertEqual(out['caption_style'], 'Pop')
        self.assertTrue(out['captions_enabled'])
        self.assertEqual(style['caption_mode'], before)  # original intacto

    def test_applied_template_passes_core_validation(self):
        flat = core.project()
        flat.update(source='x', duration=5, width=1080, height=1920,
                    ranges=[{'start': 0, 'end': 5, 'enabled': True}])
        for name in library.caption_template_names():
            core.validate(library.apply_caption_template(flat, name), files=False)

    def test_unknown_template_raises(self):
        with self.assertRaises(ValueError):
            library.apply_caption_template(native.project()['style'], 'Inexistente')


if __name__ == '__main__':
    unittest.main()
