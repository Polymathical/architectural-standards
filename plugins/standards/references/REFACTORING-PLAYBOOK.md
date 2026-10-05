# Refactoring Playbook

How to move an existing codebase toward the lessons in `LESSONS.md`. The playbook covers triage by drift, five step types, ordered stages and fourteen recipes. Like the lessons, it contains no code: each recipe describes moves that any language's tooling can make.

## 1. Principles

- **Proportion.** Most codebases have sound bones and uneven hygiene. They need targeted fixes and sweeps, not a migration. Structural recipes are used only where the audit shows structural drift.
- **Safety first.** No unit changes without tests that pin its behavior (MIG-01).
- **One kind of change per step.** Structure and behavior never change in the same step (MIG-02). Every step is small, builds, passes the tests and can be reverted on its own (MIG-13).
- **Incremental replacement.** New structure grows beside the old, and callers move over one at a time (MIG-03).
- **Ratchet.** Budget-violation counts never rise after the baseline (MIG-14).
- **No new abstractions to merge similar code.** Single-source facts, and leave repeated structure alone (MIG-15, CPLX-05, CPLX-06).
- **Contracts are preserved** unless a dedicated step versions them (MIG-16).

## 2. Triage by drift

The audit rates each lesson chapter as aligned, partial or drifted. The plan uses only what those ratings call for.

| Drift profile | Typical signs | The plan contains |
|---|---|---|
| Sound architecture, uneven hygiene (most common) | Layers and modules exist and dependency injection is used; findings concentrate in complexity, errors, logging, naming, UI and hygiene | Safety net for the areas touched, critical fixes, single-sourcing of facts, hygiene sweeps, targeted splits of oversized types and pages, naming consistency, ratchet |
| Partial drift | Some business logic in hosts, scattered data access, inline remote calls, a few statics doing I/O | All of the above, plus boundary corrections where the drift is (R14, R07, R08, R02 for the few statics) |
| Heavy drift | Statics and global state throughout, no composition root, long parameter lists, no layering | A staged migration (composition roots, seams, parameter decomposition, target modules), followed by everything above |

## 3. Step types

- **Safety:** characterization tests, the metrics baseline, analyzers in report-only mode. Never changes production code.
- **Fix:** a deliberate behavior change for a correctness or security finding. Always its own step, confirmed by the user before it runs, with a test that pins the corrected behavior.
- **Refactor:** one recipe applied to one unit. Behavior-preserving.
- **Sweep:** one mechanical, behavior-preserving change applied across many files, such as converting log messages to constant templates, fixing asynchronous naming, adopting one namespace form or removing unused imports. Runs one chunk (a module or folder) at a time, and each chunk is built and tested.
- **Tooling:** formatter and analyzer configuration, the continuous-integration ratchet, boundary enforcement.

## 4. Stages

Use only the stages that address findings. Within a stage, order steps by severity, then by value.

| Stage | Purpose | Exit criteria |
|---|---|---|
| S0 Orient | Record the build, test and metrics commands, the hosts and the entry points; create the refactor folder | Commands verified |
| S1 Safety net and tooling | Metrics baseline; analyzers in report-only mode; characterization tests for every unit an early step touches (R01) | Green build and tests; baseline recorded |
| S2 Critical fixes | Security and correctness findings, as fix steps approved one by one | No critical findings open |
| S3 Facts in one place | Configuration keys, addresses, identifiers, codes, labels and identities moved into typed settings, constant holders or lookup tables (R09) | No repeated facts left from the audit |
| S4 Composition and seams | Partial or heavy drift only: a composition root per host (R03), statics to instances (R02), hidden state to explicit dependencies (R04) | Business code receives its collaborators by injection |
| S5 Boundaries | Thin entry points (R14), data access per aggregate (R07), an adapter per external system with pipeline concerns (R08), modules and dependency direction (R10) | No layering violations; endpoints and pages only delegate |
| S6 Size and shape | Long parameter lists (R05), oversized types, interfaces and pages (R06), wrong abstractions (R13) | Within the budget, or deviations documented |
| S7 Hygiene sweeps | Asynchronous, error and logging hygiene (R11); unused code, commented-out code, regions, untracked TODOs | Counts at zero, or ratcheted |
| S8 Naming and consistency | Rename sweeps (R12), one namespace form, file and type names, style configuration | Naming findings closed |
| S9 Ratchet and cleanup | Delete temporary facades and shims, promote analyzer rules to errors, enforce in continuous integration | Rules enforced |

**Common path (sound architecture, uneven hygiene):** S0, S1, S2, S3, S7, S6, S8, S9, adding S5 steps only where entry points or data access drifted.

**Heavy-drift path:** S0, S1 (with characterization at the outermost entry points), S3, S4, S6 (parameter lists shrink as types become instances), S5, S7, S8, S9.

## 5. Recipes

### R01: Characterize behavior

**When:** before the first change to a unit that lacks adequate tests.

1. Choose the seam: the narrowest boundary that exercises the unit's observable behavior (a public function, endpoint, command, job or message handler).
2. Make the environment deterministic. Substitute the clock, randomness and identifier generation; use an isolated data store; replace remote systems with recorded or stubbed responses.
3. Record actual outputs and side effects for representative inputs, including edge cases and error paths, without correcting them.
4. Name tests by method, scenario and current result. Mark suspected bugs as current behavior, with a note, and record a finding for a later fix step.
5. Run the tests twice to confirm they are deterministic.

**Done when:** the behavior that the next steps touch is pinned and green.
**Pitfalls:** pinning implementation details the refactor must change; unstable outputs such as timestamps, ordering or generated identifiers; mocking the unit under test.

### R02: Static to instance behind an interface

**When:** a static or module-level collection of functions performs I/O, holds state or blocks testing.

1. List its public members and their callers. If the members serve several responsibilities, split them first, or convert one responsibility at a time (R06).
2. Define an interface with the members the callers use, named for the role.
3. Create an instance type that implements it and move each member's body over unchanged. Collaborators that are already instances arrive through the constructor; remaining static collaborators stay as static calls for now.
4. Turn the static members into one-line delegations to a default instance, so existing callers keep compiling and behaving the same.
5. Register the instance type in the composition root (R03).
6. Move callers to the injected interface one at a time, or one module at a time, running the tests after each batch.
7. Delete the static facade when it has no callers, as a cleanup step.

**Done when:** no caller reaches the static, the interface is injected, and the tests pass.
**Pitfalls:** moving shared mutable state into the instance without deciding who really owns it (do R04 first); changing initialization order or thread safety; one interface per function; merging unrelated statics into one interface.

### R03: Establish a composition root

**When:** a host creates objects directly or reaches for statics, or registrations are scattered.

1. Make each host's entry point its composition root.
2. Use the platform's dependency container if there is one. Otherwise, write a composition function that builds the object graph by hand.
3. Register the existing types, including the default instances behind temporary static facades.
4. Turn on container validation and settings validation (ARCH-08).
5. Resolve the host's top-level handlers, controllers, pages or jobs from the root.
6. Move registrations into one installer per module (ARCH-03).

**Done when:** each host builds its object graph in one place and starts with validation on.
**Pitfalls:** a second container built during configuration; service location spreading from the root into business code; longer-lived objects capturing shorter-lived dependencies.

### R04: Hidden state to explicit dependency

**When:** there is global or static mutable state, ambient lookups, direct clock or random calls, or shared connections.

1. Inventory each piece of state and classify it as configuration, context, cache, time or randomness or identifiers, connection or session, or registry.
2. Create the matching abstraction: typed settings; a context interface with one implementation per host; a cache abstraction with tenant-scoped keys; clock and identifier providers; a unit-of-work factory; an owning service for a registry.
3. Replace reads and writes one consumer at a time, keeping the global as a delegating shim until the last consumer has moved.
4. Remove the global.

**Done when:** no consumer reads the global, and behavior is unchanged.
**Pitfalls:** hidden initialization order; concurrency; tenant data leaking through shared caches.

### R05: Decompose a long parameter list

**When:** a function has more than four parameters, flags that select behavior, or parameters passed unchanged through several layers.

1. Classify every parameter as a collaborator, context, configuration, data or a mode.
2. Collaborators become constructor dependencies of the owning type. If the owner is static, convert it first (R02).
3. Context comes from the context interface, or as a context value passed only at the host boundary.
4. Configuration becomes typed settings injected into the owner.
5. Data that travels together becomes one parameter object named for the operation. Pass whole objects instead of their fields.
6. Each mode flag becomes its own function with an intention-revealing name; the old function delegates to them until its callers move.
7. While many callers remain, keep an overload with the old signature that delegates to the new one, and delete it in cleanup.

**Done when:** four or fewer parameters, no mode flags and no pass-through parameters remain.
**Pitfalls:** one giant parameter bag that only moves the problem; changed default values; output parameters, which should become return values.

### R06: Split an oversized type

**When:** a type, interface, page or file exceeds the budget or has several reasons to change.

1. Cluster the members by the data and collaborators they use, and by the nouns in their names.
2. Pick one cluster and name its target type by role (NAME-08), in the right module.
3. Move the cluster and let the original delegate to the new type. Then move the callers, then remove the delegation.
4. Repeat, one cluster per step, until the type fits the budget. Split interfaces by aggregate or use case. Split pages by extracting one section component that owns its data.

**Done when:** each resulting type has one reason to change and fits the budget.
**Pitfalls:** a "helper" that takes the same dependencies is not a split; numbered parts; circular references between the parts.

### R07: Consolidate data access into a repository

**When:** the queries or connections for an aggregate are scattered across services, UI or statics.

1. Identify the aggregate and every place that reads or writes its data.
2. Create the repository interface and implementation in the persistence module, with one explicit method per distinct query or write and one unit of work per call.
3. Have the owning service pass in the acting user and tenant as parameters.
4. Move callers to the service and delete the scattered data access.

**Done when:** only the repository touches that aggregate's storage.
**Pitfalls:** building a generic repository; changing transaction boundaries; changing query semantics such as ordering, filtering or null handling.

### R08: Wrap an external system in an adapter

**When:** a remote API or SDK is called inline, from several places, or with inline authentication and retries.

1. Inventory the system's call sites and operations.
2. Create an adapter module with a typed client: one function per remote operation, with vendor types translated at the boundary and kept internal.
3. Move authentication, retries, timeouts and rate limits into the client pipeline, and addresses and scopes into settings.
4. Move callers to the adapter and delete the inline calls.

**Done when:** no code outside the adapter references the vendor's types or addresses.
**Pitfalls:** one adapter covering several systems; clients created per call; vendor types leaking through signatures.

### R09: Single-source a fact

**When:** the same literal or rule appears in more than one place.

1. Find every occurrence, including tests, configuration files and scripts.
2. Choose its home: typed settings for a value that varies by environment, a constant holder for a fixed fact, a lookup table for a mapping, or the owning type for a business rule.
3. Replace each occurrence with a reference to the home.

**Done when:** the fact appears once.
**Pitfalls:** merging values that are equal by coincidence but mean different things; moving secrets into constants instead of the secret store.

### R10: Move code into a target module

**When:** code sits in the wrong layer or module, or its target module doesn't exist yet.

1. Create the module if it is missing, named per NAME-04 and referencing only lower layers.
2. Move one cohesive unit together with its tests, adjusting namespaces or packages to the new folder.
3. Build. Fix any accidental upward reference by putting the interface in the lower layer and the implementation above it.
4. Enable boundary enforcement through references or architecture tests.

**Done when:** the unit builds in its new home and the boundary is enforced.
**Pitfalls:** moving and changing code in the same step; leaving forwarding types behind without a cleanup step.

### R11: Fix asynchronous, error and logging hygiene

**When:** there are blocking waits, unobserved asynchronous calls, nested continuations, asynchronous functions without an awaitable result, swallowed errors, generic error types, interpolated log messages or misplaced logger categories.

- **Asynchronous:** await all the way up the call chain, observe every asynchronous call, and run independent calls concurrently. Convert functions with no awaitable result to awaitable ones, except framework event handlers that catch every error.
- **Errors:** replace empty or swallowing catches with logging of the error object plus handling, translation or rethrow. Replace generic error types with precise ones.
- **Logging:** convert messages to constant templates with named placeholders, set each logger's category to its owning type, and remove secrets from logs.

**Done when:** the related counts in the scope are zero.
**Pitfalls:** when an error that used to be swallowed now propagates and callers relied on the silence, that is a behavior change: make it a fix step. Partial conversion of blocking code can cause deadlocks.

### R12: Rename mechanically

**When:** names break the naming lessons and the structure is stable.

1. Use the language's refactoring tooling, not text replacement.
2. Rename one concept per step: a type and its file, one verb family, or one convention such as the asynchronous marker.
3. Keep public contracts stable. Where a public name must change, add a compatibility alias and schedule a cleanup step.

**Done when:** the convention holds in the scope and the build is green.

### R13: Inline a wrong abstraction

**When:** a shared abstraction has grown flags, modes or optional parameters to serve callers that diverged, or it doesn't pay rent (CPLX-07).

1. For each caller, copy the abstraction's body into the caller, or into a caller-specific type, specialized for that caller's arguments.
2. Delete the branches that this caller never takes.
3. Delete the abstraction once nothing uses it.

**Done when:** each caller reads top to bottom without mode switches.
**Pitfalls:** re-abstracting straight away; losing a shared fact (single-source it with R09 instead).

### R14: Thin an entry point

**When:** an endpoint, page, handler or main function contains business logic, queries or remote calls.

1. Identify the logic and the module where it belongs.
2. Move it into a service method, existing or new, named by role.
3. Leave the entry point declaring its contract and delegating in one statement. For pages, keep the orchestration and move computation into services or view models.

**Done when:** the entry point only declares and delegates.

## 6. Sweep procedure

1. Define the mechanical change and its detection signal precisely, citing the lesson.
2. Take one chunk: one module or folder.
3. Apply the change to every occurrence in the chunk and nothing else.
4. Build and test, then record the chunk.
5. Repeat until the count is zero, then plan the analyzer rule that keeps it there (S9).

## 7. Sizing and ordering

- A step is one step type, applied as one recipe or mechanical change, to one unit or one chunk.
- Keep each diff reviewable: aim for under about 400 changed lines, not counting mechanical moves and renames.
- Order by prerequisites, then severity (critical first), then risk reduction (safety, facts), then value (callers times I/O or state times change frequency), then effort (quick wins earlier within a stage).
- Characterization (R01) comes before the first refactor or fix step that touches a unit.

## 8. Verification protocol

Run this for every step:

1. Build.
2. Run the tests: the affected ones first, then the full suite before marking the step done.
3. Run metrics on the changed files. No budget-violation count may rise above the baseline.
4. Review the diff against the lessons, as the review command does.
5. Check behavior. Refactor and sweep steps change none; fix steps change only the targeted behavior.

## 9. When to stop and ask

- Before any fix step, because it changes behavior.
- Before any change to a public contract: an API, schema, file format or configuration key.
- When no practical safety net is possible, such as side effects that can't be sandboxed.
- When the blueprint doesn't cover the case, or a module boundary or product decision is needed.
- When a step grows beyond its scope. Split it and stop.
- When tests fail repeatedly for reasons the step doesn't explain.

## 10. Temporary scaffolding

Static facades that delegate to instances, overloads that keep old signatures, compatibility aliases and delegating shims are allowed during migration. Record each one in the plan, together with the cleanup step in S9 that removes it.
