import {
  COPY_ERROR,
  COPY_OK,
  bindCaptureForm,
  bindCopy,
  copyStatus,
  nextFieldText,
  saveStatus,
} from "../webapp/src/capture.js";
import {
  bindCardBackButton,
  setBackButtonVisible,
  setCaptureStripHidden,
} from "../webapp/src/cardChrome.js";
import { selectedAfterFetch, selectedAfterLoad } from "../webapp/src/ideaCard.js";

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

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
console.log("ok");
