"""Progress must be smooth (many updates), monotonic, and end at 1.0."""
import sys, time; sys.path.insert(0, "/hub/app")
from engine import Engine
e = Engine(); V = "/hub/data/voices/julio-serrano/"
ev = []; t0 = time.time()
e.speak("Welcome to the course. Today we talk about services in manufacturing. Let's begin with a simple question.", "en",
        V + "train/ref.wav", V + "train/lora_balanced", 1.0, takes=3, progress=lambda f, m: ev.append((round(time.time() - t0, 1), round(f, 3), m)))
fs = [f for _, f, _ in ev]
mono = all(b >= a for a, b in zip(fs, fs[1:]))
print(f"updates={len(ev)} monotonic={mono} final={fs[-1]} total_time={time.time() - t0:.1f}s")
for i in range(0, len(ev), max(1, len(ev) // 14)): print("  ", ev[i])
print("  ", ev[-1]); print("PROGRESS_OK" if mono and fs[-1] == 1.0 and len(ev) > 20 else "FAIL")
