#!/usr/bin/env python3
"""BuiltByKeys: non-destructive, manifest-driven FFmpeg editor. Python 3.10+."""
import argparse
import array
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parent
SIZES = {'1080p': {'16:9': (1920,1080), '9:16': (1080,1920)},
         '4k': {'16:9': (3840,2160), '9:16': (2160,3840)}}
REQUIRED_FILTERS = {'subtitles','xfade','acrossfade','concat','crop','scale','zoompan',
                    'afftdn','highpass','loudnorm','atempo','silencedetect','aresample','setparams'}


def run(args, cwd=None):
    p = subprocess.run([str(x) for x in args], cwd=cwd, capture_output=True, text=True)
    if p.returncode:
        raise ValueError(f"Command failed: {args[0]}\n{p.stderr[-6000:]}")
    return p.stdout


def ff(args, cwd=None):
    return run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
                '-threads','2','-filter_threads','1','-filter_complex_threads','1',*args],cwd)


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(data,f,indent=2,ensure_ascii=False)
        f.write('\n')


def probe(path):
    data = json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',Path(path).resolve()]))
    vs = [s for s in data['streams'] if s['codec_type']=='video']
    if not vs:
        raise ValueError(f'No video stream: {path}')
    v = vs[0]
    rate = v.get('avg_frame_rate','0/1').split('/')
    return {'duration':float(data['format']['duration']), 'width':int(v['width']),
            'height':int(v['height']), 'fps':float(rate[0])/max(float(rate[1]),1),
            'video_codec':v['codec_name'], 'pixel_format':v.get('pix_fmt'),
            'audio':any(s['codec_type']=='audio' for s in data['streams']),
            'audio_codec':next((s['codec_name'] for s in data['streams'] if s['codec_type']=='audio'),None),
            'transfer':v.get('color_transfer'), 'primaries':v.get('color_primaries'), 'colorspace':v.get('color_space'), 'rotation':next((s.get('rotation',0) for s in v.get('side_data_list',[]) if 'rotation' in s),0)}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def doctor():
    missing = [x for x in ('ffmpeg','ffprobe') if not shutil.which(x)]
    if missing:
        raise ValueError('Install required executables: '+', '.join(missing))
    filters = run(['ffmpeg','-hide_banner','-filters'])
    absent = sorted(x for x in REQUIRED_FILTERS if not re.search(r'\b'+x+r'\s',filters))
    enc = run(['ffmpeg','-hide_banner','-encoders'])
    absent += [x for x in ('libx264','aac') if not re.search(r'\b'+x+r'\s',enc)]
    if absent:
        raise ValueError('FFmpeg build lacks: '+', '.join(absent))
    return {'python':sys.version.split()[0], 'ffmpeg':run(['ffmpeg','-version']).splitlines()[0],
            'ffprobe':run(['ffprobe','-version']).splitlines()[0],
            'required_filters_and_encoders':'PASS',
            'faster_whisper_installed':importlib.util.find_spec('faster_whisper') is not None}


def number(value, name, lo, hi):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not lo<=value<=hi:
        raise ValueError(f'{name} must be a number in [{lo}, {hi}]')
    return float(value)


def resolve_file(base, value):
    if not isinstance(value,str) or '://' in value:
        raise ValueError('Sources must be local file paths')
    path = (base/value).resolve()
    if not path.is_file():
        raise ValueError(f'Missing file: {path}')
    return path


def prepare(manifest, format_override=None, resolution_override=None):
    path=Path(manifest).resolve()
    m=load(path)
    base=path.parent
    workflow=m.get('workflow')
    if workflow not in ('tech','football'):
        raise ValueError('workflow must be tech or football')
    preset=load(ROOT/'presets'/f'{workflow}.json')
    preset.update(m.get('settings',{}))
    fmt=format_override or m.get('format','16:9')
    res=resolution_override or m.get('resolution','1080p')
    if fmt not in ('16:9','9:16') or res not in SIZES:
        raise ValueError('Choose format 16:9 or 9:16; resolution 1080p or 4k')
    fps=number(preset['fps'],'fps',1,120)
    if not fps.is_integer():
        raise ValueError('fps must be a whole number; choose e.g. 25, 30, 50 or 60')
    fps=int(fps)
    number(preset['transition_seconds'],'transition_seconds',0.05,2)
    number(preset['crf'],'crf',0,40)
    for k,lo,hi in [('contrast',0.5,2),('saturation',0,2),('brightness',-0.3,0.3),('gamma',0.5,2)]:
        number(preset[k],k,lo,hi)
    if preset['encoder_preset'] not in ('ultrafast','superfast','veryfast','faster','fast','medium','slow'):
        raise ValueError('Unsupported encoder_preset')
    if preset['audio_cleanup'] not in ('speech','match','none'):
        raise ValueError('audio_cleanup must be speech, match or none')
    number(preset['loudness_lufs'],'loudness_lufs',-30,-9)
    number(preset['true_peak_db'],'true_peak_db',-6,-1)
    number(preset['loudness_range'],'loudness_range',1,20)
    clips=m.get('clips',[])
    if not isinstance(clips,list) or not clips:
        raise ValueError('Add at least one clip')
    expanded=[]
    infos={}
    warnings=[]
    for raw in clips:
        c=copy.deepcopy(raw)
        source=resolve_file(base,c['source'])
        if source not in infos:
            infos[source]=probe(source)
        info=infos[source]
        if info['rotation'] or info['transfer'] in ('smpte2084','arib-std-b67'):
            raise ValueError(f'{source.name}: normalize rotation/HDR to upright SDR before editing (see README)')
        c['source']=source
        start=number(c.get('start',0),'start',0,info['duration'])
        end=number(c.get('end',info['duration']),'end',0,info['duration']+0.001)
        speed=number(c.get('speed',1),'speed',0.25,4)
        if end-start<0.1:
            raise ValueError('Each source range must be at least 0.1 seconds')
        c.update(start=start,end=end,speed=speed)
        c['duration']=round((end-start)/speed*fps)/fps
        c['transition']=c.get('transition',preset['transition'])
        if c['transition'] not in ('cut','fade','wipeleft','slideright'):
            raise ValueError('transition must be cut, fade, wipeleft or slideright')
        c['zoom']=number(c.get('zoom',1),'zoom',1,2)
        c['zoom_end']=number(c.get('zoom_end',c['zoom']),'zoom_end',1,2)
        centers=c.get('focus',[{'time':0,'x':0.5,'y':0.5}])
        if not centers:
            raise ValueError('focus must have at least one keyframe')
        last=-1
        for p in centers:
            t=number(p['time'],'focus.time',0,end-start)
            if t<=last:
                raise ValueError('focus times must increase')
            last=t
            number(p['x'],'focus.x',0,1); number(p.get('y',0.5),'focus.y',0,1)
        c['focus']=centers
        caps=c.get('captions',[])
        if 'transcript' in c:
            caps=load(resolve_file(base,c['transcript']))['segments']
        for cap in caps:
            a=number(cap['start'],'caption.start',0,info['duration']+1)
            b=number(cap['end'],'caption.end',0,info['duration']+1)
            if a>=b or not isinstance(cap['text'],str):
                raise ValueError('Caption needs start < end and text')
        c['captions']=caps
        if info['width']<SIZES[res][fmt][0] or info['height']<SIZES[res][fmt][1]:
            warnings.append(f'{source.name}: export includes scaling; output resolution does not add captured detail.')
        expanded.append(c)
        if c.get('replay'):
            replay=copy.deepcopy(c)
            replay.update(speed=number(c.get('replay_speed',0.5),'replay_speed',0.25,1),replay=False,
                          label='REPLAY · '+str(c.get('label',c.get('event','Action'))),captions=[])
            replay['duration']=round((end-start)/replay['speed']*fps)/fps
            expanded.append(replay)
    timeline=[]; elapsed=0
    for i,c in enumerate(expanded):
        overlap=0 if i==0 or c['transition']=='cut' else round(preset['transition_seconds']*fps)/fps
        if i and overlap>=min(expanded[i-1]['duration'],c['duration'])/2:
            raise ValueError('Transition too long for adjacent clips; shorten transition_seconds or use cut')
        c['overlap']=overlap
        c['timeline_start']=elapsed-overlap
        elapsed=c['timeline_start']+c['duration']
        timeline.append({k:(str(v) if isinstance(v,Path) else v) for k,v in c.items()})
    return m,preset,expanded,infos,{'workflow':workflow,'format':fmt,'resolution':res,'fps':fps,
        'width':SIZES[res][fmt][0],'height':SIZES[res][fmt][1],'duration':elapsed,
        'clips':timeline,'warnings':sorted(set(warnings))}


def focus_expr(points,axis,speed):
    expr=str(points[-1].get(axis,0.5))
    for a,b in reversed(list(zip(points,points[1:]))):
        ta=a['time']/speed; tb=b['time']/speed
        va=a.get(axis,0.5); vb=b.get(axis,0.5)
        line=f'({va}+({vb-va})*(t-{ta})/{tb-ta})'
        expr=f'if(lt(t,{tb}),{line},{expr})'
    return f'if(lt(t,{points[0]["time"]/speed}),{points[0].get(axis,0.5)},{expr})'


def tempo(speed):
    parts=[]
    while speed<0.5:
        parts.append('atempo=0.5'); speed/=0.5
    while speed>2:
        parts.append('atempo=2'); speed/=2
    return ','.join(parts+[f'atempo={speed}'])


def render_segment(c,info,p,plan,out):
    w,h,fps=plan['width'],plan['height'],plan['fps']
    duration=c['duration']
    cx=focus_expr(c['focus'],'x',c['speed']); cy=focus_expr(c['focus'],'y',c['speed'])
    aspect=w/h
    vf=[f'setpts=(PTS-STARTPTS)/{c["speed"]}',
        f"crop=w='trunc(min(iw,ih*{aspect})/2)*2':h='trunc(min(ih,iw/{aspect})/2)*2':x='max(0,min(iw-ow,iw*({cx})-ow/2))':y='max(0,min(ih-oh,ih*({cy})-oh/2))'",
        f'scale={w}:{h}:flags=lanczos',f'fps={fps}', 'setsar=1']
    if c['zoom']!=1 or c['zoom_end']!=1:
        frames=max(1,round(duration*fps)-1)
        vf.append(f"zoompan=z='{c['zoom']}+({c['zoom_end']-c['zoom']})*min(on/{frames},1)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={w}x{h}:fps={fps}")
    vf += [f"eq=contrast={p['contrast']}:brightness={p['brightness']}:saturation={p['saturation']}:gamma={p['gamma']}",
           f'tpad=stop_mode=clone:stop_duration=1',f'trim=duration={duration}', 'setpts=PTS-STARTPTS','format=yuv420p']
    args=['-ss',c['start'],'-t',c['end']-c['start'],'-i',c['source']]
    if info['audio']:
        audio='0:a:0'
    else:
        args+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']; audio='1:a:0'
    af=f"asetpts=PTS-STARTPTS,{tempo(c['speed'])},aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={duration},asetpts=PTS-STARTPTS"
    if c.get('mute',False):
        af+=',volume=0'
    graph=f"[0:v:0]{','.join(vf)}[v];[{audio}]{af}[a]"
    ff([*args,'-filter_complex',graph,'-map','[v]','-map','[a]','-t',duration,
        '-c:v','libx264','-threads','2','-preset','veryfast','-crf','15','-c:a','pcm_s16le',out])


def ass_time(t):
    n=round(max(0,t)*100); s,cs=divmod(n,100); m,s=divmod(s,60); h,m=divmod(m,60)
    return f'{h}:{m:02}:{s:02}.{cs:02}'


def srt_time(t):
    n=round(max(0,t)*1000); s,ms=divmod(n,1000); m,s=divmod(s,60); h,m=divmod(m,60)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def safe_text(value):
    # Remove ASS override syntax and HTML tags; content never becomes filter code.
    return re.sub(r'<[^>]+>','',str(value)).replace('\\','/').replace('{','(').replace('}',')').replace('\n',r'\N').replace('\r','')


def overlays(m,clips,plan,folder):
    w,h=plan['width'],plan['height']; vertical=plan['format']=='9:16'
    font=round(h*(0.025 if vertical else 0.043))
    margin=round(h*(0.17 if vertical else 0.08))
    style=lambda name,size,color,align,mv:f'Style: {name},DejaVu Sans,{size},{color},&H000000FF,&H00101820,&H80101820,-1,0,0,0,100,100,0,0,1,2,1,{align},60,60,{mv},1'
    lines=['[Script Info]','ScriptType: v4.00+',f'PlayResX: {w}',f'PlayResY: {h}','WrapStyle: 0',
           '[V4+ Styles]','Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
           style('Caption',font,'&H00FFFFFF',2,margin),style('Brand',round(font*0.62),'&H00EACC63',9,round(h*0.055)),
           style('Label',round(font*0.8),'&H00EACC63',7,round(h*0.06)),
           '[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    def add(a,b,style,text):
        if b>a:
            lines.append(f'Dialogue: 0,{ass_time(a)},{ass_time(b)},{style},,0,0,0,,{safe_text(text)}')
    add(0,plan['duration'],'Brand',m.get('brand','BuiltByKeys'))
    captions=[]
    for c in clips:
        offset=c['timeline_start']
        label=c.get('label',c.get('event',''))
        add(offset+0.05,min(offset+2.5,offset+c['duration']), 'Label',label)
        for cap in c['captions']:
            a=max(cap['start'],c['start']); b=min(cap['end'],c['end'])
            if b>a:
                captions.append({'start':offset+(a-c['start'])/c['speed'],
                                 'end':offset+(b-c['start'])/c['speed'],'text':cap['text']})
    captions.sort(key=lambda x:x['start'])
    for c in captions:
        # Explicit wrapping also works with recognizers emitting a long segment.
        c['text']='\n'.join(textwrap.wrap(c['text'],width=30 if vertical else 58))
        add(c['start'],c['end'],'Caption',c['text'])
    (folder/'overlay.ass').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    srt='\n\n'.join(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{re.sub(r'<[^>]+>', '',c['text'])}" for i,c in enumerate(captions,1))
    (folder/'captions.srt').write_text(srt+'\n' if srt else '',encoding='utf-8')


def render(args):
    doctor()
    m,p,clips,infos,plan=prepare(args.manifest,args.format,args.resolution)
    output=Path(args.output).resolve()
    if output.suffix.lower()!='.mp4':
        raise ValueError('Output must end in .mp4')
    artifacts=[output,output.with_suffix('.srt'),output.with_suffix('.report.json'),output.with_suffix('.ass')]
    for f in artifacts:
        if f.exists():
            raise ValueError(f'Refusing to overwrite: {f}')
    output.parent.mkdir(parents=True,exist_ok=True)
    hashes={str(f):digest(f) for f in infos}
    with tempfile.TemporaryDirectory(prefix='.bbk-',dir=output.parent) as td:
        folder=Path(td)
        for i,c in enumerate(clips):
            print(f"Rendering clip {i+1}/{len(clips)}: {c['source'].name} [{c['start']}, {c['end']}]",flush=True)
            render_segment(c,infos[c['source']],p,plan,folder/f'{i}.mkv')
        overlays(m,clips,plan,folder)
        ffargs=[]; graph=[]
        for i in range(len(clips)):
            ffargs+=['-i',folder/f'{i}.mkv']
            graph += [f'[{i}:v]setpts=PTS-STARTPTS,fps={plan["fps"]}[v{i}]', f'[{i}:a]asetpts=PTS-STARTPTS[a{i}]']
        v,a='v0','a0'
        for i,c in enumerate(clips[1:],1):
            nv,na=f'joinv{i}',f'joina{i}'
            if c['overlap']:
                graph += [f'[{v}][v{i}]xfade=transition={c["transition"]}:duration={c["overlap"]}:offset={c["timeline_start"]}[{nv}]',
                          f'[{a}][a{i}]acrossfade=d={c["overlap"]}:c1=tri:c2=tri[{na}]']
            else:
                graph += [f'[{v}][v{i}]concat=n=2:v=1:a=0[{nv}]',f'[{a}][a{i}]concat=n=2:v=0:a=1[{na}]']
            graph += [f'[{nv}]setpts=PTS-STARTPTS,fps={plan["fps"]}[ratev{i}]']
            v,a=f'ratev{i}',na
        graph += [f'[{v}]subtitles=overlay.ass:fontsdir=.,format=yuv420p,setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709[vout]']
        cleanup={'speech':'highpass=f=80,afftdn=nf=-25,', 'match':'highpass=f=35,','none':''}[p['audio_cleanup']]
        # First pass over the complete edit, then a measured second loudness pass.
        audio_graph=';'.join(g for g in graph if 'asetpts=' in g or ']acrossfade=' in g or ']concat=n=2:v=0:a=1' in g)
        # Analyze only audio to avoid decoding and filtering the video twice.
        loud=f"loudnorm=I={p['loudness_lufs']}:TP={p['true_peak_db']}:LRA={p['loudness_range']}"
        analysis_graph=audio_graph+f';[{a}]{cleanup}{loud}:print_format=json[measure]'
        result=subprocess.run(['ffmpeg','-hide_banner','-nostdin','-filter_complex_threads','1',*map(str,ffargs),
                               '-filter_complex',analysis_graph,'-map','[measure]','-f','null','-'],
                              cwd=folder,capture_output=True,text=True)
        if result.returncode:
            raise ValueError('Loudness analysis failed:\n'+result.stderr[-5000:])
        match=re.search(r'\{\s*"input_i".*?\}',result.stderr,re.S)
        if not match:
            raise ValueError('FFmpeg did not return loudness measurements')
        measured=json.loads(match.group())
        if all(math.isfinite(float(measured[k])) for k in ('input_i','input_tp','input_lra','input_thresh','target_offset')):
            loud+=f":measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}:offset={measured['target_offset']}:linear=true"
        graph += [f'[{a}]{cleanup}{loud},aresample=48000,apad,atrim=duration={plan["duration"]}[aout]']
        ff([*ffargs,'-filter_complex',';'.join(graph),'-map','[vout]','-map','[aout]',
            '-t',plan['duration'],'-r',plan['fps'],'-c:v','libx264','-threads','2',
            '-preset',p['encoder_preset'],'-crf',p['crf'],'-pix_fmt','yuv420p',
            '-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709',
            '-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',folder/'finished.mp4'],cwd=folder)
        verified=probe(folder/'finished.mp4')
        if (verified['width'],verified['height'])!=(plan['width'],plan['height']) or abs(verified['duration']-plan['duration'])>0.15:
            raise ValueError('Output verification failed')
        unchanged=all(digest(f)==h for f,h in hashes.items())
        if not unchanged:
            raise ValueError('Source checksum changed during render')
        report={'plan':plan,'preset':p,'output':verified,'sources_sha256':hashes,
                'originals_unchanged':unchanged,'loudness_input_measurements':measured,
                'note':'Creative quality needs human review; output is SDR Rec.709.'}
        (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        # Exclusive hard links publish completed files on the same filesystem, never overwrite originals.
        staged=[folder/'finished.mp4',folder/'captions.srt',folder/'report.json',folder/'overlay.ass']
        for src,dst in zip(staged,artifacts):
            os.link(src,dst)
    print(f'Finished: {output}\nDuration: {verified["duration"]:.3f}s; {verified["width"]}x{verified["height"]}; originals unchanged.')


def silence_ranges(path,threshold=-35,min_silence=0.4):
    if not probe(path)['audio']:
        return []
    p=subprocess.run(['ffmpeg','-hide_banner','-nostdin','-i',str(path),'-vn','-af',
                      f'silencedetect=noise={threshold}dB:d={min_silence}','-f','null','-'],capture_output=True,text=True)
    if p.returncode:
        raise ValueError(p.stderr[-3000:])
    ranges=[]; start=None
    for key,value in re.findall(r'silence_(start|end):\s*([\d.]+)',p.stderr):
        if key=='start': start=float(value)
        elif start is not None:
            ranges.append((start,float(value))); start=None
    if start is not None: ranges.append((start,probe(path)['duration']))
    return ranges


def suggest_tech(args):
    source=Path(args.source).resolve(); duration=probe(source)['duration']
    cuts=silence_ranges(source,args.threshold,args.min_silence)
    ranges=[]; cursor=0
    for a,b in cuts:
        left=min(duration,a+args.padding); right=max(left,b-args.padding)
        if left-cursor>=0.15: ranges.append((cursor,left))
        cursor=max(cursor,right)
    if duration-cursor>=0.15: ranges.append((cursor,duration))
    if not ranges:
        raise ValueError('No speech regions found; adjust threshold or select clips manually')
    manifest={'brand':'BuiltByKeys','workflow':'tech','format':'16:9','resolution':'1080p',
              'review_required':True,'notes':'Silence heuristics only. Review sentence boundaries and false cuts before render.',
              'clips':[{'source':str(source),'start':round(a,3),'end':round(b,3),'transition':'cut'} for a,b in ranges]}
    save_new(args.output,manifest)
    print(f'Wrote {len(ranges)} proposed speech regions: {args.output}')


def suggest_football(args):
    source=Path(args.source).resolve(); info=probe(source)
    if not info['audio']:
        raise ValueError('Audio-based candidates require match audio; select events manually for a silent source')
    # Stream 1-second audio windows to keep memory bounded for whole matches.
    proc=subprocess.Popen(['ffmpeg','-v','error','-nostdin','-i',str(source),'-vn','-ac','1','-ar','8000','-f','s16le','-'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    peaks=[]; index=0
    while True:
        buf=proc.stdout.read(16000)
        if not buf: break
        samples=array.array('h'); samples.frombytes(buf)
        if sys.byteorder!='little': samples.byteswap()
        rms=math.sqrt(sum(float(v)*v for v in samples)/max(1,len(samples)))
        peaks.append((rms,index+0.5)); index+=1
    proc.stdout.close()
    if proc.wait(): raise ValueError('Audio candidate extraction failed')
    chosen=[]
    for rms,t in sorted(peaks,reverse=True):
        if rms<1: continue
        if all(abs(t-other)>args.spacing for _,other in chosen):
            chosen.append((rms,t))
        if len(chosen)>=args.count: break
    events=[{'time':t,'score_rms':round(rms,2),'type':'unclassified','review_required':True,
             'start':round(max(0,t-args.before),3),'end':round(min(info['duration'],t+args.after),3)} for rms,t in sorted(chosen,key=lambda x:x[1])]
    save_new(args.output,{'source':str(source),'method':'audio energy; not semantic event detection',
                         'notes':'Crowd noise, commentary, music or whistles can dominate. Goals, skills, tackles and saves require manual classification or a trained sports model.',
                         'candidates':events})
    print(f'Wrote {len(events)} unclassified candidates: {args.output}')


def transcribe(args):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ValueError('Optional AI dependency missing. Install: python3 -m pip install -r requirements-ai.txt; see README for model downloads.')
    source=Path(args.source).resolve()
    if not probe(source)['audio']: raise ValueError('Source has no audio to transcribe')
    if Path(args.output).exists(): raise ValueError('Refusing to overwrite transcript')
    model=WhisperModel(args.model,device=args.device,compute_type='int8' if args.device=='cpu' else 'float16')
    segments,info=model.transcribe(str(source),language=args.language,word_timestamps=True,vad_filter=True)
    data={'source':str(source),'language':info.language,'review_required':True,'segments':[]}
    for segment in segments:
        words=segment.words or []
        if not words:
            data['segments'].append({'start':segment.start,'end':segment.end,'text':segment.text.strip()})
        for i in range(0,len(words),6):
            group=words[i:i+6]
            data['segments'].append({'start':group[0].start,'end':group[-1].end,'text':''.join(w.word for w in group).strip()})
    save_new(args.output,data)
    print(f'Transcript written: {args.output}; proofread product names and timing.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor',help='Check installed executables, filters and optional AI dependency')
    p=sub.add_parser('plan',help='Validate and inspect an edit without rendering')
    p.add_argument('manifest'); p.add_argument('--format',choices=['16:9','9:16']); p.add_argument('--resolution',choices=['1080p','4k'])
    p=sub.add_parser('render',help='Render an edit; existing output files are never overwritten')
    p.add_argument('manifest'); p.add_argument('-o','--output',required=True)
    p.add_argument('--format',choices=['16:9','9:16']); p.add_argument('--resolution',choices=['1080p','4k'])
    p=sub.add_parser('suggest-tech',help='Propose speech jump cuts from silence; review before rendering')
    p.add_argument('source'); p.add_argument('-o','--output',required=True)
    p.add_argument('--threshold',type=float,default=-35); p.add_argument('--min-silence',type=float,default=0.4); p.add_argument('--padding',type=float,default=0.12)
    p=sub.add_parser('suggest-football',help='Rank audio peaks for review; does not identify goals or actions')
    p.add_argument('source'); p.add_argument('-o','--output',required=True)
    p.add_argument('--count',type=int,default=12); p.add_argument('--before',type=float,default=6); p.add_argument('--after',type=float,default=4); p.add_argument('--spacing',type=float,default=12)
    p=sub.add_parser('transcribe',help='Optional local Whisper transcription to source-time JSON')
    p.add_argument('source'); p.add_argument('-o','--output',required=True); p.add_argument('--model',default='small',help='Model name to download or local model folder')
    p.add_argument('--device',choices=['cpu','cuda'],default='cpu'); p.add_argument('--language',default=None)
    args=parser.parse_args()
    try:
        if args.command=='doctor': print(json.dumps(doctor(),indent=2))
        elif args.command=='plan': print(json.dumps(prepare(args.manifest,args.format,args.resolution)[4],indent=2))
        elif args.command=='render': render(args)
        elif args.command=='suggest-tech':
            number(args.threshold,'threshold',-90,-5); number(args.min_silence,'min_silence',0.1,10); number(args.padding,'padding',0,1)
            suggest_tech(args)
        elif args.command=='suggest-football':
            number(args.count,'count',1,200); number(args.before,'before',0,60); number(args.after,'after',0,60); number(args.spacing,'spacing',1,120)
            if args.before+args.after<0.1: raise ValueError('Candidate window must have positive length')
            suggest_football(args)
        else: transcribe(args)
    except (ValueError,KeyError,TypeError,OSError) as exc:
        parser.exit(1,f'Error: {exc}\n')

if __name__=='__main__': main()
