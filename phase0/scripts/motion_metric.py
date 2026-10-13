import cv2, sys, numpy as np
def shift(a, b):  # phase correlation, returns (dx, dy) of b relative to a
    w = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    A = np.fft.fft2(a*w); B = np.fft.fft2(b*w); R = A*np.conj(B); R /= np.abs(R)+1e-9
    r = np.fft.ifft2(R).real; y, x = np.unravel_index(np.argmax(r), r.shape)
    if y > a.shape[0]//2: y -= a.shape[0]
    if x > a.shape[1]//2: x -= a.shape[1]
    return x, y
PICK = sys.argv[1] == '--pick'
best = (-1, None)
for f in sys.argv[(2 if PICK else 1):]:
    cap = cv2.VideoCapture(f); fr = []
    while True:
        ok, im = cap.read()
        if not ok: break
        fr.append(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32))
    H, W = fr[0].shape; y0,y1,x0,x1 = int(.12*H), int(.78*H), int(.2*W), int(.8*W)
    reg = [g[y0:y1, x0:x1] for g in fr]
    d = np.array([shift(reg[0], r) for r in reg[1:]], dtype=float)
    # also consecutive-frame motion energy in region (captures tilt / non-rigid moves)
    en = np.mean([np.abs(reg[i+1]-reg[i]).mean() for i in range(len(reg)-1)])
    rng = d.max(0)-d.min(0)
    if PICK:
        if en > best[0]: best = (en, f)
        continue
    print(f"{f.split('/')[-2]}: {len(fr)} fr | head shift range x={rng[0]/W*100:.1f}% y={rng[1]/H*100:.1f}% | max |dx|={np.abs(d[:,0]).max()/W*100:.1f}% max |dy|={np.abs(d[:,1]).max()/H*100:.1f}% | motion energy {en:.2f}")
if PICK: print(best[1])
