# Naming note (added 2026-09-21, after this run)

This council run was held while the skill was named `deluxui`. It was renamed to
`deuxui` (DeuxUI) in v5.0.0, later the same day.

The advisor and peer-review transcripts in this directory are left **verbatim**.
They record what each advisor actually wrote at the time, and a transcript edited
after the fact to match a later decision is no longer evidence of anything. Read
every `deluxui` in these files as the skill now shipped at `skills/deuxui/`.

No live code, document, path, install or index still carries the old name --
including the migration probe, which was a hardcoded `.deluxui` until v5.6.0 and now
identifies a record of ours by its CONTENTS (`uxconfig.state_candidates`). That reads
any directory holding a file only this tool writes, so it finds the old name, and also
a directory somebody copied or renamed by hand, which a remembered name never could.
