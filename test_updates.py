"""Canal de atualização — a lógica de 'o que é novo / instalar' roda sem rede,
com o download injetado. Um teste que dependesse da internet não valeria como
verificação: falharia por rede, não por bug."""
import json, tempfile, unittest
from pathlib import Path
import library, updates


def _bundled(dirpath):
    base = Path(dirpath) / 'assets'
    base.mkdir()
    (base / 'catalog.json').write_text(json.dumps([
        {'id': 'sfx1', 'title': 'Pop', 'kind': 'Efeitos sonoros', 'category': 'Interface', 'path': 'pop.wav'},
    ]), encoding='utf-8')
    (base / 'presets.json').write_text('[]', encoding='utf-8')
    (base / 'pop.wav').write_bytes(b'RIFF')
    return base


def _catalog(d):
    return library.Catalog(Path(d) / 'lib', _bundled(d))


MANIFEST = {'packs': [
    {'id': 'up_boom', 'kind': 'Efeitos sonoros', 'title': 'Boom cinematográfico',
     'category': 'Impacto', 'ext': '.mp3', 'url': 'https://exemplo/boom.mp3'},
    {'id': 'up_preset_neon', 'kind': 'Presets', 'title': 'Neon urbano',
     'preset': {'name': 'Neon urbano', 'style': {'filter': 'Vívido', 'caption_style': 'Pop'}}},
]}


class ManifestTests(unittest.TestCase):
    def test_parse_accepts_valid_manifest(self):
        packs = updates.parse_manifest(json.dumps(MANIFEST))
        self.assertEqual(len(packs), 2)

    def test_parse_rejects_unknown_kind_and_bad_ext(self):
        with self.assertRaises(ValueError):
            updates.parse_manifest({'packs': [{'id': 'x', 'kind': 'Foguetes', 'title': 't', 'ext': '.mp3', 'url': 'https://a/b'}]})
        with self.assertRaises(ValueError):
            updates.parse_manifest({'packs': [{'id': 'x', 'kind': 'Músicas', 'title': 't', 'ext': '.exe', 'url': 'https://a/b'}]})

    def test_parse_rejects_non_http_url(self):
        # um manifesto não pode mandar o app abrir file:// nem javascript:
        with self.assertRaises(ValueError):
            updates.parse_manifest({'packs': [{'id': 'x', 'kind': 'Músicas', 'title': 't', 'ext': '.mp3', 'url': 'file:///etc/passwd'}]})

    def test_parse_rejects_invalid_embedded_preset(self):
        with self.assertRaises(ValueError):
            updates.parse_manifest({'packs': [{'id': 'x', 'kind': 'Presets', 'title': 't',
                                               'preset': {'name': 'x', 'style': {'filter': 'Inexistente'}}}]})


class SyncTests(unittest.TestCase):
    def test_sync_installs_new_and_is_incremental(self):
        with tempfile.TemporaryDirectory() as d:
            cat = _catalog(d)
            downloads = {'https://exemplo/boom.mp3': b'\x00\x01\x02fake-audio'}
            result = updates.sync(cat, fetch=lambda _u: json.dumps(MANIFEST),
                                  download=lambda u: downloads[u])
            self.assertEqual(result['added'], 2)
            self.assertEqual(result['errors'], [])
            # o som virou item e o arquivo foi gravado
            boom = [i for i in cat.items() if i['id'] == 'up_boom'][0]
            self.assertTrue(Path(boom['path']).is_file())
            self.assertEqual(boom['source'], 'update')
            # o preset entrou no acervo
            self.assertIn('Neon urbano', [p['title'] for p in cat.presets()])

            # rodar de novo com o MESMO manifesto não baixa nada (incremental)
            again = updates.sync(cat, fetch=lambda _u: json.dumps(MANIFEST),
                                 download=lambda u: downloads[u])
            self.assertEqual(again['added'], 0)
            self.assertEqual(again['total'], 2)

    def test_one_broken_download_does_not_block_the_others(self):
        with tempfile.TemporaryDirectory() as d:
            cat = _catalog(d)

            def flaky(url):
                raise OSError('conexão caiu')  # o arquivo falha; o preset não baixa

            result = updates.sync(cat, fetch=lambda _u: json.dumps(MANIFEST), download=flaky)
            # o preset não depende de download e entra; o som falha e é reportado
            self.assertEqual(result['added'], 1)
            self.assertEqual(len(result['errors']), 1)
            self.assertIn('Neon urbano', [p['title'] for p in cat.presets()])

    def test_reinstall_after_manifest_reissue_reflects_state(self):
        with tempfile.TemporaryDirectory() as d:
            cat = _catalog(d)
            only_preset = {'packs': [MANIFEST['packs'][1]]}
            r = updates.sync(cat, fetch=lambda _u: json.dumps(only_preset), download=lambda _u: b'')
            self.assertEqual(r['added'], 1)
            self.assertEqual(r['total'], 1)


if __name__ == '__main__':
    unittest.main()
