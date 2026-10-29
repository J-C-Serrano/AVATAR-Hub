"""Repair pdf_states.py build states against the recording (what the class saw at that moment), in place.
usage: python3 states_repair.py <recording.mp4> <states dir> [--sheet review.png] [--collapse 6,9] [--dry]
Per build state (the slide's last state is the full PDF page P):
  only where the state visibly differs from the recording (median of 5 frames of that state, so a moving pointer is
  dropped) is it changed: to the page's pixels where the page looks like the recording there (wiped borders, titles,
  footers), else to plain background (a later build not hidden; the same fill as pdf_states.py). Raw recording
  pixels are never pasted: the recording is offset ~3 px from the PDF and would leave seams. Compared at 1/4 resolution, so letter edges, re-encoding shifts and faint ghosts do not count.
The right strip (webcam / logo) is never touched. Originals are kept as png/orig/. Check with states_check.py."""
import argparse, json, os, shutil, subprocess
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("states"); ap.add_argument("--dry", action="store_true")
ap.add_argument("--collapse", default="", help="slides whose PDF page differs from the deck the teacher used (seen on the review sheet): full page from the start, no build-up")
ap.add_argument("--lines", default="", help="text slides rebuilt line by line from the page: each line (or picture) shown when the recording shows it, else plain background")
ap.add_argument("--sheet", help="png: each changed state next to the recording, for review")
a = ap.parse_args()
W, H, CAM_X = 1920, 1080, 1560
# not comparable: the recording's webcam (top right) and its logo (bottom right; the PDF has it top right)
EXCL = np.zeros((H, W), bool); EXCL[:230, CAM_X:] = True; EXCL[850:, CAM_X:] = True
LOGO = (1570, 40, 1830, 195)                          # x0, y0, x1, y1 of the deck's logo (as in pdf_states.py)
FOOT = (995, 1032)
F = 4
N9_ = np.ones((9, 9))                                    # y range of the deck's footer line
NEAR = np.ones((7, 7))                                # video compression shifts and blurs strokes by a few px


def frame(t):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", a.video, "-frames:v", "1",
                          "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3) if len(raw) == W * H * 3 else None


def ink(x, thr=45):
    x = x.astype(np.float32)
    return np.abs(x - ndi.median_filter(x, size=(15, 15, 1))).max(2) > thr


def blobs(m, min_px=30):
    """drop specks (compression noise), keep strokes and areas"""
    lab, n = ndi.label(m, np.ones((3, 3)))
    if not n: return m
    size = ndi.sum(m, lab, range(1, n + 1))
    return np.isin(lab, 1 + np.flatnonzero(size >= min_px))


def lacks(R, V):
    """share of the recording's ink that R lacks or shows extra (states_check.py's measure)"""
    iV, iR = ink(V), ink(R); iV[EXCL] = iR[EXCL] = False
    d = (iV & ~ndi.binary_dilation(iR, NEAR)) | (iR & ~ndi.binary_dilation(iV, NEAR))
    return ndi.binary_opening(d, np.ones((2, 2))).sum() / max(iV.sum(), 1)


def fill(S, V, h):
    """recording background (median-smoothed) under h, levels matched to the state on a ring around each area"""
    S = S.copy(); Vm = ndi.median_filter(V, size=(7, 7, 1)).astype(np.int16)
    lab, n = ndi.label(h)
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        sl = tuple(slice(max(0, x.start - 12), x.stop + 12) for x in sl)
        c = lab[sl] == i; ring = ndi.binary_dilation(c, np.ones((9, 9))) & ~h[sl]
        if ring.sum() > 20 and S[sl][ring].std(0).max() < 4:      # plain background: its own colour
            S[sl][c] = np.median(S[sl][ring], 0).astype(np.uint8); continue
        off = np.median(S[sl][ring].astype(np.int16) - Vm[sl][ring], 0) if ring.sum() > 20 else 0
        S[sl][c] = np.clip(Vm[sl][c] + off, 0, 255).astype(np.uint8)
    return S


rev = json.load(open(os.path.join(a.states, "reveals.json")))
png = lambda n, k: os.path.join(a.states, "png", f"slide_{n:02d}_k{k}.png")
os.makedirs(os.path.join(a.states, "png", "orig"), exist_ok=True)
finals = [np.asarray(Image.open(png(int(n), len(r["builds"]))).convert("RGB"))[LOGO[1]:LOGO[3], LOGO[0]:LOGO[2]]
          for n, r in rev.items() if os.path.exists(png(int(n), len(r["builds"])))]
LOGO_REF = np.median(np.stack(finals), 0).astype(np.uint8)   # the plain logo: most slides have nothing over it
LINES = set(int(x) for x in filter(None, a.lines.split(",")))
KEEP_LOGO = set()
tiles = []
total, collapse = 0, set(int(x) for x in filter(None, a.collapse.split(",")))
for key, r in sorted(rev.items(), key=lambda x: int(x[0])):
    n, b = int(key), r["builds"]
    if not b or not os.path.exists(png(n, len(b))): continue
    P = np.asarray(Image.open(png(n, len(b))).convert("RGB")); iP = ink(P)
    edges = [r["t0"]] + b + [r["t1"]]
    for k in range(len(b)):                                   # the last state is the full page: nothing to repair
        t0, t1 = edges[k], edges[k + 1]
        if t1 - t0 < 1.0 or not os.path.exists(png(n, k)): continue
        fr = [f for f in (frame(t0 + (t1 - t0) * q) for q in (0.15, 0.32, 0.5, 0.68, 0.85)) if f is not None]
        if not fr: continue
        V = np.median(np.stack(fr), 0).astype(np.uint8)          # a moving pointer is not baked into the slide
        S = np.asarray(Image.open(png(n, k)).convert("RGB"))
        if n in LINES:                                         # line mode: whole lines/pictures of the page, shown or hidden
            iVl = ink(V, 25); iVl[EXCL] = False
            lines, nl = ndi.label(ndi.binary_dilation(iP & ~EXCL, np.ones((5, 41))))
            R = P.copy(); hide = np.zeros((H, W), bool)
            for i in range(1, nl + 1):
                m = lines == i; own = iP & m
                if own.sum() < 15: continue
                seen = (ndi.binary_dilation(iVl, N9_) & own).sum() / own.sum()
                if seen < 0.5: hide |= ndi.binary_dilation(m, np.ones((5, 5)))
            hide &= ~EXCL
            if hide.any(): R = fill(R, V, hide)
            x0, y0, x1, y1 = LOGO; R[y0:y1, x0:x1] = LOGO_REF if n not in KEEP_LOGO else P[y0:y1, x0:x1]
            pg, rv = ~hide, hide; bad = hide[::F, ::F]
            if not np.array_equal(R, S):
                total += 1; print(f"slide {n:2d} k{k}: line mode, {int(hide.sum())} px hidden", flush=True)
                if a.sheet: tiles.append((n, k, R, V))
                if not a.dry:
                    o = os.path.join(a.states, "png", "orig", os.path.basename(png(n, k)))
                    if not os.path.exists(o): shutil.copy(png(n, k), o)
                    Image.fromarray(R).save(png(n, k))
            continue
        # compare at 1/4 resolution: letter edges, anti-aliasing and 1-2 px re-encoding shifts vanish there, while a
        # missing line, a wiped box or an early build still differs by far more than TOL
        TOL, F = 35, 4
        down = lambda X: ndi.gaussian_filter(X.reshape(H // F, F, W // F, F, 3).mean((1, 3)), (0.8, 0.8, 0))
        up = lambda m: np.repeat(np.repeat(m, F, 0), F, 1)
        rng = lambda X: (ndi.minimum_filter(X, size=(3, 3, 1)) - TOL, ndi.maximum_filter(X, size=(3, 3, 1)) + TOL)
        Vd = down(V.astype(np.float32)); Vlo, Vhi = rng(Vd)
        def ok(X):
            """both ways within 1 coarse px (4 px): the PDF renderer spaces text up to ~3 px differently from the deck"""
            Xd = down(X.astype(np.float32)); Xlo, Xhi = rng(Xd)
            return (((Xd >= Vlo) & (Xd <= Vhi)) & ((Vd >= Xlo) & (Vd <= Xhi))).all(2)
        bad = ~ok(S) & ~EXCL[::F, ::F]
        lab, nb = ndi.label(bad, np.ones((3, 3)))
        if nb: bad = np.isin(lab, 1 + np.flatnonzero(ndi.sum(bad, lab, range(1, nb + 1)) >= 3))
        okP = ndi.binary_erosion(up(ok(P)), np.ones((3, 3)))
        R = S
        if bad.any():
            wrong = ndi.binary_dilation(up(bad), np.ones((5, 5))) & ~EXCL
            pg = wrong & okP; rv = wrong & ~pg
            R = S.copy(); R[pg] = P[pg]                        # the class saw the page's content there: exact pixels
            # the page is not what the class saw either (a later build not hidden): plain background, never raw
            # recording pixels (the PDF renderer spaces text ~3 px differently, they would leave seams)
            if rv.any(): R = fill(R, V, rv)
        # faint details at full resolution (footers, source lines, thin lines), +-4 px: too faint for the 1/4 test
        N9 = np.ones((9, 9)); iR, iV = ink(R), ink(V, 25); iV[EXCL] = False   # 25: grey footers/source lines
        lost = blobs(iV & ~ndi.binary_dilation(iR, NEAR) & ndi.binary_dilation(iP, N9), 20)
        lost = ndi.binary_dilation(lost, np.ones((5, 5))) & okP & ~EXCL
        early = blobs(iR & ~ndi.binary_dilation(ink(V), N9) & ndi.binary_dilation(iP, NEAR), 20)
        early = ndi.binary_dilation(early, np.ones((5, 5))) & ~lost & ~EXCL
        if lost.any() or early.any():
            R = R.copy() if R is S else R; R[lost] = P[lost]
            if early.any(): R = fill(R, V, early)
            pg = pg | lost if bad.any() else lost; rv = rv | early if bad.any() else early
        if not bad.any() and not (lost.any() or early.any()): pg = rv = np.zeros((H, W), bool)
        # footer line: the same on every slide; back from the page wherever the recording shows it
        fb = (slice(FOOT[0], FOOT[1]), slice(0, CAM_X))
        fV = ndi.binary_dilation(iV[fb], N9)
        line = ndi.binary_dilation(ndi.binary_opening(iP[fb], np.ones((1, 61))), np.ones((3, 1)))   # long edges only the PDF may have
        lab, nl = ndi.label(iP[fb] & ~line, np.ones((3, 3)))   # the page's footer ink, letter by letter
        if nl:
            seen = ndi.maximum(fV, lab, range(1, nl + 1))
            letters = np.isin(lab, 1 + np.flatnonzero(seen))   # letters the class saw
        else: letters = np.zeros_like(fV)
        fP = ndi.binary_dilation(iP[fb], N9); fm = ndi.binary_dilation(letters, np.ones((5, 5))) & ~line
        if fm.sum() > 0.3 * max(fP.sum(), 1) and not np.array_equal(R[fb][fm], P[fb][fm]):
            R = R.copy() if R is S else R; R[fb] = np.where(fm[..., None], P[fb], R[fb]); pg[fb] |= fm
        # logo box (pdf_states never hides it): a later build overlapping the logo (e.g. a starburst) shows through it;
        # unless that build is already on screen next to the box, use the deck's plain logo
        x0, y0, x1, y1 = LOGO; lb = (slice(y0, y1), slice(x0, x1)); ring = (slice(y0, y1 + 40), slice(x0 - 60, x0))
        if np.abs(S[lb].astype(np.int16) - LOGO_REF).max(2).__gt__(60).mean() > 0.02 and \
                np.abs(R[ring].astype(np.int16) - P[ring]).max(2).__gt__(60).mean() > 0.05:
            R = R.copy() if R is S else R; R[lb] = LOGO_REF; pg[lb] = True
        if R is S: continue
        total += 1
        if a.sheet: tiles.append((n, k, R, V))
        print(f"slide {n:2d} k{k}: {int(pg.sum())} px from page, {int(rv.sum())} px hidden", flush=True)
        if not a.dry:
            o = os.path.join(a.states, "png", "orig", os.path.basename(png(n, k)))
            if not os.path.exists(o): shutil.copy(png(n, k), o)
            Image.fromarray(R).save(png(n, k))
for n in sorted(collapse):
    k_last = len(rev[str(n)]["builds"])
    print(f"slide {n:2d}: collapsed (PDF differs from the deck used), full page from the start", flush=True)
    if not a.dry:
        for k in range(k_last):
            o = os.path.join(a.states, "png", "orig", os.path.basename(png(n, k)))
            if not os.path.exists(o): shutil.copy(png(n, k), o)
            shutil.copy(png(n, k_last), png(n, k))
if a.sheet and tiles:
    from PIL import ImageDraw
    sh = Image.new("RGB", (1280, 360 * len(tiles)), "black")
    for i, (n, k, R, V) in enumerate(tiles):
        sh.paste(Image.fromarray(R).resize((640, 360)), (0, 360 * i)); sh.paste(Image.fromarray(V).resize((640, 360)), (640, 360 * i))
        ImageDraw.Draw(sh).text((8, 360 * i + 4), f"slide {n} k{k}", fill=(255, 0, 0))
    sh.save(a.sheet)
print(f"STATES_REPAIR {total} states changed, {len(collapse)} slides collapsed{' (dry run)' if a.dry else ''}")
