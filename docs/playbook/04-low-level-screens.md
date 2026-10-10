# 04 — Low-Level Screens

Page/screen catalogue for Django + Templates + Tailwind.  
Conventions: URL name `app:view`, template under `templates/`, Motion One / Alpine for motion (no Framer Motion by default).

---

## Global layout

| Item | Path / notes |
|------|----------------|
| Base | `templates/base.html` |
| App shell | Nav (exam switcher, analytics, plans) + main + footer disclaimer |
| Tailwind | Utility-first; CSS vars `--brand`, `--brand-fg` from tenant |
| Motion | `motion` package: fade/slide on section enter; Alpine `x-show`/`x-transition` for modals |
| Toasts | Alpine store + partial `components/toast.html` |

**Disclaimer strip (every scored page):**  
`Practice scores are approximations — not official Pearson/IELTS results.`

---

## Screen index

| # | Screen | URL | View name |
|---|--------|-----|-----------|
| 1 | Landing | `/` | `core:landing` |
| 2 | Login | `/accounts/login/` | `accounts:login` |
| 3 | Register | `/accounts/register/` | `accounts:register` |
| 4 | Onboarding | `/onboarding/` | `accounts:onboarding` |
| 5 | Student dashboard | `/dashboard/` | `analytics:dashboard` |
| 6 | Catalogue home | `/exams/` | `catalog:exam_list` |
| 7 | Exam detail | `/exams/<slug>/` | `catalog:exam_detail` |
| 8 | Q-type list | `/exams/<slug>/types/<code>/` | `catalog:qtype_list` |
| 9 | Mock pack list | `/exams/<slug>/mocks/` | `catalog:mock_list` |
| 10 | Pack detail / start | `/mocks/<id>/` | `catalog:mock_detail` |
| 11 | Mic check | `/attempts/<id>/mic-check/` | `attempts:mic_check` |
| 12 | Attempt player | `/attempts/<id>/play/` | `attempts:play` |
| 13 | Item partial | `/attempts/<id>/items/<n>/` | `attempts:item` |
| 14 | Audio upload API | `/api/attempts/<id>/items/<n>/audio/` | `attempts:upload_audio` |
| 15 | Autosave API | `/api/attempts/<id>/items/<n>/save/` | `attempts:autosave` |
| 16 | Submit attempt | `/attempts/<id>/submit/` | `attempts:submit` |
| 17 | Scoring wait | `/attempts/<id>/scoring/` | `attempts:scoring` |
| 18 | Results | `/attempts/<id>/results/` | `attempts:results` |
| 19 | Item review | `/attempts/<id>/review/<n>/` | `attempts:review_item` |
| 20 | Analytics | `/analytics/` | `analytics:student` |
| 21 | Plans list | `/plans/` | `plans:list` |
| 22 | Plan detail | `/plans/<id>/` | `plans:detail` |
| 23 | Study aids | `/aids/` | `catalog:aids` |
| 24 | Profile | `/profile/` | `accounts:profile` |
| 25 | Institute home | `/org/` | `institute:home` |
| 26 | Institute students | `/org/students/` | `institute:students` |
| 27 | Invite | `/org/invites/` | `institute:invites` |
| 28 | Branding | `/org/branding/` | `institute:branding` |
| 29 | Platform admin | `/platform/` | `platform:home` |
| 30 | Entitlement wall | `/locked/` | `plans:locked` |

---

## 1. Landing — `core:landing`

- **Template:** `templates/core/landing.html`  
- **UI sections:** Hero, exam cards (PTE / IELTS), feature bullets, CTA Login/Register, footer.  
- **Tailwind:** `max-w-6xl mx-auto`; hero `grid md:grid-cols-2 gap-8`; cards `rounded-2xl shadow-sm border`.  
- **Motion:** Hero title fade-up via Motion One on load.  
- **Forms/APIs:** none  

---

## 2–3. Login / Register

- **Templates:** `templates/accounts/login.html`, `register.html`  
- **UI:** Centre card form; OAuth placeholders hidden.  
- **Tailwind:** `min-h-screen flex items-center`; form `space-y-4`.  
- **Motion:** Card scale-in.  
- **Forms:** Django auth forms POST.  

---

## 4. Onboarding

- **Template:** `templates/accounts/onboarding.html`  
- **UI:** Stepper — primary exam, target score/band, optional institute code.  
- **Alpine:** `x-data="{step:1}"`  
- **Form:** POST `UserProfile` fields.  

---

## 5. Student dashboard

- **Template:** `templates/analytics/dashboard.html`  
- **UI sections:**  
  1. Greeting + target  
  2. Continue attempt card  
  3. Free mock CTA  
  4. Weak Q-types (from analytics)  
  5. Day plan today checklist (stub)  
- **Tailwind:** Bento grid `grid md:grid-cols-3 gap-4`.  
- **Motion:** Stagger cards 40ms.  
- **APIs:** none (SSR).  

---

## 6–7. Catalogue / Exam detail

- **Templates:** `catalog/exam_list.html`, `exam_detail.html`  
- **UI:** Tabs — Mocks | Practice by type | Sections. Filter chips: Prediction, Difficulty, Free.  
- **Alpine:** filter query sync to URL `?prediction=1`.  
- **Tailwind:** Chip `px-3 py-1 rounded-full text-sm`; active `bg-brand text-white`.  

---

## 8. Q-type list

- **Template:** `catalog/qtype_list.html`  
- **UI:** Table/list of questions (title stub, difficulty, practised tick); Start practice button.  
- **Edge:** Locked rows show lock icon → `/locked/`.  

---

## 9–10. Mock list / detail

- **Templates:** `catalog/mock_list.html`, `mock_detail.html`  
- **UI:** Duration, sections breakdown, free badge, Start / Retake.  
- **Form:** POST start → creates Attempt → redirect mic-check or play.  

---

## 11. Mic check

- **Template:** `attempts/mic_check.html`  
- **UI:** Level meter canvas; “Looks good” CTA; skip for non-speaking packs.  
- **Alpine + MediaRecorder:** getUserMedia; motion pulse on meter.  
- **No upload** until real items.  

---

## 12–13. Attempt player + item

- **Templates:** `attempts/play.html` (shell), `attempts/items/*.html` partials by engine  
- **Shell UI sections:**  
  - Top bar: exam logo, section name, item index `3/12`, timer  
  - Instruction collapse  
  - Main interaction region  
  - Footer: Back (if allowed), Next, Flag (optional)  
- **Tailwind:** `flex flex-col h-[100dvh]`; main `flex-1 overflow-auto p-4`.  
- **Motion:** Item swap — Alpine transition opacity; avoid layout thrash.  
- **CD-IELTS Reading:** `grid lg:grid-cols-2` passage | questions.  
- **PTE:** Single column denser chrome.  

### Item partials (examples)

| Engine | Template |
|--------|----------|
| MCQ | `attempts/items/mcq.html` |
| FIB dropdown | `attempts/items/fib_dropdown.html` |
| FIB drag | `attempts/items/fib_drag.html` |
| FIB text | `attempts/items/fib_text.html` |
| Reorder | `attempts/items/reorder.html` |
| HIW | `attempts/items/hiw.html` |
| Writing | `attempts/items/writing.html` |
| Speaking | `attempts/items/speaking.html` |
| Listening media | includes `components/audio_player.html` |
| IELTS TFNG | `attempts/items/tfng.html` |
| Matching | `attempts/items/matching.html` |
| Map label | `attempts/items/map_label.html` |

---

## 14. Audio upload API

- **Method:** POST multipart `audio`  
- **Response JSON:** `{ok, asset_id, url}`  
- **Errors:** 400 empty/too long; 415 codec  
- **UI caller:** Speaking partial Alpine `submitAudio()`  

---

## 15. Autosave API

- **Method:** PATCH/POST JSON body normalised per engine  
- **Response:** `{ok, saved_at}`  
- **Debounce:** 800ms client-side  

---

## 16. Submit

- **Template:** confirm modal in `play.html` or `attempts/submit_confirm.html`  
- **POST:** finalize → redirect scoring  
- **Motion:** Modal `x-transition`  

---

## 17. Scoring wait

- **Template:** `attempts/scoring.html`  
- **UI:** Spinner + “Scoring your responses…”; poll every 2s (`Alpine` fetch or HTMX).  
- **Redirect** when `status==SCORED` else show retry if FAILED.  

---

## 18. Results

- **Template:** `attempts/results.html`  
- **UI sections:**  
  1. Overall score / band hero  
  2. Section bars  
  3. PTE enabling radar (canvas/SVG) or IELTS trait cards  
  4. Item results table  
  5. Retake / Review CTAs  
- **Tailwind:** Hero `text-5xl font-bold`; bars `h-2 rounded bg-slate-200`.  
- **Motion:** Count-up overall number (Motion One / small JS).  
- **Disclaimer** prominent.  

---

## 19. Item review

- **Template:** `attempts/review_item.html`  
- **UI:** Your answer vs correct (if reveal allowed); AI feedback bullets; audio playback of your recording.  
- **Config:** `reveal_answers` false for full mock until scored — then true for practice.  

---

## 20. Analytics

- **Template:** `analytics/student.html`  
- **UI:** Date range; line chart overall; bar by Q-type accuracy; time spent.  
- **Charts:** Chart.js via CDN (no React).  
- **Motion:** Chart fade-in.  

---

## 21–22. Plans

- **Templates:** `plans/list.html`, `detail.html`  
- **UI:** Day list checklist; stub lock icons for paid.  
- **Form:** Enrol POST.  

---

## 23. Study aids

- **Template:** `catalog/aids.html` + `aid_detail.html`  
- **UI:** Cards for essay templates, tip sheets (static HTML).  

---

## 24. Profile

- **Template:** `accounts/profile.html`  
- **Form:** name, target, exam preference, password change.  

---

## 25–28. Institute console

- **Templates:** `institute/*.html`  
- **UI:** Sidebar layout `grid md:grid-cols-[240px_1fr]`.  
- **Students table:** search, status, last active, assign pack modal.  
- **Branding:** logo upload, colour picker → CSS vars.  
- **Motion:** Sidebar stable; main partial swap optional HTMX.  

---

## 29. Platform admin

- **Template:** `platform/home.html` + heavy use of Django admin for CRUD.  
- **UI:** Tenant list, scoring config versions, failed jobs queue.  

---

## 30. Entitlement wall

- **Template:** `plans/locked.html`  
- **UI:** Explain gate; CTA contact institute / see plans stub.  

---

## Speaking item UI detail

```text
[Prep timer]
[Waveform / timer while recording]
[Stop] [Re-record if allowed]
[Upload progress]
```

Alpine states: `idle → preparing → recording → uploading → ready`.

---

## Listening player component

- **Template:** `components/audio_player.html`  
- **Props:** `src`, `allow_seek`, `max_plays`  
- **Behaviour:** hide scrubber if `!allow_seek`; increment play_count via autosave meta.  

---

## Reorder / drag-drop motion

- Prefer **SortableJS** (CDN) + Tailwind ghost classes.  
- Optional future React island + Framer Motion **only** if SortableJS insufficient — default **no React**.  

---

## Error pages

| Code | Template |
|------|----------|
| 403 | `403.html` |
| 404 | `404.html` |
| 500 | `500.html` |

Keep brand shell + link home.

---

## Permission matrix (view layer)

| Screen | Student | Tutor | Inst Admin | Super |
|--------|:-------:|:-----:|:----------:|:-----:|
| Dashboard | ✓ | ✓ | — | ✓ |
| Play own attempt | ✓ | — | — | ✓ |
| Review student attempt | — | ✓ | ✓ | ✓ |
| Org console | — | limited | ✓ | ✓ |
| Platform | — | — | — | ✓ |
