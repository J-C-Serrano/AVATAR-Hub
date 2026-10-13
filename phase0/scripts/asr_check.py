import re, sys, torch, soundfile as sf, librosa
from transformers import pipeline
texts = {
 "en": "Hello, this is a test of my cloned voice. Today we will talk about how manufacturing companies move from selling products to selling services.",
 "fi": "Hei, tämä on testi kloonatusta äänestäni. Tänään puhumme siitä, miten teollisuusyritykset siirtyvät tuotteiden myynnistä palveluiden myyntiin.",
 "sv": "Hej, det här är ett test av min klonade röst. Idag pratar vi om hur tillverkande företag går från att sälja produkter till att sälja tjänster.",
}
def norm(s): return re.sub(r"[^\w\s]", "", s.lower()).split()
def wer(ref, hyp):
    r, h = norm(ref), norm(hyp)
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        p, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (r[i - 1] != h[j - 1]))
    return d[len(h)] / max(len(r), 1)
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cuda", torch_dtype=torch.float16)
for lang, ref in texts.items():
    a, sr = librosa.load(f"/out/tts_{lang}.wav", sr=16000)
    hyp = asr(a, generate_kwargs={"language": {"en":"english","fi":"finnish","sv":"swedish"}[lang], "task": "transcribe"})["text"].strip()
    print(f"[{lang}] WER={wer(ref, hyp):.2f}\n  ref: {ref}\n  hyp: {hyp}", flush=True)
