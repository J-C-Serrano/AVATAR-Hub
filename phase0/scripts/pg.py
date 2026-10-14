#!/usr/bin/env python3
"""Register/update progress tasks shown by progress_all.py.
  pg.py dir    <name> <path rel phase0> <total_gb>
  pg.py log    <name> <path rel phase0> [regex] [repeat: number of tqdm loops/chunks]
  pg.py count  <name> <glob rel phase0> <total>
  pg.py manual <name> <done> <total> [note]
  pg.py rm     <name>"""
import json, os, re, sys
PD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "progress"); os.makedirs(PD, exist_ok=True)
a = sys.argv[1:]; f = lambda n: os.path.join(PD, re.sub(r"\W+", "_", n) + ".json")
k, n = a[0], a[1]
if k == "rm":
    try: os.remove(f(n))
    except OSError: pass
    sys.exit()
d = {"name": n, "kind": k}
if k == "dir": d.update(path=a[2], total_gb=float(a[3]))
elif k == "log": d.update(path=a[2], regex=a[3] if len(a) > 3 else r"(\d+)/(\d+)", repeat=int(a[4]) if len(a) > 4 else 1)
elif k == "count": d.update(glob=a[2], total=int(a[3]))
elif k == "manual": d.update(done=float(a[2]), total=float(a[3]), note=" ".join(a[4:]))
json.dump(d, open(f(n), "w"))
