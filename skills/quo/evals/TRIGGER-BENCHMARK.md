# quo trigger benchmark (2026-10-08)

Runner: `evals/run_triggers.py` (full tool sequence, fixture `files/web-app`, isolated HOME via `--skill-dir`),
model claude-opus-5-5, 20 queries x 3 runs, pass = trigger rate on the right side of 0.5.

| Description | Accuracy | Missed should-trigger | False triggers |
|---|---|---|---|
| draft v2.0.0 | 18/20 | 6, 17 | 0 |
| shipped v2.0.0 | 19/20 | 17 | 0 |

Known miss: #17 ("useQuery for /api/messages refetches too often on window focus") was set to
should_trigger by the owner; it names no texting, Quo or OpenPhone, and agents treat it as a TanStack
Query question (0/3). Broadening the description to catch it risks false triggers on generic
TanStack Query work, so it ships as a known miss.

Reproduce:

    python3 evals/run_triggers.py --eval-set evals/trigger_queries.json --skill quo \
      --skill-dir . --fixtures evals/files --work /tmp/quo-trig --runs 3 --model claude-opus-5-5 --out results.json
