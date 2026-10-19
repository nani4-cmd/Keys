import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bbk import ROOT,prepare,overlays,focus_expr,tempo,doctor,render
from argparse import Namespace

class TimelineTests(unittest.TestCase):
    def test_tools(self):
        self.assertEqual(doctor()['required_filters_and_encoders'],'PASS')

    def test_replay_and_overlaps(self):
        m,p,clips,infos,plan=prepare(ROOT/'examples/football.json')
        self.assertEqual(len(clips),5)
        self.assertEqual(clips[2]['speed'],0.5)
        self.assertEqual(clips[2]['duration'],3)
        self.assertAlmostEqual(plan['duration'],7.9)
        self.assertEqual(clips[2]['captions'],[])

    def test_source_caption_retiming(self):
        m,p,clips,infos,plan=prepare(ROOT/'examples/tech.json')
        with tempfile.TemporaryDirectory() as td:
            overlays(m,clips,plan,Path(td))
            srt=(Path(td)/'captions.srt').read_text()
            self.assertIn('00:00:02,500 --> 00:00:04,500',srt)
            self.assertIn('00:00:05,000 --> 00:00:07,000',srt)

    def test_slow_caption_clipping(self):
        m,p,clips,infos,plan=prepare(ROOT/'examples/tech.json')
        c=clips[0]
        c.update(start=1,end=2,speed=0.5,duration=2,timeline_start=0,
                 captions=[{'start':0,'end':1.5,'text':'trim me'}])
        with tempfile.TemporaryDirectory() as td:
            overlays(m,[c],plan,Path(td))
            self.assertIn('00:00:00,000 --> 00:00:01,000',(Path(td)/'captions.srt').read_text())

    def test_invalid_trim_and_focus_rejected(self):
        m=json.loads((ROOT/'examples/tech.json').read_text())
        for c in m['clips']: c['source']=str(ROOT/'examples/originals/tech-synthetic.mp4')
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'bad.json'
            bad=copy.deepcopy(m); bad['clips'][0]['end']=999
            path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError): prepare(path)
            bad=copy.deepcopy(m); bad['clips'][0]['focus']=[{'time':0,'x':4,'y':0.5}]
            path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError): prepare(path)

    def test_formats(self):
        for fmt,res,wh in [('16:9','4k',(3840,2160)),('9:16','4k',(2160,3840)),('9:16','1080p',(1080,1920))]:
            plan=prepare(ROOT/'examples/tech.json',fmt,res)[4]
            self.assertEqual((plan['width'],plan['height']),wh)

    def test_existing_source_cannot_be_output(self):
        with self.assertRaisesRegex(ValueError,'Refusing to overwrite'):
            render(Namespace(manifest=ROOT/'examples/tech.json',output=ROOT/'examples/originals/tech-synthetic.mp4',format=None,resolution=None))

    def test_tempo_low_and_high(self):
        self.assertEqual(tempo(.25),'atempo=0.5,atempo=0.5')
        self.assertEqual(tempo(4),'atempo=2,atempo=2.0')

if __name__=='__main__': unittest.main()
