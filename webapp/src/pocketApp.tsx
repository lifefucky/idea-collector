import { useCallback, useLayoutEffect, useRef, useState } from "react";
import { AppRoot, Tabbar } from "@telegram-apps/telegram-ui";
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

export function PocketApp({
  getInitData,
  onCopy,
  onCount,
  onDeleteClear,
  onDeleteError,
  appearance,
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
    <AppRoot appearance={appearance} platform="ios">
      <div className="pocket-ideas" hidden={tab !== "ideas"}>
        <IdeaList
          getInitData={getInitData}
          onCopy={onCopy}
          onCount={onCount}
          onDeleteClear={onDeleteClear}
          onDeleteError={onDeleteError}
          appearance={appearance}
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
      <Tabbar>
        <Tabbar.Item
          text="Идеи"
          selected={tab === "ideas"}
          onClick={() => {
            setOverlayOpen(false);
            setTab("ideas");
          }}
        />
        <Tabbar.Item
          text="Sources"
          selected={tab === "sources"}
          onClick={() => setTab("sources")}
        />
      </Tabbar>
    </AppRoot>
  );
}
