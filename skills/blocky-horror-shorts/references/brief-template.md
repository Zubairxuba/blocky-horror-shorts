# Brief template (lead fills the <...> parts, saves as <story>/BRIEF.md)

A filled example is the "Still On" story in `example/still-on/` (its scenes show every API below in use).

````markdown
# Brief: build ONE part of "<TITLE>" (Blender 3D blocky horror Short, <LENGTH>, 3 parts)

You are one of three agents. Each builds the PICTURE for one part. The lead already made everything shared: voice,
sound mix, the timeline, sets, characters, lights, weather, the camera helper. You write ONE file: `partN/scene.py`.
Work cheaply: read each file once, grep Blender output for errors instead of reading whole logs.

## The story (read all of it; you own one slice)
Script: `<STORY>/script.txt` (line N = shot N).
<2-6 lines: the town rule, the cast with their looks, the TWIST in bold.>

### THE TWIST RULE (break it and the video breaks)
<what must never be seen before the reveal, e.g. who never looks at whom, and the single exception line>

## Your files
- WRITE ONLY `<STORY>/partN/scene.py`. Never edit `shared.py`, `timeline.py`, `assemble.py`, the skill's `engine/`, or
  another part. If you need a shared change (a new face, prop, set piece, a light state), STOP and say so in your report.
- Read first: `<STORY>/shared.py` (API + coordinates at the top), `<SKILL>/engine/characters.py`, `<STORY>/preview.py`.
  `events.json` = every synced beat (id -> frame); `words_full.json` = each word's time.

## The scene.py shape (required, so the checkers can run it)
```python
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # the story folder
import shared as S          # noqa: E402
import characters as C      # noqa: E402
import bpy                  # noqa: E402

def make(s, p):             # p = S.Part(N): p.shot(line) -> (a, b, speech_start, speech_end) in YOUR frames,
    ...                     # p.ev("id") -> event frame, p.word(line, "word") -> frame that word is spoken,
    S.finish(s, p)          # p.foley(frame, "step", gain) -> add a footstep sound, p.last -> your last frame

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    s = S.reset(32)
    p = S.Part(N)
    make(s, p)
    S.render(s, p, args)    # --frames 10,50 -> partN/test/ ; --preview -> partN/preview/ ; nothing -> partN/frames/
```
Run: `blender -b -P <STORY>/partN/scene.py -- --frames 10,200`

## Shared things you MUST use (never re-invent them)
<list the story's sets, S.char looks (each with its own hair + outfit), faces, props, the light/state table call,
weather, the sky (`look.sky` is set in shared.py), where real trees stand, S.shot / S.continue_shot>

## Sync
Key every visual beat ON its event frame (<list the event ids of this story>). The sound is placed centrally on the
same frames. A speech-start frame is `p.shot(line)[2]`; words: `p.word(line, "word")`.

## Rules
Follow `<SKILL>/references/production-rules.md` (camera, cinematic look, picture, sync, sound coverage). Act, don't
pose: characters react, turn, gesture and walk with weight. Test renders only, <= ~40 frames total.
List in your report every on-screen action that makes a sound but has no event.

## Gates before you report
- `S.finish(s, p)` passes and `blender -b -P <SKILL>/engine/camcheck.py -- <STORY>/partN/scene.py <STORY>/partN`
  gives 0 flags (or explain each) in `partN/camcheck.json`.
- A contact sheet you looked at: the middle AND last frame of every shot, tiled with ffmpeg, `partN/test_sheet.png`.
  Fix cut-off heads, dark faces, empty frames, twist-rule breaks.
- Seconds per frame on one full-quality test frame.

## Deliver (final message, <= 200 words)
Done or not; s/frame; camcheck result; known issues; actions without a sound event; any shared change you need.

## Shot list (line: what we see)
### Part 1 (lines 1-<n>): <beat>
1 <...>
### Part 2 ...
### Part 3 ...
````
