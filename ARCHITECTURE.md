# AVATAR Hub — Architecture (v0.4, demo / proof of concept)

Status: **approved to start Phase 0 (feasibility).** Companion to `HANDOVER.md`
(history/decisions). If the two disagree, `HANDOVER.md` decisions win; fix this file.

v0.4: this is a demo / proof of concept — enrollment verification, delete keys and reviewer
workflows are deferred to a later production phase. v0.3 changes vs v0.2: demo-first (no login, Streamlit UI), remote enrollment from uploaded
files, anyone can render any avatar with consent on file, user-held delete key, no retention
limit, languages fixed to Finnish / English / Swedish.

---

## 1. Goals and non-goals

**Goals**
- Self-hosted tool for a Finnish university: a person provides photos, up to 30 min of audio
  and a recorded consent; anyone using the tool can then render lip-synced videos of that
  avatar from text, in Finnish, English or Swedish.
- Offline/batch rendering on one DGX Spark (GB10, sm_121, 128 GB unified, ~273 GB/s).
- Defensible under GDPR / EU AI Act: stored consent evidence, disclosed + marked AI output,
  permissive-license models only.
- Demo first; designed so login/roles can be added later without a rewrite.

**Non-goals (v1)**: real-time avatars; 3D avatars; multi-GPU; user accounts/SSO; script
approval; automatic deletion or retention policies.

## 2. Decisions this design rests on

| # | Decision |
|---|---|
| D1 | 2D talking head, offline batch |
| D2 | Production stack uses only permissive licenses (Apache-2.0 / MIT) |
| D3 | Consent is a recorded spoken phrase (camera recording **or uploaded video/audio file**); **remote enrollment allowed**; evidence stored and retrievable |
| D4 | Ollama cloud may be used; DPA assumed for all instances |
| D5 | Visible disclosure = small "AI" mark in a corner **plus** invisible C2PA metadata + watermark (approved) |
| D6 | Plain **"Delete avatar and data"** button in the UI (no keys, no login); it deletes everything **except the consent video + consent record**, which are kept for later proof; no automatic purge; no retention limit |
| D7 | No script-approval workflow |
| D8 | Finland/EU; outputs internal and external; campus and external access |
| D9 | **Anyone using the tool can render any avatar that has valid consent on file** — consent is what unlocks use |
| D10 | Demo: no login; Streamlit UI |
| D11 | Languages: Finnish, English, Swedish. Voice quality issues fixed iteratively |
| D12 | Enrollment accepts up to 30 min of audio from files |

## 3. System context

```
 Anyone (campus / external) ──► [Caddy: TLS, optional shared passphrase] ──► Streamlit UI
                                                                              │
                                                              service layer (Python package)
                                                                              │
                      ┌──────────────────┬────────────────────────────────────┤
                      ▼                  ▼                                    ▼
                 Postgres        Encrypted volume                  Ollama cloud (optional,
          (metadata, queue,      (uploads, consent video,           script drafting only)
           audit)              voice models, outputs)
                      ▲
                      │ claim jobs (SKIP LOCKED), one GPU job at a time
        ┌─────────────┴──────── worker containers (NGC PyTorch) ────────────┐
        │ ingest/verify │ voice-train │ tts │ animate │ post (label+C2PA+wm)│
        └───────────────────────────────────────────────────────────────────┘
```

The Streamlit app talks only to the **service layer** (`libs/core`). A later FastAPI + React
front end plus SSO reuses that layer unchanged.

## 4. Components

| Component | Tech | Responsibility |
|---|---|---|
| UI (demo) | Streamlit (raise `server.maxUploadSize` to several GB) | Enroll, pick avatar, write script, queue/preview, delete |
| Service layer | Python package `libs/core` | All business rules: consent gate, job creation, delete, audit |
| Database + queue | PostgreSQL (`SELECT … FOR UPDATE SKIP LOCKED`) | Metadata, jobs, audit |
| Workers | One NGC PyTorch ≥25.10-py3 container per model family | Poll for their job type; one GPU job at a time (advisory lock) |
| Storage | Encrypted local volume (LUKS), content-addressed + SHA-256 | Uploads, consent video, models, outputs |
| Proxy | Caddy | TLS; *recommended* shared passphrase for external traffic (see §8) |
| Provenance | ffmpeg overlay + C2PA tooling + watermark | Corner "AI" mark, C2PA manifest, invisible watermark |

## 5. Data model (core)

- `avatars` — id, display_name, status (`active | deleted`), languages, created_at
- `consents` — id, avatar_id, received_at, channel (`browser_camera | file_upload`),
  consent_text_version, consent_text_sha256, challenge_phrase, challenge_issued_at,
  media_asset_id, media_sha256, verification_json (voice/face match scores, flags)
  (**append-only**)
- `assets` — id, avatar_id, kind (`photo | voice_audio | consent_media | output`), path, sha256,
  bytes, qc_json
- `voice_models` — id, avatar_id, base_model, license_spdx, path, mode (`zero_shot | finetuned`)
- `scripts` — id, text, language, created_at
- `jobs` — id, type, state, payload_json, parent_job_id, timing, error
- `renders` — id, avatar_id, script_id, output_asset_id, c2pa_id, requested_at, client_ref
- `model_registry` — name, version, license_spdx, weights_sha256, allowed_in_prod
- `audit_log` — append-only: ts, action, object, detail_json, client_ref
- Consent rows and consent media **survive avatar deletion** (D6); avatar row is marked `deleted`.

`client_ref` = proxy-level IP/session reference (personal data — mention in the DPIA).

## 6. Key workflows

### 6.1 Enrollment (remote, self-service)
1. Subject (or someone helping them) opens **Enroll**; picks the consent language.
2. System issues a one-time **challenge phrase** (timestamped) and shows the versioned consent
   text. The consent must state: purposes (lecture videos, announcements, paid courses), internal
   and external publication, **that anyone using the tool may generate videos with their face and
   voice**, that outputs are AI-labelled, and how deletion works.
3. Subject provides the consent as a **browser camera recording** (via a WebRTC component) or an
   **uploaded video/audio file**, speaking consent text + challenge phrase.
4. Subject uploads ~10 photos and up to 30 min of audio (multiple files, any common format).
5. `ingest/verify` job:
   - audio: normalise, denoise, VAD, Whisper transcripts (needed for fine-tuning), keep only
     speech matching the consent-voice speaker embedding (handles lecture recordings with other
     speakers);
   - photos: face detect, frontal/sharpness ranking, pick source portrait;
   - QC report shown to the user: usable audio minutes, chosen portrait, any problems;
   - identity/impersonation verification (voice + face match, challenge freshness) is **deferred
     to production** — demo accepts uploads at face value.
6. Avatar becomes `active` immediately after ingest QC passes.

### 6.2 Voice model
Zero-shot voice available immediately after ingest; `voice_train` job fine-tunes when ≥ the
minimum useful duration is available (threshold tuned in Phase 0; accept 10 s…30 min).
Per-language quality checked in Phase 0 and tuned over time (D11).

### 6.3 Render (anyone)
1. Pick an `active` avatar, pick language, type/paste script (optional Ollama drafting).
2. **Gate (service layer):** avatar `active` + valid consent row + not deleted. No other check.
3. `tts` → audio preview → `animate` (chunked with overlap) → `post`
   (corner "AI" mark, C2PA, watermark, mux) → download.
4. `renders` + audit entry. Chosen script text is stored (accountability).

### 6.4 Deletion
Avatar page → **"Delete avatar and data"** → confirmation dialog → removes uploads, photos,
voice models, derived embeddings, portrait and rendered outputs. **Keeps** the consent video
and consent record (hash, text version, timestamps) for later proof. No keys, no login, no
retention timers (D6).

## 7. Compute and deployment (single GB10)

- Docker + NVIDIA runtime; worker images from `nvcr.io/nvidia/pytorch:25.10-py3` (or later),
  flash-attention built from source if needed.
- One GPU job at a time (advisory lock); expect minutes of compute per minute of video.
- Compose services: `db`, `ui`, `proxy`, `worker-ingest`, `worker-voice`, `worker-animate`,
  `worker-post`.
- Backups: DB + volume. Models are re-derivable; consent media and DB are not.

## 8. Compliance and risk mapping

| Requirement | Response |
|---|---|
| Consent evidence | Recorded phrase + hash + text version + timestamps, append-only; **consent video kept after avatar deletion** |
| Remote-enrollment impersonation risk | **Deferred** (demo). Designed for later: challenge phrase, voice/face match, freshness check, review |
| AI disclosure (AI Act Art. 50) | Corner "AI" mark + C2PA + invisible watermark on every output; mark configurable |
| License hygiene | `model_registry` + gate: workers refuse non-approved models; SBOM per release |
| Third-party processing | Ollama for text only, flag-controlled, DPA assumed |
| Accountability | `audit_log`; scripts stored with renders |

**Known risks, deferred because this is a demo (revisit before any production/public use):**
1. Anonymous remote enrollment: anyone can enroll anyone; no identity verification. Mitigations
   designed but not built: challenge phrase, voice/face match, freshness check, reviewer.
2. Open-internet access with no login. Option when needed: shared passphrase at the proxy.
3. Anyone can delete any avatar's data (no key). Acceptable for a demo only.
4. Consent text wording (fi/en/sv) should be reviewed by university legal; it must cover
   "anyone may render my likeness".
5. GDPR consent in an employer–employee setting is contestable; small corner "AI" mark may
   not be judged clear for external content (invisible marking is the backstop).

## 9. Model stack

| Stage | Primary | Fallback / test |
|---|---|---|
| ASR / transcripts | Whisper (MIT; multilingual incl. fi, sv, en) | — |
| Speaker match / filter | SpeechBrain ECAPA-class (Apache-2.0) — **audit** | — |
| Denoise | DeepFilterNet-class (MIT/Apache) — **audit** | — |
| Voice | Chatterbox multilingual (MIT) — **verify fi/sv/en quality** | CosyVoice2 (Finnish unlikely) |
| Animation | EchoMimicV3 Flash (Apache-2.0) | Ditto; SadTalker smoke test |
| Face match | permissive embedding model — **select in Phase 0 (no InsightFace)** | — |
| Quality ceiling | daVinci-MagiHuman 15B | — |

## 10. Repository layout

```
AVATAR Hub/
  HANDOVER.md  ARCHITECTURE.md  docker-compose.yml
  libs/core/        # service layer: consent gate, jobs, delete, audit
  apps/ui/          # Streamlit demo
  workers/ingest/ voice/ animate/ post/
  models/registry/  # license manifests
  docs/             # consent texts (fi/en/sv), SBOM, DPIA input, runbooks
```

## 11. Build phases

| Phase | Deliverable | Exit criterion |
|---|---|---|
| 0 Feasibility | Free disk; NVIDIA container runtime verified; NGC image runs on sm_121; SadTalker + Chatterbox smoke test; **fi / sv / en voice test**; license/SBOM audit | Env works; languages acceptable or known gaps listed; no non-permissive dependency |
| 1 Pipeline CLI | photos + audio + consent file + text → video, incl. ingest/verify | One real subject end to end |
| 2 Core + queue | Postgres schema, service layer, queue, GPU lease, audit, delete | Consent gate and deletion tested |
| 3 Streamlit demo | Enroll / render / delete UI, fi-en-sv consent texts | Non-technical user completes all flows |
| 4 Hardening | Backups, proxy, runbooks, DPIA input pack | Reviewed by university IT/DPO |
| 5 Pilot | A few real users | Quality/time acceptable |

## 12. Open items

- Final consent texts (fi/en/sv) — wording to be reviewed by university legal.
- Minimum audio duration for fine-tune vs. zero-shot (Phase 0).
- Production phase (later): enrollment verification, access control/SSO, delete authorisation.
