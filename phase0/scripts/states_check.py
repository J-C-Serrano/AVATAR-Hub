"""Compare each build state made by pdf_states.py with the recording at that moment (what the class actually saw).
usage: python3 states_check.py <recording.mp4> <states dir> [--thr 0.02] [--sheet out.png]
A state whose hiding masks went wrong (box borders, titles or footers wiped together with a later build) differs
from the recording far more than the slide's final state does. Prints one line per state; BAD when the mismatch is
above --thr and clearly above the slide's final state. The webcam box (right edge) is not compared."""
import argparse, json, os, subprocess
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("states")
ap.add_argument("--thr", type=float, default=0.02); ap.add_argument("--sheet")
a = ap.parse_args()
W, H, CAM_X = 1920, 1080, 1560


def frame(t):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", a.video, "-frames:v", "1",
                          "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(np.float32) if len(raw) == W * H * 3 else None


def ink(x):
    """text, lines and edges: pixels that stand out from their neighbourhood (flat areas and soft fills do not)"""
    return (np.abs(x - ndi.median_filter(x, size=(15, 15, 1))).max(2) > 45)


def mismatch(png, v):
    """share of the recording's ink that the state lacks (wiped borders, titles, footers) or shows too early"""
    s = np.asarray(Image.open(png).convert("RGB").resize((W, H)), np.float32)
    iv, is_ = ink(v), ink(s)
    iv[:, CAM_X:] = is_[:, CAM_X:] = False
    near = np.ones((7, 7))                        # video compression shifts and blurs strokes by a few px
    d = (iv & ~ndi.binary_dilation(is_, near)) | (is_ & ~ndi.binary_dilation(iv, near))
    d = ndi.binary_opening(d, np.ones((2, 2)))
    return d.sum() / max(iv.sum(), 1), d


rev = json.load(open(os.path.join(a.states, "reveals.json")))
bad, rows = 0, []
for n, r in sorted(rev.items(), key=lambda x: int(x[0])):
    b = r["builds"]; edges = [r["t0"]] + b + [r["t1"]]
    if not b: continue
    res = []
    for k in range(len(b) + 1):
        t0, t1 = edges[k], edges[k + 1]
        if t1 - t0 < 1.0: res.append(None); continue
        png = os.path.join(a.states, "png", f"slide_{int(n):02d}_k{k}.png")
        if not os.path.exists(png): res.append(None); continue
        v = frame((t0 + t1) / 2)
        res.append(None if v is None else mismatch(png, v))
    last = next((x[0] for x in reversed(res) if x is not None), 0.0)
    for k, x in enumerate(res):
        if x is None: continue
        flag = x[0] > a.thr and x[0] > 2 * last + 0.005
        bad += flag
        print(f"slide {int(n):2d} k{k}: mismatch {x[0]:.3f} (final {last:.3f}){'  BAD' if flag else ''}", flush=True)
        if flag: rows.append((int(n), k, x[1]))
print(f"STATES_CHECK {bad} bad")
if a.sheet and rows:
    tiles = []
    for n, k, d in rows[:12]:
        im = Image.open(os.path.join(a.states, "png", f"slide_{n:02d}_k{k}.png")).convert("RGB").resize((W, H))
        arr = np.asarray(im).copy(); arr[d] = (arr[d] * 0.3 + np.array([255, 0, 0]) * 0.7).astype(np.uint8)
        tiles.append(Image.fromarray(arr).resize((640, 360)))
    sheet = Image.new("RGB", (1280, 360 * ((len(tiles) + 1) // 2)), "black")
    for i, t in enumerate(tiles): sheet.paste(t, ((i % 2) * 640, (i // 2) * 360))
    sheet.save(a.sheet)
