"""Cinematic look for every Blender short: depth of field, haze, character rim light, and a
post-grade (glow + colour grade + vignette + grain) applied when the frames are muxed.

  look.dof(cam, focus_obj, fstop)      background blur focused on the shot's target (S.shot calls it)
  look.haze(density)                   thin fog in the air so lamp light and beams show (world volume)
  look.rim(objs, strength)             a soft light edge on characters so they separate from dark backgrounds
  look.post_filter(grade)              ffmpeg filter chain for the final mux (glow, grade, vignette, grain)
"""
try:
    import bpy  # only inside Blender; post_filter() is used by plain Python (the mux) too
except ImportError:
    bpy = None


def dof(cam, focus_obj=None, fstop=2.8, distance=None):
    """Real-camera blur. Wide shots: fstop 4-5.6 (subtle); close-ups: 1.8-2.8 (strong)."""
    d = cam.data.dof
    d.use_dof = True
    d.aperture_fstop = fstop
    d.aperture_blades = 6
    if focus_obj is not None:
        d.focus_object = focus_obj
    elif distance:
        d.focus_distance = distance


def haze(density=0.0015, rgb=(0.75, 0.8, 0.95), anisotropy=0.4):
    # NOTE: a WORLD volume dims EEVEE sky lighting a lot (street 86 -> 13 brightness): interiors/close sets only
    """Thin atmospheric fog for the whole world: light cones, lamp halos and depth. Costs ~15-30% render time."""
    s = bpy.context.scene
    w = s.world
    w.use_nodes = True
    nt = w.node_tree
    vol = nt.nodes.get("haze") or nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.name = "haze"
    vol.inputs["Density"].default_value = density
    vol.inputs["Color"].default_value = (*rgb, 1)
    vol.inputs["Anisotropy"].default_value = anisotropy
    vol.inputs["Absorption Color"].default_value = (1, 1, 1, 1)  # scatter only: haze glows, it doesn't darken
    nt.links.new(vol.outputs["Volume"], nt.nodes["World Output"].inputs["Volume"])
    e = s.eevee
    for attr, val in (("volumetric_end", 60.0), ("volumetric_tile_size", "8"), ("volumetric_samples", 48),
                      ("use_volumetric_shadows", True), ("volumetric_light_clamp", 10.0)):
        if hasattr(e, attr):
            setattr(e, attr, val)


def rim(objs, strength=0.12, rgb=(0.75, 0.85, 1.0)):
    """Fresnel edge glow on each object's material(s) (once per material): a cheap 'rim light' that always reads."""
    done = set()
    for o in objs:
        if o.type != "MESH":
            continue
        for m in o.data.materials:
            if not m or m.name in done or not m.use_nodes or "rimmed" in m:
                continue
            done.add(m.name)
            nt = m.node_tree
            p = nt.nodes.get("Principled BSDF")
            if not p or p.inputs["Emission Strength"].is_linked or p.inputs["Emission Strength"].default_value > 0:
                continue  # decals / glowing things keep their own emission
            lw = nt.nodes.new("ShaderNodeLayerWeight")
            lw.inputs["Blend"].default_value = 0.1  # thin edge only
            mul = nt.nodes.new("ShaderNodeMath")
            mul.operation = "MULTIPLY"
            mul.inputs[1].default_value = strength
            nt.links.new(lw.outputs["Facing"], mul.inputs[0])
            p.inputs["Emission Color"].default_value = (*rgb, 1)
            nt.links.new(mul.outputs[0], p.inputs["Emission Strength"])
            m["rimmed"] = True


GRADES = {  # colorbalance shadows/mids/highs (r,g,b) + eq
    "horror": "colorbalance=rs=-0.02:bs=0.04:rh=0.02,eq=contrast=1.06:saturation=1.08:brightness=0.02",
    "warm": "colorbalance=rs=0.04:bs=-0.04:rm=0.04:bm=-0.03,eq=contrast=1.05:saturation=1.1",
    "neutral": "eq=contrast=1.06:saturation=1.08",
}


def post_filter(grade="horror", glow=0.35, vignette=True, grain=5):
    """ffmpeg -filter_complex body taking [0:v] and producing [v] (call sites add format/scale after).
    glow: bright areas bloom softly (lamps, flames, windows); grade: colour mood; vignette; light film grain."""
    chain = (f"[0:v]split[a][b];[b]curves=all='0/0 0.62/0 1/1',gblur=sigma=28[g];"
             f"[a][g]blend=all_mode=screen:all_opacity={glow}[bl];[bl]{GRADES[grade]},unsharp=5:5:0.5")
    if vignette:
        chain += ",vignette=PI/8"
    if grain:
        chain += f",noise=alls={grain}:allf=t"
    return chain + "[v]"


# ---------------- real skies + real vegetation  ----------------
SKIES = {  # photographed CC0 skies from Poly Haven (engine/assets.py downloads them)
    "sunny": "kloofendal_48d_partly_cloudy_puresky",   # blue sky, soft faded clouds, sunlight
    "overcast": "kloofendal_overcast_puresky",
    "sunset": "belfast_sunset_puresky",
    "night": "satara_night_no_lamps",
    "moon": "moonlit_golf",
}


def sky(kind="sunny", strength=1.0, rotate=0.0):
    """A real photographed sky the camera SEES, which also lights the whole scene (sun, colour, soft shadows).
    Replaces sets.world(). rotate (degrees) turns the sun/clouds around the scene."""
    import math
    from pathlib import Path
    s = bpy.context.scene
    w = s.world or bpy.data.worlds.new("World")
    s.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in [n for n in nt.nodes if n.type not in ("OUTPUT_WORLD",)]:
        nt.nodes.remove(n)
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(str(Path(__file__).parent / "assets/hdri" / f"{SKIES.get(kind, kind)}.hdr"), check_existing=True)
    mapping, coord = nt.nodes.new("ShaderNodeMapping"), nt.nodes.new("ShaderNodeTexCoord")
    mapping.inputs["Rotation"].default_value[2] = math.radians(rotate)
    nt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.name = "Background"  # shared.time_of_day keys this socket
    bg.inputs["Strength"].default_value = strength
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], nt.nodes["World Output"].inputs["Surface"])
    return bg


_veg = {}


def tree(name, loc, rot_z=0.0, scale=1.0, ratio=0.06):
    """A real Poly Haven tree/shrub ("tree_small_02", "island_tree_01", "shrub_01", "dead_tree_trunk").
    The first one is imported and decimated to `ratio` of its polygons (the raw trees are 3-5 M polygons, which
    once made renders 10x slower); every further copy shares that mesh (cheap)."""
    from common import model  # noqa: E402  (only inside Blender)
    import math
    if name not in _veg:
        root = model(name, (0, 0, 0))
        dg = bpy.context.evaluated_depsgraph_get()
        for o in root.children_recursive:
            if o.type == "MESH" and len(o.data.polygons) > 20000:
                m = o.modifiers.new("lod", "DECIMATE")
                m.ratio = ratio
                dg.update()
                baked = bpy.data.meshes.new_from_object(o.evaluated_get(dg))  # simplify ONCE, not every frame
                o.modifiers.remove(m)
                o.data = baked
            if o.type == "MESH":
                for mat in o.data.materials:
                    if mat and hasattr(mat, "surface_render_method"):
                        mat.surface_render_method = "DITHERED"  # leaf cards: fast cut-out, not slow blending
        _veg[name] = root
        root.location, root.rotation_euler, root.scale = loc, (0, 0, math.radians(rot_z)), (scale,) * 3
        return root
    src = _veg[name]
    root = bpy.data.objects.new(f"{name}_copy", None)
    bpy.context.collection.objects.link(root)

    def clone(o, parent):
        c = o.copy()  # linked duplicate: shares mesh + modifiers' source data
        bpy.context.collection.objects.link(c)
        c.parent = parent
        for ch in o.children:
            clone(ch, c)
    for ch in src.children:
        clone(ch, root)
    root.location, root.rotation_euler, root.scale = loc, (0, 0, math.radians(rot_z)), (scale,) * 3
    return root
