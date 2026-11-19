"""Download the free CC0 assets the Blender sets use (Poly Haven), once, into engine/assets/.

usage: python3 engine/assets.py      (re-running skips files already downloaded)
Every asset is CC0 (public domain): free for commercial/monetized use, no credit required. LICENSES.txt records the source.
"""
import json, urllib.request
from pathlib import Path

OUT = Path(__file__).parent / "assets"
UA = {"User-Agent": "studio-asset-fetch"}
HDRIS = {"cobblestone_street_night": "2k"}
TEXTURES = {  # name: resolution (2k where the camera gets close)
    "red_brick": "2k", "asphalt_01": "2k", "concrete_floor_worn_001": "1k", "laminate_floor_02": "2k",
    "beige_wall_001": "1k", "clay_roof_tiles": "1k", "denim_fabric": "1k", "wood_table_001": "1k",
}
MODELS = {  # gltf at 1k textures
    "street_lamp_01": "1k", "metal_trash_can": "1k", "fire_hydrant": "1k", "modular_chainlink_fence": "1k",
    "dining_table": "1k", "dining_chair_02": "1k", "modern_wooden_cabinet": "1k", "fancy_picture_frame_01": "1k",
    "planter_box_01": "1k", "fir_tree_01": "1k",
}
MAPS = ("Diffuse", "nor_gl", "Rough")  # colour, OpenGL normal, roughness


def get(url, dst):
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
        tmp.write_bytes(r.read())
    tmp.rename(dst)


def files(asset):
    with urllib.request.urlopen(urllib.request.Request(f"https://api.polyhaven.com/files/{asset}", headers=UA), timeout=60) as r:
        return json.loads(r.read())


def main():
    log = []
    for name, res in HDRIS.items():
        f = files(name)["hdri"][res]["hdr"]
        get(f["url"], OUT / "hdri" / f"{name}.hdr")
        log.append(f"hdri/{name}.hdr")
    for name, res in TEXTURES.items():
        fs = files(name)
        for m in MAPS:
            f = fs[m][res]["jpg"]
            get(f["url"], OUT / "textures" / name / f"{m}.jpg")
        log.append(f"textures/{name}/")
    for name, res in MODELS.items():
        g = files(name)["gltf"][res]["gltf"]
        get(g["url"], OUT / "models" / name / f"{name}.gltf")
        for rel, inc in g.get("include", {}).items():  # textures/buffers the .gltf points to, same relative paths
            get(inc["url"], OUT / "models" / name / rel)
        log.append(f"models/{name}/")
    (OUT / "LICENSES.txt").write_text("All assets: Poly Haven (polyhaven.com), licence CC0 1.0 (public domain).\n"
                                      + "".join(f"- {l}  https://polyhaven.com/a/{Path(l.rstrip('/')).stem}\n" for l in log))
    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"{len(log)} assets, {total / 1e6:.0f} MB in {OUT}")


if __name__ == "__main__":
    main()
