# BuiltByKeys — quick start

## Beginner desktop workflow — no handwritten JSON

On **Windows**, follow [WINDOWS.md](WINDOWS.md), then double-click **Start-BuiltByKeys.bat**. On Linux/macOS, use `python3 beginner.py` with Tkinter installed (Debian/Ubuntu: `sudo apt install python3-tk`).

1. Choose **tech** or **football**, **16:9** or **9:16**, and **1080p** or **4k**.
2. Click **Add footage**. Set each clip's Start/End, label, football event, replay, speed or crop focus. Apply changes before selecting another clip. Arrange the list with Move up/down.
3. Optionally enter simple instructions, one per line: `Make it vertical`, `Use 1080p`, `Smooth transitions`, `Zoom in`, `Remove pauses`, or `Add subtitles`. Subtitles need optional Whisper setup; unknown instructions are rejected. Remove pauses is for tech speech.
4. Click **Export MP4**. The app creates the timeline and renders the MP4.
5. Click **Open exports folder**. The finished file is `exports/<project-name>-<timestamp>-<id>/finished.mp4` inside the downloaded repository folder. The exact path is shown in the app. Your source files remain where you selected them.

**Save project** creates the internal timeline under `projects/` without rendering. Both `projects/` and `exports/` stay local and are ignored by Git. Keep the app open during rendering. This is a guided editor with a small supported instruction vocabulary; automatic football recognition, ball tracking and unrestricted creative prompt interpretation are not bundled.

## Try the sample workflows

Core editing requires Python 3.10+ and a full FFmpeg/FFprobe installation. Generated MP4s are excluded from Git, so generate sample footage first:

```sh
python3 bbk.py doctor
python3 make_samples.py
python3 bbk.py render examples/tech.json -o exports/tech-demo.mp4
python3 bbk.py render examples/football.json -o exports/football-demo.mp4
python3 bbk.py render examples/tech.json --format 9:16 -o exports/tech-short.mp4
```

On Windows use `py -3` instead of `python3`. MP4, SRT, ASS and report files are saved together. The editor refuses existing output filenames. It verifies source checksums before and after rendering. All samples are synthetic; 4K examples are upscaled format tests.

## Advanced and AI-assisted edits

The original CLI and JSON timeline workflow remain available, with all presets and examples. Copy `examples/tech.json` or `examples/football.json` into a project folder, replace source paths/timestamps, and validate with `python3 bbk.py plan <timeline.json>` before rendering. Optional transcription creates source-time caption JSON; silence detection proposes tech cuts; football audio-energy analysis proposes unclassified review windows.

See [README.md](README.md) for complete settings, [WINDOWS.md](WINDOWS.md) for installation and output access, and [VALIDATION.md](VALIDATION.md) for validation scope. The historical initial build's detailed results are preserved in `validation.json`; current test evidence is documented separately. Regenerate fixtures locally before running tests.
