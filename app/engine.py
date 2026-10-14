"""Speech engine shared by the app and the background job.
One Chatterbox multilingual model stays loaded; a voice = reference clip + optional LoRA delta (scaled) + settings.
LoRA deltas are cached per adapter, so switching voices only adds/subtracts weights (no reload)."""
import os, re, subprocess, tempfile
import numpy as np, soundfile as sf, torch, librosa

TONES = {  # optional tone presets -> parameter nudges (Chatterbox: exaggeration, temperature, cfg_weight)
    "Neutral": {},
    "Calm": {"exaggeration": 0.35, "temperature": 0.7},
    "Friendly": {"exaggeration": 0.6},
    "Enthusiastic": {"exaggeration": 0.85, "temperature": 0.85},
    "Serious": {"exaggeration": 0.4, "temperature": 0.65},
    "Storytelling": {"exaggeration": 0.7, "temperature": 0.9},
}
PACE = {"Slower": 0.9, "Normal": 1.0, "Faster": 1.1}
FORMATS = {"WAV": "wav", "MP3": "mp3", "M4A": "m4a", "OGG": "ogg", "FLAC": "flac"}


class Engine:
    def __init__(self, device="cuda", with_asr=True):
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        self.tts = ChatterboxMultilingualTTS.from_pretrained(device=device)
        self.sr = self.tts.sr
        self.base = {k: v.detach().clone() for k, v in self.tts.t3.tfmr.state_dict().items()}
        self.deltas, self.active = {}, (None, 0.0)
        self.asr = None
        if with_asr:
            from transformers import pipeline
            self.asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device=device, torch_dtype=torch.float16)
        self._ref = None

    # ---- voice weights ----
    def _delta(self, lora_dir):
        if lora_dir not in self.deltas:
            from peft import PeftModel
            self.tts.t3.tfmr.load_state_dict(self.base)
            merged = PeftModel.from_pretrained(self.tts.t3.tfmr, lora_dir).merge_and_unload()
            self.tts.t3.tfmr = merged
            st = merged.state_dict()
            self.deltas[lora_dir] = {k: (st[k] - self.base[k]) for k in self.base if not torch.equal(st[k], self.base[k])}
            self.tts.t3.tfmr.load_state_dict(self.base); self.active = (None, 0.0)
        return self.deltas[lora_dir]

    def use(self, lora_dir=None, scale=1.0):
        if self.active == (lora_dir, scale): return
        sd = {k: v.clone() for k, v in self.base.items()}
        if lora_dir:
            for k, d in self._delta(lora_dir).items(): sd[k] = self.base[k] + scale * d
        self.tts.t3.tfmr.load_state_dict(sd); self.active = (lora_dir, scale)

    def set_ref(self, ref, exaggeration):
        if self._ref != (ref, exaggeration):
            self.tts.prepare_conditionals(ref, exaggeration=exaggeration); self._ref = (ref, exaggeration)

    # ---- QC ----
    @staticmethod
    def _norm(s):
        return re.sub(r"[^a-z0-9äöåáéíóúñü ]", "", s.lower()).split()

    def _wer(self, r, h):
        r, h = self._norm(r), self._norm(h); d = np.arange(len(h) + 1)
        for i in range(1, len(r) + 1):
            prev, d[0] = d.copy(), i
            for j in range(1, len(h) + 1): d[j] = min(prev[j] + 1, d[j - 1] + 1, prev[j - 1] + (r[i - 1] != h[j - 1]))
        return d[len(h)] / max(len(r), 1)

    def _qc(self, w, text, lang):
        if self.asr is None: return 0.0, ""
        w16 = librosa.resample(w, orig_sr=self.sr, target_sr=16000)
        r = self.asr(w16, return_timestamps="word", generate_kwargs={"language": lang, "task": "transcribe"})
        rms = librosa.feature.rms(y=w16, frame_length=640, hop_length=320)[0]; ref = np.percentile(rms, 95) + 1e-9
        t = np.arange(len(rms)) * 0.02; inw = (t < 0.12) | (t > t[-1] - 0.12)
        for c in r["chunks"]:
            a, b = c["timestamp"]; inw |= (t >= (a or 0) - 0.05) & (t <= (b or t[-1]) + 0.05)
        stray = float(((rms > 0.15 * ref) & ~inw).sum() * 0.02)
        return 3 * self._wer(text, r["text"]) + 2 * stray, r["text"].strip()

    # ---- synthesis ----
    def speak(self, text, lang, ref, lora_dir=None, lora_scale=1.0, exaggeration=0.5, cfg_weight=0.0, temperature=0.8,
              speed=1.0, takes=3, seed=0, progress=None):
        self.use(lora_dir, lora_scale); self.set_ref(ref, exaggeration)
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text.strip()) if s.strip()]
        parts, report = [], []
        for si, s in enumerate(sents):
            best = None
            for k in range(takes):
                torch.manual_seed(seed + 101 * si + k)
                w = self.tts.generate(s, language_id=lang, exaggeration=exaggeration, cfg_weight=cfg_weight, temperature=temperature).squeeze().cpu().numpy()
                sc, heard = self._qc(w, s, lang)
                if best is None or sc < best[0]: best = (sc, w, heard)
                if sc == 0: break
            parts += [best[1], np.zeros(int(0.32 * self.sr), dtype=np.float32)]
            report.append({"sentence": s, "score": round(best[0], 3), "heard": best[2]})
            if progress: progress((si + 1) / len(sents), s)
        a = np.concatenate(parts) if parts else np.zeros(1, dtype=np.float32)
        a = a / (np.abs(a).max() + 1e-9) * 0.89
        if abs(speed - 1.0) > 1e-3: a = time_stretch(a, self.sr, speed)
        return a, report


def time_stretch(a, sr, speed):
    with tempfile.TemporaryDirectory() as d:
        i, o = os.path.join(d, "i.wav"), os.path.join(d, "o.wav")
        sf.write(i, a, sr)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", i, "-filter:a", f"atempo={speed}", o], check=True)
        return sf.read(o)[0].astype(np.float32)


def export(a, sr, out_base, formats):
    """Write the audio in each requested format; returns {fmt: path}."""
    wav = out_base + ".wav"; sf.write(wav, a, sr); paths = {}
    for f in formats:
        ext = FORMATS[f]
        if ext == "wav": paths[f] = wav; continue
        p = f"{out_base}.{ext}"
        codec = {"mp3": ["-c:a", "libmp3lame", "-b:a", "192k"], "m4a": ["-c:a", "aac", "-b:a", "160k"],
                 "ogg": ["-c:a", "libvorbis", "-q:a", "6"], "flac": ["-c:a", "flac"]}[ext]
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, *codec, p], check=True); paths[f] = p
    if "WAV" not in formats: paths.setdefault("_wav", wav)
    return paths
