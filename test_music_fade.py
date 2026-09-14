"""Música com fade — validação + render real com trilha (o afade só o FFmpeg prova)."""
import subprocess, tempfile, unittest
from pathlib import Path
import core, native


class MusicFadeValidation(unittest.TestCase):
    def test_range(self):
        p = core.project(); p.update(source='x', duration=3, width=720, height=1280,
                                     ranges=[{'start': 0, 'end': 3, 'enabled': True}])
        core.validate(dict(p, music_fade=0), files=False)
        core.validate(dict(p, music_fade=2.5), files=False)
        with self.assertRaises(ValueError):
            core.validate(dict(p, music_fade=99), files=False)

    def test_in_style_keys(self):
        self.assertIn('music_fade', native.STYLE_KEYS)


class MusicFadeRender(unittest.TestCase):
    def test_renders_with_music_and_fade(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); clip = d / 'src.mp4'; music = d / 'trilha.mp3'
            subprocess.run([core.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i',
                            'testsrc=size=720x1280:rate=30:duration=2', '-f', 'lavfi', '-i',
                            'sine=frequency=440:duration=2', '-c:v', 'libx264', '-c:a', 'aac',
                            '-shortest', str(clip)], check=True)
            subprocess.run([core.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i',
                            'sine=frequency=220:duration=3', str(music)], check=True)
            n = native.project()
            n['style'].update(music=str(music), music_volume=0.3, music_fade=1.0, captions_enabled=False)
            n['clips'] = [dict(id='c1', source=str(clip), duration=2.0, width=720, height=1280,
                               **{'in': 0.0, 'out': 2.0}, words=[], thumbs=[], peaks=[], proxy='')]
            out = native.render(n, str(d / 'out.mp4'))
            self.assertTrue(Path(out).is_file())
            self.assertGreater(Path(out).stat().st_size, 1000)


if __name__ == '__main__':
    unittest.main()
