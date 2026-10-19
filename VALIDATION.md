nani validation — 19 October 2026

Python 3.12.14; FFmpeg / FFprobe 7.1.5.
8 unit tests passed. 7 complete MP4 exports passed all verification checks.
Checks: dimensions, H.264/AAC, yuv420p, Rec.709 tags, frame rate, timeline duration, audio/video sync, full decoding, original source SHA-256 checksums.

Verified exports:
- exports/4k-landscape-smoke.mp4: 3840x2160, 30 fps, 1 seconds
- exports/4k-portrait-smoke.mp4: 2160x3840, 30 fps, 1 seconds
- exports/football-1080p.mp4: 1920x1080, 50 fps, 7.9 seconds
- exports/football-vertical-1080p.mp4: 1080x1920, 50 fps, 7.9 seconds
- exports/silent-multisource-smoke.mp4: 1920x1080, 30 fps, 1.5 seconds
- exports/tech-1080p.mp4: 1920x1080, 30 fps, 7.3 seconds
- exports/tech-short-1080p.mp4: 1080x1920, 30 fps, 7.3 seconds

All sample footage is synthetic. 4K exports upscale 1080p test sources.
Optional faster-whisper is not installed; AI inference was not tested.
Manual event selection and crop keyframes are supported. Audio candidates do not semantically detect football actions.

## Repository and beginner-workflow validation

The repository migration preserves the initial evidence above and in `validation.json`; generated video files are deliberately excluded from Git.

The expanded test suite passes **17 tests**, including the original editor tests and beginner time parsing, bounded text instructions, rejection of unsupported creative prose, silence-cut boundaries, football event/replay selections, internal project generation and transcript references.

A real export through `beginner.create_project` and the renderer produced a **1080 × 1920, 30 fps, 1-second H.264/AAC MP4** from the synthetic tech source. `beginner-validation.json` records passing dimensions, pixel format, Rec.709 tags, frame rate, timeline duration, audio/video sync, full decoding and unchanged original SHA-256 checksums. Its video and project files stay local under ignored `exports/` and `projects/` folders.

Tkinter imports successfully in this Linux environment. No display server or Windows desktop session was available, so window layout, Windows batch execution and operating-system folder opening were not exercised. Beginner project compilation and actual FFmpeg export were tested without a display. Optional Whisper inference remains untested and requires separate installation/model weights.

Reproduce the source tests after a fresh checkout:

```sh
python3 make_samples.py
python3 -m unittest discover -s tests -v
```

After rendering local MP4s, use `python3 verify_exports.py --report current-validation.json` to create new evidence without replacing the preserved initial `validation.json`.

## nani rename verification

The current application's title, visible labels, default watermark, generated captions/examples, Windows launcher, command-line module, temporary-file prefix and documentation use **nani**. The command-line entry point is `nani.py`; the Windows launcher is `Start-nani.bat`.

After renaming, all **17 tests passed**. A new 1080 × 1920, 50 fps football sample with an appended half-speed replay rendered successfully and passed full decoding, codec, Rec.709 metadata, duration, audio/video sync and unchanged-source checks. The generated overlay uses the new name. Both workflow preset files are byte-for-byte unchanged, and the video-processing engine differs only in branding. Earlier synthetic fixtures and test exports were preserved outside the active application before generating newly branded samples.

The latest render verification remains local in ignored `current-validation.json`. Windows desktop execution and optional Whisper inference were not tested in this Linux environment.
