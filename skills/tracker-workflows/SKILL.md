---
name: tracker-workflows
description: Use 3J Tracker for identity-safe issue work, project-scoped roadmap creation, ticket content standards, acceptance-criteria-derived native test coverage, forms/approvals/calendar/releases/sprints, handoff and triage tools, Tracker-ID handoffs, and exact-head merge gates. Trigger whenever a request asks to inspect, create, update, verify, hand off, schedule, approve, or gate work in Tracker.
metadata:
  author: 3J Technologies
  version: "1.0.2"
  requirements: Network access. Authentication uses the host's native MCP OAuth flow; no manual configuration is required.
---

# Tracker Workflows

Use the Tracker MCP tools supplied by this plugin. This is the remote, multi-tenant MCP deployment: it holds no credential of its own, and every call acts strictly as the caller, in the workspace chosen at OAuth consent, with that caller's own permissions. Never infer the active identity, workspace, IDs, or configured vocabulary — resolve each one with the tools below.

## Start project-, identity- and vocabulary-first

Tracker is project-first: every work item, wiki page, form, test case, test plan, release, and sprint lives in exactly one project — this is a hard partition, not a default. List and create calls take `project_id`, which accepts either a project's id or its key (e.g. `WEB`). Moving an item to another project gives it a new key there; the old key still resolves, so a stale link is not a broken one.

1. Resolve the project first with `list_projects` (pass `overview=true` for a portfolio view). Do this before any project-scoped read or write — guessing a key wastes a round trip once, but guessing wrong silently reads or writes the wrong project's data.
2. Call `whoami` before any workspace read or write. State the resolved workspace when it matters.
3. Before a write that needs status, priority, item type, label, member, or custom-field IDs, call `get_workspace_vocabulary` first. These are per-workspace rows with workspace-generated IDs, not global enums, so they cannot be guessed — the tool fetches all six kinds (statuses, priorities, labels, item types, custom fields, members) concurrently in one call. Test cases and test plans are native quality entities; they are not item types.
4. Prefer compact reads: `search`, `find_tickets`, `get_ticket(include=[...])`, `manage_test_plan(action="get")`, and `get_delivery_test_evidence`. Ask only for related data needed for the decision.
5. Carry stable Tracker human IDs such as `TRK-2416` in prose, commits, pull requests, and handoffs. Use UUIDs only where a tool requires them.

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
3. Group the resulting cases in one native test plan scoped to this work item and link that plan to the ticket. Reuse and update an existing plan for the same work item or feature area, in the same project, rather than creating a parallel one — a plan's cases and work items must share its project.
4. Cases and plans are native quality entities (`manage_test_case`, `manage_test_plan`). Never create a ticket item type named Test Case or Test Plan as a substitute for either.
5. Authoring a plan or cases is not a request to run them. Starting an execution locks the plan's scope, so do not start one unless the human asked for it or a separate step in your instructions calls for it.
6. For small or trivial work where a full native test plan would add no value (a copy fix, a config tweak with no behavioral branch), do not build one by default. Make and state an explicit proportionality decision instead — for example, link the work item to a test plan that already contains the relevant case (creating a small, one-case plan if none fits — test cases only link to plans, not directly to work items, and only plans link to work items), or record the case reference in a ticket comment. Every acceptance criterion still needs a traceable path to how it gets verified, even when that path is not a formal test plan.

## Native test management and evidence

1. Use `manage_test_case` to list, read, create, update, or delete reusable native cases. Do not create a ticket item type named Test Case or Test Plan as a substitute for either.
2. Use `manage_test_plan` for native plans and reversible links to cases and work items. Plan scope becomes immutable after the first execution starts; retire/version instead of rewriting history.
3. Use `manage_test_execution` to start, list, complete, cancel, or compare runs. Use `record_test_result` to record results and evidence while a run is in progress. Evidence may be URL, file, screenshot, log, or note metadata; never put credentials in evidence.
4. Completed or cancelled results are immutable. Only use `record_test_result(action="amend")` for a genuine admin-approved correction, always include a specific reason, and preserve the original evidence trail.
5. Use `get_delivery_test_evidence` for the compact delivery view and `manage_test_execution(action="compare")` for regressions across runs.

## Forms and intake

- `list_forms` / `get_form` read a project's intake forms; `manage_form` creates, updates, or deletes one (delete requires `confirm=true`). Every form belongs to exactly one project — `project_id` is required on create and moves the form on update.
- `list_form_responses(form_id=...)` reads raw submissions to one form. Pass `intake_queue=true` with `project_id` instead to read that project's Intake Queue — submissions, email, and portal requests still awaiting a triage decision (convert to ticket, merge, or dismiss) — which ignores `form_id`.
- Known limitation (TRK-2255): `manage_form(action="create")` 500s when the caller authenticates with an API key not linked to a user account, which is how most autonomous agents authenticate — the form's owner is a foreign key to a real user row. This is a pre-existing backend bug, not a bad payload; retry with a user-linked credential (a PAT) rather than reworking the fields.

## Approvals

- `create_approval` routes a decision to a human instead of making it yourself. `type` must be one of `plan`, `deploy`, `merge`, `prod`, `handoff`, or `other` — the API rejects anything else.
- `list_approvals(project_id=...)` reports what is pending; report it, do not act on it. `decide_approval` is a governance action — call it only when a human has explicitly asked you to approve or reject that specific request, never on your own initiative because you noticed it while listing.

## Calendar and booking links

- `create_calendar_event` / `list_calendar_events` / `manage_calendar_event` (update/delete, delete requires `confirm=true`) manage events, optionally linked to a ticket. `attendees` must be a list of objects (`{"email": ..., "name": ...}`); a bare list of email strings is rejected.
- `manage_booking_links` manages a user's own public `/book/{slug}` scheduling page (list/create/update/delete/bookings) and, via `action="set_availability"`, the caller's working-hours/buffer config used by that page.
- Known limitation (TRK-2255): `create_calendar_event` shares the same unlinked-API-key 500 as forms — retry with a user PAT, not a payload rewrite.

## Releases and sprints

- Releases (`create_release`, `manage_release`, `list_releases`) are the "reported in X / fixed in Y" version register for a project, not a deploy mechanism. Deleting a release can orphan those references, so `manage_release(action="delete")` requires `confirm=true` and should only target releases you've confirmed are unreferenced or intentionally being cleaned up.
- Sprints (`list_sprints`, `get_sprint`, `manage_sprint`) hold tickets for planning; deleting a sprint does not delete its tickets (they return to Backlog), but the sprint record itself cannot be recovered, so `manage_sprint(action="delete")` requires `confirm=true`.
- `transition_sprint` starts or completes a sprint — kept separate from `manage_sprint` because these fire real side effects. Completing requires every ticket in the sprint to already be Done or Cancelled (TRK-2137); if any ticket is still open the API refuses with 409 and the sprint stays active. Close, cancel, or move the stragglers out first (`update_ticket(sprint_id=...)` or `set_ticket_state`) — nothing carries over automatically.
- Milestones and features sit above sprints for longer-lived planning (`get_project_plan` with `milestone_id`, `update_ticket`'s `plan.milestone_id`, `manage_feature`/`create_feature`); resolve the project and read the existing plan before creating a new one, per Duplicate-safe creation above.

## Handoff and triage tools

- `file_handoff` records the did/changed/verified trail for the next person or agent to pick up work without re-deriving it. `changed` items are objects (`{"kind": "file"|"pr"|"deploy"|"other", "label": ..., "href": ...}`), not bare strings. `verified` is the load-bearing field — say what you actually checked and what you did not, rather than implying full coverage.
- `decide_handoff` approves or dismisses a filed handoff — a governance action like `decide_approval`, called only on explicit human instruction.
- `assign_agent(ticket_id, agent_id)` assigns a registered AI agent to a ticket; `agent_id` is required (there is no "unassign" via an omitted id — that 422s server-side).
- `triage_ticket` runs or reads AI triage suggestions (`action="run"` or `"suggestions"`) and accepts or dismisses one suggested field at a time (`action="accept"|"dismiss"`, with `field` naming which one).
- `set_ticket_state` closes, reopens, or ticks/unticks a ticket's done checkbox (`close`/`reopen`/`done`/`not_done`). It is deliberately separate from `update_ticket` because it fires notifications and sprint accounting — use it for state changes, not a status_id set in passing.
- `link_tickets` connects two tickets: `kind="relation"` (blocks/blocked_by/relates/duplicates/duplicated_by), `kind="blocker"` (records a blocking dependency, internal or external), or `kind="dependency"` (a scheduling edge used by the critical-path planner).

## Portable handoff

Handoffs must remain useful outside the current chat. Include:

- Tracker IDs and concise outcome;
- exact repository, branch, and commit SHA when code is involved;
- files or surfaces changed;
- commands and tests run with their results;
- native test plan, execution, and evidence IDs;
- remaining risks, blockers, and required approvals.

Never rely on a chat-only pointer such as "see above." Use `file_handoff` to record this on the ticket itself, not only in chat.

## Exact-head merge gate

Before saying work is merge-ready:

1. Resolve the pull request's current head SHA and record it in the Tracker handoff or evidence.
2. Verify required CI and review decisions against that exact SHA, not an earlier successful run.
3. Re-check the head after verification. If it changed, invalidate the gate and verify again.
4. Link the exact execution or evidence to the Tracker work item. Do not equate "tests passed locally" with a merge gate.

## Safety

- Treat delete, bulk mutation, rejection, irreversible transitions, and replacement of evidence as destructive. Destructive curated tools (`bulk_delete_tickets`, `bulk_update_tickets`, `manage_form`/`manage_calendar_event`/`manage_release`/`manage_sprint` deletes, `manage_member` change_role/remove, and similar) fail closed by design: they return `data.confirmation` describing the exact action with `request_sent=false` until you resend the call with `confirm=true`. Never manufacture that approval or set `confirm=true` from your own reasoning — show the exact target and consequence, then wait for explicit human confirmation, unless the human already explicitly requested that exact destructive action.
- `decide_approval` and `decide_handoff` are the same kind of governance action even though they take no `confirm` flag: call them only on explicit human instruction, never because you noticed a pending item while listing.
- Association unlinking is reversible but can change delivery meaning; identify both entities before doing it.
- Never expose, store, or request session credentials, API keys, or cookies in prompts, skills, MCP configuration, evidence, or handoffs. Authentication belongs entirely to the host's native MCP OAuth flow. Remember this MCP is multi-tenant: it acts strictly as the caller, in the workspace chosen at OAuth consent — never assume, switch, or ask for a different workspace's identity mid-session.
- Preserve legacy tickets when migrating toward native QA. Link new native cases or plans to them and annotate the legacy records; do not delete or silently convert them.
