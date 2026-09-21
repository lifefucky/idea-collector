import { useCallback, useLayoutEffect, useRef, useState } from "react";
import { AppRoot } from "@telegram-apps/telegram-ui";
import { Home, MessageCircle, Settings } from "lucide-react";
import { setCaptureStripHidden } from "./cardChrome.js";
import { IdeaList } from "./listApp";
import { SourcesPane } from "./sourcesPane";

type TabId = "ideas" | "sources";

type PocketAppProps = {
  getInitData: () => string;
  onCopy: (text: string) => void;
  onCount: (count: number) => void;
  onDeleteClear: () => void;
  onDeleteError: () => void;
  appearance: "light" | "dark";
  onCardOpenChange: (open: boolean, close: () => void) => void;
  onSaveError: () => void;
  onOpenError: () => void;
};

function BottomNav({
  tab,
  onIdeas,
  onSources,
}: {
  tab: TabId;
  onIdeas: () => void;
  onSources: () => void;
}) {
  const onIdeasTab = tab === "ideas";
  const onSourcesTab = tab === "sources";
  return (
    <nav className="bottom-nav" aria-label="Вкладки кармана">
      <button
        type="button"
        className="bottom-nav-item"
        aria-label="Идеи"
        aria-current={onIdeasTab ? "page" : undefined}
        onClick={onIdeas}
      >
        <Home size={18} strokeWidth={onIdeasTab ? 2.4 : 2} />
      </button>
      <button
        type="button"
        className="bottom-nav-item"
        aria-label="Sources"
        aria-current={onSourcesTab ? "page" : undefined}
        onClick={onSources}
      >
        <Settings size={18} strokeWidth={onSourcesTab ? 2.4 : 2} />
      </button>
      <button
        type="button"
        className="bottom-nav-item bottom-nav-stub"
        aria-label="Лента"
        aria-disabled="true"
        tabIndex={-1}
        data-stub="no-backend"
        style={{ pointerEvents: "none" }}
      >
        <MessageCircle size={18} strokeWidth={2} />
      </button>
    </nav>
  );
}

export function PocketApp({
  getInitData,
  onCopy,
  onCount,
  onDeleteClear,
  onDeleteError,
  appearance: _appearance,
  onCardOpenChange,
  onSaveError,
  onOpenError,
}: PocketAppProps) {
  const [tab, setTab] = useState<TabId>("ideas");
  const [overlayOpen, setOverlayOpen] = useState(false);
  const [cardOpen, setCardOpen] = useState(false);
  const closeCardRef = useRef(() => {});

  const cancelOverlay = useCallback(() => {
    setOverlayOpen(false);
  }, []);

  const reportCard = useCallback((open: boolean, close: () => void) => {
    closeCardRef.current = close;
    setCardOpen(open);
  }, []);

  useLayoutEffect(() => {
    const navVisible = !cardOpen && !overlayOpen;
    const body = document.body;
    if (navVisible) {
      body.setAttribute("data-nav-visible", "true");
    } else {
      body.setAttribute("data-nav-visible", "false");
    }

    if (tab === "sources") {
      if (overlayOpen) {
        onCardOpenChange(true, cancelOverlay);
        return;
      }
      onCardOpenChange(false, () => {});
      setCaptureStripHidden(document.getElementById("capture-strip"), true);
      return;
    }
    onCardOpenChange(cardOpen, () => {
      closeCardRef.current();
    });
  }, [tab, overlayOpen, cardOpen, cancelOverlay, onCardOpenChange]);

  return (
    <AppRoot appearance="dark" platform="ios">
      <div className="pocket-ideas" hidden={tab !== "ideas"}>
        <IdeaList
          getInitData={getInitData}
          onCopy={onCopy}
          onCount={onCount}
          onDeleteClear={onDeleteClear}
          onDeleteError={onDeleteError}
          appearance="dark"
          onCardOpenChange={reportCard}
        />
      </div>
      <div className="pocket-sources" hidden={tab !== "sources"}>
        <SourcesPane
          getInitData={getInitData}
          overlayOpen={overlayOpen}
          onOverlayOpenChange={setOverlayOpen}
          onSaveError={onSaveError}
          onDeleteError={onDeleteError}
          onOpenError={onOpenError}
        />
      </div>
      {!cardOpen && !overlayOpen ? (
        <BottomNav
          tab={tab}
          onIdeas={() => {
            setOverlayOpen(false);
            setTab("ideas");
          }}
          onSources={() => setTab("sources")}
        />
      ) : null}
    </AppRoot>
  );
}
