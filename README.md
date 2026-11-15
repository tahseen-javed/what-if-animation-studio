# What If Animation Studio

Script in, finished 16:9 animated video out. Every frame is SVG drawn in code and rendered by [Remotion](https://www.remotion.dev); the voice is [Chatterbox TTS](https://github.com/resemble-ai/chatterbox) (open source, no API key); everything heavy runs on GitHub Actions, so no GPU or fast laptop is needed.

Built on the free **What If Animation** skill by Jackson AI (MIT, see `.claude/skills/what-if-animation/LICENSE`), with the voice step moved from ElevenLabs to Chatterbox.

## What it makes

- 1920x1080, 30 fps (YouTube 16:9), mastered to -14 LUFS with true peak under -1 dBTP.
- Stylized 2D stick-figure animation in perspective rooms with lamp and window lighting. It is **not** true 3D.
- Short episodes (15-25 s) out of the box. Long-form (10-20 min) is done as chapters of 60-90 s rendered in parallel and joined (see Roadmap).

## How it works

```
script (episode.json) -> Chatterbox voice (per beat, cached, fixed seed)
  -> faster-whisper word timings -> shot list / cuts on words (plan.py)
  -> storyboard stills + self-check -> animation (shots.tsx) -> sound (sfx.py)
  -> render + master (master.py) -> <slug>-final.mp4
```

## Run it on GitHub (no local install)

Actions -> **make-video** -> Run workflow, with the episode folder name as `slug` and a stage:

| Stage | Does | Result |
|---|---|---|
| `voice` | Chatterbox voice, word timings, shot timing | committed back to the repo |
| `board` | typecheck, storyboard stills | artifact |
| `render` | render, mix, master to -14 LUFS | `*-final.mp4` and `report.json` artifact |

Optional secret `ELEVENLABS_API_KEY`, only for brand-new sound effects (a library of ~56 clips ships).

## Measured (first runs, private repo, 2-vCPU runner)

| Job | Result |
|---|---|
| Render and master, 18.8 s episode (564 frames) | 12 min 48 s |
| Chatterbox, short lines | ~0.85-1.8 s per character, 13/13 words aligned |

Public repos get a larger runner and free minutes, so expect these to improve. A 10-minute video is 18,000 frames, so it must be split into parallel chapters.

## Local use

```
cd what-if-studio && npm install && npx remotion studio src/index.ts
```
Voice locally needs Python 3.11 with `chatterbox-tts` and `faster-whisper` (set `CHATTERBOX_PYTHON`, or use `tools/chatterbox/.venv`). On CPU it is slow; prefer the workflow.

## Roadmap

- Chapter matrix workflow (voice and render per chapter in parallel, then `ffmpeg` concat and final loudness pass).
- Reference-voice sample for one consistent narrator across chapters.
- More sets (apartments, lounge) merged from the reference fork.

## Credits and licences

See [NOTICE.md](NOTICE.md). Remotion is free for individuals and companies of up to three people; check their licence before commercial use. Sound clips in `library/sfx` were generated with ElevenLabs; check their terms (free plan: non-commercial, attribution) before monetising.
