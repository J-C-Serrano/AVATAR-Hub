import cv2, sys, numpy as np
f = sys.argv[1]; cap = cv2.VideoCapture(f); fr = []
while True:
    ok, im = cap.read()
    if not ok: break
    fr.append(im)
n = len(fr); print("frames", n)
hsv = [cv2.cvtColor(i, cv2.COLOR_BGR2HSV) for i in fr]
g = [cv2.cvtColor(i, cv2.COLOR_BGR2GRAY).astype(np.float32) for i in fr]
print("sec  brightness contrast(std) saturation sharpness(lapvar)")
for s in range(0, n//25, 4):
    a = s*25; b = min(n, a+25)
    br = np.mean([g[i].mean() for i in range(a,b)]); ct = np.mean([g[i].std() for i in range(a,b)])
    sat = np.mean([hsv[i][...,1].mean() for i in range(a,b)])
    sh = np.mean([cv2.Laplacian(g[i], cv2.CV_32F).var() for i in range(a,b)])
    print(f"{s:3d}  {br:7.1f} {ct:8.1f} {sat:8.1f} {sh:9.1f}")
d = np.array([np.abs(g[i+1]-g[i]).mean() for i in range(n-1)])
print(f"frame diff: mean {d.mean():.2f} p95 {np.percentile(d,95):.2f}")
print("joins (t, diff, x mean):")
for k in range(1, 11):
    i = int(round(k*3.08*25)); w = d[max(0,i-3):i+3]
    print(f"  {k*3.08:5.2f}s  max {w.max():.2f}  ({w.max()/d.mean():.1f}x)")
