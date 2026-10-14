"""Two threads generating at the same time on the shared engine must not crash (lock + hook cleanup)."""
import sys, threading, time; sys.path.insert(0, "/hub/app")
from engine import Engine
e = Engine(); V = "/hub/data/voices/julio-serrano/"
errs, n_hooks = [], []
def job(i):
    try:
        e.speak(f"This is test number {i}. It has two sentences.", "en", V + "train/ref.wav", V + "train/lora_balanced", 1.0, takes=1)
    except Exception as ex: errs.append(repr(ex))
t0 = time.time(); ts = [threading.Thread(target=job, args=(i,)) for i in range(3)]
[t.start() for t in ts]; [t.join() for t in ts]
hooks = sum(len(m._forward_hooks) for m in e.tts.t3.tfmr.modules())
print(f"errors={errs} hooks_left={hooks} time={time.time() - t0:.0f}s"); print("CONCURRENCY_OK" if not errs else "FAIL")
