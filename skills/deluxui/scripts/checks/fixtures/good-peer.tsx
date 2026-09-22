// The same four shapes, done right. Each must be SILENT -- these are the cases the
// field report showed being flagged while already correct, or passing while wrong.

// S-COMMIT-REVIEW: a real review step, in the interface rather than in a comment.
export function RealReview({ total }) {
  return (
    <form action="/pay" method="post">
      <h2>Review your order</h2>
      <p>Total {new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }).format(total)}</p>
      <button type="submit">Pay now</button>
    </form>
  );
}
