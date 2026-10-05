# Refactor Artifacts

The plugin's commands keep their state in the target repository under `docs/refactor/`, so the work is reviewable in pull requests and can resume in any session. This file defines the layout of each artifact. Keep every artifact concise: counts and the top locations, not exhaustive dumps.

| File | Written by | Purpose |
|---|---|---|
| `AUDIT.md` | audit | Where the codebase stands against the lessons |
| `BLUEPRINT.md` | blueprint | Where the codebase is going |
| `PLAN.md` | plan, refactor, fix | The ordered steps and their status |
| `LOG.md` | refactor, fix | An append-only record of completed work |
| `metrics/baseline.json` | audit | Metrics at the start; the ratchet reference |
| `metrics/latest.json` | status, refactor | The most recent metrics |

Locations are written as `path:line`, relative to the repository root.

## AUDIT.md

1. **Header:** date, commit, scope (path audited), languages by file count, build and test commands found, metrics command used.
2. **Verdict:** one paragraph, plus the drift profile from the playbook: sound architecture with uneven hygiene, partial drift, or heavy drift.
3. **Drift by chapter:** a table with one row per chapter (ARCH, OOP, NAME, CPLX, ERR, XCUT, DATA, API, UI, SEC, TEST, HYG). Columns: status (aligned, partial, drifted), finding count, main reason.
4. **Metrics baseline:** files and functions analyzed; function length, complexity and parameter percentiles; counts over budget (functions over 30 lines, complexity over 10, more than 4 parameters, files over 300 lines); the largest types. State clearly if metrics were estimated rather than measured.
5. **Inventory:** for each category, a count and the top locations: hosts and entry points; modules and their dependencies; statics and global state (with kind); long parameter lists; oversized types, interfaces and pages; data-access sites outside repositories; external systems and where they are called; configuration access; repeated facts; error, asynchronous and logging patterns; tests and what they cover.
6. **Hotspots:** the top 10 files by change frequency combined with size or complexity.
7. **Findings:** a table with columns ID (F001 onward), severity (Critical, High, Medium, Low), lesson, location, evidence (one line), remedy (recipe or sweep), effort (S, M, L), and type (fix, refactor, sweep, safety, tooling).
8. **Recommendations:** the drift profile's path from the playbook, and the next command.

## BLUEPRINT.md

1. **Product name and module prefix.**
2. **Target modules:** a table with columns module, layer, responsibility, allowed dependencies, and status (exists, create, rename, split, merge).
3. **Hosts and composition roots:** each host, its entry point, and how its dependencies are wired.
4. **Context:** the context interface's members and the implementation per host, if the code depends on a current user, tenant or request.
5. **Configuration:** typed settings per section, sources and their precedence, and where secrets live.
6. **Component map:** a table with columns current unit, target type or types, role, module, and the recipes that get it there. One current unit may map to several targets.
7. **Conventions:** errors and results, logging, the asynchronous rules, the caching mechanism, the validation library, the testing frameworks and naming. Each convention names the lesson it follows.
8. **Corrections only:** if the architecture is already aligned, say so, and list only the structural corrections needed.
9. **Decisions and open questions:** each with an owner, and its status (decided, open).

## PLAN.md

1. **Header:** build command, test command, metrics command, link to the baseline, drift profile.
2. **Progress:** a table with one row per stage in use. Columns: stage, total steps, and counts of done, doing, todo, blocked and skipped.
3. **Steps,** grouped under stage headings, each with these fields:
   - **ID:** `S{stage}-{nn}`, such as `S7-03`. Never renumber a step that is done.
   - **Title:** imperative, such as "Convert log messages to constant templates in the billing module".
   - **Type:** safety, fix, refactor, sweep or tooling.
   - **Recipe and lessons:** such as R11 with XCUT-01.
   - **Findings closed:** audit finding IDs.
   - **Scope:** units, files or the chunk.
   - **Prerequisites:** step IDs.
   - **Verification:** the commands to run, and what to check.
   - **Status:** todo, doing, done, blocked or skipped. For blocked and skipped steps, add the reason.
   - **Approval:** required for fix steps and for contract changes. Record who approved it and when.
   - **Notes:** follow-ups and anything discovered along the way.
4. **Temporary scaffolding:** each facade, shim, overload or alias that is still in place, with its cleanup step.

## LOG.md

Append-only, newest entry last. Each entry has:

- Date and step ID (or the lesson ID for a direct fix), with the title.
- A summary in one to three sentences.
- The files changed, as a count plus the main paths.
- Tests added or changed.
- The metrics change for the touched scope (before and after for the affected counts).
- Follow-ups, including any bugs found and recorded as new fix steps.
- The commit, if one was made.
