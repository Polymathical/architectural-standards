---
name: status
description: Show refactoring progress from docs/refactor/PLAN.md and LOG.md, and compare the current metrics with the audit baseline.
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash(git log:*) Bash(git status:*)
---

# Status

1. **Plan.** Read `docs/refactor/PLAN.md` and count the steps by status in each stage. If there's no plan, say which command comes next: `/standards:audit`, `/standards:blueprint` or `/standards:plan`.
2. **Recent work.** Read the last five entries in `docs/refactor/LOG.md`.
3. **Metrics.** If `docs/refactor/metrics/baseline.json` exists, run the metrics command from the plan header with `--out docs/refactor/metrics/latest.json --compare docs/refactor/metrics/baseline.json`. Show the change in each over-budget count. Flag any count that rose, because that breaks the ratchet (MIG-14). If Python or lizard isn't available, say so and skip this step.
4. **Report:**
   - A progress table by stage (done, doing, todo, blocked, skipped).
   - Blocked steps with their notes, and fix steps still awaiting approval.
   - Temporary scaffolding that hasn't been cleaned up.
   - The metrics trend against the baseline.
   - The next step to run, with its command (for example `/standards:refactor next`).
