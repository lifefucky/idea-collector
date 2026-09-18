- source_spec: /Users/user/idea-collector/_bmad-output/implementation-artifacts/spec-v1-telegram-idea-pocket.md
  summary: CSV export of saved ideas (CAP-5) via a bot command that sends a .csv document.
  evidence: Token-count split from the v1 pocket spec; user chose Split and answered that CSV should be a chat command (`/csv`), not a Mini App control.
- source_spec: /Users/user/idea-collector/_bmad-output/implementation-artifacts/spec-v1-telegram-idea-pocket.md
  summary: Mini App tap-to-copy is not covered by an executing UI test (Cell onClick → idea.copy).
  evidence: Verification-gap finding VG5; pytest pins copy on /api/ideas JSON only. Settled by a frontend runner clicking IdeaList; this slice has none.

