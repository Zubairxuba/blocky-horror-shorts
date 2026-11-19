"""The sets: a night street (around the origin) and a kitchen (around x=100) with a small street outside its window."""
import math

import bpy

from common import ASSETS, GEN, box, color, decal, light, model, pbr, plane

WARM = (1.0, 0.72, 0.42)


def world(strength=0.25):
    """Night-sky HDRI (Poly Haven CC0) for realistic moonlight."""
    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nodes, links = w.node_tree.nodes, w.node_tree.links
    env = nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(str(ASSETS / "hdri/cobblestone_street_night.hdr"), check_existing=True)
    bg = nodes["Background"]
    bg.inputs["Strength"].default_value = strength
    links.new(env.outputs["Color"], bg.inputs["Color"])
    # the camera sees a plain dark night sky; the photo only lights the scene (it has real buildings in it)
    sky, mix, path = nodes.new("ShaderNodeBackground"), nodes.new("ShaderNodeMixShader"), nodes.new("ShaderNodeLightPath")
    sky.inputs["Color"].default_value = (0.004, 0.006, 0.018, 1)
    links.new(path.outputs["Is Camera Ray"], mix.inputs["Fac"])
    links.new(bg.outputs["Background"], mix.inputs[1])
    links.new(sky.outputs["Background"], mix.inputs[2])
    links.new(mix.outputs["Shader"], nodes["World Output"].inputs["Surface"])


def fog(center, size, density=0.0025):
    """A box of thin fog so lights glow in the air (only around the street)."""
    o = box("fog", size, center, bevel=0)
    m = bpy.data.materials.new("fog")
    m.use_nodes = True
    n = m.node_tree.nodes
    n.remove(n["Principled BSDF"])
    v = n.new("ShaderNodeVolumePrincipled")
    v.inputs["Density"].default_value = density
    v.inputs["Color"].default_value = (0.75, 0.8, 0.95, 1)
    m.node_tree.links.new(v.outputs["Volume"], n["Material Output"].inputs["Volume"])
    o.data.materials.append(m)
    o.visible_shadow = False
    return o


def prism(name, x, y, length, depth, base_z, height, mat):
    """Gable roof: a triangular prism along X."""
    hl, hd = length / 2, depth / 2
    v = [(x - hl, y - hd, base_z), (x - hl, y + hd, base_z), (x - hl, y, base_z + height),
         (x + hl, y - hd, base_z), (x + hl, y + hd, base_z), (x + hl, y, base_z + height)]
    f = [(0, 2, 1), (3, 4, 5), (0, 3, 5, 2), (1, 2, 5, 4), (0, 1, 4, 3)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


def house(x, y, facing, lit=(True, False), w=7.0, d=6.0, h=4.6, win_z=2.4):
    """Brick house with a tiled roof, door and two front windows (lit ones glow warm). facing=+1/-1 = toward -Y/+Y."""
    brick, roof = pbr("red_brick", 0.5), pbr("clay_roof_tiles", 0.35)
    box(f"house_{x}_{y}", (w, d, h), (x, y, h / 2), brick, 0.02)
    prism(f"roof_{x}_{y}", x, y, w + 0.5, d + 0.6, h, d * 0.42, roof)
    fy = y - facing * (d / 2 + 0.02)
    door = color("door_red", (0.35, 0.08, 0.06), 0.5)
    box(f"door_{x}_{y}", (1.1, 0.12, 2.1), (x, fy, 1.05), door, 0.02)
    for k, wx in enumerate((x - 2.2, x + 2.2)):
        glow = color(f"win_on", WARM, 0.4, emit=6.0) if lit[k % len(lit)] else color("win_off", (0.03, 0.04, 0.07), 0.15)
        box(f"win_{x}_{y}_{k}", (1.4, 0.08, 1.3), (wx, fy, win_z), glow, 0.0)
        box(f"winframe_{x}_{y}_{k}", (1.6, 0.06, 1.5), (wx, fy + facing * 0.03, win_z), color("frame", (0.9, 0.9, 0.86), 0.5), 0.01)
        if lit[k % len(lit)]:  # light spilling out of the window onto the street
            light("AREA", f"spill_{x}_{k}", (wx, fy - facing * 0.4, win_z), 60, WARM, rot=(math.radians(90 * facing), 0, 0))


def street():
    world(0.32)
    box("road", (90, 9, 0.1), (0, 0, -0.05), pbr("asphalt_01", 0.25), 0)
    for side in (1, -1):
        box(f"sidewalk_{side}", (90, 3, 0.25), (0, side * 6, 0.07), pbr("concrete_floor_worn_001", 0.4), 0.02)
        box(f"lawn_{side}", (90, 6, 0.1), (0, side * 10.5, 0.0), color("grass", (0.09, 0.16, 0.07), 0.9), 0)
    for k, x in enumerate(range(-30, 31, 10)):
        house(x, 15, 1, lit=(k % 3 != 1, k % 2 == 0))
        house(x + 5, -15, -1, lit=(k % 2 == 1, k % 3 == 0))
    for x in range(-30, 31, 12):  # streetlights with real light cones
        for side in (1, -1):
            model("street_lamp_01", (x + (0 if side > 0 else 6), side * 4.9, 0.15), (0, 0, math.pi if side > 0 else 0))
            light("SPOT", f"lamp_{x}_{side}", (x + (0 if side > 0 else 6), side * 4.4, 4.6), 900, (1, 0.8, 0.55),
                  size=0.15, spot=(math.radians(95), 0.6))
    for x, side in ((-14, -1), (8, 1)):
        model("metal_trash_can", (x, side * 6.8, 0.2))
    model("fire_hydrant", (-9, -5.3, 0.2))
    for x in (-24, -4, 16):
        model("fir_tree_01", (x, 12.0, 0.0), scale=0.8)
    # the town sign, facing the camera that looks down the street (+X)
    from common import empty, keep
    sign = empty("sign", (-20.5, -4.7, 0))
    box("sign_post", (0.12, 0.12, 2.4), (-20.5, -4.7, 1.2), color("post", (0.15, 0.15, 0.15), 0.4), 0.01, sign)
    box("sign_board", (0.08, 2.1, 1.35), (-20.52, -4.7, 2.35), color("board", (0.2, 0.3, 0.22), 0.6), 0.02, sign)
    plane("sign_face", (2.0, 1.25), (-20.58, -4.7, 2.35), (math.pi / 2, 0, -math.pi / 2), decal("sign", GEN / "sign.png"), sign)
    sign.rotation_euler.z = math.radians(-35)  # turned toward the camera at the end of the street
    light("POINT", "sign_light", (-22.0, -3.6, 3.4), 160, (1, 0.85, 0.65), size=0.3)
    light("SUN", "moon", (0, 0, 30), 0.25, (0.6, 0.7, 1.0), rot=(math.radians(50), 0, math.radians(30)))
    fog((0, 0, 4), (90, 40, 8))


def kitchen():
    """Kitchen room centred at (100, 0). Back wall at y=+3 (clock, window), front door in the left wall (x=97)."""
    X = 100
    floor, wall = pbr("laminate_floor_02", 0.6), pbr("beige_wall_001", 0.5, tint=(0.95, 0.9, 0.8))
    box("k_floor", (6, 6, 0.1), (X, 0, -0.05), floor, 0)
    box("k_ceiling", (6, 6, 0.1), (X, 0, 3.05), color("ceiling", (0.9, 0.88, 0.84), 0.8), 0)
    box("k_back_left", (3.2, 0.15, 3), (X - 1.4, 3.0, 1.5), wall, 0)           # back wall split around the window
    box("k_back_right", (0.9, 0.15, 3), (X + 2.55, 3.0, 1.5), wall, 0)
    box("k_back_low", (1.3, 0.15, 1.0), (X + 1.45, 3.0, 0.5), wall, 0)
    box("k_back_high", (1.3, 0.15, 0.6), (X + 1.45, 3.0, 2.7), wall, 0)
    white = color("frame", (0.9, 0.9, 0.86), 0.5)
    for name, size, loc in (("sill", (1.45, 0.25, 0.06), (X + 1.45, 2.95, 1.0)), ("bar_v", (0.05, 0.05, 1.5), (X + 1.45, 3.0, 1.75)),
                            ("bar_h", (1.3, 0.05, 0.05), (X + 1.45, 3.0, 1.75))):
        box(f"k_window_{name}", size, loc, white, 0.005)
    box("k_left_wall", (0.15, 6, 3), (X - 3.0, 0, 1.5), wall, 0)
    box("k_right_wall", (0.15, 6, 3), (X + 3.0, 0, 1.5), wall, 0)
    # front door in the left wall, hinged so it can jolt when someone knocks
    from common import empty
    hinge = empty("door_hinge", (X - 2.92, -0.4, 0))
    door = box("front_door", (0.08, 1.0, 2.15), (X - 2.92, 0.1, 1.08), pbr("wood_table_001", 0.8, tint=(0.6, 0.35, 0.25)), 0.015, hinge)
    box("door_knob", (0.1, 0.08, 0.08), (X - 2.85, 0.5, 1.0), color("brass", (0.8, 0.6, 0.25), 0.25), 0.02, hinge)
    model("dining_table", (X, 0.9, 0))
    model("dining_chair_02", (X, 1.65, 0), (0, 0, 0))       # KID's chair, behind the table
    model("modern_wooden_cabinet", (X - 2.4, 2.6, 0))
    model("planter_box_01", (X + 2.5, 2.5, 0), scale=0.6)
    model("fancy_picture_frame_01", (X - 1.0, 2.9, 1.8), (math.pi / 2, 0, 0))
    # wall clock showing 9:00
    bpy.ops.mesh.primitive_cylinder_add(radius=0.32, depth=0.06, location=(X + 0.1, 2.9, 2.2), rotation=(math.pi / 2, 0, 0))
    bpy.context.active_object.data.materials.append(color("clock_rim", (0.15, 0.12, 0.1), 0.4))
    plane("clock_face", (0.58, 0.58), (X + 0.1, 2.865, 2.2), (math.pi / 2, 0, 0), decal("clock", GEN / "clock.png"))
    light("POINT", "k_lamp", (X, 0.9, 2.7), 110, WARM, size=0.35)
    light("AREA", "k_fill", (X + 1.5, -2.5, 2.4), 80, (1, 0.9, 0.8), rot=(math.radians(60), 0, 0))
    light("POINT", "porch", (X - 3.6, 0.1, 2.3), 30, (1, 0.8, 0.5))  # light leaking under the door
    # outside the window: a dark street with one lamp, where the THING walks past
    box("out_ground", (14, 14, 0.1), (X + 1.5, 10, -0.05), pbr("asphalt_01", 0.25), 0)
    model("street_lamp_01", (X + 2.5, 8.5, 0), (0, 0, math.pi))
    light("SPOT", "out_lamp", (X + 2.5, 8.0, 4.4), 700, (1, 0.8, 0.55), size=0.15, spot=(math.radians(80), 0.5))
    box("out_house", (10, 1, 4), (X + 1.5, 15, 2), pbr("red_brick", 0.5), 0.02)
    return hinge
