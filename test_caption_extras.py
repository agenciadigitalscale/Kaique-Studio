"""Cores por palavra (arco-íris/alternada) e emojis automáticos na legenda."""
import subprocess, tempfile, unittest
from pathlib import Path
import core, native


class ColorModeTests(unittest.TestCase):
    def test_unica_is_base(self):
        self.assertEqual(core.caption_color_for('Única', 3, '#C9FF63'), '#C9FF63')

    def test_rainbow_cycles(self):
        cores = [core.caption_color_for('Arco-íris', i, '#C9FF63') for i in range(7)]
        self.assertEqual(len(set(cores[:6])), 6)      # 6 cores distintas
        self.assertEqual(cores[0], cores[6])          # cicla

    def test_alternada_includes_base_and_varies(self):
        c0 = core.caption_color_for('Alternada', 0, '#C9FF63')
        c1 = core.caption_color_for('Alternada', 1, '#C9FF63')
        self.assertEqual(c0, '#C9FF63')
        self.assertNotEqual(c0, c1)


class EmojiTests(unittest.TestCase):
    def test_maps_and_ignores_accents_punct(self):
        self.assertEqual(core.emoji_for('fogo'), '🔥')
        self.assertEqual(core.emoji_for('Coração,'), '❤️')
        self.assertEqual(core.emoji_for('banana'), '')

    def test_in_style_keys(self):
        self.assertIn('caption_colors', native.STYLE_KEYS)
        self.assertIn('caption_emojis', native.STYLE_KEYS)


class MakeAssIntegration(unittest.TestCase):
    def _p(self, **extra):
        p = core.project()
        p.update(source='x', duration=3, width=1080, height=1920, captions_enabled=True,
                 caption_mode='Palavra ativa', color='#C9FF63',
                 ranges=[{'start': 0, 'end': 3, 'enabled': True}],
                 words=[{'start': 0.0, 'end': 0.4, 'text': 'muito'},
                        {'start': 0.4, 'end': 0.9, 'text': 'fogo'},
                        {'start': 0.9, 'end': 1.4, 'text': 'agora'}], **extra)
        return p

    def test_rainbow_produces_several_colors(self):
        ass = core.make_ass(self._p(caption_colors='Arco-íris'))
        cores = set(core._RAINBOW)
        achadas = sum(1 for hexc in cores if core.ass_color(hexc) in ass)
        self.assertGreaterEqual(achadas, 3)

    def test_emoji_appended(self):
        ass = core.make_ass(self._p(caption_emojis=True))
        self.assertIn('🔥', ass)  # 'fogo' virou fogo 🔥

    def test_rainbow_and_emoji_accepted_by_libass(self):
        with tempfile.TemporaryDirectory() as d:
            ass = core.make_ass(self._p(caption_colors='Arco-íris', caption_emojis=True))
            (Path(d) / 'c.ass').write_text(ass, encoding='utf-8')
            r = subprocess.run(
                [core.ffmpeg(), '-v', 'error', '-f', 'lavfi', '-i', 'color=c=gray:s=1080x1920:d=0.1',
                 '-vf', 'subtitles=c.ass', '-frames:v', '1', '-f', 'null', '-'],
                cwd=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(r.returncode, 0, r.stderr.decode(errors='replace')[:200])


if __name__ == '__main__':
    unittest.main()
