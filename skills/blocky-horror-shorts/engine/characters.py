"""Blocky characters (our own designs: never Roblox's avatars, name or logo) + simple animation helpers.

A character faces -Y. Joints (empties) sit at neck, shoulders and hips, so rotating a joint swings that limb.
"""
import math

from common import GEN, box, color, decal, empty, plane

SKIN = (0.93, 0.78, 0.62)
LOOKS = {
    # proportions: head, torso (w,d,h), arm (w,h), leg (w,h), overall scale
    "kid": dict(head=0.5, torso=(0.62, 0.32, 0.62), arm=(0.28, 0.62), leg=(0.3, 0.62), scale=0.72,
                shirt=(0.95, 0.42, 0.08), pants=(0.12, 0.14, 0.2), shoes=(0.9, 0.9, 0.88), hair=(0.22, 0.13, 0.07),
                skin=SKIN, face="kid", hood=True),
    "mom": dict(head=0.5, torso=(0.62, 0.32, 0.7), arm=(0.27, 0.68), leg=(0.29, 0.72), scale=0.9,
                shirt=(0.28, 0.48, 0.32), pants=(0.25, 0.22, 0.2), shoes=(0.18, 0.12, 0.08), hair=(0.12, 0.07, 0.04),
                skin=SKIN, face="mom", bun=True),
    "thing": dict(head=0.46, torso=(0.42, 0.24, 0.85), arm=(0.15, 1.75), leg=(0.18, 1.25), scale=1.0,
                  shirt=(0.55, 0.55, 0.53), pants=(0.55, 0.55, 0.53), shoes=(0.85, 0.85, 0.82), hair=None,
                  skin=(0.88, 0.88, 0.86), face="thing", gown=True),
    "bro": dict(head=0.5, torso=(0.62, 0.32, 0.62), arm=(0.28, 0.62), leg=(0.3, 0.62), scale=0.58,
                shirt=(0.95, 0.78, 0.12), pants=(0.15, 0.22, 0.45), shoes=(0.2, 0.2, 0.22), hair=(0.35, 0.2, 0.08),
                skin=SKIN, face="kid", hood=True),
    # snow short (Same Time Tomorrow): winter coats; scarf = (rgb) wrapped at the neck with a hanging tail
    "narrator": dict(head=0.5, torso=(0.62, 0.32, 0.62), arm=(0.28, 0.62), leg=(0.3, 0.62), scale=0.72,
                     shirt=(0.16, 0.32, 0.62), pants=(0.12, 0.14, 0.2), shoes=(0.25, 0.16, 0.1), hair=(0.12, 0.08, 0.05),
                     skin=SKIN, face="kid", faces=("kid", "kid_scared", "kid_sad"), hood=True),
    "narrator_small": dict(head=0.5, torso=(0.62, 0.32, 0.62), arm=(0.28, 0.62), leg=(0.3, 0.62), scale=0.55,
                           shirt=(0.16, 0.32, 0.62), pants=(0.12, 0.14, 0.2), shoes=(0.25, 0.16, 0.1), hair=(0.12, 0.08, 0.05),
                           skin=SKIN, face="kid", faces=("kid", "kid_scared", "kid_sad"), hood=True, scarf=(0.75, 0.06, 0.05)),
    "owen": dict(head=0.5, torso=(0.62, 0.32, 0.62), arm=(0.28, 0.62), leg=(0.3, 0.62), scale=0.72,
                 shirt=(0.2, 0.36, 0.22), pants=(0.2, 0.2, 0.24), shoes=(0.15, 0.12, 0.1), hair=(0.55, 0.32, 0.12),
                 skin=(0.96, 0.88, 0.84), face="kid", faces=("kid", "kid_scared", "kid_sad"), scarf=(0.75, 0.06, 0.05)),
    "maya": dict(head=0.5, torso=(0.62, 0.32, 0.62), arm=(0.28, 0.62), leg=(0.3, 0.62), scale=0.7,
                 shirt=(0.85, 0.45, 0.6), pants=(0.15, 0.15, 0.22), shoes=(0.9, 0.9, 0.88), hair=(0.08, 0.05, 0.03),
                 skin=(0.78, 0.58, 0.42), face="kid", faces=("kid", "kid_scared", "kid_sad"), scarf=(0.45, 0.15, 0.6)),
    "mom_winter": dict(head=0.5, torso=(0.62, 0.32, 0.7), arm=(0.27, 0.68), leg=(0.29, 0.72), scale=0.9,
                       shirt=(0.45, 0.22, 0.2), pants=(0.25, 0.22, 0.2), shoes=(0.18, 0.12, 0.08), hair=(0.12, 0.07, 0.04),
                       skin=SKIN, face="mom", faces=("mom", "mom_sad"), bun=True),
    "coated": dict(head=0.46, torso=(0.42, 0.24, 0.85), arm=(0.15, 1.75), leg=(0.18, 1.25), scale=1.05,
                   shirt=(0.95, 0.78, 0.12), pants=(0.95, 0.78, 0.12), shoes=(0.12, 0.12, 0.12), hair=None,
                   skin=(0.88, 0.88, 0.86), face="thing", gown=True),
    # porch-light short (Still On)
    "nar": dict(head=0.5, torso=(0.62, 0.32, 0.62), arm=(0.28, 0.62), leg=(0.3, 0.62), scale=0.72,
                shirt=(0.3, 0.38, 0.55), pants=(0.12, 0.14, 0.2), shoes=(0.85, 0.85, 0.82), hair=(0.12, 0.08, 0.05),
                skin=SKIN, face="kid", faces=("kid", "kid_blink", "kid_sad", "kid_sad_blink", "kid_scared", "kid_scared_blink", "kid_talk"), hood=True, detail=True),
    "theo": dict(head=0.5, torso=(0.62, 0.32, 0.62), arm=(0.28, 0.62), leg=(0.3, 0.62), scale=0.74,
                 shirt=(0.95, 0.72, 0.1), pants=(0.15, 0.2, 0.35), shoes=(0.3, 0.12, 0.08), hair=(0.55, 0.25, 0.08),
                 skin=SKIN, face="kid", faces=("kid", "kid_blink", "kid_sad", "kid_sad_blink", "kid_scared", "kid_scared_blink", "kid_talk", "kid_sad_smile", "kid_sad_smile_blink", "kid_shout"), hood=True, detail=True),
    "mom_l": dict(head=0.5, torso=(0.62, 0.32, 0.7), arm=(0.27, 0.68), leg=(0.29, 0.72), scale=0.9,
                  shirt=(0.48, 0.36, 0.44), pants=(0.22, 0.2, 0.22), shoes=(0.18, 0.12, 0.08), hair=(0.12, 0.07, 0.04),
                  skin=SKIN, face="mom", faces=("mom", "mom_blink", "mom_sad", "mom_sad_blink", "mom_cry", "mom_talk"), bun=True, detail=True),
    "theo_mom": dict(head=0.5, torso=(0.62, 0.32, 0.7), arm=(0.27, 0.68), leg=(0.29, 0.72), scale=0.9,
                     shirt=(0.2, 0.36, 0.3), pants=(0.2, 0.2, 0.24), shoes=(0.15, 0.1, 0.08), hair=(0.5, 0.22, 0.07),
                     skin=SKIN, face="mom", faces=("mom", "mom_blink", "mom_sad", "mom_sad_blink", "mom_cry", "mom_talk"), bun=True, detail=True),
    "hale": dict(head=0.5, torso=(0.64, 0.34, 0.72), arm=(0.27, 0.66), leg=(0.29, 0.66), scale=0.86,
                 shirt=(0.62, 0.55, 0.72), pants=(0.62, 0.55, 0.72), shoes=(0.85, 0.7, 0.75), hair=(0.78, 0.78, 0.8),
                 skin=(0.9, 0.78, 0.68), face="mom", faces=("mom", "mom_blink", "mom_sad", "mom_sad_blink"), bun=True, gown=True, detail=True),
    "shade": dict(head=0.46, torso=(0.42, 0.24, 0.85), arm=(0.15, 1.75), leg=(0.18, 1.25), scale=1.05,
                  shirt=(0.02, 0.02, 0.025), pants=(0.02, 0.02, 0.025), shoes=(0.01, 0.01, 0.01), hair=None,
                  skin=(0.05, 0.05, 0.06), face="thing", gown=True),
}


def make(name, kind, loc, rot_z=0.0):
    L = LOOKS[kind]
    s = L["scale"]
    tw, td, th = L["torso"]
    aw, ah = L["arm"]
    lw, lh = L["leg"]
    hd = L["head"]
    root = empty(f"{name}", (0, 0, 0))
    skin = color(f"{kind}_skin", L["skin"], 0.45)
    shirt = color(f"{kind}_shirt", L["shirt"], 0.85, fabric=True)
    pants = color(f"{kind}_pants", L["pants"], 0.85, fabric=True)
    shoes = color(f"{kind}_shoes", L["shoes"], 0.5)
    j = {"root": root}
    # legs + shoes, swinging from the hips
    for side, x in (("l", lw / 2 + 0.01), ("r", -lw / 2 - 0.01)):
        hip = empty(f"{name}_{side}_hip", (x, 0, lh), root)
        box(f"{name}_{side}_leg", (lw, lw, lh), (x, 0, lh / 2), pants, 0.03, hip)
        box(f"{name}_{side}_shoe", (lw * 1.08, lw * 1.35, 0.1), (x, -lw * 0.15, 0.05), shoes, 0.03, hip)
        j[f"{side}_hip"] = hip
    box(f"{name}_torso", (tw, td, th), (0, 0, lh + th / 2), shirt, 0.04, root)
    if L.get("gown"):  # THING: a long old nightgown hanging over the thighs
        box(f"{name}_gown", (tw * 1.15, td * 1.2, lh * 0.55), (0, 0, lh - lh * 0.55 / 2 + 0.02), shirt, 0.03, root)
    # arms swinging from the shoulders
    for side, x in (("l", tw / 2 + aw / 2 + 0.01), ("r", -tw / 2 - aw / 2 - 0.01)):
        sh = empty(f"{name}_{side}_shoulder", (x, 0, lh + th - 0.05), root)
        box(f"{name}_{side}_sleeve", (aw, aw, ah * 0.75), (x, 0, lh + th - 0.05 - ah * 0.375), shirt, 0.03, sh)
        box(f"{name}_{side}_hand", (aw * 0.92, aw * 0.92, ah * 0.25), (x, 0, lh + th - 0.05 - ah * 0.875), skin, 0.04, sh)
        j[f"{side}_shoulder"] = sh
    # head on a neck joint, face decal on the front
    neck = empty(f"{name}_neck", (0, 0, lh + th), root)
    hz = lh + th + hd / 2 + 0.03
    box(f"{name}_head", (hd, hd, hd), (0, 0, hz), skin, 0.08, neck)
    faces = {}
    for f in L.get("faces") or (("kid", "kid_scared") if kind in ("kid", "bro") else (L["face"],)):
        faces[f] = plane(f"{name}_face_{f}", (hd * 0.9, hd * 0.9), (0, -hd / 2 - 0.006, hz), (math.pi / 2, 0, 0),
                         decal(f"face_{f}", GEN / f"face_{f}.png"), neck)
    if L["hair"]:
        hair = color(f"{kind}_hair", L["hair"], 0.7)
        box(f"{name}_hair", (hd * 1.06, hd * 1.06, hd * 0.28), (0, 0.02, hz + hd * 0.42), hair, 0.05, neck)
        box(f"{name}_hairback", (hd * 1.06, hd * 0.3, hd * 0.75), (0, hd * 0.4, hz + 0.05), hair, 0.05, neck)
        if L.get("bun"):
            bpy_sphere(f"{name}_bun", 0.13, (0, hd * 0.55, hz + hd * 0.45), hair, neck)
    if L.get("hood"):  # hoodie hood resting behind the head
        box(f"{name}_hood", (hd * 0.95, hd * 0.35, hd * 0.55), (0, hd * 0.55, lh + th + 0.12), shirt, 0.06, root)
    if L.get("scarf"):  # wrapped at the neck + a tail hanging down the chest
        sc = color(f"{name}_scarf", L["scarf"], 0.9, fabric=True)
        j["scarf"] = [box(f"{name}_scarf", (tw * 0.9, td * 1.25, 0.14), (0, 0, lh + th - 0.02), sc, 0.04, root),
                      box(f"{name}_scarf_tail", (0.13, 0.05, 0.36), (tw * 0.22, -td * 0.62, lh + th - 0.2), sc, 0.02, root)]
    if L.get("detail"):  # richer clothes: soles, cuffs, belt, hoodie pocket + strings, fringe
        dark = color(f"{kind}_trim", tuple(c * 0.55 for c in L["shirt"]), 0.8, fabric=True)
        sole = color("sole", (0.92, 0.92, 0.9), 0.6)
        for side, x in (("l", lw / 2 + 0.01), ("r", -lw / 2 - 0.01)):
            box(f"{name}_{side}_sole", (lw * 1.12, lw * 1.4, 0.035), (x, -lw * 0.15, 0.017), sole, 0.01, j[f"{side}_hip"])
            sx = tw / 2 + aw / 2 + 0.01
            sx = sx if side == "l" else -sx
            box(f"{name}_{side}_cuff", (aw * 1.06, aw * 1.06, 0.06), (sx, 0, lh + th - 0.05 - ah * 0.75 + 0.03), dark, 0.01, j[f"{side}_shoulder"])
        box(f"{name}_belt", (tw * 1.02, td * 1.04, 0.06), (0, 0, lh + 0.03), color("belt", (0.12, 0.1, 0.09), 0.6), 0.01, root)
        if not L.get("gown"):
            box(f"{name}_pocket", (tw * 0.6, 0.02, th * 0.25), (0, -td / 2 - 0.01, lh + th * 0.25), dark, 0.01, root)
            for dx in (-0.07, 0.07):
                box(f"{name}_string{dx}", (0.022, 0.022, th * 0.32), (dx, -td / 2 - 0.015, lh + th * 0.78), color("string", (0.95, 0.95, 0.93), 0.6), 0.004, root)
        if L["hair"]:
            box(f"{name}_fringe", (hd * 1.04, hd * 0.12, hd * 0.13), (0, -hd / 2 - 0.02, hz + hd * 0.39), color(f"{kind}_hair", L["hair"], 0.7), 0.03, neck)
    j["neck"], j["faces"] = neck, faces
    root.scale = (s, s, s)
    root.location, root.rotation_euler = loc, (0, 0, rot_z)
    return j


def bpy_sphere(name, r, loc, mat, parent):
    import bpy
    from common import keep
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=24, ring_count=12)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    keep(o, parent)
    return o


# ---- animation helpers (keyframes) -------------------------------------------------

def key(obj, path, frame, value):
    setattr(obj, path, value)
    obj.keyframe_insert(path, frame=frame)


def fcurves(obj):
    """All animation curves of an object (Blender 5 keeps them in layered actions: layers > strips > channelbags)."""
    act = obj.animation_data.action if obj.animation_data else None
    if not act:
        return []
    if hasattr(act, "layers") and act.layers:
        return [fc for lay in act.layers for st in lay.strips for cb in st.channelbags for fc in cb.fcurves]
    return list(getattr(act, "fcurves", []))


def breathe(j, a, b, period=1.7, amount=0.015):
    """Idle breathing over frames a..b: the whole body swells a little in height, around its own base scale."""
    root = j["root"]
    base = root.scale.copy()
    half = max(2, round(period * 15))
    for n, fr in enumerate(range(a, b + 1, half)):
        k = 1 + amount * (n % 2)
        key(root, "scale", fr, (base.x, base.y, base.z * k))
    root.scale = base


# push_in: adapted from mromidev/claude-animated-shorts, MIT License, Copyright (c) 2026 mromidev (see NOTICE.md).
def push_in(cam, a, b, rate=0.0015):
    """Slow linear lens push over a shot (frames a..b) so no hold reads as frozen; rate = zoom per frame."""
    lens = cam.data.lens
    key(cam.data, "lens", a, lens)
    key(cam.data, "lens", b, lens * (1 + rate * (b - a)))
    linear(cam.data)


def linear(obj):
    """Constant speed instead of ease-in/out (walking, camera dollies)."""
    for fc in fcurves(obj):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def sit(j):
    """Seated pose: thighs forward, arms resting forward."""
    for s in ("l", "r"):
        j[f"{s}_hip"].rotation_euler = (math.radians(-90), 0, 0)
        j[f"{s}_shoulder"].rotation_euler = (math.radians(-40), 0, 0)


def walk(j, start, end, frm, to, stride=0.9, steps_per_sec=2.0, fps=30):
    """Walk the root from frm to to between frames start..end, swinging arms and legs."""
    root = j["root"]
    key(root, "location", start, frm)
    key(root, "location", end, to)
    linear(root)
    period = fps / steps_per_sec
    f, phase = start, 0
    while f <= end:
        a = math.radians(28) * (1 if phase % 2 == 0 else -1)
        for s, sign in (("l", 1), ("r", -1)):
            key(j[f"{s}_hip"], "rotation_euler", int(f), (a * sign, 0, 0))
            key(j[f"{s}_shoulder"], "rotation_euler", int(f), (-a * sign * 0.8, 0, 0))
        f += period / 2
        phase += 1


def turn_head(j, frame, degrees, dur=8):
    neck = j["neck"]
    key(neck, "rotation_euler", frame, tuple(neck.rotation_euler))
    key(neck, "rotation_euler", frame + dur, (0, 0, math.radians(degrees)))


def show_face(j, name, frame):
    """Switch which face decal renders from this frame on (e.g. smile -> scared)."""
    for f, o in j["faces"].items():
        o.hide_render = f != name
        o.keyframe_insert("hide_render", frame=frame)


def faces_over(j, a, b, base, talk=(), blink=True, seed=0):
    """Drive one character's face over frames a..b: `base` face, a mouth flap (base <-> *_talk every 3 frames) inside
    each talk span (f0, f1), and a 3-frame blink every 2.5-4.5 s. Keys only the frames where the face changes.
    Call AFTER any S.visible on that character, and once per range (ranges must not overlap)."""
    import random
    rnd = random.Random(seed)
    faces = j["faces"]
    talk_face = next((f for f in ("kid_talk", "mom_talk") if f in faces), None)
    blink_face = f"{base}_blink" if f"{base}_blink" in faces else None
    want = {}
    for f in range(a, b + 1):
        want[f] = base
    if blink and blink_face:
        f = a + rnd.randint(20, 60)
        while f + 3 <= b:
            for k in range(3):
                want[f + k] = blink_face
            f += rnd.randint(75, 135)
    for f0, f1 in talk:
        if talk_face:
            for f in range(max(a, f0), min(b, f1) + 1):
                want[f] = talk_face if ((f - f0) // 3) % 2 == 0 else base
    prev = None
    for f in range(a, b + 1):
        if want[f] != prev:
            show_face(j, want[f], f)
            prev = want[f]


def walk_bounce(j, start, end, frm, to, steps_per_sec=2.0, bounce=0.035, fps=30):
    """walk() plus a small body bob, and returns the footfall frames (put a footstep sound on each one)."""
    walk(j, start, end, frm, to, steps_per_sec=steps_per_sec, fps=fps)
    root = j["root"]
    half = fps / steps_per_sec / 2
    falls, f = [], float(start)
    while f <= end:
        falls.append(int(round(f)))
        f += half
    z0 = root.location.z if not hasattr(frm, "__len__") else frm[2]
    for k, ff in enumerate(falls):
        root.location.z = z0
        root.keyframe_insert("location", index=2, frame=ff)
        mid = int(round(ff + half / 2))
        if mid < end:
            root.location.z = z0 + bounce
            root.keyframe_insert("location", index=2, frame=mid)
    for fc in fcurves(root):
        if fc.data_path == "location" and fc.array_index == 2:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
    return falls
