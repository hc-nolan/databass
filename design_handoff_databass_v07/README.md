# Handoff: databass v0.7 — UI redesign

## Overview

A full visual + UX redesign of **databass** (`hc-nolan/databass`), a single-user music
diary built on Flask + Jinja2 + SQLAlchemy + Postgres, with hand-rolled CSS/JS and Pure.css
grid classes. The redesign covers every screen in v0.6: home, new listen, browse
(releases/artists/labels), stats, goals, and the release/artist/label detail views.

Goals of the redesign, in priority order:

1. Keep the data-first, terminal-adjacent character of v0.6 — dark, dense, honest — while
   replacing hand-rolled table layouts with a consistent component system.
2. Promote album art and *the user's own data* (score, listen date, notes) to first-class
   elements. v0.6 shows MusicBrainz facts; v0.7 shows what the user thought.
3. Answer the question the README states as the app's purpose ("help you uncover your
   listening habits") on the stats page: time series, distributions, streaks — not just
   leaderboards.
4. Display ratings on a **0–10 scale**. The database still stores 0–100
   (`Release.rating`, `CheckConstraint("rating >= 0 AND rating <= 100")`); this is a
   presentation change only — `display = stored / 10`, one decimal.

## About the design files

The files in `designs/` are **design references written as HTML** — prototypes that show
intended look and behaviour. They are *not* production code and should not be dropped into
the app. Each is a `.dc.html` file rendered by a small runtime (`designs/support.js`);
open them in a browser to interact with them.

The task is to **recreate these designs in the existing databass codebase** — Jinja2
templates + a stylesheet, matching the project's current no-build-step,
no-framework approach unless the maintainer decides otherwise. All styling in the
prototypes is inline for streaming reasons; in the real app it should become a proper
stylesheet with the CSS custom properties listed under **Design tokens**.

The prototype logic classes (`class Component extends DCLogic`) exist to make the mock
interactive. Their contents indicate intended *behaviour* and *copy*, and the data arrays
in them indicate the *shape* of data each view needs — they are not an implementation
suggestion.

## Fidelity

**High fidelity.** Colours, type sizes, spacing, radii and copy are final and should be
matched closely. Layout is fluid (flex/grid with wrapping) rather than fixed-width — no
breakpoint work is implied beyond what the flex-wrap rules already express.

Two exceptions, both deliberate:

- **Album/artist/label art** is drawn as a striped placeholder tile with the entity's
  initials. In the real app this is `Release.image` / `Artist.image` / `Label.image`.
  The placeholder tile is the intended **fallback** when `image` is null — it replaces the
  repeated broken-image glyph in v0.6, and should be kept.
- All numbers, names and diary text in the prototypes are **plausible sample data**, not
  the user's real library.

---

## Design tokens

All colours are given in `oklch()`. They are dark-UI values on a warm-neutral ramp; keep
them as CSS custom properties.

### Colour

| Token | Value | Use |
| --- | --- | --- |
| `--bg` | `oklch(0.16 0.008 70)` | page background |
| `--panel` | `oklch(0.19 0.009 70)` | cards, header of grouped strips |
| `--panel-alt` | `oklch(0.185 0.009 70)` | cells inside grouped strips, list rows |
| `--field` | `oklch(0.16 0.008 70)` | input/textarea background |
| `--hover` | `oklch(0.19 0.009 70)` | row hover fill |
| `--line` | `oklch(0.26 0.01 70)` | hairlines, dividers |
| `--border` | `oklch(0.28 0.01 70)` | default card border |
| `--border-strong` | `oklch(0.32 0.01 70)` | input borders, chips, active card |
| `--border-hover` | `oklch(0.45 0.012 80)` | hovered control border |
| `--ink` | `oklch(0.93 0.012 80)` | primary text |
| `--ink-2` | `oklch(0.88 0.012 80)` | body copy in notes/insights |
| `--ink-3` | `oklch(0.8 0.012 80)` | secondary values |
| `--muted` | `oklch(0.7 0.012 80)` | labels, meta, inactive controls |
| `--muted-2` | `oklch(0.66 0.012 80)` | lowest-priority meta |
| `--track` | `oklch(0.26 0.01 70)` | progress/bar track |
| `--bar-dim` | `oklch(0.44 0.014 70)` | non-peak chart bars |
| `--amber` | `oklch(0.74 0.13 62)` | primary accent: section eyebrows, primary buttons, peak bars, score bars |
| `--amber-hover` | `oklch(0.8 0.13 62)` | primary button hover |
| `--on-amber` | `oklch(0.2 0.03 62)` | text on amber fills |
| `--amber-soft-bg` | `oklch(0.3 0.05 62)` | selected chip fill |
| `--amber-soft-fg` | `oklch(0.88 0.07 62)` | selected chip text |
| `--amber-soft-border` | `oklch(0.5 0.08 62)` | selected chip border |
| `--cyan` | `oklch(0.72 0.13 200)` | secondary accent: goal progress, count bars, positive status |
| `--cyan-soft-bg` | `oklch(0.3 0.05 200)` | "complete" / "on track" badge fill |
| `--cyan-soft-fg` | `oklch(0.84 0.09 200)` | that badge's text |
| `--red` | `oklch(0.7 0.13 30)` | shortfall / missed |
| `--red-soft-bg` | `oklch(0.32 0.06 30)` | "behind pace" / "missed" badge fill |
| `--red-soft-fg` | `oklch(0.86 0.09 30)` | that badge's text |
| `--danger-text` | `oklch(0.72 0.08 30)` | delete button label |

**Contrast rule:** every muted value in the table clears 4.5:1 against `--bg` and
`--panel`. Do not darken the muted ramp below `oklch(0.64 …)`; earlier drafts at
`oklch(0.48–0.55)` failed WCAG AA at these type sizes.

Links: `a { color: var(--ink) }`, `a:hover { color: var(--amber) }`. Inline links inside
prose use a `1px solid oklch(0.4 0.012 70)` bottom border rather than underline.

### Typography

Single family: **Public Sans** (Google Fonts), weights 400 / 500 / 600 / 700 / 800, plus
italic 400. Fallback stack: `'Public Sans', Helvetica, Arial, sans-serif`.

`font-variant-numeric: tabular-nums` is set on the page root — required, since most of the
UI is columns of numbers.

| Role | Size | Weight | Tracking | Notes |
| --- | --- | --- | --- | --- |
| Wordmark "databass" | 23px | 800 | `-0.04em` | version tag beside it: 10px/400, `0.12em`, `--muted` |
| Page title / section head | 15px | 700 | `0.16em` | uppercase |
| Section eyebrow (in cards) | 11px | 700 | `0.16em` | uppercase, `--amber` |
| Field label | 10.5px | 400 | `0.12–0.14em` | uppercase, `--muted` |
| Hero number (goal, KPI) | 40px / 42px | 600 | `-0.045em` | |
| Detail page `h1` | 34px | 700 | `-0.035em` | line-height 1.1 |
| Stat value | 19–26px | 600 | `-0.02 – -0.03em` | |
| Entry title | 14.5–15px | 500 | — | |
| Body / table cell | 13.5px | 400 | — | base size |
| Secondary meta | 11.5–12.5px | 400 | — | `--muted` |
| Micro label / badge | 10–11px | 700 | `0.08em` | uppercase |
| Diary / note text | 13–16px | 400 *italic* | — | `--ink-2`, line-height 1.5–1.55, `text-wrap: pretty` |

Base body: 13.5px / 1.5, `-webkit-font-smoothing: antialiased`.

### Spacing, radii, shape

- Page padding: `24px 28px 84px`; header padding `22px 28px`.
- Page max-widths: 1440px (home, browse, stats), 1240px (detail), 1100px (goals).
- Card padding: 20–26px. Gaps: 4–6px (chip rows), 10–12px (control rows), 16–20px
  (card internals), 20–28px (page sections).
- Radii: `999px` pills/chips · `4–6px` art thumbnails and small buttons · `7–8px` inputs,
  buttons, segmented items · `10px` rows and inner strips · `12px` cards · `14px` hero card.
- Borders: 1px. Hairline dividers use `--line`; cards use `--border`.
- No shadows anywhere. Depth comes from the panel/bg value difference only.
- Bars: 3px (inline score bar), 4px (genre share), 5px (goal history), 16px (active goal).

### Reusable patterns

- **Segmented control** — wrapper: `padding:4px; border:1px solid var(--border);
  border-radius:10px; background:var(--panel); display:flex; gap:4px`. Item:
  `padding:8px 16px; border:0; border-radius:7px; font-size:13px; font-weight:600`.
  Active item = `--amber` fill + `--on-amber` text (primary switchers) or
  `oklch(0.28 0.012 70)` fill + `--ink` text (secondary switchers, e.g. artists/labels).
- **Chip / filter button** — `padding:5px 11px; border-radius:999px; border:1px solid
  var(--border-strong); font-size:11.5px`. Selected: `--amber-soft-*` trio.
- **Primary button** — `padding:9–11px 16–20px; border:0; border-radius:8px;
  background:var(--amber); color:var(--on-amber); font-size:12.5px; font-weight:700;
  letter-spacing:0.03–0.04em`. Hover `--amber-hover`.
- **Ghost button** — transparent fill, `1px solid var(--border-strong)`, `--ink-3` text;
  hover raises border to `--border-hover` and text to `--ink`.
- **Input** — `padding:9–12px; border:1px solid var(--border-strong); border-radius:7–8px;
  background:var(--field); color:var(--ink); font-size:13–13.5px; outline:none`.
  Focus: `border-color: var(--amber)`. Placeholder: `oklch(0.5 0.012 80)`.
- **Stat strip** — a `display:flex; flex-wrap:wrap; gap:1px` container with
  `background: var(--border)` and `overflow:hidden`, children `flex:1 1 <min>px` on
  `--panel`/`--panel-alt`. The 1px gaps read as dividers. **Do not use
  `grid-template-columns: repeat(auto-fit, …)` here** — a trailing partial row exposes the
  container colour as an empty cell.
- **Art placeholder** — `background-color: oklch(0.28 0.01 70);
  background-image: repeating-linear-gradient(135deg, oklch(0.32 0.012 70) 0 2px,
  transparent 2px 7px);` with the entity's initials (up to 3–4 chars, uppercase, 700,
  `0.1–0.14em`, `--muted`) centred or bottom-left.
- **Mode pill** (the vim-style indicator kept from v0.6) — `position:fixed; left:14px;
  bottom:12px; pointer-events:none; padding:3px 9px; border:1px solid
  var(--border-strong); border-radius:5px; background:var(--panel); font-size:10.5px;
  letter-spacing:0.08em; color:var(--muted)`. Bottom-**left**, and non-interactive, so it
  never covers right-aligned links.

### Global chrome

Header, identical on every screen: `display:flex; flex-wrap:wrap; align-items:baseline;
gap:20px 28px; padding:22px 28px; border-bottom:1px solid var(--line)`. Contents:
wordmark + version; nav (`home · new · browse · stats · goals`) as 999px pills, active =
`oklch(0.24 0.012 70)` fill and `--ink` text, inactive = transparent with `--muted`;
then a right-aligned contextual counter (e.g. "2,171 logged · 312 this year").

Note the nav change: **releases / artists / labels collapse into one `browse` item.**

---

## Screens

### 1. Home — recent listening (`designs/Databass Home.dc.html`)

Replaces the v0.6 home table + right-hand stats/goals rail.
Route: `/`. Data: `Release.home_data()` plus the existing home stats and goal queries.

**Layout** — header; then a wrapping row with `gap:28px`, `padding:28px`,
`max-width:1440px`: `main` at `flex:1 1 540px`, `aside` at `flex:1 1 290px`
(`min-width:260px`). Aside wraps below main on narrow viewports.

**Main, top to bottom**

1. **Quick log bar** — one card (`padding:14px 16px`, `border-radius:10px`,
   `--panel`): an amber `›` prompt glyph, a borderless transparent input
   (placeholder "log a release — artist, title, or MBID"), a `TODAY` label
   (10.5px, `0.08em`, `--muted`), and a primary `LOG` button. Submitting should route to
   the new-listen search with the query pre-filled.
2. **Section head** — "Recent listening" (15px/700/`0.16em`, uppercase) with
   "sorted by listen date ↓" right-aligned in `--muted-2`.
3. **Day groups** — listens grouped by `listen_date`, newest first, `margin-bottom:22px`.
   Group header: amber label + a 1px rule that flexes to fill + right-aligned count.
   Label format: `TODAY · SAT 12 SEP` / `YESTERDAY · FRI 11 SEP` / `WED 09 SEP · 3D AGO`.
   Right meta: `"2 releases · 1h 20m"` (sum of `Release.runtime` in the group).
4. **Entry row** — `display:grid; grid-template-columns:68px minmax(0,1fr) auto;
   gap:18px; padding:14px 12px; border-radius:10px; border:1px solid transparent`.
   Hover: `--hover` fill + `--border-hover`-adjacent border (`oklch(0.27 0.01 70)`).
   - Column 1: 68×68 art, `border-radius:4px`, initials bottom-left at 10px/700.
   - Column 2: title link (15px/500) + release year (11px, `--muted-2`); artist link
     (12px, `--ink-3`) `/` label link (12px, `--muted`); then genre chips — main genre in
     an outlined 999px chip (10px, `0.06em`), subgenres as borderless chips in `--muted`;
     then the diary note (italic, 15px, `--ink-2`, `max-width:58ch`).
   - Column 3, right-aligned, `min-width:96px`: score (22px/500, `-0.03em`) + suffix
     (`/10`, 10px, `--muted`); an 88×3px track with an amber fill at `rating%`;
     then `"54m · 4 tracks"` in 10.5px.
5. **`LOAD EARLIER ↓`** ghost button, left-aligned.

**Aside** — four cards, all `--panel`, `border-radius:12px`, `padding:20px`:

1. **THIS YEAR** — 42px/600 count + "releases"; then a two-column key/value grid
   (`1fr auto`, 7px/12px gaps, 12px text): new artists, new labels, listening time,
   average score, pace (pace value in `--amber`).
2. **GOAL** — eyebrow + status badge; goal title; big percent; 5px progress bar in
   `--cyan`; key/value rows for remaining, days left, needed/day.
3. **SCORE SPREAD** — ten bars, 64px tall, `gap:5px`, modal bucket in `--amber`, rest in
   `oklch(0.36–0.4 0.012 70)`; axis row: `1 · median 5.5 · 10`.
4. **ON REPEAT — 90 DAYS** — three rows of 34px art + name link + `"7 releases · avg 6.4"`.

**Tweaks exposed in the prototype:** `showNotes` (boolean), `ratingScale`
(`0–10` / `percent` / `stars`). Treat these as user preferences if worth persisting;
otherwise implement the `0–10` default and drop the rest.

---

### 2. New listen (`designs/Databass New Listen.dc.html`)

Replaces `/new` + the modal form. Routes: search `POST`, then create.

**The central change: no modal.** Search results sit on the left; a persistent
**log panel** sits on the right (`position:sticky; top:28px`) and fills in when a result
is selected, staying editable. `main` is `flex:1 1 560px`, `aside` `flex:1 1 340px`
(`min-width:300px`).

**Search card** (`--panel`, 12px radius, 18px padding): eyebrow `SEARCH MUSICBRAINZ`,
with a `manual entry` ghost button right-aligned; then a wrapping row of three inputs
(release `flex:2 1 200px`, artist and label `flex:1 1 150px`) and a primary `SEARCH`
button; then a meta line: `"6 results for “guitar romantic”"` · separator ·
"duplicates of releases you already logged are marked".

**Result row** — `grid-template-columns:52px minmax(0,1fr) auto; gap:16px; padding:12px;
border-radius:10px`, 52px art. Selected row: `background: oklch(0.22 0.012 70)` and
`border-color: var(--amber)`; unselected `oklch(0.185 0.009 70)` / `--border`; hover
raises the border. Middle: title (14.5px/500) plus, when the MBID or
(name, artist) already exists in the DB, an `ALREADY LOGGED` badge (cyan-soft, 9.5px/700);
under it `artist / label` in `--muted`. Right: year · `10 tr` · country · format
(format right-aligned, `min-width:78px`, `--ink-3`). MusicBrainz returns many near-identical
pressings, so these disambiguating columns must all be visible without hovering.

**Log panel** (`--panel`, `border:1px solid var(--border-strong)`, 22px padding, 12px radius):

- Header: `LOG THIS LISTEN` eyebrow + `⏎ to save` hint.
- Empty state: dashed-border box, centred, "Pick a result to fill this in. / Everything
  below stays editable."
- Selected state, 18px gaps: 64px art + title/artist/subline
  (`label · year · format · country`); **rating** — label row with the live value
  (`7.0 / 10`), then ten segment buttons (`flex:1; height:30px; border-radius:4px`,
  filled = `--amber` + `--on-amber`, empty = `oklch(0.21 0.01 70)` + `--muted`), then a
  hint line pairing a word with the stored value: `"really good · stored as 70%"`.
  Word scale, index 1–10: actively bad, didn't work, flat, thin, fine, solid, really good,
  excellent, near-perfect, all-timer.
- Two-up row: `LISTENED` (date, defaults to today per `TIMEZONE`) and `TRACKS` (readonly,
  from MusicBrainz).
- `GENRE`: toggle chips seeded from the MB genre list, plus an `+ add subgenre` input.
  Maps onto `Genre.create_genres` / `release_genre_association`.
- `NOTE — OPTIONAL`: italic textarea, "what did it feel like?" — creates a `Review` row
  at the same time as the `Release`. Getting the note at creation time is the point;
  v0.6 only allows it later from the release page.
- Footer: primary `SAVE LISTEN` (becomes `SAVED ✓`) + `clear` ghost button, then
  `"189 to go on your 2026 goal"` centred in 10.5px.

Mode pill reads `insert` while the panel is active, `saved` after a save.

---

### 3. Browse — releases / artists / labels (`designs/Databass Browse.dc.html`)

One page replacing `/releases`, `/artists`, `/labels`, which shared a layout and differed
only in filters. Suggested route: `/browse/<entity>` with the old routes redirecting.

**Entity switcher** — a segmented control on the page (not just in the nav), each item
showing its total: `releases 2,171 · artists 1,124 · labels 915`. Active item is amber.
Beside it, `"10 of 2,171 shown"`.

**Filter bar** (`--panel` card, 14px padding, wrapping row, `gap:10px`):

- free-text input, `flex:1 1 240px`, placeholder per entity ("search release or artist" /
  "search artist" / "search label");
- **facet buttons** — one per available filter, each showing its label *and* current value
  (`country US`, `genre hip hop`, `year 2010s`, `rating 7+`). Selected facets take the
  amber-soft treatment. In the real app these open a value picker; the prototype toggles a
  single representative value.
- `grid` / `list` view toggle pushed right with `margin-left:auto`.

Facet sets per entity — releases: label, country, genre, year, rating.
Artists: country, type, releases count, rating. Labels: country, type, releases count.
These map to `Release.dynamic_search` and `ArtistOrLabel.dynamic_search`; the existing
comparison operators (`<`, `=`, `>`) belong inside the facet's value picker, not as
separate bare selects.

**Sort row** — `SORT` label plus pill buttons; active pill amber-soft. Releases: listened ↓,
rating ↓, year ↓, a–z. Artists: releases ↓, avg rating ↓, last listened ↓, a–z.
Labels: releases ↓, avg rating ↓, a–z. Then a divider and the **active filter chips**,
each removable (`country: US ×`), with a `clear all` link. Sorting and filtering must
actually drive the query — this row is the page's whole purpose.

**Grid view** — `repeat(auto-fill, minmax(168px,1fr))`, `gap:22px 18px`. Card: square art
(`aspect-ratio:1`, 6px radius) with a score badge bottom-left
(`padding:2px 8px; border-radius:5px; background: oklch(0.2 0.02 70)`, 11.5px/600); below,
name (13px/500, `text-wrap:pretty`) and meta (11.5px, `--muted`) — `artist · year` for
releases, `12 releases · CA` for artists/labels.

**List view** — `grid-template-columns:40px minmax(0,1fr) auto`, 40px art, name + meta
inline, score right-aligned (`min-width:52px`), hover fill as on home.

**Pagination** — centred `← back` / `next →` ghost buttons with `"page 1 of 73"` between
them. Keep the existing `pagination.py` logic; just show position.

---

### 4. Stats (`designs/Databass Stats.dc.html`)

Replaces `/stats`. Reframed from three leaderboards to "Listening habits". All of it comes
from data already in the schema (`listen_date`, `rating`, `runtime`, genre associations).

- **Period switcher** — segmented control: `2026` / `2025` / `all time`, with the date
  range beside it. Drives every section on the page.
- **KPI strip** — the flex-wrap stat strip pattern, `flex:1 1 150px` per cell: releases,
  artists, labels, listening time, mean score, pace. Each cell = label (10.5px,
  `0.13em`, `--muted`), value (26px/600, `-0.03em`), and a comparison sub-line
  ("+18% vs 2025", "54% new to you", "goal needs 1.71").
- **WHEN YOU LISTEN** (`flex:2 1 520px`) — a 170px-tall bar chart of releases per month
  (per year for all-time), value above each bar and label below, peak bar in `--amber`,
  others `oklch(0.44 0.014 70)`. Under a hairline: busiest month, busiest day, longest
  streak, quietest stretch.
- **HOW YOU RATE** (`flex:1 1 300px`) — the ten-bucket 0–10 histogram (96px tall, modal
  bucket amber), a `1 / 5 / 10` axis, then mean, median, `rated 8+`, `rated 3−`.
- **LEADERBOARDS** — one card containing an `artists` / `labels` segmented toggle and
  three columns (`repeat(auto-fit, minmax(280px,1fr))`): Most frequent, Highest average,
  Favourites. Each column has a title (13.5px/700) **and a one-line explanation**, which
  v0.6 lacked:
  - Most frequent — "by releases logged" (bars in `--cyan`, values as `29 rel`)
  - Highest average — "simple mean of your scores — thin on 2–3 release artists"
  - Favourites — "Bayesian average — weights score by how much you've actually logged"
    (bars in `--amber`, values as `7.0 / 10`)
  Row: rank (18px col, `--muted-2`) · name + 3px bar scaled to the column max · value
  right-aligned (`min-width:54px`). Backed by `frequency_highest`,
  `average_ratings_and_total_counts`, `average_ratings_bayesian`.
- **WHAT YOU LISTEN TO** — top genres, each a name + 4px share bar + `"412 · 19%"`.
  Top genre in amber.
- **NOTICED** — 3–4 plain-language reads of the same data, each a 6px accent dot plus a
  sentence in `--ink-2`. These are templated sentences computed from the stats above
  (e.g. best-rated vs most-logged genre; share of first-listens; weekday concentration;
  volume up / mean flat). Optional — cut the card if the derivations aren't worth it.

---

### 5. Goals (`designs/Databass Goals.dc.html`)

Replaces `/goals` (a bare form + a one-row table). `max-width:1100px`.

**Active goal card** (14px radius, `border:1px solid var(--border-strong)`):

- Eyebrow `ACTIVE GOAL`, a status badge (`BEHIND PACE` red-soft / `ON TRACK` cyan-soft),
  and the window right-aligned: `"01 Jan 2026 → 01 Jan 2027 · 110 days left"`.
- Headline: `312` (40px/600) `/ 500 releases` (18px, `--ink-3`) `62% complete`.
- **Progress bar with a pace marker** — 16px track, amber fill at
  `actual / target`, and a 2px white vertical marker at `days_elapsed / days_total`.
  Under it: `"312 logged"` and `"even pace would be 349 by today — you're 37 behind"`.
  This comparison is the point of the redesign: v0.6 shows progress but never says whether
  the user is ahead or behind.
- **Metric strip** (flex-wrap, `flex:1 1 140px`): remaining, days left, needed/day (amber),
  current pace, projected (cyan if it clears the target, red with "54 short" if not).
- A projection sentence: `"At 1.22 / day you finish the year on 446 — 54 short. One extra
  record on 54 of the remaining 110 days closes the gap; otherwise moving the deadline to
  2027-01-23 keeps the pace you actually have."`

**Set a new goal** card — amount input, an `OF` segmented control
(`releases` / `artists` / `labels`, matching `Goal.type`), a `BY` date input, and a
primary `CREATE GOAL` button. Below, a **feasibility readout** that recomputes as you
type: the required rate (19px/600) plus a sentence, colour-coded against the user's actual
pace — cyan ≤ 0.85×, amber ≤ 1.25×, red above (`"Ambitious. That's 2.4× your current pace
— you'd need to log 2 more per day than you do now."`). Then preset chips:
`365 in a year`, `100 by new year`, `1000 in a year`.

**Past goals** — one row each: title + window, a 5px result bar, a result line
(`"1,141 of 1,500 · 76%"` or `"hit on 02 Nov 2024 · 60 days early"`), and a
`COMPLETE` / `MISSED` badge. Completed goals come from `Goal.completed`; misses are
goals past `end` with no `completed` value.

---

### 6. Detail — release / artist / label (`designs/Databass Detail.dc.html`)

One layout, three variants (the prototype's top-right "EXAMPLE PAGE" switcher is a demo
affordance only — these are three routes: `/release/<id>`, `/artist/<id>`, `/label/<id>`).
`max-width:1240px`.

**Shared shell**

- Breadcrumb: `browse / releases / Monoliths & Dimensions`.
- Hero: 212×212 art (8px radius) + a `flex:1 1 380px` column containing the eyebrow
  (`RELEASE` / `ARTIST` / `LABEL`), an `h1` at 34px/700/`-0.035em`, a row of related-entity
  links plus a subline, genre chips, the **fact strip** (flex-wrap, `flex:1 1 128px`
  cells: label 10px/`0.12em`, value 15px/600), and the action row.
- Actions: release pages get a primary `LOG ANOTHER LISTEN` (→ `LOGGED AGAIN ✓`), then
  `edit` and `delete` ghost buttons (delete's label in `--danger-text`) and a
  `view on MusicBrainz ↗` link.

**Release-specific facts:** your score (amber), listened date, times listened, runtime,
tracks. Then two cards side by side:

- **DIARY** (`flex:1 1 420px`) — every `Review` for the release as a timeline entry:
  a 2px `oklch(0.36 0.03 62)` left rule, date + the score at the time, then the text in
  italic 14px. Below, a textarea ("add to this record's diary…") and a `save entry`
  ghost button. Re-listens should read as a history, not a single overwritten note.
- **IN CONTEXT** (`flex:1 1 280px`) — key/value rows answering "is 5.5 good *for me*":
  vs your average, vs this artist, vs the genre, rank in year, days since last listen.

**Artist / label facts:** logged count, average score (amber), best score, first and last
listened; labels also show artist count and a rank. No diary or context cards.

**Rails** (all variants, repeatable section): eyebrow title + a note + a right-aligned
`see all` link, then `repeat(auto-fill, minmax(146px,1fr))` cards identical to the browse
grid card but with a 7px-inset score badge.

- Release: `ALSO BY <ARTIST>` ("5 of 18 releases logged") and `ALSO ON <LABEL>`
  ("9 releases logged · avg 6.1").
- Artist: `RELEASES YOU'VE LOGGED` ("5 of 18 in their catalogue") and `IF YOU LIKE THIS`
  (artists sharing genres, with your counts and averages).
- Label: `RELEASES YOU'VE LOGGED` and `ARTISTS ON THIS LABEL`.

Items the user hasn't logged appear greyed with a `—` badge
(`background: oklch(0.24 0.01 70)`, text `--muted-2`) rather than being omitted — coverage
is information.

---

## Interactions & behaviour

- **Hover** — rows and cards raise their border and take the `--hover` fill; buttons
  raise border or brighten fill. No transitions are specified; if you add them keep them
  under 120ms and limited to `background-color` / `border-color`.
- **Focus** — inputs set `border-color: var(--amber)` and keep `outline:none`. Add a
  visible focus ring for keyboard users if the codebase has one.
- **New listen** — selecting a result repopulates the panel and clears the saved state;
  saving flips the button to `SAVED ✓` and the mode pill to `saved`; `clear` resets rating
  and genres but keeps the selection. `⏎` should submit the panel.
- **Browse** — text query, facets and sort all re-query; entity switch resets the sort to
  the first option and clears the query; filter chips remove individually or via
  `clear all`. Filters are per-entity and should not leak across tabs.
- **Stats** — the period switcher re-renders KPIs, the time chart, the rhythm facts and the
  insight sentences; the artists/labels toggle affects the leaderboards only.
- **Goals** — the feasibility readout recomputes on every keystroke in amount or date;
  presets fill both fields.
- **Detail** — `LOG ANOTHER LISTEN` creates a new listen for an existing release (and
  should append a diary entry, not replace one).
- **Responsive** — everything is flex/grid with wrapping and `min-width` floors; there are
  no fixed widths and no media queries. Asides wrap below main content; stat strips reflow;
  grids re-column. The README for v0.6 says development is desktop-only — these layouts are
  usable on a phone as written, provided nothing is given a fixed width.

## State

Per screen, the client-side state the prototypes hold (server-rendered equivalents are
fine — most of this can be query parameters):

- Home: none beyond the preference flags (`showNotes`, `ratingScale`).
- New listen: `selectedResult`, `rating`, `listenDate`, `genres[]`, `note`, `saved`.
- Browse: `entity`, `view` (grid/list), `query`, `sort`, `activeFacets` (per entity), `page`.
- Stats: `period`, `scope` (artists/labels).
- Goals: `amount`, `type`, `end` for the composer.
- Detail: `relistened` (transient confirmation only).

## Assets

- **Fonts:** Public Sans from Google Fonts (`https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,400;0,500;0,700;0,800;1,400&display=swap`). Self-host if you'd rather not call out.
- **Images:** none. Album/artist/label art comes from the existing CoverArtArchive /
  Discogs pipeline (`Util.get_image`), with the striped initials tile as the fallback.
- **Icons:** none — the UI uses text glyphs only (`›`, `↓`, `→`, `←`, `×`, `✓`, `▾`, `⏎`, `↗`).

## Files

```
designs/
  Databass Home.dc.html         home / recent log
  Databass New Listen.dc.html   search + log panel (replaces /new and its modal)
  Databass Browse.dc.html       releases / artists / labels, unified
  Databass Stats.dc.html        listening habits
  Databass Goals.dc.html        active goal, composer, history
  Databass Detail.dc.html       release / artist / label detail (switcher = demo only)
  support.js                    runtime that renders the .dc.html prototypes
```

Open any `.dc.html` directly in a browser; `support.js` must sit alongside them.

## Source repository

`hc-nolan/databass`, branch `main`. Relevant files for implementation:
`src/databass/templates/` (Jinja templates), `src/databass/routes.py`,
`src/databass/db/models.py` (schema — unchanged by this redesign),
`src/databass/stats2.py`, `src/databass/pagination.py`.

**No schema changes are required.** The 0–10 rating is presentational; everything on the
stats and goals pages derives from existing columns. The one thing worth checking is that
`Review` rows are easy to create at release-creation time for the new-listen note field.
