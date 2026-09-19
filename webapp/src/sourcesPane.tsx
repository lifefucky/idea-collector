import { useCallback, useEffect, useRef, useState } from "react";
import { openLink } from "@telegram-apps/sdk";
import { Button, Cell, Input, Modal, Section } from "@telegram-apps/telegram-ui";
import { sourceDeleteOutcome } from "./capture.js";
import { openSourceUrl } from "./sourceLink.js";

export const OPEN_ERROR = "Не удалось открыть";

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
      <Button
        type="button"
        mode="plain"
        size="l"
        className="sources-add"
        onClick={() => onOverlayOpenChange(true)}
      >
        +
      </Button>
      {sources.length > 0 ? (
        <Section>
          {sources.map((source) => (
            <Cell
              key={source.id}
              multiline
              className="source-row"
              onClick={() => {
                try {
                  openSourceUrl(source.url, openLink);
                } catch {
                  onOpenError();
                }
              }}
              after={
                <Button
                  type="button"
                  mode="plain"
                  size="l"
                  className="source-row-delete"
                  onClick={(event) => {
                    event.stopPropagation();
                    void deleteSource(source.id);
                  }}
                >
                  Удалить
                </Button>
              }
            >
              {source.title}
            </Cell>
          ))}
        </Section>
      ) : null}
      <Modal
        className="sources-overlay"
        open={overlayOpen}
        onOpenChange={onOverlayOpenChange}
      >
        <form
          className="sources-overlay-form"
          onSubmit={(event) => {
            event.preventDefault();
          }}
        >
          <Input
            placeholder="Название"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <Input
            placeholder="Ссылка"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
          />
          <Button
            type="button"
            size="l"
            className="sources-overlay-save"
            onClick={() => {
              void saveSource();
            }}
          >
            Сохранить
          </Button>
          <Button
            type="button"
            mode="plain"
            size="l"
            className="sources-overlay-cancel"
            onClick={() => onOverlayOpenChange(false)}
          >
            Отмена
          </Button>
        </form>
      </Modal>
    </div>
  );
}
