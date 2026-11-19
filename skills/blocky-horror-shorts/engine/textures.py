"""Paint the small textures the Blender scenes need (faces, town sign, clock). Run with python (needs Pillow).

writes engine/gen/*.png (already committed; re-run only to change them)  (faces are transparent decals stuck on the front of each blocky head)
"""
import math, os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / "gen"
BOLD = os.environ.get("BOLD_FONT", "/System/Library/Fonts/Supplemental/Arial Black.ttf")  # any heavy .ttf on Linux/Windows


def face(name, eyes, mouth, brows=None, blush=False, holes=False, closed=False, tears=False, hair_grey=False):
    im = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for x in eyes:  # eye centres along y=220
        if mouth == "coal":  # snowman: round coal eyes, no shine
            d.ellipse((x - 30, 170, x + 30, 230), fill=(15, 15, 15, 255))
        elif holes:  # THING: two black hollow eyes, no shine
            d.ellipse((x - 72, 120, x + 72, 330), fill=(3, 3, 3, 255))
        elif closed:  # blink: a soft closed-lid curve
            d.arc((x - 34, 200, x + 34, 250), 20, 160, fill=(25, 25, 30, 255), width=10)
        else:
            d.ellipse((x - 34, 186, x + 34, 262), fill=(25, 25, 30, 255))
            d.ellipse((x - 4, 196, x + 16, 216), fill=(255, 255, 255, 255))  # eye shine
    if brows:
        for x in eyes:
            d.line((x - 36, 160 + brows, x + 36, 160 - brows), fill=(40, 30, 25, 255), width=12)
    if blush:
        for x in eyes:
            d.ellipse((x - 40, 290, x + 40, 320), fill=(235, 130, 130, 110))
    if tears:  # wet streaks under each eye
        for x in eyes:
            d.rounded_rectangle((x - 9, 262, x + 9, 340), 9, fill=(150, 200, 255, 200))
    if mouth == "open":  # talking / shouting
        d.ellipse((222, 300, 290, 372), fill=(45, 20, 22, 255))
    elif mouth == "sad_smile":  # small, tired smile
        d.arc((216, 300, 296, 350), 30, 150, fill=(40, 25, 25, 255), width=10)
    elif mouth == "smile":
        d.arc((196, 280, 316, 370), 15, 165, fill=(40, 25, 25, 255), width=12)
    elif mouth == "worried":
        d.arc((206, 330, 306, 390), 200, 340, fill=(40, 25, 25, 255), width=11)
    elif mouth == "flat":  # not smiling
        d.line((214, 335, 298, 335), fill=(40, 25, 25, 255), width=11)
    elif mouth == "coal":  # snowman: a curve of coal dots
        for k in range(5):
            a = math.radians(200 + k * 35)
            d.ellipse((256 + 90 * math.cos(a) - 16, 270 - 60 * math.sin(a) - 16, 256 + 90 * math.cos(a) + 16, 270 - 60 * math.sin(a) + 16), fill=(15, 15, 15, 255))
    elif mouth == "grin":  # THING: thin endless smile
        d.arc((60, 250, 452, 470), 8, 172, fill=(5, 5, 5, 255), width=10)
    im.save(OUT / f"face_{name}.png")


def sign():
    im = Image.new("RGB", (1024, 640), (238, 232, 214))
    d = ImageDraw.Draw(im)
    d.rectangle((14, 14, 1009, 625), outline=(30, 70, 45), width=22)
    f1, f2 = ImageFont.truetype(BOLD, 64), ImageFont.truetype(BOLD, 92)
    for y, text, font, col in [(70, "WELCOME TO HOLLOWAY", f1, (30, 70, 45)), (210, "NEVER OPEN", f2, (170, 25, 25)),
                               (330, "THE DOOR", f2, (170, 25, 25)), (450, "AFTER 9 PM", f2, (170, 25, 25))]:
        d.text(((1024 - d.textlength(text, font=font)) / 2, y), text, font=font, fill=col)
    im.save(OUT / "sign.png")


def clock(hour=9, minute=0):
    im = Image.new("RGB", (512, 512), (245, 242, 232))
    d = ImageDraw.Draw(im)
    c = 256
    d.ellipse((8, 8, 504, 504), outline=(30, 30, 30), width=18)
    for h in range(12):  # hour ticks
        a = math.radians(h * 30)
        d.line((c + 205 * math.sin(a), c - 205 * math.cos(a), c + 235 * math.sin(a), c - 235 * math.cos(a)), fill=(30, 30, 30), width=12)
    for ang, length, width in [((hour % 12 + minute / 60) * 30, 130, 18), (minute * 6, 190, 11)]:
        a = math.radians(ang)
        d.line((c, c, c + length * math.sin(a), c - length * math.cos(a)), fill=(20, 20, 20), width=width)
    d.ellipse((c - 16, c - 16, c + 16, c + 16), fill=(170, 25, 25))
    im.save(OUT / "clock.png")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    face("kid", eyes=(180, 332), mouth="smile", blush=True)
    face("kid_scared", eyes=(180, 332), mouth="worried", brows=-14)
    face("mom", eyes=(180, 332), mouth="smile", brows=4)
    face("thing", eyes=(170, 342), mouth="grin", holes=True)
    face("kid_sad", eyes=(180, 332), mouth="flat", brows=8)  # snow short: Owen stops smiling
    face("mom_sad", eyes=(180, 332), mouth="worried", brows=-10)
    face("snowman", eyes=(180, 332), mouth="coal")
    # porch-light short (Still On): talking, blinking, crying and sad faces
    for base, brows, mouth in (("kid", None, "smile"), ("kid_sad", 8, "flat"), ("kid_scared", -14, "worried"),
                               ("mom", 4, "smile"), ("mom_sad", -10, "worried")):
        face(f"{base}_blink", eyes=(180, 332), mouth=mouth, brows=brows, closed=True)
    face("kid_talk", eyes=(180, 332), mouth="open", brows=-6)
    face("kid_shout", eyes=(180, 332), mouth="open", brows=-18)
    face("kid_sad_smile", eyes=(180, 332), mouth="sad_smile", brows=10)
    face("kid_sad_smile_blink", eyes=(180, 332), mouth="sad_smile", brows=10, closed=True)
    face("mom_cry", eyes=(180, 332), mouth="worried", brows=-12, tears=True)
    face("mom_talk", eyes=(180, 332), mouth="open", brows=2)
    sign()
    clock()
    print(sorted(p.name for p in OUT.iterdir()))
