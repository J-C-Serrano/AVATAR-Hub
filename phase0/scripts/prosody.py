"""Per-frame prosody features for head animation: prosody.py in.wav out.json [fps=30]
f0_st: pitch in semitones relative to the speaker's median (interpolated through unvoiced parts, 0 in long pauses)
energy: RMS normalised to ~[0,1]; onset: syllable-onset strength [0,1]; voiced: 0/1; pause: 1 inside pauses > 250 ms"""
import sys, json, numpy as np, librosa
wav, out = sys.argv[1], sys.argv[2]; fps = float(sys.argv[3]) if len(sys.argv) > 3 else 30.0
y, sr = librosa.load(wav, sr=16000); hop = int(sr / fps)
f0, vflag, _ = librosa.pyin(y, fmin=60, fmax=400, sr=sr, frame_length=1024, hop_length=hop)
n = len(f0)
rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=hop)[0][:n]
on = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)[:n]
v = np.nan_to_num(vflag.astype(float))
med = np.nanmedian(f0)
st = 12 * np.log2(f0 / med)
idx = np.arange(n); good = ~np.isnan(st)
st = np.interp(idx, idx[good], st[good]) if good.any() else np.zeros(n)
e = rms / (np.percentile(rms, 95) + 1e-9); e = np.clip(e, 0, 1.2)
silent = e < 0.08
pause = np.zeros(n)
run = 0
for i in range(n):  # mark pauses longer than 250 ms
    run = run + 1 if silent[i] else 0
    if run >= int(0.25 * fps): pause[i - run + 1:i + 1] = 1
st = np.where(pause > 0, 0, st)
on = on / (np.percentile(on, 98) + 1e-9); on = np.clip(on, 0, 1) * (1 - pause)
json.dump({"fps": fps, "median_hz": float(med), "f0_st": st.round(3).tolist(), "energy": e.round(3).tolist(),
           "onset": on.round(3).tolist(), "voiced": v.tolist(), "pause": pause.tolist()}, open(out, "w"))
print(f"frames={n} median_f0={med:.1f}Hz voiced={v.mean():.2f} pauses={pause.mean():.2f} st_range=({st.min():.1f},{st.max():.1f})")
