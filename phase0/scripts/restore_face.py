"""Post-process: GFPGAN face restoration + Lab colour grade, per frame.
usage: restore_face.py in.mp4 out_noaudio.mp4 [weight=0.5] [strength=0.8]
"""
import sys, cv2, numpy as np, torch
from gfpgan import GFPGANer
src, dst = sys.argv[1], sys.argv[2]
w = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
s = float(sys.argv[4]) if len(sys.argv) > 4 else 0.8
r = GFPGANer(model_path='/w/GFPGANv1.4.pth', upscale=1, arch='clean', channel_multiplier=2, bg_upsampler=None)
cap = cv2.VideoCapture(src); fps = cap.get(cv2.CAP_PROP_FPS)
W, H = int(cap.get(3)), int(cap.get(4))
out = cv2.VideoWriter(dst, cv2.VideoWriter_fourcc(*'mp4v'), fps, (W, H))
n = 0
while True:
    ok, f = cap.read()
    if not ok: break
    _, _, g = r.enhance(f, has_aligned=False, only_center_face=True, paste_back=True, weight=w)
    o = cv2.addWeighted(g, s, f, 1 - s, 0)
    out.write(o); n += 1
    if n % 100 == 0: print(n, flush=True)
out.release()
