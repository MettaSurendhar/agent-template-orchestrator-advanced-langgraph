# Creating a Good README

[#creating-a-good-readme](#creating-a-good-readme)

If you fork this tier, be explicit that isolation is per-*team*, not per-user — this is the single most important thing for a reader evaluating whether this tier fits their needs, and it's easy to skim past if you don't call it out directly in the Overview.

Once the sibling AWS Strands repo is published, update the "Which tier do I need?" table's placeholder link — and keep both advanced tiers' feature lists in sync in your fork too, if you maintain both. A reader shouldn't discover a capability gap between them by trial and error.

If your fork disables Azure AD SSO entirely (local-auth-only), say so plainly rather than leaving the SSO documentation in as if it's always available — a reader configuring `AZURE_TENANT_ID` for a fork that doesn't actually support it wastes real time.
