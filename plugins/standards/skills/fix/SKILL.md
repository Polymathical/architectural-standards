---
name: fix
description: Apply one engineering lesson across a path in small, verified chunks, without a full audit or plan. Suited to repeated issues such as log templates, async hygiene, swallowed errors or unused code.
argument-hint: "<lesson-id> [path] [--commit]"
disable-model-invocation: true
---

# Fix one lesson

Apply the lesson named in `$ARGUMENTS` to the given path (default: the repository root), one chunk at a time, verifying as you go.

References: the lesson's Detect and Remedy lines in `${CLAUDE_PLUGIN_ROOT}/references/LESSONS.md`; its recipe and the sweep procedure in `${CLAUDE_PLUGIN_ROOT}/references/REFACTORING-PLAYBOOK.md`.

## Procedure

1. **Read the lesson.** Find the lesson ID in LESSONS.md, then read its Detect and Remedy lines and the recipe they point to. If no lesson ID was given, ask for one.
2. **Classify the change.**
   - **Mechanical and behavior-preserving** (a sweep), such as constant log templates, asynchronous naming, namespace form, unused imports or commented-out code: continue.
   - **Structural, one unit at a time** (refactor recipes such as R05, R06 or R07): list the units, then ask whether to handle the first few now or to create a plan with `/standards:plan`.
   - **Behavior-changing** (a fix), such as adding a missing authorization check, or letting a swallowed error propagate: list every occurrence and get the user's approval, for each item or for the batch, before changing anything.
3. **Detect.** Find every occurrence in scope using the lesson's Detect signals. Report the count and group the occurrences into chunks by module or folder. If there are more than about 200 occurrences or 10 chunks, ask whether to do all of them or only the first chunks.
4. **Safety.** Confirm that the build and tests pass before you start. For changes that aren't purely mechanical, make sure tests cover the touched code; add characterization tests (R01) where they're missing.
5. **Each chunk.** Apply only this lesson's change. Then build, run the tests, and record the occurrence count before and after. Stop at the first failure you can't fix inside the chunk. Never weaken a test.
6. **Record.** If `docs/refactor/` exists, append a LOG.md entry for each chunk. If PLAN.md exists, mark the matching sweep steps done, or add them as done steps.
7. **Commit.** With `--commit`, commit each chunk with an imperative message citing the lesson ID. Otherwise, propose the messages and ask.
8. **Report** the counts before and after, the files changed, and any occurrences you skipped and why. Then name the analyzer or linter rule in this language's ecosystem that would keep the count at zero, if one exists, and offer to enable it in report-only mode.

## Rules

- One lesson per run, and no unrelated changes.
- Never merge repeated structure into a new abstraction (MIG-15). Single-sourcing repeated facts is only in scope when the lesson is CPLX-05.
- Separate behavior changes from structure changes (MIG-02). If a "mechanical" change turns out to alter behavior, stop and ask.
