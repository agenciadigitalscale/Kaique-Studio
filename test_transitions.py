"""Transições entre clipes (xfade). O nome amigável precisa virar um tipo que o
FFmpeg empacotado ACEITA — e isso só um render de verdade confirma, porque um
tipo inexistente falha na hora do xfade, não no validate."""
import subprocess, tempfile, unittest
from pathlib import Path
import core, library


def _make_source(path, seconds=4):
    """Um vídeo com áudio, para os dois lados do xfade (vídeo e acrossfade)."""
    exe = core.ffmpeg()
    subprocess.run(
        [exe, '-v', 'error', '-y',
         '-f', 'lavfi', '-i', f'testsrc=size=480x854:rate=30:duration={seconds}',
         '-f', 'lavfi', '-i', f'sine=frequency=440:duration={seconds}',
         '-c:v', 'libx264', '-c:a', 'aac', '-shortest', str(path)],
        check=True)


def _project(source, transition):
    p = core.project()
    p.update(source=str(source), duration=4, width=480, height=854,
             transition=transition, captions_enabled=False,
             # dois trechos: a transição só existe entre clipes.
             ranges=[{'start': 0, 'end': 2, 'enabled': True},
                     {'start': 2, 'end': 4, 'enabled': True}])
    return p


class TransitionCatalogTests(unittest.TestCase):
    def test_todas_no_catalogo_e_validam(self):
        for nome in core.TRANSITIONS:
            core.validate(_project('x', nome), files=False)  # não estoura

    def test_library_aceita_as_mesmas(self):
        # library não pode divergir do core, senão um preset trava no export.
        self.assertEqual(set(library._TRANSITIONS), set(core.TRANSITIONS))

    def test_rejeita_transicao_desconhecida(self):
        with self.assertRaises(ValueError):
            core.validate(_project('x', 'Buraco de minhoca'), files=False)


class TransitionRenderTests(unittest.TestCase):
    """O teste que só o ambiente real pega: cada tipo do xfade tem de renderizar."""

    def test_cada_xfade_renderiza(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            src = d / 'src.mp4'
            _make_source(src)
            for i, nome in enumerate(core.XFADE_MAP):
                out = d / f'out{i}.mp4'
                core.render(_project(src, nome), str(out))
                self.assertTrue(out.is_file(), f'{nome} não gerou arquivo')
                self.assertGreater(out.stat().st_size, 1000, f'{nome} gerou arquivo vazio')

    def test_corte_seco_e_fade_por_cor(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            src = d / 'src.mp4'
            _make_source(src)
            for nome in ('Nenhuma', 'Preto', 'Branco'):
                out = d / f'{nome}.mp4'
                core.render(_project(src, nome), str(out))
                self.assertTrue(out.is_file())


if __name__ == '__main__':
    unittest.main()
