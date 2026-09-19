/**
 * @vitest-environment jsdom
 */
import { AppRoot } from "@telegram-apps/telegram-ui";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, expect, test, vi } from "vitest";
import { IdeaList } from "./listApp";

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
});

async function flush() {
  await act(async () => {
    await new Promise((resolve) => {
      window.setTimeout(resolve, 0);
    });
  });
}

async function mountList(props: {
  onCopy?: ReturnType<typeof vi.fn>;
  onCount?: ReturnType<typeof vi.fn>;
}) {
  host = document.createElement("div");
  document.body.appendChild(host);
  root = createRoot(host);
  const onCopy = props.onCopy ?? vi.fn();
  const onCount = props.onCount ?? vi.fn();
  await act(async () => {
    root!.render(
      <AppRoot appearance="light" platform="ios">
        <IdeaList
          getInitData={() => "init"}
          onCopy={onCopy}
          onCount={onCount}
          onDeleteClear={() => {}}
          onDeleteError={() => {}}
          appearance="light"
          onCardOpenChange={() => {}}
        />
      </AppRoot>,
    );
  });
  await flush();
  return { onCopy, onCount };
}

async function click(target: string | HTMLElement) {
  const node =
    typeof target === "string" ? host!.querySelector(target) : target;
  if (!(node instanceof HTMLElement)) {
    throw new Error(`missing ${String(target)}`);
  }
  await act(async () => {
    node.click();
  });
  await flush();
}

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
  await click("[aria-expanded]");
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
