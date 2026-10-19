#!/usr/bin/env python3
"""nani desktop editor. Guided controls create the JSON timeline for you."""
from argparse import Namespace
from contextlib import redirect_stdout
from datetime import datetime
import json
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import uuid

from nani import ROOT, doctor, prepare, probe, render, save_new, silence_ranges, transcribe


def timestamp(value):
    """Accept seconds, MM:SS, or HH:MM:SS from a beginner's trim field."""
    parts=str(value).strip().split(':')
    if not 1 <= len(parts) <= 3:
        raise ValueError('Time must be seconds, MM:SS, or HH:MM:SS')
    try:
        nums=[float(x) for x in parts]
    except ValueError:
        raise ValueError('Time must be seconds, MM:SS, or HH:MM:SS') from None
    import math
    if any(not math.isfinite(n) or n<0 for n in nums) or any(n>=60 for n in nums[1:]):
        raise ValueError('Time values must be positive; minutes/seconds after a colon must be below 60')
    return sum(n*60**i for i,n in enumerate(reversed(nums)))


def parse_instructions(text):
    """A deliberately bounded instruction language; unsupported prose is never silently applied."""
    settings={}; errors=[]
    for line in text.splitlines():
        command=re.sub(r'\s+',' ',line.strip().lower()).rstrip('.!')
        if not command: continue
        if command in ('use 9:16','make it vertical','make a short'):
            settings['format']='9:16'
        elif command in ('use 16:9','make it landscape'):
            settings['format']='16:9'
        elif command in ('use 4k','export in 4k'):
            settings['resolution']='4k'
        elif command in ('use 1080p','export in 1080p'):
            settings['resolution']='1080p'
        elif command in ('remove pauses','remove silence'):
            settings['remove_pauses']=True
        elif command in ('keep pauses','keep match audio'):
            settings['remove_pauses']=False
        elif command in ('add subtitles','generate subtitles'):
            settings['auto_subtitles']=True
        elif command in ('smooth transitions','use smooth transitions'):
            settings['transition']='fade'
        elif command in ('jump cuts','use jump cuts'):
            settings['transition']='cut'
        elif command=='zoom in':
            settings['zoom_end']=1.1
        elif command=='no zoom':
            settings['zoom_end']=1.0
        else:
            errors.append(line.strip())
    if errors:
        raise ValueError('Unsupported instructions: '+ '; '.join(errors)+
                         '\nUse the examples shown in the app, one per line. Creative requests need manual choices or an AI-assisted timeline.')
    return settings


def speech_selections(start,end,silences,padding=0.12):
    """Preserve padding, intersect with the user's selected range, never leave the range."""
    regions=[]; cursor=start
    for a,b in sorted(silences):
        cut_start=max(start,a+padding); cut_end=min(end,b-padding)
        if cut_end<=cut_start: continue
        if cut_start-cursor>=0.15: regions.append((cursor,cut_start))
        cursor=max(cursor,cut_end)
    if end-cursor>=0.15: regions.append((cursor,end))
    return regions


def build_manifest(entries,workflow='tech',format='16:9',resolution='1080p',instructions='',remove_pauses=False):
    """Compile guided selections without making the user write JSON."""
    opts={'format':format,'resolution':resolution,'remove_pauses':remove_pauses,**parse_instructions(instructions)}
    if workflow not in ('tech','football'): raise ValueError('Choose tech or football')
    if workflow=='football' and opts['remove_pauses']:
        raise ValueError('Remove pauses is for tech speech. Keep match audio and select football events using Start/End.')
    if not entries: raise ValueError('Add at least one video file')
    clips=[]; cache={}
    for e in entries:
        source=Path(e['source']).expanduser().resolve()
        info=probe(source)
        start=timestamp(e.get('start',0)); end=timestamp(e.get('end',info['duration']))
        if end>info['duration']+0.001 or end-start<0.15:
            raise ValueError(f'{source.name}: select a valid Start/End range of at least 0.15 seconds')
        selections=[(start,end)]
        if opts['remove_pauses']:
            if source not in cache: cache[source]=silence_ranges(source)
            selections=speech_selections(start,end,cache[source])
        for a,b in selections:
            c={'source':str(source),'start':round(a,4),'end':round(b,4),'label':e.get('label',''),
               'focus':[{'time':0,'x':float(e.get('focus_x',0.5)),'y':0.5}],
               'speed':float(e.get('speed',1)),'mute':bool(e.get('mute',False)),
               'replay':bool(e.get('replay',False)), 'zoom_end':opts.get('zoom_end',1)}
            if workflow=='football': c['event']=e.get('event','action')
            if 'transition' in opts: c['transition']=opts['transition']
            elif opts['remove_pauses']: c['transition']='cut'
            if e.get('transcript'): c['transcript']=str(Path(e['transcript']).resolve())
            clips.append(c)
    if not clips: raise ValueError('No usable speech remains; disable Remove pauses or adjust the trim')
    return {'brand':'nani','workflow':workflow,'format':opts['format'],'resolution':opts['resolution'],
            'notes':'Generated by the nani beginner editor. Review before publishing.',
            'editing_instructions':instructions,'clips':clips},opts


def create_project(entries,name='my-video',root=ROOT,**options):
    """Save the generated project and run the same validation as the advanced editor."""
    doctor()
    manifest,opts=build_manifest(entries,**options)
    slug=re.sub('[^a-zA-Z0-9_-]+','-',name).strip('-')[:50] or 'my-video'
    job=f'{slug}-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}'
    folder=Path(root)/'projects'/job
    folder.mkdir(parents=True,exist_ok=False)
    path=folder/'edit.json'
    if opts.get('auto_subtitles'):
        transcripts={}
        for c in manifest['clips']:
            if c.get('transcript'): continue
            if c['source'] not in transcripts:
                dest=folder/f'transcript-{len(transcripts)+1}.json'
                print('Generating optional local subtitles for',Path(c['source']).name,flush=True)
                transcribe(Namespace(source=c['source'],output=str(dest),model='small',device='cpu',language=None))
                transcripts[c['source']]=str(dest.resolve())
            c['transcript']=transcripts[c['source']]
    save_new(path,manifest)
    plan=prepare(path)[4]
    (folder/'instructions.txt').write_text(options.get('instructions',''),encoding='utf-8')
    output=Path(root)/'exports'/job/'finished.mp4'
    print(f'Project: {path}\nPlanned duration: {plan["duration"]:.2f}s\nFinished MP4 will be: {output}',flush=True)
    return path,output


def open_folder(path):
    path=Path(path).resolve()
    if sys.platform=='win32':
        import os
        os.startfile(str(path))
    elif sys.platform=='darwin': subprocess.Popen(['open',str(path)])
    else: subprocess.Popen(['xdg-open',str(path)])


def main():
    try:
        import tkinter as tk
        from tkinter import ttk,filedialog,messagebox
    except ImportError:
        raise SystemExit('Tkinter is missing. Windows: reinstall Python from python.org with Tcl/Tk enabled. Linux: install python3-tk. See WINDOWS.md.')
    app=tk.Tk(); app.title('nani — guided video editor'); app.geometry('1000x900'); app.minsize(850,760)
    entries=[]; selected=[None]; events=queue.Queue(); busy=[False]; last_output=[None]
    outer=ttk.Frame(app,padding=14); outer.pack(fill='both',expand=True)
    ttk.Label(outer,text='nani',font=('Arial',22,'bold')).pack(anchor='w')
    ttk.Label(outer,text='Choose footage, set your editing choices, then export. The app creates the timeline for you.').pack(anchor='w')
    controls=ttk.Frame(outer); controls.pack(fill='x',pady=10)
    variables={}
    for i,(key,title,values,default) in enumerate([
        ('workflow','Content',['tech','football'],'tech'),('format','Shape',['16:9','9:16'],'16:9'),
        ('resolution','Quality',['1080p','4k'],'1080p')]):
        ttk.Label(controls,text=title).grid(row=0,column=i*2,padx=5)
        variables[key]=tk.StringVar(value=default)
        ttk.Combobox(controls,textvariable=variables[key],values=values,state='readonly',width=12).grid(row=0,column=i*2+1)
    name=tk.StringVar(value='my-video'); ttk.Label(controls,text='Project name').grid(row=1,column=0,pady=8)
    ttk.Entry(controls,textvariable=name,width=36).grid(row=1,column=1,columnspan=3,sticky='w')
    ttk.Label(outer,text='1. Add footage (export follows list order; add the same file again for another selection)').pack(anchor='w')
    listing=tk.Listbox(outer,height=5,exportselection=False); listing.pack(fill='x',pady=5)
    bar=ttk.Frame(outer); bar.pack(fill='x')
    fields={k:tk.StringVar(value=v) for k,v in [('start','0'),('end','0'),('label',''),('focus_x','50'),('event','action'),('speed','1'),('transcript','')]}
    replay=tk.BooleanVar(value=False); mute=tk.BooleanVar(value=False)
    pause=tk.BooleanVar(value=False)
    status=tk.StringVar(value='Ready — your original footage stays in its current location.')

    def refresh():
        listing.delete(0,'end')
        for e in entries:
            listing.insert('end',f"{Path(e['source']).name} | {e['start']} → {e['end']} | {e.get('label','')}")
        if selected[0] is not None and selected[0]<len(entries): listing.selection_set(selected[0])

    def select(event=None):
        choice=listing.curselection()
        if not choice: return
        selected[0]=choice[0]; e=entries[choice[0]]
        for k,v in fields.items(): v.set(str(e.get(k,'')) if k!='focus_x' else str(float(e.get(k,.5))*100))
        replay.set(e.get('replay',False)); mute.set(e.get('mute',False))

    def apply():
        if selected[0] is None: return
        try:
            focus=float(fields['focus_x'].get())/100
            if not 0<=focus<=1: raise ValueError('Focus must be between 0 and 100')
            speed=float(fields['speed'].get())
            if not .25<=speed<=4: raise ValueError('Speed must be between 0.25 and 4')
            timestamp(fields['start'].get()); timestamp(fields['end'].get())
            entries[selected[0]].update({k:v.get() for k,v in fields.items()})
            entries[selected[0]].update(focus_x=focus,speed=speed,replay=replay.get(),mute=mute.get())
            refresh()
        except ValueError as exc:
            messagebox.showerror('Check clip settings',str(exc)); raise

    def add():
        if busy[0]: return
        for f in filedialog.askopenfilenames(title='Choose video footage',filetypes=[('Video files','*.mp4 *.mov *.mkv *.avi *.m4v *.webm *.mts'),('All files','*.*')]):
            try:
                info=probe(f)
                entries.append({'source':f,'start':'0','end':str(info['duration']),'label':'','focus_x':.5,
                                'event':'action','speed':1,'transcript':'','replay':False,'mute':False})
            except (ValueError,OSError) as exc: messagebox.showerror('Cannot open footage',str(exc))
        if entries: selected[0]=len(entries)-1
        refresh(); select()

    def remove():
        if busy[0] or selected[0] is None: return
        entries.pop(selected[0]); selected[0]=0 if entries else None; refresh(); select()

    def move(delta):
        if busy[0] or selected[0] is None: return
        i=selected[0]; j=i+delta
        if 0<=j<len(entries):
            try: apply()
            except ValueError: return
            entries[i],entries[j]=entries[j],entries[i]; selected[0]=j; refresh(); select()

    for title,cmd in [('Add footage…',add),('Remove clip',remove),('Move up',lambda:move(-1)),('Move down',lambda:move(1))]:
        ttk.Button(bar,text=title,command=cmd).pack(side='left',padx=3)
    listing.bind('<<ListboxSelect>>',select)
    panel=ttk.LabelFrame(outer,text='2. Selected clip — apply changes before selecting another clip',padding=8); panel.pack(fill='x',pady=10)
    for row,pairs in enumerate([[('start','Start (seconds or MM:SS)'),('end','End')],[('label','Visible label'),('focus_x','Horizontal focus % (0 left / 100 right)')],[('event','Football event'),('speed','Speed (1 normal, 0.5 half speed)')]]):
        for col,(key,title) in enumerate(pairs):
            ttk.Label(panel,text=title).grid(row=row,column=col*2,sticky='w',padx=4,pady=3)
            if key=='event':
                ttk.Combobox(panel,textvariable=fields[key],values=['action','goal','skill','tackle','save'],width=15,state='readonly').grid(row=row,column=col*2+1)
            else: ttk.Entry(panel,textvariable=fields[key],width=23).grid(row=row,column=col*2+1)
    ttk.Checkbutton(panel,text='Append half-speed replay',variable=replay).grid(row=3,column=0,columnspan=2,sticky='w')
    ttk.Checkbutton(panel,text='Mute this clip',variable=mute).grid(row=3,column=2,columnspan=2,sticky='w')
    ttk.Label(panel,text='Existing transcript JSON (optional)').grid(row=4,column=0,sticky='w')
    ttk.Entry(panel,textvariable=fields['transcript'],width=37).grid(row=4,column=1,columnspan=2,sticky='ew')
    def browse_transcript():
        f=filedialog.askopenfilename(filetypes=[('Transcript JSON','*.json')])
        if f: fields['transcript'].set(f)
    ttk.Button(panel,text='Browse…',command=browse_transcript).grid(row=4,column=3)
    def safe_apply():
        try: apply()
        except ValueError: pass
    ttk.Button(panel,text='Apply clip settings',command=safe_apply).grid(row=5,column=0,sticky='w',pady=4)
    ttk.Checkbutton(outer,text='Remove pauses from tech speech (review the cuts)',variable=pause).pack(anchor='w')
    ttk.Label(outer,text='3. Optional text instructions — supported phrases only, one per line').pack(anchor='w',pady=(8,0))
    ttk.Label(outer,text='Use 9:16 · Use 4K · Remove pauses · Keep pauses · Add subtitles · Smooth transitions · Jump cuts · Zoom in').pack(anchor='w')
    instructions=tk.Text(outer,height=3,wrap='word'); instructions.pack(fill='x',pady=4)
    ttk.Label(outer,text='“Add subtitles” needs optional Whisper setup and a model download. Event detection and creative prose need review.').pack(anchor='w')
    log=tk.Text(outer,height=7,state='disabled',wrap='word'); log.pack(fill='both',expand=True,pady=8)
    footer=ttk.Frame(outer); footer.pack(fill='x')
    class Writer:
        def write(self,text):
            if text: events.put(('log',text))
        def flush(self): pass
    def start(export):
        if busy[0]: return
        try:
            apply()
            # Snapshot controls in Tk's main thread; worker never reads Tk objects.
            choices={k:v.get() for k,v in variables.items()}
            choices.update(instructions=instructions.get('1.0','end').strip(),remove_pauses=pause.get())
            parse_instructions(choices['instructions'])
            snapshot=[dict(e) for e in entries]; project_name=name.get()
            if not snapshot: raise ValueError('Add footage first')
        except ValueError as exc:
            messagebox.showerror('Check editing choices',str(exc)); return
        busy[0]=True; save_button.configure(state='disabled'); export_button.configure(state='disabled')
        status.set('Working… large files and 4K exports can take time. See progress below.')
        def worker():
            try:
                with redirect_stdout(Writer()):
                    manifest,output=create_project(snapshot,name=project_name,**choices)
                    if export: render(Namespace(manifest=manifest,output=output,format=None,resolution=None))
                events.put(('done',(export,str(manifest),str(output))))
            except Exception as exc: events.put(('error',str(exc)))
        threading.Thread(target=worker,daemon=True).start()
    save_button=ttk.Button(footer,text='Save project',command=lambda:start(False)); save_button.pack(side='left',padx=4)
    export_button=ttk.Button(footer,text='Export MP4',command=lambda:start(True)); export_button.pack(side='left',padx=4)
    def show_exports():
        folder=Path(last_output[0]).parent if last_output[0] else ROOT/'exports'
        folder.mkdir(parents=True,exist_ok=True)
        try: open_folder(folder)
        except OSError as exc: messagebox.showerror('Open folder',f'{folder}\n{exc}')
    ttk.Button(footer,text='Open exports folder',command=show_exports).pack(side='left',padx=4)
    ttk.Label(outer,textvariable=status,wraplength=950).pack(anchor='w',pady=6)
    def poll():
        while True:
            try: kind,value=events.get_nowait()
            except queue.Empty: break
            if kind=='log':
                log.configure(state='normal'); log.insert('end',value); log.see('end'); log.configure(state='disabled')
            else:
                busy[0]=False; save_button.configure(state='normal'); export_button.configure(state='normal')
                if kind=='error':
                    status.set('Could not finish — see the error. Originals are unchanged.'); messagebox.showerror('nani',value)
                else:
                    exported,manifest,output=value
                    if exported:
                        last_output[0]=output; status.set(f'Finished MP4: {output}')
                        messagebox.showinfo('Export finished',f'Your MP4 is ready:\n{output}\n\nUse Open exports folder to find it.')
                    else: status.set(f'Project saved: {manifest}. Click Export MP4 to render your current choices.')
        app.after(150,poll)
    def close():
        if busy[0]:
            messagebox.showinfo('Export in progress','Wait for this operation to finish before closing the editor.'); return
        app.destroy()
    app.protocol('WM_DELETE_WINDOW',close); poll(); app.mainloop()

if __name__=='__main__': main()
