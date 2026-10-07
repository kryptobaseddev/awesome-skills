# Source notes and authority

## Owner-supplied foundation

Reviewed all five Native Chat Workspace deliverables dated 2026-10-05:

| File | Treatment |
|---|---|
| `native-chat-development.md` | Main proposed architecture and N01–N14/A01–A25 contracts; condensed into focused references |
| `native-chat-development.html` | Readable companion with navigation, diagrams and private screenshot references; not executable chat software |
| `implementation-checklist.md` | Bundled with relative link and scenario-pointer adjustments |
| `README.md` | Deliverable map, package-verification and privacy boundaries |
| `workspace-reference.css` | Bundled verbatim as optional Tailwind CSS 4 asset |

Original-file checksums are in [source-manifest.json](source-manifest.json). References are portable and require no owner's absolute paths. Private screenshots/account data are intentionally not bundled.

The source's Resend inspection established frontend workspace patterns, not its private model, database or deployment topology. Its inspected chat used a different SDK; TanStack AI is the owner's chosen implementation. Numeric dimensions, context limits and quotas are proposed defaults. Neither source docs nor this skill are evidence that an application passed release tests.

## Current-source checks

Consulted official TanStack documentation on 2026-10-05. Use links in the integration reference as live navigation, then verify the target project's installed release. In particular:

- Prefer the current interrupt approval model over deprecated examples where the installed release supports it.
- Evaluate SDK server/client persistence surfaces before implementing custom transcript machinery.
- Keep delivery replay separate from ordinary producer survival. Sandbox-specific takeover capability does not establish takeover for arbitrary app chat.

The scaling guide adds application engineering methods such as workload modeling, fair admission, bounded queues, fencing and cost reconciliation. Those are recommendations to implement and verify, not claims that TanStack automatically provides them.

If SDK docs, snippets and declarations disagree, inspect the installed runtime source and release notes, record the discrepancy and compile/test the selected behavior. Do not silently combine release generations. The CSS reference likewise requires the selected Tailwind pipeline and a real workspace controller.
