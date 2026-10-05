# Architectural Standards

A Claude Code plugin marketplace with one plugin, `standards`. The plugin audits a codebase against a set of distilled engineering lessons, then plans and carries out an incremental refactor toward a layered, modular, low-complexity architecture. It works with any language that shares these design principles.

## What's in this repository

| Path | What it is |
|---|---|
| `plugins/standards/references/LESSONS.md` | 125 language-neutral lessons, with no code or examples. Each one states the rule, why it matters, how to detect a violation and how to remedy it. This is the plugin's source of truth. |
| `plugins/standards/references/REFACTORING-PLAYBOOK.md` | Triage by drift, five step types, stages S0 to S9, and recipes R01 to R14 |
| `plugins/standards/references/ARTIFACTS.md` | The layouts of the files the commands write into a target repository |
| `plugins/standards/skills/` | The commands, plus the auto-loaded `lessons` skill |
| `plugins/standards/scripts/metrics.py` | Function length, complexity and parameter metrics, with a ratchet comparison |
| `ENGINEERING-STANDARDS.md` | The detailed reference standard, with C# examples, that the lessons were distilled from |

## Commands

| Command | What it does | Changes code |
|---|---|---|
| `/standards:audit [path]` | Measures the codebase, inventories drift, and writes prioritized findings to `docs/refactor/AUDIT.md` | No |
| `/standards:blueprint` | Maps today's components onto the target layers, modules and roles in `docs/refactor/BLUEPRINT.md`; short when the architecture is already aligned | No |
| `/standards:plan` | Turns the findings into ordered, verifiable steps (safety, fix, refactor, sweep, tooling) in `docs/refactor/PLAN.md` | No |
| `/standards:refactor [next\|step] [--steps N\|all] [--commit]` | Carries out plan steps one at a time, with a safety net, build, tests, a metrics ratchet and a log entry | Yes |
| `/standards:fix <lesson-id> [path] [--commit]` | Applies one lesson across a path in verified chunks, without a full plan | Yes |
| `/standards:review [base\|paths]` | Reviews a diff against the lessons and reports findings by lesson ID | No |
| `/standards:status` | Shows plan progress and metrics against the baseline | No |
| `/standards:lessons [lesson-id]` | Looks up a lesson. Claude also loads this skill on its own when designing, writing or reviewing code | No |

## Typical workflow

1. **`/standards:audit`** measures the drift and rates it: sound architecture with uneven hygiene (the usual case), partial drift, or heavy drift.
2. **`/standards:blueprint`** fixes the destination. For an aligned architecture it only lists corrections.
3. **`/standards:plan`** orders the work. Critical findings become fix steps that wait for your approval; repeated patterns become sweeps; structural findings become refactor steps.
4. **`/standards:refactor next`** carries out the plan, one step per run by default, or several with `--steps`. **`/standards:fix <lesson-id>`** handles a single lesson directly.
5. **`/standards:review`** checks each change before it merges, and **`/standards:status`** tracks progress and the ratchet.

The plugin never mixes structure and behavior changes in one step. It doesn't change behavior or public contracts without asking, and it never weakens a test to make it pass.

## Install

Run these from the root of the repository that should adopt the standard. Project scope enables the plugin only there:

```text
claude plugin marketplace add Polymathical/engineering-standards --scope project
claude plugin install standards@engineering-standards --scope project
```

Commit the `.claude/settings.json` that these commands write, so teammates who trust the folder get the same setup. Inside a session, `/plugin` shows the installed plugin and its commands.

**This repository is private.** Everyone who installs the plugin needs read access to it, and credentials that git can use without prompting. With the GitHub CLI, run `gh auth login` and then `gh auth setup-git`. To try a local checkout instead, pass its path to `claude plugin marketplace add`.

**Requirements:** git. For measured metrics, Python 3 and the `lizard` package (`pip install lizard`). Without them, the audit falls back to estimates.

## Releasing a change

1. Edit the lessons, playbook or skills.
2. Run `claude plugin validate . --strict` from the repository root.
3. Bump `version` in `plugins/standards/.claude-plugin/plugin.json`. Users receive a new copy only when the version changes.
4. Commit, and push to the shared remote.
