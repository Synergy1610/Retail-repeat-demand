# Tasks

> **Status: not filled in yet.**
>
> The Team Lead creates the task breakdown here after the specification, architecture, and API contract are agreed. This file is the single source of truth for who does what.
>
> Only the Team Lead edits this file. Developers report status changes; they do not edit it, so two branches never conflict over the same document.

## 1. How to use this file

- Task IDs are `T-001`, `T-002`, … and never change once created.
- Branch names and commit messages use the task ID: `feature/T-003-login-ui`, `T-003: add login form UI`.
- A task is small enough if one agent can finish and test it in a single work session. Split anything larger.
- Every task has exactly one owner. The `Owner` column is both the team member and the assigned developer.
- Dependencies are task IDs. A task with an unfinished dependency stays `Blocked`.

### Status values

| Status | Meaning |
| --- | --- |
| `Not Started` | Defined and assigned, no work yet |
| `In Progress` | The owner is working on it now |
| `Blocked` | Cannot proceed — waiting on a dependency, decision, or external input |
| `In Review` | Pushed to a branch and waiting for the Team Lead |
| `Completed` | Reviewed, merged, and verified in `main` |

**Limit work in progress:** at most two `In Progress` tasks per developer at a time.

### Priorities

| Priority | Meaning |
| --- | --- |
| `High` | On the critical path for the demo; nothing works without it |
| `Medium` | Needed for a complete MVP, but the demo can survive briefly without it |
| `Low` | Polish, only after the MVP is integrated |

## 2. Team

| Member | Role | Owns |
| --- | --- | --- |
| Soorya | Team Lead | Specification, architecture, API contract, task plan, review, integration, deployment, demo |
| Veer | Developer (frontend / UI) | User interface, client-side state, API integration |
| Lavesh | Developer (backend / data) | API endpoints, database, validation, server-side logic |
| Fourth member | Research and testing (no agent) | Research, competitor analysis, test scenarios, bug reports, presentation |

## 3. Milestones

| Milestone | Target | Must be true to move on |
| --- | --- | --- |
| M1 — Foundation |  | Stack chosen, contract agreed, tasks assigned, repo cloned on all machines |
| M2 — Skeleton |  | App builds and starts; frontend and backend can reach each other |
| M3 — Core flow |  | The single most important user journey works end to end |
| M4 — MVP complete |  | All High priority tasks are `Completed` |
| M5 — Demo ready |  | Deployed, tested by the fourth member, presentation rehearsed |

## 4. Task board

| ID | Task | Owner | Role | Priority | Depends on | Status | Done when |
| --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |

<!-- Row format, for reference only — do not commit example tasks:

| T-003 | Build the login form | Veer | Frontend | High | T-001 | Not Started | Form renders, submits, shows validation and API errors |
| T-005 | Implement POST /auth/login | Lavesh | Backend | High | T-001 | Not Started | Endpoint matches the contract and returns 200/401 correctly |

-->

## 5. Progress

| Metric | Count |
| --- | --- |
| Total tasks | 0 |
| Not Started | 0 |
| In Progress | 0 |
| Blocked | 0 |
| In Review | 0 |
| Completed | 0 |

## 6. Task detail

Use this block for any task that needs more than one line of description.

```markdown
### T-000 — Task title

- **Owner:**
- **Role:**
- **Priority:**
- **Depends on:**
- **Status:**

**Goal**

**Scope**

- 

**Out of scope**

- 

**Acceptance criteria**

- [ ] 
- [ ] 

**Notes for the owner**
```

## 7. Handoff notes

<!-- The Team Lead records integration notes, contract changes, and environment requirements discovered during the event. Keep it short and dated. -->
