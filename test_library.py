import tempfile, unittest
from pathlib import Path
import core
from resource_library import Catalog, myinstants_url

ASSETS=Path(__file__).parent/'assets'
class LibraryTests(unittest.TestCase):
    def test_import_and_favorites_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog=Catalog(tmp,ASSETS)
            source=ASSETS/'pop.wav'
            added=catalog.add([source],'Memes','Humor')[0]
            self.assertNotEqual(Path(added['path']),source)
            self.assertEqual(Path(added['path']).read_bytes(),source.read_bytes())
            catalog.favorite(added['id'])
            loaded=Catalog(tmp,ASSETS)
            self.assertIn(added['id'],loaded.data['favorites'])
            self.assertEqual(len(loaded.data['items']),1)
            with self.assertRaises(ValueError):loaded.add([ASSETS/'warm.cube'],'Memes','Humor')
    def test_online_search_encoding(self):
        self.assertIn('name=mentira+%26+rea%C3%A7%C3%A3o',myinstants_url('mentira & reação'))
    def test_transitions_and_lut_render(self):
        import av
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.mp4'
            core.run([core.ffmpeg(),'-v','error','-f','lavfi','-i','color=red:s=320x240:r=30:d=2',
                      '-c:v','libx264',str(source)])
            p=core.project();p.update(source=str(source),duration=2,width=320,height=240,captions_enabled=False)
            p['ranges']=[dict(start=0,end=1,enabled=True),dict(start=1,end=2,enabled=True)]
            for transition in ['Preto','Branco']:
                p['transition']=transition;p['lut']=str(ASSETS/'warm.cube')
                p['sfx']=[dict(path=str(ASSETS/'pop.wav'),time=.3,volume=.5)]
                target=root/(transition+'.mp4');core.render(p,str(target))
                self.assertAlmostEqual(core.probe(target)['duration'],2,delta=.1)
                with av.open(str(target)) as video:
                    pixels=[frame.to_ndarray(format='rgb24')[120,160] for frame in video.decode(video=0)]
                pixel=pixels[30]
                if transition=='Preto':self.assertLess(max(pixel),20)
                else:self.assertGreater(min(pixel),220)
                self.assertGreater(pixels[10][0],200)
