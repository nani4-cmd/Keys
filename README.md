# nani video editing system

**Beginner:** follow [QUICKSTART.md](QUICKSTART.md) or the step-by-step [Windows guide](WINDOWS.md), then launch `beginner.py` (Windows: double-click `Start-nani.bat`). Choose footage and editing options, enter supported instructions, and click **Export MP4**. The app generates JSON internally; you do not need to write it. **Open exports folder** reveals `exports/<job>/finished.mp4` on your computer.

Supported text instructions (one per line): `Use 9:16` / `Make it vertical` / `Make a short`, `Use 16:9` / `Make it landscape`, `Use 4K` / `Export in 4K`, `Use 1080p` / `Export in 1080p`, `Remove pauses` / `Remove silence`, `Keep pauses` / `Keep match audio`, `Add subtitles` / `Generate subtitles`, `Smooth transitions` / `Use smooth transitions`, `Jump cuts` / `Use jump cuts`, `Zoom in`, `No zoom`. They override corresponding controls. Subtitles require optional Whisper installation unless you attach an existing transcript. Unknown instructions produce an error. This bounded command parser does not interpret unrestricted creative prose or detect football events; choose ranges/events and crop focus using the controls.

A reusable, local Python + FFmpeg editor for tech reviews and football highlights. All edits are described in JSON. Original footage is opened for reading, SHA-256 checked before and after a render, and never replaced. Every render produces a finished H.264/AAC MP4, retimed SRT captions, an ASS overlay file and a JSON report. Existing outputs are refused.

## Start here

Requires Python 3.10+ and a full FFmpeg build (recommended 6+; tested on 7.1.5) with FFprobe, libx264, AAC and libass. Core editing needs no pip packages, API keys or external services. The optional desktop launcher also uses Python’s Tkinter; see WINDOWS.md for setup. If FFmpeg is missing on another machine, install it using your system package manager (for example `sudo apt install ffmpeg` on Debian/Ubuntu or `brew install ffmpeg` on macOS), then run `doctor` again. Use upright SDR Rec.709 source footage with square pixels. Linux, macOS and Windows Python/FFmpeg installations are supported by the command structure; this build was tested on Linux only. A font such as DejaVu Sans or Arial must be available to libass.

```sh
python3 nani.py doctor
python3 make_samples.py
python3 nani.py plan examples/tech.json
python3 nani.py render examples/tech.json -o exports/my-tech.mp4
python3 nani.py render examples/football.json -o exports/my-football.mp4
python3 nani.py render examples/tech.json --format 9:16 -o exports/my-short.mp4
python3 nani.py render examples/football.json --format 9:16 -o exports/my-football-vertical.mp4
python3 nani.py render examples/tech.json --resolution 4k -o exports/my-tech-4k.mp4
```

On Windows use `python` when `python3` is unavailable. Quote paths containing spaces. Run from this folder; input paths in JSON are always relative to the manifest itself, while `-o` is relative to the current working directory. Absolute local source paths also work. Use a new output name for each revision.

MP4s are excluded from Git. Run `python3 make_samples.py` before the example commands or tests to generate the **synthetic test footage**, not real hardware reviews or matches. `make_samples.py` can regenerate missing examples without a network connection. The captions are authored demo text; the synthetic audio is a tone or simulated crowd noise, not spoken words. Football event labels identify manually chosen test windows, not detected actions. The 4K smoke tests upscale 1080p fixtures to verify output dimensions; they do not demonstrate native 4K image quality.

## Local files and GitHub

The repository preserves source code, presets, example JSON, tests and instructions. Camera footage, generated MP4s, project folders, exports, optional AI transcripts, caches and temporary files stay local and are ignored by `.gitignore`. The initial synthetic validation evidence is retained as small text files; it does not mean video files are bundled. Regenerate samples using `make_samples.py`. GitHub hosts the editor's code; run it on your own computer to create MP4s. The GUI saves a new project in `projects/<job>/edit.json` and exports to `exports/<job>/finished.mp4`. The CLI writes to the path provided with `-o`. Open the MP4 with a video player or upload it to YouTube.

## Supply your own footage

1. Make a project folder, for example `projects/review/`, and copy camera files into `projects/review/originals/`. Keep a separate backup of camera originals.
2. Copy `examples/tech.json` or `examples/football.json` into that project folder as `edit.json`.
3. Replace every `source` with the relative path to your clip, such as `originals/camera-a.mp4`. Use separate entries for talking head, B-roll, gaming peripherals, PC assembly and benchmarks, in the desired sequence. Multiple cameras and sources can be mixed sequentially; simultaneous picture-in-picture is not implemented.
4. Set `start` and `end` in **source seconds**. For football, select the buildup, action and aftermath, then label the event `goal`, `skill`, `tackle` or `save`. The labels are metadata; selection is determined by your ranges.
5. Adjust crop focus, captions, transitions and replay settings; run `plan` to validate; render to a new filename.
6. Watch and listen to the full export before publication. Check sentence boundaries, product details, the ball during portrait crops, replay cadence and levels. Upload the SRT separately to YouTube when you want selectable captions (the MP4 also contains burned-in subtitles).

Example tech timeline (save beside your `originals/` folder):

```json
{
  "brand": "nani",
  "workflow": "tech",
  "format": "16:9",
  "resolution": "1080p",
  "clips": [
    {"source":"originals/talking-head.mp4", "start":2.4, "end":8.1,
     "label":"KEYBOARD REVIEW", "zoom_end":1.08,
     "transcript":"talking-head.transcript.json"},
    {"source":"originals/keyboard-broll.mp4", "start":1, "end":5,
     "label":"BUILD QUALITY", "transition":"fade", "mute":true}
  ]
}
```

A football selection with an appended slow replay and a portrait crop that follows the action:

```json
{
  "workflow": "football", "format": "9:16", "resolution": "1080p",
  "clips": [
    {"source":"originals/match.mp4", "start":125.5, "end":132,
     "event":"goal", "label":"GOAL · 23 MIN",
     "replay":true, "replay_speed":0.5,
     "focus":[
       {"time":0, "x":0.35, "y":0.50},
       {"time":3, "x":0.55, "y":0.50},
       {"time":6.5, "x":0.72, "y":0.48}
     ]}
  ]
}
```

The full selected range is replayed. For a short replay of only the strike or save, add a second explicit clip with its own `start`, `end`, `speed: 0.5` and `label: "REPLAY"` instead of `replay: true`. Replay audio is time-stretched with pitch preserved; set `mute: true` on an explicit replay if you prefer silence.

## Manifest reference

| Field | Meaning |
| --- | --- |
| `workflow` | `tech` or `football`; selects a reusable preset. |
| `brand` | Watermark text; defaults to nani. |
| `format` | `16:9` or `9:16`; CLI `--format` overrides it. |
| `resolution` | `1080p` or `4k`; CLI `--resolution` overrides it. |
| `settings` | Optional overrides for fields in the workflow preset. |
| `clips` | Ordered source selections. Ranges may overlap or be reused. |
| `source` | Local file path relative to the manifest, or absolute local path. |
| `start`, `end` | Source timestamps in seconds; start defaults to 0, end to source duration. |
| `transition` | Incoming transition: `cut`, `fade`, `wipeleft`, `slideright`. First clip has no incoming transition. |
| `speed` | Playback rate, 0.25–4; defaults to 1. Audio is stretched to match. |
| `zoom`, `zoom_end` | Start/end zoom factor, 1–2; defaults to 1. Linear push or pull around crop center. |
| `focus` | List of `{time,x,y}` keyframes. `time` is seconds from selection start at original playback rate; `x/y` are normalized source coordinates, 0–1. Keys interpolate linearly, then hold. Crop is clamped to image edges. |
| `event`, `label` | Event metadata and visible title; title falls back to `event`. |
| `replay`, `replay_speed` | Append the whole selection as a replay; default replay speed 0.5. |
| `mute` | Silence the selected source audio, including an automatic replay. |
| `captions` | Inline `{start,end,text}` entries, using full-source timestamps. |
| `transcript` | JSON with `segments:[{start,end,text}]`, using full-source timestamps; replaces inline captions. |

Transitions shorten the timeline by their overlap. The report records every exact output start and duration, including replays. Captions are clipped, retimed for playback speed and shifted across cuts and transitions. Replays omit duplicate speech captions. Captions during crossfades may overlap; shorten the caption text or use a cut at dialogue boundaries. Long text wraps automatically; vertical captions reserve lower space for platform UI, but check each platform's current controls. SRT files are empty for a project with no dialogue captions. Brand and event labels appear in the MP4/ASS, not the dialogue SRT.

Crop focus represents the desired subject center, not the left edge. All formats fill the screen by cropping to the target aspect ratio, then scaling. A 16:9 source loses much of its width in 9:16. Review the focus for each short; the same focus can work for both orientations, but wider context may need a separate portrait timeline. No automatic ball or face tracker is included. Source pixels must be square, with rotation baked in.

## Workflow presets and export settings

`presets/tech.json`: 30 fps, clean jump cuts by default, mild contrast/saturation boost, speech high-pass and FFT noise reduction, -16 LUFS target, -1.5 dBTP ceiling. Add fades for product B-roll or animated zooms for emphasis. Selected source audio plays in sequence: separate music beds, ducking and simultaneous B-roll over continuing narration are not included. For that arrangement supply a pre-mixed narration/B-roll clip, or prepare the audio assembly externally.

`presets/football.json`: 50 fps, short fades, mild grade, a 35 Hz rumble filter and wider loudness range to retain match atmosphere. It avoids speech noise reduction that could damage crowd audio. Output `settings.fps` must be a whole number (fractional source rates are accepted and normalized). Set it to 60 for 60 fps matches or 25/30 for lower-rate footage. Slow motion repeats captured frames as necessary; there is no optical-flow frame synthesis. 50/60/100/120 fps sources give better slow-motion results than 25/30 fps footage. The output FPS alone does not create new action detail.

Both presets use two-pass measured FFmpeg loudness normalization on the assembled audio, H.264 CRF 18, AAC stereo 48 kHz/192 kbps, `yuv420p`, fast-start MP4 and SDR Rec.709 output tags. Short clips and changing dynamics can prevent exact integrated loudness; AAC can slightly change true peaks. Listen to the export. Denoising cannot reconstruct clipped or badly distorted recordings.

| Export | Landscape | Portrait |
| --- | --- | --- |
| 1080p | 1920 × 1080 | 1080 × 1920 |
| 4K | 3840 × 2160 | 2160 × 3840 |

Use 4K when your source and final crop have enough detail. A portrait crop from a 3840 × 2160 landscape source has only about 1215 × 2160 source pixels before scaling; vertical 4K will still be an upscale. The report warns about source dimensions. 4K is CPU-, RAM- and disk-intensive; intermediates contain lightly compressed video and PCM audio. Use `settings.encoder_preset: "veryfast"` for previews, or render a 1080p review first. The final encode and an intermediate encode are lossy, so retain the camera originals. The temporary intermediates are deleted even on an error; re-rendering starts over. Large edits use one transition filtergraph: split long programmes into chapters if RAM becomes limiting.

The grade is a reusable mild starting point, not automatic exposure or white-balance matching. HDR/log sources need camera-specific conversion and grading first. HDR PQ/HLG and rotation metadata are rejected to avoid a misleading result. Example conversion for a known SDR rotated input: use FFmpeg's normal autorotation to transcode to an upright working copy and verify it before use. For non-square-pixel sources create a square-pixel working copy. Do not just label HDR as Rec.709; use a correct tone-map or a colour-managed editor and keep the original.

## AI assistance and review boundaries

### Optional local transcription

Whisper is optional and **was not installed or run in this environment**. The tested core workflow uses authored captions. To enable recognition in your own environment:

```sh
python3 -m venv .venv
# Linux/macOS:
. .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python3 -m pip install -r requirements-ai.txt
python3 nani.py transcribe projects/review/originals/talking-head.mp4 --model small --language en -o projects/review/talking-head.transcript.json
```

`faster-whisper` uses CTranslate2. A named model downloads model weights on first use (network access, storage and model-host access are needed). Use `--model /path/to/local-model-folder` for an already downloaded CTranslate2 model. CPU uses int8; `--device cuda` requires compatible NVIDIA/CUDA/cuDNN libraries. No video or audio is sent to a hosted AI API by this code. A model download contacts the model host. Model quality, hallucinations in silence, product names and timing need proofreading. Transcripts use source time, so they remain reusable across different cuts.

### Proposed tech jump cuts

```sh
python3 nani.py suggest-tech projects/review/originals/talking-head.mp4 -o projects/review/proposed.json
python3 nani.py plan projects/review/proposed.json
```

This uses FFmpeg silence detection, not a language model. Default threshold is -35 dB for at least 0.4 s, with 0.12 s retained at each edge. Tune `--threshold`, `--min-silence` and `--padding` for your microphone. It can cut quiet speech or keep noisy pauses. Review the resulting clip ranges, attach a source transcript to **each** relevant clip, and make creative selections before rendering. It does not remove filler words or choose the best take.

### Football highlight candidates

```sh
python3 nani.py suggest-football projects/match/originals/match.mp4 --count 12 --before 6 --after 4 -o projects/match/candidates.json
```

This ranks 1-second audio RMS windows, spacing peaks by at least 12 seconds. It proposes unclassified review windows only. Commentary, crowd noise, whistles and music can all produce false positives; quiet goals, skills, tackles or saves can be missed. Candidate windows are not an edit manifest and do not render automatically. Watch the windows, classify the event, adjust buildup/aftermath and copy accepted ranges into a football manifest.

Reliable semantic event detection needs a trained sports action model, representative labelled data and validation on your camera view. Automatic action cropping needs a ball/player detector plus tracking, occlusion handling and camera-motion handling. Neither model is bundled. Manual timestamps and focus keyframes are the supported deterministic workflow. An external model or AI assistant can generate the same JSON fields, but its suggestions require review. Narrative choices, pacing, take selection, accurate match context and final colour/audio decisions remain editorial work.

## Verification and delivery

```sh
python3 make_samples.py
python3 -m unittest discover -s tests -v
python3 verify_exports.py --report current-validation.json
```

`verify_exports.py` checks locally rendered dimensions/codecs/duration, fully decodes the MP4s, compares audio and video duration, checks Rec.709 tags, and verifies source checksums against the render reports. See `validation.json` for the preserved initial build results and VALIDATION.md for the latest verification scope. Unit tests cover replay timing, transitions, caption remapping, speed handling, output protection and invalid ranges/focus. Sample render reports are beside each MP4. Tests demonstrate processing with controlled fixtures; real-world footage quality and AI recognition accuracy have not been validated.

The editor intentionally has no overwrite switch. Delete or move a prior export yourself, or use a new output name. Sources must exist and be seekable local files. The renderer keeps FFmpeg arguments as separate process arguments and generates its own numeric filter expressions; it never runs a shell or executes model-generated commands.
