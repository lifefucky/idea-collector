export function setCaptureStripHidden(strip, open) {
  if (!strip) {
    return;
  }
  strip.hidden = open;
}

export function setBackButtonVisible(api, open) {
  if (open) {
    if (api.show.isAvailable()) {
      api.show();
    }
    return;
  }
  if (api.hide.isAvailable()) {
    api.hide();
  }
}

export function bindCardBackButton(api, getClose) {
  if (api.onClick.isAvailable()) {
    api.onClick(() => {
      getClose()();
    });
  }
}
