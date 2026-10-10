# IELTS exam format: sections, question categories, timing

Source: official public format pages on ielts.org (Academic & General Training "test format" pages, checked 2026-10). Formats and timings are facts; **all question content in this repo is original** (no Cambridge / IDP / British Council material).

| | Listening | Reading | Writing | Speaking |
|---|---|---|---|---|
| Time | ~30 min (+10 min transfer on paper, 2 min check on computer) | 60 min (incl. transfer) | 60 min | 11–14 min |
| Structure | 4 parts × 10 questions = 40 | 3 passages/sections, 40 questions | Task 1 + Task 2 | Part 1, 2, 3 |
| Academic vs General | Same | Different texts (Ac: 3 long academic texts, 2150–2750 words; GT: S1 2–3 short texts, S2 two work texts, S3 one long text, 2150–2375 words) | Task 1 differs (Ac: describe graph/table/chart/diagram; GT: letter) | Same |

Test order: Listening → Reading → Writing (same day, no breaks); Speaking can be the same day or up to a week before/after.

## Listening (~30 min, 40 questions)

| Part | Context | Questions |
|---|---|---|
| 1 | Conversation, everyday social context (e.g. booking) | 1–10 |
| 2 | Monologue, everyday context (e.g. local facilities) | 11–20 |
| 3 | Conversation, education/training (up to 4 speakers) | 21–30 |
| 4 | Monologue on an academic subject (lecture) | 31–40 |

Categories (`QuestionType.code` → engine): `L_MCQ` multiple choice (one / more answers) · `L_MATCH` matching · `L_MAP` plan/map/diagram labelling · `L_FORM` form/note/table/flow-chart completion · `L_SENT` sentence completion · `L_SHORT` short-answer questions. Word limits such as "NO MORE THAN TWO WORDS AND/OR A NUMBER" are stored per question set (`stem.word_limit`). Recording is heard once.

## Reading (60 min, 40 questions)

Categories: `R_MCQ` multiple choice · `R_TFNG` identifying information (True/False/Not Given) · `R_YNNG` writer's views (Yes/No/Not Given; mainly Academic) · `R_MATCH_INFO` matching information · `R_HEAD` matching headings · `R_FEAT` matching features · `R_END` matching sentence endings · `R_SENT` sentence completion · `R_SUMM` summary/note/table/flow-chart completion · `R_DIAG` diagram label completion · `R_SHORT` short-answer questions. No extra transfer time; ~20 min per passage is the usual guide.

## Writing (60 min)

| Task | Academic | General Training | Min words | Suggested time | Weight |
|---|---|---|---|---|---|
| 1 | Describe a graph / table / chart / diagram / process / map | Letter (personal / semi-formal / formal, 3 bullet points) | 150 | 20 min | 1/3 |
| 2 | Essay: opinion, argument or problem | Semi-formal discursive essay | 250 | 40 min | 2/3 |

## Speaking (11–14 min)

| Part | What happens | Time |
|---|---|---|
| 1 | Introduction + questions on familiar topics | 4–5 min |
| 2 | Cue card: 1 min preparation, talk up to 2 min, 1–2 follow-up questions | 3–4 min |
| 3 | Discussion of more abstract issues linked to Part 2 | 4–5 min |

## How this maps to the platform

- **Defaults:** `catalog.SectionTiming` (inline on Exam in Django admin) holds the real-exam section time + transfer/review time. `seed_demo` creates them only if missing, so admin edits are never overwritten.
- **Per mock overrides:** `catalog.MockPackSection` (inline on Mock pack) can reorder sections or change their time; empty duration = exam default. `MockPack.section_plan()` returns the effective timing the Phase 3 timer will use.
- **Practice timing:** `QuestionType.default_time_sec` (per category, editable in admin) is the timer for question-wise practice: ~10 min per listening set, ~20 min per reading set, 20/40 min for Writing Task 1/2, 5/4/5 min for Speaking parts.
- **Content shape:** one `Question` = one question *set* (instructions + passage/script + numbered items), the way IELTS groups questions. `stem.items` are shown to students; `answer_key.answers` (by item number) stays on the server. `MockPackItem.part` = listening part / reading passage / writing task / speaking part.
- **Listening audio:** not recorded yet; the script lives in `scorer_meta.transcript` (server-only) until TTS/real audio is added as an `Asset`.
- **Seed content:** IELTS Academic Mock Test 1 (free) and IELTS General Training Mock Test 1 (free) with full 40/40/2/3 structure, plus practice sets for each category under "Practice by type".
