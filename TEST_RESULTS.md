# Verification — Windows 11 x64, 24 September 2026

## Passed

- Python 3.12.14 source app launch; native window visually inspected.
- 10 core unit tests: actual qualities, duplicate removal, DRM/non-video exclusion,
  resolution-before-codec preference, FPS preference, lower-resolution fallback,
  extractor ranking, audio choice, URL validation, formatting, Unicode filenames,
  safe collisions and Windows reserved filenames.
- 3 real-media integration test groups, covering metadata and 14 mode/format
  scenarios using generated local media served over HTTP. Real yt-dlp downloads,
  FFmpeg processing and ffprobe verification, for both muxed and separate sources.
- Regression for previously selected `requested_formats` in fetched metadata:
  the download respects the newly chosen stream rather than the stale default.
- Desktop tests: source and packaged app fetch/download; network cancellation;
  active FFmpeg child cancellation; failure recovery. Cancellation preserved an
  existing file and removed the operation's staging directory.
- Public YouTube metadata: Blender's official Big Buck Bunny video. Returned
  title, uploader, duration, thumbnail and 144p through 2160p qualities.
- Public YouTube download: complete 144p MP4 with H.264 video and AAC audio.
  ffprobe independently confirmed a 256×144 video track and an audio track.
- PyInstaller onedir GUI executable built; packaged GUI and download worker ran.
  Bundled FFmpeg and Deno locations verified. The executable includes Python and
  its dependencies. PE subsystem is Windows GUI (2), not console.
  Final launch with only Windows System32 on PATH returned exit code 0 and
  reported no console window; no system Python/FFmpeg/Deno was needed.
- Inno Setup 7.1.0 compiler obtained from its official release; release digest
  verified and Windows Authenticode signature valid. Installer compiled with
  Program Files destination, Start Menu entry, optional desktop shortcut and
  automatic uninstall registration.

The source/frozen smoke reports, GUI screenshots, live metadata and live-download
results are in `test-output/`. Executable build logs and installer compiler logs
are also retained there. Test media is confined to that directory.

## Scope and limitations

- Tested on this Windows 11 machine, not on a clean Windows 10 VM or every
  supported site. All four modes were exercised with local HTTP fixtures; the
  public-site end-to-end test was the 144p merged MP4 case.
- The installer was compiled and its script/output inspected; a full Program
  Files installation/uninstall was not performed on this development computer.
- The build is unsigned. SmartScreen reputation and code signing are not tested.
- Site restrictions, authentication, DRM and live streams remain unsupported;
  extractor changes require an updated application build.
- No high-resolution video transcoding occurs. Requested WebM/MP4 may fall back
  to MKV with an explicit notice if the source codecs require it.
- Qt/FFmpeg and other redistribution obligations are described in LICENSES.md;
  this is a local development/personal-use build, not a public release package.

## Issues found and resolved during verification

1. Preview card clipping at the initial size: corrected layout minimums.
2. Network TLS validation: use trusted Windows roots without disabling checking.
3. Frozen Qt startup error: excluded unrelated build-host ICU/UCRT PATH pollution.
4. Windows device filenames such as `CON`: prefix reserved names safely.
5. yt-dlp default merged selection leaked into later individual downloads:
   clear stale selection fields before applying the requested stream.
6. Manifest bitrate could override extractor protocol preferences: preserve
   yt-dlp's ranking after resolution, codec preference and frame rate.
