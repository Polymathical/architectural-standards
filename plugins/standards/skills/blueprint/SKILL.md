---
name: blueprint
description: Design the target architecture for this codebase from the audit, mapping today's components onto layers, modules and roles, and write docs/refactor/BLUEPRINT.md.
disable-model-invocation: true
allowed-tools: Read Grep Glob
---

# Blueprint

Decide where this codebase is going and write `docs/refactor/BLUEPRINT.md`. The destination is the target architecture in `${CLAUDE_PLUGIN_ROOT}/references/LESSONS.md` (section "Target architecture"): a modular monolith with layered modules and thin hosts. Adapt it to this codebase and language; don't invent a different architecture.

## Inputs

- `docs/refactor/AUDIT.md`. If it doesn't exist, stop and suggest `/standards:audit`.
- Lessons ARCH, OOP, NAME, DATA, API, XCUT and SEC.
- Layout: `${CLAUDE_PLUGIN_ROOT}/references/ARTIFACTS.md`, section "BLUEPRINT.md".

## Procedure

1. **Proportion.** Read the audit's drift profile. If ARCH, DATA and API are rated aligned, write a short blueprint that confirms the current module structure as the target and lists only the corrections needed. Then skip to step 8.
2. **Product name and prefix.** Determine the product name for module names (NAME-04). If it's unclear, ask.
3. **Modules.** Define the target modules by layer: foundation, data, persistence, services (business rules by aggregate group, one adapter module per external system, one module per cross-cutting concern), contracts (if an API has clients) and hosts. Name each one per NAME-04 and the language's package conventions (NAME-18). For each, give its responsibility, its allowed dependencies and its status (exists, create, rename, split or merge).
4. **Hosts and composition roots.** For each host in the audit, record where its composition root lives. Use the language's standard dependency-injection mechanism; where there is none, use a hand-written composition function. Don't introduce a heavy framework where a function will do (CPLX-07).
5. **Context and configuration.** If code depends on a current user, tenant or request, define the context interface's members and the implementation per host (ARCH-05). Define the typed settings per section, the source precedence, and where secrets live (ARCH-07, SEC-06).
6. **Component map.** For every static collection, oversized type, data-access cluster, fat entry point and external system in the audit, map the current unit to its target types, roles, modules and recipes (R02, R04, R05, R06, R07, R08, R14). One current unit may map to several targets.
7. **Conventions.** Decide errors and results (ERR-01, ERR-02), logging (XCUT-01), the asynchronous rules (CPLX-09), the single caching mechanism (XCUT-03), and the testing frameworks and naming (TEST). Cite the lesson for each.
8. **Decisions.** List the decisions that belong to the user, such as the product name, module boundaries, splitting deployables, or contract changes. Ask the ones that block planning with AskUserQuestion, and record the rest as open questions with owners.
9. **Write** `docs/refactor/BLUEPRINT.md`. Summarize it in chat and suggest `/standards:plan`.

## Rules

- Keep the target a modular monolith unless the user asks otherwise.
- Every abstraction in the blueprint must pay rent (CPLX-07): put interfaces at I/O seams and module boundaries, not everywhere.
- Don't plan new shared base types or generic frameworks to merge repeated structure (CPLX-06, MIG-15).
- Write only `docs/refactor/BLUEPRINT.md`.
