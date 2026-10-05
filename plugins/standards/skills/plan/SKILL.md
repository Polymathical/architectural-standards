---
name: plan
description: Turn the audit and blueprint into an ordered plan of small, verifiable steps (safety, fix, refactor, sweep, tooling) and write it to docs/refactor/PLAN.md.
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash(git log:*) Bash(git ls-files:*)
---

# Plan

Turn `docs/refactor/AUDIT.md` and `docs/refactor/BLUEPRINT.md` into `docs/refactor/PLAN.md`: an ordered list of small steps that move the code to the blueprint without breaking it.

References: stages, step types, recipes and sizing in `${CLAUDE_PLUGIN_ROOT}/references/REFACTORING-PLAYBOOK.md`; the MIG lessons in `${CLAUDE_PLUGIN_ROOT}/references/LESSONS.md`; the layout in `${CLAUDE_PLUGIN_ROOT}/references/ARTIFACTS.md` ("PLAN.md").

## Procedure

1. **Inputs.** Both documents must exist. If one is missing, stop and name the command that creates it (`/standards:audit` or `/standards:blueprint`).
2. **Commands.** Record the exact build, test and metrics commands in the plan header. If you can run the build and tests safely, confirm that they pass. If they don't, the first steps make them pass.
3. **Stages.** Use only the playbook stages that the audit's findings call for, following the path for the drift profile. A codebase with sound architecture usually needs S0, S1, S2, S3, S7, S6, S8 and S9. Say which stages are skipped and why.
4. **Steps.** Turn every audit finding into one or more steps, and mark which findings each step closes:
   - **Critical findings** become fix steps in S2. Each one needs user approval before it runs and has a test that pins the corrected behavior.
   - **A pattern repeated across many files** (logging templates, asynchronous naming, namespace form, unused imports, commented-out code) becomes one sweep step per chunk (a module or folder).
   - **Structural findings** become refactor steps, each applying one recipe to one unit.
   - **Untested units** get a safety step (R01) before the first step that changes them.
   - **Tooling** (analyzer configuration, the continuous-integration ratchet, boundary enforcement) goes in S1 in report-only mode, and is promoted in S9.
5. **Fields.** Each step has an ID (`S{stage}-{nn}`), title, type, recipe and lessons, findings closed, scope, prerequisites, verification, status `todo`, approval (for fix steps and contract changes) and notes.
6. **Order.** Order by prerequisites, then severity, then risk reduction (safety and facts), then value (units with many callers, I/O or state, and high churn), then quick wins.
7. **Size.** Each step must build, pass the tests and be revertible on its own, with a reviewable diff (aim for under about 400 changed lines, not counting mechanical moves and renames). Split anything larger.
8. **Scaffolding.** List each temporary facade, shim, overload or alias that the plan introduces, together with its cleanup step in S9.
9. **Update mode.** If PLAN.md already exists, keep its step IDs and statuses, never renumber a done step, append new steps, and mark obsolete ones `skipped` with a reason.
10. **Write** the plan and report: the steps per stage, the fix steps awaiting approval, the first five steps, and the next command (`/standards:refactor next`).

## Rules

- Structure changes and behavior changes go in separate steps (MIG-02). A bug found while planning becomes its own fix step.
- External contracts are preserved unless a dedicated step versions them (MIG-16).
- No step introduces an abstraction just to merge similar code (MIG-15).
- Write only `docs/refactor/PLAN.md`.
