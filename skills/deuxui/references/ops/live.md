# live — pick it on the screen, compare in place, accept it into the source

The loop nothing else here closes. A person looks at the real running app, says
*that bit*, sees two or three honest alternatives **in the element's own position**
rather than in a mock, picks one, and the pick lands in the source.

```bash
python3 scripts/ux_live.py pick                        # point at it
python3 scripts/ux_live.py vary REQ-001 --count 3       # variants, from the contract
python3 scripts/ux_live.py show REQ-001                 # all of them, in the page
python3 scripts/ux_live.py accept REQ-001 --variant B --who "NAME"
```

Everything before this either measured a screen that already existed or generated a
separate artefact to look at. This is the one that edits the thing while somebody is
looking at it — which is also why it is the one that needs the most refusing.

## Four properties, and each one is a refusal

**A variant can only propose declared values.** Every size comes off the type
ladder, every colour is a role, every gap is on the spacing scale, every raise uses
the one declared depth metaphor. The variants are conformant by construction, so a
person choosing between them cannot accidentally choose drift. A generator free to
propose anything is the fastest route yet out of the system it is meant to hold —
and `selftest.py` asserts every generated value is declared, because this file is
the one place where the tool writes rather than reads.

Where the project has a custom property for a declared value, the variant emits
`var(--color-canvas)` rather than the literal. That distinction is not cosmetic: the
check caught this generator writing raw hex, and a literal in a rule is a token that
escaped — it will not follow the theme, it will not flip in dark mode, and nobody
will find it again.

**One axis at a time.** Three variants that each move type, colour, spacing and
depth together cannot tell you which change did the work, so "why did you pick B"
becomes "it looked better" — which is not a decision anyone can build on. Each
variant names the single axis it moves and what that axis decides.

The axes are read off the contract: `type-up`, `type-down`, `space-loose`,
`space-tight`, `surface`, `emphasis`, `depth`, `radius-card`, `radius-control`. A
plain-language steer picks among them — `--direction "bolder"`, `quieter`,
`tighter`, `roomier`, `lift`, `flatter`. A direction with no matching axis is
**reported as unmatched** rather than approximated, because three variants labelled
"brutalist" that are really three font sizes is how a person stops trusting labels.

**Ambiguous source refuses.** The element has to resolve to exactly one place by a
distinctive anchor — its text first, since that is what the person was reading, then
its classes. Zero matches or several, and it says which anchors it tried and how many
each hit, and stops. Writing to the wrong line is worse than not writing, because the
wrong line still looks like success: the edit is plausible, the page does not change,
and the next twenty minutes go on wondering why.

**Accept is measured, not merely chosen.** The edit is applied to a copy of the
tree, the static tier runs against it, and a variant that introduces a **P0 or P1**
finding is refused with the measurement quoted:

```
REFUSED. This variant introduces 2 P0/P1 finding(s):
  P1  S-CONTRAST-PAIR  src/styles/tokens.css:7
    #b8b8b8 on #ffffff
    Contrast 1.98:1 is below the 4.5:1 floor for normal text (NUM-001).
```

Taste chooses between admissible options. It does not get to make an inadmissible
one admissible. That gate had a real bug worth knowing about: it graded findings by
reading a `severity` field, findings carry no severity — it is a property of the
**rule**, in the registry — so nothing was ever graded blocking and the gate accepted
grey on white at 1.98:1 while printing a tidy summary. `selftest.py` now asserts the
grading is non-empty and that contrast grades P1, with a control proving the
assertion fails when the grading goes inert.

## Where the accepted change goes

Into the stylesheet that already defines the project's tokens, as one commented rule
scoped to a class the element already has.

Not a new file: a rule in a file nobody imports is a change that does not happen,
and a tool that creates `deuxui-overrides.css` has moved the problem rather than
solved it. Not a merge into an existing rule either — a merge silently changes
whatever else used it. And never an invented class name, because then the change is
half-applied: present in the stylesheet, absent on the screen.

If the element has no class distinctive enough, it says so and stops. `--into PATH`
and `--scope '.selector'` override both decisions when you know better.

## It is still gated, and it is still recorded

`accept` asks the phase gate before writing. Production UI edits wait until somebody
has used a prototype and accepted it — see [phase.md](phase.md) — and `--force`
writes anyway, on the record.

Every accept writes a decision to `.deuxui/decisions/` carrying the axis, the
declarations, the file and scope it was written to, the element's source location,
the check delta, and the **hash of the contract it was decided against**. The
contract's bytes are archived at the same moment, so `ux_ledger.py show DEC-003`
can print what was declared when the change was accepted rather than what is
declared now. See [ledger.md](ledger.md).

An accept is not a build approval: `approves_a_build: false`. It changed one
element's rule; it did not say the surface is ready.

## Copy, and structure

`accept` moves declared values. Two other verbs change things values cannot reach, and
both go through the same refusal discipline.

```bash
# what it SAYS
python3 scripts/ux_live.py text REQ-001 --to "Pricing that scales with you" --who "NAME"

# what it SITS IN
python3 scripts/ux_live.py wrap REQ-001 --with div --attr 'className="hero"' --who "NAME"
python3 scripts/ux_live.py insert REQ-001 --where after \
        --markup '<p className="sub">Billed monthly, cancel any time.</p>' --who "NAME"
```

`text` requires the element to have been located by its **text**, and that the string
appear exactly once in the file. It then reports every other place the same literal
appears and leaves them alone — a translation catalogue keyed on the English string is
the coupling this exists to surface, and renaming six files because one word matched is
not something a tool should do on its own.

`wrap` and `insert` need the element's **boundaries**, not just its line, and scanning
for `<` and `>` does not survive real code. Each of these is an angle bracket that is
not a tag boundary:

```jsx
<button onClick={() => setOpen(!open)}>   // an arrow in an expression
<Cell value={a > b ? a : b} />            // a comparison in an expression
<p title="a > b">                         // a bare > in an attribute string
const [x] = useState<Row[]>([])           // a TypeScript generic
{/* <Legacy /> was here */}               // a tag in a JSX comment
```

`jsxspan.py` scans past all of them and then **verifies** what it found: the span opens
and closes with the same tag, contains the picked text exactly once, is balanced inside,
and its tag agrees with the tag the browser reported for the element. That last check
matters more than it looks — a `<section>`'s innerText starts with its first heading's
text, so without it, picking the section and asking to wrap it wrapped the `<h1>`
instead. The edit applied cleanly and read correctly in the diff.

Anything it cannot verify is a refusal with the reason, and nothing is written. Markup
you pass to `insert` is measured by the static tier first and refused on a new P0 or P1:
a clickable `div` is a finding whether this skill generated it or you typed it.

## Editing copy in the page itself

`text` takes the new wording on the command line, which is the wrong end of the
problem: the person who knows a label is wrong is looking at the label, not at a
terminal.

```bash
python3 scripts/ux_live.py edits watch          # Alt-click any text and rewrite it
python3 scripts/ux_live.py edits list           # the batch, each resolved to a file
python3 scripts/ux_live.py edits apply --who "NAME"
python3 scripts/ux_live.py edits discard
```

Nothing reaches the source while you type. What lands in the page is a DOM change
that disappears on the next reload; the source edit is a separate, checked, recorded
step — an in-page editor that wrote straight to disk would be a way around every gate
this skill has.

`apply` runs the static tier over the whole batch before writing anything, so copy is
checked like anything else: an error message rewritten to "Something went wrong" comes
back refused with `S-CONTENT-ERRORTEXT` quoted. Each edit resolves independently, so
one refusal does not discard the rest, and a refused edit **stays staged** rather than
vanishing.

Three things it refuses, and each one is a copy edit landing on the wrong string:

- the text appears more than once in the source, so there is no single occurrence;
- the element was located by its class rather than its text;
- the element's text spans more than one source string — `locate` matched a prefix,
  and replacing a prefix with the full new wording leaves the tail of the old one
  behind, while trimming the new wording invents a cut point. Neither is knowable
  from here.

## What this is not

It has no framework adapter and no AST, so it resolves textually and refuses where a
compiler would succeed — markup inside a conditional or a `.map()` callback only
resolves when the anchor is unique. It does not check HTML nesting validity: a `<p>`
placed inside an `<h1>` lands where you asked and no detector currently objects.

Originating a whole surface is [shape](shape.md) or [prototype](prototype.md); changing
the system itself is [colorize](colorize.md), [typeset](typeset.md) or
[layout](layout.md).

It also does not revert. `discard` forgets the session; the rule already written stays,
and git is what takes it back out.

## Verify

```bash
python3 scripts/ux_live.py status            # what is open, what was accepted
python3 scripts/ux_check.py .                # the rule is in the source now
bash scripts/ux_delta.sh http://localhost:5173   # and did it help
```
