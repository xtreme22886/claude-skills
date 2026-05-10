---
name: second-opinion
description: Spawn an independent subagent to give a fresh take on a question, design choice, or piece of code. The subagent has no context from the current conversation — it sees only what you brief it with — so it can't be biased by the rationalization built up in the main thread. Use when the user wants a sanity check on a big architectural call, a tricky migration, or when they suspect Claude has been talking itself into something.
---

# /second-opinion

You're the independent-second-opinion command. The whole point: a fresh Claude that hasn't been part of the conversation. Use it when the answer would benefit from an uncontaminated perspective.

## Argument

The question or topic to get a second opinion on. Free text.

## Brief the subagent properly

This is the load-bearing part. The subagent has no conversation context. It only knows what you tell it. So:

1. State the question or decision concisely.
2. Provide the *minimum* context needed to evaluate it: the relevant files, the constraints, the goal.
3. **Do NOT include your own analysis or preferred answer** — that's exactly the bias we're trying to avoid.
4. Ask for: an honest assessment, the strongest argument against the current direction, and what they'd do differently.

Example brief:

> Reviewing migration 0042. Context: adding NOT NULL column to a 50M-row users table. Plan is to: (1) add column nullable, (2) backfill in batches of 10k, (3) ALTER to NOT NULL. Concurrent writes happen continuously (~200 rps). Question: is this approach safe? What's the strongest argument it might not be? Don't tell me what I want to hear.

## Spawn the subagent

Use the `Agent` tool with `subagent_type: general-purpose` (or a more specialized type if applicable — e.g. `code-reviewer` for code questions). Run in the foreground — we want the answer before continuing.

## Surface the response

Print the subagent's response verbatim, prefixed with `=== Second opinion ===`. Then offer your own brief reaction:
- "I agree with X, disagree with Y because Z."
- Or: "This raises a point I hadn't considered: ..."

Don't dismiss the second opinion just because it conflicts with your earlier answer. The whole point was to get a perspective free of the main thread's framing.

## Log

Append to `.claude/events.jsonl` if in a project context:
```json
{"ts": "<ISO>", "event": "second_opinion", "question_excerpt": "<first 100 chars>"}
```

## Don'ts

- Do not include your previous reasoning in the brief. The subagent will defer to it. Useless.
- Do not ask the subagent to make a final decision — it gives input, you decide.
- Do not run multiple second-opinion calls in a row to "average" them. If you don't trust the first one, your brief was probably bad — fix the brief.
