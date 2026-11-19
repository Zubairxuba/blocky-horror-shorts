"""ONE timeline for picture AND sound. Run:  python timeline.py  (needs ffmpeg + whisper-cli)
timings.json (voice.py) -> shots.json, final/narration.mp3, events.json

Every shot = lead + its spoken line + gap (+ EXTRA silence for on-screen beats like knocks and flashes).
events.json lists every synced beat as a FRAME on the full timeline (frame = round(t*30)+1). scene.py keys its
visual on that frame; assemble.py plays the sound at (frame-1)/30. Neither side times anything on its own.
"""
import json, sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2]  # the skill folder; in a copied story set it to the absolute skill path
sys.path.insert(0, str(SKILL / "pipeline"))
import finish as F  # noqa: E402
from finish import words_with_times  # noqa: E402

HERE = Path(__file__).resolve().parent
FPS, LEAD, GAP, MIN_SHOT, PAD = 30, 0.15, 0.25, 2.0, 0.03
# line number (1-based): extra seconds of silence after the line, for beats the voice doesn't cover
EXTRA = {7: 0.4, 8: 0.4, 19: 1.6, 23: 0.3, 26: 1.6, 34: 0.4, 35: 0.4, 37: 0.6}
LIMIT = 119.0  # user: never longer than 2:00


def frame(t):
    return round(t * FPS) + 1


def layout():
    lines = json.loads((HERE / "timings.json").read_text())
    shots, t = [], 0.0
    for k, (a, b) in enumerate(lines):
        last = k == len(lines) - 1
        dur = (b - a) + LEAD + 0.06 if last else max(MIN_SHOT, (b - a) + LEAD + GAP + EXTRA.get(k + 1, 0))
        shots.append({"start": round(t, 3), "end": round(t + dur, 3), "say": [a, b], "lead": LEAD, "line": k + 1})
        t += dur
    assert t <= LIMIT, f"{t:.1f}s is over the {LIMIT}s limit"
    (HERE / "shots.json").write_text(json.dumps(shots, indent=1))
    fin = HERE / "final"
    fin.mkdir(exist_ok=True)
    ins, mix = [], []
    for k, s in enumerate(shots):  # same voice laying as finish_sample.plan (fades stop clicks at the cuts)
        a, b = s["say"]
        pre = min(PAD, a)
        ms = int((s["start"] + LEAD - pre) * 1000)
        dur = b - a + pre + 0.05
        ins += ["-ss", str(a - pre), "-t", str(dur), "-i", HERE / "narration.mp3"]
        mix.append(f"[{k}:a]afade=t=in:d=0.01,afade=t=out:st={dur - 0.03:.3f}:d=0.03,adelay={ms}|{ms}[l{k}]")
    graph = ";".join(mix) + ";" + "".join(f"[l{k}]" for k in range(len(shots))) + f"amix=inputs={len(shots)}:normalize=0"
    F.run([F.FF, "-y", *ins, "-filter_complex", graph, "-t", str(t), "-codec:a", "libmp3lame", "-qscale:a", "2",
           fin / "narration.mp3"])
    return shots


def word_times(shots):
    """{line: [(word, t_full)]} on the full timeline."""
    out = {}
    for t, w, ln in words_with_times(HERE):
        s = shots[ln]
        out.setdefault(ln + 1, []).append((w.strip("*\",.?!").lower(), round(s["start"] + LEAD + (t - s["say"][0]), 3)))
    return out


def events(shots, words):
    """Every synced beat: (id, time, sound or None, gain). Times come ONLY from words / line ends."""
    def w(line, word, n=1, off=0.0):  # n-th occurrence of `word` in that line
        hits = [t for x, t in words[line] if x == word]
        return hits[n - 1] + off

    def end(line, off=0.0):  # end of the line's speech
        s = shots[line - 1]
        return s["start"] + LEAD + (s["say"][1] - s["say"][0]) + off

    def start(line, off=0.0):
        return shots[line - 1]["start"] + off

    ev = [
        ("rule_knock", w(2, "knocks", off=0.05), "knock1", 0.5),
        ("nar_flash1", end(7, 0.05), "click", 0.5), ("nar_flash2", end(7, 0.4), "click", 0.5),
        ("theo_flash1", end(8, 0.05), "click", 0.45), ("theo_flash2", end(8, 0.4), "click", 0.45),
        ("power_out_16", w(16, "out"), "zap", 0.35),
        ("hale_dark", w(18, "dark"), "zap", 0.35),
        ("hale_knock1", end(19, 0.15), "knock1", 0.2), ("hale_knock2", end(19, 0.7), "knock1", 0.2),
        ("hale_knock3", end(19, 1.25), "knock1", 0.2),
        ("hale_door", w(20, "opened"), "creak", 0.5),
        ("thunder", w(23, "storm"), "thunder", 0.4),
        ("all_out", w(23, "out"), "zap", 0.4),
        ("rain_on", w(23, "storm"), None, 0),
        ("step1", w(25, "came"), "step", 0.6), ("step2", w(25, "up"), "step", 0.6), ("step3", w(25, "steps"), "step", 0.6),
        ("thing_knock1", end(26, 0.15), "knock1", 0.22), ("thing_knock2", end(26, 0.7), "knock1", 0.22),
        ("thing_knock3", end(26, 1.25), "knock1", 0.22),
        ("dont", w(27, "don't"), "stinger", 0.12),
        ("remember", w(29, "remembered"), "whoosh", 0.3),
        ("sunrise", start(32), None, 0),
        ("rain_off", w(32, "sunrise"), None, 0),
        ("truck", start(33, 0.1), "truck", 0.35),
        ("nar_flash3", w(34, "twice"), "click", 0.5), ("nar_flash4", w(34, "twice", off=0.35), "click", 0.5),
        ("porch_flicker", w(35, "flickered"), "buzz", 0.4),
        ("mom_flash1", end(37, 0.05), "click", 0.5), ("mom_flash2", end(37, 0.4), "click", 0.5),
        # attention layer (user): each one sits on a visual beat
        ("intro_drop", 0.0, "drop", 0.3),                       # the first wide street shot
        ("gust1", start(16), "gust", 0.6), ("gust2", start(17, 0.4), "gust", 0.5),  # lights dying down the street
        ("boom_out", w(23, "out"), "boom", 0.25),                # every light goes out
        ("heart_on", w(25, "came"), None, 0), ("heart_off", w(27, "don't"), None, 0),  # heartbeat under the steps/knocks
        ("riser", w(28, "ago") - 2.0, "riser", 0.35), ("boom_ago", w(28, "ago"), "boom", 0.28),  # "Six years AGO"
        ("revwhoosh", start(29) - 0.8, "revwhoosh", 0.25),          # into the flashback
        ("swell", w(35, "flickered"), "swell", 0.35),             # the porch light comes back
        ("end_swell", shots[-1]["end"] - 1.6, "endswell", 0.3),  # rises into the hard cut
    ]
    out = [dict(id=i, frame=frame(t), sound=snd, gain=g) for i, t, snd, g in ev]
    out.sort(key=lambda e: e["frame"])
    return out


if __name__ == "__main__":
    shots = layout()
    words = word_times(shots)
    ev = events(shots, words)
    (HERE / "events.json").write_text(json.dumps(ev, indent=1))
    (HERE / "words_full.json").write_text(json.dumps(words, indent=1))
    last = round(shots[-1]["end"] * FPS)
    print(f"{len(shots)} shots, {shots[-1]['end']:.2f}s = {last} frames, {len(ev)} events")
