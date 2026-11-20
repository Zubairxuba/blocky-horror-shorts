"""Shared base for "Still On" (porch-light short). Every part's scene.py imports this so all three parts match.
NEVER edit this file from a part: ask the lead.

TIMELINE: S.Part(n) gives your part's shots (frames re-based so your first frame is 1), event frames and word frames.
  Every synced beat (knocks, flashes, light changes, steps...) is in events.json: key your visual ON p.ev("id").
  The lead plays the sound on that same frame. Footsteps you create: p.foley(frame, "step") (sound added centrally).

COORDINATES (metres; characters face -Y, rot_z=math.pi faces +Y; road along X, y in [-4.5, 4.5]):
  Near side (y<0, houses face +Y = toward the street): NAR house x=0, HALE house x=-10, others x=10, 20, -20, -30, 30.
  Far side (y>0, houses face -Y): THEO house x=0 (directly across from NAR), others x=-10, 10, -20, 20, -30, 30.
  Each house (front wall at y=-FRONT_Y near / +FRONT_Y far): a porch (deck top z=PORCH_Z) with 3 steps down to the
    yard, a door (hinged object H["door"], swing it with rotation_euler.z), a porch lamp, a welcome mat, a mailbox.
  NAR and THEO houses have a REAL bedroom window (right of the door seen from the street) with a lit room behind it:
    a kid can stand inside at H["room_spot"] and be seen through the glass; from inside you see the other house across.
  Handles: H = S.street()["houses"][name] for names "nar", "theo", "hale", "n10", "n20", ..., "f-10", "f10", ...
    H keys: door, lamp (bulb object), porch_spot (on the porch in front of the door, facing the street), step_spots
    (3 points on the steps, bottom->top), mat_spot, room_spot (nar/theo), window (outside centre of the bedroom window),
    in_eye (nar/theo: camera spot inside the room looking out through the window).
  DINING room at x=100 (S.dining()), CLASSROOM at x=140 (S.classroom()): see their docstrings for spots.

LIGHTS: porch lamps follow ONE table (porch_states) driven by events.json; call S.apply_lights(street) once in your
  build. Never key a porch lamp yourself. Time of day (night / morning / dawn / afternoon) is also central.
CAMERAS: ONLY S.shot(...) and S.continue_shot(...). They key eased moves, add the marker, and refuse moves that are
  too fast. S.check_cameras(s) at the end refuses cameras inside or right against geometry.
"""
import json, math, random, sys
from pathlib import Path

import bpy
from mathutils import Vector

SKILL = Path(__file__).resolve().parents[2]  # the skill folder; in a copied story set it to the absolute skill path
BLENDER = SKILL / "engine"
sys.path.insert(0, str(BLENDER))
import characters as C  # noqa: E402
import look  # noqa: E402  (depth of field, haze, rim light, post-grade)
import sets  # noqa: E402
from common import GEN, box, color, decal, empty, light, pbr, plane  # noqa: E402

FPS, W, H = 30, 1440, 2560
HERE = Path(__file__).resolve().parent
SHOTS = json.loads((HERE / "shots.json").read_text())
EVENTS = {e["id"]: e for e in json.loads((HERE / "events.json").read_text())}
WORDS = {int(k): v for k, v in json.loads((HERE / "words_full.json").read_text()).items()}
PARTS = (1, 16, 27, 39)  # first line of each part (1-based); part n = lines PARTS[n-1] .. PARTS[n]-1
FRONT_Y, DEPTH, HOUSE_H, PORCH_Z = 11.0, 6.0, 4.2, 0.5
NEAR_X = (-30, -20, -10, 0, 10, 20, 30)
FAR_X = (-30, -20, -10, 0, 10, 20, 30)
WARM = (1.0, 0.72, 0.38)
MAX_SPEED, MAX_TURN, MAX_ZOOM = 0.45, 8.0, 0.30  # camera limits: m/s, deg/s, lens change per shot


def frame(t):
    return round(t * FPS) + 1


def line_frames(line):
    """Full-timeline (a, b, speech_start, speech_end) frames of a script line."""
    s = SHOTS[line - 1]
    a, b = frame(s["start"]), round(s["end"] * FPS)
    sp = s["start"] + s["lead"]
    return a, b, frame(sp), frame(sp + s["say"][1] - s["say"][0])


class Part:
    """Your part's view of the timeline, re-based so your first frame is 1."""

    def __init__(self, n):
        self.n = n
        self.lines = list(range(PARTS[n - 1], PARTS[n]))
        self.off = line_frames(self.lines[0])[0] - 1
        self.last = line_frames(self.lines[-1])[1] - self.off
        self._foley = []

    def shot(self, line):
        """(a, b, speech_start, speech_end) of a line, in YOUR frames."""
        return tuple(f - self.off for f in line_frames(line))

    def ev(self, eid):
        return EVENTS[eid]["frame"] - self.off

    def word(self, line, w, n=1):
        """Frame where the n-th `w` (lower case, no punctuation) of a line is spoken."""
        hits = [t for x, t in WORDS[line] if x == w]
        return frame(hits[n - 1]) - self.off

    def foley(self, f, sound="step", gain=0.5):
        self._foley.append(dict(frame=f + self.off, sound=sound, gain=gain))
        (HERE / f"part{self.n}" / "foley.json").write_text(json.dumps(self._foley, indent=1))


# ---------------------------------------------------------------- render setup ------------------------------------

def reset(samples=32):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            s.render.engine = eng
            break
        except TypeError:
            continue
    e = s.eevee
    e.taa_render_samples = samples
    for attr, val in (("use_raytracing", False), ("use_shadows", True), ("use_volumetric_shadows", False),
                      ("volumetric_tile_size", "8"), ("use_gtao", True), ("gtao_distance", 0.6)):
        if hasattr(e, attr):
            setattr(e, attr, val)
    s.render.resolution_x, s.render.resolution_y, s.render.fps = W, H, FPS
    s.render.resolution_percentage = 100
    s.view_settings.view_transform = "AgX"
    s.view_settings.look = "AgX - Medium High Contrast"
    s.view_settings.exposure = 0.3
    s.render.image_settings.file_format = "PNG"
    s.render.use_motion_blur = False
    return s


def atmosphere(density=0.0015):
    """Thin haze in the air (call once after the world/sets exist): lamp halos, light cones, depth."""
    look.haze(density)


def render(s, part, args):
    """--frames 10,50 -> partN/test/; --preview -> 30% size, 8 samples -> partN/preview/; else partN/frames/."""
    d = HERE / f"part{part.n}"
    s.frame_start, s.frame_end = 1, part.last
    frames = [int(x) for x in args[args.index("--frames") + 1].split(",")] if "--frames" in args else None
    if "--preview" in args:
        s.render.resolution_percentage, s.eevee.taa_render_samples = 30, 8
        out = d / "preview"
    else:
        out = d / ("test" if frames else "frames")
    out.mkdir(parents=True, exist_ok=True)
    for fr in frames or range(1, part.last + 1):
        p = out / f"{fr:04d}.png"
        if p.exists() and not frames:
            continue
        s.frame_set(fr)
        s.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        print(f"frame {fr}/{part.last}", flush=True)


# ---------------------------------------------------------------- small helpers -----------------------------------

def hinged(o, pivot):
    """box() bakes its location into the mesh (origin at the world origin). Move the origin to `pivot` so the object
    rotates/scales around that point (a door hinge, a lid, a hand)."""
    p = Vector(pivot)
    for v in o.data.vertices:
        v.co -= p
    o.location = p
    return o


def char(name, kind, loc, rot_z=0.0, face=None):
    """C.make + show ONLY one face (default: the look's first face). Use this, not C.make, for every character."""
    j = C.make(name, kind, loc, rot_z)
    look.rim([j["root"], *j["root"].children_recursive])  # soft light edge so characters pop off dark backgrounds
    base = face or next(iter(j["faces"]))
    for f, o in j["faces"].items():
        o.hide_render = f != base
    return j


def constant(obj):
    for fc in C.fcurves(obj):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"


def visible(j, frame_, on):
    """Key render visibility for a whole character/prop group (hide_render does not inherit to children)."""
    objs = [j["root"], *j["root"].children_recursive] if isinstance(j, dict) else [j, *j.children_recursive]
    for o in objs:
        o.hide_render = not on
        o.keyframe_insert("hide_render", frame=frame_)


def snow_mat():
    return color("snow", (0.82, 0.86, 0.95), 0.8)


# ---------------------------------------------------------------- the street --------------------------------------

def porch_house(name, x, side, room=False, lit=(True, False)):
    """side=-1: near side (front at y=-FRONT_Y, faces +Y); side=+1: far side (front at y=+FRONT_Y, faces -Y)."""
    f = -side  # direction the front faces (+1 = +Y)
    fy = side * FRONT_Y  # front wall plane
    cy = fy + side * DEPTH / 2
    brick, roof, snow = pbr("red_brick", 0.5), pbr("clay_roof_tiles", 0.35), snow_mat()
    wood = color("porch_wood", (0.42, 0.3, 0.2), 0.7)
    trim = color("trim", (0.9, 0.9, 0.86), 0.5)
    H = {"x": x, "side": side, "front_y": fy}
    wx = x + 2.2 * (1 if side < 0 else -1)  # bedroom window: right of the door as seen from the street
    if room:  # front wall in pieces around a real window opening (w 1.4, z 1.0..2.3) + a small lit room behind
        z0, z1, ww = 1.0, 2.3, 1.4
        th = 0.25
        wy = fy + side * th / 2
        left, right = x - 3.25, x + 3.25
        box(f"{name}_wall_a", (wx - ww / 2 - left, th, HOUSE_H), ((left + wx - ww / 2) / 2, wy, HOUSE_H / 2), brick, 0.0)
        box(f"{name}_wall_b", (right - wx - ww / 2, th, HOUSE_H), ((right + wx + ww / 2) / 2, wy, HOUSE_H / 2), brick, 0.0)
        box(f"{name}_wall_lo", (ww, th, z0), (wx, wy, z0 / 2), brick, 0.0)
        box(f"{name}_wall_hi", (ww, th, HOUSE_H - z1), (wx, wy, (z1 + HOUSE_H) / 2), brick, 0.0)
        for k, (sx, sz, px, pz) in enumerate(((0.08, z1 - z0 + 0.16, wx - ww / 2, (z0 + z1) / 2), (0.08, z1 - z0 + 0.16, wx + ww / 2, (z0 + z1) / 2),
                                              (ww + 0.16, 0.08, wx, z1), (ww + 0.3, 0.1, wx, z0 - 0.02), (0.05, z1 - z0, wx, (z0 + z1) / 2))):
            box(f"{name}_wframe_{k}", (sx, 0.14, sz), (px, fy, pz), trim, 0.005)
        box(f"{name}_sillsnow", (ww + 0.3, 0.16, 0.05), (wx, fy - side * 0.06, z0 + 0.05), snow, 0.02)
        glass = bpy.data.materials.get("glass_l") or bpy.data.materials.new("glass_l")
        glass.use_nodes = True
        p = glass.node_tree.nodes["Principled BSDF"]
        p.inputs["Base Color"].default_value = (0.7, 0.8, 0.9, 1)
        p.inputs["Roughness"].default_value = 0.05
        p.inputs["Alpha"].default_value = 0.1
        if hasattr(glass, "surface_render_method"):
            glass.surface_render_method = "BLENDED"
        box(f"{name}_glass", (ww, 0.02, z1 - z0), (wx, fy + side * 0.02, (z0 + z1) / 2), glass, 0.0)
        # the rest of the house behind the front wall (room box: 3.4 wide, 3 deep, 2.8 high)
        rx0, rx1 = wx - 1.7, wx + 1.7
        ry_in = fy + side * 0.25
        ry_back = ry_in + side * 3.0
        wallp = color(f"{name}_paint", (0.55, 0.62, 0.72) if name == "nar" else (0.72, 0.62, 0.45), 0.8)
        box(f"{name}_room_floor", (3.4, 3.0, 0.1), (wx, (ry_in + ry_back) / 2, -0.05), pbr("laminate_floor_02", 0.6), 0)
        box(f"{name}_room_ceil", (3.4, 3.0, 0.1), (wx, (ry_in + ry_back) / 2, 2.85), color("ceil", (0.8, 0.8, 0.8), 0.8), 0)
        box(f"{name}_room_back", (3.4, 0.1, 2.9), (wx, ry_back, 1.45), wallp, 0)
        for sx in (rx0, rx1):
            box(f"{name}_room_side_{sx}", (0.1, 3.0, 2.9), (sx, (ry_in + ry_back) / 2, 1.45), wallp, 0)
        # body of the house around the room (so it reads as solid from the street)
        box(f"{name}_body", (6.5, DEPTH - 3.3, HOUSE_H), (x, ry_back + side * (DEPTH - 3.3) / 2, HOUSE_H / 2), brick, 0.02)
        other = (left, rx0) if wx > x else (rx1, right)
        box(f"{name}_body2", (other[1] - other[0], 3.05, HOUSE_H), ((other[0] + other[1]) / 2, (ry_in + ry_back) / 2, HOUSE_H / 2), brick, 0.0)
        box(f"{name}_bed", (1.0, 1.9, 0.5), (wx + (1.1 if side < 0 else -1.1), ry_back - side * 1.0, 0.25), color("bedspread", (0.2, 0.3, 0.55) if name == "nar" else (0.55, 0.2, 0.15), 0.9, fabric=True), 0.04)
        box(f"{name}_poster", (0.6, 0.02, 0.8), (wx - 0.6, ry_back - side * 0.06, 1.7), color(f"{name}_poster", (0.85, 0.5, 0.15) if name == "nar" else (0.2, 0.5, 0.75), 0.6), 0.0)
        iy = fy + side * (th + 0.012)  # painted inside face of the front wall, around the window
        for k, (sx, sz, px, pz) in enumerate((((wx - ww / 2) - rx0, 2.9, (rx0 + wx - ww / 2) / 2, 1.45), (rx1 - (wx + ww / 2), 2.9, (rx1 + wx + ww / 2) / 2, 1.45),
                                              (ww, z0, wx, z0 / 2), (ww, 2.9 - z1, wx, (z1 + 2.9) / 2))):
            box(f"{name}_inpaint_{k}", (sx, 0.02, sz), (px, iy, pz), wallp, 0.0)
        light("POINT", f"{name}_roomlight", (wx, ry_in + side * 1.6, 2.4), 70, WARM, size=0.4)
        H["room_spot"] = (wx, ry_in + side * 0.55, 0.0)
        H["window"] = (wx, fy, 1.65)
        H["in_eye"] = (wx + (0.35 if side < 0 else -0.35), ry_in + side * 2.2, 1.5)
    else:
        box(f"{name}_house", (6.5, DEPTH, HOUSE_H), (x, cy, HOUSE_H / 2), brick, 0.02)
    sets.prism(f"{name}_roof", x, cy, 7.0, DEPTH + 0.6, HOUSE_H, DEPTH * 0.42, roof)
    sets.prism(f"{name}_roofsnow", x, cy, 6.9, DEPTH + 0.5, HOUSE_H + 0.04, DEPTH * 0.42 + 0.06, snow)
    # porch: deck, 3 steps toward the street, posts, a small roof with snow, lamp, mat, door
    py = fy - side * 0.9
    box(f"{name}_deck", (2.6, 1.8, PORCH_Z), (x, py, PORCH_Z / 2), wood, 0.02)
    steps = []
    for k in range(3):
        h = PORCH_Z * (3 - k) / 3
        sy = fy - side * (1.8 + 0.3 * k + 0.15)
        box(f"{name}_step{k}", (1.4, 0.3, h), (x, sy, h / 2), wood, 0.015)
        box(f"{name}_stepsnow{k}", (1.3, 0.22, 0.03), (x - 0.0, sy, h + 0.015), snow, 0.01)
        steps.append((x, sy, h))
    H["step_spots"] = list(reversed(steps))  # bottom -> top
    for px in (x - 1.2, x + 1.2):
        box(f"{name}_post_{px}", (0.12, 0.12, 2.6), (px, fy - side * 1.7, PORCH_Z + 1.3), trim, 0.01)
    box(f"{name}_porchroof", (2.9, 2.0, 0.12), (x, py, PORCH_Z + 2.65), trim, 0.02)
    box(f"{name}_porchroofsnow", (2.8, 1.9, 0.08), (x, py, PORCH_Z + 2.75), snow, 0.03)
    door = box(f"{name}_door", (1.0, 0.08, 2.1), (x, fy - side * 0.05, PORCH_Z + 1.05), color("door_red", (0.35, 0.08, 0.06), 0.5), 0.02)
    knob = box(f"{name}_knob", (0.07, 0.07, 0.07), (x + 0.38, fy - side * 0.11, PORCH_Z + 1.0), color("brass", (0.8, 0.62, 0.25), 0.25), 0.02)
    hinged(door, (x - 0.5, fy - side * 0.05, PORCH_Z))
    knob.parent = door
    knob.matrix_parent_inverse = door.matrix_world.inverted()
    H["door"], H["knob"] = door, knob
    bulb_m = color(f"{name}_bulb", WARM, 0.3, emit=12.0)
    box(f"{name}_lampbase", (0.18, 0.08, 0.3), (x + 0.85, fy - side * 0.06, PORCH_Z + 2.0), color("lamp_metal", (0.1, 0.1, 0.1), 0.4), 0.01)
    bulb = box(f"{name}_bulb", (0.12, 0.12, 0.16), (x + 0.85, fy - side * 0.16, PORCH_Z + 1.98), bulb_m, 0.03)
    pl = light("POINT", f"{name}_porchlight", (x + 0.6, fy - side * 0.7, PORCH_Z + 2.2), 120, WARM, size=0.15)
    H["lamp"], H["lamp_light"], H["bulb_mat"] = bulb, pl, bulb_m
    box(f"{name}_mat", (0.9, 0.55, 0.02), (x, fy - side * 0.45, PORCH_Z + 0.01), color("mat", (0.3, 0.2, 0.12), 0.95, fabric=True), 0.005)
    H["mat_spot"] = (x, fy - side * 0.45, PORCH_Z + 0.02)
    H["porch_spot"] = (x, fy - side * 0.9, PORCH_Z)
    # front windows (glowing or dark), except where the real bedroom window is
    for k, wx2 in enumerate((x - 2.2, x + 2.2)):
        if room and abs(wx2 - wx) < 0.1:
            continue
        on = lit[k % len(lit)]
        g = color("win_on_l", WARM, 0.4, emit=5.0) if on else color("win_off_l", (0.03, 0.04, 0.07), 0.15)
        box(f"{name}_win{k}", (1.3, 0.08, 1.2), (wx2, fy - side * 0.02, 1.65), g, 0.0)
        box(f"{name}_winframe{k}", (1.5, 0.06, 1.4), (wx2, fy + side * 0.01, 1.65), color("frame", (0.9, 0.9, 0.86), 0.5), 0.01)
        box(f"{name}_winsnow{k}", (1.5, 0.14, 0.05), (wx2, fy - side * 0.08, 1.0), snow, 0.02)
    # mailbox at the street edge
    my = side * 5.2
    box(f"{name}_mailpost", (0.08, 0.08, 1.0), (x + 2.6, my, 0.5), wood, 0.005)
    box(f"{name}_mailbox", (0.25, 0.45, 0.25), (x + 2.6, my, 1.1), color("mailbox", (0.15, 0.2, 0.3), 0.4), 0.03)
    box(f"{name}_mailsnow", (0.27, 0.47, 0.04), (x + 2.6, my, 1.24), snow, 0.01)
    return H


def street():
    """The whole street. Returns {"houses": {...}, "lamps": [...]}."""
    sets.world(0.3)
    snow = snow_mat()
    box("ground", (240, 90, 0.2), (0, 0, -0.1), snow, 0)
    box("road", (240, 9, 0.04), (0, 0, 0.0), color("slush", (0.32, 0.34, 0.4), 0.55), 0)  # wet slush: glossier
    for side in (1, -1):
        box(f"bank_{side}", (240, 0.45, 0.12), (0, side * 4.4, 0.04), snow, 0.06)
        box(f"path_{side}", (240, 1.4, 0.03), (0, side * 6.0, 0.015), color("path", (0.6, 0.62, 0.68), 0.7), 0.0)
    houses = {}
    for x in NEAR_X:
        name = {0: "nar", -10: "hale"}.get(x, f"n{x}")
        houses[name] = porch_house(name, x, -1, room=(x == 0), lit=(x % 20 == 0, x % 30 == 0))
    for x in FAR_X:
        name = "theo" if x == 0 else f"f{x}"
        houses[name] = porch_house(name, x, 1, room=(x == 0), lit=(x % 20 != 0, True))
    for x, y in ((-5, -8.5), (15, -8.5), (-15, 8.5), (5, 8.8), (25, 8.5), (-25, -8.5)):
        tree(x, y)
    lamps = [lamp_post(x, -4.9) for x in (-15, 5, 25)] + [lamp_post(x, 4.9) for x in (-5, 15)]
    light("SUN", "moon", (0, 0, 30), 0.8, (0.6, 0.72, 1.0), rot=(math.radians(50), 0, math.radians(30)))
    return dict(houses=houses, lamps=lamps)


def lamp_post(x, y, energy=380):
    pole = color("lamp_pole", (0.15, 0.15, 0.16), 0.4)
    box(f"pole_{x}_{y}", (0.12, 0.12, 4.2), (x, y, 2.1), pole, 0.01)
    side = 1 if y < 0 else -1
    head = box(f"lamphead_{x}_{y}", (0.55, 0.28, 0.16), (x, y + side * 0.15, 4.25), color(f"lamp_head_{x}_{y}", (1.0, 0.82, 0.45), 0.3, emit=8.0), 0.02)
    box(f"lampcap_{x}_{y}", (0.6, 0.33, 0.06), (x, y + side * 0.15, 4.36), snow_mat(), 0.02)
    spot = light("SPOT", f"lamp_{x}_{y}", (x, y + side * 0.2, 4.05), energy, (1, 0.78, 0.5), size=0.2, spot=(math.radians(80), 0.5))
    return dict(head=head, spot=spot, mat=head.data.materials[0])


def tree(x, y, s=1.0):
    bark, leaf = color("bark", (0.18, 0.11, 0.07), 0.8), color("leaf", (0.06, 0.14, 0.08), 0.8)
    box(f"trunk_{x}_{y}", (0.35 * s, 0.35 * s, 2.2 * s), (x, y, 1.1 * s), bark, 0.02)
    for n, (w, z) in enumerate(((2.4, 2.6), (1.7, 3.6), (1.0, 4.4))):
        box(f"leaf_{x}_{y}_{n}", (w * s, w * s, 1.0 * s), (x, y, z * s), leaf, 0.05)
        box(f"leafsnow_{x}_{y}_{n}", (w * s * 0.92, w * s * 0.92, 0.14 * s), (x, y, (z + 0.55) * s), snow_mat(), 0.05)


# ---------------------------------------------------------------- light states (ONE table) ---------------------

def _emit(mat, f, strength):
    sock = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    sock.default_value = strength
    sock.keyframe_insert("default_value", frame=f)
    for fc in C.fcurves(mat.node_tree):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"


def _const(idblock):
    for fc in C.fcurves(idblock):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"


def _emit_key(mat, f, strength):
    _emit(mat, f, strength)


def lamp(H, f, on):
    """Switch one porch lamp at full-timeline-free LOCAL frame f (use apply_lights; this is its building block)."""
    _emit(H["bulb_mat"], f, 12.0 if on else 0.0)
    H["lamp_light"].data.energy = 120 if on else 0
    H["lamp_light"].data.keyframe_insert("energy", frame=f)
    for fc in C.fcurves(H["lamp_light"].data):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"


def porch_states():
    """{house: [(full-timeline frame, on)]}. The countdown: far houses go dark from line 16, Hale on her word, every
    lamp on "out" in line 23; after the storm only the narrator's flickers back on (line 35)."""
    a16 = line_frames(16)[2]
    out = {h: [(1, True)] for h in ("nar", "theo", "hale", *[f"n{x}" for x in NEAR_X if x not in (0, -10)], *[f"f{x}" for x in FAR_X if x != 0])}
    for k, h in enumerate(("f-30", "n30", "f30", "n-30", "f20")):  # line 16-17: the street starts going dark
        out[h].append((a16 + 12 + k * 9, False))
    l17 = line_frames(17)
    for k, h in enumerate(("n20", "f-20", "n-20", "f10")):  # "...by January, twenty-two"
        out[h].append((l17[2] + (l17[3] - l17[2]) * (k + 2) // 6, False))
    out["hale"].append((EVENTS["hale_dark"]["frame"], False))
    for h in ("nar", "theo", "n10", "f-10"):  # line 23 "Every light went out. Even mine."
        out[h].append((EVENTS["all_out"]["frame"], False))
    a30, a32 = line_frames(30)[0], line_frames(32)[0]  # lines 30-31: memory montage, the bulb Theo kept changing
    out["nar"] += [(a30, True), (a32, False)]
    fl = EVENTS["porch_flicker"]["frame"]  # line 35: on - off - on - off - ON
    for k, on in enumerate((True, False, True, False, True, False, True)):
        out["nar"].append((fl + (0, 3, 6, 10, 13, 18, 21)[k], on))
    return out


def apply_lights(st, part):
    """Key every porch lamp from the table (re-based to your part), and Theo's bedroom light (dark from line 33,
    after his family moved). Call once in make()."""
    for h, keys in porch_states().items():
        H = st["houses"][h]
        for f, on in sorted(keys):
            lamp(H, max(1, f - part.off), on)
    out_f, back_f = max(1, EVENTS["all_out"]["frame"] - part.off), max(1, line_frames(32)[0] - part.off)
    if EVENTS["all_out"]["frame"] - part.off <= part.last:  # the storm power cut: windows, bedrooms, street lamps
        win = bpy.data.materials.get("win_on_l")
        if win:
            for f, e in ((1, 5.0), (out_f, 0.0), (back_f, 5.0)):
                _emit_key(win, f, e)
        for lp in st["lamps"]:
            for f, on in ((1, True), (out_f, False), (back_f, True)):
                _emit_key(lp["mat"], f, 8.0 if on else 0.0)
                lp["spot"].data.energy = 380 if on else 0
                lp["spot"].data.keyframe_insert("energy", frame=f)
                _const(lp["spot"].data)
        nl = bpy.data.objects["nar_roomlight"].data
        for f, e in ((1, 70), (out_f, 0), (back_f, 70)):
            nl.energy = e
            nl.keyframe_insert("energy", frame=f)
        _const(nl)
    rl = bpy.data.objects["theo_roomlight"].data
    for f, e in sorted(((1, 70), (EVENTS["all_out"]["frame"], 0), (line_frames(32)[0], 70), (line_frames(33)[0], 0))):
        rl.energy = e  # keyed in story order, so an earlier state clamped onto frame 1 is overwritten by the later one
        rl.keyframe_insert("energy", frame=max(1, f - part.off))
    for fc in C.fcurves(rl):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"


def time_of_day(part, sun=None):
    """Night everywhere except: line 21 (morning), 32 (sunrise), 33 (afternoon). Keys world + moon/sun (CONSTANT)."""
    w = bpy.context.scene.world
    bg = w.node_tree.nodes["Background"]
    sun = sun or bpy.data.objects.get("moon")
    looks = {"night": (0.3, 0.8, (0.6, 0.72, 1.0)), "morning": (1.4, 3.0, (0.85, 0.88, 1.0)),
             "dawn": (1.0, 2.2, (1.0, 0.7, 0.5)), "afternoon": (1.6, 3.5, (1.0, 0.93, 0.85))}
    plan = [(1, "night")]
    for ln, look in ((21, "morning"), (22, "night"), (32, "dawn"), (33, "afternoon"), (34, "night")):
        plan.append((line_frames(ln)[0], look))
    for f, look in plan:
        f = f - part.off
        if f < 1 and look != plan[0][1]:
            f = 1
        ws, se, col = looks[look]
        bg.inputs["Strength"].default_value = ws
        bg.inputs["Strength"].keyframe_insert("default_value", frame=max(1, f))
        sun.data.energy, sun.data.color = se, col
        sun.data.keyframe_insert("energy", frame=max(1, f))
        sun.data.keyframe_insert("color", frame=max(1, f))
    th = EVENTS["thunder"]["frame"] - part.off  # lightning: two white flashes on the thunder beat
    if 1 <= th:
        night = looks["night"]
        for f, ws, se in ((th, 4.0, 12.0), (th + 2, night[0], night[1]), (th + 5, 3.0, 9.0), (th + 7, night[0], night[1])):
            bg.inputs["Strength"].default_value = ws
            bg.inputs["Strength"].keyframe_insert("default_value", frame=f)
            sun.data.energy = se
            sun.data.keyframe_insert("energy", frame=f)
    for tgt in (w.node_tree, sun.data):
        for fc in C.fcurves(tgt):
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"


# ---------------------------------------------------------------- interiors ---------------------------------------

def dining():
    """Dining room at x=100. Table centre (100, 100, 0.75) along X; MOM_SEAT (100.9, 99.4) faces +Y (rot_z=pi) toward
    the table; the narrator's seat NAR_SEAT (99.1, 100.6) faces -Y (rot_z=0). The narrator's plate = d["plate"].
    A warm hanging lamp over the table, a window on the back wall (dark outside)."""
    X, Y = 100.0, 100.0
    wall = pbr("beige_wall_001", 0.5, tint=(0.85, 0.8, 0.7))
    box("din_floor", (6, 6, 0.1), (X, Y, -0.05), pbr("laminate_floor_02", 0.6), 0)
    box("din_back", (6, 0.1, 3), (X, Y + 2.5, 1.5), wall, 0)
    box("din_left", (0.1, 6, 3), (X - 3, Y, 1.5), wall, 0)
    box("din_right", (0.1, 6, 3), (X + 3, Y, 1.5), wall, 0)
    box("din_front", (6, 0.1, 3), (X, Y - 3.0, 1.5), wall, 0)
    box("din_cabinet", (1.4, 0.45, 0.9), (X - 1.9, Y + 2.2, 0.45), color("cabinet", (0.35, 0.22, 0.13), 0.5), 0.02)
    box("din_frame_pic", (0.7, 0.03, 0.5), (X - 1.9, Y + 2.44, 1.7), color("pic", (0.3, 0.45, 0.6), 0.6), 0.01)
    box("din_ceiling", (6, 6, 0.1), (X, Y, 3.0), color("ceil", (0.8, 0.8, 0.8), 0.8), 0)
    tw = color("table_wood", (0.4, 0.25, 0.14), 0.5)
    box("table_top", (2.0, 1.1, 0.06), (X, Y, 0.75), tw, 0.02)
    for dx in (-0.9, 0.9):
        for dy in (-0.45, 0.45):
            box(f"table_leg_{dx}_{dy}", (0.07, 0.07, 0.72), (X + dx, Y + dy, 0.36), tw, 0.01)
    box("tablecloth", (1.4, 1.15, 0.01), (X, Y, 0.785), color("cloth", (0.85, 0.85, 0.8), 0.9, fabric=True), 0.0)
    plates = {}
    for k, (px, py) in enumerate(((X + 0.9 - 0.35, Y - 0.3), (X - 0.9 + 0.35, Y + 0.3))):
        plates[k] = box(f"plate_{k}", (0.32, 0.32, 0.02), (px, py, 0.8), color("plate", (0.95, 0.95, 0.95), 0.2), 0.01)
        box(f"food_{k}", (0.16, 0.12, 0.04), (px, py, 0.83), color("food", (0.75, 0.45, 0.2), 0.7), 0.02)
        box(f"fork_{k}", (0.02, 0.18, 0.01), (px + 0.2, py, 0.8), color("steel", (0.75, 0.75, 0.78), 0.2), 0.0)
    for k, (cx, cy) in enumerate(((X + 0.9 - 0.35, Y - 0.85), (X - 0.9 + 0.35, Y + 0.85))):
        box(f"chair_seat_{k}", (0.45, 0.45, 0.05), (cx, cy, 0.46), tw, 0.01)
        box(f"chair_back_{k}", (0.45, 0.05, 0.5), (cx, cy + (-0.22 if k == 0 else 0.22), 0.72), tw, 0.01)
    box("din_window", (1.2, 0.06, 1.1), (X + 1.4, Y + 2.44, 1.6), color("win_night", (0.02, 0.03, 0.06), 0.1), 0.0)
    box("din_winframe", (1.36, 0.05, 1.26), (X + 1.4, Y + 2.47, 1.6), color("frame", (0.9, 0.9, 0.86), 0.5), 0.01)
    box("din_shade", (0.5, 0.5, 0.3), (X, Y, 2.3), color("shade", (0.95, 0.8, 0.55), 0.6, emit=2.0), 0.03)
    light("POINT", "din_lamp", (X, Y, 2.1), 160, WARM, size=0.3)
    light("POINT", "din_fill", (X - 1.5, Y - 2, 2.4), 40, (0.7, 0.75, 0.9), size=1.0)
    return dict(plate=plates[1], mom_plate=plates[0], MOM_SEAT=(X + 0.55, Y - 0.85), NAR_SEAT=(X - 0.55, Y + 0.85))


def classroom():
    """Classroom at x=140: 3 rows x 4 desks facing -Y toward a board at y=96.6. desks[(row, col)] = desk centre;
    a kid sits at a desk at (x, y + 0.45) facing -Y (rot_z=0). The narrator's desk = (1, 1); keep (1, 0) and (1, 2)
    EMPTY (nobody sits next to them)."""
    X, Y = 140.0, 100.0
    wall = pbr("beige_wall_001", 0.5, tint=(0.75, 0.85, 0.8))
    box("cls_floor", (9, 9, 0.1), (X, Y, -0.05), pbr("laminate_floor_02", 0.6), 0)
    for name, size, loc in (("cls_front", (9, 0.1, 3.2), (X, Y - 3.5, 1.6)), ("cls_back", (9, 0.1, 3.2), (X, Y + 4.5, 1.6)),
                            ("cls_l", (0.1, 9, 3.2), (X - 4.5, Y, 1.6)), ("cls_r", (0.1, 9, 3.2), (X + 4.5, Y, 1.6))):
        box(name, size, loc, wall, 0)
    box("cls_ceiling", (9, 9, 0.1), (X, Y, 3.2), color("ceil", (0.85, 0.85, 0.85), 0.8), 0)
    box("board", (3.6, 0.05, 1.2), (X, Y - 3.42, 1.7), color("board", (0.1, 0.25, 0.18), 0.8), 0.01)
    box("board_frame", (3.8, 0.04, 1.4), (X, Y - 3.44, 1.7), color("board_wood", (0.45, 0.3, 0.15), 0.6), 0.01)
    for k in range(3):  # windows with daylight on the left wall
        box(f"cls_win_{k}", (0.05, 1.3, 1.2), (X - 4.44, Y - 1.5 + k * 2.2, 1.8), color("cls_daylight", (0.85, 0.9, 1.0), 0.3, emit=3.0), 0.0)
    light("AREA", "cls_sun", (X - 3.5, Y, 2.4), 400, (1.0, 0.95, 0.88), size=6, rot=(0, math.radians(-70), 0))
    light("AREA", "cls_ceiling_light", (X, Y, 3.1), 300, (0.95, 0.97, 1.0), size=5)
    desk_m, seat_m = color("desk", (0.65, 0.5, 0.32), 0.5), color("seat", (0.2, 0.35, 0.6), 0.5)
    desks = {}
    for r in range(3):
        for c in range(4):
            dx, dy = X - 2.4 + c * 1.6, Y - 1.2 + r * 1.6
            box(f"desk_{r}_{c}", (0.9, 0.55, 0.05), (dx, dy, 0.7), desk_m, 0.01)
            box(f"desk_leg_{r}_{c}", (0.08, 0.4, 0.68), (dx, dy + 0.05, 0.34), desk_m, 0.01)
            box(f"chair_{r}_{c}", (0.42, 0.42, 0.05), (dx, dy + 0.5, 0.42), seat_m, 0.01)
            box(f"chairback_{r}_{c}", (0.42, 0.05, 0.4), (dx, dy + 0.72, 0.65), seat_m, 0.01)
            desks[(r, c)] = (dx, dy)
    return dict(desks=desks)


# ---------------------------------------------------------------- props -------------------------------------------

def flashlight(name, loc=(0, 0, 0), parent=None):
    """A small flashlight pointing along -Y. Returns {root, lens_mat, beam}. Turn it on/off with flash()."""
    root = empty(name, loc)
    body = box(f"{name}_body", (0.07, 0.24, 0.07), (0, 0.06, 0), color("flash_body", (0.12, 0.12, 0.14), 0.35), 0.015, root)
    lens_m = color(f"{name}_lens", (1.0, 0.95, 0.8), 0.2, emit=0.0)
    box(f"{name}_lens", (0.09, 0.03, 0.09), (0, -0.07, 0), lens_m, 0.01, root)
    beam = light("SPOT", f"{name}_beam", (0, -0.1, 0), 0, (1.0, 0.95, 0.85), size=0.02, rot=(math.radians(90), 0, 0), spot=(math.radians(30), 0.3))
    beam.parent = root
    if parent is not None:
        root.parent = parent
    return dict(root=root, lens_mat=lens_m, beam=beam, body=body)


def flash(fl, f, on):
    """Flashlight on/off at frame f (CONSTANT). Two quick flashes = flash on at e1, off 6 frames later, same at e2."""
    _emit(fl["lens_mat"], f, 40.0 if on else 0.0)
    fl["beam"].data.energy = 300 if on else 0
    fl["beam"].data.keyframe_insert("energy", frame=f)
    for fc in C.fcurves(fl["beam"].data):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"


def crate_of_bulbs(name, loc):
    root = empty(name, loc)
    box(f"{name}_crate", (0.55, 0.4, 0.28), (0, 0, 0.14), color("crate_wood", (0.6, 0.45, 0.28), 0.8), 0.01, root)
    glass = color("bulb_glass", (0.95, 0.95, 0.88), 0.15)
    for k in range(6):
        box(f"{name}_bulb{k}", (0.1, 0.1, 0.12), (-0.17 + (k % 3) * 0.17, -0.09 + (k // 3) * 0.18, 0.33), glass, 0.03, root)
    return root


def slippers(name, loc):
    root = empty(name, loc)
    m = color("slipper", (0.85, 0.6, 0.7), 0.9, fabric=True)
    for k, dx in enumerate((-0.09, 0.09)):
        box(f"{name}_{k}", (0.1, 0.24, 0.06), (dx, 0, 0.03), m, 0.025, root)
    return root


def truck(name, loc, rot_z=0.0):
    """A small moving truck facing -X. Animate root location to drive it away."""
    root = empty(name, loc)
    body = color("truck_white", (0.85, 0.85, 0.82), 0.5)
    box(f"{name}_cargo", (3.2, 1.9, 2.0), (0.6, 0, 1.4), body, 0.04, root)
    box(f"{name}_cab", (1.3, 1.8, 1.4), (-1.6, 0, 1.1), color("truck_blue", (0.15, 0.25, 0.5), 0.4), 0.06, root)
    box(f"{name}_windshield", (0.05, 1.5, 0.6), (-2.26, 0, 1.45), color("win_glass_dark", (0.05, 0.07, 0.1), 0.05), 0.0, root)
    tyre = color("tyre", (0.03, 0.03, 0.03), 0.8)
    for wx in (-1.6, 1.4):
        for wy in (-0.95, 0.95):
            box(f"{name}_wheel_{wx}_{wy}", (0.7, 0.25, 0.7), (wx, wy, 0.35), tyre, 0.12, root)
    root.rotation_euler.z = rot_z
    return root


# ---------------------------------------------------------------- weather -----------------------------------------

def _particles(tag, center, size, n, speed, seed, dims, mat, sway=0.0):
    rnd = random.Random(seed)
    me = bpy.data.meshes.new(f"flake_{tag}")
    rx, ry, rz = dims
    v = [(x, y, z) for x in (-rx, rx) for y in (-ry, ry) for z in (-rz, rz)]
    me.from_pydata(v, [], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    me.materials.append(mat)
    root = empty(f"wx_{tag}", (0, 0, 0))
    cx, cy, cz = center
    sx, sy, sz = size
    for k in range(n):
        o = bpy.data.objects.new(f"flake_{tag}_{k}", me)
        bpy.context.collection.objects.link(o)
        o.parent = root
        o.visible_shadow = False
        x, y = cx + (rnd.random() - 0.5) * sx, cy + (rnd.random() - 0.5) * sy
        period = sz / (speed * rnd.uniform(0.8, 1.25)) * FPS
        off = rnd.random() * period
        o.location = (x, y, cz + sz / 2)
        o.keyframe_insert("location", index=2, frame=1 - off)
        o.location.z = cz - sz / 2
        o.keyframe_insert("location", index=2, frame=1 - off + period)
        if sway:
            for i, base in ((0, x), (1, y)):
                amp, sw = rnd.uniform(0.4, 1.0) * sway, rnd.uniform(2.5, 4.5) * FPS
                ph = rnd.random() * sw
                for t, d in ((0, -amp), (sw / 2, amp), (sw, -amp)):
                    o.location[i] = base + d
                    o.keyframe_insert("location", index=i, frame=1 - ph + t)
        for fc in C.fcurves(o):
            if not (fc.data_path == "location" and fc.array_index < 2):
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
            fc.modifiers.new("CYCLES")
    return root


def snowfall(tag, center, size, n=400, seed=1):
    """Gentle snow (calm nights). Returns its root empty: move it away to switch it off (see weather())."""
    return _particles(f"snow{tag}", center, size, n, 0.6, seed, (0.016, 0.016, 0.016),
                      color("flake", (1, 1, 1), 0.5, emit=0.4), sway=0.18)


def rainfall(tag, center, size, n=900, seed=2):
    """Storm rain: thin bright streaks, fast. Returns its root empty."""
    return _particles(f"rain{tag}", center, size, n, 9.0, seed, (0.004, 0.004, 0.22),
                      color("rain", (0.75, 0.8, 0.9), 0.2, emit=0.6))


def weather(part, snow_roots, rain_roots):
    """Snow before the storm and after it; rain from the "storm" word (line 23) until sunrise (line 32).
    Off = the layer's root moved 500 m down (CONSTANT keys)."""
    on, off = EVENTS["rain_on"]["frame"] - part.off, EVENTS["rain_off"]["frame"] - part.off
    for r in snow_roots:
        for f, z in ((1, 0), (max(1, on), -500), (max(1, off), 0)):
            r.location.z = z
            r.keyframe_insert("location", index=2, frame=f)
        constant(r)
    for r in rain_roots:
        for f, z in ((1, -500), (max(1, on), 0), (max(1, off), -500)):
            r.location.z = z
            r.keyframe_insert("location", index=2, frame=f)
        constant(r)


# ---------------------------------------------------------------- cameras (the ONLY way to make one) --------------

def shot(s, name, a, b, loc, target, lens=30, move=(0, 0, 0), push=0.08, orbit=0.0, ease=True):
    """One shot camera for frames a..b with a marker at a. ONE smooth move per shot:
      move  = (dx, dy, dz) metres travelled over the shot (dolly/drift/crane),
      push  = lens change as a fraction (0.08 = 8% slow push-in; negative = pull out),
      orbit = degrees around `target` (arc), optional.
    Eased in/out (no jerk), and refuses anything faster than MAX_SPEED m/s, MAX_TURN deg/s or MAX_ZOOM per shot."""
    secs = (b - a + 1) / FPS
    dist = Vector(move).length
    r = (Vector(loc) - Vector(target)).length
    arc = math.radians(abs(orbit)) * Vector((loc[0] - target[0], loc[1] - target[1])).length
    peak = 1.5 if ease else 1.0  # an eased move peaks ~1.5x its average speed
    assert (dist + arc) / secs * peak <= MAX_SPEED, f"{name}: move {(dist + arc) / secs * peak:.2f} m/s > {MAX_SPEED}"
    assert abs(orbit) / secs * peak <= MAX_TURN, f"{name}: orbit {abs(orbit) / secs * peak:.1f} deg/s > {MAX_TURN}"
    assert abs(push) <= MAX_ZOOM, f"{name}: push {push} > {MAX_ZOOM}"
    cd = bpy.data.cameras.new(name)
    cd.lens, cd.clip_end, cd.clip_start = lens, 400, 0.05
    cam = bpy.data.objects.new(name, cd)
    bpy.context.collection.objects.link(cam)
    tgt = empty(f"{name}_target", target)
    con = cam.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
    keys = 9 if orbit else 2
    c = Vector(target)
    base = Vector(loc) - c
    for k in range(keys):
        u = k / (keys - 1)
        th = math.radians(orbit * u)
        rot = Vector((base.x * math.cos(th) - base.y * math.sin(th), base.x * math.sin(th) + base.y * math.cos(th), base.z))
        cam.location = c + rot + Vector(move) * u
        cam.keyframe_insert("location", frame=a + round((b - a) * u))
        tgt.location = c + Vector(move) * u
        tgt.keyframe_insert("location", frame=a + round((b - a) * u))
    cd.lens = lens
    cd.keyframe_insert("lens", frame=a)
    cd.lens = lens * (1 + push)
    cd.keyframe_insert("lens", frame=b)
    for o in (cam, tgt, cd):
        for fc in C.fcurves(o):
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER" if ease and keys == 2 else ("LINEAR" if keys > 2 else "BEZIER")
                kp.easing = "AUTO"
    if keys > 2 and ease:  # an orbit: linear through the arc points, eased only at its two ends
        for o in (cam, tgt):
            for fc in C.fcurves(o):
                kps = fc.keyframe_points
                kps[0].interpolation = kps[-2].interpolation = "BEZIER"
    look.dof(cam, tgt, fstop=2.0 if lens >= 45 else (2.8 if lens >= 30 else 4.5))  # focus on the shot's target
    s.timeline_markers.new(name, frame=a).camera = cam
    cam["shot"] = (a, b)
    return cam


def continue_shot(s, prev, name, a, b):
    """A new shot that continues `prev` invisibly (same spot, angle, lens AND speed at the cut): for "same view, next
    line" cuts. Call after prev is fully keyed."""
    vals = []
    for fr in (a - 2, a - 1):
        s.frame_set(fr)
        vals.append((prev.matrix_world.copy(), prev.data.lens))
    (m0, l0), (m1, l1) = vals
    dv, dl = m1.translation - m0.translation, l1 - l0
    cd = bpy.data.cameras.new(name)
    cd.clip_end, cd.clip_start = 400, 0.05
    cam = bpy.data.objects.new(name, cd)
    bpy.context.collection.objects.link(cam)
    cam.rotation_euler = m1.to_euler()
    n = b - a + 1
    C.key(cam, "location", a, m1.translation + dv)
    C.key(cam, "location", b, m1.translation + dv * n)
    C.key(cd, "lens", a, l1 + dl)
    C.key(cd, "lens", b, l1 + dl * n)
    C.linear(cam)
    C.linear(cd)
    if prev.data.dof.use_dof:  # same blur and focus as the shot it continues
        look.dof(cam, prev.data.dof.focus_object, prev.data.dof.aperture_fstop)
    s.timeline_markers.new(name, frame=a).camera = cam
    cam["shot"] = (a, b)
    s.frame_set(1)
    return cam


def check_cameras(s, min_front=0.6, min_any=0.2):
    """Refuse a camera that starts/ends inside geometry or right against it (looking into a wall or prop closer than
    min_front m, or anything closer than min_any m around it). Weather particles are ignored."""
    bad = []
    for m in s.timeline_markers:
        cam = m.camera
        if not cam or "shot" not in cam:
            continue
        a, b = cam["shot"]
        for fr in (a, (a + b) // 2, b):
            s.frame_set(fr)
            dg = bpy.context.evaluated_depsgraph_get()
            o = cam.matrix_world.translation
            fwd = cam.matrix_world.to_3x3() @ Vector((0, 0, -1))
            dirs = [(fwd, min_front)] + [(Vector(d), min_any) for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
            for d, lim in dirs:
                hit, loc, _n, _i, ob, _mx = s.ray_cast(dg, o, d.normalized(), distance=lim)
                if hit and not ob.name.startswith("flake_") and not ob.hide_render:
                    bad.append(f"{cam.name} @ {fr}: {ob.name} only {(loc - o).length:.2f} m away")
    s.frame_set(1)
    assert not bad, "camera too close to geometry:\n  " + "\n  ".join(bad[:20])
    print(f"check_cameras: {len([m for m in s.timeline_markers if m.camera])} cameras OK", flush=True)


def clear_flakes_near_cameras(s, r=2.5):
    """Hide weather particles that pass within r m (ground plan) of a shot camera's path (giant blocks at the lens)."""
    flakes = [o for o in bpy.data.objects if o.type == "MESH" and o.data.name.startswith("flake_")]
    starts = sorted(m.frame for m in s.timeline_markers if m.camera)
    hid = set()
    for m in s.timeline_markers:
        if not m.camera:
            continue
        end = min([f for f in starts if f > m.frame] + [s.frame_end + 1]) - 1
        rr = max(r, 0.055 * m.camera.data.lens)  # zoomed lenses magnify flakes: ~4 m clear at 75 mm
        for fr in (m.frame, (m.frame + end) // 2, end):
            s.frame_set(fr)
            c = m.camera.matrix_world.translation.xy
            for o in flakes:
                if (o.matrix_world.translation.xy - c).length < rr:
                    hid.add(o)
    # no snow under porch roofs or inside houses (it read as snow falling indoors)
    roofs = []
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.name.endswith(("_porchroof", "_house", "_body", "_body2", "_room_floor")):
            xs = [(ob.matrix_world @ v.co).x for v in ob.data.vertices]
            ys = [(ob.matrix_world @ v.co).y for v in ob.data.vertices]
            roofs.append((min(xs) - 0.1, max(xs) + 0.1, min(ys) - 0.1, max(ys) + 0.1))
    for o in flakes:
        x, y = o.matrix_world.translation.x, o.matrix_world.translation.y
        if any(a <= x <= b and c <= y <= d for a, b, c, d in roofs):
            hid.add(o)
    for o in hid:
        o.hide_render = True
    s.frame_set(1)
    print(f"clear_flakes_near_cameras: hid {len(hid)} of {len(flakes)}", flush=True)


def finish(s, part):
    """Call at the very end of make(): frame range, weather cleanup + camera safety checks."""
    s.frame_start, s.frame_end = 1, part.last
    clear_flakes_near_cameras(s)
    check_cameras(s)
