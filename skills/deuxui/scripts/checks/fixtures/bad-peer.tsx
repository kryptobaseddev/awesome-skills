// Field-reported false negatives and false positives, each in its own window so an
// unrelated word elsewhere in a crowded fixture cannot decide the outcome.

// S-COMMIT-REVIEW: the only mention of a review step is in a COMMENT. A comment is
// never shown to anyone, so it cannot be the disclosure, and letting it silence the
// check makes deleting the explanation of a fix the cheapest route to a green run.
export function PayWithoutCheck({ total }) {
  // The operator will review the order summary and confirm before this runs.
  return (
    <form action="/pay" method="post">
      <p>Total {new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }).format(total)}</p>
      <button type="submit">Pay now</button>
    </form>
  );
}
