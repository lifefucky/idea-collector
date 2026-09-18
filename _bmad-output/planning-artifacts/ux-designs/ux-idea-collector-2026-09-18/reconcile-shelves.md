# Reconcile — shelves.md

Source: `_bmad-output/specs/spec-telegram-idea-pocket/shelves.md`

## Landed in spines

| Source claim | Where |
|---|---|
| Полка = источник; задаёт группировку после загрузки перечня (CAP-3) | IA, `shelf-group`, Flow 3 |
| На захвате полка необязательна (CAP-4); чат бота и поле WebApp одинаковы | `capture-field`, Flow 1–2 |
| Агрегатор → именная полка (ProductHunt, Product Radar, магазины, YC, новый по имени) | IA glossary полок |
| Чужой продукт не-агрегатор → `чужие приложения` | IA |
| Своя мысль → `идея собственная` | IA |
| Идея без полки видна в перечне | IA, State Patterns, Flow 1 |

## Override (source rule dropped by user)

| Source claim | UX decision |
|---|---|
| «Указывается оператором, не выводится моделью» | Полку ставит LLM в ответе модели |
| «Оператор пишет это явно, если указывает источник» для `идея собственная` | Имя полки всё ещё из перечня `shelves.md`; кто его проставляет в v1 — модель |

## Qualitative, not lost

Идея без указанного источника остаётся в кармане — да. Отдельной группы «без полки» нет: показ в `идея собственная` (решение оператора, не текст `shelves.md`).
