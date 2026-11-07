"""Geometry, exact frame counts, final colors, and invalid active-content fixtures."""
import importlib.util
import base64
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('renderer',ROOT/'engine/render.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class EngineTests(unittest.TestCase):
    def doodle_source(self):
        image=renderer.Image.new('RGB',(320,180),(25,50,65))
        stream=io.BytesIO();image.save(stream,format='PNG')
        encoded=base64.b64encode(stream.getvalue()).decode()
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180">
          <image width="320" height="180" href="data:image/png;base64,{encoded}"/>
          <g id="doodles" fill="none" stroke="white" stroke-width="6" stroke-linecap="round">
            <path d="M20 50 L140 50"/>
            <g transform="translate(20 20)"><path d="M160 80 L280 80" stroke="#ff8080" stroke-dasharray="10 10"/></g>
          </g></svg>'''

    def test_embedded_image_validation(self):
        renderer.validate_svg(self.doodle_source())
        for href in ['https://example.com/x.png','file:///C:/x.png','data:image/svg+xml;base64,PHN2Zy8+','data:image/png;base64,abcd','data:image/jpeg;base64,@@@@']:
            with self.subTest(href=href), self.assertRaises(Exception):
                renderer.validate_svg(f'<svg><image href="{href}"/></svg>')

    def test_doodle_frames_and_seek(self):
        with renderer.open_scene(self.doodle_source(),320,180,'doodle') as (scene,final,page):
            timeline=renderer.wb._prepare_timeline([renderer.Stroke([tuple(p) for p in path['points']],source='svg') for path in scene['paths']],60)
            self.assertEqual(len(timeline),2)  # The embedded background is never traced.
            first=renderer.overlay_frame(page,timeline,0)
            self.assertEqual(first.getpixel((30,50)),(25,50,65))
            middle=renderer.overlay_frame(page,timeline,.25)
            self.assertEqual(middle.getpixel((30,50)),(255,255,255))
            self.assertEqual(middle.getpixel((130,50)),(25,50,65))
            last=renderer.overlay_frame(page,timeline,1)
            self.assertEqual(last.tobytes(),final.tobytes())
            self.assertEqual(last.getpixel((184,100)),(255,128,128))
            self.assertEqual(last.getpixel((195,100)),(25,50,65))  # dash gap preserved
            self.assertEqual(renderer.overlay_frame(page,timeline,0).tobytes(),first.tobytes())
            self.assertEqual(renderer.overlay_frame(page,timeline,.25).tobytes(),middle.tobytes())

    def test_doodle_contract(self):
        for source in [self.doodle_source().replace('id="doodles"','id="other"'),self.doodle_source().replace('fill="none"','fill="red"')]:
            with self.assertRaises(Exception):
                with renderer.open_scene(source,320,180,'doodle'): pass

    def test_active_content_rejected(self):
        for svg in [
            (ROOT/'tests/fixtures/unsafe.svg').read_text(),
            '<!DOCTYPE svg [<!ENTITY a SYSTEM "file:///C:/secret">]><svg>&a;</svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><rect onload="alert(1)"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="url(https://example.com/x)"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><rect style="fill: u\\72l(http://evil)"/></svg>',
        ]:
            with self.subTest(svg=svg), self.assertRaises(Exception): renderer.validate_svg(svg)

    def test_browser_geometry_and_colors(self):
        source=(ROOT/'tests/fixtures/curves.svg').read_text()
        scene, image=renderer.prepare_scene(source,320,180)
        paths=scene['paths']
        self.assertEqual(len(paths),5)  # background, rounded rect, arc, cubic, relative subpath
        arc=paths[2]['points']
        self.assertAlmostEqual(arc[0][0],180,delta=.1)
        self.assertAlmostEqual(arc[-1][0],270,delta=.1)
        self.assertLess(min(p[1] for p in arc),95)  # actual arc, not a straight segment
        relative=paths[4]['points']
        self.assertAlmostEqual(relative[0][0],205,delta=.1)
        self.assertAlmostEqual(relative[0][1],65,delta=.1)
        self.assertAlmostEqual(relative[-1][0],213,delta=.1)
        self.assertNotEqual(image.getpixel((80,80)),(255,255,255))

    def test_absolute_seek(self):
        stroke=renderer.Stroke([(0,0),(100,0)],source='svg')
        plan=renderer.wb._prepare_timeline([stroke],100)
        expected=renderer.evaluate_strokes(plan,.5)
        for p in [1,.2,0,.9]: renderer.evaluate_strokes(plan,p)
        self.assertEqual(expected,renderer.evaluate_strokes(plan,.5))
        self.assertEqual(expected[1],(50.,0.))

    def test_real_mp4(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as tmp:
            directory=Path(tmp)
            (directory/'input.svg').write_text((ROOT/'tests/fixtures/curves.svg').read_text(),encoding='utf-8')
            request={'schemaVersion':1,'width':320,'height':180,'fps':15,'settings':{'duration':3,'hold':.5,'handScale':.65,'hand':'asian'}}
            (directory/'request.json').write_text(json.dumps(request),encoding='utf-8')
            renderer.render(directory/'request.json')
            result=json.loads((directory/'result.json').read_text())
            self.assertEqual(result['frames'],45)
            self.assertEqual(result['ffprobe']['streams'][0]['codec_name'],'h264')
            decoded=subprocess.run(['ffmpeg','-v','error','-i',str(directory/'output.mp4'),'-vf',r'select=eq(n\,44)','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True)
            from PIL import Image, ImageChops, ImageStat
            final=Image.frombytes('RGB',(320,180),decoded.stdout)
            original=Image.open(directory/'original.png').convert('RGB')
            difference=ImageStat.Stat(ImageChops.difference(final,original))
            self.assertLess(sum(difference.mean)/3,3.0)  # H.264 is lossy, verify perceptual pixel error

    def test_doodle_mp4(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as tmp:
            directory=Path(tmp)
            (directory/'input.svg').write_text(self.doodle_source(),encoding='utf-8')
            request={'schemaVersion':1,'width':320,'height':180,'fps':15,'settings':{'duration':3,'hold':.5,'handScale':.65,'hand':'none','effect':'doodle'}}
            (directory/'request.json').write_text(json.dumps(request),encoding='utf-8')
            renderer.render(directory/'request.json')
            result=json.loads((directory/'result.json').read_text())
            self.assertEqual(result['frames'],45)
            self.assertEqual(result['effect'],'doodle')
            decoded=subprocess.run(['ffmpeg','-v','error','-i',str(directory/'output.mp4'),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True)
            first=renderer.Image.frombytes('RGB',(320,180),decoded.stdout)
            self.assertLess(max(abs(a-b) for a,b in zip(first.getpixel((30,50)),(25,50,65))),5)


if __name__=='__main__': unittest.main()
