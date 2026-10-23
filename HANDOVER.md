# AVATAR Hub — Handover File

> **Purpose:** single source of truth for project history and context, so any CLI / AI model
> can pick up where the last one left off. **Read this first. Update it at the end of every
> working session** (revise Status / Decisions / Next steps, append to the Changelog).

Last updated: 2026-10-23 · Owner: Julio Serrano

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

## 17. Session 2026-10-14: lip fix, grading, fi/sv

- **Julio's verdict:** MuseTalk base-video result is the right approach (continuous), but "only the lips are very bad"; voice variant `vA_cfg0` is the best of the four; a longer reference (up to 30 min) may improve the voice later (not yet provided; task H).
- **Diagnosis (frame zoom):** MuseTalk's 256 px mouth patch is smooth and hairless (no moustache/beard texture), pinker than the dark webcam face; looks pasted.
- **Fix:** GFPGAN v1.4 (Apache-2.0) face restoration as post-process (`phase0/scripts/restore_face.py`, `restore_run.sh`, image `avatar-restore:p0` from `docker/restore/Dockerfile`, weights `weights/gfpgan/GFPGANv1.4.pth`, weight 0.5, 80 % blend) + ffmpeg grade (gamma 1.3, sat 0.9, slight blue, unsharp). Lips and nose are visibly crisper and the image is brighter. Remaining limits: still somewhat plastic skin, source webcam is low quality, moustache not fully restored. ~3.5 min per 37 s on GB10.
- **Outputs (`phase0/out/`, git-ignored):** `mt_A_v2_graded30.mp4` (30 s, en), `mt_fi_v2.mp4`, `mt_sv_v2.mp4` (~20 s each; clones `clone_{fi,sv}_vA.wav`, Whisper-verified intelligible; script `scripts/tts_multi.py`, task `in/mt_task_fisv.yaml`).
- **Not done:** InfiniteTalk v2v test (large download, backlog C), accent fine-tune on 30 min (H, needs Julio's recording), licence audit of GFPGAN/facexlib deps (I): GFPGAN code Apache-2.0, facexlib MIT, basicsr Apache-2.0; weights licence to confirm.

## 18. Session 2026-10-14 (cont.): InfiniteTalk on GB10, universal progress bar

- **Julio's verdict on §17:** GFPGAN-restored MuseTalk video is "shit"; voice is fine. Test InfiniteTalk. New, better source clip: `samples/Julio Serrano/2026-10-14-090944.webm` (22.9 s, 2048x1536 15 fps, daylight office, glasses, beard). Use it for tests.
- **Progress bar rule (Julio):** every long job must show up in ONE fixed command he keeps open in a terminal:
  `cd "/home/julios/AI_Projects/AVATAR Hub" && ./phase0/scripts/progress_all.py`
  It reads `phase0/progress/*.json` (git-ignored). Register jobs with `phase0/scripts/pg.py` (`dir` = download size, `log` = tqdm regex in a log, `count`, `manual`; `rm` when done). Also lists running containers.
- **InfiniteTalk setup:** repo `MeiGen-AI/InfiniteTalk` commit `50aa0a9` in `phase0/infinitetalk` (sparse checkout without assets/examples; git-ignored), patch `phase0/patches/infinitetalk_aarch64.patch` (xfuser/xformers/quanto/decord/kokoro optional; xformers attention → SDPA; wav2vec eager attention; drop `inspect.ArgSpec`). Image `avatar-infinitetalk:p0` (`phase0/docker/infinitetalk/Dockerfile`, includes apt ffmpeg). Runner `phase0/scripts/infinitetalk_run.sh <json in phase0/in> <outname> [args]`. Weights (Apache-2.0): `weights/Wan2.1-I2V-14B-480P` (83 GB), `weights/infinitetalk/single/infinitetalk.safetensors` (10 GB), `weights/chinese-wav2vec2-base`, `weights/lightx2v/loras/Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors` (Apache-2.0, step+CFG distill).
- **Speed on GB10 (480 bucket, 640x640, 81-frame chunks):** model load ~9 min. Full recipe (40 steps, 3 CFG passes) ~130-145 s/step → ~1.5 h per 3 s chunk: unusable. Do NOT pass `--num_persistent_param_in_dit 0` (forces offload). With lightx2v LoRA: `--lora_scale 1.0 --sample_text_guide_scale 1.0 --sample_audio_guide_scale 2.0 --sample_steps 6 --sample_shift 2 --offload_model False` → ~86 s/step (2 passes), ~9.5 min per chunk (~2.9 s new video) ≈ 3.3 min compute per second of video.
- **Quality (`out/it_lx3.mp4`, 4 s, image→video):** far better than MuseTalk/EchoMimic: natural head motion, beard/glasses kept, mouth opens with teeth. Defect: hallucinated waving hand in first frames (image mode). Next: video→video mode on the real clip (`in/it_v2v20.json`, `in/it_src640.mp4` = crop 900x900+563+330, 25 fps, audio `in/it_a20.wav` = first 20 s of clone vA) → `out/it_v2v20.mp4`.
- **Speed-up ideas not yet tried:** 4 steps instead of 6; persistent worker (avoid 9 min reload); fp8 weights; smaller bucket; TeaCache with LoRA.

## 19. Idea 2026-10-14: stylized 3D ("Toy Story") avatar instead of video generation

**Why:** 20 h of lectures; InfiniteTalk needs ~3.5 Spark-min per second of video (5 min/lecture ≈ 17.5 h/lecture ≈ 2-3 weeks total). A rigged 3D character driven by blendshapes renders in (near) real time, never drifts, lip-syncs any language, and is editable.

**Pipeline (proposal):**
1. Character (one-time): photo → stylized concept art (permissive image model, e.g. Qwen-Image-Edit / FLUX.1-schnell, licence to verify) → image-to-3D TRELLIS.2 (MIT) → retopology (needed for facial deformation) → rig (Rigify in Blender, or UniRig MIT code) → 52 ARKit shape keys (ARKit Creator Blender add-on (open source) or paid ShapeKeyGen/Faceit). Realistic fallback: commission a 3D artist for a Pixar-style Julio with ARKit 52 (~€300-1500, assumption).
2. Voice: Chatterbox clone (existing; 20 h ≈ 11 h on Spark).
3. Face from audio → ARKit blendshape curves: NVIDIA Audio2Face-3D (SDK MIT, models NVIDIA Open Model License: commercial OK but not OSI; aarch64 unverified) or LAM Audio2Expression (Apache-2.0 badge, ARKit 52). Fallback: Rhubarb Lip Sync visemes (MIT). TalkingHead (met4citizen, MIT, three.js) has built-in Finnish/English lip-sync.
4. Body: library of idle/talk/gesture clips (Mixamo, Adobe terms) + procedural head sway, blinks, saccades. Avoid EMAGE/SMPL-X/FLAME-based models (non-commercial licences) unless licence checked.
5. Render: Blender EEVEE scripted (offline, ~0.2-0.5 s/frame est.) or three.js/TalkingHead headless capture (real time, parallel instances). Compose slides + avatar + subtitles with ffmpeg; modular segments.

**Avoid:** Hunyuan3D (licence excludes EU/UK/KR); Ready Player Me (shut down 31 Jan 2026); SMPL-X/FLAME weights (non-commercial).
**GitHub precedents:** met4citizen/TalkingHead; semperai/amica (MIT, VRM); pixiv/ChatVRM; asanchezyali/talking-avatar-with-ai (Rhubarb + RPM + R3F); HumanAIGC-Engineering/OpenAvatarChat + aigc3d/LAM (Gaussian head + Audio2Expression); 0xGF/avatar-3d (photo → Pixar-style image → TRELLIS GLB via paid Replicate APIs).
**Status:** brainstorm; awaiting Julio's decisions (style, artist budget, bust vs full body, on screen always vs clips).

## 20. Decision + proof of concept 2026-10-14: stylized 3D avatar

- **Decision (Julio):** stylized/cartoon, NOT semi-realistic: "it is an avatar we want to be obvious that is ai".
- **PoC pipeline (works end to end on the Spark):** cloned voice wav → **LAM Audio2Expression** (Apache-2.0; repo `aigc3d/LAM_Audio2Expression` commit in `phase0/poc3d/` (git-ignored), weights `weights/lam_a2e` from HF `3DAIGC/LAM_audio2exp`, patch `phase0/patches/lam_a2e_eager.patch`; runs in `avatar-chatterbox:p0` because it needs torchaudio) → ARKit-52 JSON @30 fps (`scripts/a2e_run.sh`; **37 s audio in 0.7 s**) → **Blender 4.0.2** (Ubuntu arm64 apt package in image `avatar-blender:p0`, `docker/blender/Dockerfile`; no official aarch64 Linux build) with `scripts/blender_avatar.py` / `scripts/blender_run.sh`: imports GLB, keys shape keys (mouth gain 1.4), procedural neck/head motion (smooth noise + speech-energy nods), breathing, 3-point lights, EEVEE 1080x1080 → ffmpeg mux.
- **Speed:** ~0.2 s/frame at 1080x1080 EEVEE alone (0.42 s/frame while InfiniteTalk shared the GPU). 20 h at 30 fps = 2.16 M frames ≈ 5 days at 0.2 s (less at lower res / corner overlay; parallel instances possible).
- **Test character:** `mpfb.glb` from met4citizen/TalkingHead (CC0, MakeHuman/MPFB, ARKit + Oculus visemes). Realistic, used only to test lip-sync + speed. Output `out/poc3d/poc_mpfb_37s.mp4`.
- **Note:** LAM-A2E blendshapes are tuned to FLAME topology; jawOpen subdued (max ~0.39) → gain applied. No head rotation in its output (procedural instead).
- **Next:** stylized Julio character: photo → stylized concept images (Julio picks) → TRELLIS.2 → retopo/rig/ARKit-52 (or artist) → same pipeline. Compare NVIDIA Audio2Face-3D and Rhubarb for lip quality. Add eye saccades, gestures (Mixamo-style clips), slide compositing.
- **InfiniteTalk v2v 20 s result (`out/it_v2v20.mp4`, 640x640, 25 fps):** best realistic result so far: continuous, natural head motion and hand movement from the source clip, beard/glasses kept, mouth opens with teeth. Faces a bit red/saturated. Took ~70 min (slowed while Blender shared the GPU). Render-speed benchmarks for the 3D route (150 frames, GPU shared): EEVEE 480² 0.14 s/frame, Workbench 480² 0.077 s/frame, Workbench 1080² 0.19 s/frame.

## 21. Wii-style lecture test 2026-10-14 (Julio: "go for the test")

- **Concept (Julio):** avatar does not need real lip-sync; simple mouth + head + hand gestures synchronised to the text, like a Wii character; 480x480 squares.
- **Pipeline:** cloned voice → Whisper word timestamps (`scripts/asr_words.py`, in `avatar-chatterbox:p0`) → gesture cue sheet anchored on words (`in/poc_cues.json`; in production an LLM tags the script) → `scripts/blender_wii.py` (+ `scripts/gestures.py` library: idle, wave, hand_chest, open_palms, shrug, count, point_slide; ease in/out + wiggle; volume-driven jaw + mouth-shape variation; procedural blinks, head nods from speech energy, breathing; RGBA transparent 480x480 EEVEE 16 samples) via `scripts/blender_wii_run.sh` → `scripts/compose_lecture.py` (PIL slide 1920x1080 from `in/poc_slide.json`, avatar panel bottom-right with "AI avatar" badge, ASS word-timed captions, ffmpeg).
- **Rig axes (MPFB/Mixamo names, Blender pose Euler):** Arm y- lowers arm, x- raises sideways; with arm lowered ForeArm x- lifts hand forward/up, z- crosses body; Left = mirror (y, z negated). Debug: `scripts/blender_axes.py`, `scripts/blender_gesture_preview.py`.
- **Speed:** 37 s rendered in 71 s (0.063 s/frame, ~2x faster than real time, single process). 20 h ≈ 38 h single process; LAM/A2E not needed. Voice 20 h ≈ 11 h.
- **Output:** `out/poc3d/wii_lecture_demo.mp4` (1920x1080, 37 s).
- **Next:** Julio's stylized character (photo → concept art → 3D → rig, only ~6 mouth shapes needed); LLM gesture tagging; more gestures; parallel renders; batch pipeline per lecture.

## 22. Portrait mode 2026-10-14 (Julio: "i dont need mouth moving just head synchronized melodically with the voice and just a portrait shot chest up")

- **New default look:** chest-up portrait, mouth closed (slight smile), no arm gestures; head moves with the voice's melody.
- **Pipeline:** `scripts/prosody.py` (librosa pYIN pitch in semitones vs speaker median, RMS energy, onset strength, pauses >250 ms; runs in `avatar-chatterbox:p0`) → `scripts/blender_portrait.py`: chin follows pitch contour (high-pass vs 1.5 s baseline, -2.2°/semitone, x- = chin up), stressed-syllable beats → ~300 ms nods (onset peaks with energy, ≥0.35 s apart), new turn/tilt target per phrase (eased), tilt from intonation slope, settle in pauses, blinks random + at phrase starts, brows lift on high pitch, breathing. Head bone axes: x+ nod down, x- chin up, y turn, z tilt (`scripts/blender_headaxes.py`). Compose with `scripts/compose_lecture.py`.
- **Result:** `out/poc3d/portrait_lecture_demo.mp4` (37 s): 19 phrases, 41 beats, head range about ±7°. Render 0.066 s/frame at 480x480 (37 s in 74 s).
- **Character work now simpler:** no mouth shapes needed at all; only rig (neck/head) + optional blink/brow shapes.
- **Update (Julio: 1/3 size, circle):** avatar now a 160 px circle bottom-right (orange ring, "AI avatar" badge above), rendered at 320x320 (`--res 320 --dist 0.68 --dz 0.04`, head-and-shoulders) and downscaled; `compose_lecture.py` masks it with a circle (disc + alphamerge). 0.052 s/frame at 320² → 20 h ≈ 1.3 days single process. Output `out/poc3d/portrait160_circle_demo.mp4`.

## 23. Photo avatar with LivePortrait + seamless loop 2026-10-14

- **Julio:** keep the 3D circle for now (may develop animations later); do the same with video: real photo, only head moves; then: "instead of making a live animation we just generate a loop video of the live portrait that looks smooth and loops indefinitely".
- **LivePortrait (MIT code + weights, `KwaiVGI/LivePortrait`, commit 9b294b3 in `phase0/poc3d/liveportrait`, git-ignored)**: weights `weights/liveportrait/liveportrait/{base_models,retargeting_models,landmark.onnx}` (InsightFace weights NOT downloaded/used). One-time crop via face-alignment 68 pts (BSD) + LivePortrait `crop_image`; `landmark.onnx` (onnxruntime CPU) for 203 pts → eye ratio → blinks via `retarget_eye`. Head re-posed with `get_rotation_matrix` deltas (pitch + = nod down, matches head_motion), `stitching`, `warp_decode`. Script `scripts/lp_head.py`, runner `scripts/lp_run.sh`, image `avatar-liveportrait:p0` (`docker/liveportrait/Dockerfile`, FROM avatar-musetalk + onnxruntime etc.).
- **Shared motion:** `scripts/head_motion.py` — `compute(prosody)` (voice-synced, also used by `blender_portrait.py`) and `loop(seconds)` (sum of sines with whole cycles per loop → seamless; blinks kept off the seam).
- **Source still:** `in/lp_src_full.png` = frame at 21.4 s of `samples/Julio Serrano/2026-10-14-090944.webm` (mouth closed, frontal). Crop `--scale 2.0` fills the 160 px circle.
- **Speed:** 0.08 s/frame. Voice-synced 37 s: 89 s (`out/lp_head/`). **20 s loop: 49 s once**, then reused for any lecture length → per-lecture avatar cost ≈ 0 (only ffmpeg compositing).
- **Loop quality:** PNG seam diff 0.48 vs mean frame step 0.55 (invisible); mp4 keyframe adds ~1.5/255 at the seam (invisible).
- **Outputs:** `out/lp_loop/avatar_loop_20s.mp4`, demo `out/lp_loop_circle_demo.mp4` (37 s voice, loop repeats at 20 s). `compose_lecture.py --frames` now accepts a loop .mp4 (`-stream_loop -1`).
- **v2 loop (Julio: "head movement more pronounced and more blinking and smiling"):** `--amp 1.8 --blink_min 1.8 --blink_max 3.5 --smiles 3 --smile_base 0.15` → yaw about −13..+8°, pitch about −8..+5°, 7 blinks / 20 s, 3 smile bumps (~2.5 s, LivePortrait gradio smile keypoint offsets) + slight base smile; seam-safe. Outputs `out/lp_loop2/avatar_loop_20s.mp4`, demo `out/lp_loop2_circle_demo.mp4`. 50 s render.

## 24. Feedback round 2026-10-14 (afternoon)

- **Julio on loop v2:** "it look creepy now with the floating head movements" → wants slight smile, sideways head tilts and nods. New `head_motion.loop_nodtilt()` (`lp_head.py --style nodtilt`): held sideways tilts (0.6 s ease in, 1.5–3 s hold, ease out, alternating sides, ±3.5–4.5°), discrete nods (0.45–0.7 s, 30% double), yaw only ±1.2°, constant smile 0.35, blinks every 2–3.6 s; starts/ends neutral (seam exact). Output `out/lp_loop3/avatar_loop_20s.mp4`.
- **Julio on voice:** "there is a fart-like sound in the recording and the accent is pretty bad, I'm Julio not Giulio". Gap analysis of `clone_vA_cfg0.wav` found a 0.26 s non-speech sound at ~13.7–13.96 s (between "outcomes" and "like uptime") and a short burst at ~30.2 s. New `scripts/tts_qc.py`: per sentence best-of-N takes scored by Whisper WER + stray sound outside recognised words + speaking-rate sanity; variants: `en_A` (name spelled "Hulio"), `es_A`/`es_B`/`es_A_cfg3` (Chatterbox multilingual in **Spanish mode reading English text** → Spanish-accented English). Outputs `out/voice2_<variant>.wav`, log `out/tts_qc.log`.
- **Accent, honest limit:** Chatterbox zero-shot conditions on only ~6–10 s of reference, so a longer reference alone will not fix the accent; real options: (1) Spanish-mode trick above, (2) fine-tune on Julio's ~30 min recording, (3) compare another permissive zero-shot TTS (CosyVoice2, Apache-2.0).
- **Loop v3 final:** smile removed entirely (`--smile_base 0`; fixed bug where 0 fell back to 0.35); face = natural expression of the source still.
- **Voice QC run results (`out/tts_qc.log`, 14:02–14:17, 72 takes + Whisper, GPU shared):** all chosen takes have 0 s stray sound; WER 0 except "organise→organize" spelling. Name: "Hulio" spelling → Whisper hears "Julio". Spanish mode garbles sentence 1 ("Hello" → "Hey"/"Ellos"/dropped); needs English-mode or reworded greeting. Demo per voice with loop v3: `out/demo_voice2_{en_A,es_A,es_B,es_A_cfg3}.mp4`. **Awaiting Julio's choice by ear.**
- Progress bar gained `matches` kind (count regex hits in a log, e.g. finished sentences).

## 25. Voice fine-tuning plan 2026-10-14 (research)

- **Julio's ask:** optimal recording amount to fine-tune a voice that captures accent and mannerisms; see how others do it; a purpose-built recording script; quality/speed balance on the GB10.
- **Findings:**
  - Chatterbox community fine-tuning: `gokhaneraslan/chatterbox-finetuning` (Apache-2.0; Chatterbox + Turbo, 23 languages, LJSpeech/file datasets, offline preprocessing, LoRA r64/α128). It recommends LoRA for ≤10 h, a **minimum of 30+ min** for basic training, and 3–10 s clips. Others: `stlohrey/chatterbox-finetuning` (WIP, T3 + S3/flow), `Ahmed-Ezzat20/chatterbox-finetuning-multilingual` (LoRA), `reenigne314/chatterbox-indic-lora` (language LoRA).
  - Purwar & Choudhary 2026 (arXiv 2603.10904; LoRA on a Qwen-0.5B TTS backbone): gains are governed by **data diversity**; LoRA improved speaker similarity for every speaker; uniform data can amplify noise. Diversity matters more than raw minutes.
  - GPT-SoVITS (MIT) fine-tunes from ~1 min, but its languages are zh/en/ja/ko/yue (no fi/sv) → not a fit. CosyVoice 3 speaker SFT exists, but the open recipe covers LLM-only training and gives no data size → backup option.
  - Chatterbox architecture: T3 (0.5B LLM) produces speech tokens (content, prosody, **accent**); S3Gen renders timbre from the reference. **Accent and mannerisms live in T3 → LoRA on T3 first**; S3Gen fine-tuning is optional, later.
- **Recommendation:** ~24 min of **diverse** speech (read + expressive + free talk) instead of 30+ min of uniform reading. Script: `docs/voice_recording_script.md` (A accent paragraphs incl. Speech Accent Archive "Please call Stella" (CC, cite GMU); B accent-bearing sounds/stress; C lecture passages with numbers/names; D expressive range; E 6 min free speech for fillers/habits; F optional fi/sv).
- **Pipeline (to build when the recording exists):** VAD split into 3–10 s clips → Whisper transcripts (verbatim, keep fillers) → 90/10 split → LoRA on T3 (r 32–64), est. 1–2 h on GB10 (assumption, measure) → eval: Whisper WER, speaker similarity, blind A/B vs zero-shot with Julio → merge LoRA → `tts_qc.py` for production. Keep a mixed-data option (some base-language data) if fi/sv degrade.

## 26. Voice fine-tune, first run 2026-10-14

- **Recording:** `samples/Julio Serrano/voices/Voices.zip` (7 m4a sections 0, a–e, f-finnish; 19 min; 48 kHz mono AAC; noise floor −59…−70 dB, peaks −2…−6 dB). Julio is **from El Salvador** (Central American Spanish accent in English). He also read the section headings aloud (kept: still his voice).
- **Dataset:** `scripts/prep_voice_dataset.py` (ffmpeg→WAV first; silence split top_db 38, 3–10 s merge/split, batched Whisper per clip, verbatim) → `samples/.../voices/dataset/` (git-ignored): **215 clips, 16.8 min, mean 4.7 s**, en 210 / fi 5. 58 s run. (Word-timestamp Whisper on long files was CPU-bound and >20 min: avoid.)
- **Trainer:** own `scripts/ft_t3_lora.py` (+ `scripts/ft_run.sh`, image `avatar-tts-train:p0` = chatterbox + peft 0.21, torchao removed). LoRA on the multilingual T3 Llama backbone (q,k,v,o,gate,up,down); conditioning prompt and speaker embedding taken from a **different** clip of the speaker; full target clip supervised; next-token shift; 10% unconditional; stratified 10% held out (194 train / 21 val); keeps `lora_best` by val loss. Reasons not to use `gokhaneraslan/chatterbox-finetuning` as-is: English T3 + vocab resize, prompt taken from the same clip with the first prompt-length speech labels masked (wastes ~2/3 of short clips). The built-in `T3.loss` has no next-token shift (don't use it).
- **Runs (≈12 s/epoch on GB10):** r16/lr2e-4 overfits after epoch 3 (val 4.23 → 3.68 → 5.3); **r8/α16/lr1e-4/dropout 0.1: best epoch 6, val 3.70 (−13%), stable** → `out/ft/r8_lr1e4/lora_best`; r16/lr5e-5: 3.71.
- **Eval (`scripts/ft_eval.py`, best-of-2 with QC; held-out real clips for VoiceEncoder similarity):** webcam ref sim 0.78, **clean ref (`dataset/wavs/section_c_044.wav`) 0.86**, **fine-tuned + clean ref 0.88**; EN WER 1.1% for all, 0 stray sound with the clean ref; Finnish: fine-tuned mangles one long word (English-heavy data). Demos: `out/demo_ft_{1_base_webcamref,2_base_cleanref,3_finetuned_cleanref}.mp4`. **Awaiting Julio's ears for accent.**
- Eval bug fixed: snapshot base weights BEFORE `PeftModel.merge_and_unload()` (it mutates in place); script asserts the adapter changes weights.
- **Julio: "voice 3 is good"** → production voice = fine-tuned LoRA `out/ft/r8_lr1e4/lora_best` + clean ref `dataset/wavs/section_c_044.wav`. New `scripts/say.py` / `scripts/say_run.sh "<text>" <name>.wav` (sentence split, best-of-3 QC, early stop on a perfect take) → `out/messages/`. First message: `out/messages/tatiana_message.{wav,m4a}` (20.7 s).

## 27. Front end v0: Streamlit voice tool 2026-10-14

- **Julio's spec:** landing says this is the University of Vaasa voice and video tool; 3 buttons (Voice active; AI Avatar + AI Studio greyed out); Voice: library of voices, create new voice (show what to read, record in browser or upload), progress, 3 versions, pick one or give text feedback in a loop until satisfied, save as profile; main voice page: select voice, text box → speech, optional tone/emotion and file formats (mp3, m4a…), play or download, save everything made under that voice.
- **Code:** `app/` — `app.py` (UI, router home/voice; voice views library/create/record/build/review), `engine.py` (one Chatterbox multilingual model in memory, LoRA as cached weight deltas with a strength scale, best-of-N + Whisper QC, ffmpeg export WAV/MP3/M4A/OGG/FLAC, atempo pace), `store.py` (voice library on disk), `feedback.py` (rule-based feedback → parameter steps A/B/C, shown to the user), `jobs/build_voice.py` (background: convert/unzip → `prep_voice_dataset.py` → `ft_t3_lora.py` (r8, lr 1e-4, dropout 0.1, best epoch) → choose 5 most typical clean reference clips (VoiceEncoder centroid) → render versions A Natural (no LoRA) / B Balanced (LoRA ×1.0) / C Strong (LoRA ×1.5)); registers in the terminal progress view. `Dockerfile` (FROM avatar-tts-train + streamlit 1.65) → image `avatar-hub-app:p0`; `run.sh` starts it on **http://localhost:8501** (bound to 127.0.0.1). Tests: `app/tests/smoke.py`, `app/tests/review.py` (streamlit.testing, run with `docker exec`).
- **Data:** `data/voices/<id>/` (git-ignored): profile.json, consent.json (typed name + checkbox statement), recordings/, dataset/, train/, candidates/rN/, generations/<time>_<words>/ (meta.json + audio in each chosen format), job.json/job.log. Julio's voice imported as `julio-serrano` (LoRA r8 + ref section_c_044).
- **Measured:** first speech after app start 78 s (engine load ~40 s); end-to-end build from 7.1 min of recordings: **3 min 54 s** (91 clips); feedback round (3 versions) ≈ 1 min.
- **Known limits:** feedback is keyword rules (no LLM); pitch/age not adjustable; Chatterbox fetches spacy-pkuseg from GitHub at first run (backlog J); single user (no queue); consent is typed name + checkbox (no consent video yet).
- **Bug fixed (Julio hit it):** `RuntimeError: stack expects each tensor to be equal size` in `alignment_stream_analyzer.step`. Cause: Chatterbox multilingual `T3.inference` registers new forward hooks (AlignmentStreamAnalyzer) on every call and never removes them; with a shared engine, overlapping generations (double click / rerun) mix attention maps. Fix in `app/engine.py`: `threading.RLock` around `speak` + clear `tfmr` forward hooks before each `generate`. Test `app/tests/concurrency.py` (3 threads at once → 0 errors, hooks stay bounded).
- **Dark theme** (Julio): `app/.streamlit/config.toml` (base dark, bg #0e1420, panels #182235, accent #f0a028) + dark custom CSS in `app.py`.
- **Realistic progress (Julio: bar jumped 50% → 100% → replaced):** `engine.py` swaps chatterbox T3's `tqdm` for a step counter (`_StepTqdm`) → live per-token progress within each sentence (expected tokens learned online, ~1.7 tokens/char), phases speaking → checking, monotonic, retries shown as "retry k". `app.py` `run_with_progress()` runs generation in a thread and redraws the bar 4×/s with stage text + smoothed time left; bar stays at "100% · Done in N s" and the audio appears under it. Review rounds use one combined bar over A/B/C.
- **Speed fix found via the progress timeline:** Whisper `return_timestamps="word"` took **~19.8 s per sentence** on GB10 (vs 0.24 s for segment timestamps). QC now uses segment timestamps (`engine.py`, `say.py`): 3-sentence speech 33 s → **6.7 s**. Stray-sound check is now per segment (gaps between phrases + tails), not between individual words.

## 28. Demo video 2026-10-21: "alternative to recording lectures over Zoom"

- **Output:** `phase0/out/demo_zoom/demo_zoom_alternative.mp4` (1920x1080, 25 fps, 2:15). Intro slide with the avatar (13 s), support slide with the voice-over (1:58), outro slide with the avatar (4 s). Script in `out/demo_zoom/script.txt`.
- **Voice:** production fine-tuned voice via `scripts/say_run.sh` (`out/messages/demo_{intro,body,outro}.wav`); all 30 sentences passed QC on the first take.
- **Avatar:** InfiniteTalk v2v on `in/it_src640.mp4` (Julio's real webcam clip; Julio chose this over photo mode), lightx2v recipe (6 steps), one pass for intro + 1.2 s gap + outro (`in/demo_av.{wav,json}` → `out/demo_av.mp4`, 18.5 s), split at 13.82 s. 7 chunks, ~82 s/step, ~1 h including model load.
- **Slides:** `scripts/demo_slides.py` writes HTML (dark theme of the app), rendered to PNG with headless Firefox (`--no-remote --profile <dir under home>`; snap Firefox can't write to /tmp). The support slide builds in 7 states timed from Whisper word cues (`asr_words.py` → `body_words.json`). `scripts/demo_compose.py` overlays the avatar in a rounded box and joins the parts with ffmpeg.
- **To check by ear:** Whisper heard "made with I" for "made with AI" (intro) and "one even sound" for "uneven sound" (body); these may be pronunciation issues.
- **Progress view gotcha:** for `log` jobs the ETA is extrapolated from the last 5 min, so during InfiniteTalk's ~9 min model load it shows absurd values (e.g. 22 h). The real time is ~8.3 min per chunk.

## 29. Demo v2 2026-10-21: studio avatar, nodding corner avatar, structure slide

- **Output:** `phase0/out/demo_zoom/demo_zoom_alternative_v2.mp4` (2:37). Parts: intro with avatar (11 s), "why" slide with voice-over (1:57), new "How a lecture is built" slide with voice-over (avatar opens → slides + voice-over with an optional nodding face → avatar closes; 25 s), outro with avatar (4 s). The voice-over slides show a 148 px nodding avatar circle top-right with a green "● AI avatar" light.
- **Studio media** (`samples/Julio Serrano/Studio/`): `main.MP4` (78 s, 4K 25p 10-bit 4:2:2, standing, gesturing, white curtain, UVA hoodie, no glasses), `Standing still.MP4` (50 s), `DSC00001-12.JPG` (7008x4672). Avatar source `in/studio_src640.mp4` = 0–22 s, crop 1400x1400+1220+120 (chest-up with hands). Still for the circle = DSC00002 → `in/studio_still.png` → LivePortrait `--loop 20 --style nodtilt --smile_base 0.35 --scale 2.0 --fps 25` → `out/lp_studio/avatar_loop_20s.mp4` (42 s render).
- **"AI" pronunciation (Julio: it said "ay"):** the plain "AI" spelling is heard as "I" (0/3 takes). "ay eye" works at the end of a short sentence ("I was made with ay eye.", 3/3), but mid-sentence it gives "I-I". "eh eye" worked 3/6 in context. Takes are judged *in context* (4 s of the preceding audio + take) because Whisper reads isolated takes differently. Good takes spliced in at quiet points: `out/messages/demo2_intro_fixed.wav`, `demo2_body_fixed.wav`. Tools: `scripts/tts_try.py` (spelling variants × takes, env TAKES), `say.py` QC now treats "ay eye"/"a.i." as "ai".
- **Removed the drawn-out "aaand"** by rewording the intro (no comma-"and").
- **Render:** InfiniteTalk v2v 16.4 s, 6 chunks, 108 s/step while TTS shared the GPU, 82 s/step alone; ~66 min including load. GB10 = 128 GB unified memory; the render uses ~70 GB and keeps the GPU at ~90–96%. It's compute-bound, so running two heavy jobs at once doesn't help. Speed backlog: persistent worker (skip the 9 min load), FP8, 4 steps, TeaCache.

## 30. Demo v3 2026-10-22: new intro line, "Our service" slide

- **Output:** `phase0/out/demo_zoom/demo_zoom_alternative_v3.mp4` (3:11). Order: intro avatar (13 s) → why slide (1:57) → how a lecture is built (25 s) → **our service** (32 s) → outro avatar (4 s). Script in `out/demo_zoom/script.txt` (v2 script kept as `script_v2.txt`).
- **Intro (Julio's wording):** "Hi, I am Julio Serrano's avatar. I have been created with a local artificial intelligence model, developed in-house. Please follow me through this demo." Rendered alone (`in/demo3_intro.{wav,json}` → `out/demo3_intro.mp4`, 13.6 s, 5 chunks, ~57 min). The outro is reused from `out/demo2_av.mp4` at 11.711 s. Note: the base models are open source; only the voice fine-tune is in-house ("personalised in-house" would be exact).
- **Our service slide** (Julio's process): 1 first meeting → 2 needs and fit (is an avatar suitable) → 3 studio session (video, photos, audio) → 4 avatar + voice cloned → 5 teacher sends scripts/slides, we build the lessons. Banner: "The teacher's part: one meeting, one studio session, then scripts and slides." Placed before the outro so the demo keeps its own avatar → voice-over → avatar structure.
- **Fixes:** the `.step.on` highlight border was overridden by `.step` (now shown); the structure slide benefits too. `demo_compose.py` now takes separate intro/outro avatar videos.

## 31. Two new avatars 2026-10-23: Rodrigo Rabetino, Joni Salminen

**Recipe for a new person (photos + recording, no studio video):**
1. Voice: put the recording in `data/voices/<id>/recordings/` (profile via `store.create_voice`) and run `app/jobs/build_voice.py <id>` in `avatar-hub-app:p0` (dataset → LoRA r8 → refs → A/B/C auditions). If the recording has other speakers (Zoom Q&A), first cut + transcribe it, cut the Q&A off, and run `phase0/scripts/speaker_filter.py` (VoiceEncoder similarity to the main speaker); join the kept clips into one wav as the recording. The VoiceEncoder alone does **not** separate a moderator reliably (0.89 vs 0.95 typical), so cut by transcript too.
2. Avatar speech: `phase0/scripts/say_clean.py <id> "<text>" <out.wav>` (stricter QC, below), never the plain path.
3. Corner loop: LivePortrait `--loop 20 --style nodtilt --smile_base 0.35 --scale 2.0 --fps 25` on a frontal, mouth-closed still → encode `frames/` to `avatar_loop_20s.mp4`.
4. Talking video: InfiniteTalk **image mode** (`cond_video` = png) from a waist-up crop (832x1040, head ~38% of height), lightx2v recipe (6 steps), ~55 min for 13 s alone. The model zooms in tighter than the source.

**Speech QC (Julio: "remove hesitation and other artifacts … no speech errors"; legible beats 100% real):** the app's sentence-level QC passed a take with drawn-out words ("with a" 0.66 s, "this" 1.3 s) because Whisper's text hides them. `say_clean.py` scores each take with word timestamps: 3·WER + 2·stray + 2·fillers (uh/um/…) + 3·stretch (word longer than 0.075 s/letter + 0.15 s; final word +0.25 s) + 2·gaps (>0.25 s inside a sentence); up to 12 takes per sentence; calmer settings temp 0.6, exaggeration 0.35. Roughly half the takes fail; word timestamps cost ~20 s per take on GB10 (fine offline). Possessive name + "avatar" slurs ("Rabetino's avatar" → "Ravitinos-Avatar"): use "the avatar of <name>".

**Rodrigo Rabetino** (`samples/Rodrigo Rabetino/`): 17 photos (`rodrigo-1663.zip` → `Studio/`), 10 min lecture video (voice), ElevenLabs clip as look reference (chest-up, hand gestures). Voice `data/voices/rodrigo-rabetino`: 89 clips / 9.0 min, val 4.83 → 4.33; **Julio chose B**. Loop `out/lp_rodrigo/avatar_loop_20s.mp4` (still `in/rodrigo_still.png` from 1678). Video: v1 `out/rodrigo_intro.mp4` rejected (voice stutter); **v2 `out/rodrigo_intro2.mp4`** (13.2 s, 576x704, say_clean voice, hand gestures at 4–6 s, model added a wristwatch).

**Joni Salminen** (`samples/Joni Salminen/`): 18 photos (`edited.zip` → `Studio/`), 49 min Zoom lecture (`GMT20260908-081802_Recording.m4a`). Q&A from clip 451 ("That's it for the presentation. Johnny, …") cut; 442 clips / 42.6 min kept. Voice `data/voices/joni-salminen`: val 4.71 → 4.05 (best epoch 4); **Julio chose B**. Loop `out/lp_joni/avatar_loop_20s.mp4` (j-7, slight smile). Video from `in/joni_src.png` (j.jpg) + `in/joni_intro.wav` → `out/joni_intro.mp4` (12.4 s, 576x704, ~50 min; brief thumbs-up at ~0.8 s, open-hand gesture at ~5.4 s, no colour drift).

**Consent:** both profiles were created by Julio on their behalf; their own consent statements are still to be filed.
**Gotchas:** a `while pgrep -f "<pattern>"` wait loop matches its own command line and never ends (wait on a log line instead); paths contain a space ("AVATAR Hub"), so wrap docker calls in a shell function, not an unquoted `$R` string.
