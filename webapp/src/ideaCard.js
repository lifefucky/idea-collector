export function ideaById(shelves, id) {
  for (const shelf of shelves) {
    const found = shelf.ideas.find((idea) => idea.id === id);
    if (found) {
      return found;
    }
  }
  return undefined;
}

export function shelvesWithoutIdea(shelves, id) {
  return shelves.map((shelf) => ({
    ...shelf,
    ideas: shelf.ideas.filter((idea) => idea.id !== id),
  }));
}

export function selectedAfterFetch(selected, shelves) {
  if (!selected) {
    return null;
  }
  return ideaById(shelves, selected.id) ?? null;
}

export function selectedAfterLoad(selected, ok, shelves) {
  if (!ok) {
    return selected;
  }
  return selectedAfterFetch(selected, shelves);
}

export function sourceAbbrev(title) {
  const words = String(title ?? "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (words.length === 0) {
    return "";
  }
  if (words.length >= 2) {
    const first = words[0];
    if (first.length <= 2) {
      return first.toLocaleUpperCase();
    }
    return `${first[0] ?? ""}${words[1][0] ?? ""}`.toLocaleUpperCase();
  }
  const word = words[0];
  if (word.length <= 2) {
    return word.toLocaleUpperCase();
  }
  return word.slice(0, 2).toLocaleUpperCase();
}

export const CARD_TONES = ["lime", "gold", "snow", "coral"];

export function cardTone(id) {
  const index = Math.abs(Number(id)) % CARD_TONES.length;
  return CARD_TONES[Number.isFinite(index) ? index : 0];
}

export function relatedIdeas(shelves, ideaId) {
  return (shelves ?? [])
    .flatMap((shelf) => shelf.ideas)
    .filter((item) => item.id !== ideaId)
    .slice(0, 3);
}

export function shelfNameOf(shelves, ideaId) {
  for (const shelf of shelves ?? []) {
    if (shelf.ideas.some((idea) => idea.id === ideaId)) {
      return shelf.name;
    }
  }
  return "";
}
