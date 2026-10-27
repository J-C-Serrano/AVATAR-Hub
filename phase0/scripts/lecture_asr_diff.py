"""Whole-lecture check: Whisper transcript of the finished video vs the spoken script.
usage (in avatar-hub-app:p0): python lecture_asr_diff.py <lecture.mp4> <spoken.txt> [lexicon.json]
Prints every word-level difference (missing / extra / changed words) with its time in the video. Spelling-only
differences are folded with say_clean.py's ALIASES; numbers are ignored."""
import difflib, json, re, subprocess, sys, tempfile, torch, librosa
from transformers import pipeline
src = open("/hub/phase0/scripts/say_clean.py").read()
exec(src[src.index("ALIASES = ["):src.index("load_lexicon(a.lexicon)")])   # ALIASES, NUM, load_lexicon
LEXICON = []; load_lexicon(sys.argv[3] if len(sys.argv) > 3 else None)
LEX = re.compile(r"\[(\+|silence [\d.]+)\]")


def toks(t):
    t = t.lower().replace("-", " ").replace("’", "'")
    for p, r in ALIASES: t = re.sub(p, r, t)
    return [w for w in re.sub(r"[^a-z0-9' ]", " ", t).split() if not NUM.match(w)]


wav = tempfile.mktemp(suffix=".wav"); subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", sys.argv[1], "-ac", "1", "-ar", "16000", wav], check=True)
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cuda", dtype=torch.float16,
               model_kwargs={"attn_implementation": "eager"})
w, _ = librosa.load(wav, sr=16000)
r = asr(w, return_timestamps="word", chunk_length_s=30, batch_size=4, generate_kwargs={"language": "en", "task": "transcribe"})
hyp, ht = [], []
for c in r["chunks"]:
    for t in toks(c["text"]): hyp.append(t); ht.append(c["timestamp"][0] or 0.0)
ref = toks(LEX.sub(" ", re.sub(r"^###.*$", " ", open(sys.argv[2]).read(), flags=re.M)))
sm = difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False); n = 0
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op == "equal": continue
    t = ht[min(j1, len(ht) - 1)]; n += max(i2 - i1, j2 - j1)
    print(f"{int(t // 60):02d}:{t % 60:05.2f}  {op:8s} script: {' '.join(ref[max(0, i1 - 3):i2 + 2])!r:60}  heard: {' '.join(hyp[max(0, j1 - 3):j2 + 2])!r}")
print(f"WORDS {len(ref)}  DIFF {n}  ({100 * n / max(1, len(ref)):.1f}%)")
