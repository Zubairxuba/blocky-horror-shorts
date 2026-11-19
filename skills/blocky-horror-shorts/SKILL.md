---
name: blocky-horror-shorts
description: Turn a story idea into a finished vertical (9:16) 3D blocky-character horror Short, built entirely in code with Blender - script, cloned narration, one synced timeline for picture and sound, three parts built in parallel by sub-agents, synthesized SFX, motion preview, final render. Use for "make a horror short", "3D horror story video", "blocky horror animation", or continuing a story folder made with this skill.
license: MIT
---

# Blocky Horror Shorts

You are the **lead**. You write the script, the shared base and the briefs; sub-agents only build pictures. Everything
(sets, characters, cameras, lights, sound) is Python, so every shot is reproducible and every sound lands on its frame.

Skill files (use these exact paths):
- Engine (Blender helpers): `${CLAUDE_SKILL_DIR}/engine/` - `common.py` (boxes, materials, decals, lights, glTF import),
  `characters.py` (blocky cast, faces, blinks, mouth flaps, walks, breathing, head turns), `sets.py`, `camcheck.py`
  (camera-motion QA), `short_qa.py` (rendered-video QA), `assets.py` (downloads CC0 Poly Haven assets), `gen/` (face decals).
- Pipeline (audio + timing): `${CLAUDE_SKILL_DIR}/pipeline/voice.py`, `${CLAUDE_SKILL_DIR}/pipeline/finish.py`.
- Worked example, a complete 1:56 story "Still On": `${CLAUDE_SKILL_DIR}/example/still-on/` (script, `timeline.py`,
  `shared.py`, `assemble.py`, `part1-3/scene.py`). **Copy and adapt it; never import from it.**
- Rules you must follow: [references/story-formula.md](references/story-formula.md),
  [references/production-rules.md](references/production-rules.md), [references/brief-template.md](references/brief-template.md).

## Approval stops (never skip)
1. Full script -> user OK before voicing anything.
2. Shared base preview stills -> user OK before spawning part agents.
3. Low-res motion preview of the WHOLE video with final audio -> user OK before the full render.
Never upload anywhere. Never clone a voice the user has not confirmed they own or may use.

## 0. Setup (first run only)
Check and report what is missing; do not install system software without asking:
- Blender 5.x (`blender --version`; macOS: `/Applications/Blender.app/Contents/MacOS/Blender`). Blender 5 keeps
  animation in layered actions: always reach curves through `C.fcurves(obj)`.
- `ffmpeg` (or set `FFMPEG`/`FFPROBE`), `whisper-cli` from whisper.cpp plus `ggml-base.en.bin` in
  `${CLAUDE_SKILL_DIR}/pipeline/models/` (or set `WHISPER_MODEL`).
- Python 3.10+ with `pip install -r ${CLAUDE_SKILL_DIR}/requirements.txt` (chatterbox-tts, soundfile, numpy, Pillow).
- Assets: `python3 ${CLAUDE_SKILL_DIR}/engine/assets.py` (~530 MB, CC0, once).
- A narrator reference: a clean 10-20 s wav of a voice the user owns or has permission to clone.

## 1. Story folder + script  -> STOP 1
Create `<cwd>/<slug>/` and copy `timeline.py`, `shared.py`, `assemble.py` from the example as templates. In each copy,
replace the `SKILL = Path(__file__)...` line with `SKILL = Path("${CLAUDE_SKILL_DIR}")` so they find `engine/` and `pipeline/`.
Write `script.txt` following [story-formula.md](references/story-formula.md): ONE line per shot, 30-45 lines, under 2:00
spoken. Show the full script and wait for the user's OK. Keep the twist rule written down; it drives every shot.

## 2. Voice
`python ${CLAUDE_SKILL_DIR}/pipeline/voice.py <story> --ref <voice.wav>` -> `narration.mp3`, `timings.json`.
Lines are cached in `<story>/lines/`; to fix one line, edit `script.txt`, delete `narration.mp3`, re-run.

## 3. Timeline (the single clock)
Edit the copied `timeline.py`: `EXTRA` (silence after lines for on-screen beats: knocks, flashes), `LIMIT`, and
`events()`: every synced beat as `(id, time, sound, gain)` with times taken ONLY from words (`w(line, "word")`) or line
ends. Run `python timeline.py` -> `shots.json`, `events.json`, `words_full.json`, `final/narration.mp3`.
Check the printed "voice check: N/M words heard"; if low, listen and fix the line.

## 4. Shared base (lead only)  -> STOP 2
Rewrite `shared.py` for THIS story (keep its API shape: `Part`, `reset`, `render`, `char`, `visible`, `shot`,
`continue_shot`, `check_cameras`, `finish`, plus the story's sets, light/state table, props and weather). Set `PARTS` to
the first line of each of the 3 parts, split at story beats. Every state that more than one part shows (a lamp, a time
of day, a prop's position) lives in ONE central table in `shared.py`, keyed from `events.json`.
Write a small `preview.py` that renders 4-6 stills of the sets and cast (see the example's), look at them, show them.

## 5. Three parts in parallel
Fill [brief-template.md](references/brief-template.md) into `<story>/BRIEF.md` (story, twist rule, API, shot list per
line). Spawn THREE sub-agents in one message (`model: "sonnet"`), one per part, each told: read each file once, write
ONLY `partN/scene.py`, grep Blender output instead of reading whole logs, run the gates, report in <= 200 words.
Agents never edit `shared.py`; if they need a shared change they report it and you make it.

## 6. Review + motion preview  -> STOP 3
- For each part: `blender -b -P ${CLAUDE_SKILL_DIR}/engine/camcheck.py -- <story>/partN/scene.py <story>/partN` and
  read `partN/camcheck.json` (jerks, whips, jump cuts must be 0 or explained). Look at each `partN/test_sheet.png`.
- Render previews in the background: `blender -b -P <story>/partN/scene.py -- --preview` (all three).
- `python assemble.py audio` then `python assemble.py video preview` -> `<story>/preview.mp4`. Show it; wait for OK.

## 7. Final
Full renders in the background (`blender -b -P <story>/partN/scene.py -- `), then `python assemble.py video` ->
`full_video.mp4`, then `python ${CLAUDE_SKILL_DIR}/engine/short_qa.py <story>/full_video.mp4 <story>/qa <story>/shots.json`
and read `qa/report.md`. Report length, loudness, QA flags. Extra attention SFX (a bass drop on frame 1, a riser into
the twist) are just more `events()` rows: re-run `timeline.py`, `assemble.py audio`, `assemble.py video` - no re-render.
