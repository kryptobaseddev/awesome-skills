# Remotion — a surface with different rules

A Remotion composition renders frames. There is no hover, no focus, no keyboard, no
zoom, no reflow, and no user in the loop at all. Applying interaction rules to it would
produce confident nonsense, so the checks classify Remotion files as the `video` surface
and mark the interaction families **NOT_APPLICABLE** rather than passing or failing them.

What still applies is everything about legibility, timing and honesty.

## Text is burned into pixels

No one can zoom it, select it, or let a screen reader read it.

- **Size for the smallest playback surface.** `S-VIDEO-LEGIBILITY` flags `fontSize`
  under 28px, because a 1080p composition is routinely watched at a third of that on a
  phone, after platform compression.
- **Contrast is still contrast.** Text over footage needs a scrim, a plate or a shadow
  — and the worst frame of the shot is the one that has to pass, not the first.
- **Safe margins.** Keep text well inside the frame; players, captions and platform
  chrome crop the edges.
- **Check every aspect ratio you export.** Text centred for 16:9 is often cut in 9:16.

## Timing is a readability budget

`S-VIDEO-LEGIBILITY` flags `durationInFrames` under 45 (about 1.5s at 30fps). A caption
that leaves before the viewer finishes the first line was never shown. Read it aloud at
a natural pace — that is the minimum, not the target.

## Accessibility of the output

The rendered file is where A11Y-007 lands:

- Ship a caption track (`.vtt`) alongside the video, or burn in captions where the
  platform gives you no track.
- Do not rely on colour alone to distinguish series in an animated chart.
- Avoid rapid flashing — more than three flashes per second is a seizure risk, and it
  is the one defect here that can genuinely hurt someone.
- Anything essential in the audio needs a visual equivalent, and the reverse.

## The player is a UI

The composition is not interactive; the page embedding it is. `<Player>` and any
surrounding controls are ordinary interface and every normal rule applies — accessible
names on the controls, visible focus, 44px targets, captions available, and never
autoplaying with sound.
