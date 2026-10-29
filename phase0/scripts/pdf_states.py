"""Build-up states for a lecture from the teacher's PDF slides, with the animation order/timing taken from a recording.
usage: python3 pdf_states.py <recording.mp4> <segments.json> <out states dir> [--debug]
segments.json: [{"pdf": "deck.pdf", "page": 7, "t0": 22.5, "t1": 31.0}, ...] in slide order (one slide per entry;
               {"image": "x.png"} instead of pdf/page for a slide that is in no PDF; "static": true = no build-up).
The PDF page is rendered at 1920x1080 and must line up with the recording's slide area (same deck, full frame).
Within each segment the recording's stable states (>= 1.5 s, webcam box masked) are found; for each state, whatever
the PDF page shows but the recording shows as flat background is hidden (filled with the recording's background,
median-smoothed). Content that is still hidden at the end of the segment (only in the PDF) is shown from the start.
Writes png/slide_NN_kK.png + units.json (lecture_compose.py format) and reveals.json (recording time of each build)."""
import argparse, json, os, subprocess, tempfile
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("segments"); ap.add_argument("out")
ap.add_argument("--debug", action="store_true")
ap.add_argument("--logo", help="deck.pdf:page with the plain logo; only its ink in the logo box is kept visible")
a = ap.parse_args()
W, H, FPS = 1920, 1080, 2
CAM = (1590, 185)                                  # webcam overlay box: x >= CAM[0], y < CAM[1]
LOGO = (1570, 40, 1830, 195)                       # x0, y0, x1, y1 of the logo under the webcam box
segs = json.load(open(a.segments)); base = os.path.dirname(os.path.abspath(a.segments))
os.makedirs(os.path.join(a.out, "png"), exist_ok=True)

# low-res pass for the state boundaries (same rules as the mapping step)
sw, sh = 192, 108
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-vf", f"fps={FPS},scale={sw}:{sh},format=gray", "-f", "rawvideo", "-"],
                     capture_output=True, check=True).stdout
lo = np.frombuffer(raw, np.uint8).reshape(-1, sh, sw).astype(np.int16)
lmask = np.ones((sh, sw), bool); lmask[:int(.20 * sh), int(.80 * sw):] = False


def states_in(t0, t1):
    i0, i1 = int(round(t0 * FPS)), min(len(lo), int(round(t1 * FPS)))
    ch = [0.0] + [float(((np.abs(lo[i] - lo[i - 1]) > 24) & lmask).mean()) for i in range(i0 + 1, i1)]
    cuts = [0] + [k for k, c in enumerate(ch) if c > 0.003] + [i1 - i0]
    st, s = [], 0
    for c in cuts[1:]:
        if c - s >= 3: st.append((i0 + s, i0 + c - 1))
        s = c
    return [((x) / FPS, (y + 1) / FPS) for x, y in st] or [(t0, t1)]


def frame(t):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", a.video, "-frames:v", "1", "-vf", f"scale={W}:{H}",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(r, np.uint8).reshape(H, W, 3)


_pages = {}
def page(pdf, n):
    k = (pdf, n)
    if k not in _pages:
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["pdftoppm", "-f", str(n), "-l", str(n), "-scale-to-x", str(W), "-scale-to-y", str(H), "-png",
                            os.path.join(base, pdf) if not os.path.isabs(pdf) else pdf, os.path.join(d, "p")], check=True)
            _pages[k] = np.asarray(Image.open(os.path.join(d, sorted(os.listdir(d))[0])).convert("RGB"))
    return _pages[k]


def hidden(P, V):
    """pixels the page has but the recording shows as plain background."""
    Pf, Vf = P.astype(np.int16), V.astype(np.int16)
    d = ndi.uniform_filter(np.abs(Pf - Vf).max(2).astype(np.float32), 3) > 40
    g = Vf.mean(2).astype(np.float32); m = ndi.uniform_filter(g, 7); flat = ndi.uniform_filter(g * g, 7) - m * m < 40
    h = d & flat; cam = np.zeros((H, W), bool); cam[:CAM[1], CAM[0]:] = True; h &= ~cam
    h = ndi.binary_closing(h, np.ones((9, 9)))
    # size filter on line-sized groups, so bullet markers go with their text
    lab, n = ndi.label(ndi.binary_dilation(h, np.ones((15, 61))))
    if n:
        sz = ndi.sum(h, lab, range(1, n + 1)); h &= np.isin(lab, 1 + np.flatnonzero(sz >= 150))
    h = ndi.binary_dilation(h, np.ones((13, 13)))
    # page content touching a hidden area that the recording lacks too (near edges, so not "flat" there) and,
    # under the webcam box where the recording says nothing, any page content touching a hidden area
    if h.any():
        pc = ndi.binary_dilation(np.abs(Pf - ndi.median_filter(Pf, size=(21, 21, 1))).max(2) > 25, np.ones((9, 9)))
        grow = ndi.binary_dilation(h, np.ones((3, 3)), iterations=0, mask=h | (pc & (ndi.binary_dilation(d, np.ones((5, 5))) | cam)))
        h = ndi.binary_dilation(grow, np.ones((7, 7)))
    lb = h[LOGO[1]:LOGO[3], LOGO[0]:LOGO[2]]                 # the deck's logo never hides
    if LREF is None: lb[:] = False
    else: lb &= ~(LREF & (np.abs(Pf[LOGO[1]:LOGO[3], LOGO[0]:LOGO[2]] - LIMG).max(2) < 40))
    return h


def fill(P, V, h):
    """recording background (median-smoothed) under h, levels matched to the page on a ring around each area."""
    S = P.copy(); Vm = ndi.median_filter(V, size=(7, 7, 1)).astype(np.int16)
    lab, n = ndi.label(h)
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        sl = tuple(slice(max(0, x.start - 12), x.stop + 12) for x in sl)
        c = lab[sl] == i; ring = ndi.binary_dilation(c, np.ones((9, 9))) & ~h[sl]
        oncam = sl[0].start < CAM[1] and sl[1].stop > CAM[0]       # the recording there is the webcam: never use it
        if ring.sum() > 20 and (oncam or P[sl][ring].std(0).max() < 4):   # plain background: the page's own colour
            S[sl][c] = np.median(P[sl][ring], 0).astype(np.uint8); continue
        if oncam: S[sl][c] = 255; continue
        off = np.median(P[sl][ring].astype(np.int16) - Vm[sl][ring], 0) if ring.sum() > 20 else 0
        S[sl][c] = np.clip(Vm[sl][c] + off, 0, 255).astype(np.uint8)
    return S


LREF = LIMG = None
if a.logo:
    f, n = a.logo.rsplit(":", 1); L = page(f, int(n)).astype(np.int16)[LOGO[1]:LOGO[3], LOGO[0]:LOGO[2]]
    LIMG = L; LREF = ndi.binary_dilation(L.min(2) < 235, np.ones((5, 5)))
units, reveals = [], {}
for n, s in enumerate(segs, 1):
    P = page(s["pdf"], s["page"]) if "pdf" in s else np.asarray(Image.open(os.path.join(base, s["image"])).convert("RGB").resize((W, H)))
    st = [] if s.get("static") else states_in(s["t0"], s["t1"])
    imgs, times = [], []
    if len(st) > 1:
        Hs, Vs = [], []
        for x, y in st:
            V = frame(max(x, y - 0.4)); Hs.append(hidden(P, V)); Vs.append(V)
        last = Hs[-1]
        prev = None
        for (x, y), h, V in zip(st, Hs, Vs):
            h = h & ~last
            if prev is not None and (h ^ prev).sum() < 400: continue      # same build state (cursor, flicker)
            imgs.append(fill(P, V, h)); times.append(round(x, 2)); prev = h
        if prev is not None and prev.any(): imgs.append(P.copy()); times.append(round(st[-1][0], 2))
    if not imgs: imgs, times = [P.copy()], [s.get("t0", 0.0)]
    for k, im in enumerate(imgs): Image.fromarray(im).save(os.path.join(a.out, "png", f"slide_{n:02d}_k{k}.png"))
    units.append({"slide": n, "units": [{"kind": "shapes", "text": ""} for _ in imgs[1:]]})
    reveals[n] = {"t0": s.get("t0"), "t1": s.get("t1"), "builds": times[1:]}
    print(f"slide {n:2d}  {s.get('pdf', s.get('image'))}:{s.get('page', '')}  {len(st)} rec states -> {len(imgs) - 1} builds", flush=True)
json.dump(units, open(os.path.join(a.out, "units.json"), "w"), indent=1)
json.dump(reveals, open(os.path.join(a.out, "reveals.json"), "w"), indent=1)
