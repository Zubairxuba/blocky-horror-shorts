"""Still On, PART 1 (lines 1-15): the rule, the light buddies, the clues. Run:
blender -b -P scene.py -- --frames 10,200   (add --preview for 30% size)"""
import math, random, sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))  # the story folder
import shared as S          # noqa: E402
import characters as C      # noqa: E402
import bpy                  # noqa: E402
from common import box, color, empty, light  # noqa: E402

R = math.radians


# ------------------------------------------------------------------ small helpers
def put(j, a, b):
    """Character/prop visible only in frames a..b (call BEFORE faces_over)."""
    S.visible(j, 1, False)
    S.visible(j, a, True)
    S.visible(j, b + 1, False)


def arm(j, side, f, x, y=0.0, z=0.0):
    C.key(j[f"{side}_shoulder"], "rotation_euler", f, (R(x), R(y), R(z)))


def head(j, f, yaw=0.0, pitch=0.0):
    """Full-tuple neck key. pitch + = down, - = up."""
    C.key(j["neck"], "rotation_euler", f, (R(pitch), 0, R(yaw)))


def gaze(j, f, rot_z, pos, tgt, cap=70):
    """Head toward a world point (yaw limited to +-cap deg, pitch up/down limited to 40)."""
    dx, dy, dz = tgt[0] - pos[0], tgt[1] - pos[1], tgt[2] - pos[2]
    psi = math.atan2(dx, -dy)
    yaw = math.degrees((psi - rot_z + math.pi) % (2 * math.pi) - math.pi)
    pitch = -math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    head(j, f, max(-cap, min(cap, yaw)), max(-40, min(40, pitch)))


def idle(j, a, b, seed, yaw=0.0, pitch=0.0, rz=0.0, pos=None, tgt=None, amp=2.0):
    """Tiny head drift every ~1.2 s around a pose so nothing is frozen (set pos/tgt to aim at a point)."""
    rnd = random.Random(seed)
    f = a
    while f <= b:
        dy, dp = rnd.uniform(-amp, amp), rnd.uniform(-amp * 0.6, amp * 0.6)
        if tgt:
            dx_, dy_, dz_ = tgt[0] - pos[0], tgt[1] - pos[1], tgt[2] - pos[2]
            yaw = math.degrees((math.atan2(dx_, -dy_) - rz + math.pi) % (2 * math.pi) - math.pi)
            pitch = -math.degrees(math.atan2(dz_, math.hypot(dx_, dy_)))
            yaw, pitch = max(-70, min(70, yaw)), max(-40, min(40, pitch))
        head(j, f, yaw + dy, pitch + dp)
        f += rnd.randint(30, 45)


def keyed_visible(obj, a, b):
    S.visible(obj, 1, False)
    S.visible(obj, a, True)
    S.visible(obj, b + 1, False)


def fill(name, loc, energy, a, b, rgb=(1.0, 0.85, 0.65), size=0.5, kind="POINT"):
    """A soft face fill that is on only in frames a..b."""
    o = light(kind, name, loc, 0, rgb, size=size) if kind == "POINT" else light(kind, name, loc, 0, rgb, size=size)
    d = o.data
    for f, e in ((1, 0), (a, energy), (b + 1, 0)):
        d.energy = e
        d.keyframe_insert("energy", frame=f)
    S._const(d)
    return o


def fl_arm(j, fl, side, f, ang):
    """Raise the flashlight arm to ang deg (-90 = straight forward). The flashlight counter-rotates so it always
    points straight ahead of the body."""
    arm(j, side, f, ang)
    C.key(fl["root"], "rotation_euler", f, (R(-ang), 0, 0))


def hold_fl(j, name, side):
    """Flashlight in the hand of `side` shoulder, plus a glow cube so a flash reads from across the street."""
    fl = S.flashlight(name)
    fl["root"].parent = j[f"{side}_shoulder"]
    fl["root"].location = (0, 0, -0.62 * 0.875 - 0.07)
    fl["root"].scale = (1.35, 1.35, 1.35)
    fl["beam"].rotation_euler = (R(-90), 0, 0)  # shared.flashlight() aims its spot at +Y (backwards); lens faces -Y
    gm = color(f"{name}_glow", (1.0, 0.95, 0.8), 0.2, emit=0.001)
    fl["glowbox"] = box(f"{name}_glowbox", (0.2, 0.2, 0.2), (0, -0.16, 0), gm, 0.0, fl["root"])
    fl["glow"] = gm
    C.key(fl["glowbox"], "scale", 1, (0.001, 0.001, 0.001))  # a solid cube when idle would show: scaled away
    S.constant(fl["glowbox"])
    S.flash(fl, 1, False)
    S._emit(gm, 1, 0.0)
    C.key(fl["root"], "rotation_euler", 1, (0, 0, 0))
    return fl


def flash2(fl, f, on):
    S.flash(fl, f, on)
    S._emit(fl["glow"], f, 60.0 if on else 0.0)
    k = 1.0 if on else 0.001
    C.key(fl["glowbox"], "scale", f, (k, k, k))
    S.constant(fl["glowbox"])


def double_flash(fl, e1, e2, dur=6):
    for e in (e1, e2):
        flash2(fl, e, True)
        flash2(fl, e + dur, False)


def wave(j, side, a, b, base=-150, amp=24, per=10):
    arm(j, side, max(1, a - 14), 0)
    arm(j, side, a, base, 0)
    f, n = a, 0
    while f < b:
        f = min(f + per // 2, b)
        n += 1
        arm(j, side, f, base, amp if n % 2 else -amp)


def stride(j, plants, foley=0.0, p=None):
    """Footfalls for a tall walker: plants = [(frame, (x, y, z))]. Root moves linearly between plants, legs swing
    on each plant, arms counter-swing."""
    root = j["root"]
    lead = 1
    for k, (f, pt) in enumerate(plants):
        C.key(root, "location", f, pt)
        a = 22 * lead
        arm_s = 8 * lead
        for s, sg in (("l", 1), ("r", -1)):
            C.key(j[f"{s}_hip"], "rotation_euler", f, (R(-a * sg), 0, 0))
            C.key(j[f"{s}_shoulder"], "rotation_euler", f, (R(arm_s * sg), 0, 0))
        lead = -lead
        if foley and p:
            p.foley(f, "step", foley)
    C.linear(root)


def gust(name, x, y0, y1, z0, z1, a, b, n=70, seed=3, period=34, spread=1.3):
    """Wind-blown flakes that stream toward the doorway (y0 -> y1) and vanish into it. Visible only a..b."""
    rnd = random.Random(seed)
    mat = color("gust_flake", (1, 1, 1), 0.5, emit=0.6)
    root = empty(name, (0, 0, 0))
    for k in range(n):
        bx = bpy.data.objects.new(f"{name}_{k}", bpy.data.meshes.new(f"{name}_m{k}"))
        me = bx.data
        r = 0.018 * rnd.uniform(0.7, 1.4)
        v = [(sx * r, sy * r, sz * r) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
        me.from_pydata(v, [], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
        me.materials.append(mat)
        bpy.context.collection.objects.link(bx)
        bx.parent = root
        bx.visible_shadow = False
        sx0 = x + rnd.uniform(-spread, spread)
        sz0 = rnd.uniform(z0, z1)
        per = period * rnd.uniform(0.8, 1.3)
        off = rnd.random() * per
        for t, (px, py, pz) in ((0, (sx0 + rnd.uniform(-.6, .6), y0 + rnd.uniform(0, 1.5), sz0 + rnd.uniform(0, .7))),
                                (per, (sx0 * 0.2 + x * 0.8, y1, sz0 - rnd.uniform(0, .5)))):
            bx.location = (px, py, pz)
            bx.keyframe_insert("location", frame=a - off + t)
        for fc in C.fcurves(bx):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
            fc.modifiers.new("CYCLES")
    S.visible(root, 1, False)
    S.visible(root, a, True)
    S.visible(root, b + 1, False)
    return root


def stool(name, x, y, side, w=0.8):
    """A low wooden toy chest under the window so a kid's face reaches the glass."""
    box(name, (w, 0.5, 0.3), (x, y, 0.15), color("toychest", (0.5, 0.33, 0.2), 0.6), 0.02)


def blink_seed(k):
    return k * 7 + 3


# ------------------------------------------------------------------ the scene
def make(s, p):
    st = S.street()
    H = st["houses"]
    nar, theo = H["nar"], H["theo"]
    rule = S.porch_house("rule", 60, -1, lit=(False, False))
    din = S.dining()
    cls = S.classroom()
    S.apply_lights(st, p)
    S.time_of_day(p)
    sh = {n: p.shot(n) for n in range(1, 16)}

    snows = [S.snowfall("main", (0, 0, 3.5), (70, 30, 7), 2400, seed=1),
             S.snowfall("rule", (60, -6.5, 2.5), (14, 10, 5), 400, seed=5),
             S.snowfall("b4", (-19.3, -9.6, 2.4), (2.6, 2.2, 2.6), 160, seed=7),
             S.snowfall("b11", (0.7, -9.3, 2.4), (2.6, 2.2, 2.6), 160, seed=9)]
    S.weather(p, snows, [])

    # ============ the rule house (shots 2-3) ============
    f_out = p.word(2, "out")
    S.lamp(rule, 1, True)
    S.lamp(rule, f_out, False)
    # a real doorway behind the door: dark hall panel + a faint warm spill that grows as the door opens
    rx = 60.0
    box("rule_hall", (0.96, 0.03, 2.05), (rx, -10.985, 1.55), color("hall", (0.05, 0.03, 0.03), 0.9, emit=0.25), 0.0)
    box("rule_hallfloor", (0.96, 0.7, 0.02), (rx, -10.65, 0.51), color("hallfloor", (0.32, 0.2, 0.12), 0.7, emit=0.15), 0.0)
    spill = light("POINT", "rule_spill", (rx + 0.1, -10.6, 1.4), 0, S.WARM, size=0.25)
    # cold fill so the black shade reads as a silhouette against the house
    light("AREA", "rule_rim", (rx + 1.0, -4.0, 3.2), 260, (0.55, 0.7, 1.0), size=5, rot=(R(70), 0, R(10)))
    a2, b2, a3, b3 = sh[2][0], sh[2][1], sh[3][0], sh[3][1]
    f_ans = p.word(3, "answers")
    door = rule["door"]
    bpy.context.view_layer.update()  # shared parents the knob with a stale matrix: re-parent it to the door
    kn = rule["knob"]
    kn.parent = door
    kn.matrix_parent_inverse = door.matrix_world.inverted()
    for f, z in ((1, 0), (f_ans, 0), (f_ans + 34, 100)):
        C.key(door, "rotation_euler", f, (0, 0, R(z)))
    for f, e in ((1, 0), (f_ans + 6, 0), (f_ans + 34, 90)):
        spill.data.energy = e
        spill.data.keyframe_insert("energy", frame=f)
    gust("rule_gust", rx, -6.8, -11.3, 0.7, 2.4, f_ans - 6, b3)

    shade = S.char("SHADE", "shade", (rx, -7.3, 0), 0.0)
    shade["root"].scale = (0.88, 0.88, 0.88)  # fits under the porch roof
    f0 = f_out + 4
    SZ = rule["step_spots"]
    plants = [(f0, (rx, -7.4, 0.0)), (f0 + 12, (rx, SZ[0][1], SZ[0][2])), (f0 + 24, (rx, SZ[1][1], SZ[1][2])),
              (f0 + 36, (rx, SZ[2][1], SZ[2][2])), (f0 + 47, (rx, -9.72, 0.5))]
    stride(shade, plants, 0.2, p)
    for ft in (plants[-1][0] + 8,):  # legs settle together
        for sd in ("l", "r"):
            C.key(shade[f"{sd}_hip"], "rotation_euler", ft, (0, 0, 0))
    knock = p.ev("rule_knock")
    # arm: hangs, rises while climbing, backswing, contact exactly on rule_knock, rebound, hold
    arm(shade, "r", plants[-1][0], 0)
    arm(shade, "r", plants[-1][0] + 10, -35)
    arm(shade, "r", knock - 7, -36)
    arm(shade, "r", knock, -62)      # contact on the frame
    arm(shade, "r", knock + 6, -42)
    arm(shade, "r", knock + 22, -40)
    put(shade, f_out + 2, b2)
    C.breathe(shade, f_out + 2, b2)
    head(shade, f_out + 2, 0, 0)
    head(shade, plants[-1][0], 0, 4)
    head(shade, knock - 20, -6, 6)
    head(shade, knock + 25, 4, 8)
    C.faces_over(shade, f_out + 2, b2, "thing", seed=1)

    # ============ shot 1: wide drift down the street ============
    S.shot(s, "c1", sh[1][0], sh[1][1], (-24, -2.0, 5.0), (2, 0, 2.2), 22, move=(0.8, 0, -0.5), push=0.05)
    # ============ shot 2/3: the rule house ============
    S.shot(s, "c2", a2, b2, (rx + 3.4, -6.0, 0.55), (rx + 0.2, -9.8, 1.6), 26, move=(-0.35, -0.1, 0.05), push=0.07)
    S.shot(s, "c3", a3, b3, (rx - 1.7, -6.0, 1.3), (rx + 0.1, -10.9, 1.3), 28, move=(0.25, 0.0, 0.0), push=0.08)

    # ============ shot 4: close on a glowing porch bulb ============
    S.shot(s, "c4", sh[4][0], sh[4][1], (-20.2, -7.3, 1.5), (-19.1, -10.9, 2.4), 75, move=(0.25, 0, 0.05), push=0.1)

    # ============ shot 5: neighbour changing a bulb ============
    n10 = H["n10"]
    a5, b5 = sh[5][0], sh[5][1]
    mpos = (10.57, -10.55, 0.5)
    mrot = -0.8
    nb = S.char("NEIGH", "mom", mpos, mrot)
    box("neigh_spare", (0.1, 0.1, 0.13), (0, 0, 0), color("spare_bulb", (0.95, 0.95, 0.88), 0.15), 0.03, nb["r_shoulder"])
    sp = bpy.data.objects["neigh_spare"]
    sp.location = (0, 0, -0.68 * 0.875 - 0.02)
    sp.matrix_parent_inverse.identity()
    put(nb, a5, b5)
    for f, a_ in ((1, 0), (a5, 0), (a5 + 16, -160), (b5, -160)):
        arm(nb, "l", f, a_)
    for k, f in enumerate(range(a5 + 18, b5, 7)):   # twisting the bulb
        arm(nb, "l", f, -160, 12 if k % 2 else -12)
    arm(nb, "r", a5, -55)       # the other hand holds a spare bulb at her chest
    for k, f in enumerate(range(a5, b5 + 20, 24)):  # looks up at the lamp, a glance toward us
        head(nb, f, -50 + (24 if k % 2 else 0), -22 - (6 if k % 2 else 0))
    C.breathe(nb, a5, b5)
    C.faces_over(nb, a5, b5, "mom", seed=2)
    crate = S.crate_of_bulbs("crate5", (0, 0, 0))  # built at the origin (children are placed relative to it)
    crate.location = (11.55, -9.9, S.PORCH_Z)
    keyed_visible(crate, a5, b5)
    fill("neigh_fill", (8.6, -6.4, 1.8), 50, a5, b5)
    S.shot(s, "c5", a5, b5, (8.2, -7.0, 1.4), (10.9, -10.5, 1.5), 32, move=(0.2, 0, 0.0), push=0.1)

    # ============ shot 6: high wide, the two windows ============
    a6, b6 = sh[6][0], sh[6][1]
    S.shot(s, "c6", a6, b6, (30, 0, 7), (0, 0, 2.0), 20, move=(-0.5, 0, -0.2), push=0.06)

    # kids in the two bedroom windows (shots 6-9): stools so their faces reach the glass
    wx = nar["room_spot"][0]
    stool("nar_stool", wx - 0.33, nar["room_spot"][1], -1)
    stool("theo_stool", theo["room_spot"][0] - 0.33, theo["room_spot"][1], 1)
    na_rot = math.pi + 0.17
    npos = (wx - 0.33, nar["room_spot"][1], 0.3)
    nr = S.char("NAR_room", "nar", npos, na_rot)
    nr["root"].location = npos
    fl_n = hold_fl(nr, "FLN", "r")
    put(nr, a6, sh[7][1])
    for f, ang in ((1, 0), (a6, 0), (560, 0), (586, -90), (636, -90), (668, -20)):
        fl_arm(nr, fl_n, "r", f, ang)
    double_flash(fl_n, p.ev("nar_flash1"), p.ev("nar_flash2"))
    C.breathe(nr, a6, sh[7][1])
    gaze(nr, a6, na_rot, npos, (theo["window"][0], theo["window"][1], 1.6), cap=30)
    C.faces_over(nr, a6, sh[7][1], "kid", seed=3)
    fill("nar_fill", (wx - 0.5, nar["room_spot"][1] + 0.6, 1.5), 6, a6, sh[7][1])

    tpos = (theo["room_spot"][0] - 0.33, theo["room_spot"][1], 0.3)
    t_rot = 0.13
    tr = S.char("THEO_room", "theo", tpos, t_rot)
    tr["root"].location = tpos
    fl_t = hold_fl(tr, "FLT", "l")
    put(tr, a6, sh[9][1])
    for f, ang in ((1, 0), (a6, 0), (664, 0), (686, -90), (722, -90), (760, -55), (sh[9][1], -52)):
        fl_arm(tr, fl_t, "l", f, ang)
    double_flash(fl_t, p.ev("theo_flash1"), p.ev("theo_flash2"))
    C.breathe(tr, a6, sh[9][1])
    lamp_nar = (nar["x"] + 0.85, nar["front_y"], 2.5)
    idle(tr, a6, sh[9][1], 21, rz=t_rot, pos=(tpos[0], tpos[1], 1.45), tgt=lamp_nar, amp=1.5)
    C.faces_over(tr, a6, 707, "kid", seed=4)               # shots 6-8: eyes on the light
    C.faces_over(tr, 708, sh[9][1], "kid_sad_smile", seed=5)  # shot 9: small smile
    fill("theo_fill", (theo["room_spot"][0] + 0.2, theo["room_spot"][1] - 0.75, 1.75), 7, a6, sh[9][1])

    # ============ shot 7: inside the narrator's room, over the shoulder ============
    S.shot(s, "c7", sh[7][0], sh[7][1], (3.2, -13.45, 1.55), (1.6, -9.0, 1.5), 22, move=(-0.15, 0, 0.0), push=0.06)
    # ============ shot 8: Theo flashes back (from the street) ============
    S.shot(s, "c8", sh[8][0], sh[8][1], (-6.0, 4.6, 1.45), (-1.7, 11.0, 1.5), 72, move=(0.1, 0.1, 0.0), push=0.1)
    # ============ shot 9: Theo close ============
    S.shot(s, "c9", sh[9][0], sh[9][1], (-2.5, 4.3, 1.55), (-2.5, 11.1, 1.45), 70, move=(0.0, 0.15, 0.0), push=0.1)

    # ============ shot 10: both wave across the street ============
    a10, b10 = sh[10][0], sh[10][1]
    npos10 = (0.2, -9.05, 0.5)
    n10c = S.char("NAR_wave", "nar", npos10, math.pi)
    put(n10c, a10, b10)
    wave(n10c, "l", a10 + 4, b10)
    C.breathe(n10c, a10, b10)
    head(n10c, a10, 0, 0)
    C.faces_over(n10c, a10, b10, "kid", seed=6)
    tpos10 = (-0.4, 9.05, 0.5)
    t10 = S.char("THEO_wave", "theo", tpos10, 0.0)
    put(t10, a10, b10)
    wave(t10, "l", a10 + 10, b10, per=11)
    C.breathe(t10, a10, b10)
    idle(t10, a10, b10, 31, rz=0.0, pos=(tpos10[0], tpos10[1], 1.2), tgt=(nar["x"] + 0.85, nar["front_y"], 2.5), amp=1.5)
    C.faces_over(t10, a10, b10, "kid_sad_smile", seed=7)
    S.shot(s, "c10", a10, b10, (-0.35, -10.55, 1.5), (0.0, 8.5, 1.5), 19, move=(0.15, 0, 0.0), push=0.1)

    # ============ shot 11: the narrator's own bulb ============
    S.shot(s, "c11", sh[11][0], sh[11][1], (-1.0, -7.4, 1.45), (0.85, -10.9, 2.4), 75, move=(0.2, 0, 0.0), push=0.1)

    # ============ shot 12: dinner (Mom never looks up) ============
    a12, b12 = sh[12][0], sh[12][1]
    mp = (din["MOM_SEAT"][0], din["MOM_SEAT"][1], -0.033)
    mom = S.char("MOM_d", "mom_l", mp, math.pi)
    C.sit(mom)
    put(mom, a12, b12)
    C.breathe(mom, a12, b12, amount=0.012)
    for k, f in enumerate(range(a12, b12 + 40, 38)):       # slowly pushing food around her own plate
        arm(mom, "r", f, -55 if k % 2 == 0 else -75)
        arm(mom, "l", f, -40)
    for k, f in enumerate(range(a12, b12, 34)):
        head(mom, f, 3 if k % 2 else -3, 20 + (k % 2) * 4)
    C.faces_over(mom, a12, b12, "mom_sad", seed=8)
    npd = (din["NAR_SEAT"][0], din["NAR_SEAT"][1], 0.147)
    nd = S.char("NAR_d", "nar", npd, 0.0)
    C.sit(nd)
    put(nd, a12, b12)
    C.breathe(nd, a12, b12)
    head(nd, a12, 0, 6)
    C.faces_over(nd, a12, b12, "kid_sad", seed=9)
    fill("din_fill2", (98.4, 101.4, 1.7), 30, a12, b12, (1.0, 0.9, 0.75), size=1.0)
    fill("din_fill3", (100.3, 98.3, 1.6), 22, a12, b12, (1.0, 0.9, 0.75), size=0.6)
    S.shot(s, "c12", a12, b12, (97.5, 102.1, 1.75), (100.0, 99.9, 0.95), 24, move=(0.2, -0.1, 0.0), push=0.08)

    # ============ shot 13: classroom, empty seats around the narrator ============
    a13, b13 = sh[13][0], sh[13][1]
    D = cls["desks"]
    seats = {(1, 1): ("NAR_c", "nar", "kid"), (0, 2): ("K2", "maya", "kid"),
             (0, 3): ("K3", "bro", "kid"), (1, 3): ("K4", "kid", "kid"), (2, 0): ("K5", "maya", "kid"),
             (2, 2): ("K6", "bro", "kid"), (2, 3): ("K7", "kid", "kid")}
    for n_, (rc, (nm, look, face)) in enumerate(seats.items()):
        dx, dy = D[rc]
        kid = S.char(nm, look, (dx, dy + 0.5, 0.107), 0.0)
        C.sit(kid)
        put(kid, a13, b13)
        C.breathe(kid, a13, b13, period=1.6 + 0.1 * n_)
        for k, f in enumerate(range(a13 + 3 * n_, b13, 30)):   # eyes on the board, a little fidget
            head(kid, f, (-2 if k % 2 else 2), 0)
        C.faces_over(kid, a13, b13, face, seed=40 + n_)
        if look == "nar":
            nar_c = kid
    S.shot(s, "c13", a13, b13, (136.9, 97.2, 2.3), (139.6, 100.6, 0.85), 26, move=(0.2, 0.15, 0.0), push=0.08)

    # ============ shot 14: Theo's mom walks past, crying ============
    a14, b14 = sh[14][0], sh[14][1]
    tm = S.char("THEO_MOM", "theo_mom", (2.2, -6.0, 0), -math.pi / 2)
    put(tm, a14, b14)
    falls = C.walk_bounce(tm, a14, b14, (2.2, -6.0, 0), (-0.7, -6.0, 0), steps_per_sec=1.5)
    for f in falls:
        if a14 <= f <= b14:
            p.foley(f, "step", 0.25)
    C.breathe(tm, a14, b14)
    head(tm, a14, 0, 8)
    head(tm, a14 + 34, 0, 8)
    head(tm, a14 + 48, 55, -8)     # glances at the porch light as she passes under it
    head(tm, a14 + 72, 52, -8)
    head(tm, b14, 15, 4)
    C.faces_over(tm, a14, b14, "mom_cry", seed=10)
    fill("tm_fill", (-4.4, -7.6, 1.7), 30, a14, b14)
    S.shot(s, "c14", a14, b14, (-3.6, -8.4, 1.25), (0.5, -6.0, 1.15), 25, move=(0.2, 0.05, 0.0), push=0.08)

    # ============ shot 15: porch talk, Theo looks at the lamp ============
    a15, b15, sp15, se15 = sh[15]
    np15, nrot15 = (-0.1, -9.05, 0.5), math.pi - 0.45      # both turned a little toward the camera (3/4 faces)
    n15 = S.char("NAR_talk", "nar", np15, nrot15)
    put(n15, a15, b15)
    C.breathe(n15, a15, b15)
    idle(n15, a15, b15, 11, rz=nrot15, pos=(np15[0], np15[1], 1.2), tgt=(-0.1, -7.9, 1.2), amp=3)
    C.faces_over(n15, a15, b15, "kid", talk=[(sp15, se15)], seed=11)
    tp15, t_rot15 = (-0.1, -7.9, 0.0), 0.45
    t15 = S.char("THEO_yard", "theo", tp15, t_rot15)
    put(t15, a15, b15)
    C.breathe(t15, a15, b15)
    idle(t15, a15, b15, 51, rz=t_rot15, pos=(tp15[0], tp15[1], 1.1), tgt=(nar["x"] + 0.85, nar["front_y"] + 0.2, 3.2), amp=1.2)
    C.faces_over(t15, a15, b15, "kid_sad_smile", seed=12)
    fill("t15_fill", (1.6, -7.0, 1.6), 40, a15, b15)
    fill("n15_fill", (1.6, -8.7, 1.7), 30, a15, b15)
    S.shot(s, "c15", a15, b15, (4.0, -8.3, 1.3), (-0.1, -8.7, 1.05), 26, move=(-0.15, 0, 0.0), push=0.14)

    S.finish(s, p)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    s = S.reset(32)
    p = S.Part(1)
    make(s, p)
    S.render(s, p, args)
