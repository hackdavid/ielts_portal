# 08 — Content pipeline (agentic question generation)

Generates original IELTS / PTE questions into the existing bank, reviewed in
Django admin before anything goes live. App: `content`.

## Flow

1. **Source** (`SourceDocument`): upload PDF / DOCX / TXT or paste text. Saving
   extracts pages (`SourcePage`, with MinHash for the copy guard). Same file twice
   is rejected by SHA-256.
2. **Analyse** (admin action → analyst agent): proposes `PatternProfile`s mapped
   to our `QuestionType` codes. Approve the useful ones.
3. **Job** (`GenerationJob`): pick a question type, count, difficulty mix, topic
   hints, target pool (practice / mock), optional approved patterns. Saving starts
   it (background thread when `CONTENT_JOBS_INLINE=1`, else
   `manage.py run_content_jobs`).
4. Per job: **planner** → `QuestionBrief`s (avoids topics already in the bank) →
   per brief **writer** (typed contract, validate-and-retry ×3) → **reviewer**
   (blind solve, no key) → **dedup** → **media** → draft `READY`.
5. **Review** (`DraftQuestion` change page): student-view preview, audio / image,
   key, transcript, validation, reviewer agreement, similar questions. Actions:
   publish, publish anyway, reject, revise (re-write with feedback), re-generate
   media.
6. **Publish** (one transaction): `Stimulus` + `Question(origin=generated,
   pool=practice|mock)` + assets + embedding moved to the question.

Every stage writes a `JobStep` (input, output, provider, tokens, latency, error).

## Contracts (`content/contracts.py`)

One Pydantic model per engine family (`items`, `mcq`, `inline`, `reorder`,
`hiw`, `dictation`, `writing`, `speaking`). The same model is the writer's
structured output, the validator input and `QuestionType.content_schema`.
`POLICIES` holds per-type media + length rules (`QuestionType.media_policy`
overrides). `build()` produces the existing stem / answer_key / scorer_meta
shapes, so player and scorers are unchanged.

## Dedup and no-repeat

- Exact normalised hash per type → MinHash (3-word shingles; char 5-grams for
  short items) → embedding cosine. Thresholds in `CONTENT_DEDUP`.
- Copy guard: MinHash and 12-word runs against uploaded source pages.
- `manage.py index_bank` backfills hashes / embeddings for existing questions.
- `Question.pool`: practice questions never appear in mocks, mock ones not in
  practice lists; `both` = legacy seed rows. A question is in at most one mock pack
  (DB constraint).
- `attempts.QuestionExposure`: written for every started attempt; practice lists
  show unseen questions first, then least recently seen.

## Media

| Need | Provider | Notes |
|------|----------|-------|
| Listening / PTE audio | **Piper** `en_GB-vctk-medium` (CPU, ~77 MB, 109 speakers) | One VCTK speaker per dialogue role; MP3 via ffmpeg. Fallback espeak-ng. `manage.py content_tts_setup` downloads the voice to `CONTENT_TTS_DIR`. |
| Charts (DI, Task 1) | matplotlib | Exact values; data also stored as `data_table`. |
| Scenes / diagrams | Gemini image (`GEMINI_IMAGE_MODEL`) | Mock placeholder without key. |
| Maps | Gemini base image + Pillow letters | Letters drawn by code so they are exact. |

Files are `catalog.Asset` rows (SHA-256 reuse). With `R2_BUCKET_NAME` set the
default storage is Cloudflare R2 (private objects, presigned URLs,
`R2_ROOT_PREFIX`); `MEDIA_STORAGE=local` forces local disk. Tests always use
local disk.

## Providers and env vars

| Env var | Purpose | Without it |
|---------|---------|------------|
| `CONTENT_LLM_API_KEY` (or `OPENAI_API_KEY`) | OpenAI Agents SDK agents | Labelled **mock** writer/reviewer (`is_mock`, `[MOCK]` titles) |
| `CONTENT_LLM_BASE_URL` | OpenAI-compatible endpoint | api.openai.com |
| `CONTENT_LLM_MODEL` / `CONTENT_LLM_WRITER_MODEL` | Models (default `gpt-4o-mini`) | — |
| `CONTENT_EMBEDDING_MODEL` | Embeddings (default `text-embedding-3-small`) | Hashing mock vectors |
| `GEMINI_API_KEY`, `GEMINI_IMAGE_MODEL` | Images | Mock placeholder image |
| `R2_BUCKET_NAME`, `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ROOT_PREFIX`, `R2_URL_EXPIRE_SEC` | Media storage | Local `MEDIA_ROOT` |
| `CONTENT_TTS_DIR`, `CONTENT_TTS_VOICE`, `CONTENT_TTS_ENABLED` | Piper voice | espeak-ng |
| `CONTENT_JOBS_INLINE` | `1` = run jobs in a thread from admin | Use the worker command |
| `CONTENT_ALLOW_MOCK_PUBLISH` | Allow publishing mock drafts when `DEBUG` is off | Blocked |
