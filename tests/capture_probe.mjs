import {
  COPY_OK,
  bindCaptureForm,
  copyStatus,
  nextFieldText,
  saveStatus,
} from "../webapp/src/capture.js";

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

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
console.log("ok");
