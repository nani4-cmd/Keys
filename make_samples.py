#!/usr/bin/env python3
"""Generate original synthetic fixtures; these are not real product or match footage."""
from pathlib import Path
import json
from bbk import ff
ROOT=Path(__file__).resolve().parent
EX=ROOT/'examples'
SRC=EX/'originals'

def write(name,data):
    path=EX/name
    if not path.exists(): path.write_text(json.dumps(data,indent=2)+'\n')

def text(s,x,y,size=36,color='white',extra=''):
    return f"drawtext=font=DejaVu Sans:text='{s}':x={x}:y={y}:fontsize={size}:fontcolor={color}{extra}"

def main():
    SRC.mkdir(parents=True,exist_ok=True)
    tech=SRC/'tech-synthetic.mp4'
    if not tech.exists():
        vf=["drawbox=x=0:y=0:w=iw:h=18:color=0x63CAEA:t=fill",
            text('BuiltByKeys',110,80,42,'0x63CAEA'),text('THE DESK TEST',110,155,86),
            text('SYNTHETIC PIPELINE DEMO',110,260,30,'0x9CAFC4'),
            'drawbox=x=1000:y=200:w=650:h=420:color=0x22384C:t=fill',
            'drawbox=x=1020:y=220:w=610:h=380:color=0x101C2B:t=fill',
            text('144 Hz',1195,335,60,'0x63CAEA'),
            'drawbox=x=920:y=725:w=720:h=200:color=0x22384C:t=fill',
            'drawgrid=x=920:y=725:w=65:h=62:t=3:c=0x63CAEA@0.5',
            text('HARDWARE / PERIPHERALS / PC BUILDS',110,965,30,'0xFFFFFF')]
        af="volume='if(between(t,3,4)+between(t,8,9),0,0.2)':eval=frame"
        ff(['-f','lavfi','-i','color=c=0x0B1422:s=1920x1080:r=30:d=12',
            '-f','lavfi','-i','sine=frequency=260:sample_rate=48000:duration=12',
            '-vf',','.join(vf),'-af',af,'-c:v','libx264','-threads','2','-preset','veryfast','-crf','20',
            '-c:a','aac','-shortest',tech])
    football=SRC/'football-synthetic.mp4'
    if not football.exists():
        vf=['drawbox=x=90:y=160:w=1740:h=800:color=white@0.7:t=5',
            'drawbox=x=960:y=160:w=4:h=800:color=white@0.7:t=fill',
            'drawbox=x=90:y=330:w=280:h=460:color=white@0.7:t=5',
            'drawbox=x=1550:y=330:w=280:h=460:color=white@0.7:t=5',
            text('BuiltByKeys / MATCH LAB',100,65,40),
            text('SYNTHETIC ACTION TEST',1150,65,30),
            text('●','260+120*t','520+80*sin(t)',58,'white'),
            text('7','190+120*t','450+80*sin(t)',48,'0x63CAEA'),
            text('4','400+65*t','650-40*sin(t)',48,'0xFFBA6B'),
            text('NOT REAL MATCH FOOTAGE',100,1015,26)]
        ff(['-f','lavfi','-i','color=c=0x1E603B:s=1920x1080:r=50:d=12',
            '-f','lavfi','-i','anoisesrc=color=pink:amplitude=0.12:r=48000:d=12:seed=42',
            '-vf',','.join(vf),'-af',"volume='if(between(t,4,5)+between(t,9,10),3,0.4)':eval=frame",
            '-c:v','libx264','-threads','2','-preset','veryfast','-crf','20','-c:a','aac','-shortest',football])
    write('tech.json',{'brand':'BuiltByKeys','workflow':'tech','format':'16:9','resolution':'1080p',
          'notes':'Synthetic fixture. Replace sources and source-time captions for your own footage.',
          'clips':[
          {'source':'originals/tech-synthetic.mp4','start':0,'end':2.5,'label':'HARDWARE REVIEW',
           'captions':[{'start':0.2,'end':2.2,'text':'BuiltByKeys · The desk test'}]},
          {'source':'originals/tech-synthetic.mp4','start':4,'end':6.5,'label':'PRODUCT B-ROLL','transition':'fade','zoom_end':1.15,
           'focus':[{'time':0,'x':0.65,'y':0.5}],
           'captions':[{'start':4.2,'end':6.2,'text':'A closer look at the setup.'}]},
          {'source':'originals/tech-synthetic.mp4','start':9,'end':11.5,'label':'FINAL TAKE','transition':'cut','zoom':1.08,
           'captions':[{'start':9.2,'end':11.2,'text':'Cut pauses. Keep the useful details.'}]}]})
    write('football.json',{'brand':'BuiltByKeys','workflow':'football','format':'16:9','resolution':'1080p',
          'notes':'Events are manually labelled synthetic test windows, not automatically detected actions.',
          'clips':[
          {'source':'originals/football-synthetic.mp4','start':0.5,'end':2,'event':'skill','label':'SKILL · TEST',
           'focus':[{'time':0,'x':0.18,'y':0.5},{'time':1.5,'x':0.3,'y':0.5}]},
          {'source':'originals/football-synthetic.mp4','start':3.5,'end':5,'event':'goal','label':'GOAL · TEST','replay':True,'replay_speed':0.5,
           'focus':[{'time':0,'x':0.37,'y':0.5},{'time':1.5,'x':0.48,'y':0.5}]},
          {'source':'originals/football-synthetic.mp4','start':6,'end':7.2,'event':'tackle','label':'TACKLE · TEST',
           'focus':[{'time':0,'x':0.52,'y':0.5},{'time':1.2,'x':0.62,'y':0.5}]},
          {'source':'originals/football-synthetic.mp4','start':8.5,'end':10,'event':'save','label':'SAVE · TEST',
           'focus':[{'time':0,'x':0.68,'y':0.5},{'time':1.5,'x':0.8,'y':0.5}]}]})
    write('4k-smoke.json',{'workflow':'tech','resolution':'4k','settings':{'encoder_preset':'veryfast'},
          'clips':[{'source':'originals/tech-synthetic.mp4','start':0,'end':1,'label':'4K UPSCALE · FORMAT TEST'}]})
    if not (SRC/'silent fixture.mp4').exists():
        ff(['-i',tech,'-an','-c:v','copy',SRC/'silent fixture.mp4'])
    write('silent-multisource.json',{'workflow':'tech','settings':{'transition_seconds':0.1,'encoder_preset':'veryfast'},
          'clips':[{'source':'originals/silent fixture.mp4','start':0,'end':0.8,'label':'SILENT SOURCE'},
                   {'source':'originals/tech-synthetic.mp4','start':1,'end':1.8,'transition':'wipeleft','label':'MATCHED AUDIO'}]})
    print('Created synthetic originals and reusable example edit manifests in',EX)

if __name__=='__main__': main()
