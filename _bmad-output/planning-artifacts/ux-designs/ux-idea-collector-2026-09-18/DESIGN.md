---
name: Личный карман идей
description: Telegram Mini App личного кармана идей. Визуал наследует тему Telegram, без отдельного бренда и без ЛК.
status: final
updated: 2026-09-18
colors:
  surface-base: '#FFFFFF'
  surface-raised: '#EFEFF3'
  ink-primary: '#000000'
  ink-secondary: '#999999'
  accent: '#2481CC'
  accent-foreground: '#FFFFFF'
  destructive: '#FF3B30'
  border-hairline: '#E5E5EA'
  surface-base-dark: '#18222D'
  surface-raised-dark: '#232E3A'
  ink-primary-dark: '#FFFFFF'
  ink-secondary-dark: '#8B9AAB'
  accent-dark: '#6AB2F2'
  accent-foreground-dark: '#FFFFFF'
  destructive-dark: '#FF6B61'
  border-hairline-dark: '#2B3A48'
typography:
  title:
    fontFamily: system-ui
    fontSize: 17px
    fontWeight: '600'
    lineHeight: '1.3'
    note: 'Telegram Mini App — системный UI-шрифт, заголовок полки'
  body:
    fontFamily: system-ui
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.4'
    note: 'Telegram Mini App — системный UI-шрифт, текст идеи и поле захвата'
  meta:
    fontFamily: system-ui
    fontSize: 13px
    fontWeight: '400'
    lineHeight: '1.3'
    note: 'Telegram Mini App — системный UI-шрифт, счётчик и вторичные подписи'
rounded:
  sm: 8px
  md: 12px
spacing:
  '1': 4px
  '2': 8px
  '3': 12px
  '4': 16px
  '5': 24px
components:
  capture-field:
    background: '{colors.surface-raised}'
    foreground: '{colors.ink-primary}'
    radius: '{rounded.md}'
  ideas-counter:
    foreground: '{colors.ink-secondary}'
  shelf-group:
    background: '{colors.surface-base}'
    foreground: '{colors.ink-primary}'
  idea-row:
    background: '{colors.surface-base}'
    foreground: '{colors.ink-primary}'
---

## Brand & Style

Личный карман идей — утилита одного человека внутри Telegram. Отдельного бренда нет: Mini App носит тему Telegram. Нет логотипа, маркетингового голоса и кастомных иллюстраций.

Это список, из которого забирают текст, а не лента вдохновения. Нет ЛК, онбординга и декоративного хрома. Иерархия экрана: поле захвата, счётчик, полки.

## Colors

Цвета не брендовые. Токены — дефолтная светлая и тёмная тема Telegram (`themeParams`). В рантайме: `bg_color`, `secondary_bg_color`, `text_color`, `hint_color`, `button_color` / `link_color`, `button_text_color`, `destructive_text_color`. Hex в этом файле — фолбэк, когда themeParams недоступны.

- **surface-base** (`{colors.surface-base}` / `{colors.surface-base-dark}`) — холст Mini App. `bg_color`.
- **surface-raised** (`{colors.surface-raised}` / `{colors.surface-raised-dark}`) — поле захвата. `secondary_bg_color`.
- **ink-primary** (`{colors.ink-primary}` / `{colors.ink-primary-dark}`) — текст идеи, заголовок полки, ввод. `text_color`.
- **ink-secondary** (`{colors.ink-secondary}` / `{colors.ink-secondary-dark}`) — счётчик. `hint_color`.
- **accent** (`{colors.accent}` / `{colors.accent-dark}`) — фокус поля и ссылки Telegram. `button_color` / `link_color`. Полки цветом не кодируются.
- **destructive** (`{colors.destructive}` / `{colors.destructive-dark}`) — ошибка отправки или копирования. Не статус идеи: в v1 статуса нет.

Не использовать: палитру полок, бейджи «обработано», градиенты, отдельную бренд-кнопку вне Telegram.

Контраст load-bearing: `{colors.ink-primary}` на `{colors.surface-base}`. `{colors.ink-secondary}` на `{colors.surface-base}` у счётчика — вторичный текст; смысл несут поле и список рядом.

## Typography

Системный шрифт Telegram Mini App (`system-ui`). `{typography.title}` — имя полки. `{typography.body}` — текст идеи и поле захвата. `{typography.meta}` — счётчик. Без display-serif и без кастомных файлов шрифтов. Динамический размер Telegram/OS обязателен: поле и строки идей остаются читаемыми, контролы не обрезаются.

## Layout & Spacing

Сетка `{spacing.1}` / `{spacing.2}` / `{spacing.3}` / `{spacing.4}` / `{spacing.5}`. Одна колонка. Сверху полоса захвата: `capture-field` и `ideas-counter`. Ниже скроллируемый список `shelf-group`. Горизонтальные поля Mini App — `{spacing.4}`. Модалок нет.

Чат бота — нативный Telegram, этим файлом не верстается.

## Elevation & Depth

Иерархия без теней. Поле захвата — тон `{colors.surface-raised}`. Полки и строки — `{colors.surface-base}`, разделение `{colors.border-hairline}` или `{spacing.2}`. Карточных теней нет.

## Shapes

`{rounded.sm}` у строки идеи и хедера полки. `{rounded.md}` у поля захвата. Без пилюль и без кругов как декора. Радиусы как у контролов Telegram.

## Components

- **capture-field** — поле сверху, высота растёт с текстом. Фон `{colors.surface-raised}`, текст `{colors.ink-primary}`, радиус `{rounded.md}`. Фокус — каретка и обводка `{colors.accent}`. Плейсхолдер `{colors.ink-secondary}`, строка «Идея». Без логотипа слева.
- **ideas-counter** — число всех сохранённых идей рядом с полем. `{typography.meta}`, `{colors.ink-secondary}`. Цифра, не бейдж и не акцент-заливка.
- **shelf-group** — хедер с именем полки (`{typography.title}`), тап раскрывает. Свёрнутый: только имя. Раскрытый: список `idea-row`. Пустые полки не рисуются.
- **idea-row** — текст идеи `{typography.body}` на `{colors.surface-base}`. Тап копирует. Без превью-карточки и без цветной метки полки на строке.

## Do's and Don'ts

| Do | Don't |
|---|---|
| Носить тему Telegram (`themeParams`) | Вводить отдельную бренд-палитру |
| `{colors.accent}` только на фокус и ссылку | Красить полки в разные цвета |
| Счётчик вторичным `{colors.ink-secondary}` | Делать счётчик бейджем, стриком или CTA |
| Список как инструмент извлечения | Карточки вдохновения, аватарки, онбординг |
| `{rounded.sm}` / `{rounded.md}` | Пилюли и крупные радиусы consumer-app |
