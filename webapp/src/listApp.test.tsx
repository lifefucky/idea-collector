/**
 * @vitest-environment jsdom
 */
import { AppRoot } from "@telegram-apps/telegram-ui";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, expect, test, vi } from "vitest";

vi.mock("./sourceLink.js", () => ({
  openSourceUrl: vi.fn(),
}));

import { relatedIdeas, sourceAbbrev } from "./ideaCard.js";
import { IdeaList } from "./listApp";
import { PocketApp } from "./pocketApp";
import { openSourceUrl } from "./sourceLink.js";
import { SourcesPane } from "./sourcesPane";

const openSourceUrlMock = vi.mocked(openSourceUrl);

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const gone = { id: 2, label: "gone-label", copy: "gone-copy" };
const kept = { id: 1, label: "kept-label", copy: "kept-copy" };

let root: Root | null = null;
let host: HTMLDivElement | null = null;

afterEach(() => {
  act(() => {
    root?.unmount();
  });
  host?.remove();
  root = null;
  host = null;
  vi.unstubAllGlobals();
  openSourceUrlMock.mockReset();
});

async function flush() {
  await act(async () => {
    await new Promise((resolve) => {
      window.setTimeout(resolve, 0);
    });
  });
}

function mountHost() {
  host = document.createElement("div");
  document.body.appendChild(host);
  root = createRoot(host);
}

async function mountList(props: {
  onCopy?: ReturnType<typeof vi.fn>;
  onCount?: ReturnType<typeof vi.fn>;
}) {
  mountHost();
  const onCopy = props.onCopy ?? vi.fn();
  const onCount = props.onCount ?? vi.fn();
  await act(async () => {
    root!.render(
      <IdeaList
        getInitData={() => "init"}
        onCopy={onCopy}
        onCount={onCount}
        onDeleteClear={() => {}}
        onDeleteError={() => {}}
        appearance="dark"
        onCardOpenChange={() => {}}
      />,
    );
  });
  await flush();
  return { onCopy, onCount };
}

async function click(target: string | HTMLElement) {
  const node =
    typeof target === "string"
      ? (host!.querySelector(target) ?? document.querySelector(target))
      : target;
  if (!(node instanceof HTMLElement)) {
    throw new Error(`missing ${String(target)}`);
  }
  await act(async () => {
    node.click();
  });
  await flush();
}

function stubIdeas(shelves: { name: string; ideas: typeof kept[] }[], count?: number) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/api/sources")) {
        if (init?.method === "POST") {
          const body = JSON.parse(String(init.body ?? "{}")) as {
            title?: string;
            url?: string;
          };
          return {
            ok: true,
            json: async () => ({
              id: 9,
              title: body.title,
              url: body.url,
            }),
          };
        }
        return { ok: true, json: async () => ({ sources: [] }) };
      }
      return {
        ok: true,
        json: async () => ({
          count: count ?? shelves.reduce((sum, shelf) => sum + shelf.ideas.length, 0),
          shelves,
        }),
      };
    }),
  );
}

test("load writes remaining count from GET /api/ideas", async () => {
  const onCount = vi.fn();
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: true,
      json: async () => ({
        count: 5,
        shelves: [{ name: "Toolify", ideas: [kept] }],
      }),
    })),
  );
  await mountList({ onCount });
  expect(onCount).toHaveBeenCalledWith(5);
  expect(host!.querySelector(".list-skeleton")).toBeNull();
  expect(host!.textContent).toContain("kept-label");
});

test("failed GET drops the skeleton without wiping later shelves", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: false,
      status: 401,
      json: async () => ({ error: "invalid initData" }),
    })),
  );
  await mountList({});
  expect(host!.querySelector(".list-skeleton")).toBeNull();
  expect(host!.querySelector(".shelf-title")).toBeNull();
});

test("row tap does not copy; body tap after ignoreBodyCopy copies", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: true,
      json: async () => ({
        count: 1,
        shelves: [{ name: "идея собственная", ideas: [gone] }],
      }),
    })),
  );
  const { onCopy } = await mountList({});
  expect(host!.querySelector(".shelf-title")).not.toBeNull();
  await click(".idea-row");
  expect(onCopy).not.toHaveBeenCalled();
  expect(host!.querySelector(".idea-card-body")).not.toBeNull();
  await click(".idea-card-body");
  expect(onCopy).not.toHaveBeenCalled();
  await act(async () => {
    await new Promise((resolve) => {
      window.setTimeout(resolve, 310);
    });
  });
  await click(".idea-card-body");
  expect(onCopy).toHaveBeenCalledTimes(1);
  expect(onCopy).toHaveBeenCalledWith("gone-copy");
});

test("delete then failed GET drops the id and keeps other shelves", async () => {
  const onCount = vi.fn();
  let ideasGets = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === "DELETE") {
        return {
          ok: true,
          status: 200,
          json: async () => ({ count: 1 }),
        };
      }
      ideasGets += 1;
      if (ideasGets > 1) {
        throw new Error("reload failed");
      }
      return {
        ok: true,
        json: async () => ({
          count: 2,
          shelves: [
            { name: "own", ideas: [kept] },
            { name: "ph", ideas: [gone] },
          ],
        }),
      };
    }),
  );
  await mountList({ onCount });
  expect(host!.querySelectorAll(".shelf-title").length).toBe(2);
  const goneRow = [...host!.querySelectorAll(".idea-row")].find((node) =>
    node.textContent?.includes("gone-label"),
  );
  if (!(goneRow instanceof HTMLElement)) {
    throw new Error("missing gone row");
  }
  await click(goneRow);
  expect(host!.querySelector(".idea-card-delete")).not.toBeNull();
  await click(".idea-card-delete");
  await vi.waitFor(() => {
    expect(host!.querySelector(".idea-card")).toBeNull();
    expect(host!.textContent).not.toContain("gone-label");
  });
  expect(onCount).toHaveBeenCalledWith(1);
  const titles = [...host!.querySelectorAll(".shelf-title")].map(
    (node) => node.textContent,
  );
  expect(titles).toEqual(["own"]);
  expect(host!.textContent).toContain("kept-label");
});

test("chips filter a shelf and the same chip returns to Все", async () => {
  stubIdeas(
    [
      { name: "Product Hunt", ideas: [kept] },
      { name: "YC Library", ideas: [gone] },
    ],
    2,
  );
  await mountList({});
  const chips = [...host!.querySelectorAll(".shelf-chip")];
  expect(chips[0]?.textContent).toContain("Все");
  expect(chips[0]?.textContent).toContain("2");
  expect(host!.textContent).toContain("kept-label");
  expect(host!.textContent).toContain("gone-label");
  const ph = chips.find((node) => node.textContent?.includes("PH"));
  if (!(ph instanceof HTMLElement)) {
    throw new Error("missing PH chip");
  }
  await click(ph);
  expect(host!.textContent).toContain("kept-label");
  expect(host!.textContent).not.toContain("gone-label");
  const all = [...host!.querySelectorAll(".shelf-chip")].find((node) =>
    node.textContent?.includes("Все"),
  );
  if (!(all instanceof HTMLElement)) {
    throw new Error("missing Все chip");
  }
  await click(all);
  expect(host!.textContent).toContain("kept-label");
  expect(host!.textContent).toContain("gone-label");
  await click(ph);
  expect(host!.textContent).toContain("kept-label");
  expect(host!.textContent).not.toContain("gone-label");
  await click(ph);
  expect(host!.textContent).toContain("kept-label");
  expect(host!.textContent).toContain("gone-label");
});

test("empty pocket shows only Все with 0", async () => {
  stubIdeas([], 0);
  await mountList({});
  const chips = [...host!.querySelectorAll(".shelf-chip")];
  expect(chips).toHaveLength(1);
  expect(chips[0]?.textContent).toContain("Все");
  expect(chips[0]?.textContent).toContain("0");
  expect(host!.querySelector(".shelf-title")).toBeNull();
});

test("related cards come from loaded shelves and open that card", async () => {
  stubIdeas(
    [
      { name: "own", ideas: [kept] },
      { name: "ph", ideas: [gone] },
    ],
    2,
  );
  await mountList({});
  const keptRow = [...host!.querySelectorAll(".idea-row")].find((node) =>
    node.textContent?.includes("kept-label"),
  );
  if (!(keptRow instanceof HTMLElement)) {
    throw new Error("missing kept row");
  }
  await click(keptRow);
  const related = host!.querySelector(".idea-related");
  expect(related).not.toBeNull();
  expect(related?.textContent).toContain("gone-label");
  expect(related?.textContent).not.toContain("kept-label");
  const relatedRow = [...related!.querySelectorAll(".idea-row")].find((node) =>
    node.textContent?.includes("gone-label"),
  );
  if (!(relatedRow instanceof HTMLElement)) {
    throw new Error("missing related row");
  }
  await click(relatedRow);
  expect(host!.querySelector(".idea-card-label")?.textContent).toBe("gone-label");
});

test("one loaded idea has no related block", async () => {
  stubIdeas([{ name: "own", ideas: [kept] }], 1);
  await mountList({});
  await click(".idea-row");
  expect(host!.querySelector(".idea-related")).toBeNull();
  expect(relatedIdeas([{ name: "own", ideas: [kept] }], kept.id)).toEqual([]);
});

test("Лента stays inert and does not switch tabs", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/sources")) {
      return { ok: true, json: async () => ({ sources: [] }) };
    }
    return {
      ok: true,
      json: async () => ({
        count: 1,
        shelves: [{ name: "own", ideas: [kept] }],
      }),
    };
  });
  vi.stubGlobal("fetch", fetchMock);
  mountHost();
  await act(async () => {
    root!.render(
      <PocketApp
        getInitData={() => "init"}
        onCopy={() => {}}
        onCount={() => {}}
        onDeleteClear={() => {}}
        onDeleteError={() => {}}
        appearance="dark"
        onCardOpenChange={() => {}}
        onSaveError={() => {}}
        onOpenError={() => {}}
      />,
    );
  });
  await flush();
  const before = fetchMock.mock.calls.length;
  const lenta = host!.querySelector('[aria-label="Лента"]');
  expect(lenta).not.toBeNull();
  expect(lenta?.getAttribute("aria-disabled")).toBe("true");
  expect(lenta?.getAttribute("data-stub")).toBe("no-backend");
  expect((lenta as HTMLElement).style.pointerEvents).toBe("none");
  await click(lenta as HTMLElement);
  expect(host!.querySelector(".pocket-ideas")?.hasAttribute("hidden")).toBe(false);
  expect(host!.querySelector(".pocket-sources")?.hasAttribute("hidden")).toBe(
    true,
  );
  expect(fetchMock.mock.calls.length).toBe(before);
  await click('[aria-label="Sources"]');
  expect(host!.querySelector(".pocket-sources")?.hasAttribute("hidden")).toBe(
    false,
  );
});

test("suggestion chip fills fields; save POSTs; empty save keeps overlay", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "POST") {
      return {
        ok: true,
        json: async () => ({
          id: 9,
          title: "Product Hunt",
          url: "https://www.producthunt.com",
        }),
      };
    }
    return { ok: true, json: async () => ({ sources: [] }) };
  });
  vi.stubGlobal("fetch", fetchMock);
  const onOverlay = vi.fn();
  mountHost();
  await act(async () => {
    root!.render(
      <AppRoot appearance="dark" platform="ios">
        <SourcesPane
          getInitData={() => "init"}
          overlayOpen
          onOverlayOpenChange={onOverlay}
          onSaveError={() => {}}
          onDeleteError={() => {}}
          onOpenError={() => {}}
        />
      </AppRoot>,
    );
  });
  await flush();
  await click(".sources-overlay-save");
  expect(
    fetchMock.mock.calls.some((call) => (call[1] as RequestInit | undefined)?.method === "POST"),
  ).toBe(false);
  expect(onOverlay).not.toHaveBeenCalled();
  const chip = [...document.querySelectorAll(".source-suggest-chip")].find((node) =>
    node.textContent?.includes("PH"),
  );
  if (!(chip instanceof HTMLElement)) {
    throw new Error("missing suggestion chip");
  }
  expect(chip.getAttribute("data-stub")).toBe("no-backend");
  await click(chip);
  expect(
    fetchMock.mock.calls.some((call) => (call[1] as RequestInit | undefined)?.method === "POST"),
  ).toBe(false);
  const title = document.querySelector('input[placeholder="Название"]');
  const url = document.querySelector('input[placeholder="Ссылка"]');
  expect((title as HTMLInputElement | null)?.value).toBe("Product Hunt");
  expect((url as HTMLInputElement | null)?.value).toBe(
    "https://www.producthunt.com",
  );
  await click(".sources-overlay-save");
  await vi.waitFor(() => {
    expect(
      fetchMock.mock.calls.some((call) => (call[1] as RequestInit | undefined)?.method === "POST"),
    ).toBe(true);
  });
  expect(onOverlay).toHaveBeenCalledWith(false);
});

test("sourceAbbrev uses two-word initials else first two chars", () => {
  expect(sourceAbbrev("Product Hunt")).toBe("PH");
  expect(sourceAbbrev("YC Library")).toBe("YC");
  expect(sourceAbbrev("Radar")).toBe("RA");
  expect(sourceAbbrev("Яндекс")).toBe("ЯН");
  expect(sourceAbbrev("YC")).toBe("YC");
});

function pocketFetch() {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/api/sources")) {
      if (init?.method === "DELETE") {
        return { ok: true, status: 200, json: async () => ({}) };
      }
      return {
        ok: true,
        json: async () => ({
          sources: [{ id: 3, title: "Toolify", url: "https://www.toolify.ai" }],
        }),
      };
    }
    return {
      ok: true,
      json: async () => ({
        count: 1,
        shelves: [{ name: "own", ideas: [kept] }],
      }),
    };
  });
}

async function mountPocket() {
  mountHost();
  await act(async () => {
    root!.render(
      <PocketApp
        getInitData={() => "init"}
        onCopy={() => {}}
        onCount={() => {}}
        onDeleteClear={() => {}}
        onDeleteError={() => {}}
        appearance="dark"
        onCardOpenChange={() => {}}
        onSaveError={() => {}}
        onOpenError={() => {}}
      />,
    );
  });
  await flush();
}

test("BottomNav hides on card and add-source overlay then returns", async () => {
  vi.stubGlobal("fetch", pocketFetch());
  await mountPocket();
  expect(host!.querySelector(".bottom-nav")).not.toBeNull();
  await click(".idea-row");
  expect(host!.querySelector(".bottom-nav")).toBeNull();
  await click(".idea-card-back");
  expect(host!.querySelector(".bottom-nav")).not.toBeNull();
  await click('[aria-label="Sources"]');
  await click(".sources-add");
  expect(host!.querySelector(".bottom-nav")).toBeNull();
  await click(".sources-overlay-cancel");
  expect(host!.querySelector(".bottom-nav")).not.toBeNull();
});

async function mountLoadedSources() {
  mountHost();
  await act(async () => {
    root!.render(
      <AppRoot appearance="dark" platform="ios">
        <SourcesPane
          getInitData={() => "init"}
          overlayOpen={false}
          onOverlayOpenChange={() => {}}
          onSaveError={() => {}}
          onDeleteError={() => {}}
          onOpenError={() => {}}
        />
      </AppRoot>,
    );
  });
  await flush();
}

test("source title tap opens the url and does not delete", async () => {
  const fetchMock = pocketFetch();
  vi.stubGlobal("fetch", fetchMock);
  await mountLoadedSources();
  await click(".source-row");
  expect(openSourceUrlMock).toHaveBeenCalledWith(
    "https://www.toolify.ai",
    expect.anything(),
  );
  expect(
    fetchMock.mock.calls.some((call) => (call[1] as RequestInit | undefined)?.method === "DELETE"),
  ).toBe(false);
});

test("source delete removes the row without opening the url", async () => {
  const fetchMock = pocketFetch();
  vi.stubGlobal("fetch", fetchMock);
  await mountLoadedSources();
  await click(".source-row-delete");
  await vi.waitFor(() => {
    expect(host!.querySelector(".source-row")).toBeNull();
  });
  expect(
    fetchMock.mock.calls.some(
      (call) =>
        String(call[0]).includes("/api/sources/3") &&
        (call[1] as RequestInit | undefined)?.method === "DELETE",
    ),
  ).toBe(true);
  expect(openSourceUrlMock).not.toHaveBeenCalled();
});
