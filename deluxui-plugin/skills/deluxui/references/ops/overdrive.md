# overdrive — the maximum this system can express, still inside it

A deliberate excursion to the top of the system's range. Not a new system: the
point is to find out how much the committed world can carry before it stops being
itself.

Derived from impeccable's `overdrive` (Apache-2.0) — see NOTICE.md.

## When this is legitimate

Visitor mode decides. On a **persuade** or **experience** surface — a launch
page, a campaign, a single hero moment — overdrive is the job. On an **operate**
or **read** surface it almost never is, and the request usually means something
else: the hierarchy is unclear, or the primary action is hard to find. Fix that
instead and say so.

On **native**, the platform owns structure, navigation and interaction in every
mode. Overdrive expresses through the layer the platform leaves open — tint,
type, motion, content — and nothing here licenses a reinvented navigation bar
(IOS-002) or a Cupertino control on Android (AND-012).

## The rails that stay up

Overdrive raises the ceiling on expression. It raises nothing else:

- contrast minimums (NUM-001, NUM-002, NUM-003) — these are STANDARD class and
  `scripts/uxconfig.py` refuses to override them, loudly;
- target sizes (NUM-004, NUM-005);
- the reduced-motion path (A11Y-010);
- keyboard operability (A11Y-002);
- every P0 rule.

A hero that cannot be read, or cannot be tabbed through, is not expressive. It is
broken with ambition.

## How to spend the range

One move at full commitment, and everything around it quiet enough that the move
is legible. Take the scale, the motif, the density and the motion the system
already owns and run them to the top of their declared range — then record what
you spent:

```yaml
departures:
  - value: "clamp(3rem, 12vw, 6rem)"
    where: "src/routes/launch/Hero.tsx"
    why: "The launch hero is the one display moment in the product; the ceiling
          is the contract's own display_max_rem, not a new value."
```

A departure with a reason is a decision. A departure without one is a leak, and
the difference is the whole point of the contract.

## Verify

| Detector | What it settles |
|---|---|
| `S-CRAFT-HERO-SCALE` | Still under the declared display ceiling. |
| `S-CONTRACT-COLOR`, `S-CONTRACT-FAMILY` | No new colour or face arrived unrecorded. |
| `S-CONTRAST-PAIR`, `R-CONTRAST` | The expressive pairs are still readable. |
| `S-MOTION-REDUCE`, `R-MOTION` | Everything stops when the user asked it to. |
| `R-FOCUS-WALK`, `R-TARGET` | It can still be operated. |

Hand off to [polish.md](polish.md).
