# Media Downloader

A native Windows 10/11 x64 desktop app built with Python 3.12, PySide6 and the
yt-dlp Python API. Fetch a video, choose an available resolution, and save merged
video/audio, silent video, audio, or two separate files. The installed app includes
Python, yt-dlp, FFmpeg, ffprobe, Deno and the EJS solver; end users install no
development tools.

## Run the delivered build

- Installer: `installer/output/MediaDownloader-Setup.exe`
- Portable directory: `dist/MediaDownloader/`; launch `MediaDownloader.exe` and
  keep the entire `_internal` directory alongside it.
- Installer uses Program Files, requests installation elevation, adds a Start
  Menu shortcut and uninstall entry, and offers an optional desktop shortcut.
  Normal use does not require administrator rights.

## Development

Install Python 3.12 or newer on Windows x64. From the project directory:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe tools\setup_vendor.py
.venv\Scripts\python.exe tools\make_icon.py
.venv\Scripts\python.exe run.py
```

The vendor setup script downloads pinned releases from the official Gyan FFmpeg,
Deno and Inno Setup GitHub repositories. It checks GitHub's SHA-256 digest when
provided and records origin/hash manifests. HTTPS verification remains enabled.
Inno Setup's downloaded installer is not executed automatically by that script.
Install the compiler normally, or into `tools/inno`.

Required runtime files:

```text
vendor/ffmpeg/ffmpeg.exe
vendor/ffmpeg/ffprobe.exe
vendor/deno/deno.exe
```

Never rely on a user's PATH for these dependencies. `resource_path()` resolves
them from source or PyInstaller's `_MEIPASS`. FFmpeg is checked before operations
that need it; pure stream downloads can work without it.

## Project layout

```text
run.py                   multiprocessing-safe entry point
app/config.py            application name and version
app/main.py              startup, logging, exception handler, smoke tests
app/window.py            native Qt interface and QSettings
app/worker.py            QThread supervisor, process cancellation and publication
app/downloader.py        yt-dlp API, thumbnails, FFmpeg processing
app/formats.py           resolution and codec selection
app/utils.py             paths, formatting, validation and friendly errors
app/resources/           original app icon
tests/                   unit, real-media and native desktop tests
tools/                   vendor setup, license collection and build tooling
MediaDownloader.spec     onedir, no-console packaging
installer/               Inno Setup script and executable metadata
LICENSES.md              third-party notices and redistribution considerations
```

## Build

Run `build.bat` to create/check the virtual environment, install pinned
dependencies and build `dist/MediaDownloader/MediaDownloader.exe`. The build
script cleans only this project's `build` and application distribution directory.
It regenerates the icon and executable/installer version metadata from
`app/config.py` and collects installed dependency licenses.

Run `build_installer.bat` to compile `installer/MediaDownloader.iss` with Inno
Setup. The result is `installer/output/MediaDownloader-Setup.exe`. It builds the
app first if no executable exists; run `build.bat` explicitly after source changes.
The compiler is found in `tools/inno`, the standard Inno Setup 6 directory or the
standard Inno Setup 7 directory.

The generated binary/installer is unsigned. Windows may show an unknown-publisher
or SmartScreen prompt. Code signing requires the publisher's certificate and is
not included in this project. See `LICENSES.md` before public redistribution.

## Behavior and design

- One operation at a time. The Qt main thread only updates widgets; a QThread
  supervises a separate spawned Python process performing network/media work.
- Metadata is refreshed before each download. Only real advertised video heights
  populate the quality menu. Direct media URLs without advertised resolutions
  offer Best; downloaded unknown codecs are inspected with bundled ffprobe.
- Resolution comes before H.264 preference. At a selected height, H.264/AAC are
  preferred for MP4 when requested. Higher frame rates and yt-dlp's own
  extractor/protocol quality ranking break ties. Advertised streams returning
  HTTP 403/404 are retried with another stream at the same resolution.
  If that height disappears, the best lower height is used and reported.
- MP4, MKV and WebM apply to merged output. Unsupported container/codec pairs
  produce MKV with an explicit completion notice, without video re-encoding.
  Compatibility is a preference, not a promise that all devices support a codec.
- Silent video from muxed input is remuxed to MKV with audio removed. Audio
  Original is retained as-is when already audio-only, or extracted with stream
  copy. M4A copies AAC when possible, otherwise encodes AAC; MP3 uses 192 kbps.
- Two-stream mode produces ` - video` and ` - audio` names. Duplicate output names
  receive `(1)`, `(2)`, etc. Exclusive creation protects existing files.
- Download progress is explicitly per current stream, based on yt-dlp hooks.
  Processing and unknown sizes are indeterminate; completion is shown only after
  media processing and file publication.
- Each operation owns a private temporary directory in the destination. Cancel
  kills only its worker process tree, including FFmpeg/Deno, then removes that
  staging directory. Existing completed files are untouched. Final publication
  cannot be interrupted; partial publication is rolled back on an error.
- Force-killing the entire app or a power failure can leave a `.media-downloader-*`
  staging directory; it can be removed when the app is closed. Cancellation during
  ordinary use cleans it automatically.
- Settings use per-user QSettings. Logs rotate under
  `%LOCALAPPDATA%/MediaDownloader/logs`. Nothing is written to Program Files.
- HTTP(S) only, no shell command interpolation, no account/cookie import, DRM
  bypass, playlists, live streams, queue or subtitles. Metadata is rendered as
  plain text. Only download content you are permitted to save.
- yt-dlp and EJS updates require changing the pinned dependency and rebuilding.
  There is no self-modifying updater.

## Tests

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p test_core.py -v
.venv\Scripts\python.exe tests\integration.py
.venv\Scripts\python.exe tests\test_desktop.py
.venv\Scripts\python.exe run.py --smoke-test test-output\source-smoke.json
dist\MediaDownloader\MediaDownloader.exe --smoke-test test-output\frozen-smoke.json
```

Real-media tests generate a small original test video with FFmpeg and serve it
locally over HTTP. Both muxed and adaptive-stream scenarios run actual yt-dlp
downloads and real FFmpeg processing, with ffprobe assertions on output tracks.
The desktop tests run source and frozen GUI metadata/download flows, cancellation,
and worker failure recovery. GUI smoke tests write a screenshot and resource
report; test runs use isolated settings. See `TEST_RESULTS.md` for this build's
verified results and external-network limitations.

## Troubleshooting

- **Missing FFmpeg:** restore both binaries under `vendor/ffmpeg`, then rebuild.
- **HTTPS certificate error:** check system date/time, Windows trusted roots and
  managed-network certificates. The app uses Windows trusted roots and does not
  disable certificate checking.
- **Unavailable/authenticated content:** select an accessible individual video.
  No login or cookies are supported.
- **Site suddenly stops working:** update yt-dlp/EJS and rebuild; extractor support
  depends on the site's current behavior and regional/network restrictions.
- **Qt DLL error in a custom build:** avoid unrelated ICU/UCRT DLLs on the build
  PATH. The spec sanitizes it to Python and Windows system paths before analysis.
- **Permission/disk space errors:** choose a writable local folder and allow room
  for source streams, processed media and final output during publication.
- **Compiler missing:** install Inno Setup from its official site and use one of
  the paths above. FFmpeg and Deno downloads do not install the compiler.
