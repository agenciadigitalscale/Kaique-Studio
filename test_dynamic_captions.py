"""Kit de legendas dinâmicas — CADA estilo tem de ser aceito pelo libass (uma tag
ASS torta só apareceria como erro na exportação, na cara do editor)."""
import subprocess, tempfile, unittest
from pathlib import Path
import core


def _project(style):
    p = core.project()
    p.update(source='x', duration=3, width=1080, height=1920, captions_enabled=True,
             caption_mode='Palavra ativa', caption_style=style, color='#C9FF63',
             ranges=[{'start': 0, 'end': 3, 'enabled': True}],
             words=[{'start': 0.0, 'end': 0.4, 'text': 'legenda'},
                    {'start': 0.4, 'end': 0.9, 'text': 'dinâmica'},
                    {'start': 0.9, 'end': 1.4, 'text': 'animada'}])
    return p


class DynamicCaptionTests(unittest.TestCase):
    def test_every_style_is_accepted_by_libass(self):
        exe = core.ffmpeg()
        with tempfile.TemporaryDirectory() as d:
            for style in core.CAPTION_STYLES:
                ass = core.make_ass(_project(style))
                self.assertIn('Dialogue:', ass, style)
                (Path(d) / 'c.ass').write_text(ass, encoding='utf-8')
                # cwd na pasta + nome simples: caminho do Windows com ':' quebra o
                # parser de opções do filtro subtitles.
                r = subprocess.run(
                    [exe, '-v', 'error', '-f', 'lavfi', '-i', 'color=c=gray:s=1080x1920:d=0.1',
                     '-vf', 'subtitles=c.ass', '-frames:v', '1', '-f', 'null', '-'],
                    cwd=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                detail = r.stderr.decode(errors='replace')[:200]
                self.assertEqual(r.returncode, 0, f'Estilo {style!r} rejeitado: {detail}')

    def test_validation_accepts_new_styles(self):
        base = _project('Neon')
        for style in ['Salto', 'Zoom', 'Giro', 'Sombra', 'Pulsar', 'Contorno grosso']:
            core.validate(dict(base, caption_style=style), files=False)
        with self.assertRaises(ValueError):
            core.validate(dict(base, caption_style='Glitch3D'), files=False)


if __name__ == '__main__':
    unittest.main()
