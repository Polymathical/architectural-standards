# Engineering Standards

> Architecture, object-oriented design, naming and complexity rules for building and refactoring software in any language that shares these design principles.

**Version:** 1.0 · **Date:** 2026-10-05

## Contents

- [0. About this document](#0-about-this-document)
- [1. Guiding values](#1-guiding-values)
- [2. Reference architecture](#2-reference-architecture)
- [3. Architecture and modularity](#3-architecture-and-modularity)
- [4. Object-oriented design](#4-object-oriented-design)
- [5. Naming conventions](#5-naming-conventions)
- [6. Complexity budget](#6-complexity-budget)
- [7. Errors and resilience](#7-errors-and-resilience)
- [8. Cross-cutting concerns](#8-cross-cutting-concerns)
- [9. Data and persistence](#9-data-and-persistence)
- [10. APIs and integrations](#10-apis-and-integrations)
- [11. UI components](#11-ui-components)
- [12. Security](#12-security)
- [13. Testing](#13-testing)
- [14. Code hygiene](#14-code-hygiene)
- [15. Refactoring playbook](#15-refactoring-playbook)
- [Appendix A. Rule index](#appendix-a-rule-index)
- [Appendix B. Pull request checklist](#appendix-b-pull-request-checklist)
- [Appendix C. Enforcement tools](#appendix-c-enforcement-tools)
- [Appendix D. Mechanisms across stacks](#appendix-d-mechanisms-across-stacks)

---

## 0. About this document

**What it is.** A set of rules distilled from the architecture of a production multi-tenant .NET platform: a web UI, a REST API, background workers, SQL storage, a distributed cache and several third-party integrations. The rules keep what that codebase does well and state it so it carries over to any stack with the same design principles, including C#, Java, Kotlin, TypeScript, Python, Go and PowerShell.

**What it is not.** A formatter configuration or a framework. Brace placement and line width belong in each repository's tool configuration (HYG-04).

**How to read a rule.**

- Every rule has a stable ID, such as `CPLX-05`, that reviews, commits and suppressions can cite.
- Levels follow RFC 2119. **MUST** applies to all new code. **SHOULD** is the default, and a deviation needs a written reason. **MAY** is a recommended option.
- Each rule gives the rule, then **Why**, **Do**, **Don't** and, where idioms differ, **Other stacks**.
- Code samples are in C# because the source codebase is .NET. Samples use a fictional product named `Acme`.

**How to adopt.**

1. New code follows the standard from its first commit.
2. Existing code converges by ratchet: measure, then never let a measure get worse (section 15).
3. Write a justified deviation down next to the code, so the next reader doesn't "fix" it: `// Deviation CPLX-01: generated mapping table`.

---

## 1. Guiding values

1. **Simple over clever.** The best code is code a new teammate can read once, top to bottom, and change safely. Fewer moving parts beat elegant ones.
2. **Explicit over magic.** Prefer code you can see and step through, such as a decorator class or a registration line, over behavior conjured by reflection, conventions or attributes. The exception is a well-known framework feature used the same way everywhere.
3. **Boundaries before code.** Decide where a responsibility lives (layer, module, class) before writing it. Most refactors are boundary corrections.
4. **Fail fast, fail loud.** Misconfiguration and broken invariants should stop the program at startup, or at the call that broke them. They should never surface later as a null somewhere else.
5. **Consistency over preference.** Have one way to do each thing per codebase. A slightly worse convention applied everywhere beats a better one applied half the time.
6. **Repetition over the wrong abstraction.** Sometimes it is cleaner to repeat yourself than to abstract. Repeat *structure* freely when each copy reads well on its own, but never repeat *facts* (CPLX-05 to CPLX-08).

---

## 2. Reference architecture

```text
+--------------------------------------------------------------------------------+
| HOSTS: thin composition roots, no business rules                               |
|   Web UI  |  REST API  |  Worker / CLI  |  Migration worker  |  Local AppHost  |
+--------------------------------------------------------------------------------+
            |  every host calls the same module installers: AddXxx(...)
            v
+--------------------------------------------------------------------------------+
| SERVICES                                                                       |
|   Business rules          Integrations              Cross-cutting modules      |
|   one service per         thin adapters plus        security, caching,         |
|   aggregate               anti-corruption layer     telemetry defaults         |
+--------------------------------------------------------------------------------+
            |  context is resolved above and passed down as ids (tenantId, actingUserId)
            v
+--------------------------------------------------------------------------------+
| DATA.REPOSITORY: one repository per aggregate, one unit of work per call       |
+--------------------------------------------------------------------------------+
            v
+--------------------------------------------------------------------------------+
| DATA: entities, audit base types, schema configuration, migrations             |
+--------------------------------------------------------------------------------+
            v
+--------------------------------------------------------------------------------+
| COMMON: framework-free enums, constants, result types, small extensions        |
+--------------------------------------------------------------------------------+

Outbound HTTP:  service -> typed client -> auth handler -> resilience handler -> remote API
Shared types:   Acme.Api.Contracts is referenced by both the API host and Acme.Api.Client
```

| Layer | Owns | Never |
|---|---|---|
| Common | framework-free primitives: enums, constants, result types, small extension functions | references a UI, web or persistence framework |
| Data | entities, audit base types, schema configuration, migrations | contains business rules or calls services |
| Data.Repository | one repository per aggregate; queries and writes; one unit of work per call | resolves the current user or tenant |
| Services | business rules, integrations (thin adapters plus an anti-corruption layer), cross-cutting modules | knows which host it runs in |
| Contracts | request and response types shared by an API and its clients | contains behavior |
| Hosts | composition root and framework glue: web UI, API, worker or CLI, migration worker, local orchestrator | contains business rules |

Requests flow down and dependencies point down. Context (tenant, acting user) is resolved at the top and passed down explicitly. Cross-cutting concerns (tokens, retries, caching, telemetry) wrap this flow in pipelines and decorators instead of living inside it.

---

## 3. Architecture and modularity

### ARCH-01: Layers depend one way

**MUST.** Organize code into the layers in section 2. A layer depends only on layers below it, and the foundation layer (`Common`) references no UI, web or persistence framework.

- **Why:** One-way dependencies keep a change local, so a UI rewrite or a storage swap touches one layer. A framework type in the foundation drags that framework into every project that references it.
- **Do:** Enforce direction with project or package references, not just folders, so a wrong import fails the build.
- **Don't:** Put a UI-framework helper, such as a navigation extension, in the foundation module "because everyone uses it". Give it a UI-level home.
- **Other stacks:** Java uses Gradle or Maven modules plus ArchUnit tests. TypeScript uses workspace packages plus dependency-cruiser or eslint-plugin-boundaries. Python uses packages plus import-linter. Go uses `internal/` packages.

### ARCH-02: One module per capability

**SHOULD.** Give each business capability, integration and cross-cutting concern its own module (project or package), such as `Acme.Services.Billing`, `Acme.Services.SecurityCenter` or `Acme.Services.Caching`. A module exposes its interfaces, its models and one registration entry point.

- **Why:** A small module has an obvious owner and a short dependency list, and any host can reuse it.
- **Don't:** Let a `Shared` or `Utils` module grow into a second application. A "shared" module that keeps gaining dependencies is several capabilities under one name.

### ARCH-03: Modules register themselves; the entry point is a list

**MUST.** Each module provides one installer that registers everything the module owns, including the modules it depends on. A host's entry point reads as a table of contents of installers.

- **Why:** Wiring knowledge lives next to the code it wires. A new host calls the same installers, and removing a module removes one line.
- **Don't:** Register a module's types inline in a host's startup, or register module A's services inside module B's installer.
- **Other stacks:** Spring uses a `@Configuration` class per module and NestJS uses modules. Python uses a `configure(container)` function per package. Go calls constructors only from `main`.

```csharp
// Module installer, in Acme.Services.Business/Extensions/ServiceCollectionExtensions.cs
public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddBusinessServices(this IServiceCollection services, IConfiguration configuration)
    {
        services.AddRepositories(configuration);   // compose the modules this one depends on
        services.AddScoped<IUserService, UserService>();
        services.AddScoped<ITenantService, TenantService>();
        services.AddScoped<IRoadmapService, RoadmapService>();
        return services;
    }
}

// Host entry point: a list of installers
builder.Services
    .AddAuthenticationServices(builder.Configuration)
    .AddAuthorizationPolicies()
    .AddBusinessServices(builder.Configuration)
    .AddBilling()
    .AddSupportDesk(builder.Configuration)
    .AddSecurityCenter();
```

### ARCH-04: Hosts are thin shells

**MUST.** A host (web UI, API, worker, CLI or migration runner) contains only composition, framework glue and host-specific adapters. Business behavior lives in modules, so every host gets the same behavior.

- **Why:** Running the same module unchanged in a web request and in a background agent is the cheapest proof that the boundaries are right.
- **Don't:** Put a business rule in a controller, a page or `Program`/`main` because "only this host needs it". The next host will need it too.

### ARCH-05: Ambient context goes behind an interface

**MUST.** Anything a module needs to know about who it is acting for, such as the current user, home tenant or active tenant, comes through an interface. Each host provides one implementation. Modules never read HTTP context, session state or globals directly.

- **Why:** This lets the same module run in a web request, a background job and a test. It is also the one place to enforce tenant rules.
- **Don't:** Read `HttpContext` or thread-local state deep inside a service, or repeat "current user" lookups across several services.
- **Other stacks:** Java uses a request-scoped bean, or an explicit context parameter in reactive code. TypeScript uses `AsyncLocalStorage` behind an interface, and Python uses `contextvars` behind a `Protocol`. Go reads `context.Context` through one typed accessor package.

```csharp
public interface IUserContext
{
    Guid GetHomeTenant();
    Guid GetActiveTenant();
    Task SetActiveTenantAsync(Guid tenantId);
    event EventHandler<TenantChangedEventArgs> TenantChanged;
}

// Web host: per-session implementation backed by the distributed cache
builder.Services.AddScoped<IUserContext, SessionUserContext>();

// Worker host: the same modules, with a tenant taken from the command line
builder.Services.AddSingleton<IUserContext>(_ => new ManualUserContext { TenantId = options.TargetTenant });
builder.Services.AddSecurityCenter();   // unchanged module, reused as-is
```

### ARCH-06: Share contracts, not implementations

**SHOULD.** When one of your applications calls another, put the request and response types in a contracts module that both reference (`Acme.Api.Contracts`). Ship a typed client (`Acme.Api.Client`) with one method per endpoint.

- **Why:** The compiler keeps server and client in sync, and callers never hand-build URLs or JSON.
- **Don't:** Copy DTOs into the client "for decoupling", or let the contracts module reference server internals.
- **Other stacks:** OpenAPI-generated clients, a shared types package in a TypeScript workspace, or Protobuf for gRPC.

### ARCH-07: Layered configuration, typed settings, no secrets in source

**MUST.** Load configuration from layered sources in a documented order of precedence. Bind each section to one typed settings class that declares its section name once.

| Order (later wins) | Source | Holds |
|---|---|---|
| 1 | `appsettings.json` | defaults that are safe in every environment |
| 2 | `appsettings.{Environment}.json` | environment-specific values that aren't secret |
| 3 | secret store (key vault) | secrets |
| 4 | environment variables | deployment overrides (`ConnectionStrings__AcmeDb`) |
| 5 | `appsettings.{Environment}.user.json`, git-ignored, local machines only | a developer's personal overrides |

- **Why:** Anyone can answer "where does this value come from?", secrets never touch the repository, and a renamed key breaks in one place.
- **Don't:** Read the same `"Section:Key"` string in several classes, or commit a connection string "just for dev".
- **Other stacks:** Spring profiles plus `@ConfigurationProperties`, pydantic-settings, a zod-validated config object, or a Go struct loaded with envconfig.

```csharp
public sealed class RedisCacheSettings
{
    public const string SectionName = "RedisCache";

    [Required] public string Configuration { get; init; } = string.Empty;
    [Required] public string InstanceName { get; init; } = string.Empty;
}
```

### ARCH-08: Validate wiring and configuration at startup

**MUST.** Turn on dependency-container validation and validate required settings when the host starts. A missing setting stops startup with a message that names the key.

- **Why:** A configuration bug found at deploy time costs minutes. The same bug found at the first production request costs an incident.
- **Don't:** Default a missing secret to an empty string, only to fail later with a 401 from a remote API.

```csharp
builder.Host.UseDefaultServiceProvider(o => { o.ValidateScopes = true; o.ValidateOnBuild = true; });

builder.Services.AddOptions<RedisCacheSettings>()
    .BindConfiguration(RedisCacheSettings.SectionName)
    .ValidateDataAnnotations()
    .ValidateOnStart();
```

### ARCH-09: Local infrastructure as code; migrations as their own step

**SHOULD.** Declare local dependencies (database, cache, emulators) in code, so one command starts the whole system. An orchestrator such as .NET Aspire or a compose file does this. Apply schema migrations with a dedicated one-shot worker or pipeline step that the applications wait for, never as a side effect of application startup.

- **Why:** A new developer is productive in minutes. Schema changes are explicit, ordered and observable, and two instances of an application never race to migrate.
- **Do:** Start the database and cache, run the migration worker to completion, then start the applications.
- **Other stacks:** A compose `depends_on` with `condition: service_completed_successfully`, or Flyway, Liquibase, Alembic or golang-migrate run as a job.

### ARCH-10: Long-running work is a job

**SHOULD.** An operation that can outlast a request starts a job and returns its id at once. Clients poll `GET …/job/{jobId}` or subscribe for status updates.

- **Why:** Requests stay fast and safe to retry, progress is observable, and timeouts stop being business logic.
- **Don't:** Hold an HTTP request open for minutes, or raise timeouts until it "works".

```csharp
public sealed class JobResponse
{
    public List<Guid> JobIds { get; init; } = [];

    [JsonIgnore] public bool HasJobs => JobIds.Any(id => id != Guid.Empty);
}
```

---

## 4. Object-oriented design

The four pillars come first, then SOLID, then the supporting principles. Each rule says how this architecture applies the principle.

### OOP-01: Abstraction: speak your own domain at the boundary

**MUST.** Translate vendor and framework concepts into your own vocabulary where they enter the system, in an anti-corruption layer. Inside the boundary, code talks about `SecurityPlanType.Gold`, not about a vendor's custom-field strings.

- **Why:** A vendor change touches one adapter, instead of every rule that once inspected the vendor's fields.
- **Don't:** Pass vendor SDK models through services into the UI, or test vendor field names inside business rules.

```csharp
public static class BillingPlanExtensions
{
    private const string ProductIdField = "cf_product_id";   // the vendor's field name, in one place

    public static string ProductId(this Plan plan) => plan.GetValue<string>(ProductIdField);

    public static bool IsManagedPlan(this Plan plan) => ProductCatalog.ManagedServiceIds.Contains(plan.ProductId());

    public static SecurityPlanType ToSecurityPlanType(this Plan plan) =>
        ProductCatalog.SecurityPlans.GetValueOrDefault(plan.ProductId(), SecurityPlanType.None);
}
```

### OOP-02: Encapsulation: expose the minimum

**MUST.** Keep state private by default, and expose behavior plus read-only views. Identity is set once, collections are exposed read-only, and shared constants are immutable.

- **Why:** Every public setter is a place where an invariant can break.
- **Do:** `public Guid Id { get; private set; } = Guid.NewGuid();` · `public IReadOnlyList<string> Scopes => _scopes;` · `public static readonly IReadOnlySet<string> ManagedServiceIds = ...;`
- **Don't:** `public static string[] ManagedIds = { ... };`, which any caller can reassign or mutate.

### OOP-03: Inheritance: shared shape only, at most two levels

**SHOULD.** Use a base class for genuinely shared data shape or framework hooks, such as audit fields or a component base. Keep hierarchies at most two levels deep below the framework type. A base class never knows about its subclasses.

- **Why:** Deep hierarchies hide behavior where readers don't look. A base class that references its subclasses can't be extended without being edited.
- **Don't:** Write a base class with properties or switches that exist for only one of its subclasses.

```csharp
public abstract class Auditable
{
    public DateTime UtcDateCreated { get; set; } = DateTime.UtcNow;
}

public abstract class UserAuditable : Auditable
{
    public DateTime UtcDateModified { get; set; } = DateTime.UtcNow;
    public Guid LastModifiedById { get; set; }
    public virtual User LastModifiedBy { get; set; } = null!;
}
```

### OOP-04: Polymorphism: replace repeated conditionals

**SHOULD.** When the same `switch` or `if` chain on a type, kind or name appears in more than one place, or grows with every feature, replace it with polymorphism (one strategy per case) or a lookup table.

- **Why:** Adding a case should mean adding a class or a row, not hunting down every switch.
- **Do:** Choose an implementation once, at composition time. Examples are the web or worker `IUserContext`, and a choice between client-credentials and delegated authentication handlers made per tenant in the client factory.
- **Don't:** Repeat a `switch (customerTier)` over string literals in pricing, reporting and UI code.
- A single switch expression that maps one value to another is fine (CPLX-04).

### OOP-05: Single responsibility

**MUST.** A class has one reason to change. In this architecture:

| Role | Changes when |
|---|---|
| Repository | storage or a query changes |
| Service | a business rule changes |
| Adapter | its remote API changes |
| Controller or endpoint | the HTTP contract changes |
| UI component | its section of the screen changes |

- **Why:** Mixed responsibilities couple unrelated changes and let classes grow without limit.
- **Smells:** A class over budget (CPLX-01). An interface that serves several aggregates. A page that injects ten services.

### OOP-06: Open/closed: extend by wrapping

**SHOULD.** Add cross-cutting behavior (caching, retries, authentication, logging) by wrapping stable code in decorators, pipeline handlers, middleware or authorization handlers. Don't edit the wrapped code to add it.

- **Why:** The adapter stays one line per endpoint (API-03), and caching can be removed or swapped without touching it.
- **Don't:** Add `if (cacheEnabled)` branches to every adapter method.

```csharp
public sealed class CachedSecurityCenterService : ISecurityCenterService
{
    private readonly ISecurityCenterService _inner;
    // cache, user context and duration arrive through the constructor

    public Task<MachineResponse?> GetMachineByIdAsync(string machineId) =>
        GetOrCreateAsync(() => _inner.GetMachineByIdAsync(machineId), _cacheDuration, machineId);

    public Task<MachineAlertsResponse?> GetAlertsByMachineIdAsync(string machineId) =>
        GetOrCreateAsync(() => _inner.GetAlertsByMachineIdAsync(machineId), _cacheDuration, machineId);
}

// Registration (Scrutor). The decorated adapter is unchanged.
services.AddScoped<ISecurityCenterService, SecurityCenterService>();
services.Decorate<ISecurityCenterService, CachedSecurityCenterService>();
```

Each member repeats the same one-line shape. That repetition is deliberate, because every cached call stays visible and greppable (CPLX-05).

### OOP-07: Liskov substitution: every implementation honors the whole contract

**MUST.** Every implementation of an interface, whether production, per-host or a test double, honors the interface's documented behavior, including side effects and events. If the web `IUserContext` raises `TenantChanged` when the tenant switches, the worker implementation raises it too.

- **Why:** Substitutability is what makes ARCH-05 work. A "mostly compatible" implementation produces bugs that appear only in the host that uses it.
- **Don't:** Implement half an interface and throw `NotImplementedException` from the rest. That is a sign the interface is too big (OOP-08).

### OOP-08: Interface segregation: role-sized interfaces

**SHOULD.** Keep each interface to one role or aggregate, with at most 10 members (CPLX-01). Split large service interfaces by aggregate or by use case.

- **Why:** Consumers depend only on what they use, and implementations and fakes stay small.
- **Do:** Split an `IAccountService` that has grown past 20 members into `IProfileService`, `IPreferencesService` and `IAccountStatusService`.

### OOP-09: Dependency inversion: abstractions at I/O seams, constructor injection

**MUST.** Business code depends on abstractions for anything that does I/O or varies by host: storage (`IDbContextFactory<T>`), HTTP (`IHttpClientFactory` or typed clients), cache, clock and user context. Dependencies arrive through the constructor. Service location (`GetRequiredService`) is allowed only inside composition-root factories.

- **Why:** Constructor injection makes dependencies visible and countable (CPLX-01), and I/O abstractions are the seams that tests use.
- **Do:** Define interfaces for services, repositories, adapters and context providers.
- **Don't:** Define interfaces for DTOs, entities, value objects or pure functions. Don't build a second service provider during configuration to resolve something "early", and don't create a new `HttpClient` per call.

### OOP-10: Composition over inheritance

**SHOULD.** Combine small parts instead of extending large ones: UI components with slots (`ChildContent`), services composed of injected collaborators, and decorators instead of subclass overrides.

### OOP-11: Law of Demeter

**SHOULD.** Talk to immediate collaborators. A chain such as `permission.Tenant.CompanyDetails.CompanyName` couples the caller to the whole object graph. Ask the owner for what you need, or project it in the query.

### OOP-12: Tell, don't ask; separate commands from queries

**MUST.** A query returns data and changes nothing. A command changes state and is named as a command. A method that does both says so in its name (`GetOrCreateUserAsync`).

- **Don't:** Write a `DeactivateAccount` that quietly creates the account when it doesn't exist, a `Get…` method that writes, or a property getter that validates, logs or calls the network.

### OOP-13: Least astonishment

**MUST.** Behavior matches the name and the signature. `Get…` returns null for "missing" instead of throwing. `Try…` never throws for an expected failure. `Validate…` returns true when the input is valid. A nullable return type means "may be missing".

- **Don't:** Write a `ValidateEmail()` that returns `true` when validation *failed*.

### OOP-14: Immutable data carriers

**SHOULD.** DTOs, results, events and value objects are immutable (`record`, `init`, `readonly`). Mutability is reserved for entities tracked by an ORM and for UI binding models.

### OOP-15: GRASP at a glance

**MAY.** Use these principles for assigning responsibilities to decide where a behavior goes.

| Principle | Meaning | In this architecture |
|---|---|---|
| Information expert | Give a behavior to the class that has the data | `JobResponse.HasJobs`; `plan.IsManagedPlan()` |
| Creator | The object that holds the context creates the thing | services create entities with the acting user and tenant already set |
| Controller | A thin coordinator receives each system event | endpoints and page code-behind delegate to services |
| Low coupling | Depend on few, stable abstractions | modules expose interfaces plus one installer |
| High cohesion | Keep related behavior together | one adapter per remote API; one repository per aggregate |
| Polymorphism | Vary behavior by type, not by conditionals | one `IUserContext` per host |
| Pure fabrication | Invent a non-domain class to keep cohesion | a tenant-scoped cache-key generator; a list value comparer |
| Indirection | Put an intermediary between two things that change separately | an auth handler between the HTTP client and the token service |
| Protected variations | Wrap a likely point of change in a stable interface | an anti-corruption layer around vendor SDKs; typed settings around environments |

### OOP-16: Patterns in use

**SHOULD.** Reach for these patterns first. This architecture relies on them, and the table gives each one's limits.

| Pattern | Use when | Avoid when | Example |
|---|---|---|---|
| Repository | an aggregate is persisted | it would wrap the ORM generically (CPLX-07) | `TenantRepository` |
| Unit of work per operation | each call needs isolated, short-lived state | a context would be held across calls | `IDbContextFactory<T>` used inside each method |
| Facade (service) | callers need one entry point over repositories and integrations | it becomes a pass-through for everything (OOP-08) | `TenantService` |
| Adapter / anti-corruption layer | a third-party API or SDK enters the system | the type is already your own | `SecurityCenterService`; billing plan extensions |
| Decorator | adding cross-cutting behavior over a stable interface | it would change business results | `CachedSecurityCenterService` |
| Chain of responsibility | per-request steps such as auth, retry and logging | the steps are business branching | HTTP delegating handlers; middleware |
| Strategy | behavior varies by host, tenant or configuration | only one variant exists | `SessionUserContext` and `ManualUserContext` |
| Factory, including keyed | construction needs runtime context | a plain constructor call is enough | keyed API-client factories |
| Fluent builder | one object takes optional configuration | it would hide required inputs | `.WithScopes(...).WithTenantId(...)` |
| Observer | other components react to a state change | unsubscription can't be guaranteed (UI-08) | `TenantChanged` event |
| Interceptor (AOP) | one uniform concern applies to many members | a decorator already covers that concern (XCUT-03) | a cacheable attribute |
| Result object | an integration edge has expected failures | it would hide programming errors | `Result<T>` (ERR-02) |
| Composition root | always: one place per host builds the object graph | | `Program.cs` |
| Job and poll | work outlives a request | | start a job, then poll `GET job/{jobId}` |
| Cache-aside | data is read far more often than written | the data must be strongly consistent | token cache; API response cache |
| Allow-list | access must be granted explicitly | | tenant allow-list checked at sign-in |

---

## 5. Naming conventions

Names are the cheapest documentation a codebase has. This chapter works top-down, from the repository to a local variable. NAME-18 maps the casing to other languages. The semantic rules apply in every language.

### NAME-01: General rules

**MUST.**

- **Reveal intent and role.** A reader knows what a thing is and why it exists without opening it.
- **Use one canonical term per concept** across code, UI, database and documentation. When two concepts are close, name both explicitly. `HomeTenantId` is where the user's identity lives, and `ActiveTenantId` is whose data they are viewing. `TenantUserId` is an external directory id, and `Id` is the internal key.
- **Case acronyms as words:** `Api`, `Smtp`, `Mfa`, `Utc`, as in `SmtpServer` and `GetXmlReport`, not `SMTPServer` or `GetXMLReport`. Two-letter acronyms follow the language norm: `IO` in .NET, and Go capitalizes every initialism (`ID`, `URL`).
- **Don't abbreviate** beyond the universal cases (`Id`, `Utc`, `Api`, `Url`, `Dto`).
- **Start with a letter** (`ThreeDayForecast`, not `3DayForecast`). Leave the type out of the name (`users`, not `userList`). Add no temporal markers (`New`, `Old`, `Temp`, `Copy`, `2`, `Final`).
- **Spell-check names.** A misspelled public name, such as `GetRecievedMessages`, becomes an API that is expensive to rename.

### NAME-02: Repository and solution

**SHOULD.**

| Item | Pattern | Example |
|---|---|---|
| Repository | `{product}` or `{product}-{purpose}`, kebab-case | `acme`, `acme-automation`, `engineering-standards` |
| Solution or workspace | `{Product}`, PascalCase, one per repository | `Acme.sln` |
| Top-level folders | lowercase, named for their purpose | `src/`, `docs/`, `pipelines/`, `tools/` |

Keep tests in one predictable place: beside their projects in `src/`, or in a parallel `tests/` tree. Don't do both.

### NAME-03: Solution folders

**SHOULD.** Group projects in solution folders by layer, so that a project's folder is predictable from its name.

```text
Acme.sln
├── Hosts/          Acme.Web · Acme.Api · Acme.ImportAgent · Acme.AppHost
├── Contracts/      Acme.Api.Contracts · Acme.Api.Client
├── Services/       Acme.Services.Business · Acme.Services.Billing · Acme.Services.Security · Acme.Services.Caching
├── Data/           Acme.Data · Acme.Data.Repository · Acme.Data.MigrationWorker
├── Foundation/     Acme.Common · Acme.ServiceDefaults
└── Tests/
    ├── Services/   Acme.Services.Business.UnitTests
    └── Data/       Acme.Data.UnitTests · Acme.Data.Repository.UnitTests
```

- **Don't:** File a persistence project under `Services`, or split test projects between a `Tests` folder and the folders of the projects they test.

### NAME-04: Projects and packages

**MUST.** Name projects `{Product}.{Layer}.{Capability}[.{Qualifier}]`. The folder name, project file name, assembly or package name and root namespace are identical.

| Kind | Pattern | Example |
|---|---|---|
| Web UI host | `{Product}` or `{Product}.Web` | `Acme.Web` |
| API host | `{Product}.Api` | `Acme.Api` |
| API contracts | `{Product}.Api.Contracts` | `Acme.Api.Contracts` |
| API client | `{Product}.Api.Client` | `Acme.Api.Client` |
| Worker or CLI host | `{Product}.{Purpose}Agent` or `{Product}.{Area}.{Purpose}Worker` | `Acme.ImportAgent`, `Acme.Data.MigrationWorker` |
| Local orchestration | `{Product}.AppHost`, `{Product}.ServiceDefaults` | `Acme.AppHost` |
| Foundation | `{Product}.Common` | `Acme.Common` |
| Entities and schema | `{Product}.Data` | `Acme.Data` |
| Persistence | `{Product}.Data.Repository` | `Acme.Data.Repository` |
| Business rules | `{Product}.Services.Business` | `Acme.Services.Business` |
| Integration | `{Product}.Services.{ExternalSystem}` | `Acme.Services.Billing`, `Acme.Services.SecurityCenter` |
| Cross-cutting module | `{Product}.Services.{Concern}` | `Acme.Services.Caching`, `Acme.Services.Security` |
| Tests | `{Project}.UnitTests`, `{Project}.IntegrationTests` | `Acme.Data.Repository.UnitTests` |

- **Don't:** Name a folder differently from its project (`Parser/Acme.Services.Parser.csproj`), leave a second, stale project file beside the real one, or drop the product prefix from a host (`ImportAgent`).

### NAME-05: Folders inside a project

**SHOULD.** Use two kinds of folders.

**Category folders** are plural nouns naming the kind of type they hold:

| Folder | Holds |
|---|---|
| project root | the module's main interfaces and their implementations, side by side |
| `Models/` | DTOs, entities, view models and form models (`Models/Base/` for abstract bases) |
| `Extensions/` | extension classes, including the module installer `ServiceCollectionExtensions` |
| `Configuration/` | typed settings classes |
| `Constants/` | constant holders |
| `Enums/` | enums shared across the module |
| `Exceptions/` | the module's exception types |
| `Handlers/` | pipeline and authorization handlers |
| `Providers/` | credential and state providers |
| `Decorators/` | decorators |
| `Comparers/` | equality and ordering comparers |
| `Controllers/` | API controllers |

**Feature folders** use PascalCase names for a cohesive sub-capability (`TenantSwitching/`, `Calculator/`). The child views of one page go in `{Page}Subpages/` (`EmailConfigurationSubpages/`).

A UI project:

```text
Components/
├── Layout/       MainLayout · NavMenu · HeaderMenu
├── Pages/        Overview · SecurityCenter · EmailConfiguration
│   └── EmailConfigurationSubpages/   AntiMalware · AntiSpam · LegalAgreement
├── Shared/       AcmeCardContainer · AcmeProgressCard · AcmeChip
│   ├── Dialogs/      NewRoadmapIdeaDialog · VulnerabilityDetailsDialog
│   ├── Skeletons/    ChartSkeleton · PeopleCardSkeleton
│   └── Cards/        LearnCatalogCard
└── Icons/        HomeIcon · SettingsIcon
Models/           view and form models (Models/Enums/ for UI-only enums)
wwwroot/          static assets (scripts/, styles)
```

- **Don't:** Split interfaces from their implementations into `Interfaces/` and `Services/` folders. Don't create grab-bag folders such as `Helpers/`, `Utils/`, `Misc/` or a `Common/` inside a project; name the capability instead. Keep `POC`, `Old`, `Temp` and `Backup` folders out of product trees, and use a branch instead.

### NAME-06: Namespaces

**MUST.** A namespace is the root namespace plus the folder path, as in `Acme.Services.Security.TenantSwitching`. Use one declaration form per repository. Prefer file-scoped (`namespace Acme.Data;`), which removes a level of nesting from every file.

- **Other stacks:** A Java package and a Python package each follow their directory. TypeScript path aliases mirror folders. A Go package name is the last path element, in lowercase.

### NAME-07: Files

**MUST.** Each file holds one public type, and the file name equals the type name exactly, including case. Case-sensitive file systems and build agents break on near-misses such as `appsettings.Qa.json` beside `appsettings.QA.json`.

| Artifact | Pattern | Example |
|---|---|---|
| Type | `{TypeName}.cs` | `TenantRepository.cs` |
| Component | `{Component}.razor` + `{Component}.razor.cs`, plus `.razor.css` | `AcmeProgressCard.razor.cs` |
| Test class | `{ClassUnderTest}Tests.cs` | `TenantRepositoryTests.cs` |
| App settings | `appsettings.json`, `appsettings.{Environment}.json`, `appsettings.{Environment}.user.json` (git-ignored) | `appsettings.Staging.json` |
| Static asset | `{prefix}-{purpose}.{ext}`, kebab-case | `acme-time.js`, `acme-dom-utils.js` |
| Migration | `{yyyyMMddHHmmss}_{Verb}{Subject}` | `20250115093000_AddCustomerTable` |
| Pipeline | `{purpose}-pipeline.yml`, kebab-case | `build-pipeline.yml` |
| Script | PowerShell `Verb-Noun.ps1`; shell or Python in kebab-case or snake_case | `Install-Modules.ps1`, `seed_local_db.py` |
| Repository documents | `README.md` per folder; `UPPER-KEBAB.md` for repository-wide documents | `ENGINEERING-STANDARDS.md` |

- **Don't:** Put a page component, its form model and a helper class in one file, or give a file a name that differs from the type it holds.

### NAME-08: Types

**MUST.** A class or record is a noun or noun phrase whose suffix states its role.

| Suffix | Responsibility | Example |
|---|---|---|
| `Service` | business rules or orchestration; an integration facade | `TenantService`, `BillingService` |
| `Repository` | persistence for one aggregate | `TenantRepository` |
| `Client` | typed client for one remote API | `ConfigurationApiClient` |
| `Handler` | one step in a pipeline, or an authorization handler | `ClientCredentialsHandler`, `ValidUserHandler` |
| `Provider` | supplies credentials or state to a framework | `TokenAuthenticationProvider` |
| `Middleware` | HTTP request middleware | `UserContextMiddleware` |
| `Extensions` | static extension methods, named after the extended type | `ClaimsPrincipalExtensions`, `ServiceCollectionExtensions` |
| `Settings` | typed configuration with a `SectionName` constant | `RedisCacheSettings` |
| `Options` | an option bag for one component or command line | `ImportAgentOptions` |
| `Request` / `Response` / `Details` | wire contracts | `StartTenantDriftJobRequest`, `JobResponse`, `JobDetails` |
| `Model` / `Form` | UI view model / UI input model with validation | `ScoreModel`, `RoadmapIdeaForm` |
| `Dialog` / `Skeleton` / `Card` / `Icon` / `Layout` | UI component roles | `NewRoadmapIdeaDialog`, `ChartSkeleton` |
| `Exception` | an error condition | `UnauthorizedTenantException` |
| `EventArgs` | an event payload | `TenantChangedEventArgs` |
| `Attribute` / `Requirement` | metadata / an authorization requirement | `CacheableAttribute`, `ValidUserRequirement` |
| `Comparer` / `Generator` | equality or ordering / produces an artifact | `ListValueComparer`, `ConfigurationScriptGenerator` |
| `Worker` / `Agent` / `HostedService` | a background process | `MigrationWorker` |
| `Base` | an abstract base class | `ConfigurationComponentBase` |

- **Interfaces:** `I` plus the implementation's role name (`ITenantService` ↔ `TenantService`). Name an alternative implementation by its distinguishing trait, as a prefix: `CachedSecurityCenterService` (a decorator), `SessionUserContext` (web session), `ManualUserContext` (a tenant set by hand). Don't use `Impl`, `Default` or a technology suffix as the only distinction.
- **Static holders:** Extension classes are `{ExtendedType}Extensions`. Constant holders are plural domain nouns (`Tenants`, `ServiceKeys`, `AppClaimTypes`, `Roles`), not `Constants` or `Helpers`.
- **Enums:** A singular noun with a classifier suffix (`TenantStatus`, `GuestInviterType`, `VulnerabilitySeverity`), with PascalCase members. A `[Flags]` enum is plural (`AuthorizationFlags`), with `None = 0` and named combinations. Never use an `Enum` suffix: `OrderStatus`, not `OrderStatusEnum`.
- **Generic parameters:** `T` alone, otherwise `T{Role}` (`TRequest`, `TResponse`, `TEntity`). Never `TB` or `T2`.
- **UI components:** Design-system components share the product prefix (`Acme*`). Pages are named after their feature and route (`SecurityCenter` ↔ `/security-center`).
- **Avoid these as names or suffixes:** `Helper`, `Utils`, `Manager`, `Processor`, `Data`, `Info`, `Common`, `Misc`. Each one hides the real responsibility.

### NAME-09: Methods and functions

**MUST.** Start with a verb from the shared vocabulary, so a caller can predict behavior from the name.

| Verb | Contract | Example |
|---|---|---|
| `Get{X}` | returns X, or null when missing; no side effects | `GetCompanyDetailsByTenantIdAsync` |
| `GetAll{Xs}` | returns a collection, empty rather than null | `GetAllIdeasAsync` |
| `GetLatest{X}` | returns the newest by timestamp | `GetLatestEmailSecurityConfigurationByTenantIdAsync` |
| `GetOrCreate{X}` | returns the existing item, or creates and saves it | `GetOrCreateUserAsync` |
| `Create{X}` | inserts; fails if the item already exists | `CreateIdeaAsync` |
| `Save{X}` | inserts or updates (upsert) | `SaveCompanyDetailsAsync` |
| `Update{X}` | changes an existing item; use `Update` or `Edit` per codebase, not both | `UpdateUserLastLoginAsync` |
| `Delete{X}` | removes; returns the number of rows affected | `DeleteIdeaAsync` |
| `Duplicate{X}` / `Toggle{X}` / `Reset{X}` | a named state transition; `Toggle` only flips | `ToggleTenantStatusAsync` |
| `Try{Verb}` | never throws for an expected failure; returns null, false or a result | `TryGetFromJsonAsync` |
| `Is{State}` / `Has{X}` / `Can{Action}` | boolean query | `IsUserFirstLoginAsync`, `IsManagedPlan` |
| `To{Type}` / `From{Format}` | conversion | `ToCsvString`, `FromBase64` |
| `Build` / `Generate` / `Calculate{X}` | pure computation | `BuildFilter`, `CalculateProgress` |
| `Validate{X}` | returns true, or a success result, when the input is valid | `ValidateLegalAgreement` |
| `Fetch{X}` | UI only: loads remote data into component state | `FetchDevicesAsync` |
| `Set{X}` | UI only: computes and assigns component state | `SetSecureScore` |
| `Add{Module}` | dependency registration | `AddBusinessServices` |
| `Use{Middleware}` | request-pipeline registration | `UseUserContext` |
| `With{Setting}` | fluent configuration that returns the same object | `WithScopes`, `WithTenantId` |
| `On{Event}` / `Handle{Event}` | event handler | `OnTokenValidated`, `HandleTenantChanged` |

- **Selection criteria** use `By{Key}`, as in `ByTenantId` or `ByTenantIdAndUserId`. Don't mix `By{X}` and `For{X}` for the same meaning, and reserve `With` for fluent configuration.
- **Asynchronous methods** end in `Async` where the language convention calls for it, as in .NET. Languages whose types already signal it, such as a TypeScript `Promise`, Python's `async def` or Kotlin's `suspend`, add no suffix.

### NAME-10: Properties, fields and events

**MUST.**

- **Properties** are PascalCase noun phrases. Collections are plural (`Users`, `Votes`, `DomainsToProtect`).
- **Booleans** read as positive questions with `Is`, `Has`, `Can`, `Should`, `Show`, `Enable` or `Allow` (`IsComplete`, `HasJobs`, `ShowWelcomeDialog`, `EnableMailboxAuditing`). Never negate them (`IsNotComplete`).
- **Relationships** are named by role, not by type: `CreatedBy`, `LastModifiedBy`, `HomeTenant`, `ActiveTenant`. The foreign key is the role plus `Id` (`CreatedById`, `ActiveTenantId`).
- **Ids:** Use `Id` for the entity's own key and `{Entity}Id` for references. Disambiguate when an entity carries more than one kind of id (NAME-01).
- **Time:** UTC values carry `Utc` in the name (`UtcDateCreated`, `UtcLastLogin`) or use a zone-aware type. A duration carries its unit (`CacheDurationMinutes`) unless it has a duration type such as `TimeSpan`.
- **Private fields** are `_camelCase` and `readonly` when assigned once. Constants and `static readonly` fields are PascalCase in C# (`SectionName`); C# has no SCREAMING_CASE.
- **Events** are past-tense verb phrases (`TenantChanged`). The payload type is `{Event}EventArgs`, and handlers are `On{Event}` or `Handle{Event}`.
- **UI state flags** follow one pattern per codebase, such as `IsLoading{Section}`.

### NAME-11: Parameters and local variables

**MUST.**

- Use camelCase full words: `tenantId`, `response`, `configuration`, not `tid`, `res` or `cfg`.
- Name by role, not type: `activeTenants`, not `tenantList`; `expiresOn`, not `dateTime2`.
- Use single-letter lambda parameters only for one-line projections (`x => x.Id`); otherwise use a descriptive name (`vote => vote.UserId == userId`).
- Name the actor explicitly. A repository write takes `actingUserId`, not an ambiguous `userId`.
- `cancellationToken` is the last parameter of every asynchronous method that does I/O.
- Pass boolean literals as named arguments: `optional: true`, `forceCacheWrite: true`.
- Avoid placeholder names (`data`, `item`, `obj`, `temp`, `result2`) outside scopes of three lines or fewer.

### NAME-12: Database objects

**SHOULD.**

| Object | Convention | Example |
|---|---|---|
| Table | one convention per database, plural or singular, never mixed | `Users`, `TenantActivityLogs` |
| Primary key | `Id`, a sequential GUID or an identity column | `Id` |
| Foreign key | `{Role}Id` | `ActiveTenantId`, `CreatedById` |
| Audit columns | `UtcDateCreated`, `UtcDateModified`, `CreatedById`, `LastModifiedById` | |
| Constraints and indexes | tool defaults for `PK_`, `FK_` and `IX_`; checks as `CK_{Table}_{Column}` | `CK_Subscriptions_SeatCount` |
| Enum columns | strings with a bounded length | `nvarchar(50)` |
| Migrations | see NAME-07 | `AddUserLastLoginColumn` |

### NAME-13: Configuration and environments

**MUST.**

- Section names are PascalCase and match the settings class without its `Settings` suffix (`RedisCache` ↔ `RedisCacheSettings`). Keys are PascalCase (`InstanceName`).
- Connection strings are named after their database: `ConnectionStrings:AcmeDb`.
- Environment variables are UPPER_SNAKE_CASE (`IS_LOCAL`). Nested keys use a double underscore (`ConnectionStrings__AcmeDb`, `RedisCache__InstanceName`).
- Environment names come from one canonical list: `Development`, `Staging`, `UAT`, `Production`. File names use exactly the same spelling and case.
- Don't name a settings class `{X}Configuration` when your domain also has things called "configurations". The `Settings` suffix keeps the two apart.

### NAME-14: Wire and runtime identifiers

**SHOULD.**

| Identifier | Convention | Example |
|---|---|---|
| HTTP routes | lowercase resource nouns, hierarchical, parameters in braces | `configuration/{targetDomainName}/email`, `configuration/job/{jobId}` |
| Permission scopes | `Resource.Action` | `Configuration.Get`, `Configuration.Set`, `Job.Status` |
| Authorization policies | PascalCase, kept in a constants holder | `Policies.Admin`, `Policies.Customer` |
| Named HTTP clients | `nameof(IServiceInterface)` | `nameof(ISecurityCenterService)` |
| Keyed services | constants in one holder | `ServiceKeys.TenantContextualGraphClient` |
| Custom claim types | short, product-prefixed, in a constants holder | `AppClaimTypes.UserType = "app_utyp"` |
| Cache keys | colon-separated, most general first, always including the tenant | `{instance}:{tenantId}:{type}:{method}:{args}` |
| Log templates | constant text with PascalCase placeholders | `"Cache miss for {CacheKey}"` |
| Telemetry sources | PascalCase constants | `ActivitySourceName = "Migrations"` |

### NAME-15: Styles and static assets

**SHOULD.**

- CSS classes are kebab-case and prefixed by component, as `{prefix}-{component}-{element}[-{modifier}]`: `acme-progress-card-title`. Modifiers are semantic (`-good`, `-warning`, `-critical`), not presentational (`-green`).
- Design tokens are CSS custom properties named `--{prefix}-{palette}-{shade}`, as in `--acme-default-950`.
- Script modules are kebab-case with the product prefix: `acme-time.js`.
- Page components are named after their feature, and their routes use the kebab-case form (`SecurityCenter` → `/security-center`).

### NAME-16: Branches and commits

**SHOULD.**

- Name branches `{type}/{owner}/{workItemId}-{kebab-topic}`, where `{type}` is `feature`, `bugfix`, `hotfix` or `chore` and `{owner}` is lowercase. Example: `feature/{owner}/1234-add-tenant-allow-list`.
- The integration branch is `develop`, and work lands through pull requests.
- Commit and pull request titles are imperative and reference the work item, as in "Add tenant allow-list check (#1234)".
- **Don't:** Create branches without a type prefix, in PascalCase, or with snake_case topics.

### NAME-17: Tests

**MUST.**

- Test projects are `{Project}.UnitTests` and `{Project}.IntegrationTests`.
- Test classes are `{ClassUnderTest}Tests` and are sealed.
- Test methods are `{Method}_{Scenario}_{ExpectedResult}`, such as `SaveCompanyDetails_SaveThenGet_ReflectsSavedObject` or `DeleteEmailSecurityConfiguration_WhenNotFound_ReturnsZero`.
- **Don't:** Name a test class `Tests`, or use test names like `Test1` and `Works`.

### NAME-18: Casing across languages

**SHOULD.** Follow each language's native casing. The semantic rules above don't change.

| Element | C# / .NET | Java / Kotlin | TypeScript / JS | Python | Go | PowerShell |
|---|---|---|---|---|---|---|
| Repository | `acme-api` | `acme-api` | `acme-api` | `acme-api` | `acme-api` | `acme-automation` |
| Package or module | `Acme.Services.Billing` | `com.acme.services.billing` | `@acme/billing` | `acme.services.billing` | `acme/services/billing` | `Acme.Billing` module |
| File | `TenantService.cs` | `TenantService.java` / `.kt` | `tenant-service.ts` | `tenant_service.py` | `tenant_service.go` | `Get-Tenant.ps1` |
| Class or type | `TenantService` | `TenantService` | `TenantService` | `TenantService` | `TenantService` | `TenantService` |
| Interface | `ITenantService` | `TenantService`, implemented by `JpaTenantService` | `TenantService` (no `I`) | `TenantService(Protocol)` | `TenantStore`; `-er` for one method | — |
| Method or function | `GetTenantByIdAsync` | `getTenantById` | `getTenantById` | `get_tenant_by_id` | `TenantByID` | `Get-Tenant` (approved verb) |
| Property | `ActiveTenantId` | `activeTenantId` | `activeTenantId` | `active_tenant_id` | `ActiveTenantID` | `ActiveTenantId` |
| Private field | `_tenantRepository` | `tenantRepository` | `#tenantRepository` | `_tenant_repository` | `tenantRepository` | `$tenantRepository` |
| Constant | `SectionName` | `SECTION_NAME` | `SECTION_NAME` | `SECTION_NAME` | `SectionName` | `$SectionName` (read-only) |
| Enum member | `Active` | `ACTIVE` | `Active` | `ACTIVE` | `StatusActive` | `Active` |
| Parameter or local | `tenantId` | `tenantId` | `tenantId` | `tenant_id` | `tenantID` | `$TenantId` (parameter), `$tenantId` (local) |
| Async marker | `Async` suffix | none (`CompletableFuture`, `suspend`) | none (`Promise`) | none (`async def`) | none (`ctx` as first parameter) | none |
| Test file | `TenantServiceTests.cs` | `TenantServiceTest.java` | `tenant-service.test.ts` | `test_tenant_service.py` | `tenant_service_test.go` | `TenantService.Tests.ps1` |
| Test name | `Get_WhenMissing_ReturnsNull` | `get_whenMissing_returnsNull` | `'returns null when missing'` | `test_get_when_missing_returns_none` | `TestGet_WhenMissing` | `It 'returns null when missing'` |

---

## 6. Complexity budget

Low complexity is the main goal of this standard. These rules keep each unit small enough to read in one pass, and keep abstraction from growing faster than the problem.

### CPLX-01: Stay inside the budget

**MUST.** Every unit of code fits these limits. The limits are calibrated on the source codebase: its well-factored code already fits them, and the code it struggles with does not.

| Measure | Aim | Limit | Source codebase today |
|---|---|---|---|
| Function length | ≤ 20 lines | 30 | median 9 lines; 75th percentile 19; 90th percentile 31 |
| Cyclomatic complexity per function | ≤ 5 | 10 | |
| Cognitive complexity per function | ≤ 8 | 15 | |
| Nesting depth | ≤ 2 | 3 | |
| Parameters | ≤ 3 | 4, then a parameter object (CPLX-10) | |
| Constructor dependencies | ≤ 3 | 5 | median 2; 90th percentile 5 |
| Interface members | ≤ 7 | 10 | median 4 |
| Class or file with behavior | ≤ 200 lines | 300 | about 97% of files are under 300 lines |
| Services injected into a UI component | ≤ 3 | 5 | median 1; 90th percentile 5 |

- Exceeding a limit means splitting (CPLX-11) or writing down a deviation.
- Declarative code (schema maps, route tables, static catalogs) is exempt from the length limits while it stays declarative. Organize it per entity or feature so it stays findable.

### CPLX-02: Guard clauses and early returns

**MUST.** Validate inputs at the top, return early when there's nothing to do, and keep the main path at the left margin.

```csharp
public async Task<int> DeleteIdeaAsync(Guid ideaId)
{
    if (ideaId == Guid.Empty) throw new ArgumentException("Must be a non-empty id.", nameof(ideaId));

    await using var context = await _dbContextFactory.CreateDbContextAsync();
    var idea = await context.RoadmapIdeas.Include(i => i.Votes).FirstOrDefaultAsync(i => i.Id == ideaId);
    if (idea is null) return 0;

    context.RoadmapIdeaVotes.RemoveRange(idea.Votes);
    context.RoadmapIdeas.Remove(idea);
    return await context.SaveChangesAsync();
}
```

### CPLX-03: One level of abstraction per function

**SHOULD.** A coordinating function reads like a table of contents. Each line calls a well-named step, and the steps hold the detail.

```csharp
protected override async Task OnInitializedAsync()
{
    await Task.WhenAll(FetchExposureScoreAsync(), FetchSecureScoreAsync());

    await Task.WhenAll(
        FetchDevicesAsync(),
        FetchApplicationsAsync(),
        FetchVulnerabilitiesAsync(),
        FetchAccountRepresentativeAsync());
}
```

### CPLX-04: Map with data, not branches

**SHOULD.** Express a mapping as a switch expression or a lookup table, written once.

```csharp
private static Color GetVoteColor(RoadmapVote vote) => vote switch
{
    RoadmapVote.NiceToHave => Color.Success,
    RoadmapVote.Important  => Color.Primary,
    RoadmapVote.MustHave   => Color.Error,
    _                      => Color.Default,
};
```

- **Don't:** Map strings to values with an `if`/`else` ladder, or write the same mapping in two places. The second copy is a duplicated fact (CPLX-05).

### CPLX-05: Repeat structure; single-source facts

**MUST.** Code *shape* may repeat when each copy reads cleanly on its own and could evolve independently. Examples include two repository methods with the same query skeleton, sibling handlers with similar bodies, and per-entity schema blocks. *Facts* live in exactly one place: configuration keys, ids, URLs and scopes, product codes, business labels and thresholds, and key and claim formats.

- **Why:** Repeated structure costs a little reading. A repeated fact causes a bug on the day one copy changes and the other doesn't.
- **Test:** Ask "if this changes, must every copy change the same way?" If yes, it is a fact, so keep it in one place. If no, it is structure, and repetition is fine.

```csharp
// Structure may repeat: each method is complete on its own and free to diverge later.
public async Task<int> DeleteEmailConfigurationsByTenantIdAsync(Guid tenantId)
{
    await using var context = await _dbContextFactory.CreateDbContextAsync();
    var rows = await context.EmailConfigurations.Where(x => x.ActiveTenantId == tenantId).ToListAsync();
    context.EmailConfigurations.RemoveRange(rows);
    return await context.SaveChangesAsync();
}

public async Task<int> DeleteIdentityConfigurationsByTenantIdAsync(Guid tenantId)
{
    await using var context = await _dbContextFactory.CreateDbContextAsync();
    var rows = await context.IdentityConfigurations.Where(x => x.ActiveTenantId == tenantId).ToListAsync();
    context.IdentityConfigurations.RemoveRange(rows);
    return await context.SaveChangesAsync();
}
```

```csharp
// Don't: one fact, three copies. One of them will drift.
string[] adapterScopes = ["https://api.example.com/.default"];   // in the adapter registration
string[] warmerScopes  = ["https://api.example.com/.default"];   // in the cache warmer
const string BaseUrl   = "https://api.example.com/v1";            // hard-coded again in a client
```

### CPLX-06: Prefer duplication over the wrong abstraction

**MUST.** Extract a shared abstraction only when there are at least three real occurrences **and** they change for the same reason. When an existing abstraction starts growing flags, modes or optional parameters to serve callers that have drifted apart, inline it back into the callers and let them differ.

- **Why:** The wrong abstraction costs more than duplication. Every caller pays for every other caller's special cases, and removing the abstraction later is harder than never adding it.
- **Signs of a wrong abstraction:** Boolean or mode parameters that select code paths. Type parameters added "for flexibility". A base class whose subclasses override most of it. Callers that work around it.
- **Don't:** Write a generic `TokenProviderBase<TCredential, TTarget>` with six virtual hooks so that four authentication handlers can share forty lines. Four short handlers that each read top to bottom are cheaper.

### CPLX-07: An abstraction must pay rent

**MUST.** Every interface, base class, generic, layer or framework earns its place in one of three ways: it removes a real coupling, prevents a real class of bugs, or provides a test seam that tests actually use. Fewer lines alone don't count.

- **Defaults this implies:** No generic repository over an ORM; write explicit query methods instead. No mediator or command bus between an endpoint and the one service it calls. No interface for a DTO. No plug-in system for one plug-in.
- **Do:** Put interfaces at I/O and module boundaries (OOP-09), where a second implementation exists or tests substitute one: web versus worker context, real versus cached adapter.

### CPLX-08: Copy deliberately

**MUST.** When you repeat a block, re-read every line of the copy, including routes, entity sets, names, logger categories, keys and messages. Give each copy its own test.

- **Why:** Repetition is cheap. *Careless* repetition is the real hazard: a copied method that still calls the old endpoint, or a copied class that still logs under the original class's name.

```csharp
// Don't: the second method was copied and its route never updated.
public Task<List<Invoice>?> GetInvoicesAsync(string customerId) =>
    GetAsync<List<Invoice>>($"/customers/{customerId}/invoices");

public Task<List<Payment>?> GetPaymentsAsync(string customerId) =>
    GetAsync<List<Payment>>($"/customers/{customerId}/invoices");   // should be /payments
```

### CPLX-09: Straight-line async

**MUST.** Use plain `await` from top to bottom, and run independent I/O concurrently. Never block on async code, never chain `ContinueWith` with nested awaits, and never fire and forget. Don't write `async void`, except for framework event handlers that catch every exception.

- **Other stacks:** TypeScript uses `Promise.all` with the `no-floating-promises` lint rule. Python uses `asyncio.gather` or `TaskGroup`. Kotlin uses `coroutineScope { async { } }`. Go uses `errgroup`.

```csharp
// Do: independent calls run together
var totalTask  = GetTotalTicketCountAsync(organizationId);
var openTask   = GetOpenTicketCountAsync(organizationId);
var closedTask = GetClosedTicketCountAsync(organizationId);
await Task.WhenAll(totalTask, openTask, closedTask);
```

```csharp
// Don't
var token = await await _cache.GetStringAsync(key).ContinueWith(async t => { /* ... */ });  // nested and hard to cancel
_auditService.SaveAsync(entry);                                                                // not awaited, so errors vanish
var user = _authState.GetUserAsync().Result;                                                   // blocks a thread and can deadlock
```

### CPLX-10: Parameter objects after four parameters

**SHOULD.** A function with more than four parameters, or with parameters that always travel together, takes a named type instead (`StartTenantDriftJobRequest { TargetDomainName, ExpectedConfiguration }`). Name boolean arguments at the call site (`forceRefresh: true`).

### CPLX-11: Split by aggregate or role when over budget

**SHOULD.** When a class or interface exceeds CPLX-01, split it along a seam the domain already has: one service per aggregate, one component per page section, one adapter per group of remote resources. Don't split it into "Part1" and "Part2", or into a helper class.

- **Do:** A 25-member `IAccountService` becomes `IProfileService`, `IPreferencesService` and `IAccountStatusService`. An 800-line dashboard page becomes a page plus one component per card, and each card owns its data.
- **Don't:** Move half of a large class into a `*Helper` that takes the same dependencies.

### CPLX-12: Locality of behavior

**SHOULD.** Keep the code that determines a behavior close to where that behavior is visible. A component's logic sits beside its markup, a query sits inside the repository method that uses it, and a registration sits beside the module it registers. Prefer a few local, repeated lines over a jump to a distant helper.

### CPLX-13: You aren't gonna need it (YAGNI)

**MUST.** Build for today's requirement. Don't add speculative extension points, configuration flags that never have a second value, unused parameters or dependencies, or commented-out alternatives "for later". Version control remembers.

---

## 7. Errors and resilience

### ERR-01: Exceptions for broken invariants, with precise types

**MUST.** Throw `ArgumentException` or `ArgumentNullException` with `nameof(parameter)` for bad arguments, `InvalidOperationException` for invalid state, and a named exception for a domain condition (`UnauthorizedTenantException`). Never throw bare `Exception` or `ApplicationException`. Don't use `NotImplementedException` as the `default` branch of a closed set; use `ArgumentOutOfRangeException` or `UnreachableException`.

### ERR-02: Expected failures are values at integration edges

**SHOULD.** "Not found", "unavailable" and "rejected" are normal outcomes from an external system. Return them as values, either as a `Result<T>` or as a `Try…` method that returns null, and make that visible in the signature. Callers branch on them explicitly.

```csharp
public sealed record Result<T>(bool Success, T? Data = default, FailureReason? Reason = null)
{
    public static Result<T> Ok(T data) => new(true, data);
    public static Result<T> Failure(FailureReason reason) => new(false, Reason: reason);
}

public enum FailureReason { NotFound, BadRequest, Unavailable, Unknown }
```

### ERR-03: Never swallow an error

**MUST.** Every `catch` does one of three things: handles the error with a log entry that includes the exception object, translates it (ERR-04), or rethrows it. Write no empty catches. Don't `return null` without logging, and don't treat `Debug.WriteLine` as error handling.

```csharp
// Do
catch (HttpRequestException ex)
{
    _logger.LogError(ex, "Fetching devices failed for tenant {TenantId}", tenantId);
    return Result<List<Device>>.Failure(FailureReason.Unavailable);
}

// Don't
catch { }
catch (Exception ex) { _logger.LogError($"Error: {ex.Message} {ex.StackTrace}"); return null; }
```

### ERR-04: Translate exceptions at the edge

**SHOULD.** Typed domain exceptions travel up untouched and are translated once, at the boundary: into an HTTP status or problem details in an API, a redirect or message in a UI, or an exit code in a CLI.

```csharp
options.Events.OnRemoteFailure = context =>
{
    if (context.Failure is UnauthorizedTenantException)
    {
        context.Response.Redirect("/?error=UnauthorizedTenant");
        context.HandleResponse();
    }
    return Task.CompletedTask;
};
```

### ERR-05: Resilience belongs to the client pipeline

**MUST.** Configure retries, timeouts, circuit breakers and rate limits on the HTTP client, not as hand-written loops in business code. Tune them per client when you register it; for example, a long-running automation API gets a longer timeout. XCUT-02 shows the registration.

### ERR-06: Cache-aside with safety margins; never cache failures

**SHOULD.** Cache a token until a few minutes before it expires. Cache a result only when it isn't null. When a cache entry is corrupt, remove it and fetch again instead of passing it on. Cache keys are tenant-scoped (XCUT-05).

```csharp
var token = await _cache.GetStringAsync(cacheKey, cancellationToken);
if (token is not null) return token;

var result = await _tokenClient.AcquireTokenForClientAsync(scopes, cancellationToken);
await _cache.SetStringAsync(cacheKey, result.AccessToken,
    new DistributedCacheEntryOptions { AbsoluteExpiration = result.ExpiresOn.AddMinutes(-5) },
    cancellationToken);
return result.AccessToken;
```

---

## 8. Cross-cutting concerns

### XCUT-01: Structured logging with constant templates

**MUST.** Log with a constant message template and named placeholders. The logger category is the owning class (`ILogger<OwningClass>`). When logging an error, pass the exception object as the first argument.

- **Why:** Templates keep logs searchable and aggregatable by field. Interpolated strings defeat that, and they allocate memory even when the log level is off.
- **Do:** `_logger.LogInformation("Cache miss for {CacheKey}; calling {Service}", key, nameof(SecurityCenterService));`
- **Don't:** `_logger.LogInformation($"Cache miss for {key}");`. Never log secrets or whole tokens.
- **Other stacks:** SLF4J `{}` placeholders. Python `logger.info("Cache miss for %s", key)`, not f-strings. Structured objects with pino or winston.

### XCUT-02: Cross-cutting concerns live in pipelines

**MUST.** Business code never acquires tokens, sets authentication headers, retries or touches the cache directly. Pipeline handlers and decorators do that work.

```csharp
public sealed class ClientCredentialsHandler : DelegatingHandler
{
    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        var token = await GetAccessTokenAsync(cancellationToken);   // cache-aside, ERR-06
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        return await base.SendAsync(request, cancellationToken);
    }
}

services.AddHttpClient<ISecurityCenterService, SecurityCenterService>()
        .AddHttpMessageHandler<ClientCredentialsHandler>()
        .AddStandardResilienceHandler(o => o.TotalRequestTimeout.Timeout = TimeSpan.FromMinutes(10));
```

### XCUT-03: One mechanism per concern

**MUST.** Pick one caching mechanism (an explicit decorator or an attribute interceptor), one logging abstraction, one validation library and one HTTP client style. Document each choice in the repository README.

- **Why:** Two mechanisms for one concern double the debugging surface, and behavior then depends on which mechanism a method happened to get.
- **Do:** When in doubt, prefer the explicit mechanism (a decorator) over the implicit one (reflection-based interception), per guiding value 2.

### XCUT-04: Telemetry set up once, in shared defaults

**SHOULD.** A shared defaults module (`Acme.ServiceDefaults`) configures OpenTelemetry traces, metrics and logs, health checks, service discovery and HTTP client resilience. Every host calls it once (`builder.AddServiceDefaults()`). Expose health endpoints deliberately, because they leak information.

### XCUT-05: Tenancy scopes everything

**MUST.** In a multi-tenant system, every cache key, query, token and log scope includes the tenant. The key generator refuses to build a key without one, and tenant resolution happens in one place (ARCH-05).

```csharp
public string GetCacheKey(MethodInfo method, object[] args, string prefix)
{
    var tenantId = _userContext.GetActiveTenant();
    if (tenantId == Guid.Empty) throw new InvalidOperationException("Cache access requires an active tenant.");

    return $"{_settings.InstanceName}:{tenantId}:{_defaultGenerator.GetCacheKey(method, args, prefix)}";
}
```

---

## 9. Data and persistence

### DATA-01: One repository per aggregate, with explicit queries and no context

**MUST.** Each aggregate root has one sealed repository behind an interface. Each method is one explicit query or write, with no generic CRUD base class. Repositories don't resolve the current user or tenant; services pass them in (`Save…Async(configuration, actingUserId)`).

```csharp
public sealed class TenantRepository : ITenantRepository
{
    private readonly IDbContextFactory<AcmeDbContext> _dbContextFactory;

    public TenantRepository(IDbContextFactory<AcmeDbContext> dbContextFactory)
    {
        _dbContextFactory = dbContextFactory;
    }

    public async Task<EmailSecurityConfiguration?> GetLatestEmailSecurityConfigurationByTenantIdAsync(Guid tenantId)
    {
        await using var context = await _dbContextFactory.CreateDbContextAsync();
        return await context.EmailSecurityConfigurations
            .Where(x => x.ActiveTenantId == tenantId)
            .OrderByDescending(x => x.UtcDateCreated)
            .FirstOrDefaultAsync();
    }
}
```

The service is the front door. It resolves context and passes it down explicitly, and callers never use the repository directly:

```csharp
public async Task<int> SaveEmailSecurityConfigurationAsync(EmailSecurityConfiguration configuration, Guid tenantId)
{
    var currentUser = await _userService.GetCurrentUserAsync()
        ?? throw new InvalidOperationException("No authenticated user.");

    configuration.ActiveTenantId = tenantId;
    return await _tenantRepository.SaveEmailSecurityConfigurationAsync(configuration, currentUser.Id);
}
```

### DATA-02: One unit of work per operation

**MUST.** Each repository call creates a short-lived context or session from a factory, uses it and disposes of it. A long-lived context in a UI session or a singleton leaks memory, serves stale data and breaks under concurrency.

- **Other stacks:** A SQLAlchemy session per call, a JPA transaction per service method, or a Go `sql.Tx` per operation.

### DATA-03: Declarative, central schema

**SHOULD.** Declare keys, lengths, required flags, defaults, check constraints and delete behavior in the schema configuration. `Restrict` is the default delete behavior; cascade only where a child can't exist alone. Per-entity configuration blocks may repeat the same shape (CPLX-05). Once the file gets hard to navigate, split it into one configuration class or file per entity.

```csharp
modelBuilder.Entity<GuestAccessConfiguration>(entity =>
{
    entity.ToTable("GuestAccessConfigurations", t =>
        t.HasCheckConstraint("CK_GuestAccessConfigurations_InactivityDays", "[InactivityDays] >= 0"));

    entity.Property(e => e.Id).HasDefaultValueSql("newsequentialid()");
    entity.Property(e => e.InviterType).HasConversion<string>().HasMaxLength(50);

    entity.HasOne(e => e.LastModifiedBy).WithMany()
          .HasForeignKey(e => e.LastModifiedById)
          .OnDelete(DeleteBehavior.Restrict);
});
```

### DATA-04: Audit through base types; creators never change

**MUST.** Entities inherit their audit fields (OOP-03). Repositories set `UtcDateModified` and `LastModifiedById` on every write, and preserve `UtcDateCreated` and `CreatedById` on updates.

### DATA-05: Keep history by appending

**MAY.** Each save of a multi-step, user-authored configuration inserts a new row, and the current version is the latest by `UtcDateCreated`. This gives an audit trail and a baseline for drift detection at no extra cost. Pair it with a retention policy.

### DATA-06: Readable storage

**SHOULD.** Store enums as bounded-length strings unless volume demands integers, and store times in UTC. For a small multi-valued list, a delimited column with a value comparer, or a JSON column, is acceptable; document the delimiter once.

### DATA-07: Migrations are versioned code

**MUST.** Migrations are generated, reviewed and committed, with names that describe the change (`AddTenantTable`, `AddUserLastLoginColumn`). The pipeline or a migration worker applies them (ARCH-09); never apply them by hand to a shared environment.

### DATA-08: Null-safety stays on

**MUST.** Keep nullable analysis enabled in data models, and model optional relationships as explicitly nullable. Don't disable nullability per file to silence warnings.

---

## 10. APIs and integrations

### API-01: Thin endpoints

**MUST.** An endpoint declares its route, authorization scope and response contract, then delegates in one statement.

```csharp
[ApiController]
[Authorize]
[Route("configuration")]
public sealed class ConfigurationController : ControllerBase
{
    [HttpPost("drift")]
    [RequiredScope("Configuration.Drift")]
    [ProducesResponseType<JobResponse>(StatusCodes.Status200OK)]
    public async Task<ActionResult<JobResponse>> StartTenantDriftJobAsync([FromBody] StartTenantDriftJobRequest request) =>
        Ok(await _automationService.StartTenantDriftJobAsync(request.TargetDomainName, request.ExpectedConfiguration));

    [HttpGet("job/{jobId}")]
    [RequiredScope("Configuration.JobStatus")]
    [ProducesResponseType<JobDetails>(StatusCodes.Status200OK)]
    public async Task<ActionResult<JobDetails>> GetJobDetailsAsync(Guid jobId) =>
        Ok(await _automationService.GetJobDetailsAsync(jobId));
}
```

### API-02: Shared contracts and a typed client

**SHOULD.** Following ARCH-06, the client's methods mirror the endpoints one to one, and the client attaches authentication through a pipeline handler (XCUT-02).

### API-03: One adapter method per remote operation

**MUST.** An integration adapter maps each method to one remote operation. The base address, authentication and resilience come from the client pipeline, so each method is one line.

```csharp
public sealed class SecurityCenterService : ISecurityCenterService
{
    private readonly HttpClient _httpClient;

    public SecurityCenterService(IHttpClientFactory httpClientFactory)
    {
        _httpClient = httpClientFactory.CreateClient(nameof(ISecurityCenterService));
    }

    public Task<MachineResponse?> GetMachineByIdAsync(string machineId) =>
        _httpClient.TryGetFromJsonAsync<MachineResponse>($"/machines/{machineId}");

    public Task<MachineAlertsResponse?> GetAlertsByMachineIdAsync(string machineId) =>
        _httpClient.TryGetFromJsonAsync<MachineAlertsResponse>($"/machines/{machineId}/alerts");
}
```

### API-04: Anti-corruption layer at the boundary

**MUST.** Following OOP-01, small extension functions and lookup tables translate vendor fields into domain values. Nothing outside the adapter module references vendor types.

### API-05: Explicit contracts; jobs for long operations

**SHOULD.** Declare the response types and status codes of every endpoint, so OpenAPI documentation stays accurate. Long operations follow ARCH-10.

### API-06: Endpoints, scopes and base URLs are configuration

**MUST.** Never hard-code environment-specific hosts or scopes. Bind them from settings per environment (ARCH-07).

---

## 11. UI components

These rules apply to any component framework, such as Blazor, React, Angular or Vue.

### UI-01: Separate template from behavior

**SHOULD.** A component's markup and its logic live in separate files: `Component.razor` and `Component.razor.cs` as a partial class.

- **Other stacks:** A React component plus a hook, an Angular template plus a class, or a Vue `<template>` plus `<script setup>` composables.

### UI-02: Design-system components

**SHOULD.** Reusable visual components share one prefix (`AcmeCardContainer`, `AcmeProgressCard`, `AcmeChip`). They take inputs as parameters, compose through slots (`ChildContent`) and fetch no data.

```csharp
public partial class AcmeCardContainer : ComponentBase
{
    [Parameter] public string Title { get; set; } = string.Empty;
    [Parameter] public RenderFragment? ChildContent { get; set; }
}
```

### UI-03: Progressive, parallel loading with skeletons

**SHOULD.** Each section that loads asynchronously has its own loading flag and skeleton component. Independent sections load in parallel (CPLX-03) and render as soon as their own data arrives.

```csharp
private async Task FetchDevicesAsync()
{
    Devices = await _deviceService.GetDevicesAsync();
    IsLoadingDevices = false;
    await InvokeAsync(StateHasChanged);
}
```

```razor
@if (IsLoadingDevices)
{
    <DeviceSummarySkeleton />
}
else
{
    <AcmeDeviceSummary Devices="Devices" />
}
```

### UI-04: Dialogs are components that return results

**SHOULD.** A `*Dialog` component receives parameters and returns a typed result when it closes, and the opener awaits that result. A dialog doesn't reach into the opener's state.

### UI-05: Form models aren't entities

**MUST.** Input models carry validation attributes that mirror the storage limits, and the service maps them to entities.

```csharp
public sealed class RoadmapIdeaForm
{
    [Required, StringLength(50)]  public string Title { get; set; } = string.Empty;   // matches HasMaxLength(50)
    [Required, StringLength(300)] public string Body  { get; set; } = string.Empty;   // matches HasMaxLength(300)
    [Required] public RoadmapArea? Area { get; set; }
}
```

### UI-06: Wizards: the parent owns the model, and steps have names

**SHOULD.** The wizard page owns the model and passes it to step components through a cascading parameter or context. Each step validates its own inputs. Progress (`ActiveStep`, `IsComplete`) is saved so users can resume. Code refers to steps by name or enum, never by a magic index.

- **Don't:** Write `switch (targetIndex) { case 7: …; case 8: … }`, or busy-wait for the stepper to render.

### UI-07: Pages orchestrate; they don't compute

**SHOULD.** A page wires sections together, and calculations live in services or view-model classes. The budget is at most five injected services (CPLX-01). Beyond that, add a page-level service as a facade, or split the page into sections that own their data.

### UI-08: Lifecycle hygiene

**MUST.** Unsubscribe from events and dispose of subscriptions. Don't busy-wait (`while (!ready) await Task.Delay(100)`); use the framework's lifecycle hooks. Don't write `async void`, except for event handlers that catch every exception. Import JavaScript interop modules once and dispose of them.

```csharp
public sealed partial class Overview : ComponentBase, IDisposable
{
    protected override void OnInitialized() => _userContext.TenantChanged += HandleTenantChanged;

    private async void HandleTenantChanged(object? sender, TenantChangedEventArgs e)
    {
        try
        {
            await InvokeAsync(ReloadAsync);
        }
        catch (Exception ex)   // event-handler boundary: log, never rethrow into the renderer
        {
            _logger.LogError(ex, "Reload after tenant change failed for {TenantId}", e.NewTenantId);
        }
    }

    public void Dispose() => _userContext.TenantChanged -= HandleTenantChanged;
}
```

### UI-09: Scoped styles and design tokens

**SHOULD.** Component styles live in component-scoped files (`Component.razor.css`, or CSS modules) and use design tokens (`--acme-surface-950`). Class names follow NAME-15. Don't repeat `<style>` blocks inside markup.

---

## 12. Security

### SEC-01: Policy-based authorization

**MUST.** Authorization uses named policies built from requirements and handlers. Roles are flags that can be combined, and policy names live in one constants holder.

```csharp
[Flags]
public enum AuthorizationFlags { None = 0, Admin = 1, Customer = 2, Internal = 4, Debug = 8 }

services.AddAuthorization(options =>
{
    options.AddPolicy(Policies.Customer, p => p.Requirements.Add(new ValidUserRequirement(AuthorizationFlags.Customer)));
    options.AddPolicy(Policies.Admin,    p => p.Requirements.Add(new ValidUserRequirement(AuthorizationFlags.Admin)));
    options.AddPolicy(Policies.Debug,    p => p.Requirements.Add(new ValidUserRequirement(AuthorizationFlags.Debug | AuthorizationFlags.Internal)));
    options.FallbackPolicy = new AuthorizationPolicyBuilder().RequireAuthenticatedUser().Build();   // SEC-07
});
services.AddSingleton<IAuthorizationHandler, ValidUserHandler>();
```

### SEC-02: Enrich identity once, at sign-in

**SHOULD.** When the token is validated, map the user to internal roles and claims once (for example, `app_utyp` set to `Customer`, `Internal` or `Admin`). Everywhere else, query them through typed helpers (`user.IsAdmin()`, `user.GetHomeTenantId()`) instead of parsing raw claims again.

### SEC-03: Allow-lists from data or configuration

**SHOULD.** Access by tenant or organization is an allow-list, kept in a database table with a configuration override and checked at sign-in. A rejection is a typed exception translated at the edge (ERR-04).

### SEC-04: Authorize where state changes

**MUST.** Every command that changes who can access what, such as switching tenant or granting a permission, checks authorization itself. Filtering a dropdown in the UI is not authorization.

### SEC-05: No hard-coded identities

**MUST.** Don't put email addresses, user ids or tenant ids in conditionals. Use roles and policies, allow-lists in configuration, or feature flags.

### SEC-06: Secrets come from a secret store

**MUST.** Secrets come from a vault or secret manager, or from git-ignored local files. They are never committed and never logged. Encrypt token caches that live in shared infrastructure.

### SEC-07: Authenticated by default

**MUST.** APIs require authentication globally through a fallback policy. An anonymous endpoint is an explicit, reviewed opt-out. Exclude diagnostic and test endpoints from production builds, or protect them like every other endpoint.

---

## 13. Testing

### TEST-01: A test project per module

**SHOULD.** Each module has a `{Project}.UnitTests` project, plus `.IntegrationTests` where needed, that mirrors its folders. CI runs every project whose name ends in `Tests`.

### TEST-02: Names and shape

**MUST.** Name each test `Method_Scenario_Expected` (NAME-17) and give it Arrange, Act and Assert sections. A test checks one behavior; group related assertions with `Assert.Multiple`.

```csharp
[TestFixture]
public sealed class TenantRepositoryTests
{
    [Test]
    public async Task SaveCompanyDetails_SaveThenGet_ReflectsSavedObject()
    {
        // Arrange
        var factory = CreateInMemoryDbContextFactory(databaseName: Guid.NewGuid().ToString());   // isolated store per test
        var repository = new TenantRepository(factory);
        var details = _fixture.Build<CompanyDetails>().Without(d => d.LastModifiedBy).Create();

        // Act
        await repository.SaveCompanyDetailsAsync(details, actingUserId);
        var saved = await repository.GetCompanyDetailsByTenantIdAsync(details.TenantId);

        // Assert
        Assert.That(saved?.PrimaryContactFirstName, Is.EqualTo(details.PrimaryContactFirstName));
    }
}
```

### TEST-03: Isolation

**MUST.** Each test gets fresh state, such as an in-memory database named with a new GUID. Tests don't depend on run order, and there are no shared mutable statics.

### TEST-04: Builders, and mocks only at I/O seams

**SHOULD.** Generate incidental data with builders or fixtures, excluding navigation properties explicitly. Auto-mock incidental dependencies, and mock only at I/O seams (OOP-09). Never mock the class under test or a value object.

### TEST-05: Test what breaks

**SHOULD.** Test in this order of priority:

1. Business rules in services.
2. Repository round trips, such as save-then-get, and delete returning zero when the item is missing.
3. Boundary translators: anti-corruption layers and mapping tables.
4. Each copy of repeated code (CPLX-08).
5. UI logic extracted from components.

---

## 14. Code hygiene

### HYG-01: No commented-out code or dead branches

**MUST.** Delete it, because version control remembers. This includes `if (false)` and `if (true)` blocks and unused private methods.

### HYG-02: TODOs reference a work item

**SHOULD.** Write `// TODO(#1234): handle drift`. A TODO without a work item is not a plan, it's litter.

### HYG-03: Remove what is unused

**MUST.** Remove unused imports, parameters, fields and injected dependencies, such as a logger that is injected but never used. They mislead readers about what a class depends on.

### HYG-04: One style, enforced by configuration

**MUST.** Enforce formatting and naming with `.editorconfig`, formatter and linter configuration checked into the repository and run in CI (appendix C), not with review comments. Use one namespace form, one brace style and one async naming rule.

### HYG-05: Regions don't replace splitting

**SHOULD.** If a class needs `#region` blocks or folding markers to be navigable, it is over budget (CPLX-01). Split it.

### HYG-06: Names match their owners

**MUST.** The file name equals the type name. The logger category is the class that logs. The HTTP client name is the interface that uses it. The test class is the class under test plus `Tests`.

---

## 15. Refactoring playbook

Apply the standard to an existing codebase in this order. Each step can ship on its own.

1. **Map the boundaries.** Draw the current projects, modules and hosts against section 2. List every upward or sideways dependency, every business rule that lives in a host, and every module that reads host state (ARCH-01, ARCH-04, ARCH-05). This list is the backbone of the backlog.
2. **Characterize before changing.** Pin the current behavior of anything you will touch with tests at its seams (TEST-05). Refactoring without tests is rewriting.
3. **Measure in report-only mode.** Enable the analyzers in appendix C as warnings and record a count per rule. Add a CI check that fails only when a count goes up.
4. **Keep each fact in one place.** That covers configuration keys, URLs and scopes, ids, product catalogs and labels (CPLX-05). This step has the highest bug yield and the lowest risk.
5. **Fix async, error and logging hygiene.** Remove `async void`, fire-and-forget calls, blocking waits, swallowed exceptions and interpolated logs (CPLX-09, ERR-03, XCUT-01). These fixes are mechanical and remove whole classes of production incidents.
6. **Thin the edges.** Move logic out of endpoints, pages and `Program`/`main` into services (API-01, UI-07). Make each adapter one method per remote operation (API-03). Move registrations into module installers (ARCH-03).
7. **Split what is over budget** along its existing seams: by aggregate, role or screen section (CPLX-11).
8. **Leave structural repetition alone** unless the copies change together (CPLX-06). Don't turn "similar" into "shared" during a cleanup.
9. **Ratchet.** Promote each rule from warning to error once its count reaches zero.

---

## Appendix A. Rule index

109 rules: 60 MUST, 47 SHOULD, 2 MAY.

| ID | Rule | Level |
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
| OOP-15 | GRASP at a glance | MAY |
| OOP-16 | Patterns in use | SHOULD |
| NAME-01 | General rules | MUST |
| NAME-02 | Repository and solution | SHOULD |
| NAME-03 | Solution folders | SHOULD |
| NAME-04 | Projects and packages | MUST |
| NAME-05 | Folders inside a project | SHOULD |
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
| NAME-18 | Casing across languages | SHOULD |
| CPLX-01 | Stay inside the budget | MUST |
| CPLX-02 | Guard clauses and early returns | MUST |
| CPLX-03 | One level of abstraction per function | SHOULD |
| CPLX-04 | Map with data, not branches | SHOULD |
| CPLX-05 | Repeat structure; single-source facts | MUST |
| CPLX-06 | Prefer duplication over the wrong abstraction | MUST |
| CPLX-07 | An abstraction must pay rent | MUST |
| CPLX-08 | Copy deliberately | MUST |
| CPLX-09 | Straight-line async | MUST |
| CPLX-10 | Parameter objects after four parameters | SHOULD |
| CPLX-11 | Split by aggregate or role when over budget | SHOULD |
| CPLX-12 | Locality of behavior | SHOULD |
| CPLX-13 | You aren't gonna need it (YAGNI) | MUST |
| ERR-01 | Exceptions for broken invariants, with precise types | MUST |
| ERR-02 | Expected failures are values at integration edges | SHOULD |
| ERR-03 | Never swallow an error | MUST |
| ERR-04 | Translate exceptions at the edge | SHOULD |
| ERR-05 | Resilience belongs to the client pipeline | MUST |
| ERR-06 | Cache-aside with safety margins; never cache failures | SHOULD |
| XCUT-01 | Structured logging with constant templates | MUST |
| XCUT-02 | Cross-cutting concerns live in pipelines | MUST |
| XCUT-03 | One mechanism per concern | MUST |
| XCUT-04 | Telemetry set up once, in shared defaults | SHOULD |
| XCUT-05 | Tenancy scopes everything | MUST |
| DATA-01 | One repository per aggregate, with explicit queries and no context | MUST |
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
| API-06 | Endpoints, scopes and base URLs are configuration | MUST |
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

## Appendix B. Pull request checklist

**Boundaries**

- [ ] New code sits in the right layer and module, with no upward or sideways references (ARCH-01, ARCH-02).
- [ ] New services are registered in their module's installer, not in a host (ARCH-03).
- [ ] No module reads host state; context comes from the user-context interface (ARCH-05).

**Design**

- [ ] Each new class has one reason to change and fits the budget (OOP-05, CPLX-01).
- [ ] Every new interface, base class or generic pays rent (CPLX-07).
- [ ] Any repetition repeats structure, not facts, and each copy was re-read and tested (CPLX-05, CPLX-08).
- [ ] Commands and queries are separate, and names match behavior (OOP-12, OOP-13).

**Naming**

- [ ] Names follow the role-suffix and verb vocabularies, the file name equals the type name, and the namespace matches the folder (NAME-04 to NAME-09).
- [ ] No abbreviations, mixed acronym casing or names starting with digits (NAME-01).

**Errors, async and logging**

- [ ] No swallowed exceptions; errors are logged with the exception object (ERR-03).
- [ ] No `async void`, fire-and-forget calls or blocking waits; independent I/O runs in parallel (CPLX-09).
- [ ] Logs use constant templates and contain no secrets (XCUT-01).

**Data and APIs**

- [ ] Repositories carry no context and use one unit of work per call (DATA-01, DATA-02).
- [ ] Schema changes come with a reviewed migration (DATA-07).
- [ ] Endpoints are thin and declare a scope and a response contract; URLs and scopes come from configuration (API-01, API-05, API-06).

**Security**

- [ ] Authorization is enforced where state changes, not only in the UI (SEC-04).
- [ ] No hard-coded identities or secrets (SEC-05, SEC-06).
- [ ] New endpoints are authenticated unless an anonymous exception was reviewed (SEC-07).

**UI**

- [ ] Each asynchronous section has a loading state and a skeleton, and the page injects at most five services (UI-03, UI-07).
- [ ] Subscriptions are disposed of, and nothing busy-waits (UI-08).

**Tests and hygiene**

- [ ] Tests are named `Method_Scenario_Expected`, are isolated, and cover the new rule or copy (TEST-02, TEST-03, TEST-05).
- [ ] No commented-out code, dead branches, unused imports or unused dependencies, and every TODO references a work item (HYG-01 to HYG-03).

## Appendix C. Enforcement tools

Start every rule in report-only mode and promote it to an error once its count reaches zero (section 15). A dash means no common built-in rule; cover those rules in review.

| Rule | .NET | TypeScript / JS | Python (Ruff) | Java / Kotlin | Go (golangci-lint) | PowerShell (PSScriptAnalyzer) |
|---|---|---|---|---|---|---|
| CPLX-01 size and complexity | CA1502, CA1505, CA1506 (code metrics); SonarQube S3776 | `complexity`, `max-depth`, `max-lines-per-function`, `max-params`, `max-lines` | `C901`, `PLR0912`, `PLR0913`, `PLR0915` | Checkstyle `CyclomaticComplexity`, `MethodLength`, `ParameterNumber`; PMD `CognitiveComplexity`, `GodClass`; detekt `LongMethod`, `CyclomaticComplexMethod`, `LongParameterList`, `LargeClass` | `gocyclo`, `gocognit`, `funlen`, `nestif` | — |
| OOP-03 inheritance depth | CA1501 | — | — | — | — | — |
| CPLX-05 magic values | SonarQube S109 | `no-magic-numbers` | `PLR2004` | Checkstyle `MagicNumber`; detekt `MagicNumber` | `mnd` | — |
| CPLX-09, UI-08 async hygiene | VSTHRD100, VSTHRD110, VSTHRD002, CS4014 | `@typescript-eslint/no-floating-promises`, `@typescript-eslint/no-misused-promises` | `RUF006` | — | — | — |
| ERR-03 swallowed errors | CA1031 | `no-empty` | `BLE001`, `S110` | PMD `AvoidCatchingGenericException`, `EmptyCatchBlock`; detekt `TooGenericExceptionCaught`, `SwallowedException` | `errcheck` | `PSAvoidUsingEmptyCatchBlock` |
| XCUT-01 structured logging | CA2254, CA1848 | — | `G004` | — | — | — |
| NAME rules | IDE1006 with `.editorconfig` naming rules; StyleCop SA1649, SA1402 | `@typescript-eslint/naming-convention` | `N` (pep8-naming) | Checkstyle naming checks and `OuterTypeFilename`; detekt naming rules | `revive` | `PSUseApprovedVerbs`, `PSUseSingularNouns` |
| NAME-06 namespace form | IDE0161 | — | — | — | — | — |
| HYG-01 commented-out code | SonarQube S125 | SonarQube S125 | `ERA001` | SonarQube S125 | — | — |
| HYG-03 unused code | IDE0005, IDE0051, IDE0052, IDE0060 | `@typescript-eslint/no-unused-vars` | `F401`, `F841` | PMD `UnusedPrivateField`; detekt `UnusedImports`, `UnusedPrivateMember` | compiler errors, `unused` | `PSUseDeclaredVarsMoreThanAssignments` |
| SEC-06 secrets | secret scanning in CI | secret scanning in CI | secret scanning in CI | secret scanning in CI | secret scanning in CI | `PSAvoidUsingPlainTextForPassword` |

## Appendix D. Mechanisms across stacks

The rules name .NET mechanisms. This table gives the usual equivalent in other application stacks. PowerShell scripts follow the naming and hygiene rules.

| Mechanism | .NET | Java / Kotlin | TypeScript / Node | Python | Go |
|---|---|---|---|---|---|
| Module installer (ARCH-03) | `IServiceCollection` extension `AddXxx()` | Spring `@Configuration` class | NestJS module, or a `registerXxx(container)` function | `configure(container)` with dependency-injector, or FastAPI dependencies | constructor functions wired in `main`, optionally with Wire |
| Ambient context (ARCH-05) | scoped `IUserContext` | request-scoped bean | `AsyncLocalStorage` behind an interface | `contextvars` behind a `Protocol` | `context.Context` plus a typed accessor |
| Outbound pipeline (XCUT-02) | `DelegatingHandler` plus `IHttpClientFactory` | `ClientHttpRequestInterceptor`; WebClient `ExchangeFilterFunction` | fetch or axios interceptors | httpx event hooks or a custom transport | `http.RoundTripper` wrapper |
| Inbound middleware | ASP.NET Core middleware | servlet filter; `HandlerInterceptor` | Express, Koa or NestJS middleware | ASGI or WSGI middleware | `func(http.Handler) http.Handler` |
| Unit of work per call (DATA-02) | `IDbContextFactory<T>` | `@Transactional` service method | ORM transaction per call (Prisma, TypeORM) | SQLAlchemy `sessionmaker` per call | `sql.Tx` per call |
| Extension functions | static `{Type}Extensions` class | Kotlin extension functions; a Java static utility per type | module functions | module functions | functions in the type's package |
| Decorator (OOP-06) | decorator class (Scrutor `Decorate`) | decorator bean or Spring AOP | class decorator or higher-order function | `functools.wraps` decorator or wrapper class | wrapper struct implementing the interface |
| Typed settings (ARCH-07) | options pattern with `SectionName` | `@ConfigurationProperties` | zod-validated config object | pydantic-settings `BaseSettings` | struct plus envconfig |
| Immutable data carriers (OOP-14) | `record`, `init` | Java `record`; Kotlin `data class` with `val` | `readonly` types | `@dataclass(frozen=True)` | value structs |
| Expected failures (ERR-02) | `Result<T>` | sealed result types | discriminated unions | result dataclass | `(T, error)` returns |
| Policy authorization (SEC-01) | requirements plus handlers | Spring Security `@PreAuthorize` | NestJS guards; CASL | FastAPI dependencies; Casbin | middleware plus policy functions |
| Null-safety (DATA-08) | nullable reference types | Kotlin nullability; `Optional` | `strictNullChecks` | type hints with mypy or pyright in strict mode | explicit `ok` returns |
