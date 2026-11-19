"""Original background score for "Still On", synthesized from scratch (numpy): nothing to copyright-claim.
Run: python score.py   -> final/score.wav + final/score.mp3 (full length, hard cut on the last frame)
assemble.py audio mixes final/score.wav under the voice automatically (ducked while words are spoken).
For a new story: keep the instruments and the motif, rewrite the sections A-F for your own beats and event ids.

Channel motif: a music-box lullaby in D minor ("Still on?" = the question phrase ending up on A, the answer ends on D).
Every section boundary and hit is read from shots.json / events.json, so the music follows the same clock as the picture.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
SR = 44100
SHOTS = json.loads((HERE / "shots.json").read_text())
EV = {e["id"]: (e["frame"] - 1) / 30 for e in json.loads((HERE / "events.json").read_text())}
END = round(SHOTS[-1]["end"] * 30) / 30
N = int(END * SR)
rng = np.random.default_rng(7)


def line(n):  # start of a script line's shot (s)
    return SHOTS[n - 1]["start"]


def hz(note):  # "D5", "C#4", "Bb3" -> Hz
    names = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    s = names[note[0]] + (1 if "#" in note else -1 if "b" in note[1:-1] else 0)
    return 440.0 * 2 ** ((s + 12 * (int(note[-1]) + 1) - 69) / 12)


def add(bus, t0, sig):
    i = int(t0 * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    bus[i:i + len(sig)] += sig


def bell(f, amp=0.25, dur=2.6, detune=0.0):
    """Music box tine: bright attack, inharmonic partials, long ring."""
    t = np.arange(int(dur * SR)) / SR
    f = f * (1 + detune)
    x = (np.sin(2 * np.pi * f * t) * np.exp(-t * 2.2)
         + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 5)
         + 0.18 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 9)
         + 0.08 * np.sin(2 * np.pi * f * 8.9 * t) * np.exp(-t * 16))
    return amp * x * np.minimum(t / 0.003, 1)


def piano(f, amp=0.4, dur=4.0):
    """Soft low piano-ish note for hits."""
    t = np.arange(int(dur * SR)) / SR
    x = sum(np.sin(2 * np.pi * f * k * t) * np.exp(-t * (0.9 + 0.8 * k)) / k for k in range(1, 6))
    return amp * x * np.minimum(t / 0.006, 1)


def pad(notes, dur, amp=0.08, att=2.0, rel=2.0):
    """Slow string-like pad: detuned sines + a little 2nd/3rd harmonic, breathing LFO."""
    t = np.arange(int(dur * SR)) / SR
    x = np.zeros_like(t)
    for n in notes:
        f = hz(n)
        for d in (-0.004, 0.0, 0.0043):
            ph = rng.uniform(0, 6.28)
            x += np.sin(2 * np.pi * f * (1 + d) * t + ph) + 0.25 * np.sin(4 * np.pi * f * (1 + d) * t + ph) + 0.08 * np.sin(6 * np.pi * f * (1 + d) * t)
    x *= (1 + 0.15 * np.sin(2 * np.pi * 0.17 * t)) / (3 * len(notes))
    env = np.minimum(1, t / att) * np.minimum(1, (dur - t) / rel)
    return amp * x * np.clip(env, 0, 1)


def thump(amp=0.35):
    """Low heartbeat-like pulse (D2 + sub), audible on phone speakers through its 2nd harmonic."""
    t = np.arange(int(0.6 * SR)) / SR
    f = 73.4 * (1 + 0.6 * np.exp(-t * 40))
    return amp * (np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.4 * np.sin(4 * np.pi * np.cumsum(f) / SR)) * np.exp(-t * 9) * np.minimum(t / 0.004, 1)


def tension(dur, amp=0.05):
    """Two high tones a semitone apart (E6/F6): beating dread, fades in over the whole span."""
    t = np.arange(int(dur * SR)) / SR
    trem = 0.7 + 0.3 * np.sin(2 * np.pi * 5.5 * t)
    x = (np.sin(2 * np.pi * hz("E6") * t) + np.sin(2 * np.pi * hz("F6") * t)) * trem
    return amp * x * (t / dur) ** 1.5 * np.minimum(1, (dur - t) / 0.08)


def motif(bus, t0, notes, beat=0.5, amp=0.22, detune=0.0):
    for k, (n, b) in enumerate(notes):
        dt = detune * (1 if k % 2 else -1)
        add(bus, t0 + b * beat, bell(hz(n), amp, detune=dt))


# the channel motif: (note, beat)
Q = [("D5", 0), ("A5", 1), ("F5", 2), ("E5", 3), ("D5", 4.5), ("E5", 5), ("F5", 5.5), ("A4", 6.5)]   # "Still on?"
A = [("D5", 0), ("A5", 1), ("F5", 2), ("E5", 3), ("C#5", 4.5), ("E5", 5), ("D5", 6)]               # "Still on."


def reverb(x, secs=2.8, wet=0.35):
    t = np.arange(int(secs * SR)) / SR
    ir = rng.standard_normal(len(t)) * np.exp(-t / 0.7)
    ir = np.convolve(ir, np.ones(24) / 24, mode="same")  # darker tail
    ir /= np.sqrt(np.sum(ir ** 2))
    n = 1 << int(np.ceil(np.log2(len(x) + len(ir))))
    y = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[: len(x)]
    return (1 - wet) * x + wet * y * 0.6


def cut(env, a, b, fade=0.05):
    """Silence env between a and b with short fades (a hard horror cut, not a drift)."""
    i, j, f = int(a * SR), int(b * SR), int(fade * SR)
    env[i:j] = 0
    env[max(0, i - f):i] *= np.linspace(1, 0, i - max(0, i - f))
    env[j:j + f] *= np.linspace(0, 1, len(env[j:j + f]))


bus = np.zeros(N)   # reverbed music
dry = np.zeros(N)   # hits and drones that must stay tight

# A. the rule, the buddies, the clues (lines 1-15): soft lullaby
chords = [(0.0, ["D3", "A3", "F4"]), (line(6), ["Bb2", "F3", "D4"]), (line(9), ["F3", "C4", "A4"]),
          (line(10), ["C3", "G3", "E4"]), (line(11), ["D3", "A3", "F4"]), (line(13), ["G2", "D3", "Bb3"]),
          (line(15), ["A2", "E3", "C#4"])]
for k, (t0, notes) in enumerate(chords):
    t1 = chords[k + 1][0] if k + 1 < len(chords) else line(16)
    add(bus, t0, pad(notes, t1 - t0 + 1.5, 0.07 if k else 0.06, att=1.5 if k else 3.0))
motif(bus, 0.6, Q)                              # under the opening wide
motif(bus, line(4) + 0.3, A, amp=0.16)
motif(bus, line(7) + 0.2, Q, amp=0.2)           # "Still on?"
motif(bus, line(8) + 0.2, A, amp=0.2)           # "Still on."
motif(bus, line(9) + 0.3, A, beat=0.55, amp=0.18)
for n, t0 in [("A5", line(11) + 0.4), ("F5", line(12) + 0.4), ("E5", line(13) + 0.4), ("D5", line(14) + 0.4), ("C#5", line(15) + 0.4)]:
    add(bus, t0, bell(hz(n), 0.17, detune=0.006))   # clues: single detuned notes, the lullaby going wrong

# B. the countdown, Mrs. Hale, the storm (lines 16-23): pulse + rising dread
b0, b1 = line(16), EV["all_out"]
add(bus, b0, pad(["D2", "A2", "Eb3", "F3"], b1 - b0 + 0.5, 0.075, att=2.5, rel=0.3))
add(bus, b0, tension(b1 - b0, 0.035))
t = b0 + 0.4
while t < b1 - 0.3:
    if not (EV["hale_knock1"] - 0.9 < t < EV["hale_door"] + 0.3):  # pulse stops so the three knocks land in silence
        add(dry, t, thump(0.22 + 0.18 * (t - b0) / (b1 - b0)))
    t += 60 / (72 + 22 * (t - b0) / (b1 - b0))   # 72 -> 94 bpm
motif(bus, line(22) + 0.3, Q, beat=0.6, amp=0.14, detune=0.004)   # Theo is leaving: the motif, wobbling
env = np.ones(N)
cut(env, EV["hale_knock1"] - 0.6, EV["hale_door"] - 0.2, fade=0.4)   # dread drains out before the knocks
cut(env, EV["all_out"], EV["remember"] - 0.3, fade=0.03)             # every light out: the music dies with them

# C. the steps and knocks (lines 24-27): almost nothing, a low drone the phone still plays
c0, c1 = EV["all_out"] + 1.2, EV["dont"] - 0.7
add(dry, c0, pad(["D2", "D3"], c1 - c0, 0.05, att=4.0, rel=0.15))
add(dry, EV["dont"], piano(hz("D2"), 0.32) + piano(hz("Eb2"), 0.18))   # "Don't!": low cluster hit
add(dry, EV["boom_ago"], piano(hz("D1"), 0.3, 6.0))                     # "Six years AGO"

# D. the reveal + memories (lines 29-31): the motif comes home, slow and sad
d0 = EV["remember"]
for t0, notes in [(d0, ["D3", "A3", "F4"]), (line(30), ["Bb2", "F3", "D4"]), (line(31), ["G2", "D3", "Bb3"]), (line(32) - 0.6, ["A2", "E3", "C#4"])]:
    add(bus, t0, pad(notes, 4.2, 0.075, att=1.2))
motif(bus, d0 + 0.4, A, beat=0.8, amp=0.2)
motif(bus, line(31) + 0.2, Q, beat=0.75, amp=0.16)

# E. dawn, the truck, the empty window (lines 32-34): thin, lonely
e0, e1 = line(32), EV["porch_flicker"]
add(bus, e0, pad(["F3", "C4", "A4"], line(34) - e0 + 1.0, 0.05, att=2.5))
add(bus, line(33) + 0.5, bell(hz("D5"), 0.13))
add(bus, line(33) + 1.6, bell(hz("A4"), 0.11))
add(bus, EV["nar_flash3"], bell(hz("D5"), 0.18))   # the narrator's two flashes: the question, unanswered
add(bus, EV["nar_flash4"], bell(hz("A5"), 0.18))
cut(env, EV["nar_flash4"] + 1.6, EV["porch_flicker"], fade=1.2)

# F. the light comes on, Mom answers (lines 35-38): the answer, rising into the hard cut
add(bus, e1, pad(["D3", "A3", "D4", "F#4"], END - e1 + 0.5, 0.06, att=3.5, rel=0.01))   # D major: someone answered
add(bus, EV["mom_flash1"], bell(hz("D5"), 0.22))
add(bus, EV["mom_flash2"], bell(hz("A5"), 0.22))
add(bus, line(36) + 0.3, bell(hz("F#5"), 0.12))
rise = np.arange(int((END - line(37)) * SR)) / SR
add(bus, line(37), 0.05 * np.sin(2 * np.pi * hz("A3") * rise) * (rise / rise[-1]) ** 2)

mix = reverb(bus) * env + dry
mix[-int(0.004 * SR):] *= np.linspace(1, 0, int(0.004 * SR))   # hard cut on the last frame (4 ms, no click)
mix *= 10 ** (-1.0 / 20) / np.max(np.abs(mix))                    # peak -1 dBFS; the mix sets the real level
st = np.stack([mix, np.roll(mix, int(0.011 * SR))], 1)            # small Haas width for stereo
out = HERE / "final" / "score.wav"
out.parent.mkdir(exist_ok=True)
sf.write(out, st.astype(np.float32), SR, subtype="PCM_24")
import subprocess  # noqa: E402
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(out), "-b:a", "320k", str(out.with_suffix(".mp3"))], check=True)
print(f"{out}  {END:.2f}s")
