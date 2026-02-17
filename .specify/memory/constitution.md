<!--
  Sync Impact Report
  ==================
  Version change: 1.0.0 → 1.1.0 (MINOR — new principle added)
  Modified principles: None renamed or redefined
  Added sections:
    - Principle V: Security & Access Control
  Removed sections: None
  Templates requiring updates:
    - .specify/templates/plan-template.md ✅ no updates needed (generic Constitution Check section)
    - .specify/templates/spec-template.md ✅ no updates needed (generic structure)
    - .specify/templates/tasks-template.md ✅ no updates needed (generic structure)
  Follow-up TODOs: None

  Prior history:
    1.0.0 (2026-02-17): Initial ratification with 4 principles
      (DDD, TDD, UX Consistency, Performance), Technical Standards,
      Quality Gates, Governance.
-->

# Global Military MCP Server Constitution

## Core Principles

### I. Domain-Driven Design (DDD)

All code MUST be organized around clearly defined domain boundaries
and ubiquitous language. This principle governs structural quality
and long-term maintainability of the codebase.

- **Bounded Contexts**: Every module MUST represent a single bounded
  context with explicit boundaries. Cross-context communication MUST
  occur through well-defined interfaces (anti-corruption layers,
  published language, or shared kernel) — never direct internal
  access.
- **Ubiquitous Language**: Domain terminology used in code (class
  names, method names, variables) MUST mirror the language used by
  domain experts and documentation. Ambiguous or generic naming
  (e.g., `Manager`, `Helper`, `Utils`) is prohibited for domain
  logic.
- **Aggregates & Entities**: Domain objects MUST enforce their own
  invariants. Aggregates MUST be the sole entry point for modifying
  enclosed entities. No external code may directly mutate aggregate
  internals.
- **Value Objects**: Immutable value objects MUST be used for domain
  concepts that lack identity (e.g., coordinates, classifications,
  measurement units). Primitive obsession (raw strings/numbers for
  domain concepts) is prohibited.
- **Domain Services**: Operations that do not naturally belong to a
  single entity or value object MUST be expressed as domain services
  with clear, verb-based naming that reflects the operation's intent.
- **Infrastructure Separation**: Domain logic MUST have zero
  dependencies on infrastructure concerns (databases, HTTP, file I/O).
  The dependency arrow MUST always point inward — infrastructure
  depends on domain, never the reverse.

**Rationale**: DDD ensures the codebase remains aligned with the
problem domain, reduces accidental complexity, and enables teams to
reason about behavior in domain terms rather than technical
implementation details.

### II. Test-Driven Development (TDD)

All production code MUST be written following the TDD cycle. This
principle is **NON-NEGOTIABLE** and governs correctness, design
feedback, and regression safety.

- **Red-Green-Refactor**: Every feature MUST follow this cycle
  strictly: (1) write a failing test that defines desired behavior,
  (2) write the minimum code to make the test pass, (3) refactor
  while keeping tests green. Skipping the red phase is a violation.
- **Test-First Contract**: Tests MUST be written and reviewed before
  implementation begins. No implementation PR may be opened without
  corresponding tests already merged or included.
- **Test Granularity**:
  - **Unit tests**: MUST cover all domain logic (aggregates, value
    objects, domain services). Target: 100% branch coverage of domain
    layer.
  - **Integration tests**: MUST cover all boundary crossings
    (repository implementations, external API adapters, MCP tool
    handlers).
  - **Contract tests**: MUST verify MCP protocol compliance for every
    exposed tool and resource endpoint.
- **Test Independence**: Each test MUST be independently runnable with
  no reliance on execution order or shared mutable state.
- **Naming Convention**: Test names MUST follow the pattern
  `[unit_under_test]_[scenario]_[expected_behavior]` to serve as
  living documentation.
- **No Test Pollution**: Test utilities and fixtures MUST NOT leak
  into production code paths. Test dependencies MUST be isolated to
  test-only configurations.

**Rationale**: TDD produces code that is correct by construction,
provides immediate feedback on design quality (hard-to-test code
signals poor design), and builds a comprehensive regression safety
net that enables confident refactoring.

### III. User Experience Consistency

All MCP tools, resources, and prompts exposed by this server MUST
deliver a consistent, predictable experience to consuming agents and
end users. This principle governs interface design and interaction
patterns.

- **Uniform Response Structure**: All tool responses MUST follow a
  single, documented response schema. Error responses MUST use a
  consistent error format with machine-readable error codes and
  human-readable messages.
- **Naming Conventions**: Tool names, parameter names, and resource
  URIs MUST follow a consistent naming scheme (snake_case for tools
  and parameters, hierarchical URIs for resources). Abbreviations
  MUST be documented in a project glossary or avoided entirely.
- **Input Validation & Feedback**: All tool inputs MUST be validated
  with descriptive error messages that identify the invalid field,
  the constraint violated, and the expected format. Silent failures
  are prohibited.
- **Progressive Disclosure**: Complex operations MUST support
  sensible defaults so that minimal input yields useful results,
  while advanced parameters remain available for fine-grained control.
- **Idempotency**: Read operations MUST be idempotent. Write
  operations MUST document their idempotency guarantees explicitly.
  Callers MUST be able to safely retry any operation that declares
  itself idempotent.
- **Documentation Parity**: Every tool and resource MUST have a
  description that matches its actual behavior. Descriptions MUST be
  updated in the same PR that changes behavior — no drift permitted.

**Rationale**: MCP consumers (AI agents and human users) rely on
predictable patterns to compose tools into workflows. Inconsistency
forces callers to handle special cases, increases integration errors,
and degrades trust in the server's reliability.

### IV. Performance & Reliability

All server operations MUST meet defined performance targets and
degrade gracefully under adverse conditions. This principle governs
responsiveness, resource efficiency, and operational resilience.

- **Response Time Budgets**:
  - Tool invocations MUST respond within 500ms at p95 for
    computation-bound operations.
  - Operations involving external I/O MUST respond within 2000ms at
    p95, with timeout thresholds documented per tool.
  - Any operation exceeding 5000ms MUST support progress reporting
    or asynchronous completion patterns.
- **Resource Efficiency**: Memory allocation per request MUST NOT
  exceed documented limits. Connection pools, caches, and buffers
  MUST have explicit size bounds and eviction policies.
- **Graceful Degradation**: When downstream dependencies are
  unavailable, the server MUST return meaningful error responses
  (not hang or crash). Circuit-breaker patterns MUST be applied to
  all external service calls.
- **Concurrency Safety**: All shared state MUST be protected by
  appropriate concurrency primitives. Race conditions detected in
  testing or review MUST block merge.
- **Observability**: All operations MUST emit structured logs with
  correlation IDs. Latency metrics MUST be collected for every tool
  invocation. Health-check endpoints MUST report dependency status.
- **Capacity Planning**: Load test results MUST be documented for
  each release. Regressions exceeding 10% on any latency percentile
  MUST be investigated and resolved before release.

**Rationale**: An MCP server is infrastructure that agents depend on
for real-time decision-making. Slow or unreliable responses cascade
into degraded agent performance, timeout failures, and poor user
outcomes.

### V. Security & Access Control

All data, operations, and communication channels MUST be secured
commensurate with the military domain's sensitivity requirements.
This principle is **NON-NEGOTIABLE** and governs authentication,
authorization, data protection, and auditability.

- **Authentication & Authorization**: Every tool and resource
  invocation MUST enforce identity verification. Role-based access
  control (RBAC) MUST gate every operation. Anonymous or
  unauthenticated access is prohibited for all endpoints.
- **Principle of Least Privilege**: Tools MUST request and expose
  only the minimum data and permissions required for the operation.
  Over-fetching or returning data beyond the caller's authorization
  scope is a security violation.
- **Audit Trail**: Every state-changing operation MUST produce an
  immutable, tamper-evident audit log entry containing: actor
  identity, timestamp (UTC), operation identifier, input summary,
  and outcome (success/failure with error code). Audit logs MUST be
  retained per the project's data retention policy.
- **Data Classification**: All inputs and outputs MUST respect
  classification levels. Tools MUST NOT leak higher-classification
  data into lower-classification responses. Classification
  boundaries MUST be enforced programmatically, not by convention.
- **Defense in Depth**: Input validation MUST occur at every layer
  boundary (transport, application, domain). Domain logic MUST NOT
  trust that infrastructure layers have already validated inputs.
  All inter-service communication MUST use encrypted channels
  (TLS 1.3 minimum).
- **Secure Defaults**: All configurations MUST default to the most
  restrictive setting. Relaxations MUST be explicit, documented,
  and approved through the governance amendment process. Default
  deny policies MUST apply to all access control decisions.
- **Secret Management**: Credentials, tokens, and keys MUST be
  managed through a dedicated secrets manager. Secrets MUST NOT
  appear in source code, configuration files, logs, or error
  messages. Secret rotation MUST be supported without downtime.

**Rationale**: A military-domain MCP server handles operationally
sensitive data where unauthorized access or data leakage constitutes
a mission-critical failure. Security cannot be an afterthought or a
technical-standards bullet — it requires principle-level enforcement
to ensure every design decision, code review, and deployment
considers security implications from the outset.

## Technical Standards

Additional constraints that apply across all principles:

- **Language & Runtime**: The project's language and runtime version
  MUST be pinned in configuration files. All contributors MUST use
  the same version.
- **Dependency Management**: All dependencies MUST be version-pinned.
  New dependencies MUST be justified in the PR description with
  rationale for selection over alternatives. Transitive dependency
  audits MUST be performed on each update.
- **Code Formatting**: An automated formatter MUST be configured and
  enforced in CI. No unformatted code may be merged.
- **Linting**: Static analysis MUST run in CI with zero tolerance for
  warnings in domain and application layers. Suppressions MUST
  include an inline justification comment.
- **Security**: Governed by Principle V. Dependency vulnerability
  scans MUST run on every PR. Static application security testing
  (SAST) MUST be included in CI.
- **MCP Protocol Compliance**: The server MUST conform to the MCP
  specification version declared in project configuration. Protocol
  version upgrades MUST be treated as breaking changes and follow
  the governance amendment process.

## Quality Gates

All changes MUST pass through these gates before merge:

- **PR Review**: Every PR MUST be reviewed by at least one other
  contributor. The reviewer MUST verify constitutional compliance
  as part of the review checklist.
- **CI Pipeline**: The following checks MUST pass:
  1. All unit, integration, and contract tests green.
  2. Code coverage MUST NOT decrease from the prior release baseline.
  3. Linting and formatting checks pass with zero violations.
  4. Dependency vulnerability scan reports no critical/high findings.
  5. Build completes without warnings.
- **Definition of Done**: A task is complete only when:
  - Tests written (TDD red phase) and passing (green phase).
  - Code refactored to meet DDD structural standards.
  - Documentation updated (tool descriptions, README, changelogs).
  - Performance budget verified (no p95 regressions).
  - Security review passed (no new auth gaps, audit logging verified).
  - PR approved and merged to the target branch.

## Governance

This constitution is the supreme governance document for the Global
Military MCP Server project. All development practices, code reviews,
and architectural decisions MUST comply with the principles defined
herein.

- **Supremacy**: Where conflicts arise between this constitution and
  any other project document, this constitution takes precedence.
- **Amendment Procedure**: Amendments MUST be proposed as a dedicated
  PR modifying this file. The PR description MUST include: (1) the
  specific change, (2) rationale, (3) impact assessment on existing
  code, and (4) a migration plan if the change is backward
  incompatible. Amendments require approval from all active
  maintainers.
- **Versioning Policy**: The constitution follows Semantic Versioning:
  - **MAJOR**: Removal or incompatible redefinition of a principle.
  - **MINOR**: Addition of a new principle or material expansion of
    existing guidance.
  - **PATCH**: Clarifications, wording improvements, typo fixes.
- **Compliance Review**: Each PR review MUST include a constitution
  compliance check. Reviewers MUST reference specific principle
  violations when requesting changes.
- **Periodic Audit**: The constitution MUST be reviewed quarterly to
  assess relevance and effectiveness. Audit findings MUST be tracked
  as issues.

**Version**: 1.1.0 | **Ratified**: 2026-02-17 | **Last Amended**: 2026-02-17
