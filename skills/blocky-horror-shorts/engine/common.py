"""Shared Blender helpers: rounded boxes, materials (flat colour, CC0 photo textures, decals, glow), model import."""
from pathlib import Path

import bpy

HERE = Path(__file__).parent
ASSETS = HERE / "assets"
GEN = HERE / "gen"
_mats = {}


def box(name, size, loc, mat=None, bevel=0.03, parent=None):
    """Rounded box: size=(x,y,z) metres, centred at loc."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        m = o.modifiers.new("bevel", "BEVEL")
        m.width, m.segments, m.limit_method = bevel, 3, "ANGLE"
    if mat:
        o.data.materials.append(mat)
    if parent:
        keep(o, parent)
    return o


def keep(child, parent):
    """Parent without moving the child."""
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


def empty(name, loc, parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    o.location = loc
    if parent:
        keep(o, parent)
    return o


def _principled(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree.nodes, m.node_tree.links, m.node_tree.nodes["Principled BSDF"]


def lin(rgb):
    """Colours are written as normal screen (sRGB) values; Blender wants linear light values."""
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb)


def color(name, rgb, rough=0.6, fabric=False, emit=0.0):
    """Flat colour (sRGB). fabric=True adds a fine denim weave bump so clothes don't look like plastic."""
    key = (name, rgb, rough, fabric, emit)
    if key in _mats:
        return _mats[key]
    rgb = lin(rgb)
    m, nodes, links, p = _principled(name)
    p.inputs["Base Color"].default_value = (*rgb, 1)
    p.inputs["Roughness"].default_value = rough
    if emit:
        p.inputs["Emission Color"].default_value = (*rgb, 1)
        p.inputs["Emission Strength"].default_value = emit
    if fabric:
        _normal(nodes, links, p, ASSETS / "textures/denim_fabric/nor_gl.jpg", scale=6.0, strength=0.6)
    _mats[key] = m
    return m


def _mapping(nodes, links, scale):
    tc, mp = nodes.new("ShaderNodeTexCoord"), nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    links.new(tc.outputs["Object"], mp.inputs["Vector"])
    return mp


def _image(nodes, path, noncolor=False):
    t = nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(str(path), check_existing=True)
    t.projection, t.projection_blend = "BOX", 0.25  # box projection: no UV unwrapping needed on boxes
    if noncolor:
        t.image.colorspace_settings.name = "Non-Color"
    return t


def _normal(nodes, links, p, path, scale, strength=1.0):
    mp = _mapping(nodes, links, scale)
    t = _image(nodes, path, noncolor=True)
    nm = nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = strength
    links.new(mp.outputs["Vector"], t.inputs["Vector"])
    links.new(t.outputs["Color"], nm.inputs["Color"])
    links.new(nm.outputs["Normal"], p.inputs["Normal"])


def pbr(tex, scale=1.0, tint=None):
    """Poly Haven CC0 texture set (Diffuse / nor_gl / Rough) projected onto any object."""
    key = (tex, scale, tint)
    if key in _mats:
        return _mats[key]
    m, nodes, links, p = _principled(tex)
    d = ASSETS / "textures" / tex
    mp = _mapping(nodes, links, scale)
    col, rough = _image(nodes, d / "Diffuse.jpg"), _image(nodes, d / "Rough.jpg", noncolor=True)
    for t in (col, rough):
        links.new(mp.outputs["Vector"], t.inputs["Vector"])
    if tint:
        mix = nodes.new("ShaderNodeMix")
        mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs[7].default_value = (*tint, 1)
        links.new(col.outputs["Color"], mix.inputs[6])
        links.new(mix.outputs[2], p.inputs["Base Color"])
    else:
        links.new(col.outputs["Color"], p.inputs["Base Color"])
    links.new(rough.outputs["Color"], p.inputs["Roughness"])
    _normal(nodes, links, p, d / "nor_gl.jpg", scale)
    _mats[key] = m
    return m


def decal(name, png, emit=0.0):
    """Transparent PNG on a plane (faces, signs, clock): uses the plane's own UVs."""
    m, nodes, links, p = _principled(name)
    t = nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(str(png), check_existing=True)
    links.new(t.outputs["Color"], p.inputs["Base Color"])
    links.new(t.outputs["Alpha"], p.inputs["Alpha"])
    p.inputs["Roughness"].default_value = 0.4
    if emit:
        links.new(t.outputs["Color"], p.inputs["Emission Color"])
        p.inputs["Emission Strength"].default_value = emit
    return m


def plane(name, size, loc, rot, mat, parent=None):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0], size[1], 1)
    o.data.materials.append(mat)
    if parent:
        keep(o, parent)
    return o


def model(name, loc, rot=(0, 0, 0), scale=1.0):
    """Import a Poly Haven glTF model under one empty so it can be moved/rotated as a unit."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ASSETS / "models" / name / f"{name}.gltf"))
    new = [o for o in bpy.data.objects if o not in before]
    root = empty(f"{name}_root", (0, 0, 0))
    for o in new:
        if o.parent is None:
            o.parent = root
    root.location, root.rotation_euler, root.scale = loc, rot, (scale, scale, scale)
    return root


def light(kind, name, loc, energy, rgb=(1, 0.85, 0.65), size=0.2, rot=(0, 0, 0), spot=None):
    d = bpy.data.lights.new(name, kind)
    d.energy, d.color = energy, rgb
    if kind in ("POINT", "SPOT"):
        d.shadow_soft_size = size
    if kind == "SPOT" and spot:
        d.spot_size, d.spot_blend = spot
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    o.location, o.rotation_euler = loc, rot
    return o
