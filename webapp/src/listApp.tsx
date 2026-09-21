import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Bookmark, ChevronLeft, Lightbulb } from "lucide-react";
import { deleteFetchOutcome } from "./capture.js";
import {
  cardTone,
  relatedIdeas,
  selectedAfterLoad,
  shelfNameOf,
  shelvesWithoutIdea,
  sourceAbbrev,
} from "./ideaCard.js";

type Idea = {
  id: number;
  label: string;
  copy: string;
};

type Shelf = {
  name: string;
  ideas: Idea[];
};

type IdeasResponse = {
  count: number;
  shelves: Shelf[];
};

type IdeaListProps = {
  getInitData: () => string;
  onCopy: (text: string) => void;
  onCount: (count: number) => void;
  onDeleteClear: () => void;
  onDeleteError: () => void;
  appearance: "light" | "dark";
  onCardOpenChange: (open: boolean, close: () => void) => void;
};

function IdeaToneCard({
  idea,
  shelf,
  onOpen,
}: {
  idea: Idea;
  shelf: string;
  onOpen: (idea: Idea) => void;
}) {
  return (
    <article className={`idea-tone-card tone-${cardTone(idea.id)}`}>
      <button
        type="button"
        className="idea-row"
        onClick={() => onOpen(idea)}
        onContextMenu={() => undefined}
      >
        {idea.label}
      </button>
      <div className="idea-tone-meta">
        <Bookmark size={14} />
        {shelf}
      </div>
      <div className="idea-tone-cta">
        <span className="idea-open-badge" data-stub="no-backend">
          Открыть
        </span>
      </div>
    </article>
  );
}

export function IdeaList({
  getInitData,
  onCopy,
  onCount,
  onDeleteClear,
  onDeleteError,
  appearance: _appearance,
  onCardOpenChange,
}: IdeaListProps) {
  const [shelves, setShelves] = useState<Shelf[] | null>(null);
  const [filter, setFilter] = useState<string | null>(null);
  const [selectedIdea, setSelectedIdea] = useState<Idea | null>(null);
  const ignoreBodyCopy = useRef(false);
  const ignoreBodyCopyTimer = useRef<ReturnType<typeof window.setTimeout> | undefined>(
    undefined,
  );
  const deleteInFlight = useRef(false);

  const clearIgnoreBodyCopy = useCallback(() => {
    if (ignoreBodyCopyTimer.current !== undefined) {
      window.clearTimeout(ignoreBodyCopyTimer.current);
      ignoreBodyCopyTimer.current = undefined;
    }
    ignoreBodyCopy.current = false;
  }, []);

  const closeCard = useCallback(() => {
    clearIgnoreBodyCopy();
    setSelectedIdea(null);
  }, [clearIgnoreBodyCopy]);

  const openCard = useCallback((idea: Idea) => {
    ignoreBodyCopy.current = true;
    if (ignoreBodyCopyTimer.current !== undefined) {
      window.clearTimeout(ignoreBodyCopyTimer.current);
    }
    ignoreBodyCopyTimer.current = window.setTimeout(() => {
      ignoreBodyCopy.current = false;
      ignoreBodyCopyTimer.current = undefined;
    }, 300);
    setSelectedIdea(idea);
  }, []);

  const load = useCallback(async () => {
    try {
      const response = await fetch("/api/ideas", {
        headers: { Authorization: `tma ${getInitData()}` },
      });
      if (!response.ok) {
        setSelectedIdea((current) => selectedAfterLoad(current, false, []));
        // keep current shelves (null = skeleton) and the open card
        setShelves((current) => current ?? []);
        return;
      }
      const body = (await response.json()) as IdeasResponse;
      const nextShelves = body.shelves ?? [];
      if (typeof body.count === "number") {
        onCount(body.count);
      }
      setShelves(nextShelves);
      setSelectedIdea((current) => selectedAfterLoad(current, true, nextShelves));
    } catch {
      setShelves((current) => current ?? []);
    }
  }, [getInitData, onCount]);

  const deleteSelected = useCallback(async () => {
    if (deleteInFlight.current || selectedIdea === null) {
      return;
    }
    deleteInFlight.current = true;
    try {
      let outcome;
      try {
        const response = await fetch(`/api/ideas/${selectedIdea.id}`, {
          method: "DELETE",
          headers: { Authorization: `tma ${getInitData()}` },
        });
        outcome = deleteFetchOutcome(response);
        if (outcome.count) {
          try {
            const body = (await response.json()) as { count?: number };
            if (typeof body.count === "number") {
              onCount(body.count);
            }
          } catch {
            /* still close so the operator is not on a missing card */
          }
        }
      } catch {
        outcome = deleteFetchOutcome(null);
      }
      if (outcome.close) {
        const deletedId = selectedIdea.id;
        setShelves((current) => shelvesWithoutIdea(current ?? [], deletedId));
        onDeleteClear();
        setSelectedIdea((current) => (current?.id === deletedId ? null : current));
        await load();
        return;
      }
      onDeleteError();
    } finally {
      deleteInFlight.current = false;
    }
  }, [getInitData, load, onCount, onDeleteClear, onDeleteError, selectedIdea]);

  useEffect(() => {
    void load();
    const onChanged = () => {
      void load();
    };
    window.addEventListener("ideas:changed", onChanged);
    return () => window.removeEventListener("ideas:changed", onChanged);
  }, [load]);

  const cardOpen = selectedIdea !== null;

  useLayoutEffect(() => {
    onCardOpenChange(cardOpen, closeCard);
  }, [cardOpen, closeCard, onCardOpenChange]);

  useEffect(() => {
    if (!cardOpen) {
      clearIgnoreBodyCopy();
    }
  }, [cardOpen, clearIgnoreBodyCopy]);

  useEffect(() => {
    return () => {
      clearIgnoreBodyCopy();
    };
  }, [clearIgnoreBodyCopy]);

  const namedShelves = useMemo(
    () => (shelves ?? []).filter((shelf) => shelf.ideas.length > 0),
    [shelves],
  );
  useEffect(() => {
    if (filter === null) {
      return;
    }
    if (!namedShelves.some((shelf) => shelf.name === filter)) {
      setFilter(null);
    }
  }, [filter, namedShelves]);
  const ideaCount = useMemo(
    () => (shelves ?? []).reduce((sum, shelf) => sum + shelf.ideas.length, 0),
    [shelves],
  );
  const visibleShelves = useMemo(
    () => namedShelves.filter((shelf) => (filter === null ? true : shelf.name === filter)),
    [filter, namedShelves],
  );
  const related = selectedIdea ? relatedIdeas(shelves ?? [], selectedIdea.id) : [];
  const selectedShelf = selectedIdea ? shelfNameOf(shelves ?? [], selectedIdea.id) : "";

  return (
    <>
      {selectedIdea ? (
        <div className="idea-card">
          <header className="idea-card-header">
            <button
              type="button"
              className="idea-card-back"
              aria-label="Назад"
              onClick={closeCard}
            >
              <ChevronLeft size={20} />
            </button>
            <span className="idea-card-label" title={selectedIdea.label}>
              {selectedIdea.label}
            </span>
          </header>
          <button
            type="button"
            className="idea-card-body"
            onClick={() => {
              if (ignoreBodyCopy.current) {
                return;
              }
              const selection = window.getSelection();
              if (selection && selection.toString()) {
                return;
              }
              onCopy(selectedIdea.copy);
            }}
            onContextMenu={() => undefined}
          >
            {selectedIdea.copy}
          </button>
          <div className="idea-card-meta">
            <span className="idea-card-meta-item">
              <Bookmark size={16} />
              {selectedShelf}
            </span>
            <span className="idea-card-meta-split">|</span>
            <span className="idea-card-meta-item" data-stub="no-backend">
              <Lightbulb size={16} />
              идея
            </span>
          </div>
          <div className="idea-card-delete-row">
            <button
              type="button"
              className="idea-card-delete"
              onClick={() => {
                void deleteSelected();
              }}
            >
              Удалить
            </button>
          </div>
          {related.length > 0 ? (
            <div className="idea-related">
              {related.map((item) => (
                <IdeaToneCard
                  key={item.id}
                  idea={item}
                  shelf={shelfNameOf(shelves ?? [], item.id)}
                  onOpen={openCard}
                />
              ))}
            </div>
          ) : null}
        </div>
      ) : (
        <>
          {shelves === null ? <div className="list-skeleton" aria-hidden="true" /> : null}
          {shelves !== null ? (
            <div className="shelf-chips no-scrollbar">
              <button
                type="button"
                className={`shelf-chip${filter === null ? " selected" : ""}`}
                aria-pressed={filter === null}
                onClick={() => setFilter(null)}
              >
                <span className="shelf-chip-label">Все</span>
                <span className="shelf-chip-hint">{ideaCount}</span>
              </button>
              {namedShelves.map((shelf) => (
                <button
                  key={shelf.name}
                  type="button"
                  className={`shelf-chip${filter === shelf.name ? " selected" : ""}`}
                  aria-label={shelf.name}
                  aria-pressed={filter === shelf.name}
                  onClick={() =>
                    setFilter((current) => (current === shelf.name ? null : shelf.name))
                  }
                >
                  <span className="shelf-chip-label">{sourceAbbrev(shelf.name)}</span>
                  <span className="shelf-chip-hint">{shelf.ideas.length}</span>
                </button>
              ))}
            </div>
          ) : null}
          <div className="shelf-stack">
            {visibleShelves.flatMap((shelf) =>
              shelf.ideas.map((idea) => (
                <IdeaToneCard
                  key={idea.id}
                  idea={idea}
                  shelf={shelf.name}
                  onOpen={openCard}
                />
              )),
            )}
          </div>
        </>
      )}
    </>
  );
}
