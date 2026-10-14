#!/usr/bin/env python3
"""ONE live progress view for everything (same command every session):
    ./phase0/scripts/progress_all.py          (from the 'AVATAR Hub' directory)
Tasks come from phase0/progress/*.json, managed with scripts/pg.py. Kinds:
  dir     {"name","kind":"dir","path":<rel to phase0>,"total_gb":N}          bar = folder size
  log     {"name","kind":"log","path":<rel>,"regex":"(\\d+)/(\\d+)"}          bar = last regex match in a log
  count   {"name","kind":"count","glob":<rel glob>,"total":N}                bar = files matching glob
  manual  {"name","kind":"manual","done":x,"total":y}                        bar = values set via pg.py
Finished tasks stay listed until removed (pg.py rm <name>)."""
import glob, json, os, re, subprocess, sys, time
P0 = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PD = os.path.join(P0, "progress")
def dsize(p):
    try: return int(subprocess.run(["du", "-sb", p], capture_output=True, text=True).stdout.split()[0])
    except Exception: return 0
def frac(t):
    k = t.get("kind")
    try:
        if k == "dir": return min(1, dsize(os.path.join(P0, t["path"])) / (t["total_gb"] * 1e9)), ""
        if k == "count": return min(1, len(glob.glob(os.path.join(P0, t["glob"]))) / t["total"]), ""
        if k == "manual": return min(1, t["done"] / max(t["total"], 1)), t.get("note", "")
        if k == "log":
            s = open(os.path.join(P0, t["path"]), errors="ignore").read().replace("\r", "\n")
            m = re.findall(t.get("regex", r"(\d+)/(\d+)"), s)
            if not m: return 0, ""
            cur = int(m[-1][0]) / int(m[-1][1]); R = t.get("repeat", 1)   # repeat = number of tqdm loops (e.g. chunks)
            full = len([x for x in m if x[0] == x[1]]) - (1 if cur >= 1 else 0)
            # count distinct completed loops: a finished loop prints n/n at least once
            done = len(re.findall(r"(?<!\d)(\d+)/\1 \[", s)) if R > 1 else 0
            done = min(done, R)
            f = (done + (cur if cur < 1 else 0)) / R
            return min(1, f), (f"chunk {min(done + 1, R)}/{R}" if R > 1 else "")
    except Exception: pass
    return 0, ""
def bar(f, w=34): n = int(f * w); return "█" * n + "░" * (w - n)
def hms(s): s = int(s); return f"{s//3600}:{s%3600//60:02d}:{s%60:02d}" if s >= 3600 else f"{s//60}:{s%60:02d}"
hist = {}
while True:
    tasks = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(PD, "*.json")))]
    lines = [f"AVATAR Hub progress — {time.strftime('%H:%M:%S')}   (Ctrl-C to quit)", ""]
    for t in tasks:
        f, note = frac(t); now = time.time(); n = t["name"]
        hist.setdefault(n, []).append((now, f)); hist[n] = [h for h in hist[n] if now - h[0] < 300]
        h = hist[n]; eta = "done" if f >= 1 else "…"
        if f < 1 and len(h) > 2 and h[-1][1] > h[0][1]:
            eta = "ETA " + hms((1 - f) * (h[-1][0] - h[0][0]) / (h[-1][1] - h[0][1]))
        lines.append(f" {n[:28]:<28} {bar(f)} {f*100:5.1f}%  {eta} {note}")
    ps = subprocess.run(["docker", "ps", "--format", "{{.Image}}  {{.Status}}"], capture_output=True, text=True).stdout.strip()
    lines += ["", " containers running:", *(["   " + l for l in ps.splitlines()] or ["   (none)"])]
    sys.stdout.write("\033[2J\033[H" + "\n".join(lines) + "\n"); sys.stdout.flush()
    if "--once" in sys.argv: break
    time.sleep(3)
