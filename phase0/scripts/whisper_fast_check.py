"""A/B check for whisper_fast.py: same clips, word timestamps with and without the patch, outputs must be identical.
usage (in avatar-hub-app:p0): python whisper_fast_check.py <wav> [<wav> ...]"""
import sys, time
import torch, librosa
from transformers import pipeline
import whisper_fast
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cuda", dtype=torch.float16,
               model_kwargs={"attn_implementation": "eager"})
pids = asr.tokenizer.get_prompt_ids("Umm, so, uh, I mean, hmm, eh, like, you know, ah, the the, erm, okay.", return_tensors="pt").to("cuda")
clips = []
for f in sys.argv[1:]:
    w = librosa.load(f, sr=16000)[0]
    clips += [w[:16000 * 6], w[16000 * 6:16000 * 15]]
kw = [dict(return_timestamps="word", generate_kwargs={"language": "en", "task": "transcribe"}),
      dict(return_timestamps="word", generate_kwargs={"language": "en", "task": "transcribe", "prompt_ids": pids})]
asr(clips[0], **kw[0])   # warm-up
def run():
    torch.cuda.synchronize(); t = time.time(); out = [asr(c.copy(), **k) for c in clips for k in kw]; torch.cuda.synchronize()
    return out, time.time() - t
a, ta = run()
whisper_fast.install()
b, tb = run()
same = all(x["text"] == y["text"] and [c["timestamp"] for c in x["chunks"]] == [c["timestamp"] for c in y["chunks"]]
           and [c["text"] for c in x["chunks"]] == [c["text"] for c in y["chunks"]] for x, y in zip(a, b))
print(f"FASTCHECK {len(a)} calls: original {ta:.1f}s, patched {tb:.1f}s, identical outputs: {same}")
for x, y in zip(a, b):
    if x != y: print("FASTCHECK DIFF", x["text"][:80], "|", y["text"][:80])
