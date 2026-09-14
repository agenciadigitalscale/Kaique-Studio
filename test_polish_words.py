"""Capitalização automática da transcrição (polish_words) — parte segura da
'pontuação automática'. Não inventa pontuação, só arruma as maiúsculas."""
import unittest
import core


def _w(text, i):
    return dict(text=text, start=float(i), end=i + 0.5)


class PolishWordsTests(unittest.TestCase):
    def test_capitalizes_first_word(self):
        out = core.polish_words([_w('olá', 0), _w('mundo', 1)])
        self.assertEqual(out[0]['text'], 'Olá')
        self.assertEqual(out[1]['text'], 'mundo')  # meio de frase fica como está

    def test_capitalizes_after_sentence_end(self):
        out = core.polish_words([_w('isso', 0), _w('acabou.', 1), _w('agora', 2), _w('vai', 3)])
        self.assertEqual(out[2]['text'], 'Agora')  # depois do ponto
        self.assertEqual(out[3]['text'], 'vai')

    def test_does_not_invent_punctuation(self):
        # nada de pontos/vírgulas novos — o texto só muda na 1ª letra
        out = core.polish_words([_w('bom', 0), _w('dia', 1)])
        self.assertEqual(out[1]['text'], 'dia')
        self.assertNotIn('.', ''.join(w['text'] for w in out))

    def test_leading_quote_is_skipped(self):
        out = core.polish_words([_w('"ele', 0)])
        self.assertEqual(out[0]['text'], '"Ele')

    def test_preserves_times_and_does_not_mutate(self):
        original = [_w('a', 0)]
        out = core.polish_words(original)
        self.assertEqual(out[0]['start'], original[0]['start'])
        self.assertEqual(original[0]['text'], 'a')  # original intacto

    def test_empty(self):
        self.assertEqual(core.polish_words([]), [])


if __name__ == '__main__':
    unittest.main()
