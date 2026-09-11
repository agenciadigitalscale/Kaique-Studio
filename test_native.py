import copy,tempfile,unittest
from pathlib import Path
import core,native

class NativeTests(unittest.TestCase):
    def clip(self,name,start,end,word):
        return dict(id=name,source=name,duration=3,**{'in':start,'out':end},width=320,height=240,words=[dict(start=1,end=1.4,text=word)],thumbs=[],peaks=[],proxy='')
    def test_reorder_trim_split_preserve_words(self):
        p=native.project();p['clips']=[self.clip('a',.5,2,'A'),self.clip('b',0,2,'B')]
        native.reorder(p,0,1)
        self.assertEqual([w['text'] for w in native.words(p)],['B','A'])
        self.assertAlmostEqual(native.words(p)[1]['start'],2.5)
        native.trim(p,1,.8,1.6)
        self.assertAlmostEqual(native.words(p)[1]['start'],2.2)
        saved=copy.deepcopy(p);native.split(p,1,1.2)
        self.assertAlmostEqual(native.length(saved),native.length(p))
        self.assertNotEqual(p['clips'][1]['id'],p['clips'][2]['id'])
        self.assertEqual(p['clips'][1]['words'],saved['clips'][1]['words'])
        native.trim(p,1,.8,1);self.assertEqual(p['clips'][2]['words'][0]['text'],'A')
    def test_silent_clip_preserved(self):
        p=native.project();a=self.clip('a',0,3,'A');b=self.clip('b',0,3,'B');b['words']=[];p['clips']=[a,b]
        native.suggest_cuts(p);self.assertEqual(p['clips'][-1]['id'],'b');self.assertEqual(p['clips'][-1]['out'],3)
    def test_media_pipeline(self):
        import av
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);exe=core.ffmpeg()
            paths=[]
            for name,color in [('a','red'),('b','blue')]:
                path=root/(name+'.mp4');paths.append(path)
                core.run([exe,'-v','error','-f','lavfi','-i',f'color={color}:s=320x240:r=30:d=2','-f','lavfi','-i','sine=frequency=440:duration=2','-c:v','libx264','-c:a','aac',str(path)])
            p=native.project();p['clips']=[native.inspect(path,root) for path in paths]
            self.assertEqual(len(p['clips'][0]['thumbs']),3);self.assertTrue(p['clips'][0]['peaks'])
            p['clips'][0]['words']=[dict(start=.5,end=.8,text='Primeiro')]
            native.trim(p,0,.3,1.3);native.reorder(p,0,1);native.validate(p)
            self.assertAlmostEqual(native.words(p)[0]['start'],2.2)
            old=core.project();old.update(source=str(paths[0]),duration=2,width=320,height=240,ranges=[dict(start=.3,end=1.3,enabled=True)],words=[dict(start=.5,end=.8,text='Antigo')])
            migrated=native.from_legacy(old,root)
            self.assertAlmostEqual(native.length(migrated),1)
            self.assertAlmostEqual(native.words(migrated)[0]['start'],.2)
            self.assertEqual(native.words(migrated)[0]['text'],'Antigo')
            original_words=copy.deepcopy(p['clips'][1]['words'])
            core.atomic_json(root/'p.json',p)
            import json
            loaded=json.loads((root/'p.json').read_text());native.validate(loaded)
            self.assertEqual(loaded['clips'][1]['words'],original_words)
            preview=native.proxy(p['clips'][0],root);self.assertTrue(Path(preview).is_file())
            native.render(p,str(root/'out.mp4'))
            self.assertAlmostEqual(core.probe(root/'out.mp4')['duration'],3,delta=.15)
            with av.open(str(root/'out.mp4')) as v:
                frames=[f.to_ndarray(format='rgb24')[120,160] for f in v.decode(video=0)]
            self.assertGreater(frames[10][2],200);self.assertGreater(frames[70][0],200)
            with self.assertRaises(ValueError):native.render(p,str(root/'out.mp4'))

if __name__=='__main__':unittest.main()
