# Reconcile — forged-idea.md

Source: `_bmad-output/forge/telegram-idea-pocket/forged-idea.md`

## Landed in spines

| Source claim | Where |
|---|---|
| Telegram-карман только для идей, бот + Mini App | EXPERIENCE.md Foundation, IA |
| Список идей, сгруппированный по полкам из `shelves.md` | IA, `shelf-group`, CAP-3 |
| Быстрый скролл | Interaction Primitives, Flow 3 |
| Копирование текста | `idea-row`, Flow 3 |
| Дефолт — извлечение, не вдохновение | Foundation, Inspiration, Flow 3 |
| v1 без статуса «обработано» | Foundation, Component Patterns |
| Дисциплина: только идеи, шум остаётся в Saved Messages | Inspiration |
| Трение захвата достаточно низкое, без микроспека шагов | Foundation, Flow 1–2 |
| Забирать наружу в backlog / документы / задачи | Flow 3 climax |

## Dropped or deferred

| Source claim | Why |
|---|---|
| Булевый маркер «обработано» в следующих версиях | Явно post-v1. В v1 запрещён. Не потерян: зафиксирован как out of v1, не как экран. |
| «Веб-/мини-интерфейс» как возможно отдельный веб | UX закрыт как Mini App внутри Telegram, без отдельного сайта. Отдельный браузерный web не подтверждён. |

## Conflicts with later decisions

Нет прямого конфликта с forged-idea. Полка от LLM — конфликт со `shelves.md`, не с этим файлом.
