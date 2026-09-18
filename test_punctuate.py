import unittest
import core


def w(text, start, end):
    return dict(text=text, start=start, end=end)


class TestPunctuateWords(unittest.TestCase):
    def test_pausa_longa_vira_ponto(self):
        words = [w('bora', 0.0, 0.4), w('gente', 0.5, 0.9), w('vamos', 1.8, 2.2)]
        out = core.punctuate_words(words, comma_gap=0.32, period_gap=0.72)
        # gap gente->vamos = 0.9s >= 0.72 => ponto em "gente"
        self.assertEqual(out[1]['text'], 'gente.')
        # última palavra sempre ganha ponto
        self.assertEqual(out[2]['text'], 'vamos.')

    def test_pausa_media_vira_virgula(self):
        words = [w('ola', 0.0, 0.4), w('mundo', 0.85, 1.2)]
        # gap ola->mundo = 0.45s: >=0.32 e <0.72 => vírgula
        out = core.punctuate_words(words)
        self.assertEqual(out[0]['text'], 'ola,')

    def test_pausa_curta_nao_pontua(self):
        words = [w('muito', 0.0, 0.4), w('legal', 0.45, 0.8)]
        # gap 0.05s: nada
        out = core.punctuate_words(words)
        self.assertEqual(out[0]['text'], 'muito')

    def test_respeita_pontuacao_existente(self):
        words = [w('incrivel!', 0.0, 0.4), w('demais', 1.5, 2.0)]
        out = core.punctuate_words(words)
        # não vira "incrivel!." — já tinha pontuação
        self.assertEqual(out[0]['text'], 'incrivel!')

    def test_nao_muta_original(self):
        words = [w('teste', 0.0, 0.4), w('agora', 2.0, 2.4)]
        antes = [dict(x) for x in words]
        core.punctuate_words(words)
        self.assertEqual(words, antes)

    def test_lista_vazia(self):
        self.assertEqual(core.punctuate_words([]), [])

    def test_enhance_pontua_e_capitaliza(self):
        words = [w('bom', 0.0, 0.3), w('dia', 0.4, 0.7),
                 w('vamos', 1.8, 2.2), w('comecar', 2.3, 2.8)]
        out = core.enhance_transcript(words)
        # "dia" ganha ponto pela pausa; "vamos" (início de nova frase) capitaliza
        self.assertEqual(out[1]['text'], 'dia.')
        self.assertEqual(out[2]['text'], 'Vamos')
        # primeira palavra sempre capitalizada
        self.assertEqual(out[0]['text'], 'Bom')

    def test_enhance_sem_pontuacao(self):
        words = [w('bom', 0.0, 0.3), w('dia', 2.0, 2.4)]
        out = core.enhance_transcript(words, punctuate=False)
        # sem pontuação automática: "bom" não ganha ponto, só capitaliza a 1ª
        self.assertEqual(out[0]['text'], 'Bom')
        self.assertEqual(out[1]['text'], 'dia')


if __name__ == '__main__':
    unittest.main()
