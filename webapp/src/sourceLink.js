export function openSourceUrl(url, openLink) {
  if (openLink.isAvailable()) {
    openLink(url);
    return;
  }
  const opened = window.open(url, "_blank", "noopener");
  if (!opened) {
    throw new Error("Не удалось открыть");
  }
}
