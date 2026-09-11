import tempfile, unittest
from pathlib import Path
import core

class SequenceTests(unittest.TestCase):
    def test_common_command(self):
        actions,unknown=core.commands('cortes e legenda')
        self.assertFalse(unknown)
        self.assertIn(('captions_enabled',True),[(k,v) for k,v,_ in actions])
        self.assertTrue(any(k=='cuts' for k,_,_ in actions))

    def test_mixed_takes_reorder_export(self):
        import av
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);exe=core.ffmpeg()
            red=root/'vermelho.mp4';blue=root/'azul.mp4'
            core.run([exe,'-v','error','-f','lavfi','-i','color=red:s=320x240:r=25:d=1',
                      '-f','lavfi','-i','sine=frequency=440:duration=1','-c:v','libx264','-c:a','aac',str(red)])
            core.run([exe,'-v','error','-f','lavfi','-i','color=blue:s=240x320:r=30:d=1.5',
                      '-c:v','libx264',str(blue)])
            def center_rgb(path,seconds):
                with av.open(str(path)) as video:
                    for frame in video.decode(video=0):
                        if frame.time>=seconds:
                            return frame.to_ndarray(format='rgb24')[frame.height//2,frame.width//2]
                self.fail('Quadro não encontrado')
            result=core.assemble([red,blue],root/'sequence.mp4')
            self.assertEqual(len(result['takes']),2)
            self.assertEqual((result['width'],result['height']),(320,240))
            self.assertAlmostEqual(result['duration'],2.5,delta=.15)
            self.assertTrue(result['audio'])
            self.assertGreater(int(center_rgb(result['source'],.3)[0]),200)
            self.assertGreater(int(center_rgb(result['source'],1.4)[2]),200)
            p=core.project();p.update({k:v for k,v in result.items() if k!='audio'})
            p['ranges']=[dict(start=t['start'],end=t['end'],enabled=True) for t in p['takes']]
            p['words']=[dict(start=1.4,end=1.8,text='Segundo')]
            p['ranges'][0]['enabled']=False
            core.validate(p)
            self.assertLess(core.mapped_words(p)[0]['start'],.5)
            core.render(p,str(root/'cut.mp4'))
            self.assertGreater(int(center_rgb(root/'cut.mp4',.1)[2]),200)
            self.assertAlmostEqual(core.probe(root/'cut.mp4')['duration'],1.5,delta=.15)
            reordered=core.assemble([blue,red],root/'reorder.mp4')
            self.assertGreater(int(center_rgb(reordered['source'],.3)[2]),200)
            self.assertGreater(int(center_rgb(reordered['source'],1.8)[0]),200)
            with self.assertRaises(ValueError):core.assemble([red],root/'sequence.mp4')

if __name__=='__main__':unittest.main()
