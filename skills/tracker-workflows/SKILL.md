---
name: tracker-workflows
description: Use 3J Tracker for identity-safe issue work, roadmap creation, ticket content standards, acceptance-criteria-derived native test coverage, Tracker-ID handoffs, and exact-head merge gates. Trigger whenever a request asks to inspect, create, update, verify, hand off, or gate work in Tracker.
metadata:
  author: 3J Technologies
  version: "1.0.1"
  requirements: Network access. Authentication uses the host's native MCP OAuth flow; no manual configuration is required.
---

# Tracker Workflows

Use the Tracker MCP tools supplied by this plugin. Treat Tracker as a multi-tenant system and never infer the active identity, workspace, IDs, or configured vocabulary.

## Start identity- and vocabulary-first

1. Call `whoami` before any workspace read or write. State the resolved workspace when it matters.
2. Before a write that needs status, priority, item type, label, member, or custom-field IDs, call `get_workspace_vocabulary`. Test cases and test plans are native quality entities; they are not item types.
3. Prefer compact reads: `search`, `find_tickets`, `get_ticket(include=[...])`, `manage_test_plan(action="get")`, and `get_delivery_test_evidence`. Ask only for related data needed for the decision.
4. Carry stable Tracker human IDs such as `TRK-2416` in prose, commits, pull requests, and handoffs. Use UUIDs only where a tool requires them.

## Duplicate-safe creation

Before creating a ticket, roadmap item, test case, test plan, release, or similar entity:

1. Search by exact title, distinctive keywords, and known Tracker ID.
2. Reuse or update an existing matching entity when the requested outcome is already represented.
3. If similarity is ambiguous, report candidates and ask before creating a duplicate.
4. After a successful create, keep the returned ID and do not blindly retry a timed-out or partial composite write. Re-read first.

## Roadmaps

1. Resolve the project, item-type, status, priority, assignee, and label IDs first.
2. Create a small hierarchy with clear acceptance criteria and explicit dependencies. Keep backend-owned business rules in Tracker rather than recreating them in prose.
3. Use parent/child relationships, milestones, sprints, blockers, and scheduling dependencies only when they reflect real sequencing.
4. Re-read the created items and links. Report stable Tracker IDs in dependency order.

## Ticket content standards

Write ticket content so the acceptance criteria can be verified without asking the reporter for more information. Apply this when creating a ticket and when materially refining one (any change to its acceptance criteria).

Feature and story tickets must capture:

- Outcome — the change in observable behavior or capability.
- Who benefits and why.
- Scope.
- Out of scope.
- Acceptance criteria that are testable, preferably as Given/When/Then.

Bug tickets must capture:

- Problem and affected users.
- Steps to reproduce.
- Expected behavior.
- Actual behavior.
- Environment/version.
- Acceptance criteria that restore the expected behavior, include a regression test, and verify relevant edge cases.

## Deriving native test cases from acceptance criteria

When creating a ticket or materially refining one (a new ticket, or a change to its acceptance criteria), turn its acceptance criteria into native test coverage as part of that same action:

1. Search first (Duplicate-safe creation) for an existing native case or plan that already covers the same behavior; reuse or update it instead of drafting a parallel one.
2. Derive cases from the acceptance criteria, not from a mechanical one-case-per-bullet pass:
   - Consolidate criteria that exercise the same behavior into one case; do not create near-duplicate cases.
   - Keep each case's precondition, action, and expected result specific enough to execute without re-reading the ticket.
   - Add regression and edge cases only when the ticket's own content justifies them (bug history, stated scope, explicit edge conditions) — do not invent product behavior to round out coverage. For a bug ticket, a regression case that reproduces the original defect is required, not optional.
   - If an acceptance criterion is ambiguous or not testable as written, flag it back on the ticket instead of guessing at the intended behavior.
3. Group the resulting cases in one native test plan scoped to this work item and link that plan to the ticket. Reuse and update an existing plan for the same work item or feature area rather than creating a parallel one.
4. Cases and plans are native quality entities (`manage_test_case`, `manage_test_plan`). Never create a ticket item type named Test Case or Test Plan as a substitute for either.
5. Authoring a plan or cases is not a request to run them. Starting an execution locks the plan's scope, so do not start one unless the human asked for it or a separate step in your instructions calls for it.
6. For small or trivial work where a full native test plan would add no value (a copy fix, a config tweak with no behavioral branch), do not build one by default. Make and state an explicit proportionality decision instead — for example, link the change to one existing case, or record on the ticket how its acceptance criteria will be verified without a dedicated plan. Every acceptance criterion still needs a traceable path to how it gets verified, even when that path is not a formal test plan.

## Native test management and evidence

1. Use `manage_test_case` to list, read, create, update, or delete reusable native cases. Do not create a ticket item type named Test Case or Test Plan as a substitute for either.
2. Use `manage_test_plan` for native plans and reversible links to cases and work items. Plan scope becomes immutable after the first execution starts; retire/version instead of rewriting history.
3. Use `manage_test_execution` to start, list, complete, cancel, or compare runs. Use `record_test_result` to record results and evidence while a run is in progress. Evidence may be URL, file, screenshot, log, or note metadata; never put credentials in evidence.
4. Completed or cancelled results are immutable. Only use `record_test_result(action="amend")` for a genuine admin-approved correction, always include a specific reason, and preserve the original evidence trail.
5. Use `get_delivery_test_evidence` for the compact delivery view and `manage_test_execution(action="compare")` for regressions across runs.

## Portable handoff

Handoffs must remain useful outside the current chat. Include:

- Tracker IDs and concise outcome;
- exact repository, branch, and commit SHA when code is involved;
- files or surfaces changed;
- commands and tests run with their results;
- native test plan, execution, and evidence IDs;
- remaining risks, blockers, and required approvals.

Never rely on a chat-only pointer such as "see above."

## Exact-head merge gate

Before saying work is merge-ready:

1. Resolve the pull request's current head SHA and record it in the Tracker handoff or evidence.
2. Verify required CI and review decisions against that exact SHA, not an earlier successful run.
3. Re-check the head after verification. If it changed, invalidate the gate and verify again.
4. Link the exact execution or evidence to the Tracker work item. Do not equate "tests passed locally" with a merge gate.

## Safety

- Treat delete, bulk mutation, rejection, irreversible transitions, and replacement of evidence as destructive. Show the exact target and consequence, then wait for explicit human confirmation before using `confirm=true`.
- Association unlinking is reversible but can change delivery meaning; identify both entities before doing it.
- Never expose, store, or request session credentials, API keys, or cookies in prompts, skills, MCP configuration, evidence, or handoffs. Authentication belongs entirely to the host's native MCP OAuth flow.
- Preserve legacy tickets when migrating toward native QA. Link new native cases or plans to them and annotate the legacy records; do not delete or silently convert them.
