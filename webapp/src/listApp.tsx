import { useCallback, useEffect, useMemo, useState } from "react";
import { Accordion, AppRoot, Cell, Section } from "@telegram-apps/telegram-ui";

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
};

export function IdeaList({ getInitData, onCopy, appearance }: IdeaListProps) {
  const [shelves, setShelves] = useState<Shelf[] | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const load = useCallback(async () => {
    try {
      const response = await fetch("/api/ideas", {
        headers: { Authorization: `tma ${getInitData()}` },
      });
      if (!response.ok) {
        return;
      }
      const body = (await response.json()) as IdeasResponse;
      setShelves(body.shelves ?? []);
    } catch {
      /* keep current shelves (null = skeleton) */
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

  const namedShelves = useMemo(
    () => (shelves ?? []).filter((shelf) => shelf.ideas.length > 0),
    [shelves],
  );

  return (
    <AppRoot appearance={appearance} platform="ios">
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
                  onClick={() => onCopy(idea.copy)}
                  onContextMenu={() => undefined}
                >
                  {idea.label}
                </Cell>
              ))}
            </Section>
          </Accordion.Content>
        </Accordion>
      ))}
    </AppRoot>
  );
}

