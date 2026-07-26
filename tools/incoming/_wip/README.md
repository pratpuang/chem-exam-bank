# _wip/ — not-ready fragments

Park a fragment here while it's still being drafted/reviewed. `build_bank.py` only
globs `tools/incoming/*.md` (top-level, non-recursive), so anything inside this
subfolder — or any other `_`-prefixed subfolder — is invisible to a build run and
will never be merged into `question-bank.md` by accident.

When a fragment is ready, move it up one level into `tools/incoming/` and run
`python tools/build_bank.py` as usual.
