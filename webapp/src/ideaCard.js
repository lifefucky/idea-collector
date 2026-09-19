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
