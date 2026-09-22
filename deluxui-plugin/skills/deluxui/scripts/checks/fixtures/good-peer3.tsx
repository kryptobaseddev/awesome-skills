// S-TRUST-DESTRUCT: a foreign-key referential action. Nobody can press it, there is
// nothing to confirm, and no edit to this file makes a finding go away.
export const jobs = pgTable("jobs", {
  id: uuid("id").primaryKey(),
  siteId: uuid("site_id").references(() => sites.id, { onDelete: "cascade" }),
  ownerId: uuid("owner_id").references(() => users.id, { onDelete: "set null" }),
});
