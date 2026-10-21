"""Compose the Zoom-alternative demo: demo_compose.py <demo dir> <avatar mp4> <split s> <out mp4>
<demo dir> holds png/ (from demo_slides.py + Firefox), intro.wav, body.wav, outro.wav, body_words.json (asr_words.py).
The avatar video is InfiniteTalk output for intro + gap + outro audio; <split s> = where the outro part starts."""
import json, os, re, subprocess, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__)); from demo_slides import AV_X, AV_Y, AV_S
D, AV, SPLIT, OUT = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
P = lambda *a: os.path.join(D, *a)
dur = lambda f: float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]))
ff = lambda *a: subprocess.run(["ffmpeg", "-y", "-v", "error", *a], check=True)
ENC = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "25", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
TAIL = 0.6  # silence after each part

m = Image.new("L", (AV_S, AV_S), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, AV_S - 1, AV_S - 1], 28, fill=255); m.save(P("mask.png"))
def avatar_part(slide, wav, ss, name):
    t = dur(wav) + TAIL
    ff("-loop", "1", "-i", P("png", slide), "-ss", f"{ss}", "-t", f"{t}", "-i", AV, "-loop", "1", "-i", P("mask.png"), "-i", wav,
       "-filter_complex", f"[1:v]scale={AV_S}:{AV_S},format=rgba,tpad=stop_mode=clone:stop_duration=2[v];[2:v]format=gray[m];[v][m]alphamerge[a];"
       f"[0:v][a]overlay={AV_X}:{AV_Y}:shortest=1,format=yuv420p[o];[3:a]apad[s]", "-map", "[o]", "-map", "[s]", "-t", f"{t}", *ENC, P(name))

# body: reveal states at cue phrases (first word of the phrase)
CUES = [(1, "this tool turns"), (2, "first time"), (3, "second quality"), (4, "third reach"), (5, "and fourth control"), (6, "this does not replace")]
W = json.load(open(P("body_words.json"))); toks = [re.sub(r"[^a-z]", "", w["w"].lower()) for w in W]
times = [0.0]
for st, phrase in CUES:
    ph = phrase.split(); i = next(i for i in range(len(toks)) if toks[i:i + len(ph)] == ph and W[i]["t0"] > times[-1])
    times.append(max(W[i]["t0"] - 0.15, times[-1] + 0.5)); print(f"state {st} at {times[-1]:.1f}s ({phrase})")
total = dur(P("body.wav")) + TAIL; times.append(total)
with open(P("body_list.txt"), "w") as f:
    for st in range(7): f.write(f"file 'png/png_body_{st}.png'\nduration {times[st + 1] - times[st]:.3f}\n")
    f.write("file 'png/png_body_6.png'\n")
ff("-f", "concat", "-safe", "0", "-i", P("body_list.txt"), "-i", P("body.wav"), "-filter_complex", "[1:a]apad[s]", "-map", "0:v", "-map", "[s]",
   "-t", f"{total}", "-vf", "fps=25,format=yuv420p", *ENC, P("part_body.mp4"))

avatar_part("png_intro.png", P("intro.wav"), 0, "part_intro.mp4")
avatar_part("png_outro.png", P("outro.wav"), SPLIT, "part_outro.mp4")
with open(P("parts.txt"), "w") as f: f.write("".join(f"file 'part_{n}.mp4'\n" for n in ("intro", "body", "outro")))
ff("-f", "concat", "-safe", "0", "-i", P("parts.txt"), "-c", "copy", "-movflags", "+faststart", OUT)
print(f"WROTE {OUT} {dur(OUT):.1f}s")
