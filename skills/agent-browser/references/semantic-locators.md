# Semantic Locators (Alternative to Refs)

When refs are unavailable or unreliable, use semantic locators:

```bash
agent-browser find text "Sign In" click
agent-browser find label "Email" fill "user@test.com"
agent-browser find role button click --name "Submit"
agent-browser find placeholder "Search" type "query"
agent-browser find testid "submit-btn" click
```

Semantic locators work well when:

- The page is dynamically rendered and refs go stale between snapshots
- You want a stable selector that survives layout changes
- You're targeting form fields by visible label text
- You're targeting buttons by accessible role + name
