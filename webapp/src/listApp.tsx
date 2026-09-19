import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Accordion, AppRoot, Cell, IconButton, Section, Tappable } from "@telegram-apps/telegram-ui";
import { Icon24ChevronLeft } from "@telegram-apps/telegram-ui/dist/icons/24/chevron_left";
import { selectedAfterLoad } from "./ideaCard.js";

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
  appearance: "light" | "dark";
  onCardOpenChange: (open: boolean, close: () => void) => void;
};

export function IdeaList({
  getInitData,
  onCopy,
  appearance,
  onCardOpenChange,
}: IdeaListProps) {
  const [shelves, setShelves] = useState<Shelf[] | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [selectedIdea, setSelectedIdea] = useState<Idea | null>(null);
  const ignoreBodyCopy = useRef(false);
  const ignoreBodyCopyTimer = useRef<ReturnType<typeof window.setTimeout> | undefined>(
    undefined,
  );

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
        return;
      }
      const body = (await response.json()) as IdeasResponse;
      const nextShelves = body.shelves ?? [];
      setShelves(nextShelves);
      setSelectedIdea((current) => selectedAfterLoad(current, true, nextShelves));
    } catch {
      /* keep current shelves (null = skeleton) and the open card */
    }
  }, [getInitData]);

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

  return (
    <AppRoot appearance={appearance} platform="ios">
      {selectedIdea ? (
        <div className="idea-card">
          <header className="idea-card-header">
            <IconButton
              mode="plain"
              size="l"
              className="idea-card-back"
              aria-label="Назад"
              onClick={closeCard}
            >
              <Icon24ChevronLeft />
            </IconButton>
            <span className="idea-card-label">{selectedIdea.label}</span>
          </header>
          <Section>
            <Tappable
              Component="div"
              role="button"
              tabIndex={0}
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
            </Tappable>
          </Section>
        </div>
      ) : (
        <>
          {shelves === null ? <div className="list-skeleton" aria-hidden="true" /> : null}
          {namedShelves.map((shelf) => (
            <Accordion
              key={shelf.name}
              expanded={Boolean(expanded[shelf.name])}
              onChange={(value) =>
                setExpanded((current) => ({ ...current, [shelf.name]: value }))
              }
            >
              <Accordion.Summary>
                <span className="shelf-title">{shelf.name}</span>
              </Accordion.Summary>
              <Accordion.Content>
                <Section>
                  {shelf.ideas.map((idea) => (
                    <Cell
                      key={idea.id}
                      multiline
                      className="idea-row"
                      onClick={() => openCard(idea)}
                      onContextMenu={() => undefined}
                    >
                      {idea.label}
                    </Cell>
                  ))}
                </Section>
              </Accordion.Content>
            </Accordion>
          ))}
        </>
      )}
    </AppRoot>
  );
}
