"""Still On, PART 2 (lines 16-26): the countdown, Mrs. Hale, the storm.
Run: blender -b -P part2/scene.py -- --frames 10,200        (--preview for 30% size, --probe to print geometry checks)"""
import math, sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))  # the story folder
import shared as S          # noqa: E402
import characters as C      # noqa: E402
import bpy                  # noqa: E402
from mathutils import Vector  # noqa: E402
from common import box, color, light  # noqa: E402  (shared.py put engine/ on sys.path)

PZ = S.PORCH_Z
DOOR_FACE_Y = -10.91                 # outward face of a near-side door
SH_SCALE, SH_LEAN, SH_BOW = 1.0, math.radians(12), math.radians(44)   # the shade stoops under the porch roof
HIT = 58                             # shoulder angle (deg from hanging) of the knocking arm at contact
D = math.radians


# ------------------------------------------------------------------ small helpers ------------------------------------
def upd():
    bpy.context.view_layer.update()


def bbox(o):
    ws = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(w[i] for w in ws) for i in range(3)]), Vector([max(w[i] for w in ws) for i in range(3)])


def keys(obj, path, items):
    """items: (frame, value, interpolation, easing). Key each and set the curve type of that key (applies to the segment after it)."""
    for f, v, ip, ea in items:
        C.key(obj, path, f, v)
        for fc in C.fcurves(obj):
            if fc.data_path == path:
                for kp in fc.keyframe_points:
                    if kp.co.x == f:
                        kp.interpolation, kp.easing = ip, ea


def smooth(obj, path, items):
    keys(obj, path, [(f, v, "BEZIER", "AUTO") for f, v in items])


def aim(o, target):
    o.rotation_euler = (Vector(target) - o.location).to_track_quat("-Z", "Y").to_euler()


def fix_knob(h):
    """shared.porch_house parents the knob with a stale matrix, so it is NOT on the door: re-parent it at rest."""
    h["door"].rotation_euler.z = 0
    upd()
    h["knob"].parent = h["door"]
    h["knob"].matrix_parent_inverse = h["door"].matrix_world.inverted()


def prune(root, tail=None):
    """Hide weather flakes that would show inside houses (|y| > 10.9) or under a porch roof."""
    n = 0
    for o in root.children:
        x, y = o.location.x, o.location.y
        if abs(y) > 10.9 or (tail and tail(x, y)):
            o.hide_render = True
            n += 1
    return n


def wander(a, b, seed, base=(0.0, 0.0), amp=2.5, step=34):
    """Slow idle head movement (x tilt, z turn, degrees) as (frame, (x, z)) keys."""
    import random
    r = random.Random(seed)
    out, f = [], a
    while f < b:
        out.append((f, (D(base[0] + r.uniform(-amp, amp) * 0.6), D(base[1] + r.uniform(-amp, amp)))))
        f += step + r.randint(-8, 10)
    out.append((b, (D(base[0]), D(base[1]))))
    return out


def head(j, items):
    keys(j["neck"], "rotation_euler", [(f, (x, 0, z), "BEZIER", "AUTO") for f, (x, z) in items])


def sway(j, a, b, seed, amp=1.8, step=47):
    """Weight shift: the whole body turns a hair left/right so a standing character is never frozen."""
    import random
    r = random.Random(seed)
    base = j["root"].rotation_euler.z
    items, f = [], a
    while f < b:
        items.append((f, (0, 0, base + D(r.uniform(-amp, amp)))))
        f += step + r.randint(-10, 12)
    items.append((b, (0, 0, base)))
    smooth(j["root"], "rotation_euler", [(f, v) for f, v in items])


def talk_spans(p, line, tail=7, gap=5):
    """Mouth-flap spans from the spoken words of a line (my frames)."""
    fr = sorted(S.frame(t) - p.off for _, t in S.WORDS[line])
    end = p.shot(line)[3]
    out = []
    for f in fr:
        e = min(f + tail, end)
        if out and f - out[-1][1] <= gap:
            out[-1][1] = e
        else:
            out.append([f, e])
    return [tuple(x) for x in out]


def walker(j, pts, sps=3.2, amp=34, bounce=0.04, arm_free=("l", "r")):
    """Piecewise-linear route pts=[(frame,(x,y,z))] with leg/arm swing + body bob. Returns the footfall frames."""
    f0, f1 = pts[0][0], pts[-1][0]

    def pos(f):
        for (fa, pa), (fb, pb) in zip(pts, pts[1:]):
            if fa <= f <= fb:
                u = (f - fa) / max(1, fb - fa)
                return Vector(pa) * (1 - u) + Vector(pb) * u
        return Vector(pts[-1][1])

    half = 30 / sps / 2
    ff, t = [], float(f0)
    while t <= f1:
        ff.append(round(t))
        t += half
    for i, fr in enumerate(ff):
        sg = 1 if i % 2 == 0 else -1
        for sd, s2 in (("l", 1), ("r", -1)):
            C.key(j[f"{sd}_hip"], "rotation_euler", fr, (D(amp) * sg * s2, 0, 0))
            if sd in arm_free:
                C.key(j[f"{sd}_shoulder"], "rotation_euler", fr, (-D(amp) * sg * s2 * 0.8, 0, 0))
    root = j["root"]
    for fr in range(f0, f1 + 1, 2):
        q = pos(fr)
        ph = ((fr - f0) / half) % 1.0
        root.location = (q.x, q.y, q.z + bounce * math.sin(math.pi * ph))
        root.keyframe_insert("location", frame=fr)
    root.location = pos(f1)
    root.keyframe_insert("location", frame=f1)
    for fc in C.fcurves(root):
        if fc.data_path == "location":
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    for fc in C.fcurves(j["l_hip"]) + C.fcurves(j["r_hip"]):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
    return ff


def settle(j, f, dur=8, arms=("l", "r")):
    """Return legs (and the given arms) to neutral after a walk."""
    bpy.context.scene.frame_set(f)
    for sd in ("l", "r"):
        smooth(j[f"{sd}_hip"], "rotation_euler", [(f, tuple(j[f"{sd}_hip"].rotation_euler)), (f + dur, (0, 0, 0))])
    for sd in arms:
        smooth(j[f"{sd}_shoulder"], "rotation_euler", [(f, tuple(j[f"{sd}_shoulder"].rotation_euler)), (f + dur, (0, 0, 0))])


def shade_at(name, dx, hit=HIT):
    """The shade standing under a porch roof knocking: root placed numerically so the fingertips touch the door face."""
    j = S.char(name, "shade", (dx + 0.3, DOOR_FACE_Y + 1.5, PZ), 0.0)
    r = j["root"]
    r.scale = (SH_SCALE,) * 3
    r.rotation_euler.x = SH_LEAN
    j["neck"].rotation_euler.x = SH_BOW
    j["r_shoulder"].rotation_euler.x = -D(hit)
    hand = bpy.data.objects[f"{name}_r_hand"]
    for _ in range(4):
        upd()
        lo, hi = bbox(hand)
        r.location.y += DOOR_FACE_Y - lo.y
        r.location.x += (dx + 0.1) - (lo.x + hi.x) / 2
    upd()
    j["stance"] = r.location.copy()
    j["r_shoulder"].rotation_euler.x = 0
    return j


def knock(j, door, frames, a, hit=HIT, cock=38, rest=8):
    """Slow knocks: the arm lifts, then strikes so the fingertips touch the door ON each frame; the door shivers."""
    sh = j["r_shoulder"]
    items = [(a, (-D(rest), 0, 0), "BEZIER", "AUTO"), (frames[0] - 22, (-D(cock), 0, 0), "BEZIER", "AUTO")]
    for f in frames:
        items += [(f - 7, (-D(cock), 0, 0), "QUAD", "EASE_IN"), (f, (-D(hit), 0, 0), "QUAD", "EASE_OUT"),
                  (f + 5, (-D(cock + 2), 0, 0), "BEZIER", "AUTO")]
    keys(sh, "rotation_euler", items)
    d = []
    for f in frames:
        d += [(f - 1, (0, 0, 0)), (f, (0, 0, D(-0.7))), (f + 4, (0, 0, 0))]
    smooth(door, "rotation_euler", [(1, (0, 0, 0))] + d)


# ------------------------------------------------------------------ the scene ---------------------------------------
def make(s, p):
    st = S.street()
    Hs = st["houses"]
    nar, theo, hale = Hs["nar"], Hs["theo"], Hs["hale"]
    hx = hale["x"]
    fix_knob(nar)
    fix_knob(hale)
    S.apply_lights(st, p)
    S.time_of_day(p)
    ev, shot, word = p.ev, p.shot, p.word

    # ---- weather: gentle snow before the storm, rain from `thunder`; flakes never inside houses / under porch roofs
    def under_nar_roof(x, y):
        return -1.6 < x < 1.6 and -11.2 < y < -9.0
    snow = [S.snowfall("a", (0, 0, 4), (100, 36, 8), 1500, seed=1),
            S.snowfall("h", (hx, -7, 3), (14, 9, 6), 300, seed=3),
            S.snowfall("t", (0, 5.5, 3), (12, 8, 6), 300, seed=4)]
    rain = [S.rainfall("n", (0, -5.5, 4), (14, 11, 9), 900, seed=5),
            S.rainfall("s", (-2, 2, 4), (26, 12, 9), 400, seed=6)]
    S.weather(p, snow, rain)
    for r in snow:
        prune(r)
    for r in rain:
        prune(r, under_nar_roof)

    # ---- trees sway in the wind (hinged at their base; line 16 is "wind")
    for o in list(bpy.data.objects):
        if o.name.startswith(("trunk_", "leaf_", "leafsnow_")):
            parts = o.name.split("_")
            tx, ty = float(parts[1]), float(parts[2])
            S.hinged(o, (tx, ty, 0.0))
            ph = (tx * 7 + ty * 3) % 10
            amp = D(1.6)
            smooth(o, "rotation_euler", [(1 + k, (amp * math.sin(k * 0.11 + ph) * 0.7, amp * math.cos(k * 0.09 + ph) * 0.7, 0))
                                         for k in range(0, p.last + 90, 45)])

    # ---- the power cut also kills the diffuse glow of the lit-window material (else it still reads orange under my fills)
    win = bpy.data.materials.get("win_on_l")
    if win:
        bc = win.node_tree.nodes["Principled BSDF"].inputs["Base Color"]
        warm = tuple(bc.default_value)
        for f, c in ((1, warm), (ev("all_out"), (0.01, 0.012, 0.02, 1.0))):
            bc.default_value = c
            bc.keyframe_insert("default_value", frame=f)
        for fc in C.fcurves(win.node_tree):
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"

    # ---- helper lights (cool moon fill so dark porches still read; keyed to the beats, not to the lamp table)
    def spot(name, loc, tgt, energy, rgb, cone=50, size=0.6):
        o = light("SPOT", name, loc, energy, rgb, size=size, spot=(D(cone), 0.8))
        aim(o, tgt)
        return o

    def lit(o, items):
        for f, e in items:
            o.data.energy = e
            o.data.keyframe_insert("energy", frame=f)
        for fc in C.fcurves(o.data):
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"

    f_dark, f_hdoor, f_m = ev("hale_dark"), ev("hale_door"), shot(21)[0]
    # Hale's dark porch: cool fill from the street + a warm glow from the hall for her face
    hf = spot("hale_fill", (hx - 3, -4.5, 3.6), (hx, -10.2, 1.6), 420, (0.62, 0.74, 1.0), 40)
    lit(hf, [(1, 0), (f_dark, 420), (f_m, 0)])
    hw = spot("hale_warm", (hx + 1.6, -8.4, 2.4), (hx, -10.75, 1.7), 90, (1.0, 0.72, 0.45), 30, 0.4)
    lit(hw, [(1, 0), (f_hdoor + 6, 90), (f_m, 0)])
    # storm: cool fills around the narrator's porch after the power cut
    f_out = ev("all_out")
    nf = spot("nar_fill", (2.6, -6.0, 3.4), (0, -10.0, 1.4), 330, (0.62, 0.74, 1.0), 55)
    lit(nf, [(1, 0), (f_out, 330)])
    nf2 = spot("nar_fill2", (-3.2, -6.2, 3.0), (-0.2, -10.0, 1.2), 200, (0.55, 0.68, 1.0), 55)
    lit(nf2, [(1, 0), (f_out, 200)])

    # ---- Mrs. Hale's doorway (the shared house has solid brick behind the door): a dark hall panel, only where the door opens
    box("hale_hall", (1.0, 0.012, 2.1), (hx, -10.994, PZ + 1.05), color("hale_hall", (0.5, 0.3, 0.14), 0.9, emit=0.18), 0.0)

    # ================= shots 16-17: wind, the street going dark =================
    cams = {}
    a, b = shot(16)[:2]
    cams[16] = S.shot(s, "c16", a, b, (-9, -2.6, 1.7), (26, 0.4, 2.6), 24, move=(0.5, 0, 0.05), push=0.06)
    a, b = shot(17)[:2]
    cams[17] = S.shot(s, "c17", a, b, (54, -0.8, 9.0), (8, 0.3, -3.0), 24, move=(-0.4, 0, -0.8), push=0.05)

    # ================= shot 18-19: Mrs. Hale's porch dies, the shade knocks =================
    a, b = shot(18)[:2]
    cams[18] = S.shot(s, "c18", a, b, (-12.6, -5.4, 1.9), (-9.7, -10.3, 1.8), 36, move=(0.3, -0.25, 0), push=0.10)

    sh1 = shade_at("SHADE_H", hx)
    a, b = shot(19)[:2]
    S.visible(sh1, 1, False)
    S.visible(sh1, a, True)
    S.visible(sh1, shot(20)[0], False)
    C.faces_over(sh1, a, b, "thing")
    C.breathe(sh1, a, b, period=2.6, amount=0.012)
    knocks = [ev("hale_knock1"), ev("hale_knock2"), ev("hale_knock3")]
    knock(sh1, hale["door"], knocks, a)
    head(sh1, [(a, (SH_BOW, 0)), (knocks[2] + 4, (SH_BOW, 0)), (knocks[2] + 18, (SH_BOW * 0.7, D(14)))])
    cams[19] = S.shot(s, "c19", a, b, (-7.9, -5.2, 1.5), (-9.9, -10.0, 1.7), 40, move=(-0.2, -0.2, 0.05), push=0.06)

    # ================= shot 20: the door opens, Mrs. Hale =================
    a, b = shot(20)[:2]
    hd = ev("hale_door")
    smooth(hale["door"], "rotation_euler", [(hd - 1, (0, 0, 0)), (hd + 1, (0, 0, 0)), (hd + 24, (0, 0, D(100)))])
    hj = S.char("HALE", "hale", (hx, -11.3, PZ), math.pi)
    S.visible(hj, 1, False)
    S.visible(hj, a, True)
    S.visible(hj, shot(21)[0], False)
    C.faces_over(hj, a, shot(21)[0] - 1, "mom", seed=3)
    C.breathe(hj, a, shot(21)[0] - 1, period=2.0, amount=0.016)
    falls = C.walk_bounce(hj, hd + 9, hd + 27, (hx, -11.3, PZ), (hx, -10.7, PZ), steps_per_sec=1.7, bounce=0.012)
    settle(hj, hd + 27)
    for f in falls:
        p.foley(f, "step", 0.14)
    head(hj, wander(hd + 28, shot(21)[0] - 1, 7, base=(-2, 0), amp=2.0))
    cams[20] = S.shot(s, "c20", a, b, (-8.7, -8.7, 1.85), (-10.0, -10.7, 1.75), 45, move=(-0.15, -0.1, 0), push=0.08)

    # ================= shot 21: morning, the slippers =================
    a, b = shot(21)[:2]
    sl = S.slippers("SLIPPERS", (0, 0, 0))      # built at the origin (shared helper mis-places children otherwise), then moved
    sl.location = hale["mat_spot"]
    sl.rotation_euler.z = D(8)
    S.visible(sl, 1, False)
    S.visible(sl, a, True)
    cams[21] = S.shot(s, "c21", a, b, (-10.9, -9.0, 0.95), (-10.0, -10.5, 0.62), 40, move=(0.2, -0.1, -0.05), push=0.12)

    # ================= shot 22: Theo at his steps =================
    a, b, sp0, sp1 = shot(22)
    t1 = S.char("THEO_G", "theo", (0.0, 7.5, 0.0), 0.0, face="kid_sad_smile")
    S.visible(t1, 1, False)
    S.visible(t1, a, True)
    S.visible(t1, shot(23)[0], False)
    C.faces_over(t1, a, b, "kid_sad_smile", talk=talk_spans(p, 22), seed=5)
    C.breathe(t1, a, b)
    head(t1, wander(a, b, 11, base=(-8, 4), amp=2.2, step=30))   # eyes up on the narrator's porch light
    sway(t1, a, b, 4)
    cams[22] = S.shot(s, "c22", a, b, (-1.6, 5.2, 1.3), (0.0, 7.5, 0.85), 46, move=(0.2, 0.1, 0), push=0.08)

    # ================= shot 23: the storm; Theo runs in =================
    a, b = shot(23)[:2]
    t2 = S.char("THEO", "theo", (0.15, -1.5, 0.0), 0.0, face="kid_scared")
    fl = S.flashlight("FL")
    fl["root"].parent = t2["r_shoulder"]
    fl["root"].location = (0, -0.06, -0.57)
    fl["root"].rotation_euler = (D(90), 0, 0)               # beam along the arm
    S.flash(fl, 1, False)
    f_on = f_out + 5
    S.flash(fl, f_on, True)
    run0 = f_out - 40
    S.visible(t2, 1, False)
    S.visible(t2, run0, True)
    S.visible(fl["root"], 1, False)
    S.visible(fl["root"], run0, True)
    C.faces_over(t2, run0, p.last, "kid_scared", seed=8)
    C.breathe(t2, run0, p.last)
    stand = (-0.7, -10.1, PZ)
    arrive = shot(24)[0] + 3
    route = [(run0, (0.15, -1.5, 0.0)), (f_out + 24, (0.05, -8.0, 0.0)), (f_out + 29, (0.0, -8.45, 0.167)),
             (f_out + 34, (0.0, -8.75, 0.333)), (f_out + 38, (0.0, -9.05, 0.5)), (arrive, stand)]
    falls = walker(t2, route, sps=3.4, amp=34, bounce=0.05, arm_free=("l",))
    for f in falls:
        if f >= f_out - 12:
            p.foley(f, "step", 0.3)
    r_arm = t2["r_shoulder"]
    keys(r_arm, "rotation_euler", [(run0, (-D(70), 0, 0), "BEZIER", "AUTO"), (arrive, (-D(70), 0, 0), "BEZIER", "AUTO"),
                                   (arrive + 14, (-D(94), 0, 0), "BEZIER", "AUTO")])
    # body turns to face the door centre as he reaches the porch
    smooth(t2["root"], "rotation_euler", [(run0, (0, 0, 0)), (f_out + 38, (0, 0, 0)), (arrive + 10, (0, 0, D(41)))])
    settle(t2, arrive, 10, arms=("l",))
    head(t2, [(run0, (D(-6), 0)), (arrive + 6, (D(-6), 0)),
              (arrive + 24, (D(-3), D(50))), (shot(25)[0] + 22, (D(-3), D(52))),
              (shot(25)[0] + 40, (D(-6), D(6))), (shot(26)[0] + 2, (D(-6), D(6))), (shot(26)[0] + 20, (D(-4), D(95))),
              (b + 400, (D(-4), D(95)))])
    cams[23] = S.shot(s, "c23", a, b, (-2.6, -9.9, 1.5), (8.0, -9.9, 1.9), 24, move=(0.4, 0, 0), push=0.05)

    # ================= shot 24: Theo on the porch =================
    a, b = shot(24)[:2]
    cams[24] = S.shot(s, "c24", a, b, (2.0, -7.0, 1.45), (-0.4, -10.3, 1.5), 32, move=(-0.2, 0, 0), push=0.06)

    # ================= shot 25: the shade climbs (feet on step1/2/3 exactly) =================
    a, b = shot(25)[:2]
    s1, s2, s3 = ev("step1"), ev("step2"), ev("step3")
    sh2 = shade_at("SHADE_N", 0.0)
    stance = sh2["stance"]
    r = sh2["root"]
    S.visible(sh2, 1, False)
    S.visible(sh2, a - 2, True)
    C.faces_over(sh2, a - 2, p.last, "thing")
    C.breathe(sh2, a - 2, p.last, period=2.6, amount=0.012)
    steps = nar["step_spots"]
    amp = D(26)
    # contacts: (frame, leading leg, foot y, foot z)
    contacts = [(s1 - 24, "r", -7.55, 0.0), (s1 - 12, "l", -8.05, 0.0), (s1, "r", steps[0][1], steps[0][2]),
                (s2, "l", steps[1][1], steps[1][2]), (s3, "r", steps[2][1], steps[2][2])]
    for sd in ("l", "r"):
        C.key(sh2[f"{sd}_hip"], "rotation_euler", a - 2, (0, 0, 0))
        C.key(sh2[f"{sd}_shoulder"], "rotation_euler", a - 2, (0, 0, 0))
    for f, lead, fy, fz in contacts:
        for sd in ("l", "r"):
            lead_leg = sd == lead
            C.key(sh2[f"{sd}_hip"], "rotation_euler", f, (-amp if lead_leg else amp * 0.7, 0, 0))
            C.key(sh2[f"{sd}_shoulder"], "rotation_euler", f, (D(14) if lead_leg else -D(12), 0, 0))
    # root route: stand at y=-6.7, walk the contacts, then the last stride onto the deck at the knock stance
    r.location = (stance.x - 0.3, -6.7, 0.0)
    r.keyframe_insert("location", frame=a - 2)
    for f, lead, fy, fz in contacts:
        shoe = bpy.data.objects[f"SHADE_N_{lead}_shoe"]
        for _ in range(4):                       # place the leading shoe exactly on its target at the contact frame
            s.frame_set(f)
            lo, hi = bbox(shoe)
            r.location.y += fy - (lo.y + hi.y) / 2
            r.location.z += fz - lo.z
            r.location.x = stance.x
            r.keyframe_insert("location", frame=f)
    f_end = s3 + 13
    r.location = stance
    r.keyframe_insert("location", frame=f_end)
    for fc in C.fcurves(r):
        if fc.data_path == "location":
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    for k in range(len(contacts) - 1):          # body lifts a hair between footfalls
        f0, f1 = contacts[k][0], contacts[k + 1][0]
        s.frame_set((f0 + f1) // 2)
        z = r.location.z
        r.location.z = z + 0.05
        r.keyframe_insert("location", index=2, frame=(f0 + f1) // 2)
    for sd in ("l", "r"):                       # last stride: legs come together, arm starts to rise
        smooth(sh2[f"{sd}_hip"], "rotation_euler", [(s3 + 1, (-amp if sd == "r" else amp * 0.7, 0, 0)), (f_end + 6, (0, 0, 0))])
        smooth(sh2[f"{sd}_shoulder"], "rotation_euler", [(s3 + 1, (D(14) if sd == "r" else -D(12), 0, 0)), (f_end + 6, (0, 0, 0))])
    head(sh2, [(a - 2, (SH_BOW, 0)), (f_end + 40, (SH_BOW, 0))])
    cams[25] = S.shot(s, "c25", a, b, (3.1, -6.0, 0.4), (0.1, -9.2, 1.4), 26, move=(-0.2, -0.1, 0.05), push=0.05)

    # ================= shot 26: the shade knocks at the door, Theo frozen =================
    a, b = shot(26)[:2]
    kn = [ev("thing_knock1"), ev("thing_knock2"), ev("thing_knock3")]
    keys(sh2["r_shoulder"], "rotation_euler", [(f_end + 6, (0, 0, 0), "BEZIER", "AUTO"), (kn[0] - 22, (-D(38), 0, 0), "BEZIER", "AUTO")])
    items = []
    for f in kn:
        items += [(f - 7, (-D(38), 0, 0), "QUAD", "EASE_IN"), (f, (-D(HIT), 0, 0), "QUAD", "EASE_OUT"), (f + 5, (-D(40), 0, 0), "BEZIER", "AUTO")]
    keys(sh2["r_shoulder"], "rotation_euler", items)
    smooth(nar["door"], "rotation_euler", [(1, (0, 0, 0))] + sum([[(f - 1, (0, 0, 0)), (f, (0, 0, D(-0.7))), (f + 4, (0, 0, 0))] for f in kn], []))
    # Theo trembles, light steady on the door
    trem = []
    for f in range(shot(26)[0], b, 4):
        trem.append((f, (D(2.5 if (f // 4) % 2 else -2.5), 0, 0)))
    smooth(t2["l_shoulder"], "rotation_euler", [(shot(26)[0] - 1, (0, 0, 0))] + trem)
    cams[26] = S.shot(s, "c26", a, b, (-0.3, -6.2, 1.5), (-0.1, -10.2, 1.55), 28, move=(0.15, 0, 0), push=0.08)

    S.finish(s, p)
    return dict(cams=cams, nar=nar, hale=hale, sh1=sh1, sh2=sh2, hj=hj, t1=t1, t2=t2, hs=Hs, knocks=knocks, kn=kn, st=st)


# ------------------------------------------------------------------ probe (own flag) --------------------------------
def probe(s, p, ctx):
    from bpy_extras.object_utils import world_to_camera_view as w2c
    cams, Hs = ctx["cams"], ctx["hs"]

    def uv(cam, pt):
        v = w2c(s, cam, Vector(pt))
        return f"({v.x:.2f},{v.y:.2f},{'+' if v.z > 0 else '-'})"
    def ctr(name):
        lo, hi = bbox(bpy.data.objects[name])
        return (lo + hi) / 2
    lamps = {n: bbox(h["lamp"])[0] + (bbox(h["lamp"])[1] - bbox(h["lamp"])[0]) / 2 for n, h in Hs.items() if "lamp" in h}
    for line, cam in cams.items():
        a, b = p.shot(line)[:2]
        for f in (a, (a + b) // 2, b):
            s.frame_set(f)
            if line in (16, 17):
                pts = {n: lamps[n] for n in ("n30", "f30", "f20", "n20", "f-20", "n-20", "f10") if n in lamps}
            elif line in (18, 19, 20, 21):
                pts = dict(lamp=lamps["hale"], door=(-10, -10.9, 1.6), slip=(-10, -10.55, 0.55), hale=ctr("HALE_head"), shade=ctr("SHADE_H_head"))
            elif line == 22:
                pts = dict(head=ctr("THEO_G_head"), feet=(0, 7.5, 0))
            elif line == 23:
                pts = dict(lamp=lamps["nar"], steps=(0, -8.7, 0.3), theo=ctr("THEO_head"))
            else:
                pts = dict(door=(0, -10.9, 1.6), theo=ctr("THEO_head"),
                           shade=ctr("SHADE_N_head"))
            print(f"P2 shot{line} f{f}: " + " ".join(f"{k}={uv(cam, v)}" for k, v in pts.items()), flush=True)
    roof = bbox(bpy.data.objects["nar_porchroof"])
    for nm in ("SHADE_H", "SHADE_N"):
        for f in (p.ev("hale_knock1"), p.ev("thing_knock1")):
            s.frame_set(f)
            hd = bbox(bpy.data.objects[f"{nm}_head"])
            hr = bbox(bpy.data.objects[f"{nm}_hair"]) if f"{nm}_hair" in bpy.data.objects else None
            print(f"P2 {nm} f{f} head max z {hd[1].z:.3f} (roof bottom {roof[0].z:.3f}) head y {hd[0].y:.2f}..{hd[1].y:.2f}", flush=True)
    for f, nm, hn in ((ctx["knocks"][0], "SHADE_H", "r"), (ctx["knocks"][1], "SHADE_H", "r"), (ctx["knocks"][2], "SHADE_H", "r"),
                      (ctx["kn"][0], "SHADE_N", "r"), (ctx["kn"][1], "SHADE_N", "r"), (ctx["kn"][2], "SHADE_N", "r"),
                      (ctx["knocks"][0] - 8, "SHADE_H", "r"), (ctx["kn"][0] - 8, "SHADE_N", "r")):
        s.frame_set(f)
        lo, hi = bbox(bpy.data.objects[f"{nm}_{hn}_hand"])
        print(f"P2 knock f{f} {nm} hand min y {lo.y:.3f} (door face {DOOR_FACE_Y}) x {lo.x:.2f}..{hi.x:.2f} z {lo.z:.2f}..{hi.z:.2f}", flush=True)
    for f, sd, step in ((p.ev("step1"), "r", 0.167), (p.ev("step2"), "l", 0.333), (p.ev("step3"), "r", 0.5)):
        s.frame_set(f)
        lo, hi = bbox(bpy.data.objects[f"SHADE_N_{sd}_shoe"])
        print(f"P2 step f{f} {sd} shoe z {lo.z:.3f} (step top {step}) y {lo.y:.2f}..{hi.y:.2f}", flush=True)
    s.frame_set(p.ev("hale_door") + 30)
    print("P2 hale door angle", math.degrees(ctx["hale"]["door"].rotation_euler.z), flush=True)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    s = S.reset(32)
    p = S.Part(2)
    ctx = make(s, p)
    if "--probe" in args:
        probe(s, p, ctx)
    else:
        S.render(s, p, args)
