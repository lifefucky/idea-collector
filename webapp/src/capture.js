export const COPY_OK = "Скопировано";
export const SAVE_ERROR = "Не удалось сохранить";
export const COPY_ERROR = "Не удалось скопировать";
export const DELETE_ERROR = "Не удалось удалить";

export function nextFieldText(persisted, current) {
  return persisted ? "" : current;
}

export function saveStatus(ok) {
  if (ok) {
    return { text: "", destructive: false };
  }
  return { text: SAVE_ERROR, destructive: true };
}

export function copyStatus(ok) {
  if (ok) {
    return { text: COPY_OK, destructive: false };
  }
  return { text: COPY_ERROR, destructive: true };
}

export function deleteStatus(ok) {
  if (ok) {
    return { text: "", destructive: false };
  }
  return { text: DELETE_ERROR, destructive: true };
}

export const COUNT_PLACEHOLDER = "__IDEAS_COUNT__";

export function setIdeasCounter(counter, count) {
  counter.textContent = String(count);
}

export function replaceCountPlaceholder(counter) {
  if (counter.textContent === COUNT_PLACEHOLDER) {
    setIdeasCounter(counter, 0);
  }
}

export function deleteFetchOutcome(response) {
  if (!response) {
    return { count: false, close: false, error: true };
  }
  if (response.ok) {
    return { count: true, close: true, error: false };
  }
  if (response.status === 404) {
    return { count: false, close: true, error: false };
  }
  return { count: false, close: false, error: true };
}

export function sourceDeleteOutcome(response) {
  if (!response) {
    return { remove: false, error: true };
  }
  if (response.ok) {
    return { remove: true, error: false };
  }
  if (response.status === 404) {
    return { remove: true, error: false };
  }
  return { remove: false, error: true };
}

export function applyStatus(statusEl, result) {
  if (!result.text) {
    statusEl.hidden = true;
    statusEl.textContent = "";
    statusEl.classList.remove("destructive");
    return;
  }
  statusEl.hidden = false;
  statusEl.textContent = result.text;
  statusEl.classList.toggle("destructive", result.destructive);
}

export function bindCaptureForm({
  form,
  field,
  counter,
  status,
  getInitData,
  onSaved,
}) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const current = field.value;
    if (!current.trim()) {
      return;
    }
    let persisted = false;
    let errorText = SAVE_ERROR;
    try {
      const response = await fetch("/api/ideas", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `tma ${getInitData()}`,
        },
        body: JSON.stringify({ text: current }),
      });
      persisted = response.ok;
      if (response.ok) {
        try {
          const body = await response.json();
          if (typeof body.count === "number") {
            setIdeasCounter(counter, body.count);
          }
        } catch {
          /* keep persisted true even if JSON parse fails */
        }
        onSaved?.();
      } else {
        try {
          const body = await response.json();
          if (typeof body?.error === "string" && body.error) {
            errorText = body.error;
          }
        } catch {
          /* SAVE_ERROR */
        }
      }
    } catch {
      persisted = false;
    }
    field.value = nextFieldText(persisted, current);
    applyStatus(
      status,
      persisted ? saveStatus(true) : { text: errorText, destructive: true },
    );
  });

  field.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
}

export function bindCopy(status) {
  return async (text) => {
    let ok = false;
    try {
      await navigator.clipboard.writeText(text);
      ok = true;
    } catch {
      ok = false;
    }
    applyStatus(status, copyStatus(ok));
    return ok;
  };
}
