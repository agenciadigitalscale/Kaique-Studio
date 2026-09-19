"""Efeitos sonoros embutidos: cada um TEM de ser gerado pelo ffmpeg (uma fonte/
filtro lavfi torto só apareceria como erro na hora de usar) e virar um .wav
tocável, com duração real."""
import subprocess
import tempfile
import unittest
from pathlib import Path
import core


class SfxTests(unittest.TestCase):
    def test_every_sfx_generates_valid_audio(self):
        exe = core.ffmpeg()
        with tempfile.TemporaryDirectory() as d:
            for name in core.SFX_BUILTIN:
                dest = Path(d) / f'{name}.wav'
                core.make_sfx(name, dest)
                self.assertTrue(dest.is_file(), f'{name}: arquivo não gerado')
                self.assertGreater(dest.stat().st_size, 1000, f'{name}: wav minúsculo')
                # decodifica de volta: prova que é áudio válido, não lixo
                r = subprocess.run([exe, '-v', 'error', '-i', str(dest), '-f', 'null', '-'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertEqual(r.returncode, 0, f'{name}: não decodifica ({r.stderr.decode()[:120]})')

    def test_unknown_name_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                core.make_sfx('não existe', Path(d) / 'x.wav')

    def test_every_sfx_has_category(self):
        # a categoria alimenta a coluna da galeria de sons
        for name, (cat, src, af) in core.SFX_BUILTIN.items():
            self.assertTrue(cat, f'{name} sem categoria')
            self.assertTrue(src, f'{name} sem fonte lavfi')


if __name__ == '__main__':
    unittest.main()
