# teach.html ↔ Supabase

- `schema.sql` — every table/column the teaching page uses. **Add new columns here AND run the ALTER in the
  Supabase SQL editor BEFORE pushing a teach.html that reads/writes them.**
- `tools/check_teach_schema.py` checks the live DB has every column in teach.html's `SCOL` / `XCOL`; the local
  git pre-push hook runs it and blocks the push if not (override: `SKIP_SCHEMA=1 git push`, only when the
  page is meant to cope without the column).
- The page itself also survives a missing column (drops it, keeps saving everything else, shows ⚠ in the
  footer) and saves each table independently — but that's the safety net, not the plan.
- Why: 2026-10-11 the `kind` field shipped before its column; every students write was rejected, and the old
  engine refused to download while it had unsent edits, so iPad and desktop each froze on their own copy.
