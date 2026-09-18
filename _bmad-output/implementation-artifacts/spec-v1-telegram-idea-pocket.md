---
title: 'v1 Telegram idea pocket'
type: 'feature'
created: '2026-09-18'
status: 'done'
route: 'full'
route_source: 'auto'
baseline_commit: 'a76504f349b8725806527d13a56a0d6874a56c2e'
review: 'thorough'
review_source: 'auto'
lenses_ran: ['blind-hunter', 'edge-case-hunter', 'verification-gap', 'intent-alignment']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/specs/spec-telegram-idea-pocket/shelves.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-idea-collector-2026-09-18/DESIGN.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Ideas drown in Telegram Saved Messages among materials and reminders. Need a dedicated pocket as fast as Saved to dump into, then easy to scan by source and copy out.

**Approach:** Single-operator bot + Mini App. First paint: field + count; list later by shelves. Persist the blob immediately; LLM extracts `{source, short_name, description}`. CSV deferred (`/csv`).

## Boundaries & Constraints

**Always:**
- First WebApp frame is only `capture-field` + `ideas-counter`. The capture form is in the first HTML so typing does not wait on JS. List must not block submit.
- Persist raw text first (chat or WebApp). Do not wait on LLM or `/api/ideas`. Repeat submit = another idea. Shelf never required to finish capture.
- LLM via OpenAI-compatible `OPENAI_BASE_URL` / `OPENAI_API_KEY` / `OPENAI_MODEL` extracts only those three fields. Map `source` with `shelves.md`. Empty source → `идея собственная`. No evaluative fields.
- After LLM: row = `short_name`, tap copies `description`. Pending or LLM fail: row and copy = raw text, shelf `идея собственная` until a source exists.
- Ideas only. Only `OPERATOR_TELEGRAM_ID`. One column, one screen. Vite + React + TS + `@telegram-apps/sdk` v3 + `@telegram-apps/telegram-ui` + `themeParams` (`DESIGN.md` fallbacks). No TON Connect, no router.
- Python 3.12, aiogram 3, SQLite, aiohttp serves `webapp/dist`. Also `BOT_TOKEN`, `PUBLIC_BASE_URL`, `SQLITE_PATH`.
- Placeholder `Идея`; counter is a number; `Скопировано` on copy; one destructive error line; text stays; count unchanged. Hide empty shelves; start collapsed. Empty pocket: field + `0`.

**Never:** CSV this slice. Reminders, favorites, processed marker, search, pagination, login, tabs, modals, Saved as store. Block capture on the model. Rewrite beyond the three extract fields.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Bot dump | Operator text | Raw stored; ack; count +1; LLM queued | Non-operator ignored. Persist fail → not stored, short error |
| WebApp dump | Submit, list pending | Raw stored; field clears; count +1; LLM queued | Persist fail → text remains, count unchanged, destructive line |
| LLM ok / no source / fail | Enrichment result | Ok: shelf+`short_name`+copy `description`. Empty source or fail: `идея собственная`; fail keeps raw | Unknown aggregator name used as shelf. No retry storm |
| First paint / empty | JS late / count 0 | Field + count in first HTML; empty = `0` and no headers | List may skeleton; field stays enabled |
| Copy / repeat / offline | Tap row / same text twice / no net | Copy per Always; two rows if saved twice; unsaved until accepted | Copy fail: destructive line, retry. Offline: keep field text |

</frozen-after-approval>

## Code Map

- Tracked: `README.md` stub, `LICENSE` (leave), `.gitignore` — add `.env`, `*.db`, `webapp/node_modules`, `webapp/dist`.
- Create `pyproject.toml`, `src/idea_collector/`, `webapp/`, `tests/`. Do not edit `_bmad/`, `.agents/`, or other `_bmad-output/` files.

## Tasks & Acceptance

**Execution:**
- [ ] `pyproject.toml` -- Python ≥3.12, aiogram 3, aiohttp, httpx, pytest, pytest-asyncio, ruff; script `idea-collector`
- [ ] `src/idea_collector/config.py` -- env; boot-fail without token, operator id, LLM url/key/model
- [ ] `src/idea_collector/db.py` -- `ideas(id, raw_text, source, short_name, description, created_at)`; insert, count, list, update enrichment
- [ ] `src/idea_collector/shelves.py` -- group by mapped source; empty → `идея собственная`; skip empty; order = first-seen
- [ ] `src/idea_collector/llm.py` -- OpenAI-compatible JSON extract; `shelves.md` in prompt
- [ ] `src/idea_collector/bot.py` -- operator-only capture; Mini App button `PUBLIC_BASE_URL`; no `/csv`
- [ ] `src/idea_collector/web.py` -- `initData` HMAC; `GET /` injects count, keeps form; `/api/count`; `/api/ideas`; POST returns after INSERT; `asyncio.create_task` for LLM
- [ ] `webapp/` -- Vite React TS; sdk `init`; `telegram-ui` AppRoot/Input/Section/Cell/Accordion; capture form in `index.html`; React mounts `#idea-list` only; Cell tap copies; long-press not prevented
- [ ] `tests/test_db.py` `tests/test_shelves.py` `tests/test_llm.py` `tests/test_web.py` -- I/O matrix, no live Telegram/LLM
- [ ] `README.md` `.env.example` -- polling, HTTPS URL, BotFather, webapp build

**Acceptance Criteria:**
- Given Mini App opens, when the first frame paints, then field and count work before `/api/ideas` and without the JS bundle.
- Given field submit or operator bot text, when persist succeeds, then a new idea exists, count +1, and the response did not wait on the LLM.
- Given mixed sources including none, when the list loads, then named shelves have rows, unshelved/failed-LLM rows are in `идея собственная`, empty shelves are absent.
- Given LLM success, when a row is shown, then the label is `short_name` and tap copies `description`.

## Implementation Notes

## Spec Change Log

## Review Triage Log

Pass 1 (thorough, auto): high 0, medium 8, low 14, false 12, maybe-false 2.

- medium — BH1/EC5 `src/idea_collector/enrich.py:25-27` — `queue` does not keep the Task; asyncio only weakly refs tasks, so a long LLM call can be collected. Route patch.
- medium — BH2/EC2 `src/idea_collector/auth.py:28-44` — no `auth_date` max age; stolen initData replays forever. Tests currently use `auth_date=1`. Route patch.
- medium — BH3 `src/idea_collector/web.py:73` — `initData` accepted from the query string; HMAC material can hit logs. Client uses `Authorization`. Route patch (drop query).
- false — BH4 unauthenticated `GET /` count: Mini App HTML must load without initData; frozen first-paint injects count. Fix would edit frozen intent/spec. Reject (fix edits spec).
- false — BH5 persist needs JS: frozen requires typing without JS, not persist without initData. HMAC only exists after SDK. Reject.
- low — BH6 no auto-expand after save: EXPERIENCE.md, not frozen intent; operator can tap a shelf. Reject (not everyday, adds UI state).
- low — BH7/EC15 stale list/count while Mini App stays open during bot dumps: operator usually dumps then looks. Reject (poll loop is extra complexity).
- medium — BH8 `webapp/src/capture.js:59-71` — any non-OK POST is «Не удалось сохранить», including 401/403. Route patch: use server `error` when present.
- medium — EC14/BH8 `webapp/src/listApp.tsx:35-42` — list fetch failure sets `shelves: []` (empty pocket). Route patch: keep `null` skeleton.
- low — BH9 clipboard only `navigator.clipboard`: fail path already shows destructive line and retry. Reject (SDK fallback is extra).
- low — BH10 blocking SQLite on the asyncio loop: single-operator local db. Reject (aiosqlite is extra).
- low — BH11 safe-area / 44pt / reduce-motion: not in frozen intent. Reject.
- low — BH12 source `index.html` fallback when `dist` missing: README requires build; tests use the fallback. Reject (404 would break GET `/` tests without a dist).
- medium — BH13 empty POST is HTTP 500 persist fail (`capture.py:32-33`). Route patch: 400, not a disk failure.
- false — BH14 README omits HTTPS/BotFather: README already requires HTTPS and BotFather menu URL. Remaining pytest docs are cosmetic. Reject.
- medium — EC1 `auth.py` `compare_digest` on non-ASCII `hash` can 500. Route patch: catch TypeError/ValueError → 401.
- medium — EC3 `capture.py:38` `queue` is outside the insert try; a raise after commit looks like persist fail. Route patch: catch, still return stored idea.
- medium — EC4 insert then `count()` under separate locks: concurrent dumps can ack the same count. Route patch: count in the same lock as insert.
- medium — EC6/EC7 `__main__.py` — menu-button/start can skip `runner.cleanup`; shutdown does not drain enricher tasks. Route patch: try/finally + await pending tasks.
- low — EC9 `message.answer` after store: retry can duplicate. Smallest fix is swallow answer errors (idea already saved). Route patch.
- low — EC10 captions/photos ignored: frozen I/O is operator text. Reject.
- low — EC11 `PUBLIC_BASE_URL` with a path: operator-supplied origin. Reject.
- false — EC12 missing `shelves.md` at import: file is shipped beside the module in this diff. Reject.
- medium — EC8/EC13 JSON `text` non-string or 200 body parse fail: `str(None)` stored; client may retry after a successful insert. Route patch: only accept `str`; client parse error must not flip `persisted` after `response.ok`.
- false — EC16 capture is not telegram-ui `Input`: frozen requires the form in first HTML; tasks naming Input lose. Reject (fix would edit spec).
- medium — VG1 (pre-verified) `Enricher._run` success path untested; only `apply_extraction` (unused in prod) is. Route patch: test `_run` with a successful Extraction.
- medium — VG2 (pre-verified) “queued” is a counter; `HangingLlm.started` never awaited. Route patch: wait on `started`.
- medium — VG3 (pre-verified) bot dump never runs `on_text` / `create_dispatcher`. Route patch: `feed_update` in-process.
- medium — VG4 (pre-verified) `bindCaptureForm` never executed; probe only helpers. Route patch: stub form + fetch in `capture_probe.mjs`.
- low — VG5 (pre-verified, filed defer) Cell tap → `idea.copy` has no UI runner. Route defer.
- false — IA R5 `shelves.md` vs LLM source: operator may name the source in the blob; model extracts it. Matches approved frozen Always.
- false — IA R2 “list later” as a later release: this slice implements later-in-the-same-open (R1), which matches frozen first-paint vs list API.
- maybe-false — IA tests sit on HTML/JSON not Telegram UX: covered by VG1–VG5 where concrete; remainder is the chosen test pyramid, not a second defect.
- maybe-false — IA CSV absence untested: `/` messages are ignored; no `/csv` handler. Would need an explicit ignore assertion to settle. If true, only low. Reject maybe-false-as-low.


## Verification

**Commands:**
- `uv run pytest` -- I/O-matrix tests pass
- `uv run ruff check src tests` -- clean
- `npm --prefix webapp run build` -- `webapp/dist` exists

**Manual checks (if no CLI):**
- Type while the list is skeleton; bot and WebApp increment count; after LLM, shelf + short name + copy description.
