"""Base check: blender -b -P preview.py -> preview/*.png"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import shared as S  # noqa: E402
import characters as C  # noqa: E402
import bpy  # noqa: E402

s = S.reset(16)
st = S.street()
din, cls = S.dining(), S.classroom()
nar, theo = st["houses"]["nar"], st["houses"]["theo"]
kid = S.char("NAR", "nar", nar["room_spot"], math.pi)
th = S.char("THEO", "theo", theo["room_spot"], 0)
fl = S.flashlight("FL")
fl["root"].parent = th["r_shoulder"]
S.flash(fl, 1, True)
S.char("MOM", "mom_l", (*din["MOM_SEAT"], 0), math.pi)
S.char("HALE", "hale", st["houses"]["hale"]["porch_spot"], math.pi)
S.char("SHADE", "shade", st["houses"]["nar"]["step_spots"][0], math.pi)
S.snowfall("a", (0, 0, 4), (40, 24, 8), 1500)
S.crate_of_bulbs("CRATE", nar["mat_spot"])
S.truck("TRUCK", (6, 2, 0))
views = {
    "street": ((-9, -1.5, 2.4), (2, -9, 1.2), 24),
    "across": ((1.5, -3, 1.7), (0, 11, 1.6), 30),
    "porch": ((1.2, -6.2, 1.3), (0, -10.5, 1.3), 30),
    "room_out": (nar["in_eye"], theo["window"], 30),
    "dining": ((97.8, 102.2, 1.6), (100, 100, 0.8), 26),
    "class": ((142.5, 104, 2.2), (140, 99.5, 0.6), 24),
}
out = Path(__file__).parent / "preview"
out.mkdir(exist_ok=True)
for i, (name, (loc, tgt, lens)) in enumerate(views.items()):
    cam = S.shot(s, name, 1 + i * 100, 60 + i * 100, loc, tgt, lens, push=0.0)
    s.frame_set(1 + i * 100)
    s.render.filepath = str(out / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name, flush=True)
