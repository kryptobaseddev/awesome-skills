# Author: description first, body second

## The description is the whole trigger surface

It is the only thing an agent reads at startup. A skill with an excellent body
and a vague description never runs, and no amount of body quality fixes that.

Structure that works in this repo (see `quo`, `better-auth`):

1. **What it is**, in one clause.
2. **What it covers** — concrete nouns, comma-listed. This is where the agent's
   keyword match actually lands, so name the things users say.
3. **"Use when …"** — the contexts, phrased as situations not features.
4. **A boundary** — "Not for X." Skills without one poach their neighbours.
5. **"Use even if the user only says '…'"** — the casual phrasings. Agents
   undertrigger; this is the counterweight.

Keep ~40 characters of headroom. A description at 1023/1024 cannot absorb the
one clause you will want to add after measuring.

**Write the boundary from the skill's own body.** If a workflow file says "bundle
analysis is a different job", the description should say so too. When they
disagree, the description wins in practice and the body becomes a lie.

## Body: 200–300 lines, weight in references

The pattern across this repo is a 200–300 line body plus 8–15 reference files
totalling 2500–4000 lines. The body routes; the references hold depth.

Section order that reads well:

```
# Title
(2-3 paragraph intro: what problem, why the obvious approach fails)
## The loop / mental model      -- one compact diagram or numbered list
## Facts that prevent broken work   -- the signature table: | Fact | Consequence |
## <orientation / setup>
## <the main routing table>
## <commands, with real invocations>
## Where to go next             -- | Task | Reference | with bare code paths
## Scripts                      -- | Script | Purpose |
## Common mistakes              -- numbered, ~10 rows
## Resources                    -- bare URLs
```

"Facts that prevent broken work" is the highest-value section. Each row should be
a real failure someone hit, not a generality. `| Fact | Consequence |` — bold the
fact, state what breaks.

## Write for a smart reader

Explain *why*, not just *what*. A model with good theory of mind will generalise
a reason to cases you did not enumerate; it cannot generalise a bare MUST. If you
find yourself writing ALWAYS or NEVER in caps, you are probably compensating for
an explanation you have not written yet.

Prefer the imperative. Prefer concrete numbers over "appropriate". Prefer naming
the failure over describing the ideal.

## References

One file per domain or per workflow. Each self-contained — an agent reads one,
not all. Give any file over ~300 lines a table of contents.

Link them from the body with bare inline code paths (`` `references/foo.md` ``),
not markdown links; that is the house convention and it is what the validator's
reference check resolves.

## Generate what is derivable

If a reference is a projection of structured data, generate it and say so in the
file. Hand-maintained copies of data drift, and the drift is silent. Ship the
generator next to the data so regenerating is one command.
