# Decision Board (Founder / Product Owner)

This board is for **decisions that only you can make** (product, policy, pricing, risk posture). It complements `development/task_board.md` (implementation work) and `development/open-questions.md` (loose questions).

Last updated: 2025-12-28 02:11 UTC

Use the template under each item: pick an option, confirm the intent, and we’ll lock it into docs + code.

## Decide-now quick pick (top 4)

If you only have 5 minutes, decide these four first:

1. **D0 — Product focus: standalone app vs TTS backend**
2. **D1 — Accounts + “Login” scope**
3. **D2 — IP / content responsibility policy (import + share)**
4. **D3 — Import caching/dedupe scope (waste reduction)**

## Decide Now (blocks clean MVP)

### D0 — Product focus: standalone app vs TTS backend

- **Decision:** What is LangHero’s primary focus for the next 30 days?
- **Why:** It determines whether we prioritize learner UX features (scenarios/play/import/share) or treat this repo mainly as a stable service dependency (TTS + minimal demo UI).
- **Options:**
  - **A)** Standalone learning app first (MVP play loop + import/share + accounts as needed).
  - **B)** Service-first: stable `/api/tts` + minimal demo UI; Narrative Hero orchestrates product experience.
  - **C)** Both, but with an explicit priority order (A-first or B-first) and a defined “do-not-build-yet” list.
- **Default recommendation:** **C**, with a single-week “service hardening” sprint if Narrative Hero is depending on it daily.
- **Needs from you:** pick A/B/C, and define the “success metric” for the next 30 days (e.g., # of shared runs/week, or “Narrative Hero can ship TTS reliably”).

### D1 — Accounts + “Login” scope

- **Decision:** What does “login” actually mean for LangHero v1?
- **Why:** It determines where saves live, whether `/play/<id>` works cross-device, and how we do quotas/abuse control.
- **Options:**
  - **A)** No auth for now (local-only saves). Share only via published artifacts (`/share/<id>`).
  - **B)** Lightweight auth (magic link / email OTP). Saves in a DB, private runs resolve anywhere.
  - **C)** OAuth-only (Google/Apple). Faster onboarding, more infra/config.
- **Default recommendation:** **B** (magic link) + keep publish/share explicit.
- **Needs from you:** pick A/B/C, and “must-have” fields (email only? username? age gate?).

### D2 — IP / content responsibility policy (import + share)

- **Decision:** What is our official stance on imported content and what do we store/serve?
- **Why:** GDPR/HIPAA posture does **not** shield IP liability; we need explicit policy + UX.
- **Options (storage/serving):**
  - **A)** Store only derived Scenario[] for private runs; never store raw source text/transcripts long-term.
  - **B)** Store raw imports per user (needed for “recompile”), with retention + deletion controls.
  - **C)** Store raw imports only in demo/trial cache (short TTL), purge aggressively.
- **Options (sharing):**
  - **A)** Share only compiled Scenario[] (current behavior).
  - **B)** Allow sharing the original source link + excerpt (higher IP/privacy risk).
- **Default recommendation:** store **derived-only by default** + share **compiled-only** + require rights attestation for import/publish.
- **Needs from you:** choose storage option + sharing option, and whether we want a takedown workflow (email/contact + “report” link).

### D3 — Import caching/dedupe scope (waste reduction)

- **Decision:** When two imports are “the same”, who gets the cache hit?
- **Why:** Biggest cost-saver, also the easiest privacy foot-gun.
- **Options:**
  - **A)** Per-user only (safest).
  - **B)** Per-org/workspace boundary (when teams exist).
  - **C)** Global cache only for explicitly published artifacts/templates (opt-in).
- **Default recommendation:** **A now**, design for **B**, allow **C** only for published/opt-in templates later.
- **Needs from you:** pick A/B/C as the “official” rule for v1.

## Decide Soon (next 1–2 sprints)

### D4 — Free trial / demo packaging (cost posture)

- **Decision:** What is free vs trial vs paid, and what is “allowed” per tier?
- **Why:** This is how we keep marketing cheap and prevent cost abuse.
- **Choices to make (concrete knobs):**
  - Trial: max imports/day, max video minutes/day, max streaming minutes/day.
  - Demo: allow LLM import? allow real streaming? (currently gated by env flags).
  - Paid: what lifts (quotas, history, cloud saves, org sharing).

### D5 — Private run links vs published share links

- **Decision:** Should `/play/<id>` ever be shareable/private across accounts, or stay “my device only”?
- **Why:** Impacts account model + abuse surface.
- **Options:**
  - **A)** `/play/<id>` is always private to your account; sharing requires publish (`/share/<public_id>`).
  - **B)** Allow “private share links” for specific recipients (needs auth + permissions).
- **Default recommendation:** **A** for v1.

### D6 — Streaming transcript retention + privacy

- **Decision:** Do we store any streaming transcripts/audio server-side?
- **Why:** Major privacy surface + compliance story.
- **Options:**
  - **A)** Don’t persist transcripts/audio (only ephemeral in-memory during session).
  - **B)** Persist transcripts per user for history/analytics with retention controls.
  - **C)** Persist only aggregate metrics (no raw text).
- **Default recommendation:** **A or C** until accounts + consent UI exist.

## Needs More Clarity / Research (pick a direction)

### D7 — What does “confidence” mean in the UI?

- **Current behavior:** confidence is “match confidence” (heuristics/similarity), not ASR model confidence.
- **Decision:** should we treat confidence as (A) match confidence, (B) ASR confidence, or (C) combined “judge certainty”?
- **Why:** Users will interpret this as “how sure the system is” and blame it when wrong.

### D8 — URL ingestion scope (“any video url” + “any url with text”)

- **Decision:** What classes of URLs do we officially support in v1?
- **Examples:** plain HTML pages, YouTube, direct mp4/webm, PDFs, paywalled sites, social embeds.
- **Why:** Each category changes tooling, SSRF surface, and cost.
- **Default recommendation:** v1 = http/https + HTML text extraction + YouTube/direct video via ffmpeg/yt-dlp; add PDFs and “complex scraping” later.

## Done / Locked (already implemented)

- Global top nav + breadcrumbs via `frontend/src/routes/+layout.svelte`.
- Unified `/import` page (URL auto-detect + optional text) → `POST /api/import/auto`.
- Publish/share is explicit and shares compiled Scenario[] via `/share/<public_id>`.
