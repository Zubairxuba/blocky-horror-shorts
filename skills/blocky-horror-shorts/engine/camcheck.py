"""Camera motion QA: blender -b -P camcheck.py -- <scene.py> <part_dir> [out.json]
Builds the scene (no render), walks every frame, reports per-shot camera speed/turn rate and flags
jerks (sudden speed changes), whips (fast turns) and jump cuts (next shot nearly the same angle)."""
import json, math, runpy, sys
from pathlib import Path
import bpy

args = sys.argv[sys.argv.index("--") + 1:]
scene_py, d = Path(args[0]), Path(args[1])
out = Path(args[2]) if len(args) > 2 else d / "camcheck.json"
sys.argv = [sys.argv[0]]  # keep the scene's own argv parsing quiet
mod = runpy.run_path(str(scene_py), run_name="camcheck")
if "make" in mod:  # Still On interface: make(s, part) builds + animates everything; part dir is partN
    S = mod["S"]
    part = S.Part(int(d.name.replace("part", "")))
    s = S.reset(8)
    mod["make"](s, part)
    last = part.last
else:
    shots = json.loads((d / "shots.json").read_text())
    import inspect
    anim = mod["animate"]
    s = mod["S"].reset(32)
    if len(inspect.signature(anim).parameters) == 3:
        anim(s, mod["build"](), shots)
    else:
        anim(s, shots)
    last = round(shots[-1]["end"] * 30)
s = bpy.context.scene
FPS = 30
marks = sorted((m.frame, m.camera) for m in s.timeline_markers if m.camera)

def cam_at(f):
    c = None
    for fr, cam in marks:
        if fr <= f:
            c = cam
    return c

rows = []
for f in range(1, last + 1):
    s.frame_set(f)
    c = cam_at(f)
    m = c.matrix_world
    fwd = (m.to_3x3() @ __import__("mathutils").Vector((0, 0, -1))).normalized()
    rows.append((f, c.name, m.translation.copy(), fwd, c.data.lens))

flags, per = [], {}
for i in range(1, len(rows)):
    f, name, p, v, lens = rows[i]
    _, pn, pp, pv, plens = rows[i - 1]
    if name != pn:
        ang = math.degrees(pv.angle(v))
        dist = (p - pp).length
        if ang < 1 and dist < 0.05 and abs(lens - plens) / plens < 0.03:
            continue  # seamless continuation
        if ang < 20 and dist < 1.0 and abs(lens - plens) / plens < 0.3:
            flags.append(dict(frame=f, kind="jump_cut", detail=f"{pn}->{name}: {ang:.0f} deg, {dist:.2f} m"))
        continue
    spd = (p - pp).length * FPS
    turn = math.degrees(pv.angle(v)) * FPS
    zoom = abs(lens - plens) / plens * FPS
    st = per.setdefault(name, dict(first=f - 1, spd=[], turn=[], zoom=[]))
    st["spd"].append(spd); st["turn"].append(turn); st["zoom"].append(zoom); st["last"] = f
for name, st in per.items():
    sp, tu = st["spd"], st["turn"]
    for k in range(1, len(sp)):
        f = st["first"] + k + 1
        if abs(sp[k] - sp[k - 1]) > 0.25 and max(sp[k], sp[k - 1]) > 0.3:
            flags.append(dict(frame=f, kind="speed_jerk", detail=f"{name}: {sp[k-1]:.2f}->{sp[k]:.2f} m/s"))
        if abs(tu[k] - tu[k - 1]) > 6:
            flags.append(dict(frame=f, kind="turn_jerk", detail=f"{name}: {tu[k-1]:.1f}->{tu[k]:.1f} deg/s"))
    if max(sp) > 1.2:
        flags.append(dict(frame=st["first"], kind="too_fast", detail=f"{name}: max {max(sp):.2f} m/s"))
    if max(tu) > 15:
        flags.append(dict(frame=st["first"], kind="whip", detail=f"{name}: max turn {max(tu):.1f} deg/s"))
summary = {n: dict(frames=f"{st['first']}-{st['last']}", max_mps=round(max(st['spd']), 2),
                   max_turn=round(max(st['turn']), 1)) for n, st in per.items()}
flags.sort(key=lambda x: x["frame"])
out.write_text(json.dumps(dict(summary=summary, flags=flags), indent=1))
print("CAMCHECK", len(flags), "flags ->", out)
