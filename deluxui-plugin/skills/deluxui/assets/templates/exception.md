# Exception record — EXC-<n>

For `.deluxui/exceptions.yaml`. An exception may lower a **PROJECT**-class default.
It may **not** make a failed **STANDARD** report as passing — a WCAG criterion your
product does not meet is a criterion your product does not meet. You may decide to
ship it; that decision belongs here where someone can see it, but it stays visible in
the matrix.

```yaml
exception_id: EXC-001
rule_id: NUM-005
rule_class: PROJECT          # STANDARD-class rules are not eligible
scope: "The column-header sort controls in the trade blotter, desktop only"
reason: >-
  The blotter shows 40 rows above the fold on the screens traders actually use.
  A 44px header row costs eight of them, and scrolling during a price move is the
  failure this view exists to prevent.
alternatives_considered:
  - "Larger targets with a compact toggle -- rejected, the compact mode became the
     default within a day and the exception moved rather than went away"
  - "Sort from a menu -- rejected, adds two interactions to the most frequent action"
user_impact: >-
  Coarse-pointer users get a 32px target. The view is desktop-and-mouse only in the
  support matrix; the mobile app sorts from a full-height sheet.
safety_and_accessibility_impact: >-
  NUM-004 (24px, STANDARD) still passes. Keyboard sorting is unaffected. No
  accessibility criterion is waived by this record.
compensating_controls:
  - "Keyboard sort on every column, documented in the shortcut sheet"
  - "8px spacing between adjacent header targets"
owner: "the trading-tools team lead"
approved_by: "the accessibility reviewer"
approved_at: "2026-09-20"
expires_or_review_on: "2027-03-20"
status: APPROVED             # PENDING | APPROVED | EXPIRED
retest_evidence: []
```

An exception with no expiry is a permanent decision disguised as a temporary one. Give
it a review date.
