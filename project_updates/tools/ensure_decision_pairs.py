#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class PairResult:
    decision_path: Path
    response_path: Path
    created: bool
    reason: str


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _extract_decision_fields(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str, str]:
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    project_id = str(payload.get("project_id") or decision.get("scope", {}).get("project_id") or "").strip()
    created_at = str(payload.get("created_at_utc") or payload.get("created_at") or "").strip()
    return decision, project_id, created_at


def _safe_str(x: Any) -> str:
    s = str(x or "").strip()
    return s


def _write_response_md(response_path: Path, payload: Dict[str, Any]) -> None:
    decision, project_id, created_at = _extract_decision_fields(payload)

    tldr = _safe_str(decision.get("tldr"))
    rec = decision.get("recommendation") if isinstance(decision.get("recommendation"), dict) else {}
    rec_choice = _safe_str((rec or {}).get("choice"))
    rec_rationale = _safe_str((rec or {}).get("rationale"))

    options = decision.get("options") if isinstance(decision.get("options"), list) else []
    risks = decision.get("risks") if isinstance(decision.get("risks"), list) else []
    next_actions = decision.get("next_actions") if isinstance(decision.get("next_actions"), list) else []
    citations = decision.get("citations") if isinstance(decision.get("citations"), list) else []

    lines = [
        f"# Podcast Decision Response — {tldr or response_path.stem}",
        "",
        f"- Project: `{project_id or '(unknown)'}`",
        f"- Created: `{created_at or '(unknown)'}`",
        f"- Decision JSON: `{response_path.with_suffix('').with_name(response_path.name.replace('__response.md', '__decision.json'))}`",
        "",
        "## TL;DR",
        tldr or "(missing)",
        "",
        "## Recommendation",
        f"- Choice: {rec_choice or '(missing)'}",
        f"- Rationale: {rec_rationale or '(missing)'}",
        "",
        "## Options",
    ]

    if options:
        for opt in options[:8]:
            if isinstance(opt, dict):
                name = _safe_str(opt.get("name") or opt.get("option")) or "(option)"
                tradeoffs = _safe_str(opt.get("tradeoffs") or opt.get("pros_cons"))
                lines.append(f"- {name}" + (f" — {tradeoffs}" if tradeoffs else ""))
            else:
                lines.append(f"- {_safe_str(opt)}")
    else:
        lines.append("- (none)")

    lines += ["", "## Risks"]
    if risks:
        for r in risks[:12]:
            if isinstance(r, dict):
                risk = _safe_str(r.get("risk") or r.get("name")) or "(risk)"
                mitigation = _safe_str(r.get("mitigation"))
                lines.append(f"- {risk}" + (f" — Mitigation: {mitigation}" if mitigation else ""))
            else:
                lines.append(f"- {_safe_str(r)}")
    else:
        lines.append("- (none)")

    lines += ["", "## Next actions"]
    if next_actions:
        for a in next_actions[:12]:
            if isinstance(a, dict):
                action = _safe_str(a.get("action") or a.get("step")) or "(action)"
                owner = _safe_str(a.get("owner"))
                lines.append(f"- {action}" + (f" (owner: {owner})" if owner else ""))
            else:
                lines.append(f"- {_safe_str(a)}")
    else:
        lines.append("- (none)")

    lines += ["", "## Citations"]
    if citations:
        for c in citations[:25]:
            if isinstance(c, dict):
                ts = _safe_str(c.get("timestamp") or c.get("time"))
                quote = _safe_str(c.get("quote") or c.get("text"))
                if ts or quote:
                    lines.append(f"- {ts + ': ' if ts else ''}{quote or json.dumps(c, ensure_ascii=False)}")
                else:
                    lines.append(f"- {json.dumps(c, ensure_ascii=False)}")
            else:
                lines.append(f"- {_safe_str(c)}")
    else:
        lines.append("- (none)")

    response_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def ensure_pairs(*, repo_root: Path, apply: bool) -> list[PairResult]:
    decisions_dir = repo_root / "development" / "decisions"
    if not decisions_dir.exists():
        return []

    results: list[PairResult] = []
    for decision_path in sorted(decisions_dir.glob("*__decision.json")):
        if not decision_path.is_file():
            continue
        response_path = Path(str(decision_path).replace("__decision.json", "__response.md"))
        if response_path.exists():
            results.append(PairResult(decision_path=decision_path, response_path=response_path, created=False, reason="exists"))
            continue

        payload = _read_json(decision_path) or {}
        if apply:
            response_path.parent.mkdir(parents=True, exist_ok=True)
            _write_response_md(response_path, payload)
        results.append(
            PairResult(
                decision_path=decision_path,
                response_path=response_path,
                created=apply,
                reason="created" if apply else "would_create",
            )
        )
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="Ensure every development/decisions/*__decision.json has a paired __response.md.")
    ap.add_argument("--root", default=".", help="Repo root (default: .)")
    ap.add_argument("--apply", action="store_true", help="Write missing response files (default is dry-run)")
    args = ap.parse_args()

    repo_root = Path(args.root).resolve()
    results = ensure_pairs(repo_root=repo_root, apply=args.apply)

    created = sum(1 for r in results if r.reason in {"created"})
    missing = sum(1 for r in results if r.reason in {"would_create"})
    total = len(results)

    print(f"Repo: {repo_root}")
    print(f"Decisions scanned: {total}")
    if args.apply:
        print(f"Response files created: {created}")
    else:
        print(f"Missing response files: {missing}")
        print("Dry-run only. Re-run with --apply to write files.")

    if missing and not args.apply:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

