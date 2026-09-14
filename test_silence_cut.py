"""Corte automático de silêncios — intensidade Leve/Médio/Agressivo. Lógica pura:
`suggest_ranges` (núcleo) e `suggest_cuts` (aplica nos clipes, sem tocar arquivo)."""
import unittest
import core, native


def _words(gaps):
    """Palavras de 0,3s separadas por `gaps` segundos de silêncio entre elas."""
    words = [dict(start=0.0, end=0.3, text='a')]
    t = 0.3
    for g in gaps:
        t += g
        words.append(dict(start=round(t, 3), end=round(t + 0.3, 3), text='b'))
        t += 0.3
    return words, t


class SuggestRangesTests(unittest.TestCase):
    def test_levels_are_ordered_aggressive_cuts_more(self):
        self.assertGreater(core.SILENCE_LEVELS['Leve'], core.SILENCE_LEVELS['Médio'])
        self.assertGreater(core.SILENCE_LEVELS['Médio'], core.SILENCE_LEVELS['Agressivo'])

    def test_more_aggressive_keeps_less_total(self):
        # pausas de 0,5s e 0,8s entre as falas
        words, total = _words([0.5, 0.8])
        kept = lambda th: sum(r['end'] - r['start'] for r in core.suggest_ranges(words, total, threshold=th))
        leve = kept(core.SILENCE_LEVELS['Leve'])       # 1.0s: não corta nenhuma
        medio = kept(core.SILENCE_LEVELS['Médio'])     # 0.65s: corta a de 0.8
        agr = kept(core.SILENCE_LEVELS['Agressivo'])   # 0.35s: corta as duas
        self.assertGreater(leve, medio)
        self.assertGreater(medio, agr)

    def test_no_words_raises(self):
        with self.assertRaises(ValueError):
            core.suggest_ranges([], 10)


class SuggestCutsTests(unittest.TestCase):
    def _project(self, gaps):
        words, dur = _words(gaps)
        p = native.project()
        p['clips'] = [dict(id='c1', source='x.mp4', duration=dur, width=1080, height=1920,
                           **{'in': 0.0, 'out': dur}, words=words, thumbs=[], peaks=[], proxy='')]
        return p, dur

    def test_threshold_changes_final_length(self):
        p_agr, dur = self._project([0.5, 0.8])
        native.suggest_cuts(p_agr, threshold=core.SILENCE_LEVELS['Agressivo'])
        p_leve, _ = self._project([0.5, 0.8])
        native.suggest_cuts(p_leve, threshold=core.SILENCE_LEVELS['Leve'])
        # agressivo encurta mais que leve, e leve não passa do tamanho original
        self.assertLess(native.length(p_agr), native.length(p_leve))
        self.assertLessEqual(native.length(p_leve), dur + 0.01)

    def test_default_threshold_still_works(self):
        p, _ = self._project([1.5])
        native.suggest_cuts(p)  # sem threshold — caminho antigo (comando "cortar pausas")
        self.assertTrue(p['clips'])


if __name__ == '__main__':
    unittest.main()
