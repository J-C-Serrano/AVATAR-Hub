#!/usr/bin/env python3
"""Live progress for everything: 4 head-motion variants (mv_v0..v3) then the 384 demo (demo384, 11 segments).
Run:  ./phase0/scripts/progress_all.py"""
import glob, os, re, time, sys
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
STAGES = [("variants", [f"mv_v{i}" for i in range(4)]), ("demo384", [f"demo384/seg_{k}" for k in range(11)])]
TOTAL = sum(len(u) for _, u in STAGES)
def step_of(logpath):
    try: t = open(logpath, errors="ignore").read().replace("\r", "\n")
    except OSError: return 0
    m = re.findall(r"(\d+)/8 \[", t); return int(m[-1]) if m else 0
def unit_files(u):
    return glob.glob(os.path.join(OUT, u, "*_output.mp4"))
def logfor(u):
    if u.startswith("mv_"): return os.path.join(OUT, u + ".log")
    seg = u.split("/")[-1].split("_")[1]; return os.path.join(OUT, "demo384", f"log_{seg}.txt")
t0 = time.time()
while True:
    units = [u for _, us in STAGES for u in us]
    done = [u for u in units if unit_files(u)]
    cur = next((u for u in units if u not in done), None)
    frac_cur = 0
    if cur and os.path.exists(logfor(cur)):
        frac_cur = 0.45 + 0.55 * step_of(logfor(cur)) / 8   # ~45% of a unit is model load
        if time.time() - os.path.getmtime(logfor(cur)) > 600: frac_cur = 0
    n = len(done) + (frac_cur if cur else 0)
    mt = sorted(os.path.getmtime(unit_files(u)[0]) for u in done)
    per = (mt[-1] - mt[0]) / (len(mt) - 1) if len(mt) >= 2 else None
    eta = f"{int(per*(TOTAL-n))//60}m{int(per*(TOTAL-n))%60:02d}s" if per else "--"
    stage = next((nm for nm, us in STAGES if cur in us), "finished")
    final = os.path.exists(os.path.join(OUT, "demo384_final.mp4"))
    f = 1.0 if final else min(n / TOTAL, 0.999)
    bar = int(40 * f)
    label = "ALL DONE" if final else f"{stage}: {cur.split('/')[-1] if cur else '-'}"
    print(f"\r\033[K[{'█'*bar}{'░'*(40-bar)}] {f*100:3.0f}%  {len(done)}/{TOTAL} units  {label}  ETA {eta if not final else '0'}", end="", flush=True)
    if final: print("\nout/demo384_final.mp4"); break
    time.sleep(2)
