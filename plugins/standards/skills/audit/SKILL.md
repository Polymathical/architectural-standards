---
name: audit
description: Audit a codebase against the engineering lessons and write a drift report with metrics, an inventory and prioritized findings to docs/refactor/AUDIT.md. Changes no source code.
argument-hint: "[path]"
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash(git ls-files:*) Bash(git log:*) Bash(git rev-parse:*) Bash(git status:*)
---

# Audit

Assess how far the code at `$ARGUMENTS` (default: the repository root) has drifted from the engineering lessons, and write `docs/refactor/AUDIT.md`. Don't modify source code.

References (read only the sections you need):

- Lessons: `${CLAUDE_PLUGIN_ROOT}/references/LESSONS.md`
- Drift profiles, step types and recipes: `${CLAUDE_PLUGIN_ROOT}/references/REFACTORING-PLAYBOOK.md`
- Report layout: `${CLAUDE_PLUGIN_ROOT}/references/ARTIFACTS.md`, section "AUDIT.md"

## Procedure

1. **Scope.** List tracked source files under the target path with `git ls-files`. Exclude generated, vendored and build output (bin, obj, dist, build, out, node_modules, vendor, packages, migrations, minified and generated files). Record the languages by file count.

2. **Orient.** Find the build and test commands from solution and project files, package manifests, build scripts and pipeline definitions. Find the entry points: process mains, web hosts, endpoints and controllers, message and job handlers, command-line tools and UI pages. Note the test projects and roughly what they cover.

3. **Measure.** If Python is available, run:
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/metrics.py" <path> --out docs/refactor/metrics/baseline.json`
   It needs the `lizard` package. If lizard is missing, ask the user whether to install it (`pip install lizard`) or to continue without measured metrics. Treat the output as heuristic: open the top outliers before reporting them, because data initializers are sometimes counted as functions. Without the script, estimate from the largest files and a sample of functions, and say so in the report.

4. **Inventory.** For each category, record a count and the top locations (`path:line`), not every occurrence. In a large codebase (more than about 300 source files), hand categories to parallel Explore subagents and ask each for counts and its top 10 locations.
   - Statics or module-level functions that do I/O or hold mutable state; globally reachable singletons; "current user, tenant or request" holders (MIG-05, MIG-06, ARCH-05, OOP-09).
   - Functions with more than 4 parameters, mode or boolean flags, and pass-through parameters (CPLX-01, CPLX-10, MIG-07).
   - Oversized types, interfaces, pages and files, and constructors with more than 5 dependencies (CPLX-01, OOP-05, OOP-08, UI-07).
   - Business logic, queries or remote calls in entry points, endpoints and pages (ARCH-04, API-01, UI-07).
   - Data access outside repositories, long-lived or shared connections and contexts (DATA-01, DATA-02).
   - External systems: where clients are created and called; inline authentication, retries or caching (API-03, API-04, XCUT-02, ERR-05).
   - Configuration and secrets: keys read as strings in several places, environment reads in logic, secrets or environment-specific addresses in source (ARCH-07, API-06, SEC-06).
   - Repeated facts: the same address, key, identifier, code, label or threshold in several places (CPLX-05). Don't count repeated structure.
   - Two mechanisms for one concern, such as two caching approaches (XCUT-03).
   - Security: state-changing operations without authorization, hard-coded identities, unauthenticated endpoints, protection commented out (SEC-04, SEC-05, SEC-07).
   - Errors, asynchronous code and logging: empty or swallowing catches, generic error types, blocking waits, unobserved asynchronous calls, unawaitable asynchronous functions, interpolated log messages, wrong logger categories (ERR-01, ERR-03, CPLX-09, XCUT-01, HYG-06).
   - UI lifecycle: subscriptions without disposal, busy-waits, magic step indexes (UI-06, UI-08).
   - Naming and consistency: generic names, abbreviations, mixed conventions (asynchronous markers, namespace forms, file and type mismatches, environment file casing) (NAME-01 to NAME-18).
   - Hygiene: commented-out code, dead branches, demo data in production paths, unused imports and dependencies, regions, untracked TODOs (HYG-01 to HYG-05).
   - Tests: which units are covered; naming and isolation (TEST-01 to TEST-05).
   - Copy-paste slips: copied blocks whose route, entity, category or message still points at the original (CPLX-08).

5. **Hotspots.** Rank files by how often they changed in the last 12 months (`git log --since="12 months ago" --name-only --format=""`), combined with size or complexity. List the top 10.

6. **Findings.** Turn the inventory into findings. Each one gets an ID (F001 onward), severity, lesson, location, one line of evidence, a remedy (recipe or sweep), effort (S, M or L) and a step type (fix, refactor, sweep, safety or tooling). Severity:
   - **Critical:** a correctness, security or data-loss risk, such as a missing authorization check, an error swallowed on a write, a secret in source, an endpoint calling the wrong route, or a check whose result is ignored.
   - **High:** blocks testability or the target architecture, such as statics doing I/O, global mutable state, layering violations or functions with more than 10 parameters.
   - **Medium:** over budget, a wrong abstraction, a repeated fact, a fat entry point, or a hygiene pattern repeated across the codebase.
   - **Low:** isolated naming or hygiene issues.

7. **Drift profile.** Rate each chapter (ARCH, OOP, NAME, CPLX, ERR, XCUT, DATA, API, UI, SEC, TEST, HYG) as aligned, partial or drifted, with one reason each. Then name the overall drift profile from the playbook: sound architecture with uneven hygiene, partial drift, or heavy drift.

8. **Write** `docs/refactor/AUDIT.md` using the layout in ARTIFACTS.md. Create the folder if needed.

9. **Report** in chat: the drift profile and chapter table, the critical and high findings (at most 10), the metrics headline, and the next command (`/standards:blueprint`). If the architecture is already aligned, say the blueprint will be short.

## Rules

- Read-only, except `docs/refactor/AUDIT.md` and `docs/refactor/metrics/`.
- Every finding cites `path:line`. Prefer evidence over opinion.
- Repeated structure is not a finding (CPLX-05, CPLX-06). Repeated facts and copy-paste slips are.
- Report counts and top locations, not exhaustive lists.
