---
date: 2026-08-20
title: "Make a YAML registry release-safe with explicit metadata and atomic lookups"
category: "data-quality"
language: "Python"
tags: [yaml-registry, variable-effect, abbreviations, schema, packaging, pytest]
root-cause: "Registry schema, source data, bundled data, reader indexes, documentation, and release metadata were not enforced as one contract."
severity: "P1"
---

# Make a YAML Registry Release-Safe with Explicit Metadata and Atomic Lookups

## Problem

The registry needed to expose `variable_effect` for downstream data-flow tools,
correct its explicit abbreviation contract, remove syntax fragments registered
as commands, and publish a reproducible release. The initial implementation had
weak completeness tests, silent token collisions, a manually synchronized
packaged-data copy, stale release guidance, and generated artifacts in the
worktree.

## Root Cause

The YAML schema, editable registry files, bundled package data, Python reader,
tests, documentation, and release metadata evolved independently. An
existential test allowed incomplete metadata, dictionary assignment used
last-write-wins for conflicting tokens, and several module-level indexes were
published independently during lazy initialization.

## Solution

- Define `variable_effect` as an enum and annotate every shipped source and
  bundled entry. Keep the schema optional for legacy documents, while enforcing
  complete valid coverage for shipped data in tests.
- Treat `abbreviations` as explicit enumeration. Document the contract and add
  verified forms such as `generate -> g`, `describe -> d`, and `list -> l`.
- Register `in` and `of` as syntax fragments rather than commands, and remove
  the invalid `us` abbreviation from `use`.
- Build the reader's lookup tables as one tuple and publish it atomically after
  YAML loading. Reject duplicate canonical records and conflicting names,
  abbreviations, or aliases instead of silently overwriting owners.
- Make release verification executable: run `pytest`, `check-jsonschema`, build
  a `0.2.0` wheel, and install it from outside the repository root while
  checking package metadata, bundled data, and the public API.
- Update README and wiki API documentation with the primary-effect semantics
  and resolved defaults: `egen=creates`, `recode=modifies`,
  `merge/append/sort=restructures`, and `keep=removes`.

## Prevention

- Add an exhaustive source-and-bundle completeness test whenever a schema field
  is required by a consumer.
- Fail fast on registry token collisions and duplicate canonical records.
- Keep release references, package metadata, wheel checks, and tags aligned.
- Treat the scalar effect as a documented primary-effect policy; audit
  option-dependent and contributed-command effects separately before relying on
  them for full data-flow analysis.
- Automate `commands/` to package-data synchronization and clean tracked build
  artifacts in a follow-up hygiene plan.

## Related

- [Audit remediation plan](../../plans/2026-08-17-audit-remediation.md)
- [Audit review](../../reviews/2026-08-17-audit-remediation-review.md)
- [Audit triage](../../brainstorms/2026-08-17-audit-triage.md)
