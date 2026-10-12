import { createFileRoute } from "@tanstack/react-router";

const titles = { library: "Proof point library", shortlist: "Seller shortlist" } as const;

export const Route = createFileRoute("/")({
  head: ({ match }) => ({
    meta: [{ title: `${titles[match.search.view]} | Huron` }],
  }),
  component: () => <main><h1>Proof points</h1></main>,
});
