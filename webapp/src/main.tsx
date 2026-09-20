import { createRoot } from "react-dom/client";
import {
  backButton,
  init,
  initDataRaw,
  isColorDark,
  miniApp,
  restoreInitData,
  retrieveLaunchParams,
  retrieveRawInitData,
  themeParams,
} from "@telegram-apps/sdk";
import "@telegram-apps/telegram-ui/dist/styles.css";
import {
  applyStatus,
  bindCaptureForm,
  bindCopy,
  deleteStatus,
  saveStatus,
  replaceCountPlaceholder,
  setIdeasCounter,
} from "./capture.js";
import {
  bindCardBackButton,
  setBackButtonVisible,
  setCaptureStripHidden,
} from "./cardChrome.js";
import { PocketApp } from "./pocketApp";
import { OPEN_ERROR } from "./sourcesPane";

function bootSdk(): void {
  try {
    init();
  } catch {
    return;
  }
  try {
    restoreInitData();
  } catch {
    /* launch params may already populate init data */
  }
  try {
    if (themeParams.mountSync.isAvailable()) {
      themeParams.mountSync();
    }
    if (themeParams.bindCssVars.isAvailable()) {
      themeParams.bindCssVars();
    }
  } catch {
    /* DESIGN.md fallbacks remain in CSS */
  }
  try {
    if (miniApp.mountSync.isAvailable()) {
      miniApp.mountSync();
    }
    if (miniApp.ready.isAvailable()) {
      miniApp.ready();
    }
  } catch {
    /* first paint already showed the field */
  }
  try {
    if (backButton.mount.isAvailable()) {
      backButton.mount();
    }
  } catch {
    /* Skip BackButton if !isAvailable */
  }
}

function readInitData(): string {
  try {
    const raw = initDataRaw();
    if (raw) {
      return raw;
    }
  } catch {
    /* try other sources */
  }
  try {
    const raw = retrieveRawInitData();
    if (raw) {
      return raw;
    }
  } catch {
    /* try launch params */
  }
  try {
    const launch = retrieveLaunchParams(true) as { initDataRaw?: string; tgWebAppData?: string };
    if (launch.initDataRaw) {
      return launch.initDataRaw;
    }
    if (launch.tgWebAppData) {
      return launch.tgWebAppData;
    }
  } catch {
    /* outside Telegram */
  }
  if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    // Local preview and tests: treat as operator without weakening real Telegram auth.
    return "dev";
  }
  return "";
}

function readAppearance(): "light" | "dark" {
  try {
    const background = themeParams.backgroundColor();
    if (background) {
      return isColorDark(background) ? "dark" : "light";
    }
  } catch {
    /* fall through */
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

bootSdk();

const form = document.getElementById("capture-form");
const field = document.getElementById("capture-field");
const counter = document.getElementById("ideas-counter");
const status = document.getElementById("status-line");
const listRoot = document.getElementById("idea-list");

if (counter instanceof HTMLElement) {
  replaceCountPlaceholder(counter);
}

if (
  form instanceof HTMLFormElement &&
  field instanceof HTMLTextAreaElement &&
  counter instanceof HTMLElement &&
  status instanceof HTMLElement
) {
  bindCaptureForm({
    form,
    field,
    counter,
    status,
    getInitData: readInitData,
    onSaved: () => {
      window.dispatchEvent(new Event("ideas:changed"));
      for (const ms of [1000, 3000, 8000]) {
        window.setTimeout(() => {
          window.dispatchEvent(new Event("ideas:changed"));
        }, ms);
      }
    },
  });
}

if (listRoot && status instanceof HTMLElement) {
  const onCopy = bindCopy(status);
  let closeIdeaCard = () => {};
  try {
    bindCardBackButton(backButton, () => closeIdeaCard);
  } catch {
    /* Skip BackButton if !isAvailable */
  }
  createRoot(listRoot).render(
    <PocketApp
      getInitData={readInitData}
      onCopy={(text) => {
        void onCopy(text);
      }}
      onCount={(count) => {
        if (counter instanceof HTMLElement) {
          setIdeasCounter(counter, count);
        }
      }}
      onDeleteClear={() => {
        applyStatus(status, deleteStatus(true));
      }}
      onDeleteError={() => {
        applyStatus(status, deleteStatus(false));
      }}
      onSaveError={() => {
        applyStatus(status, saveStatus(false));
      }}
      onOpenError={() => {
        applyStatus(status, { text: OPEN_ERROR, destructive: true });
      }}
      appearance={readAppearance()}
      onCardOpenChange={(open, close) => {
        closeIdeaCard = close;
        setCaptureStripHidden(document.getElementById("capture-strip"), open);
        try {
          setBackButtonVisible(backButton, open);
        } catch {
          /* Skip BackButton if !isAvailable */
        }
      }}
    />,
  );
}
