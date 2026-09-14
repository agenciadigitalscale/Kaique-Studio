"""Ponte com o DS HUB — parse da fila, nome de export e entrega. Rede injetada,
roda offline (um teste que dependesse do painel no ar falharia por rede, não por bug)."""
import json, tempfile, unittest
from pathlib import Path
import bridge


class ConfigTests(unittest.TestCase):
    def test_defaults_when_missing(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = bridge.load_config(d)
            self.assertEqual(cfg['base'], bridge.DEFAULT_BASE)
            self.assertEqual(cfg['key'], '')

    def test_save_then_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            bridge.save_config(d, 'https://painel.exemplo', '  minha-chave  ')
            cfg = bridge.load_config(d)
            self.assertEqual(cfg['base'], 'https://painel.exemplo')
            self.assertEqual(cfg['key'], 'minha-chave')  # trim

    def test_corrupt_file_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            Path(bridge.config_path(d)).write_text('{lixo', encoding='utf-8')
            self.assertEqual(bridge.load_config(d)['base'], bridge.DEFAULT_BASE)


QUEUE = {'queue': [
    {'card_id': '2007', 'cliente': 'Lorenzeti', 'titulo': 'Vídeo Chuveiro', 'selo': '05NX'},
    {'card_id': '3012', 'cliente': 'Kátia', 'titulo': 'Reel receita'},  # sem selo
]}


class ParseQueueTests(unittest.TestCase):
    def test_parses_valid_queue(self):
        tasks = bridge.parse_queue(json.dumps(QUEUE))
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]['selo'], '05NX')
        self.assertEqual(tasks[1]['selo'], '')  # ausente vira string vazia

    def test_skips_items_without_id_or_title(self):
        tasks = bridge.parse_queue({'queue': [
            {'cliente': 'X'},                       # sem card_id/titulo
            {'card_id': '9', 'titulo': 'Bom'},
        ]})
        self.assertEqual([t['card_id'] for t in tasks], ['9'])

    def test_invalid_shape_raises(self):
        with self.assertRaises(ValueError):
            bridge.parse_queue({'nope': 1})
        with self.assertRaises(ValueError):
            bridge.parse_queue('nao-e-json')


class ExportNameTests(unittest.TestCase):
    def test_with_selo(self):
        t = {'cliente': 'Lorenzeti', 'titulo': 'Vídeo Chuveiro', 'selo': '05NX'}
        self.assertEqual(bridge.export_name(t), 'Lorenzeti - Vídeo Chuveiro [05NX]')

    def test_without_selo_and_no_double_extension(self):
        t = {'cliente': 'Kátia', 'titulo': 'Reel', 'selo': ''}
        name = bridge.export_name(t)
        self.assertEqual(name, 'Kátia - Reel')
        self.assertNotIn('.mp4', name)


class DeliveryTests(unittest.TestCase):
    def test_payload_shape(self):
        body = bridge.delivery_payload({'card_id': '2007'}, 'https://drive/x')
        self.assertEqual(body, {'card_id': '2007', 'link': 'https://drive/x', 'source': 'kaique-studio'})

    def test_empty_link_raises(self):
        with self.assertRaises(ValueError):
            bridge.delivery_payload({'card_id': '2007'}, '')

    def test_fetch_queue_uses_injected_fetch_and_key(self):
        seen = {}
        def fake(url, key):
            seen['url'] = url; seen['key'] = key; return json.dumps(QUEUE)
        tasks = bridge.fetch_queue(base='https://painel.exemplo', fetch=fake, key='segredo')
        self.assertEqual(seen['url'], 'https://painel.exemplo/api/studio-queue')
        self.assertEqual(seen['key'], 'segredo')
        self.assertEqual(len(tasks), 2)

    def test_deliver_posts_payload(self):
        sent = {}
        def fake_post(url, body, key):
            sent['url'] = url; sent['body'] = json.loads(body); sent['key'] = key; return b'{"ok":true}'
        bridge.deliver({'card_id': '3012'}, 'C:/videos/out.mp4', base='https://p', post=fake_post, key='k')
        self.assertEqual(sent['url'], 'https://p/api/studio-deliver')
        self.assertEqual(sent['body']['card_id'], '3012')
        self.assertEqual(sent['key'], 'k')


if __name__ == '__main__':
    unittest.main()
