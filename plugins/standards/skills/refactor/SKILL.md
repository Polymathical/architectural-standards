---
name: refactor
description: Execute the next step, or a named step, of docs/refactor/PLAN.md as a small change verified by build and tests, then record it in the plan and log.
argument-hint: "[next | step-id] [--steps N|all] [--commit]"
disable-model-invocation: true
---

# Refactor

Carry out steps from `docs/refactor/PLAN.md`, one at a time.

Arguments (`$ARGUMENTS`):

- `next` (the default) or a step ID such as `S7-03`.
- `--steps N` or `--steps all`: keep going for up to N steps, or until the plan is done. Stop at the first failure or at any decision that needs the user.
- `--commit`: commit each completed step. Without it, propose a commit message and ask.

References: recipes, the sweep procedure and the verification protocol in `${CLAUDE_PLUGIN_ROOT}/references/REFACTORING-PLAYBOOK.md`; lessons in `${CLAUDE_PLUGIN_ROOT}/references/LESSONS.md`; the LOG layout in `${CLAUDE_PLUGIN_ROOT}/references/ARTIFACTS.md`.

## Before the first step

1. Read the plan header for the build, test and metrics commands. If there is no plan, stop and suggest `/standards:plan`.
2. Run `git status`. If there are uncommitted changes that this plan didn't make, ask before continuing.
3. If you're on the default branch, propose a branch named `refactor/{step-id}-{kebab-title}`, and create it once the user agrees.

## For each step

1. **Select.** Take the named step, or the first `todo` step whose prerequisites are all `done`. Mark it `doing` in PLAN.md.
2. **Approve.** A fix step, or any step that changes a public contract, needs the user's approval. Show what will change and why, and wait. Record the approval in the step.
3. **Study.** Read the step's recipe and lessons, and every file in its scope, before editing.
4. **Safety net.** Make sure tests pin the behavior of the code the step changes (MIG-01). If they don't, write characterization tests first (R01) and run them green against the unchanged code. Purely mechanical sweeps that the build verifies, such as removing unused imports, don't need new tests.
5. **Change.** Apply the recipe, or the sweep's mechanical change, to the step's scope only.
   - Refactor and sweep steps keep behavior identical (MIG-02). A fix step changes only the targeted behavior, and adds a test that pins the corrected behavior.
   - Name anything new according to the naming lessons.
   - Don't add abstractions to merge similar code (MIG-15).
   - Use the language's refactoring tools for moves and renames.
   - Note any opportunity outside the scope in the step's notes instead of acting on it.
6. **Verify.** Build. Run the affected tests, then the full suite. Run the metrics command with `--compare` against the baseline: no over-budget count may rise (MIG-14). Then review your own diff against the lessons, as `/standards:review` does.
7. **On failure.** If the cause is inside the step's scope, fix it. Otherwise stop: explain the failure, ask before discarding any changes, and mark the step `blocked` with notes. Never weaken, skip or delete a test to make it pass.
8. **Record.** Mark the step `done` in PLAN.md, and update the progress table and any scaffolding entries. Append a LOG.md entry with the date, step, summary, files, tests, metrics change and follow-ups. A bug found along the way becomes a new fix step; don't fix it inside this one.
9. **Commit.** With `--commit`, commit the step with an imperative message that cites the step ID and its lessons. Otherwise, propose the message and ask.
10. **Continue or stop.** Stop after one step unless `--steps` allows more. Always stop for a fix step that hasn't been approved, a contract change, a safety net you can't build, or a product decision.

## Scope discipline

- If a step turns out bigger than planned, split it in PLAN.md and do only the first part.
- Mechanical moves and renames go in their own steps.
- Finish with a short report: the steps completed, their verification results, the metrics change, and the next step.
