# Development Notes

Working directory for long-lived plans, design decisions, and research spikes. Each page keeps links to its neighbors so we can see how a choice in one area ripples through the rest of the experience.

- [UX Vision](./ux.md) — north-star experience and current UX decisions.
- [Scenario Progression](./scenario-progression.md) — how difficulty and time-stop streaming evolve.
- [Streaming Architecture](./streaming-plan.md) — technical path to live audio feedback.
- [Testable Milestones](./testable-milestones.md) — bite-sized, validated checkpoints.
- [Open Questions](./open-questions.md) — issues we still need to resolve.
- [Decision Board](./decision-board.md) — product/policy decisions only you can make.
- [Transcription Provider Strategy](./transcription-plan.md) — provider-agnostic transcription design and config.
- [Provider Benchmarks](./notes/provider-benchmarks.md) — runbook + logbook for transcription latency comparisons.
- [`/demo` Smoke Checklist](./demo-smoke.md) — quick M4 mode-toggle sanity checks.
- [Code Map](./code-map.md) — quick “where do I look?” guide.
- [Contracts](./contracts.md) — frontend/backend payload contracts.
- [North Star Execution](./north-star-execution.md) — turning the vision into MVP milestones.
- [Import Scaling](./import-scaling.md) — resource model, caching/dedupe layers, and privacy-friendly waste reduction.
- [Deployment](./deployment.md) — production topology, persistence, WebSockets, and scaling notes.
- [Security Audit](./security-audit.md) — M6 threat model, vulnerability review, and hardening checklist.
- [Session Artifacts](./session_artifacts/README.md) — end-of-session snapshots (generated via `python3 tools/close_session.py`).

## Action Items

- [ ] Keep this index updated whenever we add or retire a planning doc.
- [ ] Cross-link any new research notes so nothing drifts out of context.
