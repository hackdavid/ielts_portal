# Design system and app shells

## Direction
Premium, calm, "adaptive practice" product. Dark ink + aurora (indigo / violet / cyan) hero surfaces, white cards on slate-50, Plus Jakarta Sans for display, Inter for body, Instrument Serif italic for accents. Fonts are served locally from `static/vendor/fonts/`.

Honesty rules: previews are labelled "Illustrative preview"; scores are "practice estimates" and never "official"; the next-step card is rule-based and must not claim live AI.

## Tokens and components
Defined in `static/src/tailwind.css` (build: `uv run python manage.py tailwind`).

- Colours: `ink`, `ink-2`, `aurora-1..3`, plus tenant `brand` / `brand-fg` (from `--brand`, `--brand-fg`).
- Components are Tailwind v4 `@utility` rules (not `@layer components`, which breaks `@apply`):
  `btn`, `btn-primary`, `btn-ghost`, `btn-light`, `btn-glass`, `btn-lg`, `card`, `card-hover`, `card-dark`,
  `chip`, `chip-brand`, `chip-muted`, `chip-good`, `chip-warn`, `eyebrow`, `field`, `table-clean`, `side-link`, `tab-link`.
- Backgrounds: `bg-aurora`, `bg-grid`, `text-gradient`.
- Motion: add `data-animate` (optional `data-delay`) to reveal on scroll; reduced motion shows instantly.
- Icons: `{% include "components/icon.html" with name="..." cls="h-4 w-4" %}`.

## Layouts
| Template | Used by |
|---|---|
| `base.html` | Public pages, login, 403 (site header + footer) |
| `app/base.html` | Signed-in student and org pages: desktop sidebar, phone bottom tabs, top bar with `crumbs` block |
| `app/focus.html` | Test player, mic check, onboarding (no navigation) |

Navigation items come from `core.context_processors.app_nav` (role-aware; sets `aria-current`). Add a page to the nav by adding its URL name to `STUDENT_NAV` or `ORG_NAV`.

Shared partials: `app/_page_head.html`, `app/_score.html`, `app/_section_icon.html`, `catalog/_pack_card.html`, `institute/_student_row.html`.

## Adaptive seam
`analytics/insights.py`:
- `skill_profile(user, exam)` averages the last 10 scored attempts per section and per question type.
- `next_step(profile, exam, in_progress, packs)` picks: resume an attempt, then drill the weakest question type, then a first mock, then browse.

The future AI picker should replace `next_step()` and return the same dict (`eyebrow`, `title`, `body`, `cta`, `url`, `meta`, `pct`).
