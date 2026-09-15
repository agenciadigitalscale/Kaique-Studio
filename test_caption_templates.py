"""Modelos prontos de legenda — cada um tem de gerar um projeto que o core aceita,
senão o 'escolher um estilo pronto' quebraria só na hora de exportar."""
import subprocess, tempfile, unittest
from pathlib import Path
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


class DynamicDimensionTests(unittest.TestCase):
    """Os modelos novos são LOOKS completos: têm de carregar cor por palavra,
    posição e emoji — não só modo/animação. Se PRESET_KEYS não os deixasse
    passar, o apply_preset os descartaria em silêncio e o look sairia genérico."""

    def _apply(self, name):
        return library.apply_caption_template(native.project()['style'], name)

    def test_rainbow_template_carries_color_mode(self):
        self.assertEqual(self._apply('🌈 Karaokê arco-íris')['caption_colors'], 'Arco-íris')

    def test_emoji_template_turns_emojis_on(self):
        self.assertTrue(self._apply('🔥 Viral com emoji')['caption_emojis'])

    def test_position_template_moves_to_middle(self):
        self.assertEqual(self._apply('🎙️ Podcast no meio')['caption_pos'], 'Meio')

    def test_alternada_template_carries_mode(self):
        self.assertEqual(self._apply('⚡ Salto alternado')['caption_colors'], 'Alternada')


class DynamicRenderTest(unittest.TestCase):
    """O que só o ambiente real pega: um look dinâmico (arco-íris + emoji +
    posição) tem de gerar um ASS que o libass aceita, não só passar no validate."""

    def test_dynamic_look_renders_through_libass(self):
        flat = core.project()
        flat.update(source='x', duration=3, width=1080, height=1920,
                    captions_enabled=True, caption_mode='Palavra ativa',
                    ranges=[{'start': 0, 'end': 3, 'enabled': True}],
                    words=[{'start': 0.0, 'end': 0.4, 'text': 'muito'},
                           {'start': 0.4, 'end': 0.9, 'text': 'fogo'},
                           {'start': 0.9, 'end': 1.4, 'text': 'agora'}])
        p = library.apply_caption_template(flat, '🌈 Karaokê arco-íris')
        p['caption_emojis'] = True  # cobre arco-íris + emoji + posição juntos
        core.validate(p, files=False)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'c.ass').write_text(core.make_ass(p), encoding='utf-8')
            r = subprocess.run(
                [core.ffmpeg(), '-v', 'error', '-f', 'lavfi',
                 '-i', 'color=c=gray:s=1080x1920:d=0.1',
                 '-vf', 'subtitles=c.ass', '-frames:v', '1', '-f', 'null', '-'],
                cwd=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(r.returncode, 0, r.stderr.decode(errors='replace')[:200])


if __name__ == '__main__':
    unittest.main()
