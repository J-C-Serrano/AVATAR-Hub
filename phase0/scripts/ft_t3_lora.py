"""LoRA fine-tuning of Chatterbox *multilingual* T3 on one speaker (accent, rhythm, habits live in T3).
Differences from community toolkits: conditioning prompt + speaker embedding come from a DIFFERENT clip of the same
speaker (as at inference), the whole target clip is supervised, proper next-token shift, held-out validation.
usage: python ft_t3_lora.py --data /v/dataset --out /out/ft_run [--epochs 15] [--r 16] [--alpha 32] [--lr 2e-4] [--bs 8]
data: metadata.csv (name|text|text) + wavs/ (24 kHz); language from clip name ("finnish" -> fi, "swedish" -> sv, else en)."""
import argparse, json, math, os, random, time
import numpy as np, torch, torch.nn.functional as F, librosa
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
from chatterbox.models.t3.modules.cond_enc import T3Cond
from chatterbox.models.s3tokenizer import S3_SR
from peft import LoraConfig, get_peft_model

ap = argparse.ArgumentParser()
ap.add_argument("--data"); ap.add_argument("--out")
ap.add_argument("--epochs", type=int, default=15); ap.add_argument("--r", type=int, default=16); ap.add_argument("--alpha", type=int, default=32)
ap.add_argument("--lr", type=float, default=2e-4); ap.add_argument("--bs", type=int, default=8); ap.add_argument("--val_frac", type=float, default=0.1)
ap.add_argument("--save_epochs", default=""); ap.add_argument("--dropout", type=float, default=0.05); ap.add_argument("--seed", type=int, default=0)
A = ap.parse_args(); os.makedirs(A.out, exist_ok=True)
random.seed(A.seed); torch.manual_seed(A.seed)
dev = "cuda"
tts = ChatterboxMultilingualTTS.from_pretrained(device=dev)
t3, hp = tts.t3, tts.t3.hp
lang_of = lambda n: "fi" if "finnish" in n else ("sv" if "swedish" in n else "en")

# ---------- 1. cache tokens / embeddings ----------
cache_p = os.path.join(A.out, "cache.pt")
if os.path.exists(cache_p):
    items = torch.load(cache_p)
else:
    rows = [l.split("|") for l in open(os.path.join(A.data, "metadata.csv")).read().strip().split("\n")]
    items = []
    for i, (name, text, _) in enumerate(rows):
        wav, _ = librosa.load(os.path.join(A.data, "wavs", name + ".wav"), sr=S3_SR)
        with torch.no_grad():
            st, _ = tts.s3gen.tokenizer.forward([wav])
            emb = torch.from_numpy(tts.ve.embeds_from_wavs([wav], sample_rate=S3_SR))[0]
        tt = tts.tokenizer.text_to_tokens(text, language_id=lang_of(name))[0]
        items.append({"name": name, "lang": lang_of(name), "text": text, "speech": st[0].cpu().long(), "text_tok": tt.long(), "emb": emb.float()})
        if i % 50 == 0: print(f"cache {i}/{len(rows)} [", flush=True)
    torch.save(items, cache_p)
# stratified held-out split (every section represented)
by_sec = {}
for it in items: by_sec.setdefault(it["name"].rsplit("_", 1)[0], []).append(it)
val, train = [], []
for sec, lst in sorted(by_sec.items()):
    lst = sorted(lst, key=lambda x: x["name"]); k = max(1, round(len(lst) * A.val_frac)) if len(lst) >= 5 else 0
    idx = set(random.sample(range(len(lst)), k)); val += [x for j, x in enumerate(lst) if j in idx]; train += [x for j, x in enumerate(lst) if j not in idx]
json.dump({"train": [x["name"] for x in train], "val": [x["name"] for x in val]}, open(os.path.join(A.out, "split.json"), "w"), indent=0)
print(f"train={len(train)} val={len(val)} speech_min={sum(len(x['speech']) for x in train) / 25 / 60:.1f}", flush=True)
PLEN = hp.speech_cond_prompt_len  # 150 tokens = 6 s

def batchify(lst, train_mode):
    sot, eot, bos, eos = hp.start_text_token, hp.stop_text_token, hp.start_speech_token, hp.stop_speech_token
    T, S, P, E = [], [], [], []
    for it in lst:
        other = random.choice([x for x in train if x["name"] != it["name"]]) if train_mode else train[hash(it["name"]) % len(train)]
        T.append(torch.cat([torch.tensor([sot]), it["text_tok"], torch.tensor([eot])]))
        S.append(torch.cat([torch.tensor([bos]), it["speech"][:800], torch.tensor([eos])]))
        p = other["speech"][:PLEN]; P.append(p); E.append(other["emb"])
    tl = torch.tensor([len(x) for x in T]); sl = torch.tensor([len(x) for x in S]); pl = max(len(x) for x in P)
    pad = lambda xs, v: torch.nn.utils.rnn.pad_sequence(xs, batch_first=True, padding_value=v)
    Pm = torch.stack([F.pad(x, (0, pl - len(x)), value=x[-1].item()) for x in P])   # repeat last token (no pad id)
    emb = torch.stack(E)
    if train_mode:  # 10% unconditional (keeps CFG/zero-speaker behaviour intact)
        drop = torch.rand(len(lst)) < 0.10; emb[drop] = 0
    cond = T3Cond(speaker_emb=emb.to(dev), cond_prompt_speech_tokens=Pm.to(dev), emotion_adv=0.5 * torch.ones(len(lst), 1, 1, device=dev))
    return cond, pad(T, eot).to(dev), tl.to(dev), pad(S, eos).to(dev), sl.to(dev)

def step_loss(model, lst, train_mode):
    cond, tt, tl, st, sl = batchify(lst, train_mode)
    with torch.autocast("cuda", dtype=torch.bfloat16):
        out = model(t3_cond=cond, text_tokens=tt, text_token_lens=tl, speech_tokens=st, speech_token_lens=sl, training=True)
    IG = -100
    lab = st[:, 1:].masked_fill(torch.arange(st.size(1) - 1, device=dev)[None] >= (sl[:, None] - 1), IG)
    ls = F.cross_entropy(out.speech_logits[:, :-1].float().transpose(1, 2), lab, ignore_index=IG)
    labt = tt[:, 1:].masked_fill(torch.arange(tt.size(1) - 1, device=dev)[None] >= (tl[:, None] - 1), IG)
    lt = F.cross_entropy(out.text_logits[:, :-1].float().transpose(1, 2), labt, ignore_index=IG)
    return ls, lt

# ---------- 2. LoRA on the Llama backbone ----------
t3.train()
for p_ in t3.parameters(): p_.requires_grad = False
lcfg = LoraConfig(r=A.r, lora_alpha=A.alpha, lora_dropout=A.dropout, bias="none",
                  target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
t3.tfmr = get_peft_model(t3.tfmr, lcfg); t3.tfmr.print_trainable_parameters()
params = [p_ for p_ in t3.parameters() if p_.requires_grad]
opt = torch.optim.AdamW(params, lr=A.lr, weight_decay=0.01)
steps_per_ep = math.ceil(len(train) / A.bs); total = steps_per_ep * A.epochs; warm = max(10, total // 20)
sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1, (s + 1) / warm) * 0.5 * (1 + math.cos(math.pi * min(1, s / total))))

def evaluate():
    t3.eval(); L = []
    with torch.no_grad():
        for i in range(0, len(val), A.bs):
            ls, _ = step_loss(t3, val[i:i + A.bs], False); L.append(ls.item())
    t3.train(); return float(np.mean(L))

v0 = evaluate(); print(f"epoch 0/{A.epochs} [ val_speech_loss={v0:.4f} (base model)", flush=True)
log = [{"epoch": 0, "val": v0}]; best = v0; save_eps = {int(x) for x in A.save_epochs.split(",") if x}; step = 0; t0 = time.time()
for ep in range(1, A.epochs + 1):
    random.shuffle(train); tr = []
    for i in range(0, len(train), A.bs):
        ls, lt = step_loss(t3, train[i:i + A.bs], True)
        loss = ls + 0.1 * lt
        opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(params, 1.0); opt.step(); sched.step(); step += 1
        tr.append(ls.item())
    v = evaluate(); log.append({"epoch": ep, "train": float(np.mean(tr)), "val": v, "min": (time.time() - t0) / 60})
    print(f"epoch {ep}/{A.epochs} [ train_speech_loss={np.mean(tr):.4f} val_speech_loss={v:.4f} t={(time.time() - t0) / 60:.1f} min", flush=True)
    if ep in save_eps:
        t3.tfmr.save_pretrained(os.path.join(A.out, f"lora_ep{ep}"))
    if v < best:
        best = v; t3.tfmr.save_pretrained(os.path.join(A.out, "lora_best")); json.dump({"epoch": ep, "val": v}, open(os.path.join(A.out, "best.json"), "w"))
json.dump(log, open(os.path.join(A.out, "log.json"), "w"), indent=1)
print("TRAIN_DONE", flush=True)
