# AVATAR Hub — Handover File

> **Purpose:** single source of truth for project history and context, so any CLI / AI model
> can pick up where the last one left off. **Read this first. Update it at the end of every
> working session** (revise Status / Decisions / Next steps, append to the Changelog).

Last updated: 2026-10-13 · Owner: Julio Serrano

> **Repo:** `git@github.com:J-C-Serrano/AVATAR-Hub.git` (**public**, own repo, branch `main`).
> **Rule: at the end of every session, update this file, then `git add -A && git commit && git push`.**
> The repo is public: never commit secrets, photos/voice samples, consent videos, generated videos or model weights (see `.gitignore`).

---

## 1. Project summary

Building software that creates a **talking-head video avatar** from ~10 studio photos of a
person, clones their voice from a ~30-minute audio/video recording, and renders **lip-synced
video offline/batch** (not real-time).

**Why:** internal tool, similar in spirit to HeyGen / Synthesia / D-ID but self-hosted and
open-source, run on hardware already owned rather than a SaaS API.

## 2. Hardware / environment

| Item | Detail |
|---|---|
| Machine | Dell workstation with NVIDIA GB10 "Spark" (DGX Spark) |
| Memory | 128 GB unified LPDDR5x shared CPU/GPU, only ~273 GB/s bandwidth (vs. 1 TB/s+ on discrete GPUs) |
| CPU / GPU arch | ARM64 CPU, Blackwell GPU, compute capability **sm_121** |
| OS | Linux 6.17.0-1008-nvidia |
| Project dir | `/home/julios/AI_Projects/AVATAR Hub` |
| Extra inference | Ollama cloud endpoint available if local isn't enough |

**Key constraint (research, Oct 2026):**
- GB10/sm_121 software support is still immature.
- flash-attention has no official sm_121 build → needs source-build workarounds inside
  NVIDIA's NGC PyTorch container (**25.10-py3 or later**).
- Plain pip PyTorch does **not** support sm_121 at all.
- Plenty of *capacity* (128 GB fits large models) but *bandwidth-bound* → good for
  batch/offline work, not real-time/low-latency generation.

## 3. Decisions made

| Date | Decision | Why |
|---|---|---|
| 2026-10-13 | 2D talking-head video, offline/batch | Scope; hardware is bandwidth-bound |
| 2026-10-13 | Context: **university**, Finland/EU; outputs internal and external; uses: lecture videos, announcements, paid online courses | Julio |
| 2026-10-13 | Production stack: permissive licenses only | Julio |
| 2026-10-13 | Consent = spoken phrase, recorded by **camera or uploaded file**; **remote enrollment allowed**; evidence stored in system | Julio (supersedes in-person-only) |
| 2026-10-13 | Enrollment accepts up to 30 min of audio from files (+ ~10 photos) | Julio |
| 2026-10-13 | **Anyone can render any avatar; consent on file unlocks it** | Julio |
| 2026-10-13 | Demo: **no login**, Streamlit UI; access campus + external | Julio |
| 2026-10-13 | Ollama cloud allowed; DPA assumed for all instances | Julio |
| 2026-10-13 | Disclosure: small "AI" corner mark + invisible C2PA/watermark (approved) | Julio |
| 2026-10-13 | This is a **demo / proof of concept**: enrollment-verification concerns deferred to production | Julio |
| 2026-10-13 | Deletion = plain "Delete avatar and data" button, no keys; **consent video is kept** after deletion; no retention limit | Julio (supersedes delete-key design) |
| 2026-10-13 | No script approval | Julio |
| 2026-10-13 | Languages: Finnish, English, Swedish; voice-quality problems fixed on the go | Julio |
| 2026-10-13 | **Voice must keep the speaker's own accent** (English must sound like Julio's accented English, not native/"perfect" English) | Julio |
| 2026-10-13 | **Visual realism:** no unnaturally white teeth; head movement must be more than a few cm (natural nods/tilts/turns) | Julio |
| 2026-10-13 | Demo target: ~30 s video | Julio |
| 2026-10-13 | Repo is public on GitHub, own repo, **Apache-2.0** license | Julio |

Architecture: `ARCHITECTURE.md` v0.3 (demo-first). Approved to start Phase 0.

## 4. Open questions

- [ ] Final consent texts fi/en/sv — university legal to review (must cover "anyone may render my likeness").
- [ ] Minimum audio duration for fine-tune vs zero-shot (Phase 0).
- [ ] Production phase (later): enrollment verification, access control, delete authorisation, counsel/DPO review.

## 5. Proposed pipeline

```
10 studio photos ──► best-frame selection/alignment ──► source portrait
30-min video/audio ──► extract + clean audio ──► voice-clone model (fine-tuned)
script/text ──► cloned-voice TTS ──► speech .wav
source portrait + speech .wav ──► talking-head animation model ──► lip-synced video
```

The 10 photos don't need full 3D reconstruction for a 2D talking head — they are used to
pick/curate the cleanest frontal reference, and optionally to build a multi-image identity
anchor (PhotoMaker / InstantID / ConsistentID) if generating stylized avatar variants later.

## 6. Model shortlist (researched 2026-10-13)

### Talking-head animation (photo + audio → lip-synced video)

| Model | License | VRAM | Notes |
|---|---|---|---|
| **EchoMimicV3 (Flash)** — recommended start | Apache-2.0 | ~12 GB | AntGroup, AAAI 2026, actively maintained, no face-mask needed, 768×768 |
| LivePortrait (+ audio-driven fork) | MIT, but InsightFace buffalo_l dep is non-commercial | 8–16 GB | Fast iteration/testing; license caveat if commercial |
| Ditto | Apache-2.0 | moderate | Motion-space diffusion, real-time capable |
| daVinci-MagiHuman (15B) | Apache-2.0 | ~80 GB class (H100 ref) | Highest fidelity; "quality ceiling" once env is proven |
| SadTalker | permissive | low | Simple smoke-test for the environment |

### Voice cloning (30-min recording → clonable voice)

| Model | License | VRAM | Notes |
|---|---|---|---|
| **Chatterbox (Resemble AI)** — recommended | MIT | ~6–7 GB | Clean commercial rights, fine-tunable |
| **CosyVoice2** — recommended alt | Apache-2.0 | moderate | Alibaba, strong multilingual, commercial-safe |
| XTTS-v2 (Coqui) | Coqui Public Model License — non-commercial | ~4–6 GB | Very good quality, blocked for commercial use |
| F5-TTS | code MIT, weights CC-BY-NC | ~4–8 GB | Same commercial caveat |
| Fish-Speech | commercial use needs paid license | — | Rule out unless licensed |

30 min of audio is far above the ~5–10 s these models need for zero-shot cloning; the real
value is **fine-tuning** (Chatterbox and CosyVoice2 both support it) for better fidelity.

## 7. Legal & compliance (summary — detail in ARCHITECTURE.md §8; needs counsel/DPO review)

Not legal advice. Finland/EU (GDPR, EU AI Act).

- **Licenses:** permissive only; audit weights + transitive deps; exclude InsightFace buffalo_l, XTTS-v2, F5-TTS weights, Fish-Speech.
- **Consent:** recorded phrase (camera/file), versioned text, hashed, append-only; consent video survives avatar deletion.
- **Remote enrollment has no identity verification in the demo** (deferred to production).
- **Disclosure:** corner "AI" mark + C2PA + invisible watermark.
- **Data:** on-prem, encrypted; Ollama cloud allowed for text (DPA assumed). `client_ref` (IP/session) is personal data.
- **Deletion:** plain delete-avatar button; consent video kept; no retention limit.

## 8. Architecture (summary — full: `ARCHITECTURE.md` v0.4)

Streamlit demo UI -> Python service layer (consent gate, jobs, delete, audit) -> Postgres (metadata + queue) ->
NGC-PyTorch worker containers (ingest/verify, voice, animate, post), one GPU job at a time -> encrypted storage.
Primary stack: Whisper + Chatterbox (voice) + EchoMimicV3 (animation). Phases 0-5.

## 9. Status

- [x] Research, scope, pipeline, shortlist
- [x] Legal posture and product decisions (see §3)
- [x] Architecture v0.3 (`ARCHITECTURE.md`) — approved to start Phase 0
- [x] Disk freed: 20 GB -> 236 GB free (74% used) after model cleanup
- [x] GPU in Docker verified: `docker run --device nvidia.com/gpu=all nvcr.io/nvidia/pytorch:25.10-py3` (CDI; torch 2.9.0a0 nv25.10, CUDA 13.0, GB10 cc 12.1, bf16 matmul OK, flash_attn 2.7.4 importable). NGC image pulled (~18 GB).
- [x] Host ffmpeg 6.1.1 installed
- [x] Phase 0: Chatterbox multilingual runs on GB10 (zero-shot clone from Julio's 48 s sample); fi/sv/en intelligible (Whisper WER 0.00 / 0.04 / 0.00); RTF ~0.55. **Julio must still listen** to `phase0/out/tts_{en,fi,sv}.wav` for voice likeness + Finnish/Swedish accent
- [x] Phase 0: voice likeness + fi/sv accent approved by Julio (2026-10-13)
- [x] Phase 0: animation smoke test: EchoMimicV3-Flash runs on GB10 (81 frames / 3.2 s clip in ~2.5 min incl. 8 steps; output 656x880 25fps with audio). **Julio must still watch** `phase0/out/anim_en/face_768_output.mp4` for lip-sync/quality
- [ ] Phase 0: license/SBOM audit (not started) (repo itself is Apache-2.0, see `LICENSE`)
- [ ] Phases 1-5 (see ARCHITECTURE.md §11)

## 10. Next steps

1. Julio watches `phase0/out/anim_en/face_768_output.mp4` (lip-sync, identity, artefacts).
2. Longer clip + fi/sv audio through animation; measure s-of-compute per s-of-video and peak memory; try 768x768 crop vs. full portrait.
3. License/SBOM audit (Phase 0 last item).
4. Julio answers the open questions in §4 (none block Phase 0).

## 11. Changelog

- **2026-10-13 (16)** — Julio rejected segmented EchoMimic output (seams, bad head movement). Built MuseTalk pipeline (§16) on his webcam base clip with a new Spanish-accented voice clone; result `out/mt_A_final.mp4`, continuous 37.4 s. Remaining backlog (C-J) not started.

- **2026-10-13 (15)** — 384 demo finished and QC'd (see §15 A). New voice sample extracted from Julio's webcam clip (`samples/.../2026-10-13-154745 new.webm`, 47.6 s, 2048x1536 15 fps, -15.7 LUFS) -> `phase0/in/voice_video_{24k,48k}.wav` (git-ignored); not yet cloned.

- **2026-10-13 (14)** — Landscape research (similar GitHub projects) and experiment backlog A-J added as §15. Julio: try everything; wait for the running 384 render to finish before starting new GPU experiments.

- **2026-10-13 (13)** — Added `README.md` (public project overview, reproduction steps, consent policy).

- **2026-10-13 (12)** — AVATAR Hub made its own git repo (was an untracked folder inside the 7 GB `AI_Projects` repo), public on GitHub as `J-C-Serrano/AVATAR-Hub`, branch `main`; Apache-2.0 `LICENSE` added; `.gitignore` excludes samples, inputs, outputs, weights (28 GB), and the upstream `echomimic_v3` clone. Policy: update HANDOVER + commit + push every session. Also: motion study at 384 (seed and audio-guidance are the levers; text prompt and text guidance barely matter), 384x384 head-crop render `scripts/run_demo384.sh` (re-anchored to original photo, best-of-2 seeds, xfade joins) in progress.

- **2026-10-13 (11)** — Julio's requirement changes (accent preserved, natural teeth, bigger head motion, 30 s demo; see §3). Accent: 3 Chatterbox variants of a 37 s script in `phase0/out/long_en_{a_cfg0,b_cfg0_ex7,c_default}.wav` (cfg_weight 0 lowers pull toward the model's native accent; default is cfg 0.5) - **Julio to pick**. Motion/teeth: via EchoMimic text prompt + negative prompt (see `animate_test.sh` env PROMPT/NEG); head tilt/shift visibly larger than the first run. 30 s demo: chained 81-frame segments (`scripts/animate_long.sh`, last frame seeds next segment) -> `phase0/out/demo32_final.mp4`.

- **2026-10-13 (10)** — Voice approved by Julio. Animation smoke test: cloned `antgroup/echomimic_v3` (commit 7e89489) into `phase0/echomimic_v3`, built `avatar-echomimic:p0` (`phase0/docker/echomimic/`), downloaded weights (23 GB in `phase0/weights/`: EchoMimicV3 flash-pro Apache-2.0, Wan2.1-Fun-1.3B-InP Apache-2.0, chinese-wav2vec2-base MIT). First run OK: tts_en.wav + face_768.png -> `phase0/out/anim_en/face_768_output.mp4`, 81 frames, ~18 s/step at 8 steps (~2.5 min), TeaCache on. Run via `phase0/scripts/animate_test.sh <audio> <out_dir> [frames]`.

- **2026-10-13 (9)** — Samples received (`samples/Julio Serrano/`: face.jpeg, Voice.m4a 48 s; Julio's own voice/face). Built `avatar-chatterbox:p0` (NGC pytorch:25.10 + chatterbox-tts 0.1.7 `--no-deps`, constraints pin NVIDIA torch; torchaudio forced to 2.9.0 because dep resolution pulled 2.11 which fails to load). Ran Chatterbox multilingual en/fi/sv zero-shot: works, Whisper-large-v3-turbo WER 0.00/0.00/0.04, RTF 0.55 (first call 1.4 incl. warmup), model load ~57 s. Chatterbox has built-in PerTh audio watermark. Forced-EOS warnings appeared (repetition/long tail) but output was complete. Files in `phase0/` (in/, out/, scripts/, docker/chatterbox/, hf_cache/ ~3+ GB).

- **2026-10-13 (8)** — Host ffmpeg 6.1.1 installed by Julio. Phase 0 prerequisites complete; next: SadTalker + Chatterbox (fi/sv/en) smoke tests, license audit.

- **2026-10-13 (7)** — GPU-in-Docker verified via CDI (`--device nvidia.com/gpu=all`); NGC pytorch:25.10-py3 pulled; torch sees GB10 (12,1), arch list sm_80..sm_120 + compute_120 (runs via sm_120 compat). flash_attn 2.7.4 imports (kernels not yet tested on real model). Disk 218 GB free.

- **2026-10-13 (6)** — Julio-approved cleanup: removed Ollama gpt-oss:120b, qwen2.5vl:72b, qwen3.5:35b, ministral-3:14b and LM Studio gpt-oss-120b-GGUF, Qwen3.5-35B-A3B-GGUF. Disk now 236 GB free.

- **2026-10-13 (5)** — Demo/PoC simplifications: no enrollment verification, no delete keys; delete button keeps consent video. `ARCHITECTURE.md` -> v0.4. Model inventory of the Spark taken (see §12); nothing deleted yet.

- **2026-10-13 (4)** — Julio's answers folded in: remote consent/enrollment from files, anyone can render, no login (Streamlit demo), fi/en/sv, user-only deletion, no retention. `ARCHITECTURE.md` rewritten as v0.3. Env check on the Spark (aarch64, GB10 cc 12.1, driver 580, Docker 29.1.3, 119 GB RAM): disk 98% full (20 GB free), docker shows only runc runtime, ffmpeg/psql missing on host.

- **2026-10-13 (3)** — Julio's decisions recorded (in-person consent video, Ollama OK, corner AI mark, admin-only deletion, no script approval, Finland/EU, internal+external). Wrote `ARCHITECTURE.md` v0.2. Flagged Finnish TTS quality as top risk.

- **2026-10-13 (2)** — University context set: must be legal and defensible. Added legal & compliance outline (§7) and draft architecture (§8). Policy: permissive licenses only, consent-first, on-prem, disclosed/watermarked outputs.

- **2026-10-13** — Project started. Research on GB10 constraints and candidate models; chose
  2D talking-head + offline rendering; drafted pipeline and shortlist. Created `HANDOVER.md`
  (merged from original Avatar Maker md).

---

## 15. Landscape research and experiment backlog (2026-10-13)

Sources: [PunithVT/ai-avatar-system](https://github.com/PunithVT/ai-avatar-system) (MIT; Whisper->LLM->Chatterbox->MuseTalk, Celery/Redis, persistent worker, fallbacks, **no consent step**),
[InfiniteTalk](https://github.com/MeiGen-AI/InfiniteTalk) (Apache-2.0; Wan2.1-14B; streaming mode with context frames; head/body aligned to audio; video-to-video; colour shift beyond ~1 min),
[MultiTalk](https://github.com/meigen-ai/multitalk) (APG against colour error accumulation),
[EchoMimicV3 paper](https://arxiv.org/html/2507.03905v4) (windows show colour/identity inconsistency; Long Video CFG for >138 frames),
[NVIDIA forum: Wan on Spark](https://forums.developer.nvidia.com/t/image-to-video-generation-using-the-spark-vs-pc/370077) (anecdotal: 14B-class models are slow on GB10).
Caveat: speeds/VRAM are from READMEs/blogs/forums, not reproducible benchmarks; MuseTalk dependency licenses unverified.

**Own measurements (384x384 head crop, EchoMimicV3-Flash):** sampling 27 s per 81 frames (656x880: ~150 s; 512: ~53 s). Head motion is controlled by **seed** and **audio_guidance_scale**; text prompt and text guidance_scale have ~no effect (Flash is distilled); TeaCache off and audio_scale gave no gain. Chaining segments from the last frame causes colour/contrast drift (visible by ~20 s); re-anchoring each segment to the original photo avoids it.

**Backlog (all to be tried; status in checkboxes):**
- [x] A. 384 demo done (`phase0/out/demo384_final.mp4`, 32 s, 384x384, 11 segments x 2 seeds, ~50 min wall). Result: **no colour drift** (brightness 143-145, contrast 68-69, saturation 48-50 flat over 32 s, `scripts/video_qc.py`); head motion clearly larger (best seed: x 12.5% / y 13% of width/height over 3.2 s); teeth natural off-white; joins show mild jumps (frame diff up to 2.7x average at 4-frame xfades) -> improve with longer windows / overlap blending. Seeds picked: 21 for 8/11 segments. Julio must still judge lip-sync, accent, naturalness.
- [x] B. Base-video approach via **MuseTalk v1.5** (MIT) on Julio's webcam clip: works on GB10. Output `phase0/out/mt_A_final.mp4` (768x768, 25 fps, 37.4 s, one continuous take, no segment seams, real head motion). Weaknesses: webcam clip is dark/yellow, mouth patch is soft (256 px native), moustache not preserved around lips, occasional jitter. Julio must judge lip-sync, accent, naturalness. See §16.
- [ ] C. InfiniteTalk audio-only on GB10 (14B; try fp8, `--mode streaming`, 480P) as quality ceiling; record speed and drift.
- [ ] D. EchoMimic Long Video CFG with longer windows (e.g. 161+ frames) vs. 81-frame re-anchored.
- [ ] E. Persistent worker (load weights once, loop segments); ~40% of wall time is model load today.
- [ ] F. Fallbacks (TTS/animation/seed) instead of hard failure.
- [ ] G. Objective evals: SyncNet LSE-C/D (lip-sync), identity similarity (not InsightFace: licence), per-second colour drift, head-motion metric (`scripts/motion_metric.py`).
- [ ] H. Accent: compare CosyVoice2 and Chatterbox cfg_weight 0 / fine-tune on the 30-min recording (no public Chatterbox accent-fine-tune recipe found; own R&D).
- [ ] I. SBOM/licence audit incl. MuseTalk deps, InfiniteTalk, SyncNet.
- [ ] J. Remove runtime network dependency (spacy-pkuseg model fetched from GitHub on first run).

---

## Notes for any AI picking this up

- Re-verify named models/repos still exist and match the specs above; this space moves fast.
- Don't lock a final model stack before licensing is confirmed.
- Never put secrets/passwords in this file.
- After meaningful work, update §3, §4, §7-§10 and append to §11.

---

## 12. Spark model/disk inventory (2026-10-13, read-only scan; nothing deleted)

Disk: 925 GB, 859 GB used, ~20 GB free. Avatar models (TTS/animation/ASR) installed: **none**.

| Location | Size | Notes |
|---|---|---|
| `~/.lmstudio/models` | ~329 GB | 11 GGUF LLMs (Qwen3.5-122B, Nemotron-3-Super-120B, gpt-oss-120b, gemma-4-26B, etc.) |
| Ollama (`/usr/share/ollama`) | ~208 GB | 7 local models + 6 cloud stubs (cloud = no disk) |
| `~/Desktop` | ~186 GB | not models; unscanned |
| `~/AI_Projects` | ~48 GB | incl. 7 GB `.git`, several Rhizomatic copies (~5.5 GB each) |
| Docker | ~12 GB images | 96% reclaimable |
| `~/.cache` | ~6 GB | pip 3.3 GB, huggingface 1.7 GB |

Duplicates across LM Studio and Ollama: gpt-oss-120b, Qwen3.5-35B, Ministral-3-14B.

**Update after cleanup (2026-10-13):** removed the models above; kept LM Studio Ministral-3-14B, Qwen3.5-122B, Qwen3.5-27B, gpt-oss-20b, Nemotron, gemma, Mistral. Ollama still has llama4:scout (67 GB), llama3.2-vision, nomic-embed-text.

---

## 13. Phase 0 reproduction notes

- Image: `phase0/docker/chatterbox/Dockerfile` -> `docker build -t avatar-chatterbox:p0 .`
- Run flags: `--device nvidia.com/gpu=all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 --user $(id -u):$(id -g) -e HF_HOME=/hf -e HOME=/tmp`
- Scripts: `phase0/scripts/tts_test.py` (TTS en/fi/sv), `phase0/scripts/asr_check.py` (Whisper WER check).
- Gotchas: chatterbox pins torch==2.6.0 (never let pip replace NGC torch); torchaudio must be 2.9.0; spacy-pkuseg downloads a model from GitHub at first run (unneeded Chinese segmenter, but a runtime network dependency to remove/vendor); HF downloads are unauthenticated (set HF_TOKEN if rate-limited).
- To audit: licenses of resemble-perth, s3tokenizer, conformer, spacy-pkuseg, pykakasi, diffusers/transformers pins.

## 14. Phase 0 animation reproduction notes

- Image: `phase0/docker/echomimic/Dockerfile` -> `docker build -t avatar-echomimic:p0 .` (NGC 25.10 base).
- Skipped from upstream requirements: tensorflow, retina-face, mmgp (unused by `infer_flash.py`); `decord` is import-only and stubbed in `/opt/stubs` (no aarch64 wheel).
- Pins that matter: diffusers==0.35.2, transformers==4.57.1; NGC `torchao` must be uninstalled (breaks both libraries' quantizer imports). Latest diffusers/transformers (0.41/5.x) failed.
- Harmless warning: `low_cpu_mem_usage ... load_model_dict_into_meta` (diffusers version drift); weights load with 0 missing/unexpected keys.
- Weights: `phase0/weights/` (not in git; ~23 GB). Download script `phase0/scripts/hf_download.py`.
- To audit: LICENSE of Wan2.1-Fun (Apache-2.0 per HF card), echomimic_v3 repo (Apache-2.0), chinese-wav2vec2-base (MIT), imageio-ffmpeg/moviepy deps.

## 16. MuseTalk base-video pipeline (2026-10-13)

Why: Julio rejected the EchoMimic segment approach (different head position at each segment start, poor movement). The base-video approach keeps **his real head motion** and only re-syncs the mouth to the new speech.

- Upstream: `TMElyralab/MuseTalk` commit `0a89dec` cloned to `phase0/musetalk` (git-ignored). Patch: `phase0/patches/musetalk_no_mmpose.patch` (apply with `git apply`): replaces mmpose/DWPose (no aarch64 build) with `face-alignment` 68-pt landmarks, and loads the legacy resnet18 checkpoint with `weights_only=False` (file from download.pytorch.org).
- Image: `phase0/docker/musetalk/Dockerfile` -> `avatar-musetalk:p0` (NGC 25.10, diffusers 0.35.2, transformers 4.57.1, torchao and non-headless opencv removed).
- Weights: `phase0/scripts/mt_download.py` -> `phase0/weights/musetalk` (3.8 GB: MuseTalk v1.5 unet, sd-vae-ft-mse, whisper-tiny, face-parse-bisent 79999_iter.pth from Google Drive id `154JgKpz...`, resnet18). face-alignment fetches S3FD + 2DFAN4 from adrianbulat.com at first run (runtime network dependency). **Licence audit pending** for face-parse-bisent and S3FD/FAN weights.
- Base video: webcam clip 2048x1536 15 fps -> `crop=1100:1100:330:0`, scale 768, `minterpolate` to 25 fps (`phase0/in/base_768_25fps.mp4`, first 39 s).
- Run: `phase0/scripts/musetalk_run.sh <task.yaml in phase0/in> <result_dir>`; yaml has `video_path` and `audio_path` (16 kHz wav) under `task_0`.
- Voice: new reference from the webcam clip (Julio speaks English with a **Spanish accent**; he said this accent is wanted). Chatterbox clones with `scripts/tts_clone.py`: `phase0/out/clone_{vA_cfg0,vA_cfg3,vB_cfg0,vB_cfg3}.wav` (refs: 0-15 s and 20-35 s of the clip; cfg_weight 0 / 0.3). MuseTalk run used `vA_cfg0`. **Julio to choose the best-sounding variant.**
