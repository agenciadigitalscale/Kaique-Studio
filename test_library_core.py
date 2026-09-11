"""Núcleo da biblioteca — testável sem Qt (por isso `library.py` foi separado)."""
import json, tempfile, unittest
from pathlib import Path
import core, native, library


def _bundled(dirpath):
    """Cria uma pasta 'assets' mínima (catálogo + presets) para o Catalog ler."""
    base = Path(dirpath) / 'assets'
    base.mkdir()
    (base / 'catalog.json').write_text(json.dumps([
        {'id': 'sfx1', 'title': 'Pop', 'kind': 'Efeitos sonoros', 'category': 'Interface', 'path': 'pop.wav'},
    ]), encoding='utf-8')
    (base / 'presets.json').write_text(json.dumps([
        {'id': 'p_quente', 'name': 'Gastronomia quente', 'category': 'Gastronomia',
         'description': 'x', 'style': {'filter': 'Quente', 'caption_mode': 'Palavra ativa'}},
    ]), encoding='utf-8')
    (base / 'pop.wav').write_bytes(b'RIFF')
    return base


class PresetTests(unittest.TestCase):
    def test_apply_preset_overrides_and_does_not_mutate(self):
        style = native.project()['style']
        original_filter = style['filter']
        out = library.apply_preset(style, {'name': 'x', 'style': {'filter': 'Quente', 'zoom': 1.1}})
        self.assertEqual(out['filter'], 'Quente')
        self.assertEqual(out['zoom'], 1.1)
        # o style recebido não muda — aplicar tem desfazer no editor
        self.assertEqual(style['filter'], original_filter)

    def test_applied_preset_passes_core_validation(self):
        """Aplicar um preset bundled tem de gerar um projeto que o core aceita —
        senão o combo 'pronto' quebraria só na hora de exportar."""
        with tempfile.TemporaryDirectory() as d:
            base = _bundled(d)
            cat = library.Catalog(Path(d) / 'lib', base)
            preset = cat.presets()[0]['preset']
            flat = core.project()
            flat.update(source='x', duration=5, width=1080, height=1920,
                        ranges=[{'start': 0, 'end': 5, 'enabled': True}])
            flat = library.apply_preset(flat, preset)
            core.validate(flat, files=False)  # não estoura

    def test_reject_unknown_key(self):
        with self.assertRaises(ValueError):
            library.validate_preset({'name': 'x', 'style': {'clips': []}})

    def test_reject_out_of_range(self):
        for bad in [{'font_size': 99}, {'zoom': 2.0}, {'music_volume': 5}, {'color': 'azul'},
                    {'filter': 'Neon'}, {'transition': 'Espiral'}, {'caption_mode': 'Karaokê'}]:
            with self.assertRaises(ValueError):
                library.validate_preset({'name': 'x', 'style': bad})

    def test_reject_nameless_or_empty(self):
        with self.assertRaises(ValueError):
            library.validate_preset({'name': '  ', 'style': {'filter': 'Quente'}})
        with self.assertRaises(ValueError):
            library.validate_preset({'name': 'x', 'style': {}})


class CatalogTests(unittest.TestCase):
    def test_bundled_paths_resolved_and_user_presets_persist(self):
        with tempfile.TemporaryDirectory() as d:
            base = _bundled(d)
            lib = Path(d) / 'lib'
            cat = library.Catalog(lib, base)
            # o item bundled sai com caminho absoluto resolvido
            self.assertTrue(Path(cat.items()[0]['path']).is_absolute())
            # presets bundled aparecem como itens de biblioteca
            self.assertEqual(cat.presets()[0]['kind'], 'Presets')
            # salvar um preset do usuário persiste e reabre
            cat.save_preset('Meu estilo', native.project()['style'], 'Outros')
            reopened = library.Catalog(lib, base)
            names = [p['title'] for p in reopened.presets()]
            self.assertIn('Meu estilo', names)
            self.assertIn('Gastronomia quente', names)  # bundled continua

    def test_cannot_remove_bundled_preset(self):
        with tempfile.TemporaryDirectory() as d:
            base = _bundled(d)
            cat = library.Catalog(Path(d) / 'lib', base)
            with self.assertRaises(ValueError):
                cat.remove_preset('p_quente')  # é do app, não removível

    def test_old_catalog_without_presets_key_still_loads(self):
        """Um catálogo gravado antes dos presets não tem a chave 'presets' —
        abrir não pode quebrar nem perder os itens do usuário."""
        with tempfile.TemporaryDirectory() as d:
            base = _bundled(d)
            lib = Path(d) / 'lib'
            lib.mkdir()
            (lib / 'catalogo.json').write_text(json.dumps(
                {'items': [{'id': 'u1', 'title': 'meu', 'kind': 'Músicas', 'category': 'Outros', 'path': 'x'}],
                 'favorites': ['u1']}), encoding='utf-8')
            cat = library.Catalog(lib, base)
            self.assertEqual(cat.data['presets'], [])
            self.assertIn('u1', cat.data['favorites'])
            cat.save_preset('novo', native.project()['style'])  # não estoura


if __name__ == '__main__':
    unittest.main()
