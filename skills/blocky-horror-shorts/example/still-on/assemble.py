"""Sound + final video for "Still On". Run with python (needs ffmpeg).

  assemble.py audio            # events.json -> synthesized SFX (+ final/score.wav if present) -> final/full_audio.wav
  assemble.py video [preview]  # part1..3 frames (or preview frames) + full_audio -> full_video.mp4 (or preview.mp4)
"""
import json, subprocess, sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2]  # the skill folder; in a copied story set it to the absolute skill path
sys.path.insert(0, str(SKILL / "pipeline"))
sys.path.insert(0, str(SKILL / "engine"))  # look.post_filter
import finish as F  # noqa: E402
from finish import SFX  # noqa: E402

HERE = Path(__file__).resolve().parent
FIN = HERE / "final"
FPS, SR = 30, 48000
shots = json.loads((HERE / "shots.json").read_text())
EV = json.loads((HERE / "events.json").read_text())
END_F = round(shots[-1]["end"] * FPS)
E = {e["id"]: e for e in EV}

# name: (seconds, ffmpeg source, filter chain). All synthesized: nothing to copyright-claim.
NEW_SFX = {
    "knock1": (0.4, "aevalsrc='(0.9*sin(2*PI*85*t)+0.6*(random(0)-0.5))*exp(-28*t)'", "lowpass=f=1800"),
    "click": (0.15, "aevalsrc='0.7*(random(0)-0.5)*exp(-t*260)+0.4*sin(2*PI*1600*t)*exp(-t*180)+0.3*(random(0)-0.5)*exp(-(t-0.05)*300)*gt(t,0.05)'", "highpass=f=400"),
    "zap": (0.7, "aevalsrc='(0.6*(random(0)-0.5)*(0.5+0.5*sin(2*PI*60*t))+0.35*sin(2*PI*120*t))*exp(-t*7)'", "lowpass=f=5000"),
    "creak": (1.3, "aevalsrc='0.4*sin(2*PI*(260+90*sin(2*PI*1.1*t))*t+2.5*sin(2*PI*31*t))*sin(PI*t/1.3)'", "bandpass=f=600:width_type=h:w=900"),
    "thunder": (4.0, "anoisesrc=color=brown:amplitude=1:r=44100:d=4", "lowpass=f=260,volume='(0.3+0.7*exp(-((t-0.25)*(t-0.25))/0.02))*exp(-0.7*t)*(1+0.4*sin(2*PI*2.3*t))':eval=frame,volume=6"),
    "step": (0.45, "aevalsrc='(sin(2*PI*65*t)+0.35*(random(0)-0.5))*exp(-t*22)+0.15*sin(2*PI*(380+60*t)*t)*exp(-t*9)'", "lowpass=f=1500"),
    "truck": (5.0, "anoisesrc=color=brown:amplitude=0.8:r=44100:d=5", "lowpass=f=220,volume='(min(t/0.8,1))*exp(-0.45*t)*(1+0.25*sin(2*PI*14*t))':eval=frame,volume=3"),
    "buzz": (1.4, "aevalsrc='0.3*(sin(2*PI*120*t)+0.5*sin(2*PI*240*t)+0.25*sin(2*PI*360*t))*if(lt(t,0.7),gt(sin(2*PI*11*t+3*sin(2*PI*3*t)),0.1),1)*exp(-0.6*max(t-0.7,0))'", "lowpass=f=3000"),
    "drop": (3.0, "aevalsrc='0.95*sin(2*PI*(32+70*exp(-t*3.5))*t)*exp(-t*1.1)+0.5*(random(0)-0.5)*exp(-t*18)'", "lowpass=f=2500"),
    "boom": (3.0, "aevalsrc='0.9*sin(2*PI*(36+40*exp(-t*4))*t)*exp(-t*1.4)+0.25*(random(0)-0.5)*exp(-t*10)'", "lowpass=f=900"),
    "riser": (2.0, "aevalsrc='(0.6*(random(0)-0.5)+0.35*sin(2*PI*(180+500*t*t)*t))*pow(t/2,2.2)'", "highpass=f=150"),
    "revwhoosh": (0.8, "aevalsrc='(random(0)-0.5)*pow(t/0.8,3)'", "bandpass=f=1200:width_type=h:w=1600"),
    "swell": (2.5, "aevalsrc='0.18*(sin(2*PI*220*t)+sin(2*PI*277.2*t)+sin(2*PI*329.6*t))*min(t/1.2,1)*exp(-0.5*max(t-1.2,0))'", "lowpass=f=2000"),
    "endswell": (1.6, "aevalsrc='(0.4*(random(0)-0.5)+0.3*sin(2*PI*(110+300*t*t)*t))*pow(t/1.6,2.5)'", "highpass=f=100"),
    "gust": (3.0, "anoisesrc=color=pink:amplitude=0.7:r=44100:d=3", "bandpass=f=450:width_type=h:w=500,volume='pow(sin(PI*t/3),2)':eval=frame"),
    "rain": (None, "anoisesrc=color=pink:amplitude=0.5:r=44100", "highpass=f=900,lowpass=f=7000,volume='0.8+0.2*sin(2*PI*t/5)':eval=frame"),
}


def make_sfx(name, secs):
    """Write pipeline/sfx/<name>_<secs>.wav (the path finish.mix_audio looks for) and register its volume."""
    F.SFX_DIR.mkdir(exist_ok=True)
    dur, src, filt = NEW_SFX[name]
    secs = round(secs, 1) if dur is None else dur
    out = F.SFX_DIR / f"{name}_{secs:g}.wav"
    if not out.exists():
        src = src if "d=" in src or "aevalsrc" not in src else src
        src = f"{src}:d={secs}" if src.startswith("aevalsrc") else (src if "d=" in src else f"{src}:d={secs}")
        fade = f"afade=t=in:d={0.6 if dur is None else 0.003},afade=t=out:st={max(0, secs - (1.0 if dur is None else 0.08)):.2f}:d={1.0 if dur is None else 0.08}"
        F.run([F.FF, "-y", "-f", "lavfi", "-i", src, "-af", f"{filt},{fade}", "-ar", "44100", "-ac", "1", out])
    SFX[name] = (None, secs, 1.0)
    return secs


def cues():
    t = lambda i: (E[i]["frame"] - 1) / FPS  # noqa: E731  (same frame the picture keys on)
    out = [(0.0, "wind", round(END_F / FPS, 1), 0.8)]
    rain_a, rain_b = t("rain_on"), t("rain_off")
    out.append((rain_a, "rain", make_sfx("rain", rain_b - rain_a + 1.0), 0.7))
    hb_a, hb_b = t("heart_on"), t("heart_off")
    out.append((hb_a, "heartbeat", round(hb_b - hb_a, 1), 0.25))
    for e in EV:
        if e["sound"]:
            name = e["sound"]
            secs = make_sfx(name, 0) if name in NEW_SFX else SFX[name][1]
            out.append((t(e["id"]), name, secs, e["gain"]))
    for n in (1, 2, 3):  # footsteps the part scenes created on their walk cycles (same frames as the legs)
        fj = HERE / f"part{n}" / "foley.json"
        if fj.exists():
            for e in json.loads(fj.read_text()):
                out.append(((e["frame"] - 1) / FPS, e["sound"], make_sfx(e["sound"], 0), e["gain"] * 0.5))  # part foley sits under the story beats
    return out


def audio():
    end = END_F / FPS
    raw = F.mix_audio(HERE, cues(), True, end, FIN / "mix_raw.wav")
    if (FIN / "score.wav").exists():  # score.py's music: -9 dB, ducked under the voice, before the one fixed gain
        F.run([F.FF, "-y", "-i", raw, "-i", FIN / "score.wav", "-i", FIN / "narration.mp3", "-filter_complex",
               "[1:a]aresample=48000,volume=-9dB[m];[2:a]aresample=48000,pan=stereo|c0=c0|c1=c0[k];"
               "[m][k]sidechaincompress=threshold=0.02:ratio=4:attack=40:release=600[md];"
               "[0:a][md]amix=inputs=2:normalize=0:duration=first[a]", "-map", "[a]", "-ar", "48000",
               "-c:a", "pcm_s16le", FIN / "mix_music.wav"])
        raw = FIN / "mix_music.wav"
    i, tp = F.loudness(raw)
    gain = min(F.TARGET_I - i, F.TARGET_TP - tp)
    F.run([F.FF, "-y", "-i", raw, "-af", f"volume={gain:.2f}dB", "-ar", str(SR), "-c:a", "pcm_s16le", FIN / "full_audio.wav"])
    print(f"mix {i:.1f} LUFS / {tp:.1f} dBTP, fixed gain {gain:+.2f} dB -> {FIN / 'full_audio.wav'}")


def video(preview=False):
    """Number every part's frames onto one timeline (symlinks) and mux with the full audio. No captions."""
    seq = FIN / ("seq_preview" if preview else "seq")
    seq.mkdir(parents=True, exist_ok=True)
    for old in seq.glob("*.png"):
        old.unlink()
    n = 0
    for p in (1, 2, 3):
        src = HERE / f"part{p}" / ("preview" if preview else "frames")
        frames = sorted(src.glob("*.png"))
        for f in frames:
            n += 1
            (seq / f"{n:04d}.png").symlink_to(f)
    assert n == END_F, f"{n} frames, timeline has {END_F}"
    out = HERE / ("preview.mp4" if preview else "full_video.mp4")
    import look  # glow + colour grade + vignette + grain (same look in preview and final)
    graph = look.post_filter("horror").replace("[v]", ",scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p[v]")
    F.run([F.FF, "-y", "-framerate", str(FPS), "-i", seq / "%04d.png", "-i", FIN / "full_audio.wav",
           "-filter_complex", graph, "-map", "[v]", "-map", "1:a",
           "-frames:v", str(n), "-c:v", "libx264", "-preset", "veryfast" if preview else "slow", "-crf", "20" if preview else "16",
           "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-movflags", "+faststart", out])
    print(out, f"{n} frames, {n / FPS:.2f}s")


if __name__ == "__main__":
    {"audio": audio, "video": lambda: video("preview" in sys.argv)}[sys.argv[1]]()
