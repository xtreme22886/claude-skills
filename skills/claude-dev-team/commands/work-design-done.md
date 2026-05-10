---
name: work-design-done
description: Mark the design phase complete and unlock implementation. Updates .claude/current-work.json phase from design to implement, prompts to record any non-obvious design decisions as ADRs. Use when the user has finished thinking through how to approach the slice and is ready to write code.
---

# /work-design-done

You're the phase-transition command from design to implement. Cheap and quick — just a checkpoint.

## Prechecks

1. Read `.claude/current-work.json`. If missing, refuse: "No active slice. Start one with `/work-start`."
2. Confirm `phase == "design"`. If `implement`, no-op with a friendly note. If `review` or `done`, refuse: "Slice has moved past design. Use `/work-rethink` if you need to back up."

## Optional: capture design decisions

If the user mentions any non-obvious design decisions during the design conversation, ask: "Any of these worth an ADR? I can capture them now via `/grill-with-docs`." Don't push — the user knows what's load-bearing.

## Update current-work.json

- `phase: "implement"`
- `last_phase_change_at: <ISO>`

## Log

Append to `.claude/events.jsonl`:
```json
{"ts": "<ISO>", "event": "phase_transition", "issue_id": "<id>", "from": "design", "to": "implement"}
```

## Final output

- Confirm phase is now `implement`.
- Suggest the user kick off the TDD loop via the `tdd` skill if applicable.
- Reminder: vertical slice — touch every layer this slice needs to, but only what this slice needs.

## Don'ts

- Do not write any code. This is a metadata transition only.
- Do not push or commit anything.
