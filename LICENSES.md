# Third-party software notices

This application bundles unmodified third-party components. Their respective
license terms apply; the original notices are in the accompanying `licenses`
directory. No ownership of those components is claimed.

- **yt-dlp 2026.08.19** — Unlicense; [source and notices](https://github.com/yt-dlp/yt-dlp).
- **yt-dlp-ejs 0.8.0** — Unlicense, with MIT / ISC components; [source](https://github.com/yt-dlp/ejs).
- **FFmpeg / ffprobe 9.0.2**, Gyan essentials Windows build — this particular
  build is GPLv3, not an LGPL-only build. FFmpeg runs as a separate executable.
  [Provider and build information](https://www.gyan.dev/ffmpeg/builds/),
  [exact release](https://github.com/GyanD/codexffmpeg/releases/tag/9.0.2),
  [FFmpeg source revision](https://github.com/FFmpeg/FFmpeg/commit/946fcce07b),
  [license guidance](https://ffmpeg.org/legal.html).
- **PySide6 / Shiboken6 / Qt 6.11.2** — open-source distributions include LGPLv3,
  GPL and other third-party notices. This app uses Qt Core, Gui, Widgets and their
  runtime dependencies through dynamically loaded libraries; it does not use
  Qt WebEngine. [Qt for Python licensing](https://doc.qt.io/qtforpython-6/licenses.html),
  [Qt source](https://download.qt.io/official_releases/qt/),
  [PySide source](https://code.qt.io/cgit/pyside/pyside-setup.git/).
  The onedir installation keeps these libraries replaceable. No application
  restriction is imposed on reverse engineering to debug modifications to LGPL
  components.
- **Deno 2.9.7** — MIT and bundled third-party notices;
  [source and license](https://github.com/denoland/deno/tree/v2.9.7).
- **Python 3.12** — PSF and bundled notices; [source](https://www.python.org/downloads/source/).
- **PyInstaller** — GPL with a bootloader exception; [license](https://pyinstaller.org/en/stable/license.html).
- Python dependency notices for Requests, urllib3, certifi, idna,
  charset-normalizer, Brotli, Mutagen, PyCryptodome and websockets are included.
- **Inno Setup** is a development/installer tool;
  [terms and source](https://github.com/jrsoftware/issrc).

The included installer is a local development/personal-use build, not a signed
public release. Before distributing it to other people, supply the corresponding
source and build materials required for the exact FFmpeg/Qt and other copyleft
components, retain their notices, and review the applicable terms. Upstream links
alone are not a blanket statement that every redistribution obligation has been
fulfilled. The FFmpeg package hash and official download URL are recorded in
`vendor/ffmpeg.zip.json`; analogous records exist for Deno and Inno Setup.
