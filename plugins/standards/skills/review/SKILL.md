---
name: review
description: Review changes against the engineering lessons and report findings by lesson ID, with severity and suggested fixes. Read-only.
argument-hint: "[base-branch | path ...]"
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash(git diff:*) Bash(git log:*) Bash(git merge-base:*) Bash(git status:*) Bash(git rev-parse:*) Bash(git branch:*) Bash(git symbolic-ref:*)
---

# Review

Review a set of changes against `${CLAUDE_PLUGIN_ROOT}/references/LESSONS.md` and report the findings. Don't edit any files.

## What to review (`$ARGUMENTS`)

- **Nothing given:** uncommitted changes, plus the commits on this branch since it left the default branch.
- **A branch name:** everything on the current branch since its merge base with that branch.
- **One or more paths:** those files as they are now, reviewed whole.

## Procedure

1. Collect the diff and the list of changed files. Read enough of each file to judge each change in context.
2. Check each change against the lessons for that kind of code:
   - Entry points, endpoints and pages: ARCH-04, API-01, API-05, UI-07.
   - New types and modules: OOP-05, OOP-08, OOP-09, NAME-04 to NAME-08, ARCH-01 to ARCH-03.
   - Functions: CPLX-01 to CPLX-04, CPLX-09, CPLX-10, NAME-09 to NAME-11.
   - Data access: DATA-01 to DATA-08.
   - Remote calls: API-03, API-04, API-06, XCUT-02, ERR-05.
   - Errors and logs: ERR-01 to ERR-04, XCUT-01.
   - Security-relevant changes: SEC-01 to SEC-07.
   - UI components: UI-01 to UI-09.
   - Tests: TEST-01 to TEST-05.
   - Everything: HYG-01 to HYG-06.
3. Check the budget for each changed function and type (CPLX-01).
4. Apply the repetition lesson. Don't report repeated structure. Do report repeated facts (CPLX-05), new abstractions that don't pay rent (CPLX-06, CPLX-07), and copy-paste slips such as a copied route, entity, category or message that wasn't updated (CPLX-08).
5. If `docs/refactor/PLAN.md` has a step marked `doing`, or one just marked `done`, also check that the diff stays within that step's scope and that a refactor or sweep step doesn't change behavior (MIG-02, MIG-13).
6. Report a findings table (severity, lesson, `path:line`, issue, suggested fix) ordered by severity, then a verdict: ready, ready with follow-ups, or changes needed. Include only findings that matter, and say so plainly if there are none.
