import {
  COPY_ERROR,
  COPY_OK,
  DELETE_ERROR,
  applyStatus,
  bindCaptureForm,
  bindCopy,
  copyStatus,
  deleteFetchOutcome,
  sourceDeleteOutcome,
  deleteStatus,
  nextFieldText,
  saveStatus,
  setIdeasCounter,
  replaceCountPlaceholder,
  COUNT_PLACEHOLDER,
} from "../webapp/src/capture.js";
import {
  bindCardBackButton,
  setBackButtonVisible,
  setCaptureStripHidden,
} from "../webapp/src/cardChrome.js";
import {
  selectedAfterFetch,
  selectedAfterLoad,
  shelvesWithoutIdea,
} from "../webapp/src/ideaCard.js";
import { openSourceUrl } from "../webapp/src/sourceLink.js";

const failures = [];

function assertEqual(actual, expected, message) {
  if (actual !== expected) {
    failures.push(`${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
  }
}

function stubCapture() {
  const listeners = {};
  return {
    form: {
      addEventListener(type, fn) {
        listeners[type] = fn;
      },
    },
    field: {
      value: "hello",
      addEventListener() {},
    },
    counter: { textContent: "0" },
    status: {
      hidden: true,
      textContent: "",
      classList: {
        toggle() {},
        remove() {},
      },
    },
    listeners,
  };
}

assertEqual(nextFieldText(true, "hello"), "", "field clears after persist");
assertEqual(nextFieldText(false, "hello"), "hello", "text stays on persist fail");
assertEqual(nextFieldText(false, "offline draft"), "offline draft", "offline keeps field text");
assertEqual(saveStatus(false).destructive, true, "persist fail is destructive");
assertEqual(saveStatus(true).text, "", "persist success has no error line");
assertEqual(copyStatus(true).text, COPY_OK, "copy success label");
assertEqual(copyStatus(false).destructive, true, "copy fail is destructive");
assertEqual(deleteStatus(false).text, DELETE_ERROR, "delete fail label");
assertEqual(deleteStatus(false).destructive, true, "delete fail is destructive");
assertEqual(deleteStatus(true).text, "", "delete success has no error line");
const counterEl = { textContent: "2" };
setIdeasCounter(counterEl, 0);
assertEqual(counterEl.textContent, "0", "setIdeasCounter writes remaining count");
const placeholderEl = { textContent: COUNT_PLACEHOLDER };
replaceCountPlaceholder(placeholderEl);
assertEqual(placeholderEl.textContent, "0", "replaceCountPlaceholder swaps token for 0");
const numericEl = { textContent: "7" };
replaceCountPlaceholder(numericEl);
assertEqual(numericEl.textContent, "7", "replaceCountPlaceholder leaves a real count");
const deleteStatusEl = {
  hidden: true,
  textContent: "",
  classList: {
    toggle(_name, on) {
      deleteStatusEl.destructive = on;
    },
    remove() {},
  },
  destructive: false,
};
applyStatus(deleteStatusEl, deleteStatus(false));
assertEqual(deleteStatusEl.textContent, DELETE_ERROR, "applyStatus shows delete error");
assertEqual(deleteStatusEl.destructive, true, "applyStatus marks delete error destructive");
applyStatus(deleteStatusEl, deleteStatus(true));
assertEqual(deleteStatusEl.textContent, "", "deleteStatus(true) clears status text");
assertEqual(deleteStatusEl.hidden, true, "deleteStatus(true) hides status line");

function assertDeleteOutcome(response, expected, message) {
  const actual = deleteFetchOutcome(response);
  assertEqual(actual.count, expected.count, `${message} count`);
  assertEqual(actual.close, expected.close, `${message} close`);
  assertEqual(actual.error, expected.error, `${message} error`);
}
assertDeleteOutcome(
  { ok: true, status: 200 },
  { count: true, close: true, error: false },
  "200 applies count and closes",
);
assertDeleteOutcome(
  { ok: false, status: 404 },
  { count: false, close: true, error: false },
  "404 closes without count",
);
assertDeleteOutcome(
  { ok: false, status: 500 },
  { count: false, close: false, error: true },
  "5xx stays with error",
);
assertDeleteOutcome(
  { ok: false, status: 401 },
  { count: false, close: false, error: true },
  "401 stays with error",
);
assertDeleteOutcome(
  null,
  { count: false, close: false, error: true },
  "throw stays with error",
);

function assertSourceDeleteOutcome(response, expected, message) {
  const actual = sourceDeleteOutcome(response);
  assertEqual(actual.remove, expected.remove, `${message} remove`);
  assertEqual(actual.error, expected.error, `${message} error`);
}
assertSourceDeleteOutcome(
  { ok: true, status: 200 },
  { remove: true, error: false },
  "source 200 removes",
);
assertSourceDeleteOutcome(
  { ok: false, status: 404 },
  { remove: true, error: false },
  "source 404 removes",
);
assertSourceDeleteOutcome(
  { ok: false, status: 500 },
  { remove: false, error: true },
  "source 5xx stays with error",
);
assertSourceDeleteOutcome(
  null,
  { remove: false, error: true },
  "source throw stays with error",
);

const linkCalls = [];
const availableOpenLink = Object.assign((url) => linkCalls.push(url), {
  isAvailable: () => true,
});
const unavailableOpenLink = Object.assign((url) => linkCalls.push(`sdk:${url}`), {
  isAvailable: () => false,
});
const openedWindows = [];
globalThis.window = {
  open(url, target, features) {
    openedWindows.push({ url, target, features });
    return { stub: true };
  },
};
openSourceUrl("https://available.example", availableOpenLink);
assertEqual(linkCalls.join(","), "https://available.example", "openLink when available");
assertEqual(openedWindows.length, 0, "window.open unused when openLink available");
openSourceUrl("https://fallback.example", unavailableOpenLink);
assertEqual(openedWindows[0]?.url, "https://fallback.example", "window.open when unavailable");
assertEqual(openedWindows[0]?.target, "_blank", "window.open target");
assertEqual(openedWindows[0]?.features, "noopener", "window.open noopener");
globalThis.window.open = () => null;
let openThrew = false;
try {
  openSourceUrl("https://blocked.example", unavailableOpenLink);
} catch {
  openThrew = true;
}
assertEqual(openThrew, true, "falsy window.open throws");

const originalFetch = globalThis.fetch;

const ok = stubCapture();
globalThis.fetch = async () => ({
  ok: true,
  json: async () => ({ count: 3 }),
});
bindCaptureForm({
  form: ok.form,
  field: ok.field,
  counter: ok.counter,
  status: ok.status,
  getInitData: () => "init",
});
await ok.listeners.submit({ preventDefault() {} });
assertEqual(ok.field.value, "", "bindCaptureForm clears field on 200");
assertEqual(ok.counter.textContent, "3", "bindCaptureForm updates counter on 200");

const thrown = stubCapture();
globalThis.fetch = async () => {
  throw new Error("offline");
};
bindCaptureForm({
  form: thrown.form,
  field: thrown.field,
  counter: thrown.counter,
  status: thrown.status,
  getInitData: () => "init",
});
await thrown.listeners.submit({ preventDefault() {} });
assertEqual(thrown.field.value, "hello", "bindCaptureForm keeps text on throw");
assertEqual(thrown.status.textContent, "Не удалось сохранить", "bindCaptureForm save error on throw");

const notOk = stubCapture();
globalThis.fetch = async () => ({
  ok: false,
  json: async () => ({ error: "custom fail" }),
});
bindCaptureForm({
  form: notOk.form,
  field: notOk.field,
  counter: notOk.counter,
  status: notOk.status,
  getInitData: () => "init",
});
await notOk.listeners.submit({ preventDefault() {} });
assertEqual(notOk.field.value, "hello", "bindCaptureForm keeps text on non-OK");
assertEqual(notOk.status.textContent, "custom fail", "bindCaptureForm prefers JSON error");

globalThis.fetch = originalFetch;

const copied = { value: null, fail: false };
Object.defineProperty(globalThis.navigator, "clipboard", {
  configurable: true,
  value: {
    async writeText(text) {
      if (copied.fail) {
        throw new Error("denied");
      }
      copied.value = text;
    },
  },
});
const copyStatusEl = {
  hidden: true,
  textContent: "",
  classList: {
    toggle() {},
    remove() {},
  },
};
const copyFn = bindCopy(copyStatusEl);
copied.fail = false;
await copyFn("body-copy");
assertEqual(copied.value, "body-copy", "bindCopy writes clipboard text");
assertEqual(copyStatusEl.textContent, COPY_OK, "bindCopy success status");
copied.fail = true;
await copyFn("nope");
assertEqual(copyStatusEl.textContent, COPY_ERROR, "bindCopy fail keeps error status");

const strip = { hidden: false };
setCaptureStripHidden(strip, true);
assertEqual(strip.hidden, true, "strip hidden when card open");
setCaptureStripHidden(strip, false);
assertEqual(strip.hidden, false, "strip visible when card closed");

const backCalls = [];
const backApi = {
  show: Object.assign(() => backCalls.push("show"), { isAvailable: () => true }),
  hide: Object.assign(() => backCalls.push("hide"), { isAvailable: () => true }),
  onClick: Object.assign((fn) => {
    backApi.press = fn;
  }, { isAvailable: () => true }),
  press: () => {},
};
setBackButtonVisible(backApi, true);
assertEqual(backCalls.join(","), "show", "BackButton show when card open");
setBackButtonVisible(backApi, false);
assertEqual(backCalls.join(","), "show,hide", "BackButton hide when card closed");
let closeLabel = "close-a";
bindCardBackButton(backApi, () => () => backCalls.push(closeLabel));
backApi.press();
closeLabel = "close-b";
backApi.press();
assertEqual(
  backCalls.join(","),
  "show,hide,close-a,close-b",
  "BackButton onClick runs current close",
);

const selected = { id: 1, label: "old", copy: "old-copy" };
const refreshed = selectedAfterFetch(selected, [
  { name: "own", ideas: [{ id: 1, label: "new", copy: "new-copy" }] },
]);
assertEqual(refreshed?.label, "new", "found id refreshes label");
assertEqual(refreshed?.copy, "new-copy", "found id refreshes copy");
assertEqual(
  selectedAfterFetch(selected, [{ name: "own", ideas: [] }]),
  null,
  "missing id is null",
);
assertEqual(
  selectedAfterLoad(selected, false, []),
  selected,
  "callers keep the card on failed fetch",
);

const shelves = [
  {
    name: "own",
    ideas: [
      { id: 1, label: "keep-a", copy: "a-copy" },
      { id: 2, label: "gone", copy: "gone-copy" },
    ],
  },
  { name: "ph", ideas: [{ id: 3, label: "keep-b", copy: "b-copy" }] },
];
const withoutGone = shelvesWithoutIdea(shelves, 2);
assertEqual(withoutGone[0].ideas.length, 1, "deleted id gone from shelf");
assertEqual(withoutGone[0].ideas[0].id, 1, "sibling idea kept");
assertEqual(withoutGone[1].ideas[0].id, 3, "other shelf kept");
assertEqual(shelves[0].ideas.length, 2, "original shelves not mutated");
assertEqual(
  shelvesWithoutIdea(withoutGone, 1)[0].ideas.length,
  0,
  "empty group stays for namedShelves to hide",
);

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
console.log("ok");
