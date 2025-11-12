# Testing Strategy

## Current Coverage Snapshot

- **Backend**
  - `process_interaction_test.py`: time-stop intent matching, score/life deltas for correct, incorrect, and wrong-language responses.
  - `streaming_session_test.py`: `StreamingSession` reward/penalty bookkeeping.
  - WebSocket smoke tests: `/stream/mock` and `/stream/interaction` (partial, penalty, final).
- **Frontend**
  - No automated runner yet (Vitest pending); `npm run check` surfaces type/a11y issues.
  - Manual streaming sanity flows via demo UI.

> **Gaps:** No frontend unit/e2e tests, no provider harness, limited scenario fixtures; Python tests cover only one/two scenario configs.

## Gaps & Priorities

### High-Priority Additions

1. **Frontend unit tests** *(blocked: Vitest install — no network access to npm registry right now)*
   - Set up Vitest + `@testing-library/svelte` when dependency installation becomes available.
   - Tests: `ScenarioStatus` HUD updates; `ScenarioDisplay` penalty/final handling; `storyStore` mode/lives reset logic.
2. **Scenario fixtures**
   - Author beginner/advanced JSON fixtures with different rewards/penalties; reuse across backend & frontend tests.
3. **End-to-end smoke tests**
   - Introduce Playwright/Cypress to verify time-stop & streaming flows end-to-end with stubbed backends.
4. **Provider harness (Milestone M2)**
   - Run streaming providers with sample audio, log latency/accuracy, generate regression CSV/JSON.
5. **Negative/backstop tests**
   - Add pytest coverage for missing scenario metadata (defaults) and penalty overrides.
   - Validate error payloads (`scoreDelta`/`livesDelta`) for fallback paths.

## Next Actions

- [ ] Add Vitest + testing-library dependencies and base test for `ScenarioStatus.svelte` (blocked until dependency install is allowed).
- [ ] Update `npm run check` script (or add `npm test`) to run Vitest once available.
- [ ] Address outstanding Svelte type/a11y warnings (see `npm run check` output).
- [ ] Expand pytest coverage for scenario schema parsing (mode defaults, penalty overrides).
- [ ] Plan Playwright smoke tests (time-stop + streaming paths) once Vitest is in place.

This document should be updated whenever new test suites are introduced or major coverage areas change.
