# idea-collector

Single-operator Telegram bot and Mini App for parking ideas. Dump raw text in chat or in the WebApp field; an LLM later fills source, short name, and description.

## Setup

1. Copy `.env.example` to `.env` and fill in the values.
2. Build the Mini App:

   ```bash
   npm --prefix webapp install
   npm --prefix webapp run build
   ```

3. Start polling and the web server (serves `webapp/dist`):

   ```bash
   uv run idea-collector
   ```

The bot uses long polling. Put a TLS reverse proxy or tunnel in front of `PORT` so `PUBLIC_BASE_URL` is a public **HTTPS** URL. Telegram Mini Apps will not load over plain HTTP.

## BotFather

1. Create a bot and put its token in `BOT_TOKEN`.
2. Set your user id in `OPERATOR_TELEGRAM_ID` (only that account can save ideas).
3. Point the Mini App / menu button at `PUBLIC_BASE_URL` (the HTTPS origin that serves `/`).

## Environment

See `.env.example`. The process exits on boot if `BOT_TOKEN`, `OPERATOR_TELEGRAM_ID`, `OPENAI_BASE_URL`, `OPENAI_API_KEY`, or `OPENAI_MODEL` is missing.
