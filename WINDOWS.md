# Run nani on Windows

## Install once

1. Install **Python 3.10 or newer** from [python.org](https://www.python.org/downloads/windows/). Enable **Tcl/Tk**, the **Python launcher**, and **Add Python to PATH**. Tcl/Tk is what opens the desktop editor.
2. Install a full **FFmpeg** build with FFprobe, libx264, AAC and libass. In PowerShell, one option is:

   ```powershell
   winget install --id Gyan.FFmpeg --exact
   ```

   Alternatively use a Windows build linked from [ffmpeg.org](https://ffmpeg.org/download.html#build-windows), extract it, and add its `bin` folder to your Windows user PATH. Keep `ffmpeg.exe` and `ffprobe.exe` together. If `winget` is missing, use the manual option.
3. Close and reopen PowerShell after installing. Confirm:

   ```powershell
   py -3 --version
   ffmpeg -version
   ffprobe -version
   ```

4. Download the repository with **Code → Download ZIP**, then **Extract All** to a writable local folder such as `Documents\nani`. Before the PR is merged, select the PR's branch first; downloading `main` will only include the editor after merge. Alternatively clone and select the feature branch using Git.

Do not run from inside the ZIP, `Program Files`, or a protected folder. Keep footage on a drive with enough free space and a stable connection. Camera originals are referenced in place; keep a separate backup and do not move them while a project uses them. NTFS is recommended for the project's working/export folder because the renderer publishes files using hard links.

## Open the beginner editor

Double-click **Start-nani.bat**, or open PowerShell in the extracted repository folder and run:

```powershell
py -3 nani.py doctor
py -3 beginner.py
```

If `py` is unavailable but `python` works, replace `py -3` with `python`. If Windows opens the Store instead of Python, install Python from python.org and check the Windows App execution aliases / PATH.

In the app:

1. Choose **tech** or **football**, shape (**16:9** landscape / **9:16** vertical), resolution and project name.
2. Click **Add footage**. Select one or more videos. Add a file again to use another range from it.
3. Select each clip. Set **Start** and **End** using seconds or `MM:SS`. Set its label, football event, optional half-speed replay, speed and horizontal crop focus. Click **Apply clip settings** before selecting another clip. Use **Move up/down** to arrange the story.
4. Optionally use **Remove pauses** for tech speech. Match footage should retain its audio and use selected event ranges.
5. Optionally enter supported text instructions, one per line. For example:

   ```text
   Make it vertical
   Use 1080p
   Smooth transitions
   Zoom in
   ```

   These are explicit command phrases, not a general language model. Unsupported prose produces an error instead of silently guessing. For goals, skills, tackles or saves, choose the event and the Start/End fields yourself. The app does not identify those actions automatically.
6. Click **Save project** to create a reusable timeline internally, or **Export MP4** to save and render. You never need to type JSON. Keep the window open until it finishes; long videos and 4K can take substantial time. Progress and errors appear in the app.

`Add subtitles` is another supported text instruction, but requires the optional AI setup below. You can instead select an existing source-time transcript JSON with **Browse**. Without either choice the export includes brand/event labels but no dialogue captions. Read `README.md` for other supported settings and limitations.

## Find and play your finished MP4

After a successful export, click **Open exports folder**. The app displays the exact path and saves:

```text
Keys\exports\my-video-<timestamp>-<id>\finished.mp4
Keys\exports\my-video-<timestamp>-<id>\finished.srt
Keys\exports\my-video-<timestamp>-<id>\finished.ass
Keys\exports\my-video-<timestamp>-<id>\finished.report.json
```

The folder name may be `Keys`, `Keys-<branch>` or whatever you named the extracted directory. The MP4 opens with VLC or another H.264/AAC-compatible player, and can be uploaded to YouTube. Captions are burned into the picture; the SRT also supports selectable YouTube captions. If the player has no sound, check its selected audio device and volume.

The generated project is under `projects\<same-job-name>\edit.json`. For a later identical rerender without changing any JSON, use:

```powershell
py -3 nani.py render "projects\<job-name>\edit.json" -o "exports\my-rerender-v2.mp4"
```

Replace `<job-name>` with the actual folder. CLI outputs go exactly where `-o` points; relative paths start in your current terminal folder. Existing exports are refused, so choose a new name. The beginner app always creates a new job folder.

**Your MP4s remain on your computer.** GitHub stores source and example timelines; generated footage, exports, transcripts, projects and temporary files are excluded from Git. GitHub does not run the desktop app or produce videos when you open the repository. Share MP4s by uploading them directly to your platform or a storage service.

## Optional local AI subtitles

Core editing needs no pip packages. For local speech recognition using faster-whisper:

```powershell
py -3 -m pip install -r requirements-ai.txt
```

Then use **Add subtitles** in the app's instructions. It uses the `small` Whisper model on CPU, downloads weights on first use, and saves source-time transcripts inside the generated project. A first run needs model-host access and storage; the code sends no footage to a hosted AI API. Proofread names and timing. To select another model or use an already downloaded model folder, run the CLI:

```powershell
py -3 nani.py transcribe "C:\Videos\review.mp4" --model small --language en -o "review-transcript.json"
```

Then select that transcript in the app. The optional transcription model was not installed or run during this build's tests.

## Reproduce the sample tests

Large MP4s are intentionally absent from Git. Generate the synthetic samples locally:

```powershell
py -3 make_samples.py
py -3 -m unittest discover -s tests -v
py -3 nani.py render examples\tech.json -o exports\tech-demo.mp4
py -3 nani.py render examples\football.json -o exports\football-demo.mp4
py -3 verify_exports.py --report current-validation.json
```

Tests and actual exports were verified on Linux. The Windows batch launcher and paths are provided for Windows use, but no Windows desktop session was available to test them here. If the window fails to open, run `py -3 beginner.py` in PowerShell to see the error. A missing `tkinter` means Python needs Tcl/Tk installed. A missing FFmpeg/filter/encoder error is resolved by installing a complete FFmpeg build and checking PATH with `doctor`.
