# Testing Blockers

- Cannot install Vitest or other npm packages (network access to registry.npmjs.org is blocked). Attempts via `npx vitest --help` fail with ENOTFOUND.
- Until the runner is available, frontend unit tests (HUD, store) and Playwright smoke tests remain on hold.
- Reminder: once network access returns, add `vitest`, `@testing-library/svelte`, and configure `npm test` alongside existing pytest suite.
