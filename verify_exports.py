#!/usr/bin/env python3
"""Decode locally rendered exports and verify format, sync, timeline duration and source integrity."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from nani import ROOT,probe,run,digest,doctor

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,default=ROOT/'validation.json',help='JSON verification report path')
    args=parser.parse_args()
    results={'tools':doctor(),'exports':[]}
    files=sorted((ROOT/'exports').rglob('*.mp4'))
    if not files: raise ValueError('No exports to verify')
    for path in files:
        report=json.loads(path.with_suffix('.report.json').read_text())
        plan=report['plan']; p=probe(path)
        raw=json.loads(run(['ffprobe','-v','error','-show_streams','-of','json',path]))
        v=next(x for x in raw['streams'] if x['codec_type']=='video')
        a=next(x for x in raw['streams'] if x['codec_type']=='audio')
        checks={'dimensions':(p['width'],p['height'])==(plan['width'],plan['height']),
                'h264_aac':p['video_codec']=='h264' and p['audio_codec']=='aac',
                'pixel_format':p['pixel_format']=='yuv420p',
                'fps':abs(p['fps']-plan['fps'])<0.01,
                'rec709_tags':all(p.get(k)=='bt709' for k in ('transfer','primaries','colorspace')),
                'timeline_duration':abs(p['duration']-plan['duration'])<0.15,
                'audio_video_duration_sync':abs(float(v['duration'])-float(a['duration']))<0.1,
                'originals_unchanged':True}
        for source,expected in report['sources_sha256'].items():
            source_path=Path(source)
            if not source_path.exists(): source_path=ROOT/'examples/originals'/source_path.name
            checks['originals_unchanged'] &= digest(source_path)==expected
        run(['ffmpeg','-v','error','-xerror','-nostdin','-threads','2','-i',path,'-f','null','-'])
        checks['full_decode']=True
        results['exports'].append({'file':str(path.relative_to(ROOT)), 'probe':p,
                                   'checks':checks,'pass':all(checks.values())})
        print(path.name, 'PASS' if all(checks.values()) else 'FAIL',flush=True)
    results['all_pass']=all(x['pass'] for x in results['exports'])
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(results,indent=2)+'\n')
    if not results['all_pass']: sys.exit(1)

if __name__=='__main__': main()
