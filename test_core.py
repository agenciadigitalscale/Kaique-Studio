import copy, tempfile, unittest
from pathlib import Path
import core

class EditingTests(unittest.TestCase):
    def setUp(self):
        self.p=core.project();self.p.update(source='sample.mp4',duration=5,width=320,height=240)
        self.p['ranges']=[dict(start=0,end=1,enabled=True),dict(start=3,end=5,enabled=True)]
        self.p['words']=[dict(start=.1,end=.7,text='Olá'),dict(start=3.2,end=3.8,text='Kaique')]
    def test_timestamp_mapping(self):
        w=core.mapped_words(self.p)
        self.assertAlmostEqual(w[1]['start'],1.2)
        self.assertAlmostEqual(core.duration(self.p),3)
    def test_cuts_keep_word_padding(self):
        r=core.suggest_ranges(self.p['words'],5)
        self.assertEqual(len(r),2);self.assertLessEqual(r[1]['start'],3.2);self.assertGreaterEqual(r[1]['end'],3.8)
    def test_validation(self):
        core.validate(self.p,False)
        self.p['ranges'][1]['start']=.5
        with self.assertRaises(ValueError):core.validate(self.p,False)
    def test_command_scope(self):
        actions,unknown=core.commands('legendas dinâmicas; filtro quente; volume música 15%; escolha o melhor take')
        self.assertEqual(len(actions),3);self.assertEqual(unknown,['escolha o melhor take'])
        self.assertTrue(core.commands('volume música 200%')[1])
    def test_caption_highlight(self):
        text=core.make_ass(self.p)
        self.assertIn('Kaique',text);self.assertIn('0:00:01.20',text);self.assertIn('\\c&H63FFC9&',text)
    def test_render(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);exe=core.ffmpeg()
            core.run([exe,'-v','error','-f','lavfi','-i','testsrc2=size=320x240:rate=30:duration=5','-f','lavfi','-i','sine=frequency=440:duration=5','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(d/'source.mp4')])
            core.run([exe,'-v','error','-f','lavfi','-i','sine=frequency=220:duration=1',str(d/'music.wav')])
            Image.new('RGBA',(60,60),(255,0,0,180)).save(d/'sticker.png')
            p=copy.deepcopy(self.p);p['source']=str(d/'source.mp4');p['music']=str(d/'music.wav');p['filter']='Quente';p['zoom']=1.1
            p['sticker']=str(d/'sticker.png');p['sticker_end']=2
            p['sfx']=[dict(path=str(d/'music.wav'),time=1,volume=.2)]
            result=core.render(p,str(d/'out.mp4'))
            info=core.probe(result)
            self.assertAlmostEqual(info['duration'],3,delta=.15);self.assertTrue(info['audio'])
            with self.assertRaises(ValueError):core.render(p,result)
            # No-audio source must produce a valid audio stream, too.
            core.run([exe,'-v','error','-i',str(d/'source.mp4'),'-an','-c:v','copy',str(d/'silent.mp4')])
            p=copy.deepcopy(self.p);p['source']=str(d/'silent.mp4');p['captions_enabled']=False
            core.render(p,str(d/'silent-out.mp4'),preview=True)
            self.assertTrue(core.probe(d/'silent-out.mp4')['audio'])

if __name__=='__main__':unittest.main()
