"""Organização da fila do DS HUB — agrupar por cliente e ordenar A–Z. Lógica pura."""
import unittest
import bridge


def _t(cliente, titulo, selo='X'):
    return dict(card_id=titulo, cliente=cliente, titulo=titulo, selo=selo)


class GroupQueueTests(unittest.TestCase):
    def test_groups_by_client_alpha_with_headers_and_count(self):
        rows = bridge.group_queue([
            _t('Zé Burger', 'Reels 1'),
            _t('Ateliê', 'Bolo'),
            _t('Ateliê', 'Antes'),
        ])
        # Ateliê (acento) vem antes de Zé; cabeçalho com contagem
        self.assertEqual(rows[0], ('header', 'Ateliê', 2))
        titles = [r[1]['titulo'] for r in rows if r[0] == 'item' and r[1]['cliente'] == 'Ateliê']
        self.assertEqual(titles, ['Antes', 'Bolo'])  # itens A–Z por título
        self.assertEqual(rows[3], ('header', 'Zé Burger', 1))

    def test_titulo_mode_is_flat_and_sorted(self):
        rows = bridge.group_queue([_t('B', 'banana'), _t('A', 'Abacate')], by='titulo')
        self.assertTrue(all(r[0] == 'item' for r in rows))
        self.assertEqual([r[1]['titulo'] for r in rows], ['Abacate', 'banana'])  # ignora maiúscula

    def test_empty_client_bucketed(self):
        rows = bridge.group_queue([_t('', 'sem dono')])
        self.assertEqual(rows[0], ('header', 'Sem cliente', 1))

    def test_empty(self):
        self.assertEqual(bridge.group_queue([]), [])


if __name__ == '__main__':
    unittest.main()
