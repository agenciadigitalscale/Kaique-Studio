"""Cadastro dos efeitos sonoros embutidos no acervo (Catalog.ensure_builtin_sfx)."""
import tempfile
import unittest
from pathlib import Path
from resource_library import Catalog
import core

ASSETS = Path(__file__).parent / 'assets'


class BuiltinSfxTests(unittest.TestCase):
    def test_generates_and_registers_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            cat = Catalog(tmp, ASSETS)
            novos = cat.ensure_builtin_sfx()
            self.assertEqual(len(novos), len(core.SFX_BUILTIN))
            # cada um virou um .wav de verdade, do tipo certo
            for e in novos:
                self.assertEqual(e['kind'], 'Efeitos sonoros')
                self.assertTrue(Path(e['path']).is_file())
                self.assertGreater(Path(e['path']).stat().st_size, 1000)
            # aparecem no acervo carregado numa nova sessão
            recarregado = Catalog(tmp, ASSETS)
            titulos = {e['title'] for e in recarregado.data['items']}
            self.assertTrue(set(core.SFX_BUILTIN).issubset(titulos))

    def test_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            cat = Catalog(tmp, ASSETS)
            cat.ensure_builtin_sfx()
            # segunda chamada não adiciona nada nem duplica
            self.assertEqual(cat.ensure_builtin_sfx(), [])
            ids = [e['id'] for e in cat.data['items']]
            self.assertEqual(len(ids), len(set(ids)))


if __name__ == '__main__':
    unittest.main()
