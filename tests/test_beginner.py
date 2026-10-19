import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nani import ROOT,prepare
from beginner import timestamp,parse_instructions,speech_selections,build_manifest,create_project

SOURCE=ROOT/'examples/originals/tech-synthetic.mp4'

class BeginnerTests(unittest.TestCase):
    def test_time_input(self):
        self.assertEqual(timestamp('01:02.5'),62.5)
        self.assertEqual(timestamp('1:02:03'),3723)
        for bad in ['nan','-1','1:99','one minute','1:2:3:4']:
            with self.subTest(value=bad),self.assertRaises(ValueError): timestamp(bad)

    def test_supported_instructions_override_controls(self):
        result=parse_instructions('Make it vertical.\nExport in 4K\nSmooth transitions\nZoom in')
        self.assertEqual(result,{'format':'9:16','resolution':'4k','transition':'fade','zoom_end':1.1})

    def test_unknown_prose_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unsupported instructions'):
            parse_instructions('Choose only the best goals and make it cinematic')

    def test_silence_trim_stays_inside_selection(self):
        self.assertEqual(speech_selections(5,10,[(0,6),(8,12)]),[(5.88,8.12)])

    def test_football_silence_removal_rejected(self):
        with self.assertRaisesRegex(ValueError,'Keep match audio'):
            build_manifest([{'source':str(SOURCE),'start':0,'end':1}],workflow='football',instructions='Remove pauses')

    def test_guided_football_selections(self):
        m,opts=build_manifest([{'source':str(SOURCE),'start':'00:01','end':'00:02','event':'goal','label':'GOAL','replay':True,'focus_x':.75}],workflow='football',instructions='Use 9:16\nSmooth transitions')
        self.assertTrue(m['clips'][0]['replay'])
        self.assertEqual(m['clips'][0]['focus'][0]['x'],.75)
        self.assertEqual(m['clips'][0]['event'],'goal')
        self.assertEqual(m['format'],'9:16')

    def test_create_and_validate_without_handwritten_json(self):
        with tempfile.TemporaryDirectory() as td:
            manifest,output=create_project([{'source':str(SOURCE),'start':'00:00','end':'00:01','label':'TEST'}],root=Path(td),name='CON: unsafe / name',instructions='Make a short\nJump cuts')
            self.assertTrue(manifest.is_file())
            self.assertEqual(output.name,'finished.mp4')
            self.assertEqual(prepare(manifest)[4]['duration'],1)
            self.assertEqual(prepare(manifest)[4]['format'],'9:16')
            self.assertEqual(output.parent.parent,Path(td)/'exports')
            self.assertEqual(json.loads(manifest.read_text())['editing_instructions'],'Make a short\nJump cuts')

    def test_silence_cuts_are_applied(self):
        with patch('beginner.silence_ranges',return_value=[(3,4),(8,9)]):
            m,_=build_manifest([{'source':str(SOURCE),'start':0,'end':12}],instructions='Remove pauses')
        self.assertEqual(len(m['clips']),3)
        self.assertTrue(all(c['transition']=='cut' for c in m['clips']))
        self.assertAlmostEqual(m['clips'][1]['start'],3.88)

    def test_existing_transcript_is_preserved(self):
        entry={'source':str(SOURCE),'start':0,'end':1,'transcript':str(ROOT/'examples/transcript.json')}
        m,_=build_manifest([entry],instructions='Add subtitles')
        self.assertEqual(m['clips'][0]['transcript'],entry['transcript'])

if __name__=='__main__': unittest.main()
