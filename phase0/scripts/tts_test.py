import time, sys, torch, soundfile as sf
print("torch", torch.__version__, "cuda", torch.cuda.is_available(), flush=True)
from chatterbox.mtl_tts import ChatterboxMultilingualTTS, SUPPORTED_LANGUAGES
print("supported:", {k: SUPPORTED_LANGUAGES[k] for k in ("en", "fi", "sv") if k in SUPPORTED_LANGUAGES}, flush=True)
t = time.time()
model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
print("model loaded in %.1fs, sr=%d" % (time.time() - t, model.sr), flush=True)
ref = "/in/voice_24k.wav"
texts = {
 "en": "Hello, this is a test of my cloned voice. Today we will talk about how manufacturing companies move from selling products to selling services.",
 "fi": "Hei, tämä on testi kloonatusta äänestäni. Tänään puhumme siitä, miten teollisuusyritykset siirtyvät tuotteiden myynnistä palveluiden myyntiin.",
 "sv": "Hej, det här är ett test av min klonade röst. Idag pratar vi om hur tillverkande företag går från att sälja produkter till att sälja tjänster.",
}
for lang, text in texts.items():
    t = time.time()
    try:
        wav = model.generate(text, language_id=lang, audio_prompt_path=ref)
        dt = time.time() - t
        a = wav.squeeze().cpu().numpy()
        sf.write(f"/out/tts_{lang}.wav", a, model.sr)
        print(f"{lang}: {len(a)/model.sr:.1f}s audio in {dt:.1f}s (RTF {dt/(len(a)/model.sr):.2f})", flush=True)
    except Exception as e:
        print(f"{lang}: FAILED {type(e).__name__}: {e}", flush=True)
