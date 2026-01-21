# Project Updates Archive

This folder stores **versioned, portable “project upgrade” artifacts** so you can apply the same standards to other repos and still understand *why* each standard exists.

## Naming schema

All files are date-prefixed so “latest” is obvious when sorted:

- `YYYY-MM-DD__langhero__workflow-standards.md`
- `YYYY-MM-DD__langhero__project-upgrade-prompt.md`

Rules:
- Use **UTC date** (`date -u +%F`).
- If you publish multiple revisions in one day, add a suffix: `...__r2.md`, `...__r3.md`.

## Latest

- Workflow standards: `project_updates/2025-12-28__langhero__workflow-standards.md`
- Upgrade prompt: `project_updates/2025-12-28__langhero__project-upgrade-prompt.md`

## How to add a new entry

1. Copy the latest file.
2. Update the **Context / What changed / Why** sections.
3. Link to prior versions under **Previous versions** so the rationale chain stays intact.
4. Update this README “Latest” section.
