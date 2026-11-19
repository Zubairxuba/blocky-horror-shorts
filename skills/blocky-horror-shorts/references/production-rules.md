# Production rules (each one came from a real mistake)

## Sync: one clock for picture and sound
- `timeline.py` is the only place time is decided. Each beat in `events.json` is a frame number; a scene keys its
  visual ON `p.ev("id")` and `assemble.py` plays the sound at `(frame-1)/30`. Neither side times anything alone.
- Times come only from word timings or line ends, never from hand-typed seconds.
- Footsteps: scenes call `p.foley(frame, "step", gain)` on each on-screen footfall (from `C.walk_bounce`); the lead mixes them.
- Audio is mixed centrally with one fixed gain to about -14 LUFS. Effects and the drone duck under the voice; nothing
  dynamic touches the voice itself (a normaliser on the whole mix made the voice pump).

## Camera
- Only `S.shot(...)` / `S.continue_shot(...)`: one smooth eased move per shot, capped speed, turn and zoom
  (`MAX_SPEED`, `MAX_TURN`, `MAX_ZOOM` in shared.py). No sudden speed changes, no flips.
- Every shot moves a little (push, drift or small orbit). Nothing is static.
- 30-degree rule: consecutive shots of the same subject change angle >= 30 deg or size clearly, unless continued.
  180-degree rule: don't jump to the other side of the action.
- Never inside or right against geometry (`S.check_cameras`, `camcheck.py`). No props within 1.5 m of the lens;
  clear falling snow/rain near cameras.
- Lens 24-60 mm (85 max for tiny props).

## Picture
- Vertical 1440x2560, 30 fps. Subject big and readable on a phone.
- Faces readable: light them (practical lamp + a small soft AREA fill). Only the monster may be a black silhouette.
- Every visible character breathes and blinks (`C.breathe`, `C.faces_over`); mouths flap only inside spoken spans.
- `hide_render` does not pass to children: use `S.visible(j, frame, on)` for whole characters.
- Eased (BEZIER) keys for body moves; CONSTANT only for flicker and snaps.
- Everything visible looks finished: nothing floating, nothing inside walls.
- No captions by default. If captions are wanted, put them lower-third (~65% down), never mid-screen.

## Process
- Test renders only while building: <= ~40 frames per agent, each Blender call under 9 minutes.
- Full renders run in the background; never block on them.
- A low-res motion preview of the WHOLE video with final audio is approved before the full render.
- Part agents run on a smaller model (sonnet), read each file once and grep Blender output: they used too many
  tokens otherwise. The lead keeps the shared base and the review.
