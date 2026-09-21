---
name: bad-skill
description: "Short one."
metadata:
  category: not-a-real-slug
---

# bad-skill

Invokes a script directly while shipping it non-executable,
uses a category slug that does not exist, has a description with no trigger and no
boundary, and has neither enough body lines nor three top-level references.


## Usage

```bash
scripts/thing.py --flag
```

That is a direct invocation, so it needs the executable bit. `python3 scripts/thing.py`
would not -- the interpreter opens the file and the kernel never execs it.
