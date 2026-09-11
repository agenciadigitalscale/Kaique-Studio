"""Legendas dinâmicas — o gerador ASS é texto puro, então testável sem render;
mais um render de confirmação de que o FFmpeg aceita o ASS animado."""
import subprocess, tempfile, unittest
from pathlib import Path
import core, native, library


def _project_with_words():
    p = core.project()
    p.update(source='x', duration=4, width=1080, height=1920,
             ranges=[{'start': 0, 'end': 4, 'enabled': True}],
             words=[{'start': 0.0, 'end': 0.5, 'text': 'Olha'},
                    {'start': 0.5, 'end': 1.0, 'text': 'só'},
                    {'start': 1.0, 'end': 1.6, 'text': 'isso'}])
    return p


class CaptionStyleTests(unittest.TestCase):
    def test_default_is_realce_no_animation(self):
        p = _project_with_words()
        ass = core.make_ass(p)
        self.assertNotIn(r'\t(', ass)  # Realce não anima
        self.assertIn('Dialogue:', ass)

    def test_pop_injects_scale_animation(self):
        p = _project_with_words(); p['caption_style'] = 'Pop'
        ass = core.make_ass(p)
        self.assertIn(r'\t(', ass)       # tem transição temporal (o "pop")
        self.assertIn(r'\fscx', ass)     # mexendo em escala

    def test_contorno_injects_thick_border(self):
        p = _project_with_words(); p['caption_style'] = 'Contorno'
        ass = core.make_ass(p)
        self.assertIn(r'\bord5', ass)

    def test_style_only_affects_active_word_mode(self):
        """Nos modos Frase/Palavras-chave a legenda mostra o grupo inteiro; o
        estilo de animação por palavra não deve vazar para lá."""
        p = _project_with_words(); p['caption_style'] = 'Pop'; p['caption_mode'] = 'Frase'
        ass = core.make_ass(p)
        # o pop da palavra ativa (fscx82) não aparece no modo Frase
        self.assertNotIn(r'\fscx82', ass)

    def test_validation_rejects_unknown_style(self):
        p = _project_with_words(); p['caption_style'] = 'Neon'
        with self.assertRaises(ValueError):
            core.validate(p, files=False)


class ModelIntegrationTests(unittest.TestCase):
    def test_caption_style_survives_native_round_trip(self):
        """O style do projeto nativo é reconstruído só com STYLE_KEYS — se
        caption_style não estivesse lá, um preset com 'Pop' se perderia."""
        self.assertIn('caption_style', native.STYLE_KEYS)
        p = native.project()
        p['style']['caption_style'] = 'Pop'
        flat = native.legacy(p)
        self.assertEqual(flat['caption_style'], 'Pop')

    def test_preset_can_carry_style_and_validates(self):
        self.assertIn('caption_style', library.PRESET_KEYS)
        library.validate_preset({'name': 'x', 'style': {'caption_style': 'Contorno'}})
        with self.assertRaises(ValueError):
            library.validate_preset({'name': 'x', 'style': {'caption_style': 'Glitch'}})

    def test_bundled_presets_use_new_styles(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / 'assets'; base.mkdir()
            (base / 'catalog.json').write_text('[]', encoding='utf-8')
            import shutil
            shutil.copyfile(Path(__file__).with_name('assets') / 'presets.json', base / 'presets.json')
            cat = library.Catalog(Path(d) / 'lib', base)
            styles = {q['title']: q['preset']['style'].get('caption_style') for q in cat.presets()}
            self.assertEqual(styles['Dinâmico de impacto'], 'Pop')
            self.assertEqual(styles['Preto e branco marcante'], 'Contorno')


class RenderTests(unittest.TestCase):
    """Confirma que o FFmpeg aceita o ASS com animação (o teste que só o
    ambiente real pega — o Pop injeta tags \\t que um ASS torto rejeitaria)."""

    def _make_clip(self, path, seconds=1):
        exe = core.ffmpeg()
        subprocess.run([exe, '-v', 'error', '-y', '-f', 'lavfi', '-i',
                        f'testsrc=size=1080x1920:rate=30:duration={seconds}',
                        '-f', 'lavfi', '-i', f'sine=frequency=440:duration={seconds}',
                        '-c:v', 'libx264', '-c:a', 'aac', '-shortest', str(path)], check=True)

    def test_pop_style_renders(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            clip = d / 'src.mp4'; self._make_clip(clip)
            p = core.project()
            p.update(source=str(clip), duration=1, width=1080, height=1920,
                     caption_style='Pop',
                     ranges=[{'start': 0, 'end': 1, 'enabled': True}],
                     words=[{'start': 0.0, 'end': 0.4, 'text': 'Vai'},
                            {'start': 0.4, 'end': 0.9, 'text': 'agora'}])
            out = core.render(p, str(d / 'out.mp4'))
            self.assertTrue(Path(out).is_file())
            self.assertGreater(Path(out).stat().st_size, 1000)


if __name__ == '__main__':
    unittest.main()
