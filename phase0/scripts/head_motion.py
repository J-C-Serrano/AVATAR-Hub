"""Prosody-driven head motion shared by the 3D (Blender) and photo (LivePortrait) avatars.
compute(prosody_dict, amp=1.0, seed=11) -> dict of per-frame arrays (degrees):
  pitch (+ = nod down / chin down), yaw (turn), roll (tilt), blink [0..1], melody (semitones, high-passed), lean, starts (phrase start frames)
Sign convention follows the Blender MPFB Head bone (x+ nod down). Callers map to their own axes."""
import math
import numpy as np


def compute(P, amp=1.0, seed=11):
    FPS = int(P["fps"]); AMP = amp
    rng = np.random.default_rng(seed)

    def lp(x, sec):  # zero-phase smoothing (two-pass exponential)
        k = 1 - math.exp(-1 / (sec * FPS)); y = np.copy(x).astype(float)
        for i in range(1, len(y)): y[i] = y[i - 1] * (1 - k) + y[i] * k
        for i in range(len(y) - 2, -1, -1): y[i] = y[i + 1] * (1 - k) + y[i] * k
        return y

    st = np.clip(np.array(P["f0_st"]), -6, 6); E = np.array(P["energy"]); ON = np.array(P["onset"]); PZ = np.array(P["pause"])
    N = len(st)


    # 1) melody: chin follows smoothed pitch (relative to a slow baseline so declination doesn't tilt the head forever)
    melody = lp(st, 0.18) - lp(st, 1.5)
    chin = -2.2 * melody                                   # deg, x- = chin up when pitch rises
    # 2) beats: nods on stressed syllables (onset peaks with energy, min spacing 0.35 s)
    beat = np.zeros(N); last = -99
    for i in range(1, N - 1):
        if ON[i] > 0.45 and ON[i] >= ON[i - 1] and ON[i] >= ON[i + 1] and E[i] > 0.3 and i - last > 0.35 * FPS:
            beat[i] = ON[i] * min(E[i], 1.0); last = i
    kern = np.array([math.sin(math.pi * j / 9) for j in range(10)])   # ~300 ms down-and-back
    nod = np.convolve(beat, kern, "full")[:N] * 3.2      # deg, x+ = down
    # 3) phrases: new turn/tilt target at each phrase start
    starts = [0] + [i for i in range(1, N) if PZ[i - 1] > 0 and PZ[i] == 0]
    yaw_t, roll_t = np.zeros(N), np.zeros(N); cur_y = 0
    for j, s in enumerate(starts):
        e = starts[j + 1] if j + 1 < len(starts) else N
        cur_y = float(np.clip(-cur_y * 0.5 + rng.uniform(-6, 6), -7, 7))   # alternate sides, natural spread
        yaw_t[s:e] = cur_y; roll_t[s:e] = rng.uniform(-2.5, 2.5)
    yaw = lp(yaw_t, 0.45); roll = lp(roll_t, 0.6) + 1.5 * lp(np.gradient(lp(st, 0.3)), 0.3) * FPS / 10
    # 4) energy: slight lean-in when emphatic; pauses settle
    lean = 1.5 * lp(E, 0.5); settle = 1 - 0.6 * lp(PZ, 0.3)
    micro = lp(rng.standard_normal(N), 0.8) * 0.6          # tiny life noise
    hx = AMP * (settle * (chin + nod) + micro + lean * 0.5)
    hy = AMP * (yaw + micro * 0.8); hz = AMP * (roll * settle)
    # blinks: random 2.5-5 s plus at phrase starts
    blink = np.zeros(N); t = rng.uniform(0.5, 2)
    bl = [int(t * FPS)]
    while t < N / FPS: t += rng.uniform(2.5, 5.0); bl.append(int(t * FPS))
    bl += [s + 2 for s in starts[1:]]
    for f0 in bl:
        for d_, v in enumerate((0.6, 1.0, 1.0, 0.5)):
            if 0 <= f0 + d_ < N: blink[f0 + d_] = max(blink[f0 + d_], v)
    return {"pitch": hx, "yaw": hy, "roll": hz, "blink": blink, "melody": melody, "lean": lean, "starts": starts,
            "beats": int((beat > 0).sum()), "fps": FPS, "n": N}


def loop(seconds, fps=30, amp=1.0, seed=5):
    """Seamless idle/talking loop: every component is a sum of sines with a whole number of cycles over the loop,
    so frame N == frame 0. Blinks avoid the seam. Same output keys/signs as compute()."""
    rng = np.random.default_rng(seed)
    N = int(round(seconds * fps)); t = np.arange(N) / N          # 0..1 over the loop

    def periodic(spec):  # spec: [(cycles, amplitude_deg)], random phase each
        return sum(a * np.sin(2 * np.pi * k * t + rng.uniform(0, 2 * np.pi)) for k, a in spec)
    L = seconds  # cycles chosen so periods are ~1.5-10 s
    c = lambda period: max(1, round(L / period))
    pitch = periodic([(c(9), 2.0), (c(4.5), 1.4), (c(2.2), 1.0), (c(1.3), 0.6)])      # slow drift + talking nods
    yaw = periodic([(c(10), 4.5), (c(5), 2.0), (c(2.7), 0.8)])
    roll = periodic([(c(11), 2.0), (c(6), 1.0)])
    blink = np.zeros(N); f = int(rng.uniform(0.8, 1.6) * fps)
    while f < N - int(0.6 * fps):                                 # keep the seam clear of blinks
        for d_, v in enumerate((0.6, 1.0, 1.0, 0.5)): blink[f + d_] = v
        f += int(rng.uniform(2.8, 5.0) * fps)
    z = np.zeros(N)
    return {"pitch": amp * pitch, "yaw": amp * yaw, "roll": amp * roll, "blink": blink, "melody": z, "lean": z,
            "starts": [0], "beats": 0, "fps": fps, "n": N}
