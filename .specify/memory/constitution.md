<!--
Sync Impact Report
- Version change: template -> 1.0.0
- Modified principles:
  - Principle 1 -> I. Trading Safety First
  - Principle 2 -> II. Existing-Project Consistency
  - Principle 3 -> III. Reproducible Dependencies
  - Principle 4 -> IV. Risk-Proportionate Validation
  - Principle 5 -> V. Observable Operations
- Added sections:
  - Project Constraints
  - Delivery Workflow
- Removed sections:
  - None
- Templates requiring updates:
  - [x] .specify/templates/plan-template.md
  - [x] .specify/templates/spec-template.md
  - [x] .specify/templates/tasks-template.md
- Follow-up TODOs:
  - None
-->
# AI Trading Bot Constitution

## Core Principles

### I. Trading Safety First
All changes that can influence orders, positions, portfolio limits, market-data freshness,
or live/paper execution MUST preserve explicit safety controls. Trading paths MUST fail
closed when configuration, credentials, market data, or guardrail inputs are missing or
invalid. Live-trading behavior MUST remain blocked by default and only become available
through an intentional, documented opt-in.

Rationale: This project can place orders and manage risk-sensitive decisions. Safety checks
are a baseline requirement, not a later refinement.

### II. Existing-Project Consistency
This is an existing project. New work MUST extend or reuse the current architecture,
module boundaries, naming patterns, and operational flows unless a deviation produces a
clear, documented benefit. Feature specs and plans MUST identify the existing files,
classes, or workflows being extended. New abstractions, frameworks, or repo reshaping are
allowed only when the simpler path of following existing patterns is shown to be
insufficient.

Rationale: Consistency keeps the bot maintainable and lowers the risk of regressions in a
codebase built around root-level Python entrypoints, shared configuration, and file-backed
monitoring outputs.

### III. Reproducible Dependencies
Every new dependency MUST be justified in the spec or plan before implementation. Python
dependencies SHOULD be added in a reproducible form that matches the repository's existing
environment management. Any npm package introduced for UI, tooling, or build support MUST
use an exact pinned version and MUST be at least seven days old at the time it is chosen.
Version ranges such as `^`, `~`, `latest`, or unpinned tags are not allowed for npm
packages.

Rationale: Dependency drift is costly in operational systems. The explicit npm age gate
reduces breakage from freshly published packages while exact version pinning preserves
repeatability.

### IV. Risk-Proportionate Validation
Every change MUST include validation proportional to its operational risk. Trading logic,
risk rules, data pipelines, and monitoring changes MUST define how they will be verified
before being considered complete. Higher-risk changes require stronger evidence such as
backtests, smoke tests, targeted manual scenarios, or log inspection. A change is not done
when code compiles but when its intended behavior has been checked.

Rationale: This project mixes research, execution, and monitoring. Validation quality must
track impact, especially when behavior changes can influence trading outcomes.

### V. Observable Operations
Runtime-relevant behavior MUST emit or update observable evidence using the repository's
existing mechanisms where practical, including logs, CSV outputs, dashboard data sources,
or explicit health signals. New features that affect decision-making, fills, portfolio
state, or operator visibility MUST specify what evidence operators can inspect when
behavior succeeds or fails.

Rationale: A trading bot is only trustworthy when its actions and failure modes can be
understood quickly from durable outputs.

## Project Constraints

- Primary implementation work SHOULD stay aligned with the existing Python-first structure
  and current runtime stack unless the spec explicitly justifies a new runtime boundary.
- Features that introduce UI or frontend work MUST prefer the repository's current Flask
  and template-based patterns before proposing a separate frontend stack.
- Specs and plans MUST call out any environment-variable additions, file-path assumptions,
  migrations of existing logs/data, and any effect on paper-vs-live execution behavior.

## Delivery Workflow

- Specifications MUST document how the requested work fits into the existing project,
  including touched modules, reused patterns, justified deviations, and any new
  dependencies.
- Plans MUST include a constitution check that confirms safety controls, dependency
  discipline, validation approach, and observability impact.
- Tasks MUST be organized so validation and operational evidence are implemented alongside
  the affected feature work rather than deferred to a later cleanup pass.
- When npm packages are proposed, the implementation plan or research notes MUST record the
  exact version selected and confirm the package is at least seven days old.

## Governance

This constitution overrides conflicting local process guidance for specification, planning,
tasking, and implementation in this repository. Amendments MUST be made explicitly in this
file and reflected in dependent templates in the same change. Versioning follows semantic
versioning for the constitution itself: MAJOR for incompatible governance changes, MINOR
for new principles or materially expanded rules, and PATCH for clarifications that do not
change expected behavior. Compliance reviews MUST occur during planning and again before
implementation is considered complete. Every feature plan, task list, and review outcome
MUST be able to show how these principles were satisfied or why a narrowly scoped exception
was approved.

**Version**: 1.0.0 | **Ratified**: 2026-04-08 | **Last Amended**: 2026-04-08
