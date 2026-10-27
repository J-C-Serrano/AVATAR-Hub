"""Find fillers (eh, uh, um, hmm), stutters and non-word sounds in generated speech.
usage (in avatar-hub-app:p0): python disfl_scan.py <a.wav> [<b.wav> ...]
Whisper normally leaves fillers out of its transcript; prompted with disfluent text it writes them. Also reports voiced
sound that no transcribed word covers (a hum between words) and words much longer than their letters allow."""
import re, sys
import numpy as np, torch, librosa
from transformers import pipeline
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cuda", dtype=torch.float16,
               model_kwargs={"attn_implementation": "eager"})
PROMPT = "Umm, so, uh, I mean, hmm, eh, like, you know, ah, the the, erm, okay."
pids = asr.tokenizer.get_prompt_ids(PROMPT, return_tensors="pt").to("cuda")
FILL = re.compile(r"^(u+h+m*|u+m+|e+h+|e+r+m*|a+h+|h+m+|m+h*m+|e+m+|a+m{2,}|o+h+|mm+)$")


def scan(w16):
    r = asr(w16.copy(), return_timestamps="word", generate_kwargs={"language": "en", "task": "transcribe", "prompt_ids": pids})
    ch = [c for c in r["chunks"] if c["text"].strip()]
    # the prompt can leak into the first chunk(s); drop words that start before 0
    words = [(re.sub(r"[^\w']", "", c["text"].lower()), c["timestamp"][0] or 0.0, c["timestamp"][1] or len(w16) / 16000) for c in ch]
    fill = [(w, t0) for w, t0, _ in words if FILL.match(w)]
    toks = [w for w, _, _ in words if w and not FILL.match(w)]
    reps = [(toks[i], i) for i in range(1, len(toks)) if toks[i] == toks[i - 1] and toks[i] not in ("that", "really", "many", "very")]
    return r["text"].strip(), fill, reps, words


if __name__ == "__main__":
    for f in sys.argv[1:]:
        w, sr = librosa.load(f, sr=16000)
        for s in range(0, len(w), 25 * 16000):       # 25 s windows, no chunk stitching
            seg = w[max(0, s - 16000):s + 25 * 16000]
            text, fill, reps, _ = scan(seg)
            if fill or reps:
                off = max(0, s - 16000) / 16000
                print(f"{f.split('/')[-1]} @{s/16000:.0f}s fillers={[(x, round(t + off, 1)) for x, t in fill]} reps={[x for x, _ in reps]}")
                print("   ", text[:400])
