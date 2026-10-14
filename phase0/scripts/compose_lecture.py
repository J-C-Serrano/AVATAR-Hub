#!/usr/bin/env python3
"""Compose a lecture segment: slide (1920x1080) + avatar RGBA frames (corner) + voice + word-timed captions + AI badge.
usage: compose_lecture.py --slide slide.json --frames out/poc3d/wii/frames --wav in/speech.wav --words in/words.json --out out.mp4
slide.json: {"title": str, "bullets": [str], "footer": str}"""
import argparse, json, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

p = argparse.ArgumentParser()
for k in ("--slide", "--frames", "--wav", "--words", "--out"): p.add_argument(k, required=True)
p.add_argument("--fps", type=int, default=30); p.add_argument("--avatar", type=int, default=480)
A = p.parse_args()
F = "/usr/share/fonts/truetype/dejavu/"
font = lambda n, s: ImageFont.truetype(F + n, s)
W, H = 1920, 1080
tmp = tempfile.mkdtemp()

# --- slide image ---
s = json.load(open(A.slide))
im = Image.new("RGB", (W, H), (246, 247, 250)); d = ImageDraw.Draw(im)
d.rectangle([0, 0, W, 150], fill=(22, 52, 92)); d.rectangle([0, 150, W, 158], fill=(240, 160, 40))
d.text((80, 42), s["title"], font=font("DejaVuSans-Bold.ttf", 64), fill="white")
y = 240
for b in s["bullets"]:
    d.ellipse([90, y + 22, 108, y + 40], fill=(240, 160, 40))
    d.text((140, y), b, font=font("DejaVuSans.ttf", 46), fill=(30, 35, 45)); y += 100
d.text((80, H - 60), s.get("footer", ""), font=font("DejaVuSans.ttf", 26), fill=(120, 125, 135))
# avatar panel (rounded) + AI badge
px, py, a = W - A.avatar - 50, H - A.avatar - 40, A.avatar
# circular avatar: ring on the slide, disc background + circle mask applied in ffmpeg
ring = max(4, a // 40)
d.ellipse([px - ring - 2, py - ring - 2, px + a + ring + 2, py + a + ring + 2], fill=(240, 160, 40))
SS = 4  # supersampled masks for smooth edges
disc = Image.new("RGBA", (a * SS, a * SS), (0, 0, 0, 0)); ImageDraw.Draw(disc).ellipse([0, 0, a * SS - 1, a * SS - 1], fill=(205, 215, 230, 255))
mask = Image.new("L", (a * SS, a * SS), 0); ImageDraw.Draw(mask).ellipse([0, 0, a * SS - 1, a * SS - 1], fill=255)
disc_png, mask_png = os.path.join(tmp, "disc.png"), os.path.join(tmp, "mask.png")
disc.resize((a, a), Image.LANCZOS).save(disc_png); mask.resize((a, a), Image.LANCZOS).save(mask_png)
bf = font("DejaVuSans-Bold.ttf", 22); label = "AI avatar"
bw = d.textlength(label, font=bf) + 24
bx, by = px + a / 2 - bw / 2, py - ring - 48            # badge centred above the circle
d.rounded_rectangle([bx, by, bx + bw, by + 36], radius=10, fill=(22, 52, 92))
d.text((bx + 12, by + 5), label, font=bf, fill="white")
slide_png = os.path.join(tmp, "slide.png"); im.save(slide_png)

# --- captions (ASS), lines of <= 7 words, broken at sentence ends ---
words = json.load(open(A.words)); lines, cur = [], []
for w in words:
    cur.append(w)
    if len(cur) >= 7 or w["w"].endswith((".", "?", "!")): lines.append(cur); cur = []
if cur: lines.append(cur)
def ts(t): return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"
ass = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "",
       "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV",
       f"Style: Cap,DejaVu Sans,44,&H00FFFFFF,&H00000000,&HA0101820,0,3,14,0,1,80,{A.avatar + 120},105", "",
       "[Events]", "Format: Layer, Start, End, Style, Text"]
for i, ln in enumerate(lines):
    end = lines[i + 1][0]["t0"] if i + 1 < len(lines) else ln[-1]["t1"] + 0.5
    ass.append(f"Dialogue: 0,{ts(ln[0]['t0'])},{ts(min(end, ln[-1]['t1'] + 0.6))},Cap," + " ".join(w["w"] for w in ln))
ass_path = os.path.join(tmp, "cap.ass"); open(ass_path, "w").write("\n".join(ass))

cmd = ["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-framerate", str(A.fps), "-i", slide_png,
       "-framerate", str(A.fps), "-i", os.path.join(A.frames, "f_%04d.png"), "-i", A.wav,
       "-loop", "1", "-i", disc_png, "-loop", "1", "-i", mask_png,
       "-filter_complex", f"[1]scale={a}:{a}[av];[3][av]overlay=0:0:shortest=1[c];[4]format=gray[m];[c][m]alphamerge[circ];"
                          f"[0][circ]overlay={px}:{py}:shortest=1,subtitles={ass_path}:fontsdir={F}[v]",
       "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", A.out]
subprocess.run(cmd, check=True); print("WROTE", A.out)
