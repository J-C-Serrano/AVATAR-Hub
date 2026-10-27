"""Speech for avatar videos with a strict, word-level QC (no stretched words, mid-sentence pauses, fillers).
usage (in avatar-hub-app:p0):
  python say_clean.py <voice_id> --text "<text>" --out <out.wav>
  python say_clean.py <voice_id> --script spoken.txt --outdir <dir> [--slides 2-12,15]   (blocks "### N"; resumable)
Per sentence: up to N takes, each scored with Whisper word timestamps:
  3*WER + 2*stray sound + 3*fillers (uh, um..., from a second Whisper pass with a disfluent prompt) + 3*repeated words + 3*stretch (longest word beyond 0.075 s/letter + 0.15 s;
  final word +0.25 s) + 2*gaps (> 0.25 s between words, > 0.8 s after punctuation). Best take kept; early stop when score <= --accept.
The text is written normally; LEXICON respells terms the voice mispronounces (tested with spell_test.py) and
ALIASES map Whisper's spellings back, so the check compares meaning, not spelling. Numbers are not checked.
Script mode writes slide_NN.wav + slide_NN.json (sentence start/end times in the wav, for slide animation)."""
import argparse, json, os, re, sys
sys.path.insert(0, "/hub/app")
import numpy as np, torch, librosa, soundfile as sf
from transformers import pipeline
from engine import Engine

ap = argparse.ArgumentParser()
ap.add_argument("vid"); ap.add_argument("--text"); ap.add_argument("--out")
ap.add_argument("--script"); ap.add_argument("--outdir"); ap.add_argument("--slides", default="")
ap.add_argument("--takes", type=int, default=8); ap.add_argument("--accept", type=float, default=0.2)
ap.add_argument("--temp", type=float, default=0.6); ap.add_argument("--exag", type=float, default=0.35)
ap.add_argument("--lang", default="en")
ap.add_argument("--lexicon", help="per-course JSON of extra respellings/aliases (names, course terms)")
ap.add_argument("--cfg", type=float, help="cfg_weight instead of the profile's (0.2-0.3 = fewer fillers in long sentences)")
ap.add_argument("--keep", action="store_true", help="text mode: also save every take as <out>_tK.wav")
a = ap.parse_args()

# respellings for the TTS input (order matters); generic terms, from spell_test.py runs 2026-10-23.
# Names and course terms go in a per-course --lexicon file (git-ignored, phase0/in/<lec>/lexicon.json).
LEXICON = [(r"\bChatGPT", "Chat G-P-T"), (r"\bGPT-4\b", "gee-pee-tee four"), (r"\bGPT\b", "gee-pee-tee"),
           (r"\bGenAI\b", "Gen eh-eye"), (r"\bAGI\b", "eh-jee-eye"), (r"\bAI-driven\b", "eh-eye driven"),
           (r"\bAI\b", "eh-eye"), (r"\bML\b", "em-el"), (r"\bCLV\b", "see-el-vee"), (r"\bLLMs\b", "L-L-Ms"),
           (r"\bLLM\b", "L-L-M"), (r"\bHCI\b", "aitch-see-eye"), (r"\bDL\b", "dee-el"), (r"\bSOTA\b", "sow-ta"),
           (r"\bXGBoost\b", "X-G-Boost"), (r"\bscikit-learn\b", "sy-kit learn")]
# applied to both the expected text and Whisper's transcript before the WER
ALIASES = [(r"\b((?:[a-z]\.\s?){2,})", lambda m: m.group(1).replace(".", "").replace(" ", "") + " "),
           (r"\bchat\s*g\s*p\s*t\b", "chatgpt"), (r"\bg\s*p\s*t\b", "gpt"), (r"\bgen\s*ai\b", "genai"),
           (r"\bk\s+means\b", "kmeans"), (r"\bsci\s*kit\s*learn\b", "scikitlearn"), (r"\bxg\s*boost\b", "xgboost"),
           (r"\b(so\s*ta|soda|sota)\b", "sota"), (r"\bna[iï]ve\b", "naive"), (r"\be\s*commerce\b", "ecommerce"),
           (r"\bfine\s*tun", "finetun"), (r"\bco\s*pasting\b", "copypasting"), (r"\bok\b", "okay"),
           (r"\bpre\s*trained\b", "pretrained"), (r"\bscore\s+card", "scorecard"), (r"\bnineties\b", "90s")]


def load_lexicon(path):
    """Per-course additions: {"lexicon": [[regex, respelling], ...], "aliases": [[regex, canonical], ...]}; lexicon
    entries go first (a name can contain a generic term), aliases after the generic ones."""
    if not path: return
    d = json.load(open(path)); LEXICON[:0] = [tuple(x) for x in d.get("lexicon", [])]; ALIASES.extend(tuple(x) for x in d.get("aliases", []))


NUM = re.compile(r"^(\d.*|zero|one|two|three|four|five|six|seven|eight|nine|ten|twenty\w*|thirty\w*|hundred|thousand|point)$")
load_lexicon(a.lexicon)
FILLERS = {"uh", "um", "er", "erm", "ah", "eh", "hmm", "mm", "uhm"}
FILL = re.compile(r"^(u+h+m*|u+m+|e+h+|e+r+m*|a+h+|h+m+|m+h*m+|e+m+|a+m{2,}|o+h+|mm+)$")
# Whisper leaves fillers and repeats out of its transcript unless the prompt itself is disfluent
DISFL_PROMPT = "Umm, so, uh, I mean, hmm, eh, like, you know, ah, the the, erm, okay."

V = f"/hub/data/voices/{a.vid}"; s = json.load(open(f"{V}/profile.json"))["settings"]
eng = Engine(with_asr=False); eng.use(os.path.join(V, s["lora"]), s["lora_scale"]); eng.set_ref(os.path.join(V, s["ref"]), a.exag)
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cuda", dtype=torch.float16,
               model_kwargs={"attn_implementation": "eager"})  # eager: word timestamps several times faster here
PIDS = asr.tokenizer.get_prompt_ids(DISFL_PROMPT, return_tensors="pt").to("cuda")


def toks(t):
    t = t.lower().replace("-", " ").replace("’", "'")
    for p, r in ALIASES: t = re.sub(p, r, t)
    return [w for w in re.sub(r"[^a-z0-9' ]", " ", t).split() if not NUM.match(w)]


def wer(r, h):
    r, h = toks(r), toks(h); d = np.arange(len(h) + 1)
    for i in range(1, len(r) + 1):
        prev, d[0] = d.copy(), i
        for j in range(1, len(h) + 1): d[j] = min(prev[j] + 1, d[j - 1] + 1, prev[j - 1] + (r[i - 1] != h[j - 1]))
    return d[len(h)] / max(len(r), 1)


def score(w, text):
    w16 = librosa.resample(w, orig_sr=eng.sr, target_sr=16000); dur = len(w16) / 16000
    r = asr(w16, return_timestamps="word", generate_kwargs={"language": a.lang, "task": "transcribe"})
    ch, heard = r["chunks"], r["text"].strip()
    rms = librosa.feature.rms(y=w16, frame_length=640, hop_length=320)[0]; ref = np.percentile(rms, 95) + 1e-9
    t = np.arange(len(rms)) * 0.02; inw = (t < 0.12) | (t > t[-1] - 0.12)
    onset = float(t[np.argmax(rms > 0.1 * ref)])  # Whisper starts the first word at 0 even after leading silence
    stretch, gaps, worst = 0.0, 0.0, ""
    for i, c in enumerate(ch):
        t0, t1 = c["timestamp"]; t0 = t0 or 0.0; t1 = t1 if t1 is not None else dur
        if i == 0: t0 = max(t0, onset - 0.05)
        inw |= (t >= t0 - 0.05) & (t <= t1 + 0.05)
        wd = re.sub(r"[^\w]", "", c["text"])
        allow = (0.2 if wd.isupper() and len(wd) > 1 else 0.075) * len(wd) + 0.15   # spelled acronyms take longer
        if re.search(r"[,;:]$", c["text"].strip()): allow += 0.25                      # natural lengthening before a comma
        ex = max(0.0, (t1 - t0) - allow)
        if i == len(ch) - 1: ex = max(0.0, ex - 0.25)  # sentence-final words may trail
        if ex > stretch: worst = f"{c['text'].strip()} {t1 - t0:.2f}s"
        stretch = max(stretch, ex)
        if i:   # a pause after punctuation is wanted; elsewhere it is a hesitation
            ok = 0.8 if re.search(r"[,;:.?!]$", ch[i - 1]["text"].strip()) else 0.25
            gaps += max(0.0, t0 - (ch[i - 1]["timestamp"][1] or t0) - ok)
    stray = float(((rms > 0.15 * ref) & ~inw).sum() * 0.02)
    verb = asr(w16, generate_kwargs={"language": a.lang, "task": "transcribe", "prompt_ids": PIDS})["text"]
    verb = re.sub(r"^.*?" + re.escape(DISFL_PROMPT[-12:]), "", verb).strip()  # prompt echo, if any
    vw = [re.sub(r"[^\w']", "", x.lower()) for x in verb.split()]
    fillers = sum(bool(FILL.match(x)) or x in FILLERS for x in vw if x)
    if fillers: worst = f"{fillers} filler(s)"
    e = wer(text, heard)
    hw, tw = toks(verb) or toks(heard), toks(text)   # a doubled word ("with a a") is a stutter; one in 25 words barely moves the WER
    reps = max(0, sum(hw[k] == hw[k - 1] for k in range(1, len(hw))) - sum(tw[k] == tw[k - 1] for k in range(1, len(tw))))
    if reps: worst = f"{reps} repeat(s)"
    sc = 3 * e + 2 * stray + 3 * stretch + 2 * gaps + 3 * fillers + 3 * reps
    return sc, dict(heard=heard, verbatim=verb, wer=round(e, 3), stray=round(stray, 2), stretch=round(stretch, 2), gaps=round(gaps, 2), worst=worst)


def say(text):
    for p, r in LEXICON: text = re.sub(p, r, text)
    return text


def split_long(t, maxw=48):
    """Very long sentences make the TTS drift; split at ; or , nearest the middle (keeps the words)."""
    if len(t.split()) <= maxw: return [t]
    cuts = [m.end() for m in re.finditer(r"[;,:]\s", t)]
    if not cuts: return [t]
    c = min(cuts, key=lambda x: abs(x - len(t) / 2))
    return split_long(t[:c].strip(), maxw) + split_long(t[c:].strip(), maxw)


def trim(w, keep=0.04):
    """Cut the take's own leading/trailing silence so the pauses between sentences are exactly the ones set below."""
    e = np.convolve(np.abs(w), np.ones(480) / 480, "same"); on = np.flatnonzero(e > 0.02 * e.max())
    if not len(on): return w
    k = int(keep * eng.sr); return w[max(0, on[0] - k):on[-1] + k]


def render(paragraphs, tag, seed0):
    parts, rows, pos = [], [], 0
    for pi, para in enumerate(paragraphs):
        sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", para.strip()) if x.strip()]
        for si, sent in enumerate(sents):
            cue = sent.startswith("[+]"); sent = sent[3:].strip() if cue else sent
            for ci, piece in enumerate(split_long(sent)):
                best = None
                for k in range(a.takes):
                    torch.manual_seed(seed0 + 1009 * pi + 101 * si + 13 * ci + k); eng._clear_hooks()
                    w = eng.tts.generate(say(piece), language_id=a.lang, exaggeration=a.exag, cfg_weight=s["cfg_weight"] if a.cfg is None else a.cfg,
                                         temperature=a.temp).squeeze().cpu().numpy()
                    sc, q = score(w, piece)
                    if a.keep and a.text: sf.write(f"{os.path.splitext(a.out)[0]}_t{k + 1}.wav", w, eng.sr)
                    print(f"{tag} p{pi + 1}s{si + 1}{'abcdef'[ci]} take {k + 1}: {sc:.2f} {q}", flush=True)
                    if best is None or sc < best[0]: best = (sc, w, q)
                    if sc <= a.accept: break
                best = (best[0], trim(best[1]), best[2])
                rows.append(dict(text=piece, t0=round(pos / eng.sr, 3), t1=round((pos + len(best[1])) / eng.sr, 3),
                                 score=round(best[0], 2), takes=k + 1, para=pi, cue=cue and ci == 0, **best[2]))
                # pauses: comma split 0.25 s, full stop 0.45 s, question 0.55 s, paragraph (new click) 0.8 s
                gap = 0.25 if ci < len(split_long(sent)) - 1 else (0.8 if si == len(sents) - 1 else 0.55 if sent.endswith("?") else 0.45)
                parts += [best[1], np.zeros(int(gap * eng.sr), dtype=np.float32)]; pos += len(best[1]) + int(gap * eng.sr)
    out = np.concatenate(parts[:-1]) if parts else np.zeros(1, np.float32)
    return out / (np.abs(out).max() + 1e-9) * 0.89, rows


if a.text:
    out, rows = render([a.text], "txt", 1000)
    sf.write(a.out, out, eng.sr); print(json.dumps(rows, indent=1)); print("DUR", round(len(out) / eng.sr, 2))
else:
    blocks = {int(m.group(1)): m.group(2).strip() for m in re.finditer(r"^### (\d+)\n(.*?)(?=^### |\Z)", open(a.script).read(), re.S | re.M)}
    want = set()
    for r in filter(None, a.slides.split(",")):
        lo, _, hi = r.partition("-"); want |= set(range(int(lo), int(hi or lo) + 1))
    os.makedirs(a.outdir, exist_ok=True)
    for n in sorted(blocks):
        if want and n not in want: continue
        base = os.path.join(a.outdir, f"slide_{n:02d}")
        if os.path.exists(base + ".json"): print(f"slide {n}: done, skipping", flush=True); continue
        m = re.fullmatch(r"\[silence ([\d.]+)\]", blocks[n])
        if m:   # slide without speech (e.g. a section title card)
            sf.write(base + ".wav", np.zeros(int(float(m.group(1)) * eng.sr), np.float32), eng.sr)
            json.dump({"slide": n, "dur": float(m.group(1)), "sentences": []}, open(base + ".json", "w")); continue
        out, rows = render([p for p in blocks[n].split("\n") if p.strip()], f"slide {n}", 1000 + 100003 * n)
        sf.write(base + ".wav", out, eng.sr)
        json.dump({"slide": n, "dur": round(len(out) / eng.sr, 3), "sentences": rows}, open(base + ".json", "w"), indent=1, ensure_ascii=False)
        bad = [r for r in rows if r["score"] > 1.0]
        print(f"SLIDE_DONE {n} dur {len(out) / eng.sr:.1f}s sentences {len(rows)} worst {max(r['score'] for r in rows):.2f} flagged {len(bad)}", flush=True)
