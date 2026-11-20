# Production rules (each one came from a real mistake)

## Sync: one clock for picture and sound
- `timeline.py` is the only place time is decided. Each beat in `events.json` is a frame number; a scene keys its
  visual ON `p.ev("id")` and `assemble.py` plays the sound at `(frame-1)/30`. Neither side times anything alone.
- Times come only from word timings or line ends, never from hand-typed seconds.
- Footsteps: scenes call `p.foley(frame, "step", gain)` on each on-screen footfall (from `C.walk_bounce`); the lead mixes them.
- Audio is mixed centrally with one fixed gain to about -14 LUFS. Effects and the drone duck under the voice; nothing
  dynamic touches the voice itself (a normaliser on the whole mix made the voice pump).

## Sound coverage
- Every visible impact, knock, horn, call, door, flash or fall is an event with a sound. The final report lists any
  on-screen action still without one.
- Attention SFX: a bass drop on frame 1 and booms/risers on the key beats, all through `events.json`.

## Music (optional; many creators add it in their editor)
- Original only: `score.py` synthesizes it (no samples, no loops, nothing to copyright-claim).
- It sits about 9 dB down and is side-chain ducked under the voice; one fixed gain on the whole mix afterwards.
- Silence is the scariest sound: cut the music on the scare event and before knocks, then hit on the reveal line.

## Camera
- Only `S.shot(...)` / `S.continue_shot(...)`: one smooth eased move per shot, capped speed, turn and zoom
  (`MAX_SPEED`, `MAX_TURN`, `MAX_ZOOM` in shared.py). No sudden speed changes, no flips.
- Every shot moves a little (push, drift or small orbit). Nothing is static.
- 30-degree rule: consecutive shots of the same subject change angle >= 30 deg or size clearly, unless continued.
  180-degree rule: don't jump to the other side of the action.
- Never inside or right against geometry (`S.check_cameras`, `camcheck.py`). No props within 1.5 m of the lens;
  clear falling snow/rain near cameras.
- Lens 24-60 mm (85 max for tiny props).

## Cinematic look (every new video)
- Real photographed sky: `look.sky(kind, strength, rotate)` replaces the plain dark world and also lights the scene.
- Real trees and shrubs: `look.tree(name, loc, rot_z, scale)`. It decimates the heavy model ONCE and shares the mesh;
  never leave a DECIMATE modifier live (it made renders ~15x slower).
- Depth of field on every shot (`look.dof` in `S.shot`; f/2-2.8 close-ups, f/4.5 wides), rim light on every character
  (`look.rim`), detailed clothes (`detail=True` looks: soles, cuffs, belt, hoodie pocket and strings, fringe), and the
  post-grade at the mux (`look.post_filter`: glow, colour grade, vignette, grain).
- Do NOT put a world-wide haze volume (`look.haze`) on outdoor scenes: it dropped street brightness from 86 to 13.
  Use it only for interiors or small sets.
- Bright looks work very well: pale fog from the compositor Mist pass mixed to a fog colour, plus emissive "fog card"
  planes drifting between the layers, over pastel sets. A world volume renders black for this; don't use one.
  Improve the look with every video; don't slide back to plain dark navy.

## Picture
- Vertical 1440x2560, 30 fps. Subject big and readable on a phone.
- Faces readable: light them (practical lamp + a small soft AREA fill). Only the monster may be a black silhouette.
- Every visible character breathes and blinks (`C.breathe`, `C.faces_over`); mouths flap only inside spoken spans.
- `hide_render` does not pass to children: use `S.visible(j, frame, on)` for whole characters.
- Eased (BEZIER) keys for body moves; CONSTANT only for flicker and snaps.
- Everything visible looks finished: nothing floating, nothing inside walls.
- No captions by default. If captions are wanted, put them lower-third (~65% down), never mid-screen.

## Process
- The script is the only approval. After it, the lead runs everything to delivery without stopping.
- Test renders only while building: <= ~40 frames per agent, each Blender call under 9 minutes.
- An Opus reviewer agent checks all three parts (camcheck, contact sheets, twist rule, sync, visual detail, sound
  coverage) before the final render; the lead fixes what it finds.
- Full renders run in the background; never block on them.
- Part agents run on a smaller model (sonnet), read each file once and grep Blender output: they used too many
  tokens otherwise. The lead keeps the shared base and the review.
