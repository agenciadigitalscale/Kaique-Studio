"""Legenda inteligente — agrupamento das palavras em frases legíveis.
Lógica pura (group_words), mais uma checagem de que make_ass usa esse agrupamento."""
import unittest
import core


def _w(text, start, end):
    return dict(text=text, start=start, end=end)


class GroupWordsTests(unittest.TestCase):
    def _seq(self, texts, gap=0.1, dur=0.3):
        words, t = [], 0.0
        for tx in texts:
            words.append(_w(tx, round(t, 3), round(t + dur, 3))); t += dur + gap
        return words

    def test_breaks_on_sentence_end(self):
        # "acabou." força a próxima palavra a começar um grupo novo
        words = self._seq(['isso', 'acabou.', 'agora', 'vai'])
        groups = core.group_words(words)
        self.assertEqual([w['text'] for w in groups[0]], ['isso', 'acabou.'])
        self.assertEqual(groups[1][0]['text'], 'agora')

    def test_breaks_on_long_pause(self):
        words = [_w('antes', 0.0, 0.3), _w('depois', 1.5, 1.8)]  # pausa de 1.2s
        groups = core.group_words(words, gap=0.45)
        self.assertEqual(len(groups), 2)

    def test_breaks_on_char_limit(self):
        words = self._seq(['palavragrande', 'outrapalavragrande'])  # >30 chars juntas
        groups = core.group_words(words, max_chars=20)
        self.assertEqual(len(groups), 2)

    def test_breaks_on_word_count(self):
        words = self._seq(['a', 'b', 'c', 'd', 'e', 'f'])
        groups = core.group_words(words, max_words=3, max_chars=99, gap=99)
        self.assertTrue(all(len(g) <= 3 for g in groups))
        self.assertEqual(len(groups), 2)

    def test_short_phrase_stays_together(self):
        words = self._seq(['olha', 'só', 'isso'])
        self.assertEqual(len(core.group_words(words)), 1)

    def test_empty(self):
        self.assertEqual(core.group_words([]), [])


class MakeAssUsesGroupingTests(unittest.TestCase):
    def test_make_ass_splits_sentences_into_separate_lines(self):
        p = core.project()
        p.update(source='x', duration=4, width=1080, height=1920, captions_enabled=True,
                 caption_mode='Frase', ranges=[{'start': 0, 'end': 4, 'enabled': True}],
                 words=[_w('primeira.', 0.0, 0.5), _w('segunda', 0.6, 1.1), _w('frase', 1.2, 1.7)])
        dialogues = [ln for ln in core.make_ass(p).splitlines() if ln.startswith('Dialogue:')]
        # a frase que termina em "." fica numa linha, o resto em outra
        self.assertEqual(len(dialogues), 2)


if __name__ == '__main__':
    unittest.main()
