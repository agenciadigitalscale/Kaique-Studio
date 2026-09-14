"""Destaque automático de palavras-chave — o app escolhe as palavras de conteúdo
quando o editor não digita nenhuma. Lógica pura + checagem no make_ass."""
import unittest
import core


class ContentKeywordsTests(unittest.TestCase):
    def test_drops_stopwords_and_short_words(self):
        keys = core.content_keywords(['o', 'gato', 'de', 'olhos', 'azuis'])
        self.assertIn('gato', keys)
        self.assertIn('olhos', keys)
        self.assertIn('azuis', keys)
        self.assertNotIn('de', keys)     # stopword
        self.assertNotIn('o', keys)      # curta demais

    def test_normalizes_accents_and_punctuation(self):
        keys = core.content_keywords(['Coração,', 'PROMOÇÃO!'])
        self.assertIn('coracao', keys)     # minúscula, sem acento, sem vírgula
        self.assertIn('promocao', keys)

    def test_common_fillers_are_stopwords(self):
        keys = core.content_keywords(['muito', 'para', 'voce', 'entao', 'produto'])
        self.assertEqual(keys, {'produto'})

    def test_empty(self):
        self.assertEqual(core.content_keywords([]), set())


class MakeAssAutoHighlightTests(unittest.TestCase):
    def _project(self, mode, keywords=''):
        p = core.project()
        p.update(source='x', duration=4, width=1080, height=1920, captions_enabled=True,
                 caption_mode=mode, keywords=keywords, color='#C9FF63',
                 ranges=[{'start': 0, 'end': 4, 'enabled': True}],
                 words=[{'start': 0.0, 'end': 0.5, 'text': 'o'},
                        {'start': 0.6, 'end': 1.4, 'text': 'produto'}])
        return p

    def test_keywords_mode_auto_highlights_content_word(self):
        ass = core.make_ass(self._project('Palavras-chave'))
        accent = core.ass_color('#C9FF63')
        # 'produto' recebe a cor de destaque; 'o' (stopword curta) NÃO
        self.assertIn('{\\c' + accent + '}' + 'produto', ass)
        self.assertNotIn('{\\c' + accent + '}' + 'o ', ass)

    def test_manual_keywords_still_win(self):
        # se o editor digitou algo, respeita a escolha dele (não auto)
        ass = core.make_ass(self._project('Palavras-chave', keywords='produto'))
        self.assertIn('produto', ass)


if __name__ == '__main__':
    unittest.main()
