---
name: lessons
description: Engineering lessons for layered, modular, low-complexity code. Use when designing, writing, reviewing or refactoring code, or when asked whether code follows the engineering standards.
when_to_use: Adding a module, service, repository, adapter, endpoint or UI component; a function passing 30 lines or 4 parameters; deciding whether to extract an abstraction or remove duplication; naming projects, folders, types or methods; looking up a lesson ID such as CPLX-05.
argument-hint: "[lesson-id]"
---

# Engineering lessons

The full lessons are in `${CLAUDE_PLUGIN_ROOT}/references/LESSONS.md`. Read only what you need: search the file for a lesson ID (such as `CPLX-05`) or a chapter heading, rather than loading it all.

If a lesson ID was given (`$ARGUMENTS`), quote that lesson and explain how it applies to the code at hand.

## Apply these whenever you write or change code

1. Dependencies point one way, from hosts to services to persistence to data to foundation (ARCH-01).
2. Each module registers its own services; a host's entry point is a list of module installers (ARCH-03).
3. No business logic in hosts, endpoints or pages; they declare and delegate (ARCH-04, API-01, UI-07).
4. The current user, tenant or request comes through a context interface, never from statics or request globals (ARCH-05).
5. Anything that does I/O sits behind an interface and arrives through the constructor (OOP-09).
6. One reason to change per type, and a role suffix in its name (OOP-05, NAME-08).
7. Budget: functions at most 30 lines, 4 parameters and 3 levels of nesting; types at most 300 lines and 5 constructor dependencies; interfaces at most 10 members (CPLX-01).
8. Repeat structure freely, but keep every fact in one place (CPLX-05). Don't extract an abstraction until three copies change for the same reason (CPLX-06, CPLX-07). Re-read every line you copy (CPLX-08).
9. Await straight through: no blocking waits, fire-and-forget calls or unawaitable asynchronous functions (CPLX-09).
10. Never swallow an error; log the error object with a constant message template (ERR-03, XCUT-01).
11. Tokens, retries and caching live in pipelines and decorators, not business code (XCUT-02).
12. One repository per aggregate, with explicit queries, one unit of work per call, and the acting user passed in (DATA-01, DATA-02).
13. One adapter method per remote operation, with vendor types translated at the boundary (API-03, API-04).
14. Authorize where state changes; no hard-coded identities or secrets (SEC-04, SEC-05, SEC-06).
15. Tests are named method, scenario and expected result, are isolated, and come before refactoring (TEST-02, TEST-03, MIG-01).

## When changing existing code

- Keep structure changes and behavior changes in separate steps (MIG-02), and keep each step small and reversible (MIG-13).
- Don't introduce new abstractions to merge similar code while refactoring (MIG-15).
- For planned, multi-step work, use the commands: `/standards:audit`, `/standards:blueprint`, `/standards:plan`, `/standards:refactor`. For one lesson across a codebase, use `/standards:fix`. Recipes are in `${CLAUDE_PLUGIN_ROOT}/references/REFACTORING-PLAYBOOK.md`.

## When explaining or reviewing

Cite lesson IDs. Never report repeated structure as a defect; report repeated facts, abstractions that don't pay rent, and copy-paste slips.
