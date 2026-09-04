# Project guidance

Before planning or implementing this project, read `PROJECT_CONTEXT.md`.

Treat that document as the durable product and architecture brief for the SEO/AEO Audit Agent. Keep it current when the product scope, architectural decisions, or MVP boundaries change materially.

Do not present inferred details about Dual7's private implementation as confirmed facts. Preserve the distinction between:

- capabilities stated in the supplied Dual7 product copy;
- reasonable architectural inferences; and
- decisions made specifically for this project.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
