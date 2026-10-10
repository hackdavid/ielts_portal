# Implementation tracker

Phase-wise progress against [06-phase-wise-implementation.md](playbook/06-phase-wise-implementation.md).
Update the checkboxes and the status table in the same PR that delivers the work.

**Status legend:** `Done` · `In progress` · `Not started` · `Deferred`

| Phase | Name | Status | Notes |
|------:|------|--------|-------|
| 0 | Skeleton | Done | Settings split, apps, Tailwind build, Alpine + Motion, `api.js`, health API |
| — | Data models (05) | Done | All models from [05-data-models.md](playbook/05-data-models.md) + admin + initial migrations |
| 1 | Auth & profiles (Google via Firebase) | Done | Design in [07](playbook/07-authentication-firebase.md); `accounts.User` + `UserProfile` already in place |
| 2 | Catalogue (dummy data) | Not started | Catalog models ready; needs `seed_demo` + screens |
| 3 | Take mock (dummy) | Not started | `Attempt` / `AttemptItem` models ready |
| 4 | Scoring stubs | Not started | `ScoreBreakdown` / `ScoringConfig` models ready |
| 5 | Analytics | Not started | |
| 6 | Institute admin | Not started | `Tenant` / `Membership` models ready |
| 7 | Payments later (+ polish) | Not started | `Plan*` / `Entitlement` stubs ready |

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
| Frontend API | — | `static/js/api.js` (`window.api`) | Single place for CSRF, auth headers, errors |

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
- [x] Role router (`/platform/`, `/org/`, `/onboarding/`, `/dashboard/` stubs)
- [x] Onboarding (primary exam, target)
- [x] Permission mixins `StudentRequired`, `InstituteAdminRequired`, `SuperAdminRequired`
- [x] `api.js` auth wiring (`api.onUnauthorized` → login redirect)

**Acceptance**

- [x] First Google sign-in creates user → onboarding → dashboard (unit-tested with mocked token; real-popup E2E pending a test Google account)
- [x] Returning user → dashboard; invited/existing email linked, not duplicated
- [x] Invalid / non-Google / stale token → 401, no session
- [x] Logout clears session
- [x] Superuser `role_primary=super_admin` reaches `/platform/` (stub)
- [x] Unauthorized access to `/org/` → 403

## Phase 2 — Catalogue (dummy data)

- [x] Catalog models
- [ ] `seed_demo` management command + JSON fixtures (idempotent)
- [ ] Catalogue screens (exam list/detail, qtype list, mock list/detail)
- [ ] Prediction filter chip
- [ ] Locked state UI for non-entitled packs

**Acceptance**

- [ ] ≥1 free mock pack per PTE Academic & IELTS Academic
- [ ] ≥3 questions for each major engine family used in Phase 3
- [ ] Filters update list without 500s
- [ ] No copyrighted stems — placeholders only
- [ ] Answer keys never appear in HTML source of catalogue pages

## Phase 3 — Take mock with dummy responses

- [x] `Attempt`, `AttemptItem` models
- [ ] Snapshotting pack items into `AttemptItem` on start
- [ ] Player shell + item partials (MCQ, FIB text/dropdown, reorder, writing, speaking, listening)
- [ ] Timers with server deadline
- [ ] Autosave + audio upload endpoints (via `api.js`)
- [ ] Mic check page
- [ ] Submit → `SUBMITTED`

**Acceptance**

- [ ] Full mock completable with dummy pack end-to-end
- [ ] Refresh mid-attempt restores responses + timer within 2s skew
- [ ] Speaking upload stores playable file
- [ ] Listening play_count increments; seek hidden when configured
- [ ] Double finalize is idempotent
- [ ] Section-wise & question-wise modes create attempts with correct `mode`

## Phase 4 — Scoring stubs

- [x] `ScoreBreakdown`, `ScoringConfig` models
- [ ] `ScoringConfig` seeded per exam
- [ ] `DeterministicScorer` (selection/FIB/reorder/WFD/HIW/TFNG/matching)
- [ ] `DummyAIScorer` (speaking/writing)
- [ ] `score_attempt` task (sync fallback for dev)
- [ ] Results + review item pages with disclaimer
- [ ] Re-score admin action (optional)

**Acceptance**

- [ ] MCQ/FIB/reorder scores match documented formulas on fixture keys
- [ ] WFD partial credit returns mid scores for partial typing
- [ ] Writing/speaking leave `pending` then resolve via dummy traits
- [ ] PTE attempt shows communicative sections + enabling JSON
- [ ] IELTS attempt shows band-style overall + writing/speaking traits
- [ ] UI never says “official”
- [ ] Failed worker sets Attempt FAILED + retry works

## Phase 5 — Analytics

- [ ] Analytics queries (attempts over time, accuracy by Q-type, section averages)
- [ ] Dashboard widgets wired to real data
- [ ] Chart.js charts
- [ ] Empty states

**Acceptance**

- [ ] After ≥3 scored attempts, charts render non-zero series
- [ ] Filter by exam works
- [ ] No cross-user data leakage (two students)

## Phase 6 — Institute admin

- [x] `Tenant`, `Membership` models
- [ ] Tenant-resolve middleware (subdomain or session)
- [ ] Institute console screens
- [ ] Invite create/accept
- [ ] Branding colour/logo → CSS vars (`--brand`, `--brand-fg`)
- [ ] Assign entitlement / pack access
- [ ] Tutor (optional): view-only attempt list + `FeedbackNote`

**Acceptance**

- [ ] Inst admin sees only own students
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
