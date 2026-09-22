/**
 * THIS FILE CONTAINS NO COLOUR AT ALL. From the 5.24.4 field report, where
 * S-TOKEN-HEX reported five P1 findings on it.
 * Fixed in #856 after #840 and #832 landed. See also #779 and #721.
 */
export function NoColoursHere() {
  // React error #310: rendered more hooks than during the previous render.
  return (
    <p className="text-ink">
      Lot&#8212;number&#8203;separator, mailbox #4784, invoice #2026.
    </p>
  );
}
