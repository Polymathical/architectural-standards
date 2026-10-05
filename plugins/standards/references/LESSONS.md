# Engineering Lessons

Language-neutral lessons for building software, and for refactoring software toward, a layered, modular, low-complexity architecture. The lessons contain no code and no examples on purpose: each one states a principle, why it matters, how to detect a violation, and how to remedy it.

## How to use these lessons

- Every lesson has a stable ID (for example `CPLX-05`). Cite IDs in audits, plans, reviews and commit messages.
- Levels: **MUST** applies to all new code and is the target for refactored code. **SHOULD** is the default; a deviation needs a written reason. **MAY** is a recommended option.
- **Detect** lists signals an auditor can search for. **Remedy** points to a recipe (R01 to R14) in the refactoring playbook, or to another lesson.
- Chapters ARCH to HYG describe the destination. The MIG chapter describes how to get there safely, in proportion to how far a codebase has drifted: most codebases need targeted fixes and sweeps, and only a few need structural migration.
- When lessons seem to conflict, choose the option that keeps the code simpler and more explicit (values V1 and V2).

## Values

- **V1. Simple over clever.** The best code is code a new teammate can read once, top to bottom, and change safely. Fewer moving parts beat elegant ones.
- **V2. Explicit over magic.** Prefer what a reader can see and step through over behavior conjured by reflection, conventions or attributes, unless the mechanism is a well-known framework feature used the same way everywhere.
- **V3. Boundaries before code.** Decide where a responsibility lives (layer, module, type) before writing it. Most refactoring is boundary correction.
- **V4. Fail fast, fail loud.** Misconfiguration and broken invariants stop the program at startup or at the call that broke them, instead of surfacing later as a null somewhere else.
- **V5. Consistency over preference.** One way to do each thing per codebase. A slightly worse convention applied everywhere beats a better one applied half the time.
- **V6. Repetition over the wrong abstraction.** Sometimes it is cleaner to repeat yourself than to abstract. Repeat structure freely when each copy reads well on its own; never repeat facts.

## Target architecture

The destination is a modular monolith: one codebase, several thin hosts, and modules arranged in layers. It is not a microservice architecture and does not require a framework.

| Layer | Owns | Never |
|---|---|---|
| Foundation | framework-free primitives: enumerations, constants, result types, small extension functions | references a UI, web or persistence framework |
| Data | entities, audit base types, schema configuration, migrations | contains business rules or calls services |
| Persistence | one repository per aggregate; queries and writes; one unit of work per call | resolves the current user, tenant or request |
| Services | business rules (one service per aggregate or use-case group), integrations (one adapter module per external system), cross-cutting modules (security, caching, telemetry defaults) | knows which host it runs in |
| Contracts | request and response types shared by an API and its clients | contains behavior |
| Hosts | composition root and framework glue: web UI, API, workers and command-line tools, migration runner, local orchestration | contains business rules |

- Dependencies point toward the foundation. Requests flow down.
- Context (who the code acts for: user, tenant, request) is resolved at the top and passed down as explicit identifiers, or read through one context interface.
- Cross-cutting concerns (authentication tokens, retries, caching, logging, telemetry) wrap the flow in pipelines and decorators. They don't live inside business code.
- Outbound calls go through typed clients whose pipelines add authentication and resilience.
- Every host builds its object graph in one composition root by calling one installer per module.

---

## ARCH: Architecture and modularity

### ARCH-01: Layers depend one way

**MUST.** Organize code into the layers of the target architecture. A layer depends only on layers below it, and the foundation references no UI, web or persistence framework.

- **Why:** Changes stay local. A framework type in the foundation spreads that framework into everything.
- **Detect:** References from a lower layer to a higher one; cycles between modules; foundation modules importing UI, web or data-access libraries.
- **Remedy:** R10. Enforce direction with module or package references so a violation fails the build.

### ARCH-02: One module per capability

**SHOULD.** Each business capability, external integration and cross-cutting concern lives in its own module, which exposes its interfaces, its models and one registration entry point.

- **Why:** Clear ownership, a short dependency list, and reuse by any host.
- **Detect:** Catch-all modules (shared, utilities, common, helpers) whose dependency list keeps growing; one module mixing unrelated integrations.
- **Remedy:** R10 for capabilities, R08 for integrations.

### ARCH-03: Modules register themselves; the entry point is a list

**MUST.** Each module provides one installer that registers everything it owns, including the modules it depends on. A host's entry point reads as a list of installers.

- **Why:** Wiring knowledge lives next to the code it wires. Adding a host or removing a module is one line.
- **Detect:** Startup code registering individual types from many modules; one module registering another module's types; no registration at all because objects are created directly or reached through statics.
- **Remedy:** R03, then move registrations into per-module installers.

### ARCH-04: Hosts are thin shells

**MUST.** A host (web UI, API, worker, command-line tool, migration runner) contains only composition, framework glue and host-specific adapters. Business behavior lives in modules.

- **Why:** The same module running unchanged in two hosts is the cheapest proof that boundaries are right.
- **Detect:** Business rules, queries, calculations or remote calls inside entry points, controllers, handlers, pages or main functions.
- **Remedy:** R14.

### ARCH-05: Ambient context goes behind an interface

**MUST.** Whatever tells a module who it acts for (current user, home tenant, active tenant, request) reaches it only through an interface with one implementation per host. Modules never read request, session, thread-local or global state directly.

- **Why:** The same module can then run in a request, a background job and a test, and tenant rules are enforced in one place.
- **Detect:** Static or global holders of the current user, tenant or request; request or session state read deep inside services; the same lookup implemented in several places.
- **Remedy:** R04, using a context interface implemented per host.

### ARCH-06: Share contracts, not implementations

**SHOULD.** When one application calls another, put the request and response types in a contracts module that both reference, and provide a typed client with one method per endpoint.

- **Why:** The compiler keeps server and client in sync, and callers never hand-build addresses or payloads.
- **Detect:** The same transfer types defined on both sides; addresses and payloads assembled by hand in callers.
- **Remedy:** Create the contracts module; route callers through the typed client (R08).

### ARCH-07: Layered configuration, typed settings, no secrets in source

**MUST.** Configuration loads from layered sources in a documented order: defaults, environment-specific values, a secret store, environment variables, then developer-local overrides that are excluded from version control. Each section binds to one typed settings object that declares its section name once.

- **Why:** Every value has one known origin, secrets stay out of the repository, and a renamed key breaks in one place.
- **Detect:** Configuration keys read as strings in many places; environment variables read deep inside logic; secrets, connection strings or tokens in source; constants that differ per environment.
- **Remedy:** R09 into typed settings; move secrets to the secret store.

### ARCH-08: Validate wiring and configuration at startup

**MUST.** Turn on dependency-container validation and validate required settings at startup. A missing value stops startup with a message that names the key.

- **Why:** Configuration bugs surface at deploy time instead of at the first production request.
- **Detect:** Defaults that silently replace missing secrets; configuration errors discovered only at run time; lazily created singletons that fail on first use.
- **Remedy:** Add startup validation for every typed settings object and enable container verification.

### ARCH-09: Local infrastructure as code; migrations as their own step

**SHOULD.** Declare local dependencies (database, cache, emulators) in code so that one command starts the whole system. Run schema migrations as a dedicated one-shot step that applications wait for, never as a side effect of application startup.

- **Why:** Fast onboarding, ordered and observable schema changes, and no migration races between instances.
- **Detect:** Manual setup instructions; applications migrating the schema at startup; schema changes applied by hand.
- **Remedy:** Add an orchestration or compose definition; move migrations into a migration step.

### ARCH-10: Long-running work is a job

**SHOULD.** An operation that can outlast a request starts a job and returns its identifier at once. Clients poll or subscribe for status.

- **Why:** Requests stay fast and safe to retry, progress is observable, and timeouts stop being business logic.
- **Detect:** Requests held open for minutes; timeouts raised repeatedly; batch processing inside request handlers.
- **Remedy:** Introduce a job model (start, identifier, status) and move the work to a background worker.

---

## OOP: Object-oriented design

### OOP-01: Abstraction: speak your own domain at the boundary

**MUST.** Translate vendor and framework concepts into your own vocabulary where they enter the system, in an anti-corruption layer.

- **Why:** A vendor change touches one adapter instead of every rule that inspected the vendor's fields.
- **Detect:** Vendor or SDK types in service signatures, UI or persistence; vendor field names or codes inside business rules.
- **Remedy:** R08, with small translation functions and lookup tables at the boundary.

### OOP-02: Encapsulation: expose the minimum

**MUST.** State is private by default. Expose behavior and read-only views; set identity once; make shared constants and collections immutable.

- **Why:** Every public mutable member is a place where an invariant can break.
- **Detect:** Public mutable fields; publicly settable identity; mutable public static collections; internal collections returned for callers to modify.
- **Remedy:** Make fields private, expose read-only views, and make shared collections immutable.

### OOP-03: Inheritance: shared shape only, at most two levels

**SHOULD.** Use inheritance for genuinely shared data shape or framework hooks. Keep hierarchies at most two levels deep below the framework type. A base type never knows its subclasses.

- **Why:** Deep hierarchies hide behavior where readers don't look, and a base type that references its subclasses can't be extended without editing it.
- **Detect:** Inheritance deeper than two levels; base types with members or branches for specific subclasses; inheritance used only to share utility functions.
- **Remedy:** Replace with composition (OOP-10); move subclass-specific members down.

### OOP-04: Polymorphism: replace repeated conditionals

**SHOULD.** When the same branching on a type, kind or name appears in several places, or grows with every feature, replace it with one strategy per case chosen once at composition time, or with one lookup table.

- **Why:** Adding a case means adding a type or a row, not hunting down every branch.
- **Detect:** The same switch or if-chain over a kind, name or string literal in more than one place.
- **Remedy:** Introduce a strategy interface or a single lookup table (CPLX-04). A single mapping expression is fine as it is.

### OOP-05: Single responsibility

**MUST.** A type has one reason to change. Repositories change with storage, services with business rules, adapters with their remote API, endpoints with their contract, UI components with their part of the screen.

- **Why:** Mixed responsibilities couple unrelated changes and let types grow without limit.
- **Detect:** Types over budget (CPLX-01); one type touching storage, remote systems and presentation; interfaces that serve several aggregates.
- **Remedy:** R06.

### OOP-06: Open/closed: extend by wrapping

**SHOULD.** Add cross-cutting behavior (caching, retries, authentication, logging) by wrapping stable code with decorators, pipeline handlers or middleware. Don't edit the wrapped code to add it.

- **Why:** Core code stays simple, and each concern can be added, removed or swapped on its own.
- **Detect:** Caching, retry, authentication or feature-flag code interleaved with business logic across many functions.
- **Remedy:** Move the concern into a decorator or pipeline handler (XCUT-02).

### OOP-07: Liskov substitution: every implementation honors the whole contract

**MUST.** Every implementation of an interface, whether production, per-host or a test double, honors its documented behavior, including side effects and events.

- **Why:** Substitutability is what makes per-host implementations safe.
- **Detect:** Implementations that throw "not implemented"; implementations that skip events or side effects that others perform.
- **Remedy:** Complete the implementation, or split the interface (OOP-08).

### OOP-08: Interface segregation: role-sized interfaces

**SHOULD.** Keep each interface to one role or aggregate, with at most ten members.

- **Why:** Consumers depend only on what they use, and implementations and test doubles stay small.
- **Detect:** Interfaces with more than ten members; consumers that use a small fraction of an interface.
- **Remedy:** Split by aggregate or use case (R06).

### OOP-09: Dependency inversion: abstractions at I/O seams, constructor injection

**MUST.** Business code depends on abstractions for anything that does I/O or varies by host: storage, network calls, caches, the file system, the clock, randomness and the current context. Dependencies arrive through the constructor. Service location is allowed only inside the composition root.

- **Why:** Dependencies become visible and countable, and I/O abstractions are the seams tests use.
- **Detect:** Static calls that perform I/O inside logic; types that construct their own clients or connections; service-locator lookups inside business code; a second dependency container built during configuration to resolve something early.
- **Remedy:** R02 and R04.
- **Limit:** Don't create interfaces for data carriers, value objects or pure functions.

### OOP-10: Composition over inheritance

**SHOULD.** Combine small parts instead of extending large ones: UI components with content slots, services composed of injected collaborators, decorators instead of subclass overrides.

- **Detect:** Subclasses that exist only to override one behavior or reuse helpers.
- **Remedy:** Extract the varying behavior into a collaborator and inject it.

### OOP-11: Law of Demeter

**SHOULD.** Talk to immediate collaborators. Ask the owner for what you need, or project it in the query, instead of navigating long chains through an object graph.

- **Detect:** Chains of three or more member accesses through different objects.
- **Remedy:** Add an intention-revealing member on the owner, or select the needed values in the query.

### OOP-12: Tell, don't ask; separate commands from queries

**MUST.** A query returns data and changes nothing. A command changes state and is named as a command. A function that does both says so in its name (get-or-create).

- **Detect:** Getter-style functions that write, log or call the network; commands with surprising creation side effects.
- **Remedy:** Split the query from the command, or rename the function to state both.

### OOP-13: Least astonishment

**MUST.** Behavior matches the name and the signature. A "get" returns empty for "missing" instead of throwing. A "try" never throws for an expected failure. A "validate" returns true when the input is valid. Optional results are typed as optional.

- **Detect:** Inverted boolean returns; names that contradict behavior; non-optional types that return null.
- **Remedy:** Fix the behavior or the name, with tests pinning the corrected contract (in its own step: MIG-02).

### OOP-14: Immutable data carriers

**SHOULD.** Transfer objects, results, events and value objects are immutable. Mutability is reserved for persisted entities and UI binding models.

- **Detect:** Transfer objects mutated after construction; shared result objects modified by callers.
- **Remedy:** Use the language's immutable record or read-only construct.

### OOP-15: Responsibility assignment (GRASP)

**MAY.** When unsure where a behavior belongs: give it to the type that has the data (information expert); let the holder of the context create things (creator); keep coordinators thin (controller); depend on few, stable abstractions (low coupling); keep related behavior together (high cohesion); vary by type instead of by condition (polymorphism); invent a non-domain type to keep cohesion (pure fabrication); put an intermediary between things that change separately (indirection); wrap likely points of change in stable interfaces (protected variations).

### OOP-16: Patterns in use

**SHOULD.** Prefer these patterns, within their limits:

- **Repository** per aggregate, never a generic one wrapping the data-access library.
- **Unit of work** per operation, never held across calls.
- **Service facade** over repositories and integrations, never a pass-through for everything.
- **Adapter and anti-corruption layer** for every third-party API or SDK.
- **Decorator** for cross-cutting behavior, never to change business results.
- **Chain of responsibility** (pipeline handlers, middleware) for per-request steps, not for business branching.
- **Strategy** when behavior varies by host, tenant or configuration, not when there is one variant.
- **Factory**, including keyed factories, when construction needs runtime context.
- **Fluent builder** for optional configuration, never hiding required inputs.
- **Observer** only when unsubscription is guaranteed.
- **Interceptor** only when no decorator already covers the same concern.
- **Result object** for expected failures at integration edges, never to hide programming errors.
- **Composition root**: exactly one per host.
- **Job and poll** for work that outlives a request.
- **Cache-aside** for data that is read far more than written and tolerates staleness.
- **Allow-list** for explicit access grants.

---

## NAME: Naming

Naming runs top-down, from the repository to a local variable. Casing follows each language's native conventions (NAME-18). The semantic rules apply everywhere.

### NAME-01: General rules

**MUST.** Names reveal intent and role. Use one canonical term per concept across code, UI, storage and documentation. When two concepts are close, name both explicitly: where an identity lives versus whose data is being viewed, an external identifier versus an internal key. Case acronyms as words (two-letter acronyms and language-specific initialism rules excepted). Avoid abbreviations beyond universal ones. Names start with a letter and carry no type information and no temporal markers (new, old, temp, copy, numbered variants). Spell-check public names.

- **Detect:** Abbreviations; numbered or temporal names; mixed acronym casing; synonyms for the same concept; misspellings.
- **Remedy:** R12, after structure stabilizes (MIG-12).

### NAME-02: Repository and solution

**SHOULD.** Repository names are kebab-case product or product-purpose names. There is one solution or workspace per repository, named after the product. Top-level folders are lowercase and named for their purpose (source, documentation, pipelines, tools). Tests live in one predictable place: beside their projects, or in one parallel tree.

### NAME-03: Solution folders

**SHOULD.** Group projects or packages by layer (hosts, contracts, services, data, foundation, and tests mirroring the same groups) so that a project's location is predictable from its name.

- **Detect:** Persistence projects filed under services; test projects split between a tests group and the groups of the projects they test.

### NAME-04: Projects and packages

**MUST.** Name modules `{Product}.{Layer}.{Capability}[.{Qualifier}]`, adapted to the language's package conventions. The folder name, project file, package or assembly name and root namespace are identical. Test projects are named after the project they test plus a unit or integration suffix. Hosts carry the product prefix.

- **Detect:** Folder and project name mismatches; stale duplicate project files; modules named after a technology or a person instead of a capability.
- **Remedy:** R10 and R12.

### NAME-05: Folders inside a module

**SHOULD.** Category folders are plural nouns naming the kind of type they hold: models, extensions, configuration, constants, enumerations, exceptions, handlers, providers, decorators, comparers, controllers. Feature folders are named after a cohesive sub-capability. The child views of one page sit in one folder named after the page. Interfaces sit beside their implementations.

- **Detect:** Separate folders for interfaces and implementations; grab-bag folders (helpers, utilities, miscellaneous, common inside a module); proof-of-concept, old, temporary or backup folders in product trees.

### NAME-06: Namespaces

**MUST.** The namespace or package path equals the module root plus the folder path. Use one declaration form per repository, preferring the least nested one.

### NAME-07: Files

**MUST.** One public type per file, and the file name equals the type name exactly, including case. Companion files (markup and logic, styles, tests) share the type's name with a role suffix. Settings files follow one pattern per environment with canonical casing. Static assets and pipeline files are kebab-case. Migrations are timestamped with a verb-subject description. Scripts follow their language's convention.

- **Detect:** Several public types in one file; file and type names that differ; files that differ only by case.

### NAME-08: Types

**MUST.** A type is a noun or noun phrase whose suffix states its role:

- **Service:** business rules or orchestration, or an integration facade.
- **Repository:** persistence for one aggregate.
- **Client:** a typed client for one remote API.
- **Handler:** one pipeline step, or an authorization handler.
- **Provider:** supplies credentials or state to a framework.
- **Middleware:** request middleware.
- **Extensions:** extension functions, named after the extended type.
- **Settings:** typed configuration declaring its section name. **Options:** an option bag for one component or command.
- **Request, Response, Details:** wire contracts. **Model, Form:** UI view models and input models.
- **Dialog, Skeleton, Card, Icon, Layout:** UI component roles.
- **Exception, EventArgs, Attribute, Requirement, Comparer, Generator.**
- **Worker, Agent:** background processes. **Base:** an abstract base type.

Interfaces follow the language's convention and pair with their implementation's role name. Name alternative implementations by their distinguishing trait, as a prefix (for instance cached, manual, session or non-switching variants), never by "implementation" or "default" alone. Constant holders are plural domain nouns. Enumerations are singular nouns with a classifier suffix (type, status, kind, severity); flag enumerations are plural with an explicit "none"; no "enum" suffix. Generic type parameters are a single letter or a role-prefixed name.

- **Detect:** Helper, utilities, manager, processor, data, info, common or miscellaneous as names or suffixes; types whose suffix doesn't match what they do.
- **Remedy:** R06 when the name hides several responsibilities, otherwise R12.

### NAME-09: Methods and functions

**MUST.** Start with a verb from a shared vocabulary whose contract callers can rely on:

- **get:** returns the item, or empty when missing; no side effects. **get-all:** a collection, never null. **get-latest:** the newest by timestamp. **get-or-create:** announces the write.
- **create:** inserts, failing if the item exists. **save:** upsert. **update:** changes an existing item (choose update or edit per codebase, not both). **delete:** returns the affected count.
- **duplicate, toggle, reset:** named state transitions; toggle only flips.
- **try:** never throws for expected failures. **is, has, can:** boolean queries.
- **to, from:** conversions. **build, generate, calculate:** pure computation. **validate:** true when valid.
- **fetch, set:** UI-only loading and state assignment.
- **add:** registration. **use:** pipeline registration. **with:** fluent configuration. **on, handle:** event handlers.

Selection criteria use "by {key}". Never mix "by" and "for" for the same meaning, and reserve "with" for fluent configuration. Mark asynchronous functions the way the language convention requires.

- **Detect:** Verbs that contradict behavior; several verbs for the same operation; missing or inconsistent asynchronous markers.

### NAME-10: Properties, fields and events

**MUST.** Properties are noun phrases; collections are plural. Booleans read as positive questions (is, has, can, should, show, enable, allow). Relationships are named by role, and the foreign key is the role plus "id". The entity's own key is "id"; references are "{entity} id". Time values state their zone and durations their unit. Private fields follow one convention and are read-only when assigned once. Events are past-tense phrases with matching payload and handler names. UI loading flags follow one pattern.

- **Detect:** Negated booleans; relationship names that repeat the type instead of the role; time values without a zone; mutable fields assigned once.

### NAME-11: Parameters and local variables

**MUST.** Full words named for their role, not their type. Single-letter names only in one-line lambdas. Name the acting user explicitly. Cancellation tokens come last. Pass boolean literals as named arguments. Avoid placeholder names (data, item, object, temp, numbered results) outside tiny scopes.

### NAME-12: Database objects

**SHOULD.** One table-naming convention, singular or plural, never mixed. The primary key is "id" and a foreign key is "{role} id". Use standard audit columns (created and modified timestamps in UTC, plus actors). Keys and indexes use the tool's default names; check constraints are named by table and column. Enumerations are stored as bounded strings.

### NAME-13: Configuration and environments

**MUST.** Section names match their settings type without the "settings" suffix, and keys are cased consistently. Environment variables are upper snake case, with a double underscore for nesting. Connection strings are named after their database. Environment names come from one canonical list and appear verbatim in file names. Don't name settings types "configuration" when the domain also has things called configurations.

### NAME-14: Wire and runtime identifiers

**SHOULD.** Routes are lowercase, hierarchical resource nouns with parameters in braces. Permission scopes are "resource dot action". Authorization policies, keyed-service keys and custom claim types live in constant holders. Named HTTP clients are named after the interface that uses them. Cache keys are colon-separated from most general to most specific and always include the tenant. Log message templates are constant, with consistently cased placeholders. Telemetry source names are constants.

### NAME-15: Styles and static assets

**SHOULD.** CSS classes are kebab-case, prefixed by component, with semantic rather than presentational modifiers. Design tokens are custom properties named by prefix, palette and shade. Script modules are kebab-case with a product prefix. Page routes are the kebab-case form of the page name.

### NAME-16: Branches and commits

**SHOULD.** Branches follow `{type}/{owner}/{workItem}-{kebab-topic}` with a fixed set of types (feature, bugfix, hotfix, chore). There is one integration branch. Commit and pull request titles are imperative and reference the work item.

### NAME-17: Tests

**MUST.** Test projects are named after the project plus a unit or integration suffix. Test classes are named after the class under test plus "tests". Test names state the method, the scenario and the expected result. No generic names.

### NAME-18: Casing per language

**SHOULD.** Follow each language's native casing for packages, files, types, functions, fields, constants, enumeration members and locals. The semantic rules in this chapter don't change. Where a language capitalizes initialisms or discourages interface prefixes, its convention wins over NAME-01 and NAME-08.

---

## CPLX: Complexity budget

### CPLX-01: Stay inside the budget

**MUST.** Every unit of code fits these limits:

| Measure | Aim | Limit |
|---|---|---|
| Function length | 20 lines | 30 lines |
| Cyclomatic complexity per function | 5 | 10 |
| Cognitive complexity per function | 8 | 15 |
| Nesting depth | 2 | 3 |
| Parameters | 3 | 4, then a parameter object |
| Constructor dependencies | 3 | 5 |
| Interface members | 7 | 10 |
| Type or file with behavior | 200 lines | 300 lines |
| Services injected into one UI component | 3 | 5 |

Exceeding a limit means splitting the unit or writing down a deviation. Declarative code (schema maps, route tables, static catalogs) is exempt from length limits while it stays declarative.

- **Detect:** Metrics output; the largest files; long parameter lists; deep nesting.
- **Remedy:** R05 for parameters, R06 for size, CPLX-02 and CPLX-03 for structure.

### CPLX-02: Guard clauses and early returns

**MUST.** Validate inputs first, return early when there is nothing to do, and keep the main path at the left margin.

- **Detect:** Nesting deeper than three; else branches after a return; validation buried inside logic.

### CPLX-03: One level of abstraction per function

**SHOULD.** A coordinating function reads like a table of contents of well-named steps, and the steps hold the detail.

- **Detect:** Functions that mix orchestration with low-level detail such as parsing, formatting or raw I/O.

### CPLX-04: Map with data, not branches

**SHOULD.** Express a mapping as one switch expression or one lookup table, written once.

- **Detect:** If/else ladders that map values; the same mapping written in more than one place.

### CPLX-05: Repeat structure; single-source facts

**MUST.** Code shape may repeat when each copy reads cleanly on its own and could evolve independently. Facts live in exactly one place: configuration keys, identifiers, addresses and scopes, product codes, business labels, thresholds, and key and claim formats. The test: if this changes, must every copy change the same way? If yes, it is a fact and belongs in one place. If no, it is structure, and repetition is fine.

- **Why:** Repeated structure costs a little reading. A repeated fact causes a bug on the day one copy changes and the other doesn't.
- **Detect:** The same literal (address, key, identifier, code, label, threshold) in more than one place.
- **Remedy:** R09. Never report repeated structure as a defect.

### CPLX-06: Prefer duplication over the wrong abstraction

**MUST.** Extract a shared abstraction only when there are at least three real occurrences that change for the same reason. When an abstraction starts growing flags, modes or optional parameters to serve callers that have drifted apart, inline it back into the callers.

- **Why:** Every caller of a wrong abstraction pays for every other caller's special cases, and removing it later is harder than never adding it.
- **Detect:** Mode or boolean parameters that select code paths; base types whose subclasses override most members; type parameters added "for flexibility"; callers working around a shared component.
- **Remedy:** R13.

### CPLX-07: An abstraction must pay rent

**MUST.** Every interface, base type, generic, layer or framework earns its place by removing a real coupling, preventing a real class of bugs, or providing a test seam that tests actually use. Fewer lines alone don't count. Defaults: no generic repository over a data-access library, no mediator between an endpoint and the single service it calls, no interfaces for data carriers, no plug-in system for one plug-in.

- **Detect:** Generic layers that only forward calls; frameworks wrapping a single call path; interfaces on data carriers.
- **Remedy:** R13.

### CPLX-08: Copy deliberately

**MUST.** When you repeat a block, re-read every line of the copy, including routes, entity sets, names, logger categories, keys and messages. Give each copy its own test.

- **Why:** Repetition is cheap. Careless repetition is the real hazard.
- **Detect:** Copies whose identifiers still point at the original's route, entity, category or message.

### CPLX-09: Straight-line asynchronous code

**MUST.** Await from top to bottom and run independent I/O concurrently. Never block on asynchronous work, nest continuation chains, or fire and forget. Asynchronous functions with no awaitable result are allowed only as framework event handlers that catch every error.

- **Detect:** Blocking waits on asynchronous results; asynchronous calls whose result is never observed; nested continuations; asynchronous functions that return nothing awaitable.
- **Remedy:** R11.

### CPLX-10: Parameter objects after four parameters

**SHOULD.** More than four parameters, or parameters that always travel together, become a named type. Boolean arguments are named at the call site.

- **Remedy:** R05.

### CPLX-11: Split by aggregate or role when over budget

**SHOULD.** Split along a seam the domain already has (aggregate, page section, group of remote resources), never into numbered parts or into a helper that shares the same dependencies.

- **Remedy:** R06.

### CPLX-12: Locality of behavior

**SHOULD.** Keep the code that determines a behavior near where that behavior is visible. Prefer a few local lines over a jump to a distant helper.

### CPLX-13: You aren't gonna need it

**MUST.** Build for today's requirement: no speculative extension points, no flags that never have a second value, no unused parameters or dependencies, no commented-out alternatives kept for later.

- **Detect:** Unused parameters, dependencies and extension points; configuration switches with a single value in every environment.

---

## ERR: Errors and resilience

### ERR-01: Exceptions for broken invariants, with precise types

**MUST.** Use precise error types for bad arguments, invalid state and named domain conditions. Never raise the base error type, and never use "not implemented" as the default branch of a closed set.

- **Detect:** Generic error types raised; domain conditions signaled only by message text.

### ERR-02: Expected failures are values at integration edges

**SHOULD.** "Not found", "unavailable" and "rejected" from an external system are normal outcomes. Return them as result values (success, reason, data) or through "try" functions that return empty, visible in the signature, and branch on them explicitly.

- **Detect:** Exceptions used for ordinary outcomes of remote calls; nulls returned without a documented meaning.

### ERR-03: Never swallow an error

**MUST.** Every catch handles the error (logging the error object), translates it, or rethrows it. No empty catches, no silent null returns, and debug output is not error handling.

- **Detect:** Empty catch blocks; catch-all blocks that return a default without logging; logs that keep only the message text.
- **Remedy:** R11.

### ERR-04: Translate errors at the edge

**SHOULD.** Typed domain errors travel up untouched and are translated once at the boundary: an HTTP status, a UI message or redirect, or an exit code.

- **Detect:** The same error converted repeatedly at several layers.

### ERR-05: Resilience belongs to the client pipeline

**MUST.** Retries, timeouts, circuit breakers and rate limits are configured on each client, not hand-written in business code.

- **Detect:** Retry loops and sleeps around remote calls in business logic.
- **Remedy:** R08.

### ERR-06: Cache-aside with safety margins; never cache failures

**SHOULD.** Cache a token until shortly before it expires. Cache only non-empty results. Drop corrupt entries and fetch again. Scope keys by tenant.

---

## XCUT: Cross-cutting concerns

### XCUT-01: Structured logging with constant templates

**MUST.** Log with constant message templates and named placeholders. The logger category is the owning type. Errors are logged with the error object. Never log secrets or whole tokens.

- **Detect:** Interpolated or concatenated log messages; loggers categorized under another type; secrets in logs.
- **Remedy:** R11.

### XCUT-02: Cross-cutting concerns live in pipelines

**MUST.** Business code never acquires tokens, sets authentication headers, retries, or reads and writes caches directly. Pipeline handlers and decorators do that work.

- **Detect:** Token acquisition, header assembly, retries or cache calls inside business functions.
- **Remedy:** R08, or a decorator (OOP-06).

### XCUT-03: One mechanism per concern

**MUST.** Use one caching mechanism, one logging abstraction, one validation library and one HTTP client style, and document each choice. Prefer explicit mechanisms over reflection-based ones.

- **Detect:** Two libraries or styles for the same concern.

### XCUT-04: Telemetry set up once

**SHOULD.** A shared defaults module configures tracing, metrics, logs, health checks and client defaults, and each host calls it once. Expose health endpoints deliberately.

### XCUT-05: Tenancy scopes everything

**MUST.** In a multi-tenant system, every cache key, query, token and log scope includes the tenant. Key builders refuse to work without one, and tenant resolution happens in one place.

- **Detect:** Cache keys or queries without a tenant component; tenant resolved in many places.

---

## DATA: Data and persistence

### DATA-01: One repository per aggregate, explicit queries, no ambient context

**MUST.** Each aggregate root has one repository behind an interface. Each method is one explicit query or write, with no generic create-read-update-delete base. Repositories receive the acting user and tenant as parameters from services, which are their only callers.

- **Detect:** Queries scattered through services, UI or static helpers; generic data-access bases; repositories reading the current user.
- **Remedy:** R07.

### DATA-02: One unit of work per operation

**MUST.** Each repository call opens a short-lived session or context, uses it and disposes of it. Never keep one in a long-lived object, a user session or a static.

- **Detect:** Shared static connections or contexts; contexts stored in long-lived objects.
- **Remedy:** R04 and R07.

### DATA-03: Declarative, central schema

**SHOULD.** Declare keys, lengths, required flags, defaults, constraints and delete behavior in schema configuration, with restricted deletes by default. Per-entity configuration may repeat the same shape; split it per entity once the file is hard to navigate.

### DATA-04: Audit through base types; creators never change

**MUST.** Entities inherit audit fields. Writes set the modified timestamp and actor, and updates preserve the creation timestamp and creator.

### DATA-05: Keep history by appending

**MAY.** Version multi-step, user-authored configuration by appending rows, where "current" is the latest. Pair it with a retention policy.

### DATA-06: Readable storage

**SHOULD.** Store enumerations as bounded strings unless volume demands integers, and times in UTC. Small multi-valued lists may use a delimited or document column with a documented delimiter.

### DATA-07: Migrations are versioned code

**MUST.** Migrations are generated, reviewed, committed and descriptively named, and are applied by the pipeline or the migration step, never by hand on shared environments.

### DATA-08: Null-safety stays on

**MUST.** Keep the language's null analysis enabled in data models, and model optional relationships explicitly. Never disable it per file to silence warnings.

---

## API: APIs and integrations

### API-01: Thin endpoints

**MUST.** An endpoint declares its route, authorization scope and response contract, then delegates in one statement.

- **Detect:** Endpoints that contain queries, loops, calculations or remote calls.
- **Remedy:** R14.

### API-02: Shared contracts and a typed client

**SHOULD.** Clients mirror endpoints one to one and attach authentication through their pipeline (ARCH-06).

### API-03: One adapter method per remote operation

**MUST.** Each adapter method maps to one remote operation. The base address, authentication and resilience come from the client pipeline, so each method is one line.

- **Detect:** Remote calls built inline in business code; adapters that mix several systems; clients created per call.
- **Remedy:** R08.

### API-04: Anti-corruption layer at the boundary

**MUST.** Small translation functions and lookup tables turn vendor fields into domain values. Nothing outside the adapter module references vendor types (OOP-01).

### API-05: Explicit contracts; jobs for long operations

**SHOULD.** Every endpoint declares its response types and status codes. Long operations follow ARCH-10.

### API-06: Endpoints, scopes and base addresses are configuration

**MUST.** No environment-specific hosts, addresses or scopes in code.

- **Remedy:** R09 into typed settings.

---

## UI: User interface components

### UI-01: Separate template from behavior

**SHOULD.** A component's markup and its logic live in separate, matching files, or in the framework's equivalent split.

### UI-02: Design-system components

**SHOULD.** Reusable visual components share one prefix, take inputs as parameters, compose through content slots, and fetch no data.

### UI-03: Progressive, parallel loading with skeletons

**SHOULD.** Each section that loads asynchronously has its own loading flag and skeleton. Independent sections load in parallel and render as soon as their own data arrives.

### UI-04: Dialogs are components that return results

**SHOULD.** A dialog receives parameters and returns a typed result when it closes. It doesn't reach into its opener's state.

### UI-05: Form models aren't entities

**MUST.** Input models carry validation that mirrors the storage limits, and services map them to entities.

### UI-06: Wizards: the parent owns the model, and steps have names

**SHOULD.** The wizard owns the model and passes it to its steps. Each step validates its own inputs. Progress is saved so users can resume. Steps are addressed by name, never by a magic index.

- **Detect:** Step logic keyed by numeric indexes; busy-waiting for the UI to render.

### UI-07: Pages orchestrate; they don't compute

**SHOULD.** A page wires sections together, and calculations live in services or view models. A page injects at most five services; beyond that, add a page-level facade or split the page into sections that own their data.

- **Detect:** Pages with many injected services, long code-behind or calculations.
- **Remedy:** R14 and R06.

### UI-08: Lifecycle hygiene

**MUST.** Unsubscribe from events and dispose of subscriptions. Never busy-wait for rendering; use lifecycle hooks. Asynchronous handlers that return nothing awaitable must catch every error. Load script-interop modules once and dispose of them.

- **Detect:** Subscriptions without matching unsubscription; polling loops with delays; asynchronous handlers without error handling.

### UI-09: Scoped styles and design tokens

**SHOULD.** Component styles live in component-scoped files and use design tokens. Class names follow NAME-15. No style blocks repeated inside markup.

---

## SEC: Security

### SEC-01: Policy-based authorization

**MUST.** Authorization uses named policies built from requirements and handlers. Roles are combinable flags, and policy names live in one constant holder.

- **Detect:** Role checks written inline in business code or UI; policy names repeated as string literals.

### SEC-02: Enrich identity once, at sign-in

**SHOULD.** Map the user to internal roles and claims once, when the token is validated. Everywhere else, query them through typed helpers instead of parsing raw claims again.

### SEC-03: Allow-lists from data or configuration

**SHOULD.** Access by tenant or organization is an allow-list kept in data with a configuration override and checked at sign-in. A rejection is a typed error translated at the edge.

### SEC-04: Authorize where state changes

**MUST.** Every command that changes who can access what checks authorization itself. Filtering a list in the UI is not authorization.

- **Detect:** State-changing operations with no authorization check of their own.

### SEC-05: No hard-coded identities

**MUST.** No email addresses, user identifiers or tenant identifiers in conditionals. Use roles and policies, configured allow-lists, or feature flags.

- **Detect:** Identity literals in conditions.
- **Remedy:** R09.

### SEC-06: Secrets come from a secret store

**MUST.** Secrets come from a vault or secret manager, or from local files excluded from version control. They are never committed and never logged. Token caches in shared infrastructure are encrypted.

- **Detect:** Credentials, keys or connection strings in source or history.

### SEC-07: Authenticated by default

**MUST.** APIs require authentication globally, and an anonymous endpoint is an explicit, reviewed exception. Diagnostic and test endpoints are excluded from production builds or protected like every other endpoint.

- **Detect:** Endpoints with authentication commented out or missing; test endpoints reachable in production.

---

## TEST: Testing

### TEST-01: A test project per module

**SHOULD.** Each module has a unit test project, plus an integration test project where needed, that mirrors its folders. Continuous integration runs every test project.

### TEST-02: Names and shape

**MUST.** Name each test by method, scenario and expected result (NAME-17), and give it arrange, act and assert sections. One behavior per test; group related assertions.

### TEST-03: Isolation

**MUST.** Each test gets fresh state, such as an isolated in-memory store. Tests don't depend on run order or share mutable statics.

### TEST-04: Builders, and mocks only at I/O seams

**SHOULD.** Generate incidental data with builders or fixtures, and auto-mock incidental dependencies. Mock only at I/O seams (OOP-09). Never mock the type under test or a value object.

### TEST-05: Test what breaks

**SHOULD.** In order of priority: business rules in services; repository round trips; boundary translators and mapping tables; each copy of repeated code (CPLX-08); UI logic extracted from components.

---

## HYG: Code hygiene

### HYG-01: No commented-out code or dead branches

**MUST.** Delete it; version control remembers. This includes always-true or always-false branches, unused private functions, and demo or mock data left in production code paths.

### HYG-02: TODOs reference a work item

**SHOULD.** Every TODO carries a work-item reference, or it is removed.

### HYG-03: Remove what is unused

**MUST.** Remove unused imports, parameters, fields and injected dependencies. They mislead readers about what a type depends on.

### HYG-04: One style, enforced by configuration

**MUST.** Formatting and naming are enforced by formatter and analyzer configuration checked into the repository and run in continuous integration, not by review comments.

### HYG-05: Regions don't replace splitting

**SHOULD.** If a type needs folding regions to be navigable, it is over budget (CPLX-01). Split it.

### HYG-06: Names match their owners

**MUST.** File names equal type names. Logger categories, HTTP client names and test class names match the type that owns them.

---

## MIG: Migrating toward the standard

These lessons govern every change that moves existing code toward the standard, whatever the starting point. A codebase with sound architecture and uneven hygiene mostly needs MIG-01, MIG-02, MIG-13, MIG-14 and MIG-15 while it fixes findings and runs sweeps. The structural lessons (MIG-04 to MIG-11) matter in proportion to how far the architecture has drifted. The refactoring playbook turns them into stages, step types and recipes.

### MIG-01: Build a safety net before changing structure

**MUST.** Before changing a unit, make the build green and pin its current observable behavior with characterization tests at the nearest seam: an entry point, a public function or a process boundary. Existing behavior, including bugs, is the specification until a separate step changes it.

- **Why:** Refactoring without tests is rewriting.
- **Detect:** Units scheduled for change with no tests that exercise them.
- **Remedy:** R01.

### MIG-02: Separate structure changes from behavior changes

**MUST.** A refactoring step never changes behavior, and a behavior fix never rides along with a refactoring step. Bugs found during refactoring are recorded and fixed in their own steps.

- **Why:** Reviewers can verify each kind of change, and a regression is attributable to one step.

### MIG-03: Strangle, don't rewrite

**MUST.** Replace a drifted system incrementally behind stable entry points. The new structure grows beside the old, callers move over one at a time, and the old path is deleted when nothing uses it.

- **Why:** The system keeps working and shipping throughout, and the risk of each step stays bounded.
- **Detect:** Plans that need a long-lived rewrite branch or a single cutover.

### MIG-04: Work outside-in from the entry points

**SHOULD.** Establish a composition root in each host first, then push dependencies inward one layer at a time, so each converted unit receives its collaborators from above instead of reaching for statics.

- **Remedy:** R03.

### MIG-05: Turn statics into instances behind interfaces

**MUST.** Convert a static or module-level collection of functions into an instance type behind an interface. Keep a thin static facade delegating to a default instance while callers migrate, inject the interface into callers gradually, and delete the facade when it has no callers. Start with the statics that perform I/O or hold state, then those with the most callers.

- **Why:** Statics hide dependencies, block substitution in tests, and couple every caller to one implementation.
- **Detect:** Static types or module-level function collections that do I/O; mutable static fields; globally reachable singletons.
- **Remedy:** R02.

### MIG-06: Expose hidden state as explicit dependencies

**MUST.** Every piece of global or static mutable state becomes an explicit dependency of the right kind: configuration becomes typed settings; who-and-where becomes the context interface; caches become a cache abstraction; time, randomness and identifier generation become injectable providers; shared connections become per-operation units of work.

- **Detect:** Mutable static fields; global registries; lazily initialized singletons; direct clock, random or identifier calls inside logic.
- **Remedy:** R04.

### MIG-07: Decompose long parameter lists by kind

**MUST.** Sort every parameter of a long list into one of five kinds and move it accordingly:

- **Collaborators** become constructor dependencies.
- **Who-and-where context** comes from the context interface.
- **Configuration** becomes typed settings.
- **Data that travels together** becomes a parameter object named for the operation.
- **Mode and boolean flags** become separate functions.

What remains must fit the budget (CPLX-01).

- **Detect:** Functions with more than four parameters; parameters passed unchanged through several layers; boolean or mode parameters.
- **Remedy:** R05.

### MIG-08: Split god types along reasons to change

**MUST.** Split an oversized type by responsibility (aggregate, role, remote system, screen section), extracting one cohesive group of members per step. The original delegates to the extracted type until its callers have moved.

- **Detect:** Types over budget; many unrelated dependencies; members clustering around different nouns.
- **Remedy:** R06.

### MIG-09: Create the target structure early; move code into it gradually

**SHOULD.** Create the target modules and their dependency rules early, even while they are nearly empty. Move code into them one cohesive unit at a time, and enforce dependency direction as soon as a boundary exists so new violations fail the build.

- **Remedy:** R10.

### MIG-10: Consolidate data access per aggregate

**SHOULD.** Gather the scattered queries and connections for one aggregate into its repository, with a unit of work per operation, and route callers through the owning service.

- **Remedy:** R07.

### MIG-11: Wrap each external system before changing its callers

**SHOULD.** Put each external system behind an adapter with one function per remote operation, translation at the boundary, and authentication and resilience in the client pipeline. Then move the callers to the adapter.

- **Remedy:** R08.

### MIG-12: Rename last, and mechanically

**SHOULD.** Rename after the structure has stabilized, using refactoring tools rather than text replacement, one concept per step, and keeping public contracts stable unless a step explicitly versions them.

- **Remedy:** R12.

### MIG-13: Keep steps small, single-purpose and reversible

**MUST.** Each step addresses one concern, builds, passes every test, and can be reverted on its own. Mechanical moves and renames go in their own steps. A step that grows beyond a reviewable change is split.

### MIG-14: Measure and ratchet

**MUST.** Record baseline metrics and analyzer counts before the first step. After each step, no budget-violation count may increase. Promote each rule to an error once its count reaches zero.

### MIG-15: Don't abstract while migrating

**MUST.** During migration, remove duplicated facts but leave duplicated structure. Don't introduce generic bases, frameworks or shared helpers to merge similar code (CPLX-06). Revisit only after the copies prove that they change together.

### MIG-16: Preserve external contracts

**MUST.** Public APIs, wire formats, database schemas, file formats and configuration keys stay compatible through refactoring steps. When one must change, version it in a dedicated step with a migration path.

---

## Lesson index

125 lessons: 71 MUST, 52 SHOULD, 2 MAY.

| ID | Lesson | Level |
|---|---|---|
| ARCH-01 | Layers depend one way | MUST |
| ARCH-02 | One module per capability | SHOULD |
| ARCH-03 | Modules register themselves; the entry point is a list | MUST |
| ARCH-04 | Hosts are thin shells | MUST |
| ARCH-05 | Ambient context goes behind an interface | MUST |
| ARCH-06 | Share contracts, not implementations | SHOULD |
| ARCH-07 | Layered configuration, typed settings, no secrets in source | MUST |
| ARCH-08 | Validate wiring and configuration at startup | MUST |
| ARCH-09 | Local infrastructure as code; migrations as their own step | SHOULD |
| ARCH-10 | Long-running work is a job | SHOULD |
| OOP-01 | Abstraction: speak your own domain at the boundary | MUST |
| OOP-02 | Encapsulation: expose the minimum | MUST |
| OOP-03 | Inheritance: shared shape only, at most two levels | SHOULD |
| OOP-04 | Polymorphism: replace repeated conditionals | SHOULD |
| OOP-05 | Single responsibility | MUST |
| OOP-06 | Open/closed: extend by wrapping | SHOULD |
| OOP-07 | Liskov substitution: every implementation honors the whole contract | MUST |
| OOP-08 | Interface segregation: role-sized interfaces | SHOULD |
| OOP-09 | Dependency inversion: abstractions at I/O seams, constructor injection | MUST |
| OOP-10 | Composition over inheritance | SHOULD |
| OOP-11 | Law of Demeter | SHOULD |
| OOP-12 | Tell, don't ask; separate commands from queries | MUST |
| OOP-13 | Least astonishment | MUST |
| OOP-14 | Immutable data carriers | SHOULD |
| OOP-15 | Responsibility assignment (GRASP) | MAY |
| OOP-16 | Patterns in use | SHOULD |
| NAME-01 | General rules | MUST |
| NAME-02 | Repository and solution | SHOULD |
| NAME-03 | Solution folders | SHOULD |
| NAME-04 | Projects and packages | MUST |
| NAME-05 | Folders inside a module | SHOULD |
| NAME-06 | Namespaces | MUST |
| NAME-07 | Files | MUST |
| NAME-08 | Types | MUST |
| NAME-09 | Methods and functions | MUST |
| NAME-10 | Properties, fields and events | MUST |
| NAME-11 | Parameters and local variables | MUST |
| NAME-12 | Database objects | SHOULD |
| NAME-13 | Configuration and environments | MUST |
| NAME-14 | Wire and runtime identifiers | SHOULD |
| NAME-15 | Styles and static assets | SHOULD |
| NAME-16 | Branches and commits | SHOULD |
| NAME-17 | Tests | MUST |
| NAME-18 | Casing per language | SHOULD |
| CPLX-01 | Stay inside the budget | MUST |
| CPLX-02 | Guard clauses and early returns | MUST |
| CPLX-03 | One level of abstraction per function | SHOULD |
| CPLX-04 | Map with data, not branches | SHOULD |
| CPLX-05 | Repeat structure; single-source facts | MUST |
| CPLX-06 | Prefer duplication over the wrong abstraction | MUST |
| CPLX-07 | An abstraction must pay rent | MUST |
| CPLX-08 | Copy deliberately | MUST |
| CPLX-09 | Straight-line asynchronous code | MUST |
| CPLX-10 | Parameter objects after four parameters | SHOULD |
| CPLX-11 | Split by aggregate or role when over budget | SHOULD |
| CPLX-12 | Locality of behavior | SHOULD |
| CPLX-13 | You aren't gonna need it | MUST |
| ERR-01 | Exceptions for broken invariants, with precise types | MUST |
| ERR-02 | Expected failures are values at integration edges | SHOULD |
| ERR-03 | Never swallow an error | MUST |
| ERR-04 | Translate errors at the edge | SHOULD |
| ERR-05 | Resilience belongs to the client pipeline | MUST |
| ERR-06 | Cache-aside with safety margins; never cache failures | SHOULD |
| XCUT-01 | Structured logging with constant templates | MUST |
| XCUT-02 | Cross-cutting concerns live in pipelines | MUST |
| XCUT-03 | One mechanism per concern | MUST |
| XCUT-04 | Telemetry set up once | SHOULD |
| XCUT-05 | Tenancy scopes everything | MUST |
| DATA-01 | One repository per aggregate, explicit queries, no ambient context | MUST |
| DATA-02 | One unit of work per operation | MUST |
| DATA-03 | Declarative, central schema | SHOULD |
| DATA-04 | Audit through base types; creators never change | MUST |
| DATA-05 | Keep history by appending | MAY |
| DATA-06 | Readable storage | SHOULD |
| DATA-07 | Migrations are versioned code | MUST |
| DATA-08 | Null-safety stays on | MUST |
| API-01 | Thin endpoints | MUST |
| API-02 | Shared contracts and a typed client | SHOULD |
| API-03 | One adapter method per remote operation | MUST |
| API-04 | Anti-corruption layer at the boundary | MUST |
| API-05 | Explicit contracts; jobs for long operations | SHOULD |
| API-06 | Endpoints, scopes and base addresses are configuration | MUST |
| UI-01 | Separate template from behavior | SHOULD |
| UI-02 | Design-system components | SHOULD |
| UI-03 | Progressive, parallel loading with skeletons | SHOULD |
| UI-04 | Dialogs are components that return results | SHOULD |
| UI-05 | Form models aren't entities | MUST |
| UI-06 | Wizards: the parent owns the model, and steps have names | SHOULD |
| UI-07 | Pages orchestrate; they don't compute | SHOULD |
| UI-08 | Lifecycle hygiene | MUST |
| UI-09 | Scoped styles and design tokens | SHOULD |
| SEC-01 | Policy-based authorization | MUST |
| SEC-02 | Enrich identity once, at sign-in | SHOULD |
| SEC-03 | Allow-lists from data or configuration | SHOULD |
| SEC-04 | Authorize where state changes | MUST |
| SEC-05 | No hard-coded identities | MUST |
| SEC-06 | Secrets come from a secret store | MUST |
| SEC-07 | Authenticated by default | MUST |
| TEST-01 | A test project per module | SHOULD |
| TEST-02 | Names and shape | MUST |
| TEST-03 | Isolation | MUST |
| TEST-04 | Builders, and mocks only at I/O seams | SHOULD |
| TEST-05 | Test what breaks | SHOULD |
| HYG-01 | No commented-out code or dead branches | MUST |
| HYG-02 | TODOs reference a work item | SHOULD |
| HYG-03 | Remove what is unused | MUST |
| HYG-04 | One style, enforced by configuration | MUST |
| HYG-05 | Regions don't replace splitting | SHOULD |
| HYG-06 | Names match their owners | MUST |
| MIG-01 | Build a safety net before changing structure | MUST |
| MIG-02 | Separate structure changes from behavior changes | MUST |
| MIG-03 | Strangle, don't rewrite | MUST |
| MIG-04 | Work outside-in from the entry points | SHOULD |
| MIG-05 | Turn statics into instances behind interfaces | MUST |
| MIG-06 | Expose hidden state as explicit dependencies | MUST |
| MIG-07 | Decompose long parameter lists by kind | MUST |
| MIG-08 | Split god types along reasons to change | MUST |
| MIG-09 | Create the target structure early; move code into it gradually | SHOULD |
| MIG-10 | Consolidate data access per aggregate | SHOULD |
| MIG-11 | Wrap each external system before changing its callers | SHOULD |
| MIG-12 | Rename last, and mechanically | SHOULD |
| MIG-13 | Keep steps small, single-purpose and reversible | MUST |
| MIG-14 | Measure and ratchet | MUST |
| MIG-15 | Don't abstract while migrating | MUST |
| MIG-16 | Preserve external contracts | MUST |
