# idea-collector

Карман идей для одного оператора: Telegram-бот и Mini App. Сырой текст пишется в чат или в поле WebApp; LLM позже заполняет полку (источник), короткое имя и описание.

## Возможности

- Захват текста в Telegram-чате (отвечает числом сохранённых идей)
- Команда `/csv` в чате оператора: непустой карман → файл `ideas-YYYY-MM-DD.csv` (колонки `title` / `description`); пустой → `В кармане нет идей`. Sources в файл не входят
- Mini App «Карман»: вкладки «Идеи | Sources», поле ввода, счётчик, полки и карточка идеи с копированием описания
- Фоновая разметка через OpenAI-совместимый `/chat/completions`
- SQLite-хранилище
- Доступ только у `OPERATOR_TELEGRAM_ID`; Mini App проверяет Telegram `initData`

## Требования

- Python **3.12+** (см. `.python-version`)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js и npm (сборка Mini App)
- Бот в [@BotFather](https://t.me/BotFather) и публичный **HTTPS**-URL для Mini App

Процесс читает переменные из окружения. Файл `.env` сам не подхватывается: его нужно передать через `uv run --env-file`.

## Быстрый старт

```bash
git clone https://github.com/lifefucky/idea-collector.git
cd idea-collector

cp .env.example .env
# заполните BOT_TOKEN, OPERATOR_TELEGRAM_ID, OPENAI_* и PUBLIC_BASE_URL

uv sync

npm --prefix webapp install
npm --prefix webapp run build

uv run --env-file .env idea-collector
```

Сервер слушает `0.0.0.0:$PORT` (по умолчанию **8080**) и отдаёт `webapp/dist`. Бот работает long polling.

Перед Mini App нужен TLS-прокси или туннель на `PORT`, чтобы `PUBLIC_BASE_URL` был публичным **HTTPS**. Telegram не откроет Mini App по HTTP.

После правок фронтенда снова соберите Mini App и перезапустите процесс: статика `/assets` монтируется при старте.

```bash
npm --prefix webapp run build
uv run --env-file .env idea-collector
```

## BotFather

1. Создайте бота и запишите токен в `BOT_TOKEN`.
2. Укажите свой Telegram user id в `OPERATOR_TELEGRAM_ID` — сохранять идеи может только этот аккаунт.
3. Направьте Mini App / Menu Button на `PUBLIC_BASE_URL` (HTTPS-origin, с которого отдаётся `/`). При старте, если URL задан, бот сам ставит кнопку меню «Карман».

В чате `/start` открывает ту же кнопку. `/csv` отдаёт карман файлом (или сообщает, что идей нет). Любой не-командный текст от оператора сохраняется как идея.

## Переменные окружения

Шаблон: [`.env.example`](.env.example).

| Переменная | Обязательная | По умолчанию | Назначение |
|---|---|---|---|
| `BOT_TOKEN` | да | — | Токен бота |
| `OPERATOR_TELEGRAM_ID` | да | — | Числовой Telegram id оператора |
| `OPENAI_BASE_URL` | да | — | База OpenAI-совместимого API (пример: `https://api.openai.com/v1`) |
| `OPENAI_API_KEY` | да | — | Ключ API |
| `OPENAI_MODEL` | да | — | Модель для разметки |
| `PUBLIC_BASE_URL` | нет | пусто | HTTPS-origin Mini App; без него кнопка WebApp не ставится |
| `SQLITE_PATH` | нет | `ideas.db` | Путь к SQLite |
| `PORT` | нет | `8080` | Порт HTTP |

При отсутствии обязательных переменных процесс сразу выходит с ошибкой `Missing required environment: …`.

## HTTP API

Mini App ходит на эти маршруты. JSON API требуют заголовок `Authorization: tma <initData>` (или `X-Telegram-Init-Data`) оператора.

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/` | HTML Mini App, в счётчик подставляется число идей |
| `GET` | `/api/count` | `{ "count": N }` |
| `GET` | `/api/ideas` | `{ "count", "shelves" }` |
| `POST` | `/api/ideas` | Тело JSON `{ "text": "…" }` или form-field `text` |
| `DELETE` | `/api/ideas/{id}` | `{ "count": N }` оставшихся идей |
| `GET` | `/api/sources` | `{ "sources": [{id, title, url}] }` |
| `POST` | `/api/sources` | Тело JSON `{ "title": "…", "url": "…" }` |
| `DELETE` | `/api/sources/{id}` | `{ "ok": true }` |
| `GET` | `/assets/…` | Сборка Vite (`webapp/dist/assets`) |

## Разработка

```bash
uv sync
uv run pytest
uv run ruff check src tests
```

`uv run pytest` запускает `npm --prefix webapp test` и требует `npm --prefix webapp install`.

Локальный Vite проксирует `/api` на `http://127.0.0.1:8080` (`dev` и `preview`). Авторизация API не ослабляется.

```bash
npm --prefix webapp install
npm --prefix webapp run preview
```

Рядом должен работать `uv run --env-file .env idea-collector`. Без Telegram `initData` `/api/*` отвечает 401.

Для полного контура (бот + Mini App) нужна сборка `webapp` и `uv run --env-file .env idea-collector`, а не `vite dev`.

## Структура

```
src/idea_collector/   # бот, HTTP, SQLite, LLM
webapp/               # Mini App (Vite + React)
tests/                # pytest
.env.example          # шаблон окружения
```

## Стек

- Python 3.12, [uv](https://docs.astral.sh/uv/), aiogram 3, aiohttp, httpx
- SQLite
- Vite 6, React 18, `@telegram-apps/sdk`, `@telegram-apps/telegram-ui`

## Лицензия

[Apache License 2.0](LICENSE)
