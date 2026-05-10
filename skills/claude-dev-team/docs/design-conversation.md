# Design conversation transcript

Original grilling session that produced the claude-dev-team bundle. Exported from the local Claude Code transcript cache. Read alongside `DESIGN.md` for the full context behind every design decision.

Tool calls (file writes during the scaffolding phase) have been omitted for readability — only user prompts and assistant text replies are included.

---

## **User**

Base directory for this skill: /home/xtreme/.claude/skills/grill-me

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time.

If a question can be answered by exploring the codebase, explore the codebase instead.


ARGUMENTS: I'm going to be working on a large project that involves several smaller tasks/projects. I want to setup a team of agents that'll help with this project. for example, i want an agent to orchestrate tasks between other agents. there should be an agent that knows the full scope of the project and keeps all other agents on task. an agent for tracking issues, an agent for testing, an agent for debugging, an agent for coding, an agent for reviewing, an agent for keeping track of progress, an agent to keep track of to do. I basically want an entire software developement team in agent form that utilize best practice developement practices and techniques. if there are tool we should incorporate like GitHub for trackig issues or a ticketing system for features, or whatever. work out what would be best to achieve a team of agents that'll work together to develop, design, code, test, debug, etc the project we will be working on. it could any project. current or future. perhaps we can build a skill out that we can use to incorporate this team into new projects to ahcieve the same level of software developement.

---

## **Claude**

Let's start at the foundation, because the rest of the design hinges on it.

**Q1: What do you mean by "agent" here?**

In Claude Code there are several distinct primitives that people sometimes lump together as "agents," and they behave very differently:

- **Subagents** (`Task` tool) — short-lived, spawned to do one job, return a single result, then vanish. No memory of prior runs, no inbox, can't be "talked to" again.
- **Skills** — bundled instructions + tools the main Claude invokes (e.g. `tdd`, `review`, `diagnose` already exist).
- **Hooks** — shell commands the harness fires on events (PreToolUse, Stop, etc). Deterministic automation, not reasoning.
- **Slash commands** — user-triggered workflows.
- **Scheduled / cron agents** — fire on a schedule, run remote.
- **Separate Claude Code sessions** — independent conversations, no shared state unless you write to disk/GitHub.
- **External orchestration via the Claude API** (CrewAI / AutoGen / LangGraph style) — long-lived "personas" that message each other through a queue you build yourself.

When you picture "an orchestrator that delegates to a coder, tester, reviewer that all stay aware of each other," you're describing the **last** option — and that is *not* how Claude Code works out of the box. The main session IS Claude; subagents don't persist; nothing "watches" the others. Trying to force that pattern inside Claude Code usually produces something slow, expensive, and brittle (every "handoff" reloads the world from scratch).

**My recommended answer:** drop the AutoGen/CrewAI mental model. Treat the **main Claude session as the only persistent intelligence** ("the team lead"). The "team members" are really:
- **Skills** for repeatable workflows (coder = default, tester = `tdd`, debugger = `diagnose`, reviewer = `review` / `security-review`, scope = `to-prd` / `to-issues`).
- **Subagents** for *parallelizable, read-heavy* work (research, exploration, independent reviews) — never for "ongoing roles."
- **GitHub Issues + Projects** as the shared brain (scope, todo, progress, bugs all live there — survives sessions, survives Claude restarts, you can see it too).
- **Memory + CLAUDE.md** for continuity across sessions.
- **One "kickoff" skill** that wires the conventions in for any new project.

That gives you the *behavior* you want (specialized, coordinated, scoped) without inventing a fragile multi-agent runtime.

**Does that reframing match what you actually want, or are you specifically after the "personas talking to each other" model?** If the latter, we need to talk about whether we're building inside Claude Code or building an external system on top of the Claude API — they're very different projects.

---

## **User**

i like your recommendation

---

## **Claude**

Good — locking in the reframing. Moving to the next branch.

**Q2: Where does the shared brain live — GitHub Issues, or something lighter?**

The "scope keeper / issue tracker / progress tracker / todo tracker" you listed are really one thing: a single source of truth that survives sessions and that every skill reads from and writes to. Three realistic options:

1. **GitHub Issues + Projects (board)** — issues for work items, labels for type (`bug`/`feature`/`chore`), a Project board for status (`backlog`/`in-progress`/`review`/`done`), milestones for scope. Free, durable, you can see it in a browser, `gh` CLI is already first-class. Survives across machines and across Claude rewrites. Best when the project is or will be in a git repo.
2. **Linear / Jira / other tracker** — nicer UI, more process. Worth it only if you're already paying for one or the project is multi-human. Adds an MCP/API integration burden.
3. **Local files in the repo** (e.g. `docs/backlog.md`, `docs/decisions/`) — zero dependencies, works offline, but no status board, no cross-project view, and gets messy fast.

**My recommendation: GitHub Issues + a Project board, plus `docs/adr/` for architectural decisions in-repo.**

Why: you already have skills built around this exact pattern (`to-prd`, `to-issues`, `triage`, `grill-with-docs` updates ADRs inline). They expect issues-as-units-of-work. Going local-files-only would mean reinventing what those skills already do; going Linear/Jira would mean rewriting them. Issues for *work*, ADRs for *why decisions were made*, CLAUDE.md/CONTEXT.md for *how the project works*.

One caveat: this assumes every project you'll use this on lives in a GitHub repo (or you're willing to `gh repo create` at kickoff). If some projects will be private/offline/not-on-GitHub, say so now — it changes the design.

**Does GitHub Issues + Projects + ADRs work as the shared brain, or is there a constraint (private code, no GitHub, team policy) that pushes us elsewhere?**

---

## **User**

instead of using a GitHub, could we utilize an internal GitLab server which we already have setup internally for work?

---

## **Claude**

Yes — GitLab works fine as the shared brain. The pattern is identical (Issues + Boards + Milestones + MRs); only the tooling changes.

**What shifts:**
- Replace `gh` CLI with `glab` (GitLab's official CLI — `glab issue create`, `glab mr create`, `glab issue board view`). Install once, point at your internal host with `glab auth login --hostname gitlab.yourcompany.com`.
- The existing `to-prd`, `to-issues`, `triage`, `review` skills are GitHub-flavored — they shell out to `gh`. We'll need to either (a) fork/adapt them to detect `glab` vs `gh` and branch, or (b) write thin GitLab-specific variants. Option (a) is cleaner long-term; option (b) is faster to ship.
- ADRs in `docs/adr/` stay exactly the same (just markdown in the repo).
- MRs (merge requests) replace PRs. Same review flow.

**One thing to confirm before we go further** — internal GitLab servers often have quirks that affect the design:

1. **API access from your machine** — can `glab` reach the internal host from wherever you'll run Claude Code? (VPN-only? Cert pinning? SSO that doesn't play nice with CLI tokens?)
2. **Personal access tokens** — do you have permission to mint a PAT with `api`, `read_repository`, `write_repository` scopes? Some corporate GitLabs lock this down.
3. **Webhooks / automation policy** — if we later want hooks that auto-comment on MRs or move board cards, is outbound automation against the internal server allowed by your team's policy?

**My recommendation:** GitLab as the shared brain, `glab` as the CLI, and we adapt the existing skills to be tracker-agnostic (detect `glab` first, fall back to `gh`). That way the same skill works on personal GitHub projects *and* work GitLab projects — important since you said "any project, current or future."

**Can you confirm `glab` works against your internal server from this machine (or that you can get it set up), and that you can mint a PAT? If either is a no, we need a different shared-brain story for work projects.**

---

## **User**

it would be nice to be able to have the option of using both GitHub and GitLab. Our GitLab instance is not publically available so would require us to be in the office or utilize a VPN connection. I do not have access to the GitLab server on the machine I am on now but my other machine does have VPN access. We can create access tokens in GitLab, that is not restricted. Since our internal GitLab server is not publically available, it makes things like CI/CD impossible. whereas that is possible with GitHub. But for security reasons, we prefer to keep code repos internal on our GitLab server.

---

## **Claude**

Locking in: **dual-tracker support, auto-detected per project.** Adapter layer so skills don't care which backend is live. CI/CD design must assume GitLab projects have *no remote CI* — runners are local-only.

**Q3: How do we decide which tracker a given project uses, and what happens when the tracker isn't reachable?**

Three realistic detection strategies:

1. **Git remote sniffing** — read `git remote get-url origin`. If the host matches your internal GitLab → use `glab`. If it's `github.com` → use `gh`. Unknown/none → ask once at kickoff and write the choice to `.claude/project.json` (or similar) so we never ask again.
2. **Explicit per-project config file** — `.claude/tracker.json` with `{ "tracker": "gitlab", "host": "gitlab.internal", "project_id": 1234 }`. Authoritative, no guessing, but requires kickoff to populate it.
3. **Ask every time** — annoying, rules out.

**My recommendation: #1 with #2 as the cache.** Sniff `origin` on first use, confirm with you, write the answer to `.claude/tracker.json`, never ask again unless the remote changes. Skills load that file and dispatch through a thin adapter (`tracker_create_issue`, `tracker_list_issues`, `tracker_create_mr_or_pr`, etc.) so the *workflow* skills (`to-issues`, `triage`, `review`) stay tracker-agnostic.

**The harder problem: reachability.** Your VPN-gated GitLab means the tracker will sometimes be unreachable — wrong machine, VPN down, working from coffee shop. Two failure modes to design for:

- **Read failure** (can't fetch issues) — Claude can still code, but loses scope/progress context. Bad.
- **Write failure** (can't create/update issues) — work happens, tracker drifts out of sync. Worse, because state diverges silently.

**My recommendation for offline-tolerance:** an **outbox pattern.** Every tracker write goes through the adapter, which:
1. Tries the live API call.
2. On failure (network, auth, host unreachable), appends the intended operation to `.claude/tracker-outbox.jsonl` and surfaces a yellow warning ("queued — 3 ops pending sync").
3. A `sync-tracker` slash command (or a hook on session start) drains the outbox when connectivity returns.

For reads, cache the issue list / board state into `.claude/tracker-cache.json` after every successful fetch, with a timestamp. When offline, Claude works from cache and *says so explicitly* in responses.

**Plus an explicit constraint we have to bake in:** GitLab projects get **no remote CI**. So the "reviewer" / "tester" agent flow has to be:
- **GitHub projects:** can rely on Actions running tests/lints on push, review skill can read CI status via `gh`.
- **GitLab projects:** all tests/lints/security checks run **locally** before push (pre-push hook, or a `verify` skill that runs the suite). Review skill reads local results, not remote.

Two sub-questions inside Q3 — answer whichever you have an opinion on, I'll recommend the rest:

**(a)** Are you OK with the outbox pattern for offline writes, or would you rather Claude just *block* and tell you "can't reach GitLab, reconnect VPN" instead of queueing? (Block is simpler, outbox is more forgiving.)

**(b)** For GitLab projects with no remote CI — should the `verify` step be **mandatory before MR creation** (pre-push hook refuses to push if `verify` fails) or **advisory** (Claude runs it, reports results, you decide)?

---

## **User**

actually, lets assume that we CAN use GitLab CI as all internal services should be able to reach the GitLab server

---

## **Claude**

Good — that simplifies a lot. Updating: **GitLab CI is on the table**, server-to-server reachability is fine, only *your dev machine* is sometimes off-VPN. So CI runs server-side as normal; the only offline concern is *Claude's* ability to read/write the tracker from a non-VPN machine.

Revised picture:
- **GitHub projects** → GitHub Actions for CI, `gh` for tracker.
- **GitLab projects** → GitLab CI for CI, `glab` for tracker, runners live inside the network so pipelines just work.
- **Offline tolerance** still needed, but only for *your* interactions when you're on the wrong machine — not for CI.

Let me re-pose the two sub-questions with that in mind, since the answers shift:

**(a) Offline writes from your dev machine** — when you're on this (no-VPN) machine and a skill wants to file an issue or comment on an MR against the internal GitLab, what should happen?
- **Block** — Claude refuses, tells you to switch machines / connect VPN. Simple, no drift, but interrupts flow.
- **Outbox** — Claude queues the write to `.claude/tracker-outbox.jsonl`, keeps working, syncs on next reachable session. Smooth, but state is briefly divergent and you have to trust the drain.
- **Read-only fallback** — Claude can read from cache, but any write attempt blocks. Middle ground.

**My recommendation: read-only fallback.** Reads from a stale cache are usually fine ("here are the open issues as of 2 hours ago — may be out of date"). Writes are where drift hurts — silently queueing an issue creation means you might file the same thing twice when you reconnect, or reference an issue number that doesn't exist yet. Better to block writes with a clear "switch to VPN machine to create this issue" message than to fake success.

**(b) Pre-push verification** — even with CI now available, do you want a local `verify` step (lint + typecheck + fast tests) to run **before** push, or rely entirely on CI?
- **Local pre-push** catches dumb mistakes in <30s instead of waiting 5 min for CI to fail and email you. But slows down every push.
- **CI-only** is faster per-push, but means broken pipelines clutter the MR and waste runner minutes.
- **Hybrid** — local `verify` runs only the *fast* subset (lint, typecheck, changed-file unit tests); CI runs the full suite.

**My recommendation: hybrid, enforced by a pre-push hook.** The hook runs a `verify-fast` skill (≤30s budget); CI runs everything. The reviewer skill reads CI status from the MR/PR, not from local. This keeps fast feedback local without duplicating the full suite, and CI remains the source of truth for "is this mergeable."

**Pick (a) and (b), and one follow-up:** for the hybrid hook in (b), should it be **blocking** (push refused on failure, must `--no-verify` to override) or **advisory** (warns but lets the push through)? I'd say **blocking with explicit override** — the whole point is to catch dumb mistakes, and if you really need to push broken code (WIP branch, debugging CI itself) `--no-verify` is right there.

---

## **User**

we should be forced to be "on" the network anytime we are actively developing/working on the project.

---

## **Claude**

Locking in: **network presence is a precondition, not a fallback.** No outbox, no cache-fallback, no offline mode. If GitLab isn't reachable for a GitLab-tracked project, Claude **refuses to start work** with a clear "connect to VPN / switch machines" message.

Concretely:
- A `preflight` check runs at session start (Stop hook → SessionStart hook, or first tracker-touching skill invocation): pings the tracker host, verifies auth token still valid, fails loud if either is broken.
- Removes ~half the complexity from the tracker adapter (no outbox, no cache reconciliation, no "stale data" warnings).
- GitHub projects skip the preflight (public internet assumed).

Carrying forward your earlier answer on **(b)**: hybrid pre-push verification, blocking with `--no-verify` override. Good.

---

**Q4: How does the main Claude session ("team lead") decide which skill / subagent to invoke for a given user request?**

You listed roles: orchestrator, scope-keeper, issue-tracker, tester, debugger, coder, reviewer, progress, todo. We've collapsed most of these to existing skills. But the *routing* — "user said X, which skill fires?" — is the part that makes it feel like a coordinated team vs. a pile of tools.

Three approaches:

1. **Implicit routing** — main Claude reads the user's message and picks the right skill based on the skill descriptions. This is what already happens today. Works well for obvious cases ("debug this" → `diagnose`), unreliable for ambiguous ones ("let's add user auth" — is that `to-prd`? `to-issues`? `tdd`? Just code?).

2. **Explicit kickoff convention** — every new piece of work starts with one of a small set of slash commands that establish *what mode we're in*: `/feature <description>`, `/bug <description>`, `/chore <description>`. The slash command writes a small state file (`.claude/current-work.json` with `{ issue_id, type, phase }`) and from then on every skill reads that file to know what to do. Phase transitions (`design → implement → review → done`) are explicit user commands.

3. **A dedicated "router" skill** — `/work <anything>` that asks 2–3 clarifying questions, files the right issue, picks the right next skill, and hands off. More magic, more failure modes, harder to debug when it picks wrong.

**My recommendation: #2, the explicit kickoff convention.** Reasoning:

- It mirrors how a real human team works — you don't just "start coding," you pick up a ticket, move it to In Progress, do the work, move it to Review, then Done. Making those phase transitions explicit *forces* the discipline you're after ("keep all other agents on task"). The phase IS the scope-keeper.
- It makes state observable. `cat .claude/current-work.json` tells you (and Claude) exactly what's being worked on, what phase, which issue. No need for a "progress agent" — the file IS the progress.
- It composes cleanly with hooks: a SessionStart hook can read `current-work.json` and remind Claude of context; a PreToolUse hook can warn if Claude tries to write code while phase is `design`.
- Implicit routing (#1) keeps working for *within-phase* decisions — once we're in `implement` phase, "fix this bug" still routes to `diagnose` automatically. We only need explicit commands at phase boundaries.

Concrete shape of the kickoff commands:

| Command | What it does |
|---|---|
| `/work-start <issue-ref or description>` | Resolves to issue (creates one if needed via `to-issues` flow), writes `current-work.json` with phase=`design`, checks out a branch. |
| `/work-design-done` | Phase → `implement`. From here, coding skills are unlocked. |
| `/work-review` | Phase → `review`. Pushes branch, opens MR/PR, runs reviewer skill, posts comments. |
| `/work-done` | Phase → `done`. Merges (or asks you to), moves issue to closed, clears `current-work.json`. |
| `/work-status` | Prints current state (issue, phase, branch, what's blocking). |
| `/work-pause` | Saves current state to a stash entry, clears `current-work.json` so you can pick up something else. |

**Two sub-questions:**

**(a)** Are you OK with the explicit-phase model, or does it feel too heavy / process-y for the kinds of projects you work on? (If your typical project is "small script, hack it out in an hour" rather than "feature shipped to production," this is overkill.)

**(b)** How strict should phase enforcement be? Three levels:
- **Strict** — PreToolUse hook *blocks* code edits during `design` phase, blocks merges before `review`, etc. Maximum discipline, most friction.
- **Advisory** — Claude warns but proceeds. ("You're in design phase — sure you want to edit code? [proceeding]")
- **None** — phase is informational only, used for status reporting and skill routing hints, never enforced.

My recommendation: **advisory by default, with a per-project setting to escalate to strict.** Solo hacking → advisory is plenty. Shared/work projects with real consequences → strict, so the process can't be accidentally skipped.

---

## **User**

most of the projects will mainly be me as the only human developer so it can be laxed. advising me instead of being strict is prefered

---

## **Claude**

Locking in: **explicit phase commands, advisory enforcement.** Claude warns when you do something out-of-phase but never blocks. Per-project setting exists to escalate to strict if you ever want it (e.g. a shared work project), default is advisory.

Concretely:
- Phase warnings come from a PreToolUse hook checking `.claude/current-work.json` against the tool being called. Hook returns a non-blocking notice, not a refusal.
- `/work-*` commands stay as listed.
- `/work-start` is also tolerant of "I just want to mess around" — invoking any code-editing tool with no `current-work.json` present produces *one* gentle nudge per session ("not tracking this work — `/work-start` to file an issue first, or ignore this and keep going"), then shuts up.

---

**Q5: When should the main Claude *delegate to a subagent* vs. just do the work itself?**

This is the part that determines whether your "team" actually feels like a team or just one Claude wearing different hats. Subagents are the only mechanism in Claude Code that gives you genuine parallelism and context isolation, but they're expensive — each one re-reads the world from cold, so overusing them is slow and burns tokens.

The honest rule of thumb: **delegate when the work is (a) read-heavy, (b) parallelizable with other work, or (c) needs a fresh perspective uncontaminated by the main thread's context.** Don't delegate just to feel "team-like."

Mapping that to your roles:

| Role | Delegate to subagent? | Why |
|---|---|---|
| **Coder** | No — main Claude does it | Writing code needs the full conversation context. A subagent would have to re-learn everything. |
| **Reviewer** | **Yes** — fresh subagent per review | Critical to have eyes that *haven't* seen the rationalization. Independent read = better catches. Already what `/review` and `/security-review` do. |
| **Tester (writing tests)** | No — same context as coder | TDD loop needs tight feedback with the implementer. |
| **Tester (running tests)** | No — just a Bash call | Not actually agent work. |
| **Debugger** | Sometimes | If reproducing the bug needs lots of exploration → subagent (Explore type) to investigate without bloating main context. If you already have a clear hypothesis → main Claude. The `diagnose` skill handles this. |
| **Issue tracker / scope-keeper / progress / todo** | No — these are file/CLI operations | Talking to GitLab/GitHub via `glab`/`gh` is just tool calls, no reasoning needed. The shared brain (issues + `current-work.json`) IS the scope-keeper; no agent required. |
| **Orchestrator** | No — this IS main Claude | Already established. |
| **Research / exploration** ("how does the auth flow work in this codebase?") | **Yes** — Explore subagent | Read-heavy, results-summarizable, would otherwise dump thousands of lines into main context. |

**My recommendation — codify this as three subagent types, used sparingly:**

1. **`reviewer`** — invoked by `/work-review` (and on demand). Reads the diff cold, has no idea why we made the choices we made, reports issues. Already exists as `/review` and `/security-review` — keep them.
2. **`explorer`** — invoked by main Claude any time a question requires reading >3 files or grepping a pattern across the repo. The built-in `Explore` agent type does this; we just need a convention that the main thread *uses* it instead of doing it inline.
3. **`independent-second-opinion`** — invoked manually via `/second-opinion <question>`. For when you (or main Claude) want a sanity check from a Claude that hasn't been part of the conversation. Rare but valuable for big architectural calls.

That's it. **No "tester agent," no "debugger agent," no "progress agent."** Those are skills running in the main thread, reading/writing the shared brain. The illusion of a team comes from skills + slash commands + the issue tracker, not from spawning agents.

This will probably feel like *fewer* agents than you originally pictured. That's the point — fewer moving parts, less token burn, less "wait, which Claude knows what?" confusion.

**One sub-question:**

Are you OK with this minimalist subagent palette (3 types, used surgically), or do you have a specific scenario in mind where you'd genuinely want a long-lived "tester agent" or "debugger agent" running alongside the main thread? If yes, describe the scenario — there might be a real need I'm collapsing away too aggressively.

---

## **User**

yes that minimalist palette is fine. I also want to make sure that we implement vertical slices. so instead of building out the entire databaes schema before incorporating ui changes, we should build out a section of the database schema, add it to the ui, test the ui and debug any issues. smaller chucks to test every new addition in detail before we make too many changes and have a harder time debugging/testing

---

## **Claude**

Locking in: **vertical slices are mandatory, not optional.** Every issue must cut through the full stack (DB → API → UI → test) end-to-end for a single narrow capability. No horizontal layers ("build all the schemas," "build all the endpoints"). This matches the existing `to-issues` skill's "tracer-bullet" framing — good, we're aligned with infrastructure that already exists.

Concretely, this changes a few things in the design we've built so far:

- **`to-issues` skill stays as-is** — it already enforces tracer-bullet vertical slices. We just make it the *only* sanctioned way to break down work. No "let me file 5 issues real quick" shortcuts that produce horizontal tickets.
- **`/work-start` gates on vertical-slice shape.** When you start an issue, Claude reads the issue body and checks: does this touch one capability end-to-end, or is it a horizontal layer? If horizontal, it warns ("this looks like a layer, not a slice — want to re-scope via `/to-issues`?"). Advisory, per your earlier preference.
- **`/work-review` checks slice integrity before opening the MR/PR.** A slice isn't done unless: (a) DB change is migrated, (b) API/service layer hits it, (c) UI surfaces it (if applicable), (d) at least one test exercises the path end-to-end. Reviewer skill flags missing layers.
- **`tdd` skill is the default implementation loop inside a slice.** Red → green → refactor, scoped to *just* this slice. Don't write tests for code the slice doesn't introduce.

---

**Q6: How small is a slice, and what's the escape hatch when one is genuinely too big?**

This is where vertical-slice discipline usually breaks down in practice. Two failure modes:

1. **Slices that are too big** — "add user authentication" sounds like one slice, but it's really login + signup + password reset + session management + UI for all of it. People file it as one issue, it sprawls for 2 weeks, debugging gets exactly as hard as the horizontal approach you're trying to avoid.
2. **Slices that are too small** — "add a database column" filed as its own issue, no UI, no test of the full path. You end up with horizontal work wearing a slice costume.

You need a sizing rule and an enforcement point.

**My recommendation — the "one-sitting" rule with a hard ceiling:**

- **Target size:** a slice should be completable in **one focused work session** (call it 2–4 hours, including tests). If it's bigger, it's not a slice yet — it's an epic.
- **Hard ceiling:** if `/work-start` opens an issue and Claude estimates >1 day of work, it warns and offers to `/to-issues` it into smaller slices first. Advisory, but loud.
- **Minimum viability:** a slice must produce a *user-visible behavior change* (or, for non-UI projects, an externally-observable behavior change — new CLI flag works, new API endpoint returns, new metric appears). "Added a column" alone is not a slice. "User can now save their timezone preference, persisted across sessions, visible in settings" is a slice — even though the implementation includes adding a column.
- **Escape hatch for genuinely-big slices:** an `epic` label on the issue, with sub-issues linked. The parent stays open until all children close. `/work-start <epic>` refuses and tells you to pick a child. This is the *only* sanctioned way to have work that spans multiple sessions.

This gives you the discipline without making you fight the tool every time something legitimately needs to be bigger.

**Two sub-questions:**

**(a)** Are you OK with the "one-sitting / user-visible behavior change" definition, or do you have a different mental model for slice size? (Some people prefer "one commit," some prefer "one PR no matter how long it takes" — both are worse, IMO, but you may have a reason.)

**(b)** For projects that *aren't* full-stack (a CLI tool, a library, a data pipeline) — the "DB → API → UI" framing doesn't map. What's the analogue?

My recommendation for (b): the slice rule generalizes to **"one externally-observable capability, fully wired and tested."** For a library: new public function + docs + test. For a CLI: new flag + handler + integration test invoking the binary. For a data pipeline: new transformation + upstream input shape + downstream output shape + a fixture-based test. The point is *something a user (or a calling system) can observe end-to-end*, not the specific layers.

Does that generalization hold for the kinds of non-full-stack projects you'll work on, or is there a project shape you're picturing where it breaks down?

---

## **User**

a) one sitting / user visible behavior change is fine. b) your recommendation is good

on a side note, we should also incorporate docs into the process so when projects ship, we have documentation built to help train other departments and troubleshooting guides to help them understand why something isn't working, what to expect and how to resolve issues.

---

## **Claude**

Locking in:
- **Slice size:** one-sitting, user-visible behavior change. Generalized "one observable capability, fully wired and tested" rule for non-full-stack projects.
- **Docs are first-class deliverables**, not an afterthought.

Adding docs to the model. Two things matter here: *what kinds of docs*, and *when they get written*. The failure mode you want to avoid is "we'll write the docs at the end" — they never get written, or they're written from memory after the context is gone.

**Doc types, mapped to audiences:**

| Doc type | Audience | Lives in | Written when |
|---|---|---|---|
| **`README.md`** | Anyone landing on the repo | Repo root | At project kickoff, updated per slice if scope changes |
| **`CLAUDE.md` / `CONTEXT.md`** | Future-Claude, future-you | Repo root | At kickoff via `/init`, updated when architecture decisions land |
| **`docs/adr/NNNN-*.md`** | Future devs asking "why did we do it this way" | `docs/adr/` | At decision time, via `grill-with-docs` skill |
| **`docs/user-guide/`** | End users / other departments | `docs/user-guide/` | **At slice-review time** — every slice that adds user-visible behavior must update or add a user-guide page |
| **`docs/troubleshooting/`** | Support / other departments hitting problems | `docs/troubleshooting/` | **At slice-review time** for any slice that introduces a new failure mode, error message, or "what could go wrong" |
| **API/code reference** | Developers integrating | Auto-generated from docstrings | CI step, no manual writing |

**The key enforcement point:** `/work-review` checks for doc deltas before opening the MR/PR. If a slice changed user-visible behavior, the reviewer skill flags missing user-guide updates. If a slice introduced new error paths or failure modes, it flags missing troubleshooting entries. Advisory (per your earlier preference), but loud — same warning style as the slice-shape check.

**Practical:** a small `/work-docs` slash command that, mid-slice, says "given the changes so far, here's the doc skeleton you should fill in" and drops a stub into `docs/user-guide/` and/or `docs/troubleshooting/` for you to flesh out. Stops docs from being written from memory after the fact.

**Troubleshooting guides specifically** — these are notoriously hard to write well because devs forget the "naive user perspective." My recommendation: every troubleshooting entry follows a fixed template:

```
### Symptom
What the user sees (exact error message, observable behavior).

### What it means
Plain-language explanation, no jargon.

### Likely causes
Ranked by frequency.

### How to fix
Numbered steps. Include commands to copy-paste.

### How to confirm it's fixed
Observable check.
```

Reviewer skill enforces this template exists for new entries.

**Three sub-questions:**

**(a)** Are user-guide and troubleshooting docs **per-slice** (write the relevant page when you add the feature) or **batched at release** (write all docs when shipping a milestone)? My strong recommendation: **per-slice**, because the context is fresh and the slice is small enough that the doc delta is tractable. Batched docs at release time is the antipattern that gets us into "no docs ever shipped."

**(b)** Should docs live **in the repo** (markdown, versioned with code) or in **an external system** (Confluence, Notion, internal wiki, GitLab Wiki)? My recommendation: **in-repo markdown** as the source of truth, with optional one-way export to Confluence/Wiki for the "other departments" audience who won't go to GitLab. This way docs are reviewed in the same MR as the code, can't drift from the implementation, and survive tooling changes.

**(c)** For the "training other departments" use case specifically — is that a doc *style* (the user-guide pages, written for non-devs) or does it need a separate artifact (slide deck, recorded walkthrough, training script)? My recommendation: **same markdown**, but with a `docs/training/` subdirectory containing scenario-based walkthroughs ("Scenario: Sarah from Accounting needs to export a report"). Don't try to generate slide decks from Claude — they're a different medium and the conversion is brittle. If your departments need slides, export the markdown to a slide tool manually or use Marp/Pandoc as a build step.

---

## **User**

per-slice, in-repo markdown, same markdown for training

We have access to Notion and the IT Operations team will be better suited to access documentation in Notion rather than in the repo. I would like to have some of the documentation in Notion for that team. What the IT Operations team should expect in Notion is: How to set up/configure something, how to troubleshoot something and requirements for doing both.

---

## **Claude**

Locking in:
- **Per-slice doc updates, in-repo markdown as source of truth, training uses same markdown.**
- **Notion is a downstream publishing target** for a specific subset of docs aimed at IT Operations: setup/config guides, troubleshooting guides, and requirements/prerequisites for both.

Critical principle: **Notion is a mirror, never a source.** Docs are written and reviewed in the repo (so they're versioned, MR-reviewable, can't drift from code). A publish step pushes the IT-Ops-relevant subset to Notion. Editing in Notion directly is forbidden — changes get clobbered on next publish. We surface this as a banner at the top of every published Notion page: *"This page is auto-published from `<repo>/docs/...`. Edit there, not here."*

**Repo structure to support this:**

```
docs/
  user-guide/         # end users
  troubleshooting/    # general devs/support — full template
  training/           # scenario walkthroughs for cross-dept
  adr/                # decisions, dev-only
  ops/                # ← THIS subtree publishes to Notion
    setup/            # how to set up / configure
    troubleshooting/  # IT-Ops-flavored, not dev-flavored
    requirements/     # prereqs for setup AND troubleshooting
```

The `docs/ops/` subtree is the contract with Notion. Anything outside it stays repo-only. Anything inside it gets published. Clean boundary, easy to reason about.

**Publishing mechanism — three realistic options:**

1. **CI step on merge to main** — GitLab CI job reads changed files under `docs/ops/`, calls Notion API to upsert pages. Most automated, requires Notion integration token in CI secrets, runs without you.
2. **Manual `/publish-ops-docs` slash command** — you run it when ready. More control, but relies on you remembering. Skips on broken state.
3. **Pre-MR-merge step in `/work-review`** — reviewer skill detects `docs/ops/` changes, prompts you to publish before merging. Hybrid.

**My recommendation: #1 (CI step on merge to main), with #2 as a manual override.** Reasoning: docs that aren't auto-published are docs that drift. CI makes it impossible to forget. The `/publish-ops-docs` command exists for "I edited a typo, want it on Notion now without waiting for a merge" cases.

**Mapping repo → Notion structure:**

The Notion side needs to be predictable so IT Ops can find things. My recommendation:

- One Notion **database** per project (created at kickoff via a `/notion-init` command).
- Pages within it tagged by `type` (Setup / Troubleshooting / Requirements) and `component` (drawn from frontmatter in the markdown file).
- Markdown frontmatter drives the Notion properties:

```markdown
---
notion_type: troubleshooting
component: auth-service
audience: it-ops
last_reviewed: 2026-05-04
---
```

The publisher reads frontmatter, upserts the Notion page with those properties set, converts markdown body → Notion blocks. Missing frontmatter on a file under `docs/ops/` → CI fails with a clear "add frontmatter" message.

**The "requirements" doc type** specifically — you said requirements for doing setup AND troubleshooting. My recommendation: each setup or troubleshooting doc has a **`## Requirements`** section in the markdown body (network access, credentials, software versions, permissions). The publisher promotes those sections into a separate "Requirements" view in Notion (filtered database view), so IT Ops can see "what do I need to even *attempt* this" at a glance, without having to open every page. Single source, two views.

**Three sub-questions:**

**(a)** When a doc gets *deleted* from `docs/ops/` (slice removed a feature), should the corresponding Notion page be **deleted**, **archived** (Notion has an archive state), or **left alone with a "deprecated" banner**? My recommendation: **archived with a deprecated banner** added before archive. IT Ops may have bookmarked it; outright deletion is hostile. Archive keeps it findable but out of the main views.

**(b)** Notion API access — do you have an integration set up already, or do we need a one-time setup step (create internal integration in Notion admin, share the target database with it, store the token)? If you don't know, that's fine — flag it and we'll add "Notion integration setup" as a kickoff prerequisite.

**(c)** Should the Notion publisher run **per-project** (each project has its own Notion database, fully independent) or **org-wide** (one big "Engineering Docs" database in Notion, projects are pages within it, IT Ops browses by project)? My recommendation: **org-wide database, projects as a top-level filter**, because IT Ops will want a single bookmark and to search across everything. Per-project databases mean they have to know which project owns the doc they're looking for, which they often won't.

---

## **User**

a) your recommendation
b) I don't have that integration set up yet
c) your recommendation

---

## **Claude**

Locking in:
- **Deleted ops docs → deprecated banner + archive in Notion.**
- **Notion integration setup** is now a one-time prerequisite, captured as a kickoff task.
- **Org-wide "Engineering Docs" Notion database**, projects as a top-level filter.

Adding to the open setup-tasks list (we'll surface this whole list at the end as the bootstrap checklist):

- [ ] Create internal Notion integration in Notion admin → grab integration token
- [ ] Create org-wide "Engineering Docs" database in Notion with properties: `Project` (select), `Type` (Setup/Troubleshooting/Requirements), `Component` (text), `Status` (Active/Deprecated/Archived), `Last Reviewed` (date), `Source File` (URL back to repo)
- [ ] Create a saved view per `Type` and a "By Project" view filtered by `Project`
- [ ] Share the database with the integration
- [ ] Store the integration token in: (1) your local `~/.config/<skill-name>/notion-token` for `/publish-ops-docs` manual publishes, (2) GitLab CI/CD masked variable `NOTION_TOKEN` for auto-publish, (3) GitHub Actions secret `NOTION_TOKEN` for GitHub-hosted projects

---

**Q7: Where does the meta-stuff live — the skill itself, its config, and per-project state?**

We've now accumulated a lot of moving parts. Time to nail down where everything lives so it's not scattered across nine places. Three layers to decide:

1. **The skill bundle itself** (the workflows, slash commands, hooks, doc templates, tracker adapter, Notion publisher). This is the thing you'll reuse across projects.
2. **Per-user config** (your Notion token, your GitLab token, your preference defaults). One copy on each machine.
3. **Per-project state** (`current-work.json`, `tracker.json`, the project's `CLAUDE.md`, ADRs, docs).

**My recommendation — three clean homes:**

| Layer | Lives in | Why |
|---|---|---|
| **Skill bundle** | `~/.claude/skills/dev-team/` (a single skill, with sub-resources) — and *also* mirrored in a git repo (`erikclay/claude-dev-team` or similar) so it's versioned, syncable across machines, and updateable. Local skill dir is a clone/symlink of the repo. | Versionable, portable, you can pull updates and roll back. Avoids the "which version of the skill is on which machine" problem. |
| **Per-user config** | `~/.config/claude-dev-team/config.toml` (tokens, defaults, machine-specific paths) | Standard XDG location, not in the skill repo (no secrets in git), easy to back up, easy to differ per machine. |
| **Per-project state** | `.claude/` in the project repo: `project.json` (tracker host, project_id, doc-publish settings), `current-work.json` (active phase/issue/branch), `tracker-cache.json` if we ever add one. Plus standard repo-level docs/ADRs/CLAUDE.md at the repo root. | State that belongs to the project travels with the project. Switching machines or onboarding a new dev = clone, you have everything. |

**A few specific design calls inside this:**

- **Skill is *one* skill, not nine.** Even though it surfaces many slash commands (`/work-start`, `/work-review`, `/work-docs`, `/publish-ops-docs`, etc.), they all belong to one bundle (`dev-team`). Splitting into nine skills is what you'd do for unrelated tools — these are tightly coupled and share state. One bundle = one place to install, one version number, one changelog.
- **`.claude/` directory inside each project, gitignored selectively.** `project.json` is committed (it's part of the project's identity — tracker host, etc). `current-work.json` is gitignored (it's *your* in-flight state, not the team's). This matters even though most projects are solo — keeps the model right for if you ever collaborate.
- **Skill installation is `git clone`, not `cp -r`.** New machine: clone the skill repo into `~/.claude/skills/dev-team/`. Updating: `git pull`. Local changes: branch, commit, optionally push back. This makes the skill itself *another* project that follows the same conventions you're building — eats its own dog food, which is the right test.
- **No global "team config" file beyond the skill repo.** Conventions live in the skill's `SKILL.md`. Per-project overrides live in `.claude/project.json`. Per-user overrides live in `~/.config/claude-dev-team/config.toml`. Three layers, clear precedence (project > user > skill defaults). No fourth layer.

**Two sub-questions:**

**(a)** Are you OK with the skill itself living in a **public** GitHub repo (no secrets in it, but the workflow is visible to anyone), or does it need to be **private** (internal GitLab, or a private GitHub repo)? My recommendation: **public GitHub**, because (1) it's free and easy, (2) the skill itself contains no proprietary code or secrets, (3) you might want to share it with teammates or other internal devs eventually, and that's frictionless if it's already public. The *projects* it operates on can be wherever they need to be (internal GitLab for work, public/private GitHub for personal). If your employer has a policy against public-OSS contributions on company time, that changes the answer — flag if so.

**(b)** Per-user config (`~/.config/claude-dev-team/config.toml`) — should it be **bootstrapped via an interactive `/dev-team-setup` slash command** (you run it once on a new machine, it asks for tokens, writes the file), or **a documented manual file you edit yourself**? My recommendation: **interactive setup command**, because (1) you've now got 3 tokens (Notion, GitLab PAT, GitHub PAT) and machine-specific paths to enter, (2) the command can validate each token by making a test API call before saving, catching typos and permission gaps at setup time instead of at first-use, (3) it can also do the initial Notion-integration check from Q6's setup list. Manual editing is fine as a fallback for tweaking later.

---

## **User**

a) i'd rather keep this in Gitlab. Also, a bunch of thsee skills we are using come from a public GitHub repo (https://github.com/mattpocock/skills)  b) your recommendation

---

## **Claude**

Locking in:
- **Skill bundle lives in internal GitLab.** Repo name TBD (suggest `claude-dev-team` under your personal namespace or a team namespace — your call at kickoff). Implication: every machine you install on must be VPN-reachable to clone/pull. New-machine bootstrap requires VPN, same constraint as the projects themselves. Consistent with the "must be on the network to work" rule from earlier.
- **Interactive `/dev-team-setup` command** for per-user config bootstrap, with live token validation against each API before writing.

Two threads worth pulling on briefly before moving to Q8:

**Re: mattpocock/skills as a reference point** — that repo is a good model for *shape* (one folder per skill, clear `SKILL.md`, minimal dependencies). Worth cribbing the structure even though we're hosting in GitLab. Where we'll diverge: that repo's skills are mostly *single-purpose, stateless* (e.g. `tdd`, `simplify`). Ours is a *multi-command, stateful* bundle (slash commands, hooks, per-project state files, external API integrations). That justifies a different internal layout — more like a small application than a skill collection. Concretely, I'd expect the skill repo to look roughly like:

```
claude-dev-team/
  SKILL.md                  # entry point, describes the bundle
  commands/                 # slash commands as separate skill defs (per Claude Code convention)
    work-start.md
    work-review.md
    work-docs.md
    publish-ops-docs.md
    dev-team-setup.md
    ...
  hooks/
    preflight.sh            # session-start: VPN/auth check for GitLab projects
    phase-warn.sh           # PreToolUse: phase advisory
    pre-push.sh             # local verify-fast
    docs-publish.yml        # GitLab CI job template for Notion publish
  adapter/
    tracker.py              # gh/glab dispatch
    notion_publish.py       # markdown -> Notion blocks
  templates/
    project.json.tmpl
    current-work.json.tmpl
    troubleshooting.md.tmpl
    setup.md.tmpl
    requirements.md.tmpl
    adr.md.tmpl
  config/
    defaults.toml           # baked-in defaults, overridden by user/project config
  README.md                 # how to install, how to bootstrap
  CHANGELOG.md
```

Not asking you to approve the layout right now — just naming it so we have something concrete to point at. We'll refine when we actually build.

---

**Q8: How does the *kickoff* of a brand-new project work end-to-end?**

This is the moment-of-truth question. Everything we've designed has to compress into one ergonomic motion: "I'm starting a new project, get me set up." If kickoff is painful, you'll skip it on small projects, the discipline won't apply uniformly, and the whole system frays.

Picture the situation: empty directory, you have an idea, you want to start. What does the kickoff command do, in what order, and how interactive is it?

**My recommendation — a single `/dev-team-init` command that runs an interactive wizard, in this order:**

1. **Detect or ask for project basics** — name, one-line description, language/stack (best-guess from any existing files, ask if empty).
2. **Pick the tracker** — sniff `git remote` if present, else ask GitHub-or-GitLab. If GitLab, sniff which internal host (config has it). Validate connectivity *before* proceeding.
3. **Create the remote project if it doesn't exist** — `gh repo create` or `glab repo create` with a sensible default name. Set as `origin`. Push initial commit.
4. **Bootstrap the project skeleton:**
   - `.gitignore` (pulled from a per-language template)
   - `README.md` (stub with project name + description)
   - `CLAUDE.md` (per-project, references the dev-team skill conventions, includes the project's stack notes)
   - `docs/adr/0001-initial-stack-decision.md` (records the stack choices made in step 1)
   - `docs/user-guide/`, `docs/troubleshooting/`, `docs/training/`, `docs/ops/{setup,troubleshooting,requirements}/` (empty dirs with `.gitkeep`)
   - `.claude/project.json` (tracker, host, project_id, doc-publish settings)
   - `.claude/.gitignore` (ignores `current-work.json`)
5. **Set up CI** — drop in a `.gitlab-ci.yml` or `.github/workflows/main.yml` template that includes: lint, typecheck, test, and the docs-publish job pointing at Notion. CI is *opinionated*, not blank — same template across projects so the skill knows how to read CI status later.
6. **Register the project in the org-wide Notion database** — one row added with `Project=<name>`, `Status=Active`, link back to repo. Doesn't publish any pages yet (no docs to publish), just makes the project filterable in Notion immediately.
7. **Install pre-push hook** locally (`verify-fast`).
8. **Print a "what's next" summary** — with the suggested first command (`/work-start "your first slice"` or `/grill-with-docs` if scope still fuzzy).

That's a lot of steps, but they're all things that would otherwise have to be done manually on every new project — and forgotten, inconsistently. Wizard runs in <2 minutes if all tokens/access are already set up.

**Idempotent and resumable:** if any step fails (network blip, name collision), `/dev-team-init` resumes from where it left off on re-run. No half-baked states.

**For *existing* projects** (you want to adopt this skill on a project that's already underway): a separate `/dev-team-adopt` command that does the same thing but **skips repo creation** and **prompts before overwriting** any existing CLAUDE.md / CI config / docs structure. Migration mode, not greenfield.

**Three sub-questions:**

**(a)** Should `/dev-team-init` always create a *new* remote repo, or also support **"I already created the repo in GitLab/GitHub UI, now hook it up locally"**? My recommendation: support both. The wizard asks "create new or use existing?" early. Both paths converge after the remote exists.

**(b)** The CI template is opinionated (lint + typecheck + test + docs-publish, in that fixed order). Should the wizard let you **opt out of CI entirely** for one-off scratch projects? My recommendation: **no opt-out, but provide a `--minimal` flag** that skips CI, Notion registration, and the docs/ structure — leaving just `.claude/project.json`, `CLAUDE.md`, and basic `.gitignore`. Use `/dev-team-init --minimal` for true throwaway prototypes. Promotes to full kickoff later via `/dev-team-promote`. Keeps the default path opinionated (the whole point), gives you a release valve for the genuinely-tiny case.

**(c)** Stack/language detection in step 1 — how strongly should the wizard push **defaults**? Three choices:
- **Detect-only:** if it's empty, ask; otherwise infer from existing files. Quiet.
- **Detect-and-confirm:** always show what it inferred, let you override. Slightly more interactive.
- **Opinionated stack picker:** offer a small menu of "blessed" stacks the skill knows well (e.g. "Python+pytest", "TypeScript+vitest", "Rust+cargo") and lightly discourage off-menu choices because the skill's templates are tuned to them.

My recommendation: **detect-and-confirm, with a soft menu of blessed stacks shown when greenfield.** Reasoning: hard opinionation makes the skill brittle (you'll inevitably want a project in a stack we don't bless). Pure detection means the skill silently picks wrong defaults. Show what we inferred + the blessed menu = transparent and steerable. Blessed stacks just get nicer templates; off-menu stacks still work, just with a more generic template and a note that "lint/test commands may need editing in `.claude/project.json`."

---

## **User**

a, b, and c your recommendations

---

## **Claude**

Locking in:
- `/dev-team-init` supports both **create new remote** and **hook up existing remote**.
- **No CI opt-out**, but `--minimal` flag for throwaway prototypes; `/dev-team-promote` to upgrade later.
- **Detect-and-confirm stack picker** with a soft menu of blessed stacks.

---

**Q9: How does the team handle *failure* and *interruption*? Specifically: what happens when CI fails, when a slice goes sideways mid-implementation, and when you context-switch?**

We've designed the happy path well. The boring-but-load-bearing question is what happens when things break. Three failure modes worth nailing down:

**1. CI fails on a pushed branch.**

Two flavors: (a) the local `verify-fast` passed but the full CI suite caught something (slow test, integration check, lint rule that only runs in CI), or (b) infrastructure flake (runner died, registry timeout). Both look the same to you — red pipeline.

The risk is "fix it manually, push, repeat" — turning into a CI-driven debug loop where Claude isn't helping. Or worse, Claude proposes a fix without actually reading the CI output and you waste another cycle.

**My recommendation:** when `/work-review` detects a failed pipeline, it **automatically fetches the failure logs** (`gh run view --log-failed` or `glab ci view --log`), parses for the actual error (vs the noise above/below), and routes to one of:
- **Real failure** → spawns the `diagnose` skill in the main thread with the parsed error as the seed. Diagnose's red-green-refactor loop kicks in.
- **Suspected flake** (timeout, network error, runner-killed) → offers to **retry once** before debugging. If the retry passes, log it as a flake to `.claude/flakes.jsonl` (so we can spot patterns over time) and continue. If it fails again, treat as real.

The point: you never look at the raw CI logs unless Claude can't make sense of them. The team handles the loop.

**2. A slice goes sideways mid-implementation.**

You're 30 minutes into implementing a slice and discover the design assumption was wrong. Database can't model what you need. UI library doesn't support the interaction. Whatever. You need to back out gracefully without losing context or polluting the issue tracker.

The risk is silent scope creep — you start "fixing" the design assumption inside the same slice, the slice grows, the one-sitting rule breaks, and now you have a 6-hour mess.

**My recommendation:** a `/work-rethink` command that:
1. Saves current diff as a WIP commit on the slice branch (not lost).
2. Forces you to choose: (a) **scope is still right, design needs to change** → record the new design choice as an ADR via `grill-with-docs`, then continue; (b) **scope is wrong, this slice was the wrong shape** → roll back to the slice's start point, file a new "design spike" issue (separate from the original slice), close-or-reshape the original, write what we learned into the spike's body. Phase moves back to `design`.
3. Either way, the original issue gets a comment on it ("rethink triggered at <commit>, decision: <a/b>, see <new ADR or new issue>") so the trail is visible.

This makes "we got it wrong" a **first-class flow**, not a guilty silent rework. Eats its own dog food: rethink isn't a bug in your process, it's the slice discipline working as intended (catching the wrong shape *small* instead of *large*).

**3. You context-switch off a slice and come back days later.**

Real life: you start a slice, get pulled into something else for a week, come back. `current-work.json` is stale, branch is behind main, you've forgotten what you were doing.

The risk is silent loss — you check out a different branch, forget the WIP, lose work; or you try to resume but the context is gone, so you basically restart, wasting the prior session.

**My recommendation:** the `/work-pause` command from Q4 plus a `/work-resume` counterpart, plus a SessionStart hook check.

- **`/work-pause`** writes `current-work.json` into `.claude/paused/<issue-id>.json` (with a snapshot of: branch name, last commit, phase, a 1-paragraph "where I left off" summary that Claude generates from the conversation), clears the active `current-work.json`. Branch stays — never deleted.
- **`/work-resume <issue-id>`** restores from the paused file, checks out the branch, fetches latest main, surfaces the "where I left off" summary, and runs a quick "what's changed in main since I left" diff so Claude can flag conflicts before you start coding again.
- **SessionStart hook** checks: if `current-work.json` is set but the branch is behind main by >7 days OR you haven't committed in >3 days, gently prompt "this slice has been idle — `/work-pause` or `/work-resume` to refresh?"

The "where I left off" summary is the magic ingredient. It's not your job to write it — Claude generates it from the conversation at pause time, when the context is fresh. Reading it back at resume is what makes the slice actually resumable instead of a guessing game.

**Two sub-questions:**

**(a)** For CI-flake handling: I suggested **retry-once-then-treat-as-real**. Is that aggressive enough, or do you want a higher retry budget (some teams retry 2-3 times because their CI is genuinely flakey)? My recommendation stays at **once**, because higher retry budgets normalize flakiness instead of forcing you to fix it. The `flakes.jsonl` log is the pressure-release valve — when you see a pattern, you fix the underlying flake instead of upping the retry count.

**(b)** For `/work-rethink`: should branch 2 (scope was wrong) **always** force the original slice to be closed/reshaped, or allow you to **keep both** (resume original later, file the spike separately)? My recommendation: **force a decision** — either the original issue is reshaped to match the new understanding, or it's closed with a comment pointing to the spike. Allowing "both open, figure out later" is exactly the silent-state-drift problem the whole shared-brain design exists to prevent. The decision can be "reshape later, for now close" — but it must be a deliberate close, not a forgotten-open issue lingering in the tracker.

---

## **User**

your recommendations for both

---

## **Claude**

Locking in:
- **CI flakes: retry-once-then-treat-as-real**, logged to `.claude/flakes.jsonl` for pattern-spotting.
- **`/work-rethink` forces a decision** — original issue is either reshaped or closed with a pointer to the spike. No "both open, figure out later."

---

**Q10: How do *you* see what the team is doing without having to ask?**

Everything we've designed is bookkeeping for *Claude's* benefit — `current-work.json`, paused state, the issue tracker, ADRs, flakes log. But you also need a glanceable surface to see what state things are in without typing `/work-status` every time you sit down. Otherwise the system feels opaque and you stop trusting it.

Three realistic surfaces:

1. **Status line** — Claude Code's bottom-bar `statusLine`. Always visible, very limited real estate (one line). Good for "active issue + phase + branch + dirty/clean."
2. **A `/dashboard` slash command** — generates a markdown summary on demand. Rich detail (active slice, paused slices, open MRs, recent flakes, doc-publish status, CI status of last push). You invoke when you want it.
3. **Notion dashboard page** — same content as #2, but lives in Notion. Visible without opening Claude Code. Auto-refreshed by a scheduled job (cron agent).

**My recommendation: all three, with clear separation of concerns.**

- **Status line (always-on, 1 line):** `[issue-id] phase | branch | ✓/✗ ci | ⚠ N pending` — at-a-glance state. Zero friction. Tells you whether you're in good shape or there's something to attend to. The `⚠` is a count of "things needing your attention" (failed CI, stale paused slices, undrained outbox if we ever add one, etc.) — clicking through (i.e. running `/dashboard`) shows what they are.
- **`/dashboard` (on-demand, rich):** when you want to see the whole picture. Shows active slice, paused slices (with last-touched dates so you can see what's rotting), open MRs/PRs across all your projects with their CI status, recent flakes, doc-publish status (anything in `docs/ops/` that hasn't been published yet), and a "suggested next actions" section ("issue #42 paused 12 days — close or resume?"). This is your Monday-morning surface.
- **Notion dashboard (passive, cross-project):** scheduled remote agent (CronCreate) runs nightly, queries each tracker for your assigned-to-you open issues / open MRs / failed CI runs, writes them as a single Notion page in the org-wide Engineering Docs database. Lets you (and anyone you share with) see "what's Erik working on across all projects" without VPN-ing into your dev box. Particularly useful for IT Ops or a manager wanting visibility without bothering you. Read-only — editing the Notion page does nothing; it's overwritten nightly.

**Why all three vs. one:**
- Status line alone is too small for anything beyond the active slice. You'd lose visibility into paused/cross-project state.
- `/dashboard` alone means you have to remember to check it. Things rot silently.
- Notion alone is too async — you don't want to alt-tab to a browser to know whether your current branch's CI passed.

The combination is: status line nags you in real time, `/dashboard` answers "what's the full picture," Notion gives async visibility for everyone else (and for you when you're away from Claude Code).

**One important constraint to bake in:** the dashboards (both `/dashboard` and the Notion one) read **only from the existing shared brain** (issue tracker, `.claude/` state files, CI APIs). They don't introduce a new state store. This matters because every additional state store is another thing that can drift. Dashboards are *views*, never sources of truth.

**Two sub-questions:**

**(a)** For the status-line `⚠ N pending` counter — should the count include **gentle nudges** (paused slice idle 7+ days, undrafted ADR for a recent design call, missing docs on a merged slice) or **only urgent things** (failed CI on current branch, blocked MR review, broken pre-push hook)? My recommendation: **only urgent things in the counter, gentle nudges surfaced only in `/dashboard`.** Reasoning: a status-line counter that's always non-zero gets ignored. Reserve it for "stop and look at this now" so when it lights up you actually look. The Monday-morning `/dashboard` is where the soft nudges get aired out.

**(b)** Notion dashboard refresh cadence — **nightly** (low cost, slightly stale), **hourly** (more current, more API calls / more chance of hitting rate limits), or **on-write** (every tracker change triggers a republish via webhook)? My recommendation: **nightly**, with a manual `/refresh-notion-dashboard` command for "I want it current right now." Reasoning: this dashboard is for *async* visibility — people checking it aren't expecting real-time. Hourly burns API quota for marginal benefit. On-write is a webhook plumbing project we don't need. Nightly + manual override is the right cost/value trade.

---

## **User**

your recommendations for both

---

## **Claude**

Locking in:
- **Status-line counter: urgent things only.** Gentle nudges live in `/dashboard`.
- **Notion dashboard refresh: nightly cron + `/refresh-notion-dashboard` for on-demand.**

---

We've worked through the major design tree. Before I close out with a consolidated summary, there are three smaller branches I want to surface — each is a real decision with consequences, but small enough that I'll batch them into one question and you can answer in shorthand.

**Q11 (final batch): Three loose ends.**

**(a) Secrets handling for the `dev-team-setup` flow.** You'll have at minimum: GitLab PAT, GitHub PAT, Notion integration token. Three storage options:
- **Plain `~/.config/claude-dev-team/config.toml`** with file mode 600. Simplest, but plaintext on disk.
- **OS keychain** (macOS Keychain, GNOME Keyring on Linux, Windows Credential Manager). More secure, but adds a dependency on `keyring` Python lib (or equivalent) and behaves differently per OS.
- **OS keychain on macOS, plaintext-with-warning on Linux** (since Linux keyring is inconsistent across distros). Pragmatic split.

**My recommendation:** **OS keychain where available, plaintext-600 fallback with a warning.** The setup wizard probes for keychain availability and uses it transparently; if not, it writes plaintext, prints a yellow warning explaining the file location and permissions, and records the choice in `~/.config/claude-dev-team/config.toml` (`secrets_backend = "plaintext"`) so subsequent runs don't re-prompt. Pragmatic, secure-by-default, no surprises.

**(b) Updates to the skill itself — push/pull cadence.** You'll be improving this skill over time as you find what works. Three patterns for how updates roll out:
- **Manual** — you `git pull` in `~/.claude/skills/dev-team/` when you remember.
- **Notification** — a SessionStart hook checks `git fetch` and prints "skill has updates available, run `/dev-team-update`."
- **Automatic** — SessionStart silently `git pull`s on every session.

**My recommendation:** **notification, not automatic.** Auto-pull means a skill update can change behavior mid-conversation in ways you didn't expect, with no chance to read the changelog. Manual-only means you'll forget. Notification-with-explicit-update-command is the right balance — the SessionStart hook does `git fetch` (cheap, no working-tree changes), compares to local, prints a one-liner if behind, and you decide when to apply. Updates don't surprise you.

**(c) Telemetry / introspection on the team itself.** Over time, you'll want to know things like: which slices took longer than one sitting (slice-sizing pressure), how often CI flaked (infrastructure pressure), how often `/work-rethink` fires (design-quality pressure), how often docs were missing at review time (process pressure). Three options:
- **None** — don't collect, don't worry about it.
- **Local log** — append events to `.claude/events.jsonl` per project, optionally aggregate via `/team-stats` slash command.
- **Cross-project aggregation** — pump events to a single sink (e.g. a Notion database, or a small SQLite at `~/.local/share/claude-dev-team/events.db`) for cross-project metrics.

**My recommendation:** **local `.claude/events.jsonl` per project, plus a `/team-stats` command** that reads it. Skip cross-project aggregation initially — adds plumbing for value you may never use. If after a few months of use you find yourself wanting cross-project metrics ("am I getting better at slice-sizing?"), promote to SQLite then. YAGNI for the first version.

---

Answer (a), (b), (c) and we'll be done with grilling. I'll then produce the consolidated design doc + the bootstrap checklist so you can see the whole design in one place.

---

## **User**

a) I will be developing mainly on Windows OS but I don't want to use credential manager. Use plain text. When project ships, secrets will be secured in a way that makes sense. for example, if shipping to Azure, Auzre Key Vaults. If running script on a Windows Servers, use Export/Import-CliXml. b) notification c) your recomendation

---

## **Claude**

Locked in. Final answers:
- **Secrets: plaintext config file, Windows-flavored.** Production secrets handled at deploy-time per platform (Azure Key Vault for Azure, `Export/Import-CliXml` for Windows Server scripts) — outside the skill's scope.
- **Skill updates: SessionStart notification + `/dev-team-update`.**
- **Telemetry: local `.claude/events.jsonl` + `/team-stats`.**

One callout from your Windows answer: I'd been quietly assuming Unix paths and `chmod 600`. Those don't apply. Going forward the design uses **`%APPDATA%\claude-dev-team\config.toml`** for per-user config, **`icacls`** to restrict file ACLs to your user account, and `.ps1` (with optional `.bat` shims) for hooks instead of bash. Git Bash is assumed available since Claude Code uses it on Windows.

---

# Consolidated design

## The shape of the team
- **Main Claude session = the team lead.** No separate "orchestrator agent."
- **Skills = roles** (`tdd`, `diagnose`, `review`, `to-prd`, `to-issues`, `triage`, `grill-with-docs`, plus the new bundle).
- **Subagents = surgical, 3 types only:** `reviewer` (cold review), `explorer` (read-heavy research), `second-opinion` (manual sanity-check).
- **Shared brain = issue tracker + ADRs + `.claude/` state files.** No agent persists between turns; the files do.

## Trackers
- **Dual GitHub + GitLab**, auto-detected per project via `git remote get-url origin`, cached in `.claude/project.json`.
- **GitLab projects require network presence.** Session-start preflight checks reachability + token validity; refuses to start if either fails. No outbox, no offline mode.
- **`gh` for GitHub, `glab` for GitLab.** Adapter layer (`adapter/tracker.py`) so workflow skills are tracker-agnostic.

## CI
- **GitHub Actions** for GitHub projects, **GitLab CI** for GitLab projects (runners are internal-network, reachable).
- **Hybrid pre-push verification:** local `verify-fast` (lint + typecheck + changed-file unit tests, ≤30s budget), full suite in CI. Blocking with `--no-verify` override.
- **CI is opinionated, templated.** Same shape across projects so the skill knows how to read CI status.
- **CI flakes:** retry once, log to `.claude/flakes.jsonl`. No higher retry budget — patterns get fixed instead of normalized.

## Slices
- **Vertical slices mandatory.** One slice = one user-visible (or externally-observable) capability, fully wired DB→API→UI→test.
- **Sizing rule: one focused work session (2–4h).** Larger work uses `epic` label with linked sub-issues. `/work-start <epic>` refuses, makes you pick a child.
- **`to-issues` skill is the only sanctioned way** to break work down. No ad-hoc horizontal tickets.

## Phase commands (advisory, not strict)
| Command | Effect |
|---|---|
| `/dev-team-init [--minimal]` | Bootstrap a new project (interactive wizard) |
| `/dev-team-adopt` | Adopt the system on an existing project |
| `/dev-team-promote` | Upgrade `--minimal` project to full kickoff |
| `/dev-team-setup` | One-time per-machine setup (tokens, validation) |
| `/dev-team-update` | Pull skill updates (after notification) |
| `/work-start <ref>` | Begin a slice, branch, phase=`design` |
| `/work-design-done` | Phase → `implement` |
| `/work-review` | Phase → `review`, push, open MR/PR, run reviewer, fetch CI |
| `/work-done` | Phase → `done`, close issue |
| `/work-pause` | Snapshot + "where I left off" summary, clear active state |
| `/work-resume <id>` | Restore from pause, fetch latest main, surface summary |
| `/work-rethink` | Forces decision: reshape original issue OR close + spike |
| `/work-status` | Active state |
| `/work-docs` | Mid-slice doc-stub generator |
| `/dashboard` | Full picture across projects |
| `/publish-ops-docs` | Manual Notion publish |
| `/refresh-notion-dashboard` | Force dashboard refresh |
| `/team-stats` | Read local events.jsonl |
| `/second-opinion <q>` | Cold sanity-check from independent Claude |

## Docs (per-slice, in-repo source of truth)
```
docs/
  user-guide/         # end users
  troubleshooting/    # general devs/support
  training/           # scenario walkthroughs
  adr/                # architecture decisions (grill-with-docs)
  ops/                # ↓ publishes to Notion
    setup/
    troubleshooting/
    requirements/
```
- **Markdown frontmatter** drives Notion properties (`notion_type`, `component`, `audience`, `last_reviewed`).
- **Org-wide "Engineering Docs" Notion database**, projects as a top-level filter.
- **CI auto-publishes `docs/ops/`** on merge to main; `/publish-ops-docs` for manual.
- **Notion is a mirror, never a source.** Banner on every page: edit in repo.
- **Deleted ops doc → deprecated banner + archive** (not delete).
- **Troubleshooting template enforced:** Symptom / What it means / Likely causes / How to fix / How to confirm.

## Visibility
- **Status line:** `[issue] phase | branch | ✓/✗ ci | ⚠ N urgent` — urgent only.
- **`/dashboard`:** full picture, soft nudges live here.
- **Notion dashboard:** nightly cron-published cross-project view, read-only.

## Where things live
- **Skill bundle:** internal GitLab (`claude-dev-team` or similar). Cloned to `~/.claude/skills/dev-team/` on each machine. VPN required to clone/update.
- **Per-user config:** `%APPDATA%\claude-dev-team\config.toml` (plaintext, ACL-restricted to user).
- **Per-project state:** `.claude/` in repo. `project.json` committed; `current-work.json`, `paused/`, `events.jsonl`, `flakes.jsonl` gitignored.
- **One skill bundle, many slash commands.** Not nine separate skills.

## Skill updates
- SessionStart hook does `git fetch`, prints one-liner if behind. `/dev-team-update` to apply. No silent auto-pull.

## Telemetry
- `.claude/events.jsonl` per project. `/team-stats` reads it. No cross-project aggregation yet — promote to SQLite later if needed.

---

# Bootstrap checklist

Stuff to do — in roughly this order — before the skill is real:

**One-time, environment:**
- [ ] Create internal Notion integration → grab token
- [ ] Create org-wide "Engineering Docs" Notion DB with properties: `Project`, `Type`, `Component`, `Status`, `Last Reviewed`, `Source File`
- [ ] Create saved views: by `Type`, by `Project`
- [ ] Share DB with the Notion integration
- [ ] Mint GitLab PAT (`api`, `read_repository`, `write_repository`)
- [ ] Mint GitHub PAT (`repo`, `workflow`)
- [ ] Pick name + namespace for the skill repo in internal GitLab
- [ ] Install `glab` + `gh` on dev machine; verify `glab auth login --hostname <internal>` works on VPN

**Build the skill bundle (in the GitLab repo):**
- [ ] `SKILL.md` — entry point describing the bundle
- [ ] `commands/` — one `.md` per slash command listed above
- [ ] `hooks/` — `preflight.ps1`, `phase-warn.ps1`, `pre-push.ps1`, `session-start.ps1`, GitLab CI job templates
- [ ] `adapter/` — `tracker.py` (gh/glab dispatch), `notion_publish.py` (markdown→Notion blocks)
- [ ] `templates/` — `project.json.tmpl`, `current-work.json.tmpl`, doc templates (troubleshooting, setup, requirements, ADR), `.gitlab-ci.yml.tmpl`, GitHub Actions workflow tmpl, `.gitignore` per stack
- [ ] `config/defaults.toml`
- [ ] `README.md` + `CHANGELOG.md`

**First real test:**
- [ ] Pick a small real project (or scratch project)
- [ ] Run `/dev-team-setup` → `/dev-team-init`
- [ ] File one slice via `to-issues`, run it through `/work-start` → `/work-review` → `/work-done`
- [ ] Note what breaks, what's awkward, what's missing — feed back into the skill repo

That's the design and the path to building it. The skill itself is a project that follows its own conventions — so the first thing to build inside it is the slice that makes the slice flow work. Eat-your-own-dog-food from day one.

---

## **User**

would it be better to use linux instead of Windows for developement. I have WSL installed on Windows. Do all the skills worth in both environments or are they better suited for linux?

---

## **Claude**

Short answer: **WSL is meaningfully better for this kind of work.** Skills technically run on both, but they're written assuming Unix conventions, and you'll spend energy paving over the gaps on native Windows.

**Where the friction actually lives:**

| Area | Native Windows | WSL2 |
|---|---|---|
| **Hook scripts in `settings.json`** | PowerShell `.ps1` or Git Bash; many ecosystem skills ship `.sh` and you'll be rewriting/wrapping | Bash `.sh` works first-class, no translation |
| **File permissions** (secrets file, executable hooks) | `icacls` ACLs, no `chmod` — works but unidiomatic and easy to get wrong | `chmod 600` works, executable bit works |
| **Path handling in skill code** | Backslashes vs forward, drive-letter prefixes, mixed handling in tools that assume `/` | Plain Unix paths everywhere |
| **Line endings** (CRLF vs LF) | Constant low-grade nuisance with hooks, scripts, git autocrlf | Not a problem |
| **Process / signal handling** in long-running tooling | Git Bash emulates but with edge cases | Native |
| **The `mattpocock/skills` bundle and most public skills** | Authors test on macOS/Linux. Some work, some break subtly | Designed for this environment |
| **Symlinks** (sometimes useful for skill installation) | Need admin or Developer Mode | Just work |
| **Performance for typical dev tooling** (npm install, pytest, etc.) | Fine | Fine — *if* the project lives inside WSL's filesystem (`/home/...`), not on the Windows mount (`/mnt/c/...`) |

**What stays the same regardless:** Production targets (Azure, Windows Server with `Export-CliXml`) don't care what your dev box runs. You can develop in WSL and deploy to Windows production all day. The skill bundle is for the dev workflow, not deployment artifacts.

**What changes in the design we just built if you switch to WSL:**

- Per-user config goes back to `~/.config/claude-dev-team/config.toml` with `chmod 600` (drop `%APPDATA%` and `icacls`).
- Hooks become `.sh`, not `.ps1`. No PowerShell-specific shims.
- The `verify-fast` pre-push hook is a one-liner shell script instead of platform-specific.
- The skill bundle becomes simpler — one platform's conventions, not "if Windows then X else Y" branches.

That's a real reduction in surface area. The skill itself becomes ~20% less code to write and maintain.

**The one thing you must verify before committing:** *does your corporate VPN route to your internal GitLab from inside WSL?*

This is the single risk. Corporate VPNs (Cisco AnyConnect, GlobalProtect, Zscaler, etc.) interact with WSL2 networking in fiddly ways — sometimes transparent, sometimes requires WSL2 "mirrored networking mode" (newer feature in `.wslconfig`), sometimes needs DNS overrides. 5-minute test:

```bash
# inside WSL, with VPN active on Windows
curl -I https://your-internal-gitlab-host
glab auth status   # after you've installed glab and authenticated
```

If those work, you're golden — switch to WSL, simplify the design accordingly.

If they fail, you have three options: (a) configure WSL networking to play nicely (usually `mirrored` mode in `.wslconfig` plus a DNS tweak — well-documented but fiddly), (b) ask IT for a WSL-aware VPN config, (c) stay on native Windows for the work-tracker projects and use WSL only for personal/GitHub projects (dual-mode, more complexity).

**My recommendation:** test VPN-to-GitLab from WSL right now. If it works, switch. The design becomes simpler, the skill ecosystem aligns with you instead of against you, and you're working in the environment most Claude Code users and skill authors target.

If VPN doesn't work cleanly and you can't get IT to help, native Windows is fine — we just keep the design we have.

---

## **User**

okay, we'll develope on either a linux VM or WSL. leave Windows OS out of the equation for developement work

---

## **Claude**

Locked in: **Linux-only dev environment** (WSL2 or a Linux VM). Windows is out of scope for the skill bundle.

**Design deltas from the Windows-flavored version:**

- **Per-user config:** `~/.config/claude-dev-team/config.toml`, `chmod 600`. Drop `%APPDATA%` and `icacls`.
- **Hooks:** `.sh` only. Drop `.ps1` and Git Bash workarounds.
- **Pre-push, preflight, phase-warn, session-start hooks:** plain bash, executable bit set.
- **CI templates:** GitLab CI / GitHub Actions YAML unchanged (server-side, OS-agnostic).
- **Skill bundle layout** simplifies to one platform — no `if windows` branches anywhere.
- **`verify-fast` hook:** straight shell script invoking the project's lint/test commands from `.claude/project.json`.

**One environment note worth flagging up front** — for WSL specifically:

- Keep project files **inside the WSL filesystem** (`~/projects/...`), never on the Windows mount (`/mnt/c/...`). The cross-mount is an order of magnitude slower for git, npm, pytest, file watching — basically every tool the skill runs.
- The skill bundle itself: clone to `~/.claude/skills/dev-team/` inside WSL.
- Editor: VS Code with the Remote-WSL extension is the standard pattern. Editing happens "in Windows" but the files and processes live in WSL.

For a dedicated Linux VM the same structure applies, just without the cross-OS edge.

**Still pending from earlier — the gating test:**

```bash
# from inside WSL (or the Linux VM), with VPN connected on the host
curl -I https://your-internal-gitlab-host
```

If that resolves and returns a `200`/`302`/whatever non-error, you're set. If it doesn't, that's the problem to solve before any of this matters — and the answer is environment-specific (WSL `.wslconfig` mirrored mode, or VM network adapter set to bridged, etc.).

The full consolidated design from before stands, with the deltas above applied. Ready to build whenever you are — first concrete step is whichever of these you want to do:

1. **Verify VPN reachability** from your chosen Linux env (the `curl` above).
2. **Run the bootstrap checklist** (Notion integration, tokens, skill repo creation in GitLab).
3. **Scaffold the skill bundle** itself — start with `SKILL.md` and the smallest end-to-end slice (`/dev-team-setup` + `/dev-team-init` + one `/work-*` command), then iterate.

Which do you want to tackle first?

---

## **User**

i'm currently on my personal machine, not work machine. let's forgo the VPN reachability test. This machine also does not have access to my works GitLab, so we'll skip that. Let's scaffold the skill bundle. But do it in a way where we don't do any testing from this machine. Make it so that I can transfer all this to my work machine and pick up where we left off there.

---

## **Claude**

Got it — building a self-contained scaffold in `/home/xtreme/claude-dev-team/` that you can `tar` or `git push` to your work machine. No network calls, no testing, no git operations on this machine. The work machine becomes the place where the scaffold becomes a real GitLab repo and gets installed.

Setting up the directory structure first.

---

## **Claude**

Starting with the top-level docs.

---

## **Claude**

Now templates — these can all be written in parallel since they don't depend on each other.

---

## **Claude**

Now the slash commands. Each is a self-contained skill file with frontmatter plus the workflow Claude follows when invoked.

---

## **Claude**

Now the adapter Python scaffolds — interfaces and skeleton implementations with TODOs marked where live testing is required.

---

## **Claude**

Sanity-checking the final tree.

---

## **Claude**

Scaffold is done. Here's what got built and what comes next.

## What's at `/home/xtreme/claude-dev-team/`

**54 files** across the layout we agreed on:

- **6 top-level docs** — `SKILL.md`, `README.md`, `INSTALL.md`, `TRANSFER.md`, `CHANGELOG.md`, `.gitignore`
- **2 install scripts** — `install.sh` (symlinks into `~/.claude/`, patches `settings.json`), `uninstall.sh`
- **19 slash commands** under `commands/` — every command from the design (setup, init, adopt, promote, update, work-start through work-rethink, dashboard, publish-ops-docs, refresh-notion-dashboard, team-stats, second-opinion). Each is a self-contained skill file with frontmatter and the workflow Claude follows when invoked
- **5 hooks** under `hooks/` — preflight, phase-warn, pre-push, session-start, statusline (all bash, executable)
- **2 standalone CI templates** under `hooks/ci-templates/` — for projects adding only the docs-publish job to existing CI
- **4 Python adapters** under `adapter/` — `tracker.py` (gh/glab dispatch), `notion_publish.py` (markdown→Notion), `verify_fast.py` (pre-push), `slice_check.py` (vertical-slice heuristics) plus `requirements.txt`
- **13 templates** under `templates/` — project.json, current-work.json, CLAUDE.md, ADR, all four doc types (user-guide, troubleshooting, ops-setup, ops-troubleshooting, ops-requirements), three .gitignore variants, two CI configs
- **1 defaults config** — `config/defaults.toml` capturing all the bundle defaults (advisory mode, 3h slice target, 1 flake retry, 30s verify-fast budget, etc.)

## What's intentionally not done

Everything that requires network, real credentials, or testing against live APIs is left for the work machine:

- No git init (you'll do this when you push to GitLab)
- No Python deps installed
- No `gh`/`glab`/Notion calls actually exercised
- Adapter Python has working code for the common paths but TODOs marked where the implementation needs verification against real responses
- The `notion_publish.py` markdown→blocks converter handles paragraphs, headings, lists, code blocks; tables/callouts/images are TODOs

## Next steps on the work machine

Path is laid out in `TRANSFER.md` but the short version:

1. tar the directory, transfer it, `tar xzf` to `~/dev/claude-dev-team/`
2. `git init && git push -u origin main` to the new internal GitLab repo
3. `pip install --user -r adapter/requirements.txt`
4. `./install.sh`
5. Restart Claude Code → `/dev-team-setup` → `/dev-team-init` on a throwaway test project → run a real slice through to `/work-done`
6. Fix what breaks, push back, `/dev-team-update` to pull the fixes anywhere

Bundle is now scaffold-complete. Whenever you're at the work machine, `TRANSFER.md` walks you through the rest.

---

## **User**

tar it up so I can transfer it

---

## **Claude**

Tarball ready at `/home/xtreme/claude-dev-team.tar.gz` (46K, 61 entries = 54 files + 7 directories).

**Transfer it via whichever route works** (USB drive, internal share, scp). On the work machine:

```bash
mkdir -p ~/dev
cd ~/dev
tar xzf /path/to/claude-dev-team.tar.gz

# verify integrity (optional)
sha256sum claude-dev-team.tar.gz
# expected: f8fd836e6ec68fcc6e05dfbf5f850a95dee370f9290ad406a53190647eb67f36
```

From there, follow `~/dev/claude-dev-team/TRANSFER.md` from step 2 onward (`git init` + push to internal GitLab, then `INSTALL.md` for the actual install).

---

## **User**

if i need to continue developement of this skilk package on the other machine, will I be able to do that with full context?

---

## **Claude**

Partial — let me be honest about what transfers and what doesn't.

**Transfers in the tarball:**
- All 54 files (the bundle itself)
- `SKILL.md` — design summary, key principles
- `README.md` — high-level intent
- `TRANSFER.md` + `INSTALL.md` — operational continuity
- The "## Don'ts" sections in each command — these encode a lot of the "why"
- Inline TODOs marking what's deferred

**Does NOT transfer:**
- This conversation — the 11 grilling questions and the alternatives we considered and rejected
- The reasoning behind specific decisions (why advisory not strict, why retry-once for flakes, why Notion is mirror-only, why one-sitting slice rule, etc.)
- Your stated preferences I picked up (terse responses, mostly solo dev, work projects target Azure/Windows Server in production)
- My in-context memory of how we arrived at the design

A fresh Claude on the work machine reading just the bundle will be **capable but uninformed about the road not taken**. It will know *what* to do but not always *why* decisions went the way they did, so when you ask "should I change this?" it might give you the wrong answer because it doesn't know what tradeoff you already weighed.

**Three things to bridge the gap, in order of value:**

1. **Save this conversation transcript and include it in the bundle.** In Claude Code: use `/export` (or however your version surfaces transcript export) to dump this conversation as markdown, save it to `claude-dev-team/docs/design-conversation.md`. This is the highest-bandwidth context transfer — every alternative we considered, every recommendation you accepted or modified, every constraint you raised.

2. **Let me write a `DESIGN.md` (or `docs/adr/0001-bundle-design.md`)** capturing the major decisions with their alternatives and reasoning. Cheaper than the full transcript, denser, and structured for fast skimming. ~10 ADRs covering: agent model, dual-tracker, vertical slices, advisory enforcement, per-slice docs, Notion mirror, network-required, Linux-only, etc.

3. **On the work machine, brief the new Claude** at session start: "Read `SKILL.md`, `DESIGN.md`, and `docs/design-conversation.md`. We're continuing development of this bundle."

**My recommendation:** do #2 right now (I'll write it before re-tarring), and you do #1 manually from the Claude Code UI before transferring. #3 happens naturally when you start working on the work machine.

Want me to write the `DESIGN.md` and re-tar?

---

## **User**

write the DESIGN.md and re-tar

---

## **Claude**

Now updating README and CHANGELOG to reference DESIGN.md, then re-tarring.

---

## **Claude**

Re-tarred at `/home/xtreme/claude-dev-team.tar.gz` (55K, 55 files — DESIGN.md added).

**New checksum** (the previous one is now stale):

```
15ab660912a1a2bdeb6f165f1be28fe9c407d5b23eb5682817ee50974895df41
```

**What changed in this revision:**

- New `DESIGN.md` at the bundle root — 19 ADR-style entries covering every design decision from the grilling, with alternatives considered and reasoning. This is now the load-bearing document for any future structural change to the bundle.
- `README.md` updated to point at `DESIGN.md` and `docs/design-conversation.md`.
- `TRANSFER.md` updated with a "continuing development on the work machine" section telling new-Claude exactly which files to read for context.
- `CHANGELOG.md` notes DESIGN.md inclusion.

**One thing left for you to do before tarring is fully complete:** export this conversation as markdown from Claude Code (via the UI's transcript-export feature, or whatever your version provides) and drop it in `claude-dev-team/docs/design-conversation.md` *before* you transfer. Then re-tar one more time. That gives the new-Claude on the work machine the highest-bandwidth possible context.

If you skip that step, `DESIGN.md` alone is enough — it's a deliberate compression of the conversation into the decisions that matter, with the reasoning preserved.

---

## **User**

export the conversation and re-tar

---

## **Claude**

Good — the conversation is stored locally. Let me extract it as readable markdown.

---
