"""Compose a lecture video: avatar intro (first slide) -> voice-over slides with build-up + nodding avatar -> avatar outro (last slide).
usage: python3 lecture_compose.py --states <deck_build out> --voice <say_clean outdir> --intro <mp4> --outro <mp4> [--outro_ss s]
                                  --nod <loop mp4> --out <mp4> [--only 2,5-7] [--work dir]
- Build-up: each unit of a slide appears when the voice reaches the sentence that shares the most key words with it
  (monotonic in reading order); units without a match are spread between their neighbours. Pictures appear with
  the next text unit. Times are written to <work>/timing.json for review.
- Nodding avatar: circle placed in the emptiest spot along the edges (corners preferred) of the fully built slide (checked against the content);
  the loop keeps running across slides (no restart jumps). Green "AI avatar" light under it (disclosure).
- Intro/outro: the slide is shown whole, scaled, next to the talking avatar (nothing on the slide is covered)."""
import argparse, glob, json, math, os, re, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ap = argparse.ArgumentParser()
for k in ("states", "voice", "intro", "outro", "nod", "out"): ap.add_argument(f"--{k}", required=True)
ap.add_argument("--outro_ss", type=float, default=0.0); ap.add_argument("--intro_ss", type=float, default=0.0)
ap.add_argument("--only", default=""); ap.add_argument("--work", default=None)
ap.add_argument("--reuse", action="store_true", help="keep voice-over parts already rendered in the work dir")
ap.add_argument("--bg", default="#0e1420"); ap.add_argument("--tail", type=float, default=0.7)
ap.add_argument("--clip", action="append", default=[], help="N=video.mp4: play this clip instead of slide N (no avatar)")
ap.add_argument("--place", action="append", default=[], help="N=tr[:140]: put slide N's nodding avatar in this corner (size)")
ap.add_argument("--preroll", help="clip played before the first slide"); ap.add_argument("--corner", help="fix the nodding avatar to tr/br/tl/bl")
a = ap.parse_args()
for k in ("states", "voice", "intro", "outro", "nod", "out", "preroll", "work"):   # ffmpeg concat lists resolve relative to the list file
    if getattr(a, k): setattr(a, k, os.path.abspath(getattr(a, k)))
a.clip = [c.split("=", 1)[0] + "=" + os.path.abspath(c.split("=", 1)[1]) for c in a.clip]
W, H, FPS = 1920, 1080, 25
PLACE = {int(k): (v.split(':')[0], int(v.split(':')[1]) if ':' in v else 176) for k, v in (p.split('=') for p in a.place)}
WK = a.work or os.path.splitext(a.out)[0] + "_work"; os.makedirs(WK, exist_ok=True)
dur = lambda f: float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]))
ff = lambda *x: subprocess.run(["ffmpeg", "-y", "-v", "error", *x], check=True)
def level(wav, target=-16.0):
    """audio filter: fixed gain to the target integrated loudness (LUFS) + peak limiter (no dynamic compression)"""
    r = subprocess.run(["ffmpeg", "-nostats", "-i", wav, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    i = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])
    return f"volume={max(-20.0, min(20.0, target - i)):.2f}dB,alimiter=limit=0.89:level=0" if i > -70 else "anull"


ENC = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), "-crf", "18", "-preset", "medium",
       "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]
units = {u["slide"]: u["units"] for u in json.load(open(os.path.join(a.states, "units.json")))}
N = max(units)
FONT = next((f for f in ["/home/julios/.local/share/fonts/aptos/Aptos-SemiBold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if os.path.exists(f)), None)
STOP = set("the a an and or of to in on for is are be with as by it this that we you can from at not but they their our its "
           "have has was were will would should could also about into than then there these those which what when how why".split())


def state_png(n, k): return os.path.join(a.states, "png", f"slide_{n:02d}_k{k}.png")


def stem(w): return re.sub(r"(ing|ed|es|s)$", "", w)[:6] if len(w) > 4 else w


def words(t): return {stem(w) for w in re.findall(r"[a-z]+", t.lower().replace("’", "'")) if len(w) > 3 and w not in STOP}


def reveal_times(n, vj):
    """time (s) at which unit k becomes visible, k = 0..len-1."""
    us, ss = units[n], vj["sentences"]
    if not us: return []
    cues = [s["t0"] for s in ss if s.get("cue")]
    if cues:   # script marks where each unit appears ([+] at a sentence start)
        if len(cues) != len(us): print(f"WARNING slide {n}: {len(cues)} cues for {len(us)} units")
        cues = (cues + [cues[-1] + 2.0 * (i + 1) for i in range(len(us))])[:len(us)]
        out = []
        for c in cues: out.append(round(max(0.0, c - 0.2, out[-1] + 0.5 if out else 0.0), 2))
        return out
    S = [words(s["text"]) for s in ss]
    sc = [[(len(words(u["text"]) & S[i]) / math.sqrt(len(words(u["text"])) + 1)) if u["text"] else 0.0 for i in range(len(ss))] for u in us]
    # DP: assign each unit a sentence index, non-decreasing, maximising total overlap
    m, L = len(us), len(ss); best = np.full((m, L), -1e9); arg = np.zeros((m, L), int)
    for i in range(L): best[0, i] = sc[0][i] - 0.01 * i
    for k in range(1, m):
        run, ri = -1e9, 0
        for i in range(L):
            if best[k - 1, i] > run: run, ri = best[k - 1, i], i
            best[k, i] = run + sc[k][i] - 0.01 * (i - ri); arg[k, i] = ri
    idx = [int(np.argmax(best[m - 1]))]
    for k in range(m - 1, 0, -1): idx.append(arg[k, idx[-1]])
    idx = idx[::-1]
    matched = [sc[k][idx[k]] > 0.25 for k in range(m)]
    t = [ss[idx[k]]["t0"] if matched[k] else None for k in range(m)]
    if not any(matched):   # nothing matches: spread evenly over the first 85% of the speech
        return [round(k * 0.85 * vj["dur"] / m, 2) for k in range(m)]
    t[0] = 0.0 if t[0] is None or idx[0] == 0 else t[0]
    for k in range(m):     # pictures / unmatched: with the next matched unit, else after the previous
        if t[k] is None:
            nxt = next((t[j] for j in range(k + 1, m) if t[j] is not None), None)
            t[k] = nxt if nxt is not None else min(vj["dur"] * 0.9, t[k - 1] + 3.0)
    out = []
    for k in range(m):
        x = max(0.0, t[k] - 0.25)
        if out: x = max(x, out[-1] + 0.6)
        out.append(round(x, 2))
    return out


def free_spot(png, size, force=None, pad=30):
    """Emptiest place for the circle (+ label) along the slide edges, judged with a 30 px clearance around it;
    corners are preferred (br first), then positions closer to a corner."""
    im = np.asarray(Image.open(png).convert("L").resize((W, H)), dtype=np.int16)
    border = np.concatenate([im[0], im[-1], im[:, 0], im[:, -1]]); bgv = np.bincount(border.astype(np.uint8)).argmax()
    busy = (np.abs(im - bgv) > 18).astype(np.float64); ii = np.pad(busy.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    mg, lab = 26, 34
    x0, x1, y0, y1 = mg, W - size - mg, mg, H - size - mg - lab
    corners = {"br": (x1, y1), "tr": (x1, y0), "bl": (x0, y1), "tl": (x0, y0)}
    pref = {"br": 0, "tr": 0.003, "bl": 0.006, "tl": 0.01}

    def frac(x, y):
        a, b = max(0, y - pad), min(H, y + size + lab + pad); c, d = max(0, x - pad), min(W, x + size + pad)
        return (ii[b, d] - ii[a, d] - ii[b, c] + ii[a, c]) / ((b - a) * (d - c))
    if force: x, y = corners[force]; return force, (x, y), round(float(frac(x, y)), 4)
    cands = {(x, y) for x in range(x0, x1 + 1, 8) for y in (y0, y1)} | {(x, y) for y in range(y0, y1 + 1, 8) for x in (x0, x1)} | set(corners.values())
    best = None
    for x, y in cands:
        k, (cx, cy) = min(corners.items(), key=lambda kv: abs(kv[1][0] - x) + abs(kv[1][1] - y))
        f = frac(x, y); sc = (f > 0.0002) * 0.05 + f + pref[k] + 0.002 * (abs(cx - x) + abs(cy - y)) / 100   # fully clear first
        if best is None or sc < best[0]: best = (sc, k if (x, y) == (cx, cy) else f"{k}~", (x, y), frac(x, y))
    return best[1], best[2], round(float(best[3]), 4)


def badge(size):
    """RGBA overlay the size of the circle + label: white ring, soft shadow, green 'AI avatar' light."""
    lab = 34; img = Image.new("RGBA", (size + 24, size + lab + 24), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse([12, 16, 12 + size, 16 + size], fill=(0, 0, 0, 90))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(6))); d = ImageDraw.Draw(img)
    d.ellipse([10, 10, 14 + size, 14 + size], outline=(255, 255, 255, 255), width=4)
    f = ImageFont.truetype(FONT, 19) if FONT else ImageFont.load_default(); txt = "AI avatar"
    tw = d.textlength(txt, font=f); pw = tw + 44; px = 12 + (size - pw) / 2; py = 12 + size - 6
    d.rounded_rectangle([px, py, px + pw, py + 30], 15, fill=(14, 20, 32, 235))
    d.ellipse([px + 12, py + 9, px + 24, py + 21], fill=(46, 204, 113, 255)); d.text((px + 32, py + 4), txt, font=f, fill=(255, 255, 255, 255))
    return img


def circle_mask(size):
    m = Image.new("L", (size * 4, size * 4), 0); ImageDraw.Draw(m).ellipse([0, 0, size * 4 - 1, size * 4 - 1], fill=255)
    return m.resize((size, size), Image.LANCZOS)


def voiceover(n, t_nod, timing):
    vj = json.load(open(os.path.join(a.voice, f"slide_{n:02d}.json"))); wav = os.path.join(a.voice, f"slide_{n:02d}.wav")
    total = vj["dur"] + a.tail; rt = reveal_times(n, vj); k_last = len(units[n])
    times = [0.0] + rt if (rt and rt[0] > 0) else rt or [0.0]
    states = list(range(len(times))) if (rt and rt[0] > 0) else list(range(1, len(times) + 1)) if rt else [0]
    lst = os.path.join(WK, f"s{n:02d}_list.txt")
    with open(lst, "w") as f:
        for j, st in enumerate(states):
            end = times[j + 1] if j + 1 < len(times) else total
            f.write(f"file '{state_png(n, st)}'\nduration {max(0.04, end - times[j]):.3f}\n")
        f.write(f"file '{state_png(n, states[-1])}'\n")
    fin = state_png(n, k_last); force = PLACE.get(n, (a.corner, 176))
    if force[0]: size = force[1]; corner, (x, y), busy = free_spot(fin, size, force[0])
    else:   # a clean corner first; else the clearest edge spot; else the same with the smaller circle
        for size, pad in ((176, 12), (140, 12)):
            c = min((free_spot(fin, size, k, pad) + (pref,) for k, pref in (("br", 0), ("tr", 1), ("bl", 2), ("tl", 3))), key=lambda r: (r[2] > 0.0002, r[3]))
            if c[2] <= 0.0002: corner, (x, y), busy = c[:3]; break
        else:
            size = 176; corner, (x, y), busy = free_spot(fin, size)
            if busy > 0.0002: size = 140; corner, (x, y), busy = free_spot(fin, size)
    circle_mask(size).save(os.path.join(WK, f"m{size}.png")); badge(size).save(os.path.join(WK, f"b{size}.png"))
    timing[n] = {"dur": round(total, 2), "reveal": dict(zip([f"{i + 1}: " + (u["text"][:60] or u["kind"]) for i, u in enumerate(units[n])], rt)), "avatar": corner, "busy": busy, "size": size}
    out = os.path.join(WK, f"part_{n:02d}.mp4")
    ff("-f", "concat", "-safe", "0", "-i", lst, "-ss", f"{t_nod % dur(a.nod):.3f}", "-stream_loop", "-1", "-i", a.nod,
       "-loop", "1", "-i", os.path.join(WK, f"m{size}.png"), "-loop", "1", "-i", os.path.join(WK, f"b{size}.png"), "-i", wav,
       "-filter_complex", f"[0:v]scale={W}:{H},fps={FPS},format=rgb24[bg];[1:v]scale={size}:{size}:flags=lanczos,format=rgba[n];[2:v]format=gray[m];"
       f"[n][m]alphamerge[c];[bg][c]overlay={x}:{y}:shortest=1[v1];[v1][3:v]overlay={x - 12}:{y - 12}:shortest=1,format=yuv420p[o];[4:a]{level(wav)},apad[s]",
       "-map", "[o]", "-map", "[s]", "-t", f"{total:.3f}", *ENC, out)
    return out, total


def avatar_part(n, av, ss, timing):
    wav = os.path.join(a.voice, f"slide_{n:02d}.wav"); total = dur(wav) + a.tail
    sw, sh_ = 1290, 726; sx, sy = 60, (H - sh_) // 2                       # slide, scaled, left
    aw = 470; ah = round(aw * 704 / 576); ax, ay = sx + sw + 40, (H - ah) // 2  # avatar, right
    k = len(units[n]); bg = Image.new("RGB", (W, H), a.bg)
    sl = Image.open(state_png(n, k)).convert("RGB").resize((sw, sh_), Image.LANCZOS); bg.paste(sl, (sx, sy))
    d = ImageDraw.Draw(bg); f = ImageFont.truetype(FONT, 24) if FONT else ImageFont.load_default()
    d.ellipse([ax, ay - 40, ax + 16, ay - 24], fill=(46, 204, 113)); d.text((ax + 26, ay - 45), "AI avatar", font=f, fill=(255, 255, 255))
    bgp = os.path.join(WK, f"avbg_{n:02d}.png"); bg.save(bgp)
    m = Image.new("L", (aw, ah), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, aw - 1, ah - 1], 26, fill=255); m.save(os.path.join(WK, "avmask.png"))
    out = os.path.join(WK, f"part_{n:02d}.mp4")
    ff("-loop", "1", "-i", bgp, "-ss", f"{ss}", "-i", av, "-loop", "1", "-i", os.path.join(WK, "avmask.png"), "-i", wav,
       "-filter_complex", f"[1:v]scale={aw}:{ah}:flags=lanczos,format=rgba,tpad=stop_mode=clone:stop_duration=3[v];[2:v]format=gray[m];[v][m]alphamerge[av];"
       f"[0:v][av]overlay={ax}:{ay}:shortest=1,format=yuv420p[o];[3:a]{level(wav)},apad[s]", "-map", "[o]", "-map", "[s]", "-t", f"{total:.3f}", *ENC, out)
    timing[n] = {"dur": round(total, 2), "avatar": "talking"}
    return out, total


only = set()
for r in filter(None, a.only.split(",")):
    lo, _, hi = r.partition("-"); only |= set(range(int(lo), int(hi or lo) + 1))
clips = dict((int(c.split("=")[0]), c.split("=", 1)[1]) for c in a.clip)


def clip_part(src, name):
    out = os.path.join(WK, name); t = dur(src)
    ff("-i", src, "-f", "lavfi", "-t", f"{t:.3f}", "-i", "anullsrc=r=48000:cl=stereo", "-filter_complex",
       f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS},format=yuv420p[o]",
       "-map", "[o]", "-map", "1:a", "-t", f"{t:.3f}", *ENC, out)
    return out, t


timing, parts, t_nod = {}, [], 0.0
if a.preroll and not only: p, t = clip_part(a.preroll, "part_00_preroll.mp4"); parts.append(p); timing[0] = {"dur": round(t, 2), "clip": a.preroll}
for n in range(1, N + 1):
    if only and n not in only: continue
    if n in clips: p, t = clip_part(clips[n], f"part_{n:02d}.mp4"); timing[n] = {"dur": round(t, 2), "clip": clips[n]}
    elif n == 1: p, t = avatar_part(n, a.intro, a.intro_ss, timing)
    elif n == N: p, t = avatar_part(n, a.outro, a.outro_ss, timing)
    elif a.reuse and os.path.exists(os.path.join(WK, f"part_{n:02d}.mp4")):
        p = os.path.join(WK, f"part_{n:02d}.mp4"); t = dur(p); timing[n] = {"dur": round(t, 2), "reused": True}; t_nod += t
    else: p, t = voiceover(n, t_nod, timing); t_nod += t
    parts.append(p); print(f"slide {n}: {t:.1f}s {timing[n]}", flush=True)
json.dump(timing, open(os.path.join(WK, "timing.json"), "w"), indent=1, ensure_ascii=False)
with open(os.path.join(WK, "parts.txt"), "w") as f: f.write("".join(f"file '{p}'\n" for p in parts))
ff("-f", "concat", "-safe", "0", "-i", os.path.join(WK, "parts.txt"), "-c", "copy", "-movflags", "+faststart", a.out)
print(f"WROTE {a.out} {dur(a.out):.1f}s")
