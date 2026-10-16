# Implementation tracker

Phase-wise progress against [06-phase-wise-implementation.md](playbook/06-phase-wise-implementation.md).
Update the checkboxes and the status table in the same PR that delivers the work.

**Status legend:** `Done` · `In progress` · `Not started` · `Deferred`

| Phase | Name | Status | Notes |
|------:|------|--------|-------|
| 0 | Skeleton | Done | Settings split, apps, Tailwind build, Alpine + Motion, `api.js`, health API |
| — | Data models (05) | Done | All models from [05-data-models.md](playbook/05-data-models.md) + admin + initial migrations |
| 1 | Auth & profiles (Google via Firebase) | Done | Design in [07](playbook/07-authentication-firebase.md); `accounts.User` + `UserProfile` already in place |
| 2 | Catalogue (dummy data) | Done | `seed_demo`, original IELTS-style content, admin-configurable timings |
| 3 | Take mock (dummy) | Done | Player, server-side section timers, autosave, speaking upload, listening play rules |
| 4 | Scoring stubs | Done | Deterministic + stand-in AI scoring, results, answer review, re-score |
| UX | Premium redesign | Done | Design system, public/student/org app shells, rule-based "Your next step" ([design.md](design.md)) |
| 5 | Analytics | In progress | Skill map, trend sparkline, results history on the student dashboard; Chart.js + filters still to do |
| 6 | Institute admin | In progress | Org overview, students, student detail, read-only access/invites; invites managed in Django admin |
| 7 | Payments later (+ polish) | Not started | `Plan*` / `Entitlement` stubs ready |
| — | Content pipeline (08) | Done | `content` app: sources → patterns → jobs → drafts → publish; Piper TTS, matplotlib charts, Gemini/R2 adapters, dedup + practice/mock pools + exposure ([08](playbook/08-content-pipeline.md)). Admin → student flow browser-tested on mock providers (PR #8). Still to verify with real keys: live LLM agents, Gemini images, embeddings, R2; PDF upload |

---

## Project decisions (deviations from the playbook)

| Topic | Playbook | Repo | Why |
|-------|----------|------|-----|
| Project package | `portal` | `config` | Existing project layout; no functional difference |
| Landing app | `core:landing` | `pages:home` (`pages` app holds all public pages) | Public pages kept in one app as originally requested |
| DB | PostgreSQL | SQLite (`db.sqlite3`) for now | Local-first; Postgres in prod settings later |
| Tailwind | CDN for Phase 0–1 | Standalone CLI via `pytailwindcss` (`manage.py tailwind`), built `static/css/app.css` committed | No Node needed; production-grade CSS from day one |
| Alpine / Motion | CDN | Vendored in `static/vendor/` (Alpine 3.17.4, Motion 14.1.0) | Own infra, no runtime CDN dependency |
| Templates | `templates/<app>/…` | Same — all templates live in root `templates/` | Tailwind scans one directory |
| User model | `User` + `UserProfile` | `accounts.User(AbstractUser)` + `UserProfile` (auto-created by signal) | Swapping user model later is painful |
| Tags | `ArrayField` | `catalog.Tag` M2M | SQLite has no `ArrayField` |
| `Exam.slug` | not in 05 | added | Screens use `/exams/<slug>/` |
| Auth | Email/password (django-allauth or built-in) | Google sign-in via Firebase → Django session; `/admin/` keeps password login | Product decision; see [07](playbook/07-authentication-firebase.md) |
| Exams | Seeded in Phase 2 `seed_demo` | 4 `Exam` rows seeded by data migration `catalog/0002_seed_exams` | Onboarding needs an exam to pick |
| Demo data | JSON fixtures | Python definitions in `catalog/demo.py` (`update_or_create`) | Idempotent re-runs; easy to generate 3 questions × every type |
| Catalogue access | Public browse | Login required for everything | User decision |
| Frontend API | — | `static/js/api.js` (`window.api`) | Single place for CSRF, auth headers, errors |
| Shared stimuli | Passage copied into each stem | `catalog.Stimulus` (passage / script / image, one audio per stimulus); stems stay self-contained | Dedup + one recording per listening part |
| Practice vs mock | Same pool | `Question.pool` + one mock pack per question (`uniq_mockpackitem_question`) | No repeats between practice and mocks |

---

## Phase 0 — Skeleton

- [x] Django project + apps: `core`, `accounts`, `tenancy`, `catalog`, `attempts`, `scoring`, `analytics`, `plans`, `institute` (+ `pages`)
- [x] `base.html` + Tailwind
- [x] Motion One + Alpine.js included in base
- [ ] Docker Compose (optional): web + postgres + redis
- [x] `manage.py check` green
- [x] Disclaimer component (`templates/components/disclaimer.html`)
- [x] Health check `GET /api/health/`
- [x] Central JS API client `static/js/api.js`

**Acceptance**

- [x] `GET /` returns landing with exam placeholder cards
- [x] Static Tailwind classes render
- [x] Alpine + Motion smoke (toggle + fade-in) on landing
- [x] Settings split base/dev/prod stubs
- [x] README points to this playbook path

## Data models (from 05)

- [x] `tenancy`: `Tenant`, `Membership`
- [x] `accounts`: `User`, `UserProfile`
- [x] `catalog`: `Exam`, `QuestionType`, `Tag`, `Asset`, `Question`, `MockPack`, `MockPackItem`, `StudyAid`
- [x] `attempts`: `Attempt`, `AttemptItem`, `FeedbackNote`
- [x] `scoring`: `ScoreBreakdown`, `ScoringConfig`
- [x] `plans`: `Plan`, `PlanDay`, `PlanEnrolment`, `PlanDayProgress`, `Entitlement`
- [x] All registered in Django admin
- [x] Initial migrations committed
- [x] Recommended indexes / unique constraints

## Phase 1 — Auth & profiles

- [x] Firebase project + Google provider enabled; web config + authorized domains
- [x] `firebase-admin` dep, `FIREBASE_*` settings, COOP `same-origin-allow-popups`
- [x] `User.firebase_uid`, `UserProfile.avatar_url` + migration
- [x] Login page (Continue with Google) + `static/js/firebase-login.js`; register → login redirect
- [x] `POST /api/auth/firebase/` exchange, `/api/auth/logout/`, `/api/auth/me/`
- [x] Role router (`/admin/`, `/org/`, `/onboarding/`, `/dashboard/`)
- [x] Onboarding (primary exam, target)
- [x] Three roles only (student, org, super admin = Django admin); mixins `StudentRequired`, `OrgRequired`
- [x] Org access emails (`AccessInvite`) in Django admin → membership on sign-in; independent students default
- [x] Session `auth_context` re-validated from DB every request; no browser token persistence; no-store on auth pages
- [x] Student + org dashboards
- [x] `api.js` auth wiring (`api.onUnauthorized` → login redirect)

**Acceptance**

- [x] First Google sign-in creates user → onboarding → dashboard (unit-tested with mocked token; real-popup E2E pending a test Google account)
- [x] Returning user → dashboard; invited/existing email linked, not duplicated
- [x] Invalid / non-Google / stale token → 401, no session
- [x] Logout clears session
- [x] Superuser → `/admin/`; org email → `/org/`
- [x] Unauthorized access to `/org/` → 403

## Phase 2 — Catalogue (dummy data)

- [x] Catalog models
- [x] `seed_demo` management command (idempotent; data defined in `catalog/demo.py`)
- [x] Catalogue screens (exam list/detail, qtype list, mock list/detail)
- [x] Prediction filter chip
- [x] Locked state UI for non-entitled packs (`Entitlement` keys `pack:<id>` / `unlimited`, user or org)
- [x] Login required for every catalogue page (user decision)

**Acceptance**

- [x] ≥1 free mock pack per PTE Academic & IELTS Academic
- [x] ≥3 questions for each major engine family used in Phase 3
- [x] Filters update list without 500s
- [x] No copyrighted stems — placeholders only
- [x] Answer keys never appear in HTML source of catalogue pages
- [x] IELTS exam format doc (`docs/exams/ielts.md`): sections, question categories, official timings
- [x] Real-exam section timings configurable in admin (`SectionTiming` per exam, `MockPackSection` per-mock override, `QuestionType.default_time_sec` for practice)
- [x] Original IELTS-style content: Academic + General Training Mock Test 1 (40 listening / 40 reading / 2 writing / 3 speaking) + practice sets for every category
- [x] Student dashboard lists mock tests (with section timings) and practice by section

## Phase 3 — Take mock with dummy responses

- [x] `Attempt`, `AttemptItem` models
- [x] Snapshotting pack items into `AttemptItem` on start
- [x] Player shell + item partials (MCQ, FIB text/dropdown, reorder, writing, speaking, listening)
- [x] Timers with server deadline
- [x] Autosave + audio upload endpoints (via `api.js`)
- [x] Mic check page
- [x] Submit → `SUBMITTED`
- [x] Section timers: one server deadline per section (`SectionTiming` / `MockPackSection`), auto-advance on expiry, no return to closed sections; late saves (> deadline + 5 s) rejected
- [x] Listening audio via `Question.audio`; `manage.py listening_audio` makes espeak-ng demo audio (replace with real recordings)
- [x] Dashboard: Continue (in-progress) + Recent attempts

**Acceptance**

- [x] Full mock completable with dummy pack end-to-end
- [x] Refresh mid-attempt restores responses + timer within 2s skew
- [x] Speaking upload stores playable file
- [x] Listening play_count increments; seek hidden when configured
- [x] Double finalize is idempotent
- [x] Section-wise & question-wise modes create attempts with correct `mode`

## Phase 4 — Scoring stubs

- [x] `ScoreBreakdown`, `ScoringConfig` models
- [x] `ScoringConfig` seeded per exam
- [x] `DeterministicScorer` (selection/FIB/reorder/WFD/HIW/TFNG/matching)
- [x] `DummyAIScorer` (speaking/writing)
- [x] `score_attempt` task (sync fallback for dev) — runs inline on submit (`SCORING_INLINE`); `manage.py score_attempts` is the worker/retry until Celery/Redis lands
- [x] Results + review item pages with disclaimer
- [x] Re-score admin action (optional)

**Acceptance**

- [x] MCQ/FIB/reorder scores match documented formulas on fixture keys
- [x] WFD partial credit returns mid scores for partial typing
- [x] Writing/speaking leave `pending` then resolve via dummy traits
- [x] PTE attempt shows communicative sections + enabling JSON
- [x] IELTS attempt shows band-style overall + writing/speaking traits
- [x] UI never says “official”
- [x] Failed worker sets Attempt FAILED + retry works

## UX — Premium redesign

- [x] Design system: local fonts, aurora/ink tokens, Tailwind v4 `@utility` components, reduced-motion reveal
- [x] Layouts: `base.html` (public), `app/base.html` (sidebar + phone tabs via `app_nav`), `app/focus.html` (player)
- [x] Public: home, about, contact, for institutes, login
- [x] Student: dashboard with rule-based "Your next step", catalogue, mocks, unlock, player, results, review, results history
- [x] Org: overview, students, student detail, access & invites
- [ ] Replace rule-based `next_step()` with the AI question picker

## Phase 5 — Analytics

- [x] Analytics queries (accuracy by Q-type, section averages, overall trend) — `analytics/insights.py`
- [x] Dashboard widgets wired to real data (skill map, trend, stats, results history)
- [ ] Chart.js charts (inline SVG sparkline for now)
- [x] Empty states

**Acceptance**

- [ ] After ≥3 scored attempts, charts render non-zero series
- [ ] Filter by exam works
- [x] No cross-user data leakage (two students) — results history test

## Phase 6 — Institute admin

- [x] `Tenant`, `Membership` models
- [ ] Tenant-resolve middleware (subdomain or session)
- [x] Institute console screens (overview, students + search, student detail, access & invites)
- [ ] Invite create/accept
- [x] Branding colour → CSS vars (`--brand`, `--brand-fg`); logo still to do
- [ ] Assign entitlement / pack access
- [ ] Tutor (optional): view-only attempt list + `FeedbackNote`

**Acceptance**

- [x] Inst admin sees only own students (student detail 404s outside the org)
- [ ] Invited student joins tenant and sees branding
- [ ] `seat_limit` enforced when set
- [ ] Super Admin can switch/list tenants
- [ ] Tenant A student cannot open Tenant B attempt URLs (404/403)

## Phase 7 — Payments later (+ polish)

- [x] `Plan`, `PlanDay`, `PlanEnrolment`, `PlanDayProgress`, `Entitlement` models
- [ ] Plan catalogue + day-index progress UI
- [ ] Study aids pages
- [ ] Stripe or Razorpay behind feature flag
- [ ] Entitlement grants on successful payment
- [ ] Rate limits, Sentry, backup docs
- [ ] Accessibility pass on player
- [ ] PTE Core pack + ScoringConfig profile
- [ ] IELTS General reading/writing Task 1 variants

**Acceptance**

- [ ] Paid plan grant flips entitlement without manual DB edit
- [ ] Day plan checklist auto-completes when tasks satisfied
- [ ] Webhook idempotency covered by tests
- [ ] Load smoke: 50 concurrent autosaves no data loss
