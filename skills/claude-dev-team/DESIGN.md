# claude-dev-team — design decisions

This is the rationale-record for the bundle. Each section captures a decision we made, the alternatives we considered, and *why* we chose what we chose. Read this before changing the bundle's shape — most decisions have a non-obvious cost on the road we didn't take.

If you only read one section, read the first one — it sets the foundation everything else rests on.

> **For new sessions / new Claudes:** This document plus `SKILL.md` is the minimum reading. The full grilling conversation that produced these decisions should also be in `docs/design-conversation.md` — read it if you have time, skim if you don't.

---

## D1 — One Claude with skills, not a multi-agent team

**Decision:** The main Claude Code session IS the team. Specialized "roles" (coder, tester, debugger, reviewer, scope-keeper, progress-tracker) are realized as **skills running in the main thread** + **state files on disk**, not as separate persistent agents.

**Alternatives considered:**

- **AutoGen / CrewAI / LangGraph-style multi-agent orchestration.** Long-lived persona agents that message each other through a queue.
- **Many subagents per session, each playing a role.** Spawn a "tester agent" alongside the "coder agent" and have them coordinate.

**Why we rejected them:**

- Claude Code's subagent primitive (`Task` tool) is short-lived. Each spawn re-reads the world from cold; nothing persists between calls. Forcing a long-lived "team" pattern on top fights the grain of the tool.
- Building external multi-agent orchestration is a different project — would need its own runtime, message queue, state store, and would be slow + expensive (every handoff = full context reload).
- Most "roles" the user originally listed (issue tracker, scope keeper, progress tracker) aren't reasoning roles — they're just *files and tool calls*. Promoting them to agents adds complexity without value.

**What we use subagents for instead:** read-heavy research (`Explore`), cold-eyes review (`reviewer`), independent sanity checks (`/second-opinion`). Three types, used surgically. See D8.

**Consequence:** The bundle never spawns a "tester agent" or "debugger agent." It invokes the `tdd` skill or the `diagnose` skill in the main thread instead. If a future contributor proposes "let's add a persistent reviewer agent that watches the diff," push back hard — it's the AutoGen mental model creeping back in.

---

## D2 — The issue tracker is the shared brain

**Decision:** The issue tracker (GitHub Issues or GitLab Issues + Boards) is the single source of truth for scope, todo, in-progress, and progress. Every skill reads/writes through it. No parallel state store.

**Alternatives considered:**

- **Local files in the repo** (`docs/backlog.md`, `docs/todo.md`).
- **External tracker like Linear/Jira.**

**Why:**

- Local files don't survive across machines or have a status board, and the user works across machines.
- Linear/Jira would require rewriting the existing skills (`to-issues`, `triage`, `to-prd`) that already shell out to `gh`. Wrong tradeoff.
- GitHub/GitLab Issues are durable, free, browsable in a UI, scriptable, and the existing skill ecosystem already targets them.

**Consequence:** "Where is this work tracked?" always has one answer per project: the tracker. Don't add a `TASKS.md` file, don't add a private SQLite, don't track progress in a spreadsheet.

---

## D3 — Dual tracker support (GitHub + GitLab), auto-detected

**Decision:** Bundle supports both GitHub (personal/public projects) and the user's internal GitLab (work projects). Per-project tracker is auto-detected from `git remote get-url origin`, cached in `.claude/project.json`. An adapter layer (`adapter/tracker.py`) makes workflow skills tracker-agnostic.

**Alternatives considered:**

- **GitHub only.** User's internal work code can't go to public GitHub for security reasons.
- **GitLab only.** User has personal projects that live on GitHub.
- **Ask every time.** Annoying.

**Consequence:** Every workflow skill (`work-start`, `work-review`, etc.) calls into `adapter/tracker.py` rather than `gh` or `glab` directly. Adding a third tracker (Bitbucket, Gitea) means extending the adapter, not rewriting skills.

---

## D4 — Network presence is required for GitLab projects

**Decision:** When working on a GitLab project, Claude must be able to reach the internal GitLab host. If it can't (off-VPN, wrong machine), session-start preflight refuses to start work with a clear "connect to VPN / switch machines" message. **No outbox, no read-only fallback, no offline mode.**

**Alternatives considered:**

- **Outbox pattern** — queue tracker writes to `.claude/tracker-outbox.jsonl`, drain on reconnect.
- **Read-only fallback** — work from cached tracker state when offline.

**Why we rejected those:**

- User stated: "we should be forced to be 'on' the network anytime we are actively developing/working on the project."
- Outbox introduces drift risk (silent state divergence, double-creates on reconnect, dangling references).
- Read-only fallback introduces "stale data" footgun — Claude makes decisions based on outdated issue state.

**Consequence:** Removed ~half the complexity from the tracker adapter. Preflight is mandatory for GitLab projects, skipped for GitHub (public internet assumed).

---

## D5 — CI runs server-side per tracker; pre-push runs verify-fast locally

**Decision:** GitHub projects use GitHub Actions. GitLab projects use GitLab CI (the user's internal runners are reachable from the internal GitLab server, even though the GitLab server isn't reachable from outside the network). Local pre-push hook runs a fast subset (lint + typecheck + changed-file unit tests, ≤30s budget); CI runs the full suite. Pre-push blocks on failure with `--no-verify` override available.

**Alternatives considered:**

- **CI-only** — skip the local pre-push entirely.
- **Local-only full suite** — no CI for GitLab projects (originally assumed since the GitLab server isn't public-facing).

**Why this hybrid:**

- Local-only would mean broken pipelines on the GitLab server (since runners are internal, they actually CAN reach the server). User updated the constraint mid-design: "actually, lets assume that we CAN use GitLab CI as all internal services should be able to reach the GitLab server."
- CI-only means a 5-minute round trip to learn that you forgot a semicolon. Local pre-push catches the dumb mistakes in <30s.
- Full local suite (no CI) means no independent verification.

**Consequence:** CI templates are opinionated and identical-shaped across both trackers (`templates/gitlab-ci.yml.tmpl`, `templates/github-actions-main.yml.tmpl`). Reviewer skill reads CI status from the MR/PR, not from local. Pre-push hook lives at `<project>/.git/hooks/pre-push`, installed per-project (not globally).

---

## D6 — CI flakes retry once, then fail loud

**Decision:** When `/work-review` detects a failed CI pipeline, it parses the failure. If it looks like a flake (timeout, runner exited, network error), it retries **once** before treating it as real. Either way, log to `.claude/flakes.jsonl` for pattern-spotting.

**Alternatives considered:**

- **Higher retry budget** (2-3 retries) — common in flakey-CI environments.
- **No retry** — let every failure be real.

**Why one:**

- Higher retry budgets normalize flakiness instead of fixing it. The flakes log is the pressure-release valve — when you see a pattern (e.g. test stage flakes 3x in a week), fix the underlying flake, don't bump the budget.
- Zero retry means time wasted re-pushing for known-transient failures.

**Consequence:** Pattern data accumulates locally. `/team-stats` surfaces top failure-excerpt patterns. If the user sees the same flake repeatedly, that's the signal to fix it.

---

## D7 — Phase-tracked slices, advisory enforcement

**Decision:** Every piece of work moves through explicit phases — `design` → `implement` → `review` → `done` — driven by slash commands (`/work-start`, `/work-design-done`, `/work-review`, `/work-done`). Out-of-phase actions trigger **warnings, not blocks**. Strict enforcement is a per-project setting available but defaulted off.

**Alternatives considered:**

- **Implicit routing only** — just let main Claude pick skills based on user intent.
- **Strict enforcement** — `PreToolUse` hook blocks code edits during `design`, blocks merges before `review`, etc.

**Why advisory:**

- User stated: "most of the projects will mainly be me as the only human developer so it can be laxed. advising me instead of being strict is preferred."
- Strict mode adds friction without proportionate value for solo work where the developer can self-correct.
- Strict mode remains available for shared/work projects via `.claude/project.json` `enforcement.mode = "strict"`.

**Consequence:** `phase-warn.sh` only warns, never exits non-zero. The strict path is left as a TODO in the hook (see hook source). When implementing strict mode later, route through the same hook with a different exit code.

---

## D8 — Three subagent types, used surgically

**Decision:** The bundle uses subagents in exactly three scenarios:

1. **`reviewer`** — cold review of a diff with no conversation context (built-in `/review`, `/security-review`).
2. **`explorer`** — read-heavy research across the repo (built-in `Explore` agent type).
3. **`second-opinion`** — manual independent sanity check (`/second-opinion`).

**Not** used for: coder, tester, debugger, issue tracker, scope keeper, progress tracker, todo tracker. Those are skills or tool calls in the main thread.

**Why:**

- Subagents are valuable when (a) the work is read-heavy, (b) parallelizable, or (c) needs a fresh perspective uncontaminated by the main thread's context.
- Using them for "ongoing roles" is the AutoGen mental model from D1 — wrong fit for Claude Code.
- Each subagent spawn re-reads context from cold = expensive + slow. Use only when the cost is justified.

**Consequence:** If a future contributor proposes adding a `tester` or `debugger` subagent, push back. Those are skills (`tdd`, `diagnose`) in the main thread.

---

## D9 — Vertical slices, mandatory; one-sitting sizing

**Decision:** Every piece of work is a **vertical slice** — one capability cut through the full stack (DB → API → UI → test, or the project-shape equivalent for non-full-stack projects). Sized to **one focused work session (2-4 hours)**. Larger work uses the `epic` label with linked sub-issues; `/work-start <epic>` refuses and forces picking a child.

**Alternatives considered:**

- **Horizontal layers** ("build all the schemas first, then all the endpoints").
- **Larger slices** ("one PR no matter how long it takes").
- **Smaller slices** ("one commit per slice").

**Why:**

- User stated: "we should also incorporate vertical slices. so instead of building out the entire database schema before incorporating ui changes, we should build out a section of the database schema, add it to the ui, test the ui and debug any issues."
- The existing `to-issues` skill already enforces the tracer-bullet vertical-slice pattern — design aligns with infrastructure that exists.
- One-sitting sizing matches what makes vertical slices actually work in practice. Bigger and they become epics in disguise; smaller and they become horizontal work in costume.

**Generalization for non-full-stack:** "One externally-observable capability, fully wired and tested." Library = new public function + docs + test. CLI = new flag + handler + integration test. Data pipeline = new transformation + fixture-based test.

**Consequence:** `slice_check.py` heuristically flags horizontal-shaped or oversized issues at `/work-start` time (advisory). `to-issues` is the only sanctioned way to break down work — no ad-hoc horizontal tickets.

---

## D10 — Per-slice docs, in-repo source, Notion mirror for ops

**Decision:** Documentation is mandatory per-slice (not batched at release). Source of truth lives in the repo as markdown:

- `docs/user-guide/` — end users (in-repo only)
- `docs/troubleshooting/` — devs/support (in-repo only)
- `docs/training/` — cross-department scenario walkthroughs (in-repo only)
- `docs/adr/` — architectural decisions (in-repo only)
- **`docs/ops/{setup, troubleshooting, requirements}/`** — IT Ops audience, **auto-publishes to Notion** on merge to main

**Alternatives considered:**

- **All docs in Notion / Confluence / wiki.** Drift hard from code; can't be code-reviewed in the same MR.
- **All docs in repo, no Notion.** IT Ops won't go to GitLab to read setup docs.
- **Batched docs at release time.** Antipattern — docs never get written.

**Why this split:**

- User stated: "We have access to Notion and the IT Operations team will be better suited to access documentation in Notion rather than in the repo. I would like to have some of the documentation in Notion for that team."
- Per-slice keeps docs fresh (written while context is fresh, not from memory after).
- In-repo source means docs survive tooling changes, get reviewed in the same MR as code, and can't drift from the implementation.

**Consequence:** `/work-review` does an advisory completeness check — flags missing user-guide updates if user-visible behavior changed, flags missing troubleshooting if new error paths appeared, etc. `/work-docs` mid-slice generates stubs while context is fresh. The reviewer skill enforces the troubleshooting template (Symptom / What it means / Likely causes / How to fix / How to confirm).

---

## D11 — Notion is a mirror, never a source

**Decision:** Notion is published *to*; never edited *from*. CI publishes `docs/ops/` on merge to main. Manual `/publish-ops-docs` exists for ad-hoc republish. Every published page carries a banner: "Edit in repo, not here." Edits made directly in Notion are silently overwritten on next publish.

**Alternatives considered:**

- **Bidirectional sync.** Notion edits flow back to the repo.
- **Notion as primary, repo as backup.**

**Why one-way:**

- Bidirectional sync is a hard problem (conflict resolution, merge semantics, who wins) that we'd be reinventing for low value.
- Notion-as-primary loses code-review of doc changes and version-control of docs.

**Consequence:**

- Org-wide "Engineering Docs" Notion database, projects as a top-level filter (single bookmark for IT Ops; they don't need to know which project owns each doc).
- Deleted ops docs → deprecated banner added, then page archived (not deleted — IT Ops may have bookmarked it).
- Frontmatter (`notion_type`, `component`, `audience`, `last_reviewed`) drives Notion page properties.
- Requirements sections in setup/troubleshooting docs get promoted into a Notion "Requirements" filtered view (single source, two views).

---

## D12 — `/work-rethink` forces a decision

**Decision:** When a slice goes sideways mid-implementation (design assumption was wrong), `/work-rethink` snapshots WIP and forces a binary choice: (a) keep scope, change design (record new ADR, continue); (b) scope was wrong (file a spike, then either reshape or close the original). **No "leave both open, decide later" option.**

**Alternatives considered:**

- **Allow defer** — let the user keep both issues open and figure it out later.

**Why force the decision:**

- "Leave both open" is exactly the silent-state-drift the shared-brain design (D2) exists to prevent.
- The decision can be "close for now, revisit later" — but it must be a deliberate close, not a forgotten-open issue.

**Consequence:** Every `/work-rethink` produces a trail comment on the original issue and a `work_rethink` event in `.claude/events.jsonl`. Frequent rethinks = signal that slices are being filed at the wrong shape (slice-quality pressure surfaces in `/team-stats`).

---

## D13 — `/work-pause` with auto-generated "where I left off" summary

**Decision:** `/work-pause` snapshots `current-work.json` to `.claude/paused/<id>.json`, **including a Claude-generated short summary** of: goal, what's been done, next concrete action, blockers, non-obvious context. `/work-resume <id>` surfaces this summary so the slice picks up cold without re-discovery. SessionStart hook nudges on slices paused >7 days.

**Why the summary:**

- Resume-from-cold is the failure mode that kills context-switched work. Reading a diff doesn't reconstitute "what I was about to do." A summary written when context was fresh does.

**Consequence:** The summary is the magic ingredient — bundle authors should never skip generating it on pause, even for short pauses.

---

## D14 — Three visibility surfaces with separated concerns

**Decision:**

- **Status line (always-on, one line):** `[issue] phase | branch | ✓/✗ ci | ⚠ N urgent` — urgent counter only includes blocking things (failed CI, blocked review).
- **`/dashboard` (on-demand, rich):** full picture across projects; soft nudges (stale paused slices, missing docs) live here.
- **Notion dashboard (passive, cross-project):** nightly cron-published page in the Engineering Docs database, read-only, viewable without VPN-ing into the dev box. `/refresh-notion-dashboard` for manual refresh.

**Why all three:**

- Status line alone is too small for cross-project state.
- `/dashboard` alone means user has to remember to check; things rot silently.
- Notion alone is too async; you don't want to alt-tab to a browser to know your current branch's CI state.

**Why nightly (not hourly or real-time) for Notion:**

- Hourly burns API quota for marginal benefit; this dashboard is for *async* visibility.
- Real-time would need a webhook plumbing project we don't need.

**Consequence:** Status line counter must stay urgent-only — if it's always non-zero, it gets ignored. Soft nudges live in `/dashboard`.

---

## D15 — Where things live (skill bundle / per-user config / per-project state)

**Decision:** Three clean homes:

| Layer | Location | Why |
|---|---|---|
| Skill bundle | Internal GitLab repo, cloned to `~/.claude/skills/dev-team/` | Versionable, syncable across machines, requires VPN to clone/update (consistent with D4) |
| Per-user config | `~/.config/claude-dev-team/config.toml` (`chmod 600`) | Standard XDG location, machine-specific, plaintext (see D17) |
| Per-project state | `.claude/` inside each project repo (`project.json` committed; `current-work.json`, `paused/`, `events.jsonl`, `flakes.jsonl` gitignored) | Travels with the project; survives onboarding to a new machine |

**Alternatives considered:**

- **Public GitHub** for the skill bundle — rejected; user prefers internal GitLab.
- **OS keychain for tokens** — rejected for this use case; see D17.

---

## D16 — Single skill bundle (not nine separate skills)

**Decision:** Even though the bundle surfaces 19 slash commands, they all belong to one bundle (`dev-team`). One install, one version, one changelog.

**Alternatives considered:**

- **One skill per command** — 19 separate skill installs.
- **Smaller bundles by topic** — e.g. `dev-team-init` + `dev-team-work` + `dev-team-docs`.

**Why one:**

- The commands share state (`.claude/project.json`, `.claude/current-work.json`, `~/.config/claude-dev-team/config.toml`).
- Splitting means version-skew bugs (project bootstrap from v0.3 + work commands from v0.5).

**Consequence:** Updates are atomic. `/dev-team-update` pulls the entire bundle. No "partial install."

---

## D17 — Plaintext local secrets; deploy-time secrets are out of scope

**Decision:** Per-user config (`~/.config/claude-dev-team/config.toml`) holds tokens in plaintext, ACL-restricted to the user (`chmod 600` on Linux). For production deploys (whatever the project ships to), secrets are handled per-platform — Azure Key Vault for Azure deploys, `Export-CliXml` for Windows Server scripts, etc. The bundle does not provide a "production secrets" layer.

**Alternatives considered:**

- **OS keychain** (macOS Keychain, GNOME Keyring) — added complexity, behaves differently per distro, and the user explicitly opted out for Windows Credential Manager.

**Why plaintext:**

- User stated: "I don't want to use credential manager. Use plain text."
- Tokens are local-machine, low-blast-radius (revocable).
- Production secrets are a separate problem with platform-specific answers.

**Consequence:** `/dev-team-setup` writes `~/.config/claude-dev-team/config.toml` with `chmod 600`. The user is responsible for not committing it to git, not syncing it to cloud storage. If a token leaks, revoke and re-run setup.

---

## D18 — Local telemetry per project; no cross-project aggregation yet

**Decision:** `.claude/events.jsonl` and `.claude/flakes.jsonl` per project. `/team-stats` reads them. **No cross-project aggregation (no SQLite, no central store).**

**Alternatives considered:**

- **Cross-project SQLite at `~/.local/share/claude-dev-team/events.db`** for "am I getting better at slice-sizing across all projects?" metrics.
- **Notion-backed event store** for cross-project visibility.

**Why local-only-for-now:**

- YAGNI — we don't yet know which cross-project questions matter.
- Adding plumbing for value we may never use is the wrong default.

**Consequence:** If after a few months the user wants cross-project trends, promote to SQLite then. The events.jsonl format is forward-compatible.

---

## D19 — Linux-only dev environment (WSL2 or VM)

**Decision:** The bundle targets Linux. Windows native is out of scope. WSL2 (with project files inside the WSL filesystem, not on `/mnt/c/`) and dedicated Linux VMs are both supported.

**Alternatives considered:**

- **Native Windows** with PowerShell hooks and `icacls` ACLs.
- **Cross-platform** (Linux + Windows + macOS).

**Why Linux-only:**

- User stated: "we'll develop on either a linux VM or WSL. leave Windows OS out of the equation for development work."
- Most public Claude Code skills target Unix; aligning means we don't fight the ecosystem.
- One platform = ~20% less code (no `.ps1` hooks, no `if windows` branches in adapters, no `chmod` vs `icacls` divergence).

**Consequence:** All hook scripts are bash. All paths assume Unix conventions. Production targets (Azure, Windows Server) are unaffected — they're deployment targets, not dev environments.

---

## D20 — Bundle-owned venv for Python adapters

**Decision:** The bundle creates and owns a private virtual environment at `<bundle>/.venv/` at install time. `install.sh` runs `python3 -m venv` and pip-installs `adapter/requirements.txt` into it. Callers (hooks, slash commands) invoke adapter scripts via a generated wrapper `~/.claude/skills/dev-team/dt-python` which `exec`s the venv's Python. Stdlib-only Python snippets in hooks (JSON reads, file timestamps) keep using the system `python3` — they don't need the venv.

**Alternatives considered:**

- **`pip install --user -r adapter/requirements.txt`** (the original `INSTALL.md` instruction). Blocked by PEP 668 on Ubuntu 24.04 / Debian 12+ because the system Python is marked externally-managed.
- **`pip install --break-system-packages`.** Works in one line, fights the distro's package manager, and contradicts the "works the same everywhere" goal. The flag exists for emergencies, not for documented install paths.
- **`pipx` + repackage the adapters as installable CLIs.** Cleanest for true applications, but the adapters are also imported as libraries by other adapters (and would be by future helpers). Promoting them to standalone pipx-managed apps is more packaging work than the bundle's scale justifies.
- **System packages (`apt install python3-notion-client`).** Not all of `requirements.txt` is packaged in Debian; mixing apt and pip is its own footgun.
- **A user-wide venv at `~/.local/share/claude-dev-team/venv`.** Reasonable, but ties venv lifecycle to a separate path. Bundle-local venv keeps everything that belongs to the bundle inside the bundle dir, which makes "delete the clone" a complete uninstall.

**Why bundle-owned:**

- PEP 668 compliance without `--break-system-packages`.
- The venv lifecycle matches the bundle lifecycle. `install.sh` (re)creates it; `git clean -fdx` or deleting the bundle removes it. No orphaned environments after an uninstall.
- A single wrapper (`dt-python`) is the only thing callers need to know. The actual venv path is encapsulated; if it ever moves, the wrapper is regenerated by `install.sh` and callers don't change.
- Bundle dir is always writable by the user (it's their clone, in their home), so creating a venv inside it is always possible — no path-permission edge cases.

**Consequence:**

- `INSTALL.md` no longer instructs users to run `pip install` themselves. Running `./install.sh` is the only required Python-side step.
- `python3-venv` is now a documented prerequisite on Debian/Ubuntu (some minimal images omit it).
- The `adapter/` directory is symlinked into `~/.claude/skills/dev-team/adapter/` so slash command instructions can use the stable `~/.claude/skills/dev-team/...` path. Without that symlink, the bundle's clone path would leak into every command's instructions.
- CI templates (`templates/gitlab-ci.yml.tmpl`, `templates/github-actions-main.yml.tmpl`) are unaffected — CI runners have their own Python environment with their own deps. Future contributors should not try to share the dev-machine venv with CI; they are deliberately separate.
- Subagents / future automation that want to run adapter scripts should invoke `~/.claude/skills/dev-team/dt-python`, never the bundle's `.venv/bin/python` directly. The wrapper is the only stable contract.

---

## How to use this document

When changing the bundle:

- **Adding a feature?** Check whether it fits the existing decisions or fights them. If it fights one, that's the decision to revisit (and update the ADR).
- **Removing a constraint?** Check the alternatives section to see what you'd be giving up. Some constraints exist because the alternative was worse.
- **Onboarding a new contributor?** Have them read this doc + `SKILL.md` first. Then `docs/design-conversation.md` if they want the long-form reasoning.

When adding a *new* design decision, append a new ADR section here following the same structure: Decision / Alternatives considered / Why / Consequence.
