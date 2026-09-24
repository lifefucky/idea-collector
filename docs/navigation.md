# Навигация по файлам

Путь от корня репозитория и краткое назначение. Не включены: `.git`, `node_modules`, `webapp/dist`, кэш `_bmad/`, установленные скиллы `.agents/`, локальная БД `ideas.db`, артефакты исследовательских выгрузок.

## Документация

| Путь | Назначение |
|---|---|
| [docs/navigation.md](navigation.md) | Эта карта файлов. |
| [docs/backlog.md](backlog.md) | Идеи на следующий срез. Открыто: YAML-промпты, Docker, Tinder-отсев. Сделано: карточка, удаление, `/csv`, Sources. |
| [docs/ui-front-v2.md](ui-front-v2.md) | Спека фронта Mini App v2: адаптация визуального референса под Telegram Mini App. |
| [docs/api-v2.md](api-v2.md) | Спека бэкенда Mini App v2: API и модели без новых сущностей. |
| [README.md](../README.md) | Запуск, переменные окружения, HTTP API, `/csv`, стек. |

## Корень репозитория

| Путь | Назначение |
|---|---|
| [pyproject.toml](../pyproject.toml) | Пакет Python: зависимости, точка входа `idea-collector`, pytest и ruff. |
| [uv.lock](../uv.lock) | Зафиксированные версии Python-зависимостей. |
| [skills-lock.json](../skills-lock.json) | Хеши установленных BMAD-скиллов. |
| [.env.example](../.env.example) | Шаблон переменных окружения без секретов. |
| `.env` | Локальные секреты (не в git). Процесс сам файл не читает — нужен `uv run --env-file`. |
| [.python-version](../.python-version) | Требуемая версия Python: 3.12. |
| [.gitignore](../.gitignore) | Игнор: `.env`, `*.db`, `webapp/dist`, `_bmad*`, `.agents`. |
| [Dockerfile](../Dockerfile) | Многостадийный образ: сборка фронтенда (Node+Vite), установка Python-зависимостей через `uv` и финальный runtime с non-root пользователем и healthcheck. |
| [LICENSE](../LICENSE) | Apache License 2.0. |

## Бэкенд — `src/idea_collector`

Бот, HTTP, SQLite и фоновая разметка LLM.

| Путь | Назначение |
|---|---|
| [src/idea_collector/__init__.py](../src/idea_collector/__init__.py) | Пакет «Telegram idea pocket». |
| [src/idea_collector/__main__.py](../src/idea_collector/__main__.py) | Старт процесса: конфиг, SQLite, LLM, HTTP `0.0.0.0:$PORT`, long polling бота. |
| [src/idea_collector/config.py](../src/idea_collector/config.py) | Чтение окружения; ошибка, если нет обязательных переменных. |
| [src/idea_collector/bot.py](../src/idea_collector/bot.py) | Aiogram: `/start` с кнопкой Mini App, `/csv`, захват текста в чате, кнопка меню «Карман». |
| [src/idea_collector/csv_export.py](../src/idea_collector/csv_export.py) | Байты CSV кармана: колонки `title`/`description` (`label`/`copy`), имя `ideas-YYYY-MM-DD.csv`. |
| [src/idea_collector/web.py](../src/idea_collector/web.py) | Aiohttp: HTML Mini App, `/api/count`, `GET`/`POST /api/ideas`, `DELETE /api/ideas/{id}`, `GET`/`POST /api/sources`, `DELETE /api/sources/{id}`, статика `/assets`. |
| [src/idea_collector/auth.py](../src/idea_collector/auth.py) | Проверка Telegram `initData` (HMAC) и что пользователь — оператор. |
| [src/idea_collector/capture.py](../src/idea_collector/capture.py) | Общий захват: только оператор, insert в SQLite, постановка в очередь разметки. |
| [src/idea_collector/db.py](../src/idea_collector/db.py) | SQLite `IdeaStore` (`ideas`: insert / count / list / get / delete / update_enrichment) и `SourceStore` (`sources`: insert / list / get / delete). |
| [src/idea_collector/enrich.py](../src/idea_collector/enrich.py) | Фоновая задача: LLM → полка, short_name, description в уже сохранённую строку. |
| [src/idea_collector/llm.py](../src/idea_collector/llm.py) | Вызов OpenAI-совместимого `/chat/completions` и разбор JSON извлечения. |
| [src/idea_collector/shelves.py](../src/idea_collector/shelves.py) | Нормализация имени полки, представление идеи для API, группировка списка по полкам. |
| [src/idea_collector/shelves.md](../src/idea_collector/shelves.md) | Правила полок (источник идеи); текст подмешивается в системный промпт LLM. |

## Mini App — `webapp`

Vite + React. Сборка `webapp/dist` отдаётся бэкендом.

| Путь | Назначение |
|---|---|
| [webapp/package.json](../webapp/package.json) | Скрипты `dev` / `build` / `preview` / `test` и зависимости Telegram Mini Apps. |
| [webapp/package-lock.json](../webapp/package-lock.json) | Зафиксированные версии npm. |
| [webapp/vite.config.ts](../webapp/vite.config.ts) | Сборка Vite, плагин React, `base: "/"`, proxy `/api` → `:8080` для `dev` и `preview`. |
| [webapp/tsconfig.json](../webapp/tsconfig.json) | TypeScript для `webapp/src` (JSX, strict). |
| [webapp/tsconfig.node.json](../webapp/tsconfig.node.json) | Project reference на основной tsconfig. |
| [webapp/index.html](../webapp/index.html) | Оболочка Mini App: поле захвата, счётчик, слот списка, стили темы Telegram. |
| [webapp/src/main.tsx](../webapp/src/main.tsx) | Точка входа: SDK Telegram, тема, форма захвата, монтирование `PocketApp`. |
| [webapp/src/pocketApp.tsx](../webapp/src/pocketApp.tsx) | Таббар «Идеи \| Sources»; `IdeaList` остаётся смонтированным при смене вкладки. |
| [webapp/src/sourcesPane.tsx](../webapp/src/sourcesPane.tsx) | Список Sources: оверлей «+», тап открывает url, удаление со строки. |
| [webapp/src/sourceLink.js](../webapp/src/sourceLink.js) | Открытие url источника через SDK `openLink` или `window.open`. |
| [webapp/src/listApp.tsx](../webapp/src/listApp.tsx) | Полки и строки идей; тап открывает карточку с копированием описания и удалением. |
| [webapp/src/listApp.test.tsx](../webapp/src/listApp.test.tsx) | Vitest+jsdom: тап по строке не копирует, тап по телу копирует; delete без призрачной строки. |
| [webapp/src/capture.js](../webapp/src/capture.js) | POST `/api/ideas`, счётчик, статусы «сохранено» / «скопировано» / «не удалось удалить». |
| [webapp/src/ideaCard.js](../webapp/src/ideaCard.js) | Поиск идеи по id, `shelvesWithoutIdea` и сохранение выбранной карточки после перезагрузки списка. |
| [webapp/src/cardChrome.js](../webapp/src/cardChrome.js) | Скрытие полосы захвата на карточке и Telegram BackButton. |
| [webapp/src/vite-env.d.ts](../webapp/src/vite-env.d.ts) | Типы клиента Vite. |

## Тесты — `tests`

| Путь | Назначение |
|---|---|
| [tests/__init__.py](../tests/__init__.py) | Маркер пакета тестов. |
| [tests/conftest.py](../tests/conftest.py) | Фикстуры: тестовый `Config` и `IdeaStore` в памяти. |
| [tests/helpers.py](../tests/helpers.py) | Сборка конфига и подпись `initData` для API-тестов. |
| [tests/test_web.py](../tests/test_web.py) | HTTP API идей и Sources, auth Mini App, захват и `/csv` через бота; subprocess `npm --prefix webapp test`. |
| [tests/test_csv_export.py](../tests/test_csv_export.py) | Юнит-тесты `csv_bytes` / `csv_filename`: quoting, неразмеченные строки, пустой CSV (только заголовок). |
| [tests/test_db.py](../tests/test_db.py) | SQLite `IdeaStore` / `SourceStore` и загрузка конфига. |
| [tests/test_llm.py](../tests/test_llm.py) | Промпт, разбор ответа LLM, очередь Enricher. |
| [tests/test_shelves.py](../tests/test_shelves.py) | Алиасы полок, группировка, поля `label` / `copy`. |
| [tests/capture_probe.mjs](../tests/capture_probe.mjs) | Node-пробы UI-хелперов захвата, карточки и BackButton (без браузера). |

## Планирование (локально, не в git)

Каталоги `_bmad-output/` и `_bmad/` в `.gitignore`. Кратко по смыслу артефактов:

| Путь | Назначение |
|---|---|
| `_bmad-output/specs/spec-telegram-idea-pocket/SPEC.md` | Контракт v1: захват, полки, Mini App. |
| `_bmad-output/specs/spec-telegram-idea-pocket/shelves.md` | Исходные правила полок (копия живёт в `src/.../shelves.md`). |
| `_bmad-output/implementation-artifacts/spec-v1-telegram-idea-pocket.md` | Спека реализации v1 кармана. |
| `_bmad-output/implementation-artifacts/spec-idea-card-delete.md` | Спека карточки идеи. |
| `_bmad-output/implementation-artifacts/deferred-work.md` | Отложенное: CSV-юнит-тесты, click-раннер Mini App, призрачная строка после delete. |
| `_bmad-output/planning-artifacts/ux-designs/ux-idea-collector-2026-09-18/DESIGN.md` | Визуал Mini App (токены Telegram). |
| `_bmad-output/planning-artifacts/ux-designs/ux-idea-collector-2026-09-18/EXPERIENCE.md` | Поведение чата и Mini App. |
| `_bmad-output/forge/telegram-idea-pocket/forged-idea.md` | Закалённая идея продукта. |
| `_bmad-output/forge/next-slice-backlog/forged-idea.md` | Следующий срез: карточка, delete, `/csv`, Sources. |
