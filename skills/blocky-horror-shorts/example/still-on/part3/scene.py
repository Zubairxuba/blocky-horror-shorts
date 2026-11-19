"""Still On, PART 3 (lines 27-38): the reveal and the ending.
Run: blender -b -P part3/scene.py -- --frames 10,200   (or --preview)."""
import math, random, sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))  # the story folder
import shared as S          # noqa: E402
import characters as C      # noqa: E402
import bpy                  # noqa: E402
from mathutils import Vector  # noqa: E402
from common import box, color, empty, light  # noqa: E402

PI = math.pi


def R(*deg):
    return tuple(math.radians(d) for d in deg)


# ------------------------------------------------------------------ small helpers ---------------------------------

def vis(j, a, b):
    S.visible(j, 1, False)
    S.visible(j, a, True)
    S.visible(j, b + 1, False)


def actor(name, look, a, b, loc, rz, face, scale=1.0, lean=0.0):
    """A character visible only over a..b, breathing, facing rz (0 = -Y, pi = +Y), leaning `lean` degrees forward."""
    j = S.char(name, look, loc, rz)
    r = j["root"]
    if scale != 1.0:
        r.scale = tuple(v * scale for v in r.scale)
    r.rotation_euler = (math.radians(lean), 0, rz)
    vis(j, a, b)
    C.breathe(j, a, b)
    return j


def arm(j, side, f, deg, yaw=0.0, roll=0.0):
    C.key(j[f"{side}_shoulder"], "rotation_euler", f, R(deg, roll, yaw))


def neck(j, f, x=0.0, y=0.0, z=0.0):
    C.key(j["neck"], "rotation_euler", f, R(x, y, z))


def root_rot(j, f, lean, rz):
    C.key(j["root"], "rotation_euler", f, (math.radians(lean), 0, rz))


def smooth(o):
    """Eased (Bezier, auto) keys on every curve of o."""
    for fc in C.fcurves(o):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"


def tremble(o, a, b, base, amp, every=3, seed=0):
    rnd = random.Random(seed)
    for f in range(a, b + 1, every):
        C.key(o, "rotation_euler", f, R(*(v + rnd.uniform(-amp, amp) for v in base)))


def aim(o, target):
    o.rotation_euler = (Vector(target) - Vector(o.location)).to_track_quat("-Z", "Y").to_euler()


def slight(kind, name, loc, energy, rgb, a, b, size=1.0, target=None, spot=None):
    """A light that is only on over frames a..b (CONSTANT keys): per-shot fills so shots do not light each other."""
    o = light(kind, name, loc, 0, rgb, size=size, spot=spot)
    if kind == "AREA":
        o.data.size = size
    if target is not None:
        aim(o, target)
    for f, e in ((1, 0), (a, energy), (b + 1, 0)):
        o.data.energy = e
        o.data.keyframe_insert("energy", frame=f)
    S._const(o.data)
    return o


def pulse(o, pairs):
    """Keys a light's energy at [(frame, energy)], CONSTANT."""
    for f, e in pairs:
        o.data.energy = e
        o.data.keyframe_insert("energy", frame=f)
    S._const(o.data)


def cone_mat(name, L):
    """A faint visible light shaft: brightest at the lens, fading with length, soft edges. gain socket is keyed."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    N, lk = nt.nodes.new, nt.links.new
    tc, sep, mr = N("ShaderNodeTexCoord"), N("ShaderNodeSeparateXYZ"), N("ShaderNodeMapRange")
    geo, dot, ab, m1, m2 = N("ShaderNodeNewGeometry"), N("ShaderNodeVectorMath"), N("ShaderNodeMath"), N("ShaderNodeMath"), N("ShaderNodeMath")
    tr, em, mix, out = N("ShaderNodeBsdfTransparent"), N("ShaderNodeEmission"), N("ShaderNodeMixShader"), N("ShaderNodeOutputMaterial")
    lk(tc.outputs["Object"], sep.inputs["Vector"])
    lk(sep.outputs["Z"], mr.inputs["Value"])
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = -L / 2, L / 2
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1.0, 0.0
    dot.operation = "DOT_PRODUCT"
    lk(geo.outputs["Normal"], dot.inputs[0])
    lk(geo.outputs["Incoming"], dot.inputs[1])
    ab.operation = "ABSOLUTE"
    lk(dot.outputs["Value"], ab.inputs[0])
    m1.operation = "MULTIPLY"
    lk(mr.outputs["Result"], m1.inputs[0])
    lk(ab.outputs["Value"], m1.inputs[1])
    m2.operation = "MULTIPLY"
    lk(m1.outputs["Value"], m2.inputs[0])
    m2.inputs[1].default_value = 0.0
    em.inputs["Color"].default_value = (1.0, 0.93, 0.75, 1)
    em.inputs["Strength"].default_value = 2.0
    lk(m2.outputs["Value"], mix.inputs["Fac"])
    lk(tr.outputs["BSDF"], mix.inputs[1])
    lk(em.outputs["Emission"], mix.inputs[2])
    lk(mix.outputs["Shader"], out.inputs["Surface"])
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "BLENDED"
    return m, m2.inputs[1]


def sky_dome(name, a, b, horizon, zenith, strength=1.0):
    """The camera sees a fixed dark sky (central world), so dawn/afternoon get a gradient sky dome over a..b."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=200, segments=32, ring_count=16, location=(0, 0, 0))
    o = bpy.context.active_object
    o.name = name
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    tc, sep, ramp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeSeparateXYZ"), nt.nodes.new("ShaderNodeValToRGB")
    em, out = nt.nodes.new("ShaderNodeEmission"), nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    el = ramp.color_ramp.elements
    el[0].position, el[0].color = 0.5, (*horizon, 1)
    el[1].position, el[1].color = 0.85, (*zenith, 1)
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    o.data.materials.append(m)
    o.visible_shadow = False
    vis(o, a, b)
    return o


def torch(j, look, name, a, b, side="l", cone=0.0, power=300):
    """A flashlight in a character's hand. S.flashlight's beam points BACKWARDS (+Y), so it is turned round here.
    cone > 0 adds a faint visible beam (a translucent cone, length in metres) for flashes seen from behind."""
    fl = S.flashlight(name)
    fl["beam"].rotation_euler = R(-90, 0, 0)
    fl["beam"].data.spot_size = math.radians(40)
    ah = C.LOOKS[look]["arm"][1]
    fl["root"].parent = j[f"{side}_shoulder"]
    fl["root"].location = (0, -0.02, -(ah * 0.875 + 0.06))
    fl["root"].rotation_euler = R(90, 0, 0)
    fl["power"] = power
    if cone:
        sc = j["root"].scale.x
        L = cone / sc
        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.03, radius2=L * 0.075, depth=L, location=(0, 0, 0))
        o = bpy.context.active_object
        o.name = f"{name}_cone"
        m, gain = cone_mat(f"{name}_cone", L)
        o.data.materials.append(m)
        o.parent = fl["root"]
        o.rotation_euler = R(90, 0, 0)
        o.location = (0, -0.1 - L / 2, 0)
        o.visible_shadow = False
        fl["cone"], fl["cone_mat"] = gain, m
    vis(fl, a, b)
    lit(fl, 1, False)
    return fl


def lit(fl, f, on):
    S._emit(fl["lens_mat"], f, 40.0 if on else 0.0)
    d = fl["beam"].data
    d.energy = fl.get("power", 300) if on else 0
    d.keyframe_insert("energy", frame=f)
    S._const(d)
    if "cone" in fl:
        fl["cone"].default_value = 0.5 if on else 0.0
        fl["cone"].keyframe_insert("default_value", frame=f)
        S._const(fl["cone_mat"].node_tree)


def flash2(fl, e1, e2):
    for f, on in ((e1, True), (e1 + 6, False), (e2, True), (e2 + 6, False)):
        lit(fl, f, on)


def place(o, f, loc):
    o.location = loc
    o.keyframe_insert("location", frame=f)


def const_keys(o):
    for fc in C.fcurves(o):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"


def hide_posts(spans):
    """Porch corner posts that would stand in front of the lens in oblique shots: hidden over the (a, b) spans."""
    for nm in ("nar_post_1.2", "nar_post_-1.2"):
        post = bpy.data.objects[nm]
        keys = {1: False}
        for a, b in spans:
            keys[a], keys[b + 1] = True, False
        for f, h in sorted(keys.items()):
            post.hide_render = h
            post.keyframe_insert("hide_render", frame=f)


# ------------------------------------------------------------------ the narrator's door ---------------------------

def hardware(NAR):
    """The shared door knob is parented with the door pivot's offset (it floats far away): hide it and build a real
    lever handle that turns, plus a dark doorway behind the door so an open door shows a hall, not brick."""
    NAR["knob"].hide_render = True
    D = NAR["door"]
    x, fy = NAR["x"], NAR["front_y"]
    brass = color("brass3", (0.8, 0.62, 0.25), 0.25)
    void = color("door_void", (0.012, 0.012, 0.016), 1.0)
    box("door_void", (1.0, 0.012, 2.1), (x, fy + 0.0055, S.PORCH_Z + 1.05), void, 0.0)
    bpy.context.view_layer.update()
    kx, ky, kz = x + 0.38, fy + 0.105, S.PORCH_Z + 1.0
    box("door_rose", (0.1, 0.02, 0.1), (kx, ky - 0.0, kz), brass, 0.006, D)
    hk = empty("door_lever_pivot", (kx, ky + 0.012, kz), D)
    bpy.context.view_layer.update()
    box("door_lever", (0.17, 0.035, 0.035), (kx - 0.065, ky + 0.025, kz), brass, 0.008, hk)
    return hk


def lever(hk, f, deg):
    C.key(hk, "rotation_euler", f, R(0, deg, 0))


# ------------------------------------------------------------------ flashback set (line 29) -----------------------

FB = (300.0, 0.0)


def flashback_set(a, b):
    """The narrator's hall in the blackout, six years ago, at x=300: cold and blue. Camera stands inside, the door
    (hinged, opens outward) leads to a dark rainy porch. Returns handles."""
    X = FB[0]
    wall = color("fb_wall", (0.17, 0.2, 0.28), 0.9)
    wall2 = color("fb_wall2", (0.12, 0.15, 0.22), 0.9)
    wood = color("fb_wood", (0.2, 0.15, 0.12), 0.7)
    trim = color("fb_trim", (0.45, 0.5, 0.6), 0.5)
    snow = S.snow_mat()
    # hall (x +-2, y -3.2..0, z 0..2.9) with a doorway (w 1.0, h 2.6) in the front wall at y=0
    box("fb_floor", (4.2, 3.4, 0.1), (X, -1.6, -0.05), color("fb_floor", (0.22, 0.16, 0.12), 0.5), 0.0)
    box("fb_ceil", (4.2, 3.4, 0.1), (X, -1.6, 2.95), wall2, 0.0)
    box("fb_back", (4.2, 0.1, 3.0), (X, -3.25, 1.45), wall, 0.0)
    for sx in (-2.05, 2.05):
        box(f"fb_side{sx}", (0.1, 3.4, 3.0), (X + sx, -1.6, 1.45), wall, 0.0)
    box("fb_front_l", (1.6, 0.2, 3.0), (X - 1.3, 0.0, 1.45), wall, 0.0)
    box("fb_front_r", (1.6, 0.2, 3.0), (X + 1.3, 0.0, 1.45), wall, 0.0)
    box("fb_front_t", (1.0, 0.2, 0.4), (X, 0.0, 2.8), wall, 0.0)
    for k, (sx, sz, px, pz) in enumerate(((0.07, 2.62, -0.53, 1.31), (0.07, 2.62, 0.53, 1.31), (1.14, 0.07, 0.0, 2.62))):
        box(f"fb_dframe{k}", (sx, 0.26, sz), (X + px, 0.0, pz), trim, 0.005)
    # skirting, rug, picture frames, a coat stand with a coat, shoes, a little table with a candle
    box("fb_skirt_b", (4.1, 0.03, 0.14), (X, -3.18, 0.07), trim, 0.005)
    for sx in (-1.98, 1.98):
        box(f"fb_skirt{sx}", (0.03, 3.2, 0.14), (X + sx, -1.6, 0.07), trim, 0.005)
    box("fb_rug", (1.5, 2.0, 0.015), (X - 0.1, -1.3, 0.008), color("fb_rug", (0.3, 0.12, 0.14), 0.95, fabric=True), 0.004)
    for k, (px, pz, w, h) in enumerate(((-1.5, 1.75, 0.45, 0.6), (-0.95, 1.95, 0.3, 0.38), (1.35, 1.8, 0.5, 0.4))):
        box(f"fb_pic{k}", (w, 0.025, h), (X + px, -0.11, pz), wood, 0.01)
        box(f"fb_picin{k}", (w - 0.08, 0.015, h - 0.08), (X + px, -0.1, pz), color(f"fb_pic{k}", (0.22 + 0.06 * k, 0.3, 0.38), 0.6), 0.0)
    box("fb_pole", (0.05, 0.05, 1.9), (X + 1.2, -0.5, 0.95), wood, 0.01)
    for k in range(3):
        box(f"fb_hook{k}", (0.03, 0.18, 0.03), (X + 1.2, -0.5 + (-0.09 if k == 0 else 0.0), 1.55 + 0.12 * k), wood, 0.005)
    box("fb_coat", (0.34, 0.16, 0.7), (X + 1.2, -0.68, 1.15), color("fb_coat", (0.35, 0.12, 0.1), 0.9, fabric=True), 0.04)
    for k, dx in enumerate((-0.12, 0.12)):
        box(f"fb_shoe{k}", (0.1, 0.24, 0.08), (X - 1.4 + dx, -0.5, 0.04), color("fb_shoe", (0.1, 0.1, 0.12), 0.5), 0.02)
    box("fb_table", (0.9, 0.35, 0.05), (X - 1.15, -0.7, 0.7), wood, 0.01)
    for dx in (-0.4, 0.4):
        box(f"fb_tleg{dx}", (0.05, 0.05, 0.68), (X - 1.15 + dx, -0.7, 0.34), wood, 0.005)
    box("fb_candle", (0.06, 0.06, 0.16), (X - 1.15, -0.7, 0.8), color("fb_candle", (0.9, 0.88, 0.8), 0.6), 0.01)
    flame = box("fb_flame", (0.025, 0.025, 0.05), (X - 1.15, -0.7, 0.915), color("fb_flame", (1.0, 0.7, 0.3), 0.3, emit=30.0), 0.005)
    cl = light("POINT", "fb_candle_light", (X - 1.15, -0.65, 0.95), 14, (1.0, 0.65, 0.3), size=0.05)
    rnd = random.Random(4)
    for f in range(a, b + 1, 3):
        cl.data.energy = 14 * rnd.uniform(0.6, 1.25)
        cl.data.keyframe_insert("energy", frame=f)
    # porch outside, dead lamp, snowy yard, a pale backdrop so the shade reads as a silhouette
    box("fb_deck", (4.4, 3.0, 0.1), (X, 1.7, -0.05), color("fb_deck", (0.28, 0.2, 0.15), 0.7), 0.01)
    box("fb_ground", (60, 40, 0.3), (X, 22, -0.25), snow, 0.0)
    box("fb_back", (30, 0.4, 9), (X, 11.5, 4.3), color("fb_backdrop", (0.42, 0.5, 0.62), 0.9), 0.0)
    for sx in (-2.1, 2.1):
        box(f"fb_post{sx}", (0.14, 0.14, 2.9), (X + sx, 2.4, 1.45), trim, 0.01)
    box("fb_porchroof", (4.8, 2.4, 0.14), (X, 1.4, 3.0), trim, 0.02)
    box("fb_lampbase", (0.18, 0.08, 0.3), (X + 0.95, 0.16, 2.0), color("fb_lamp", (0.1, 0.1, 0.1), 0.4), 0.01)
    box("fb_bulb", (0.12, 0.12, 0.16), (X + 0.95, 0.24, 1.98), color("fb_deadbulb", (0.2, 0.2, 0.22), 0.3), 0.03)
    door = box("fb_door", (1.0, 0.06, 2.6), (X, 0.04, 1.3), color("fb_doorc", (0.22, 0.06, 0.05), 0.5), 0.02)
    S.hinged(door, (X - 0.5, 0.04, 0.0))
    kn = box("fb_knob", (0.07, 0.07, 0.07), (X + 0.38, -0.03, 0.92), color("fb_brass", (0.75, 0.6, 0.28), 0.25), 0.02)
    kn.parent = door
    bpy.context.view_layer.update()
    kn.matrix_parent_inverse = door.matrix_world.inverted()
    # lights: blue night through the doorway, a faint hall fill, outside rim for the silhouette
    key = slight("AREA", "fb_key", (X + 0.5, 7.0, 4.2), 2600, (0.5, 0.65, 1.0), a, b, size=7, target=(X, 1.2, 1.3))
    fill = slight("AREA", "fb_fill", (X + 0.4, -3.0, 2.4), 140, (0.45, 0.58, 1.0), a, b, size=2.5, target=(X + 0.2, -0.5, 0.8))
    back = slight("AREA", "fb_back", (X + 0.5, 3.2, 3.0), 800, (0.55, 0.7, 1.0), a, b, size=3, target=(X + 0.1, 0.3, 1.0))
    rain = S.rainfall("fb", (X, 5.2, 2.4), (5.0, 5.2, 5.0), 320, seed=5)
    for f, z in ((1, -500), (a, 0), (b + 1, -500)):
        rain.location.z = z
        rain.keyframe_insert("location", index=2, frame=f)
    S.constant(rain)
    return dict(door=door, key=key, fill=fill, back=back)


# ------------------------------------------------------------------ make ------------------------------------------

def make(s, p):
    st = S.street()
    Hs = st["houses"]
    NAR, THEO = Hs["nar"], Hs["theo"]
    S.apply_lights(st, p)
    S.time_of_day(p)
    snow = S.snowfall("a", (0, 1.45, 4), (40, 21.1, 8), 1500)  # y > -9.1: none under the porch roof or in the rooms
    rain = S.rainfall("a", (0, -5, 3), (14, 8, 6), 900)
    S.weather(p, [snow], [rain])
    sh = {n: p.shot(n) for n in range(27, 39)}
    A = {n: v[0] for n, v in sh.items()}
    A_32 = A[32]
    B = {n: v[1] for n, v in sh.items()}
    hk = hardware(NAR)
    win = bpy.data.materials.get("win_on_l")
    if win:  # blackout: unlit windows must not keep their orange base colour (lines 27-31)
        bc = win.node_tree.nodes["Principled BSDF"].inputs["Base Color"]
        orange = tuple(bc.default_value)
        for f, c in ((1, (0.03, 0.04, 0.07, 1)), (A_32, orange)):
            bc.default_value = c
            bc.keyframe_insert("default_value", frame=f)
        S._const(win.node_tree)
    g = bpy.data.materials.get("glass_l")
    if g:  # the bedroom lamp reflected as a round "moon" in the pane: soften it
        g.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.08
    # memory (lines 30-31): the night of the bulb was snowy, not stormy
    for root, on_z, off_z in ((snow, 0, -500), (rain, -500, 0)):
        for f, z in ((A[30], on_z), (A[32], off_z)):
            root.location.z = z
            root.keyframe_insert("location", index=2, frame=f)
        S.constant(root)

    # ============================================================ 27: the door, the shout
    a, b = A[27], B[27]
    dont = p.ev("dont")
    w_reach, w_knob, w_theo, w_scr = p.word(27, "reached"), p.word(27, "knob"), p.word(27, "theo"), p.word(27, "screamed")
    shade = actor("SH27", "shade", a, b, (0.39, -9.18, 0.5), 0.0, "thing", lean=12)
    C.faces_over(shade, a, b, "thing")
    arm(shade, "r", a, -70)
    arm(shade, "r", a + 22, -6)
    arm(shade, "l", a, 2)
    neck(shade, a, 44)
    neck(shade, a + 40, 46, 5, -4)
    neck(shade, dont + 10, 44, -4, 4)
    neck(shade, b, 45, 2, 0)
    th = actor("TH27", "theo", a, b, (-0.7, -10.1, 0.5), 0.716, "kid_scared")
    C.faces_over(th, a, dont - 1, "kid_scared", seed=3)
    C.faces_over(th, dont, dont + 17, "kid_shout", blink=False)
    C.faces_over(th, dont + 18, b, "kid_scared", seed=4)
    fl27 = torch(th, "theo", "T27", a, b, "l", power=110)
    lit(fl27, a, True)
    arm(th, "l", a, -86)
    arm(th, "l", dont - 6, -84)
    arm(th, "l", dont, -98)
    arm(th, "l", dont + 20, -88)
    arm(th, "r", a, 4)
    arm(th, "r", dont - 5, 6)
    arm(th, "r", dont + 2, -35)
    arm(th, "r", dont + 24, -10)
    root_rot(th, a, 0, 0.716)
    root_rot(th, w_scr, 0, 0.716)
    root_rot(th, dont - 8, -4, 0.716)  # a gasp: leans back
    root_rot(th, dont + 1, 11, 0.716)  # the shout: lunges at the door
    root_rot(th, dont + 26, 3, 0.716)
    root_rot(th, b, 3, 0.716)
    neck(th, a, 4, 0, -30)  # head turned toward the shade (to his right)
    neck(th, dont - 8, -8, 0, -22)
    neck(th, dont + 1, 6, 0, 8)  # the shout is at the door
    neck(th, b, 2, 0, -4)
    tremble(fl27["root"], a, dont - 9, (90, 0, 0), 0.9, 3, 1)
    tremble(fl27["root"], dont + 24, b, (90, 0, 0), 0.7, 3, 2)
    # the narrator's hand turns the knob, the door cracks, the shout, it eases shut
    lever(hk, a, 0)
    lever(hk, w_reach, 0)
    lever(hk, w_knob, -42)
    lever(hk, dont + 6, -42)
    lever(hk, dont + 22, 0)
    D = NAR["door"]
    for f, d in ((a, 0), (w_theo, 0), (w_scr + 4, 3.5), (dont - 2, 6.0), (dont + 4, 6.0), (dont + 34, 0.0)):
        C.key(D, "rotation_euler", f, R(0, 0, d))
    slight("AREA", "f27_fill", (4.0, -8.8, 2.6), 40, (0.55, 0.68, 1.0), a, b, size=3, target=(-0.4, -10.0, 1.3))
    cam27 = S.shot(s, "c27", a, b, (4.7, -9.5, 1.3), (-0.5, -10.2, 1.5), 30, move=(-0.3, 0.0, 0.0), push=0.28, orbit=0)

    # ============================================================ 28: Theo talks to the door
    a, b = A[28], B[28]
    th = actor("TH28", "theo", a, b, (-0.7, -9.5, 0.5), 0.47, "kid_sad")
    t1 = (p.word(28, "you"), p.word(28, "it") + 9)
    t2 = (p.word(28, "six"), p.word(28, "ago") + 11)
    C.faces_over(th, a, b, "kid_sad", talk=[t1, t2], seed=7)
    fl28 = torch(th, "theo", "T28", a, b, "l")
    lit(fl28, a, True)
    arm(th, "l", a, -74)
    arm(th, "l", b, -80)
    arm(th, "r", a, 3)
    arm(th, "r", t2[0] - 2, 3)
    arm(th, "r", t2[0] + 8, -14)
    arm(th, "r", b, 0)
    neck(th, a, 2, 0, 6)
    neck(th, t1[0], -4, 0, 12)
    neck(th, t2[0] - 6, 6, 0, 6)  # head drops on "Six years"
    neck(th, b, 2, 0, 8)
    tremble(fl28["root"], a, b, (90, 0, 0), 0.5, 4, 5)
    slight("AREA", "f28_fill", (1.1, -9.4, 2.3), 30, (0.6, 0.72, 1.0), a, b, size=2, target=(-0.7, -9.5, 1.5))
    slight("AREA", "f28_rim", (-2.5, -8.6, 2.2), 25, (0.7, 0.8, 1.0), a, b, size=2, target=(-0.7, -9.5, 1.5))
    S.shot(s, "c28", a, b, (0.84, -10.2, 1.5), (-0.7, -9.55, 1.6), 44, move=(0.0, 0.1, 0.0), push=0.1)

    # ============================================================ 29: flashback, the blackout
    a, b = A[29], B[29]
    fb = flashback_set(a, b)
    X = FB[0]
    kid = actor("NAR29", "nar", a, b, (X + 0.28, -0.42, 0.0), PI, "kid", scale=0.8)
    C.faces_over(kid, a, b, "kid", seed=11)
    w_hand, w_kn, w_knocks = p.word(29, "hand"), p.word(29, "knob"), p.word(29, "knocks")
    arm(kid, "l", a, 0)
    arm(kid, "l", p.word(29, "my") + 2, 0)
    arm(kid, "l", w_hand + 4, -112)
    arm(kid, "l", w_kn + 14, -104)
    arm(kid, "r", a, 0)
    neck(kid, a)
    neck(kid, w_knocks - 4, 0, 0, 0)
    neck(kid, w_knocks + 2, 4, 0, 6)  # flinches at the knocks
    neck(kid, w_kn, 2, 0, 0)
    sd = actor("SH29", "shade", a, b, (X + 0.0, 1.15, 0.0), 0.0, "thing")
    C.faces_over(sd, a, b, "thing")
    sd["root"].location = (X, 2.4, 0)  # waits out in the rain, steps up to the door as it opens
    C.key(sd["root"], "location", a, (X, 2.4, 0))
    C.key(sd["root"], "location", w_kn - 8, (X, 2.4, 0))
    C.key(sd["root"], "location", w_kn + 12, (X, 1.15, 0))
    arm(sd, "l", a, 0)
    arm(sd, "l", w_kn + 4, 0)
    arm(sd, "l", w_kn + 14, -20)
    arm(sd, "l", b, -53)
    arm(sd, "r", a, 0)
    neck(sd, a, 0, 0, 0)
    neck(sd, b, 14, 0, 0)  # the head dips toward her
    # door: three silent knocks (shudders), then the lever turns and it swings out
    fbd = fb["door"]
    for k, f in enumerate((w_knocks - 1, w_knocks + 8, w_knocks + 18)):
        for ff, d in ((f - 1, 0.0), (f, 1.6), (f + 2, 0.0)):
            C.key(fbd, "rotation_euler", ff, R(0, 0, d))
        p.foley(f, "knock1", 0.22)
    for f, d in ((w_kn - 8, 0.0), (w_kn - 2, 4.0), (w_kn + 4, 20.0), (b, 70.0)):
        C.key(fbd, "rotation_euler", f, R(0, 0, d))
    # the blue "pop" of the memory on the whoosh
    rm = p.ev("remember")
    pulse(fb["fill"], [(1, 0), (a, 140), (rm, 900), (rm + 3, 140), (rm + 6, 500), (rm + 9, 140), (b + 1, 0)])
    pulse(fb["back"], [(1, 0), (a, 800), (rm, 2600), (rm + 3, 800), (rm + 6, 1800), (rm + 9, 800), (b + 1, 0)])
    S.shot(s, "c29", a, b, (X + 0.25, -2.95, 1.0), (X + 0.0, 0.2, 1.3), 22, move=(-0.03, 0.35, 0.0), push=0.06)

    # ============================================================ 30: the bulb (memory), lamp on, snow
    a, b = A[30], B[30]
    wood = color("ladder", (0.5, 0.36, 0.22), 0.7)
    lad = [box("ladder_top", (0.5, 0.34, 0.05), (0.51, -10.62, 1.175), wood, 0.01),
           box("ladder_mid", (0.5, 0.5, 0.05), (0.51, -10.55, 0.84), wood, 0.01)]
    for dx in (-0.22, 0.22):
        for yy in (-10.77, -10.47):
            lad.append(box(f"ladder_leg_{dx}_{yy}", (0.05, 0.05, 0.68), (0.51 + dx, yy, 0.84), wood, 0.005))
    for o in lad:
        S.visible(o, 1, False)
        S.visible(o, a, True)
        S.visible(o, B[31] + 1, False)
    crate30 = S.crate_of_bulbs("CR30", (0, 0, 0))  # (group roots must start at the origin: children are baked in world space)
    crate30.location, crate30.rotation_euler.z = (-0.35, -10.3, 0.5), 0.25
    vis(crate30, a, B[31])
    th = actor("TH30", "theo", a, b, (0.51, -10.6, 1.2), 0.0, "kid_sad_smile")
    C.faces_over(th, a, b, "kid_sad_smile", seed=13)
    bulb = box("bulb_new", (0.07, 0.07, 0.11), (0, 0, 0), color("bulb_glass", (0.95, 0.95, 0.88), 0.15), 0.03)
    vis(bulb, a, b)
    bulb.parent = th["l_shoulder"]
    bulb.location = (0, 0, -0.66)
    arm(th, "l", a, -146)
    arm(th, "l", a + 62, -149)
    arm(th, "l", a + 82, -40)
    arm(th, "l", b, -20)
    arm(th, "r", a, 4)
    arm(th, "r", b, 4)
    for f, z in ((a, 0), (a + 20, 200), (a + 44, 400), (a + 66, 560)):
        C.key(bulb, "rotation_euler", f, R(0, 0, z))
    for f, x in ((a, -14), (a + 60, -18), (a + 84, -4), (b, 8)):
        neck(th, f, x, 0, 0)
    slight("AREA", "f30_fill", (2.6, -7.0, 2.2), 30, (0.55, 0.68, 1.0), a, b, size=3, target=(0.5, -10.5, 1.5))
    S.shot(s, "c30", a, b, (2.8, -7.5, 1.4), (0.6, -10.5, 1.85), 32, move=(-0.2, 0.0, 0.1), push=0.08)

    # ============================================================ 31: the narrator comes home (memory)
    a, b = A[31], B[31]
    nar = actor("NAR31", "nar", a, b, (0.35, -6.3, 0.0), 0.0, "kid")
    C.faces_over(nar, a, b, "kid", seed=17)
    end = a + 50
    falls = C.walk_bounce(nar, a, end, (0.35, -6.3, 0.0), (0.35, -7.85, 0.0), steps_per_sec=1.9)
    for lf in ("l_hip", "r_hip", "l_shoulder", "r_shoulder"):
        C.key(nar[lf], "rotation_euler", end + 7, (0, 0, 0))
    for f in falls:
        if a <= f <= end:
            p.foley(f, "step", 0.2)
    for f, x in ((end, 0), (end + 8, 0), (end + 34, -34), (b, -36)):
        neck(nar, f, x, 0, 0)
    slight("AREA", "f31_fill", (-2.4, -5.0, 1.8), 30, (0.55, 0.68, 1.0), a, b, size=3, target=(0.4, -7.5, 1.0))
    S.shot(s, "c31", a, b, (-1.7, -4.4, 0.7), (0.55, -9.7, 1.9), 28, move=(0.1, -0.1, 0.32), push=0.06)

    # ============================================================ 32: dawn, Theo on the porch
    a, b = A[32], B[32]
    th = actor("TH32", "theo", a, b, (0.15, -9.5, 0.152), PI, "kid_sad")
    C.sit(th)
    th["root"].location = (0.15, -9.5, 0.152)
    fl32 = torch(th, "theo", "T32", a, b, "r")
    lit(fl32, a, True)
    gone = p.word(32, "gone")
    blink_a, blink_b = a + 38, a + 58  # a long, heavy-lidded blink as he nods off
    C.faces_over(th, a, blink_a - 1, "kid_sad", seed=19)
    C.show_face(th, "kid_sad_blink", blink_a)
    C.faces_over(th, blink_b, b, "kid_sad", seed=21)
    arm(th, "r", a, -42)
    arm(th, "r", a + 60, -46)
    arm(th, "r", b, -42)
    arm(th, "l", a, -34)
    arm(th, "l", b, -34)
    for f, x, z in ((a, 18, 0), (a + 38, 36, 0), (blink_b, 30, 0), (gone - 6, 28, 0), (gone + 8, 6, 0), (b, 2, 0)):
        neck(th, f, x, 0, z)
    tremble(fl32["root"], a, b, (50, 0, 0), 0.4, 6, 8)
    slight("AREA", "f32_fill", (-2.4, -6.6, 2.0), 60, (1.0, 0.85, 0.75), a, b, size=3, target=(0.15, -9.5, 1.1))
    S.shot(s, "c32", a, b, (-1.7, -6.5, 0.95), (0.15, -9.4, 1.0), 30, move=(0.25, 0.1, 0.0), push=0.08)

    # ============================================================ 33: afternoon, the truck leaves
    a, b = A[33], B[33]
    fl33 = S.flashlight("FL33")
    fl33["beam"].rotation_euler = R(-90, 0, 0)
    fl33["root"].location = (0.5, -9.55, 0.5 + 0.04)
    fl33["root"].rotation_euler = R(0, 0, 25)
    S.visible(fl33, 1, False)
    S.visible(fl33, a, True)
    S.visible(fl33, A[36], False)  # Mom picks it up
    lit(fl33, 1, False)
    crate33 = S.crate_of_bulbs("CR33", (0, 0, 0))
    crate33.location, crate33.rotation_euler.z = (-0.02, -9.4, 0.5), 0.2
    S.visible(crate33, 1, False)
    S.visible(crate33, a, True)
    tr = S.truck("TRUCK", (0, 0, 0))
    tr.location = (1.6, 3.5, 0.0)
    tf = p.ev("truck")
    place(tr, a, (1.6, 3.5, 0.0))
    place(tr, tf, (1.6, 3.5, 0.0))
    for k in range(1, 14):
        t = k * 10 / 30
        place(tr, tf + 10 * k, (1.6 - 0.5 * 1.15 * t * t, 3.5, 0.0))
    for fc in C.fcurves(tr):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    for fc in C.fcurves(tr):  # ease the first second so it pulls away, not jumps
        if fc.array_index == 0:
            for kp in fc.keyframe_points[:4]:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
    for f in range(tf, tf + 130, 6):  # a little suspension bob
        tr.location.z = 0.02 if (f - tf) // 6 % 2 else 0.0
        tr.keyframe_insert("location", index=2, frame=f)
    S.visible(tr, 1, False)
    S.visible(tr, a, True)
    S.visible(tr, B[33] + 1, False)
    slight("AREA", "f33_fill", (0.6, -9.9, 2.3), 30, (1.0, 0.93, 0.85), a, b, size=3, target=(0.1, -9.5, 0.6))
    S.shot(s, "c33", a, b, (0.2, -10.45, 0.95), (0.25, 3.0, 1.35), 26, move=(0.25, 0.0, 0.05), push=0.07)

    # ============================================================ 34-38: the narrator's window (one actor)
    room = NAR["room_spot"]
    na, nb = A[34], B[38]
    tw = THEO["window"]
    rz = math.atan2(tw[0] - room[0], -(tw[1] - room[1]))
    stool = box("win_stool", (0.5, 0.4, 0.22), (room[0], room[1], 0.11), color("toybox", (0.55, 0.3, 0.2), 0.7), 0.02)
    nr = actor("NAR_ROOM", "nar", na, nb, (room[0], room[1], 0.22), rz, "kid_sad")
    C.faces_over(nr, na, nb, "kid_sad", seed=23)
    flr = torch(nr, "nar", "NF", na, nb, "r", cone=26, power=14000)
    f3, f4 = p.ev("nar_flash3"), p.ev("nar_flash4")
    flash2(flr, f3, f4)
    w_nothing = p.word(34, "nothing")
    # 34: raise the light, two flashes at Theo's dark window, nothing
    arm(nr, "r", na, 0)
    arm(nr, "r", f3 - 22, 0)
    arm(nr, "r", f3 - 6, -98)
    arm(nr, "r", f4 + 14, -98)
    arm(nr, "r", f4 + 46, -8)   # the light sinks
    # 38: it comes back up and the flashlight starts to glow on "on"
    a38, b38 = A[38], B[38]
    arm(nr, "r", a38 - 2, -8)
    arm(nr, "r", a38 + 16, -98)
    won = p.word(38, "on")
    lit(flr, won - 1, True)
    for f, x in ((na, -2), (w_nothing, -2), (w_nothing + 18, 12), (A[35], 12), (A[37], 6), (a38, 3), (a38 + 14, -4)):
        neck(nr, f, x, 0, 0)
    for f, z in ((na, 0), (f3 - 20, 0), (f3 - 4, 3)):
        root_rot(nr, f, 0, rz + math.radians(z))
    tremble(flr["root"], f3 - 6, f4 + 14, (90, 0, 0), 0.25, 5, 3)
    slight("POINT", "f34_fill", (2.2, -13.3, 2.0), 25, (0.8, 0.85, 1.0), na, nb, size=0.6)
    in_eye = NAR["in_eye"]
    S.shot(s, "c34", A[34], B[34], (in_eye[0], in_eye[1], 1.7), (tw[0], tw[1], 1.65), 28, move=(0.1, 0.0, 0.0), push=0.08)

    # 35: from across the street, the porch lamp flickers on (central table); the narrator at his window
    S.shot(s, "c35", A[35], B[35], (-0.9, 6.0, 1.7), (1.0, -10.8, 2.0), 54, move=(0.0, -0.25, 0.0), push=0.08)

    # 36-37: Mom under the lamp, then she turns and looks at the narrator's window
    a36, b36, a37, b37 = A[36], B[36], A[37], B[37]
    mom = actor("MOM", "mom_l", a36, b37, (0.62, -10.15, 0.5), PI, "mom_sad")
    w_looked, w_right, w_window = p.word(37, "looked"), p.word(37, "right"), p.word(37, "window")
    turn0, turn1 = a37 + 2, w_right + 4
    C.faces_over(mom, a36, turn1 + 2, "mom_sad", seed=29)
    C.faces_over(mom, turn1 + 3, b37, "mom_cry", blink=False)
    flm = torch(mom, "mom_l", "MF", a36, b37, "r", power=300)
    m1, m2 = p.ev("mom_flash1"), p.ev("mom_flash2")
    flash2(flm, m1, m2)
    arm(mom, "r", a36, -52)
    arm(mom, "r", m1 - 24, -52)
    arm(mom, "r", m1 - 8, -92)
    arm(mom, "r", b37, -94)
    arm(mom, "l", a36, -38)
    arm(mom, "l", b37, -38)
    rz_end = 1.26
    for f, z in ((a36, PI), (turn0, PI), (turn1, rz_end), (b37, rz_end)):
        root_rot(mom, f, 0, z)
    for f, z, x in ((a36, 0, -22), (a37 - 6, 0, -24), (turn0 - 1, 0, -24), (turn0 + 8, 0, -2), (b37, 0, -2)):
        neck(mom, f, x, 0, z)
    tremble(flm["root"], a36, m1 - 9, (90, 0, 0), 0.3, 6, 6)
    slight("AREA", "f36_fill", (-3.2, -6.4, 2.2), 60, (1.0, 0.82, 0.62), a36, b36, size=3, target=(0.6, -10.1, 1.4))
    slight("AREA", "f37_fill", (2.7, -10.2, 2.4), 30, (1.0, 0.85, 0.7), a37, b37, size=2, target=(0.62, -10.15, 1.4))
    S.shot(s, "c36", a36, b36, (-2.3, -7.0, 1.4), (0.6, -10.2, 1.5), 55, move=(0.2, -0.1, 0.0), push=0.1)
    S.shot(s, "c37", a37, b37, (2.45, -10.5, 1.5), (0.55, -10.1, 1.75), 30, move=(0.1, 0.05, 0.0), push=0.1)

    # 38: inside, behind the narrator, the light comes up (hard cut on the last frame)
    S.shot(s, "c38", A[38], B[38], (3.4, -13.2, 1.1), (2.0, -11.2, 1.2), 26, move=(-0.08, 0.0, 0.0), push=0.06)
    sky_dome("sky_dawn", A[32], B[32], (1.0, 0.66, 0.42), (0.3, 0.42, 0.68), 1.4)
    sky_dome("sky_day", A[33], B[33], (0.78, 0.86, 0.95), (0.3, 0.5, 0.85), 1.3)
    hide_posts([(A[27], B[27]), (A[30], B[30])])
    S.finish(s, p)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    s = S.reset(32)
    p = S.Part(3)
    make(s, p)
    S.render(s, p, args)
