import { useCallback, useEffect, useRef, useState } from "react";
import { openLink } from "@telegram-apps/sdk";
import { Modal } from "@telegram-apps/telegram-ui";
import { ChevronLeft, ExternalLink, Trash2 } from "lucide-react";
import { sourceDeleteOutcome } from "./capture.js";
import { cardTone, sourceAbbrev } from "./ideaCard.js";
import { openSourceUrl } from "./sourceLink.js";

export const OPEN_ERROR = "Не удалось открыть";

const sourceSuggestions = [
  { title: "Product Hunt", url: "https://www.producthunt.com" },
  { title: "YC Library", url: "https://www.ycombinator.com/library" },
  { title: "Product Radar", url: "https://productradar.so" },
  { title: "App Store", url: "https://apps.apple.com" },
];

type Source = {
  id: number;
  title: string;
  url: string;
};

type SourcesResponse = {
  sources: Source[];
};

type SourcesPaneProps = {
  getInitData: () => string;
  overlayOpen: boolean;
  onOverlayOpenChange: (open: boolean) => void;
  onSaveError: () => void;
  onDeleteError: () => void;
  onOpenError: () => void;
};

export function SourcesPane({
  getInitData,
  overlayOpen,
  onOverlayOpenChange,
  onSaveError,
  onDeleteError,
  onOpenError,
}: SourcesPaneProps) {
  const [sources, setSources] = useState<Source[]>([]);
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const saveInFlight = useRef(false);
  const deleteInFlight = useRef(false);

  const load = useCallback(async () => {
    try {
      const response = await fetch("/api/sources", {
        headers: { Authorization: `tma ${getInitData()}` },
      });
      if (!response.ok) {
        return;
      }
      const body = (await response.json()) as SourcesResponse;
      setSources(body.sources ?? []);
    } catch {
      /* keep current rows */
    }
  }, [getInitData]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!overlayOpen) {
      setTitle("");
      setUrl("");
    }
  }, [overlayOpen]);

  const saveSource = useCallback(async () => {
    if (saveInFlight.current) {
      return;
    }
    const nextTitle = title.trim();
    const nextUrl = url.trim();
    if (!nextTitle || !nextUrl) {
      return;
    }
    saveInFlight.current = true;
    try {
      const response = await fetch("/api/sources", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `tma ${getInitData()}`,
        },
        body: JSON.stringify({ title: nextTitle, url: nextUrl }),
      });
      if (!response.ok) {
        onSaveError();
        return;
      }
      const created = (await response.json()) as Source;
      setSources((current) => [...current, created]);
      onOverlayOpenChange(false);
      await load();
    } catch {
      onSaveError();
    } finally {
      saveInFlight.current = false;
    }
  }, [getInitData, load, onOverlayOpenChange, onSaveError, title, url]);

  const deleteSource = useCallback(
    async (sourceId: number) => {
      if (deleteInFlight.current) {
        return;
      }
      deleteInFlight.current = true;
      try {
        let outcome;
        try {
          const response = await fetch(`/api/sources/${sourceId}`, {
            method: "DELETE",
            headers: { Authorization: `tma ${getInitData()}` },
          });
          outcome = sourceDeleteOutcome(response);
        } catch {
          outcome = sourceDeleteOutcome(null);
        }
        if (outcome.remove) {
          setSources((current) => current.filter((item) => item.id !== sourceId));
          return;
        }
        onDeleteError();
      } finally {
        deleteInFlight.current = false;
      }
    },
    [getInitData, onDeleteError],
  );

  return (
    <div className="sources-pane">
      <div className="sources-header">
        <button
          type="button"
          className="sources-add"
          onClick={() => onOverlayOpenChange(true)}
        >
          + Источник
        </button>
        <span className="sources-count" aria-label={`Источников: ${sources.length}`}>
          {sources.length}
        </span>
      </div>
      <div className="sources-heading">
        <h1>Sources</h1>
        <span>ссылки</span>
      </div>
      {sources.length > 0 ? (
        <div className="source-abbrev-row no-scrollbar">
          {sources.map((source) => (
            <button
              key={source.id}
              type="button"
              className="shelf-chip"
              onClick={() => {
                try {
                  openSourceUrl(source.url, openLink);
                } catch {
                  onOpenError();
                }
              }}
            >
              <span className="shelf-chip-label">{sourceAbbrev(source.title)}</span>
              <span className="shelf-chip-hint">полка</span>
            </button>
          ))}
        </div>
      ) : null}
      <div className="source-stack">
        {sources.map((source) => (
          <article
            key={source.id}
            className={`source-card tone-${cardTone(source.id)}`}
          >
            <div className="source-card-top">
              <button
                type="button"
                className="source-row idea-row"
                onClick={() => {
                  try {
                    openSourceUrl(source.url, openLink);
                  } catch {
                    onOpenError();
                  }
                }}
              >
                {source.title}
              </button>
              <button
                type="button"
                className="source-abbrev"
                aria-label="Открыть ссылку"
                onClick={() => {
                  try {
                    openSourceUrl(source.url, openLink);
                  } catch {
                    onOpenError();
                  }
                }}
              >
                <ExternalLink size={15} />
              </button>
            </div>
            <p className="source-url">{source.url}</p>
            <div className="source-card-footer">
              <span className="source-open-hint">тап открывает</span>
              <button
                type="button"
                className="source-row-delete"
                onClick={(event) => {
                  event.stopPropagation();
                  void deleteSource(source.id);
                }}
              >
                <Trash2 size={12} />
                Удалить
              </button>
            </div>
          </article>
        ))}
      </div>
      <Modal
        className="sources-overlay"
        open={overlayOpen}
        onOpenChange={onOverlayOpenChange}
      >
        <div className="sources-overlay-chrome">
          <button
            type="button"
            className="sources-overlay-back"
            aria-label="Назад"
            onClick={() => onOverlayOpenChange(false)}
          >
            <ChevronLeft size={20} />
          </button>
          <button
            type="button"
            className="sources-overlay-cancel"
            onClick={() => onOverlayOpenChange(false)}
          >
            Отмена
          </button>
        </div>
        <form
          className="sources-overlay-form"
          onSubmit={(event) => {
            event.preventDefault();
          }}
        >
          <h2 className="sources-overlay-title">Hey, новый источник</h2>
          <label>
            Название
            <input
              placeholder="Название"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>
          <label>
            Ссылка
            <input
              placeholder="Ссылка"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
            />
          </label>
          <p className="source-suggest-label">Подсказка</p>
          <div className="source-suggest-row no-scrollbar">
            {sourceSuggestions.map((item) => (
              <button
                key={item.title}
                type="button"
                className="source-suggest-chip"
                data-stub="no-backend"
                onClick={() => {
                  setTitle(item.title);
                  setUrl(item.url);
                }}
              >
                <span>{sourceAbbrev(item.title)}</span>
                <span>полка</span>
              </button>
            ))}
          </div>
          <button
            type="button"
            className="sources-overlay-save"
            onClick={() => {
              void saveSource();
            }}
          >
            Сохранить
          </button>
        </form>
      </Modal>
    </div>
  );
}
