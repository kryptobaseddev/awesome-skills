# Motion

## The band

120–240ms for almost everything. Under about 100ms a transition is not perceived
as motion, only as a flicker; over about 300ms the interface is making the user
wait to watch an animation they have seen before. The contract declares
`motion.duration_ms`, and `S-CONTRACT-MOTION` and `S-CRAFT-MOTION` measure against
it.

Longer is defensible in exactly two places: an element travelling a long distance
across a large screen, where the eye needs to follow it, and a deliberate, once-per
-session moment. Everything else that is slow is slow by accident.

## Easing says what kind of thing is moving

Exponential ease-out — fast at the start, settling at the end — is right for almost
all interface motion, because it matches how a thing with momentum arrives. Linear
reads as mechanical. Bounce and elastic read as a toy, and on the fourth viewing
they read as an obstruction.

`S-CRAFT-EASING` flags `linear` on transitions and the spring/bounce families where
the product is not a game.

## One authored moment

A product gets roughly one piece of motion that is *designed* rather than
functional — a considered entrance, a satisfying confirmation, one transition that
carries meaning. The contract declares `motion.authored_moments: 1`.

The failure this prevents is the scroll-triggered fade-up on every section, which
is not a design decision made eleven times; it is a default applied to a list. It
also has a cost nobody accounts for: content hidden at rest, waiting for an
observer that may never fire on a fast scroll, on a reduced-motion setting, or when
the JavaScript fails — so the text is simply gone. `S-CRAFT-HIDDEN-AT-REST` catches
exactly that pattern, and it is a content-availability defect before it is a craft
one.

## Reduced motion is not "no motion"

`prefers-reduced-motion: reduce` means the user gets migraines, or vertigo, from
large-area movement, parallax and spin. It does not mean they want state changes to
happen invisibly. Replace the movement with a cross-fade or an instant change —
never remove the feedback entirely, because an interface where nothing acknowledges
a click is a worse experience than one that moves.

`S-MOTION-REDUCE` flags animation with no reduced-motion path, `R-MOTION` measures
whether the running page actually respects the setting, and `S-IOS-REDUCEMOTION`
and `S-AND-REDUCEMOTION` do the native equivalents.

## Motion that carries information

The motion worth writing is the motion that answers a question the user would
otherwise have to work out:

- Where did this come from? A dropdown that grows from its trigger.
- Where did it go? A dismissed item that leaves in the direction of the undo.
- What is related to what? A shared element that persists across a route change.
- Is anything happening? A pending state that appears within 1 second
  (`NUM-014`, `S-STATE-LOADING`) — see [states.md](states.md).

Motion that answers no question is decoration, and decoration on a screen someone
uses forty times a day is a tax.

## Performance is part of craft here

Animating anything other than `transform` and `opacity` forces layout or paint per
frame, and on a mid-range Android that is the difference between smooth and
visibly stepped. A layout shift caused by content arriving is measured directly as
CLS (`R-VITALS`), and the most common cause is an image with no intrinsic size —
`S-PERF-IMGDIM`, one line to fix.

## Adjudicated by

`S-CONTRACT-MOTION` · `S-CRAFT-MOTION` · `S-CRAFT-EASING` ·
`S-CRAFT-HIDDEN-AT-REST` · `S-MOTION-REDUCE` · `S-PERF-IMGDIM` · `R-MOTION` ·
`R-VITALS` · `S-IOS-REDUCEMOTION` · `S-AND-REDUCEMOTION` · `S-IOS-TRANSITION`
