# Blocky Horror Shorts: AI YouTube Shorts generator for Claude Code + Blender

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Claude Code skill](https://img.shields.io/badge/Claude%20Code-skill%20%2B%20plugin-8A63D2)
![Blender 5](https://img.shields.io/badge/Blender-5.x-orange)
![Free tools only](https://img.shields.io/badge/cost-free%20%26%20local-green)

A [Claude Code](https://claude.com/claude-code) skill that turns a story idea into a finished **vertical 9:16 3D animated
horror Short** for YouTube Shorts, TikTok or Instagram Reels. Everything is generated as **Blender Python code**: sets,
blocky characters with faces and lip flaps, cameras, lights, weather, narration, sound effects and the final edit.
It is built for **faceless horror story channels**.

No paid APIs: a local voice clone (Chatterbox), local Whisper timing, CC0 assets and ffmpeg-synthesized sound effects.

> Ask Claude: *"make a 2-minute horror short about a town where every porch light must stay on"*.
> You approve the script, the set stills and a low-res preview; it renders the rest.

## Features
- **Story to video:** writes a 1:30–2:00 twist horror script (town rule → best friend → clues → countdown → twist), then
  produces it shot by shot.
- **Picture and sound in sync:** one timeline built from the narration's word timings. Every knock, flash or footstep is
  keyed on the frame its sound plays.
- **Procedural 3D animation in Blender:** blocky character rigs, blinking and talking faces, walk cycles with foley,
  porch lamps, snow and rain, lightning.
- **Cinematic camera rules enforced in code:** one eased move per shot, speed caps, a 30°/180° cut check, and no
  cameras inside props (`camcheck.py`).
- **Multi-agent production:** three Claude sub-agents build the three parts of the video in parallel against one
  shared base, so the parts match.
- **Automatic QA:** contact sheets, plus checks for black, frozen and popping frames and loudness (-14 LUFS for YouTube).
- **Voice cloning from your own sample** (Chatterbox). No voice audio is shipped.
- **No captions by default.** They can be added lower-third.

## How it works
```
script.txt ──► voice.py ──► timeline.py ──► shots.json + events.json   (one clock for picture AND sound)
                                   │
              shared.py (sets, cast, light table, camera rules)
                                   │
          ┌────────────────────────┼────────────────────────┐
     part1/scene.py           part2/scene.py           part3/scene.py    (3 sub-agents in parallel)
          └──────── Blender frames ┼────────────────────────┘
                                   │
                assemble.py: synthesized SFX on event frames + voice + drone ──► full_video.mp4
```

## Install
As a Claude Code plugin:
```
/plugin marketplace add Zubairxuba/blocky-horror-shorts
/plugin install blocky-horror-shorts@blocky-horror-shorts
```
Or copy just the skill: `cp -r skills/blocky-horror-shorts ~/.claude/skills/`

## Requirements
- [Blender](https://www.blender.org/) 5.x (EEVEE renderer)
- [ffmpeg](https://ffmpeg.org/)
- [whisper.cpp](https://github.com/ggml-org/whisper.cpp) `whisper-cli`, with `ggml-base.en.bin` in
  `skills/blocky-horror-shorts/pipeline/models/` (or set `WHISPER_MODEL`)
- Python 3.10+: `pip install -r skills/blocky-horror-shorts/requirements.txt`
- Assets (~530 MB, CC0 from Poly Haven, downloaded once): `python3 skills/blocky-horror-shorts/engine/assets.py`
- A 10–20 s wav of a narrator voice **you own or have permission to clone**

Render time: EEVEE at 1440×2560 and 32 samples runs about 2.3 s per frame on an Apple M1 Max, so a 2-minute video
takes roughly 2.5 hours. `--preview` renders fast low-res checks.

## Example: "Still On"
`skills/blocky-horror-shorts/example/still-on/` holds a complete 1:56 story: the script, timeline, shared set and cast,
and all three part scenes. A town where porch lights must stay on, two kids who flash flashlights across the street at
midnight, and a twist. Run `voice.py` with your own voice to regenerate the narration, then `timeline.py`, and it
renders end to end.

## FAQ
**Can I use the videos on a monetized channel?** Yes. The stories are original, the assets are CC0 and the sound
effects are synthesized. The voice must be yours or licensed to you.

**Does it need a GPU or paid AI credits?** No paid credits. Any machine that runs Blender's EEVEE works. Apple Silicon,
NVIDIA and CPU all work, just at different speeds.

**Can I make other genres?** The engine is generic: blocky characters, sets, cameras and synced sound. The story
formula and example are horror. Swap the script and `shared.py` for anything else.

**Is this Roblox or Minecraft?** No. The blocky characters are original designs built from primitives in code.

## Repository layout
```
.claude-plugin/            plugin + marketplace manifests
skills/blocky-horror-shorts/
  SKILL.md                 the workflow Claude follows (with approval stops)
  references/              story formula, production rules, part-agent brief template
  engine/                  Blender helpers: characters, sets, materials, camera check, video QA, asset download
  pipeline/                voice.py (Chatterbox voice clone), finish.py (Whisper timing, SFX, loudness mix)
  example/still-on/        worked example story
```

## Contributing
Issues and pull requests are welcome: new sets, characters, faces, sound recipes, other genres.

License: MIT (see [LICENSE](LICENSE); third-party notes in [NOTICE.md](NOTICE.md)).
