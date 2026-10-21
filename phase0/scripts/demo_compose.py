"""Compose the Zoom-alternative demo: demo_compose.py <demo dir> <avatar mp4> <split s> <nod loop mp4> <out mp4>
<demo dir> holds png/ (from demo_slides.py + Firefox), {intro,body,process,outro}.wav and {body,process}_words.json (asr_words.py).
The avatar video is InfiniteTalk output for intro + gap + outro audio; <split s> = where the outro part starts.
The voice-over slides get the small nodding avatar (LivePortrait loop) in the corner circle."""
import json, os, re, subprocess, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__)); from demo_slides import AV_X, AV_Y, AV_S, CX, CY, CS
D, AV, SPLIT, NOD, OUT = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4], sys.argv[5]
P = lambda *a: os.path.join(D, *a)
dur = lambda f: float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]))
ff = lambda *a: subprocess.run(["ffmpeg", "-y", "-v", "error", *a], check=True)
ENC = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "25", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
TAIL = 0.6  # silence after each part

m = Image.new("L", (AV_S, AV_S), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, AV_S - 1, AV_S - 1], 28, fill=255); m.save(P("mask.png"))
c = Image.new("L", (CS * 4, CS * 4), 0); ImageDraw.Draw(c).ellipse([0, 0, CS * 4 - 1, CS * 4 - 1], fill=255)
c.resize((CS, CS), Image.LANCZOS).save(P("mask_circle.png"))

def avatar_part(slide, wav, ss, name):
    t = dur(wav) + TAIL
    ff("-loop", "1", "-i", P("png", slide), "-ss", f"{ss}", "-t", f"{t}", "-i", AV, "-loop", "1", "-i", P("mask.png"), "-i", wav,
       "-filter_complex", f"[1:v]scale={AV_S}:{AV_S},format=rgba,tpad=stop_mode=clone:stop_duration=2[v];[2:v]format=gray[m];[v][m]alphamerge[a];"
       f"[0:v][a]overlay={AV_X}:{AV_Y}:shortest=1,format=yuv420p[o];[3:a]apad[s]", "-map", "[o]", "-map", "[s]", "-t", f"{t}", *ENC, P(name))

def voiceover_part(slide, n_states, cues, name):
    """Slide builds to state k at the first word of cues[k-1]; nodding avatar loops in the corner."""
    W = json.load(open(P(f"{slide}_words.json"))); toks = [re.sub(r"[^a-z]", "", w["w"].lower()) for w in W]
    times = [0.0]
    for phrase in cues:
        ph = phrase.split(); i = next(i for i in range(len(toks)) if toks[i:i + len(ph)] == ph and W[i]["t0"] > times[-1])
        times.append(max(W[i]["t0"] - 0.15, times[-1] + 0.5)); print(f"{slide} state {len(times) - 1} at {times[-1]:.1f}s ({phrase})")
    total = dur(P(f"{slide}.wav")) + TAIL; times.append(total)
    with open(P(f"{slide}_list.txt"), "w") as f:
        for st in range(n_states): f.write(f"file 'png/png_{slide}_{st}.png'\nduration {times[st + 1] - times[st]:.3f}\n")
        f.write(f"file 'png/png_{slide}_{n_states - 1}.png'\n")
    ff("-f", "concat", "-safe", "0", "-i", P(f"{slide}_list.txt"), "-stream_loop", "-1", "-i", NOD, "-loop", "1", "-i", P("mask_circle.png"),
       "-i", P(f"{slide}.wav"), "-filter_complex",
       f"[0:v]fps=25[bg];[1:v]scale={CS}:{CS}:flags=lanczos,format=rgba[n];[2:v]format=gray[m];[n][m]alphamerge[a];"
       f"[bg][a]overlay={CX}:{CY}:shortest=1,format=yuv420p[o];[3:a]apad[s]",
       "-map", "[o]", "-map", "[s]", "-t", f"{total}", *ENC, P(name))

voiceover_part("body", 7, ["this tool turns", "first time", "second quality", "third reach", "and fourth control", "this does not replace"], "part_body.mp4")
voiceover_part("process", 5, ["the avatar speaks", "in between", "if you like", "this demo follows"], "part_process.mp4")
avatar_part("png_intro.png", P("intro.wav"), 0, "part_intro.mp4")
avatar_part("png_outro.png", P("outro.wav"), SPLIT, "part_outro.mp4")
with open(P("parts.txt"), "w") as f: f.write("".join(f"file 'part_{n}.mp4'\n" for n in ("intro", "body", "process", "outro")))
ff("-f", "concat", "-safe", "0", "-i", P("parts.txt"), "-c", "copy", "-movflags", "+faststart", OUT)
print(f"WROTE {OUT} {dur(OUT):.1f}s")
