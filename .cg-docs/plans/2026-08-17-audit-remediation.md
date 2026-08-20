---
date: 2026-08-17
title: "Audit remediation — blocking + correctness fixes for do2screen-py"
status: completed
completed-date: 2026-08-20
scope: "Deep"
brainstorm: ".cg-docs/brainstorms/2026-08-17-audit-triage.md"
language: "Python"
estimated-effort: "medium"
deviation-policy: "ask"
phases: 3
artifact-schema-version: 1
execution-report: ".cg-docs/work-reports/2026-08-17-audit-remediation.md"
tags: [audit, variable-effect, abbreviations, schema, do2screen-py]
completed-phases: [1, 2, 3]
---

# Plan: Audit Remediation — Blocking + Correctness Fixes

Model context: `/cg-plan` inherits the model picker or runtime configuration selected on the active platform. If the platform reports Auto or an unknown selection, I will not infer or name a hidden underlying model. If the actual selection matters, inspect the active platform's UI or configuration.

## Objective

Make `stata-registry` fit for `do2screen-py` to depend on by: (1) adding the
`variable_effect` field so the parser can classify command effects without
hardcoding names, (2) pinning a version so the dependency is reproducible, and
(3) correcting abbreviation data so the vocabulary is accurate. Hygiene items
are deferred.

## Context

The audit triage (`.cg-docs/brainstorms/2026-08-17-audit-triage.md`) reduced
8 blocking findings to 2 genuinely blocking, 8 correctness, and 5 hygiene.
Three load-bearing decisions gate the correctness work. This plan structures
implementation so Phase 1 (blocking) can start immediately, Phase 2 (data)
requires one decision, and Phase 3 (correctness) requires two more.

Key numbers: 669 commands, 29 have abbreviations, 640 have no `abbreviations`
field, 0 have `variable_effect`.

## Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| R1 | `variable_effect` field in schema.json (optional) | B-1 |
| R2 | `variable_effect` values on all 669 YAML entries | B-1 |
| R3 | `variable_effect()` accessor in reader API | B-1 |
| R4 | v0.1.0 tag on current commit (before any fixes) | B-7 |
| R5 | Abbreviation contract documented and consistent | B-2 |
| R6 | Missing abbreviations fixed (generate→g, describe→d, list→l) | B-3, B-4, B-5 |
| R7 | `in` and `of` removed from YAML | B-6 / C-2, D-3 (default) |
| R8 | `use` abbreviation `us` removed | C-4, D-8 (default) |
| R9 | Non-abbreviable commands have explicit `abbreviations: []` | C-1 |
| R10 | Missing xfail tests committed for B-6/C-2 and C-4 | Test evidence |
| R11 | Full test suite passes (xfail markers removed for fixed findings) | Verification |

## Decision Gates

Three decisions from the triage must be resolved before their dependent steps.
The plan is structured so that each phase can begin once its gate is cleared.

### Gate A: Abbreviation contract (D-1a + D-1b)

**Blocks:** Steps 5, 6, 7, 8.

**D-1a — Enumeration vs implied intermediates:**

| Option | Consequences |
|--------|--------------|
| A: Enumeration | YAML lists every valid abbreviation. Reader stays trivial. Cannot overgenerate. Current code already does this. |
| B: Implied intermediates | YAML lists shortest only. Reader must generate forms. Will overgenerate for `display`→`di` (not `d`), `describe`→`d` (not intermediates). Needs per-command exceptions. |

**D-1b — "No abbreviation" representation:**

| Option | Consequences |
|--------|--------------|
| A: `abbreviations: []` | Empty list = deliberately none. Absent = not yet classified. 640 commands need `[]` added after verification. |
| B: `abbreviatable: false` | New boolean field. Two fields to keep in sync. |
| C: Absent = none | Simplest. Can't distinguish "not yet classified" from "deliberately none". |

### Gate B: variable_effect for ambiguous commands (D-2)

**Blocks:** Step 4.

| Command | Options |
|---------|---------|
| `egen` | A: `creates` (safe default). B: omit field. C: `conditional`. |
| `recode` | A: `modifies` (common case). B: `creates` (conservative). C: `conditional`. |
| `merge` | A: `restructures` (primary purpose). B: `creates` (conservative). C: list both. |
| `append` | A: `restructures`. B: `creates`. C: list both. |
| `sort` | A: `restructures` (row order is structural). B: `none` (no variables touched). |
| `keep` | A: `removes`. Not truly ambiguous. |

### Gate C: is_prefix / is_control_flow coupling (D-4)

**Blocks:** Nothing in this plan. Deferred to hygiene. Noted here for
completeness — if the user decides to add explicit boolean fields, it can be
added to a follow-up plan.

## Implementation Steps

## Phase 1: Blocking — pin and scaffold

### 1. Tag v0.1.0 on current commit
- **Requirements**: R4
- **Files**: none (git operation)
- **Details**: Run `git tag v0.1.0` on the current commit (pre-fixes). This
  gives do2screen-py a pinnable ref immediately. The tag captures known warts.
- **Test Scenarios**: `git tag -l v0.1.0` returns `v0.1.0`.
- **Tests**: `test_v010_tag_exists` should pass after this step.
- **Acceptance criteria**: Tag exists and points to current HEAD.

### 2. Add variable_effect to schema.json
- **Requirements**: R1
- **Files**: `commands/schema.json`
- **Details**: Add `variable_effect` as an optional string enum on the command
  item schema. Allowed values: `creates`, `modifies`, `renames`, `removes`,
  `labels`, `restructures`, `none`. Field is optional so existing entries
  without it remain valid and stataGlow is unaffected.
- **Test Scenarios**: Schema validates; entries with the field pass; entries
  without it still pass; invalid values are rejected.
- **Tests**: `test_variable_effect_not_in_schema` will need its assertion
  flipped (currently asserts absence). Add new test for schema acceptance.
- **Acceptance criteria**: `check-jsonschema` validates all three YAML files
  against the updated schema.

### 3. Add variable_effect() accessor to reader
- **Requirements**: R3
- **Files**: `stata_registry/__init__.py`
- **Details**: Add a `variable_effect(command: str) -> str` function. Returns
  the field value. Raises `KeyError` if command not recognised. Raises
  `ValueError` if entry has no `variable_effect` field. Build a
  `_name_to_variable_effect` dict in `_build_index`.
- **Test Scenarios**: Returns correct value for a command with the field.
  Raises `KeyError` for unknown command. Raises `ValueError` for command
  without the field.
- **Tests**: `test_variable_effect_accessor_exists` should pass. Add tests
  for KeyError/ValueError paths.
- **Acceptance criteria**: `sr.variable_effect` is callable and raises the
  documented exceptions.

### 4. Add variable_effect values to YAML entries
- **Requirements**: R2
- **Blocks on**: Gate B (ambiguous command decisions)
- **Files**: `commands/official_stata_commands.yaml`,
  `commands/ssc_contributed_commands.yaml`,
  `commands/github_contributed_commands.yaml`
- **Details**: Add `variable_effect` to every command entry. Most commands
  are `none`. Data management commands get non-none values per the audit
  report's table and the user's resolution of Gate B. Ambiguous commands
  (`egen`, `recode`, `merge`, `append`, `sort`, `keep`) get values per the
  decision. Copy updated files to `stata_registry/data/`.
- **Test Scenarios**: Every entry has the field. Schema validates. Reader
  returns correct value for each.
- **Tests**: `test_variable_effect_in_official_yaml` and
  `test_variable_effect_full_stack` should pass.
- **Acceptance criteria**: `sr.variable_effect("generate")` returns
  `"creates"`. Full test suite run with no new failures.

### 5. Sync data directory
- **Requirements**: R2
- **Files**: `stata_registry/data/*.yaml`
- **Details**: Copy all three YAML files from `commands/` to
  `stata_registry/data/` after Phase 1 edits. (Hygiene item H-1 — build
  step automation — is deferred. Manual copy for now.)
- **Test Scenarios**: `test_file_is_identical` passes for all three files.
- **Tests**: Existing packaging tests.
- **Acceptance criteria**: Byte-identical copies.

## Phase 2: Correctness — abbreviation fixes

### 6. Update abbreviation contract documentation
- **Requirements**: R5
- **Blocks on**: Gate A (D-1a)
- **Files**: `README.md`, `commands/schema.json`
- **Details**: If D-1a resolves to Enumeration (option A): update README
  field reference from "Shortest accepted forms (all intermediate forms
  between the shortest and name are implied)" to "All accepted abbreviation
  forms, listed explicitly." Update schema description to match. If D-1a
  resolves to Implied intermediates (option B): update schema description
  and add reader generation logic (larger change).
- **Test Scenarios**: `test_readme_field_reference_matches_code` should pass
  after this step.
- **Tests**: Existing xfail test.
- **Acceptance criteria**: README, schema, and code agree on the contract.

### 7. Fix missing abbreviations
- **Requirements**: R6
- **Blocks on**: Gate A (D-1a — determines whether to list all forms or
  just the shortest)
- **Files**: `commands/official_stata_commands.yaml`
- **Details**: Add `g` to `generate`'s abbreviations. Add `d` to
  `describe`'s abbreviations. Add `l` to `list`'s abbreviations. If
  enumeration contract: list all intermediate forms. If implied contract:
  list only the shortest.
- **Test Scenarios**: `sr.canonical_command("g")` returns `"generate"`.
  `sr.canonical_command("d")` returns `"describe"`.
  `sr.canonical_command("l")` returns `"list"`.
- **Tests**: `test_generate_abbreviates_to_g`,
  `test_generate_shortest_abbreviation_in_yaml`,
  `test_describe_abbreviation_d_in_yaml`,
  `test_list_abbreviation_l_in_yaml` should all pass.
- **Acceptance criteria**: All four xfail tests pass.

### 8. Resolve "no abbreviation" representation and update entries
- **Requirements**: R9
- **Blocks on**: Gate A (D-1b)
- **Files**: `commands/official_stata_commands.yaml` (and potentially schema)
- **Details**: If D-1b resolves to `abbreviations: []` (option A): add
  explicit `abbreviations: []` to every command that Stata does not allow
  to be abbreviated. Start with confirmed non-abbreviable commands:
  `replace`, `egen`, `destring`, `use` (after `us` is removed). The full
  list of 640 commands without the field needs auditing — for this plan,
  add `[]` only to commands verified as non-abbreviable. Leave the rest
  with absent field (meaning "not yet classified"). If D-1b resolves to
  option B or C: adjust approach accordingly.
- **Test Scenarios**: `test_replace_abbreviations_field_present`,
  `test_egen_abbreviations_field_present`,
  `test_destring_abbreviations_field_present` should pass.
- **Tests**: Existing xfail tests.
- **Acceptance criteria**: Confirmed non-abbreviable commands have explicit
  `abbreviations: []`.

### 9. Remove `in` and `of` from YAML
- **Requirements**: R7
- **Files**: `commands/official_stata_commands.yaml`
- **Details**: Remove the `in` and `of` entries from the `control_flow`
  category. They are `foreach` syntax fragments, not standalone commands.
  After removal, `sr.is_command("in")` and `sr.is_command("of")` should
  return False.
- **Test Scenarios**: `is_command("in")` returns False. `is_command("of")`
  returns False. `is_command("foreach")` still returns True.
- **Tests**: Add new xfail tests before the fix (for B-6/C-2), then remove
  xfail after. Or add passing tests directly since the fix is in the same
  phase.
- **Acceptance criteria**: `in` and `of` are not in the registry.

### 10. Fix `use` abbreviation `us`
- **Requirements**: R8
- **Files**: `commands/official_stata_commands.yaml`
- **Details**: Remove `us` from `use`'s abbreviations list. If `use` has
  no other abbreviations, add `abbreviations: []` (per the convention
  resolved in Gate A).
- **Test Scenarios**: `is_command("us")` returns False. `is_command("use")`
  returns True.
- **Tests**: Add new xfail test for C-4, then remove xfail after fix.
- **Acceptance criteria**: `us` is not a recognised token.

### 11. Add missing xfail tests
- **Requirements**: R10
- **Files**: `tests/test_abbreviations.py` (or new file)
- **Details**: Commit xfail tests for B-6/C-2 (`in`/`of` as commands) and
  C-4 (`use` abbreviation `us`). These encode the findings as test evidence
  before the fixes are applied. If the fixes in steps 9-10 are applied
  first, commit the tests as passing instead.
- **Test Scenarios**: Tests exist and have `reason` strings.
- **Tests**: New test functions.
- **Acceptance criteria**: Every finding in the audit has a corresponding
  test.

## Phase 3: Release — verify and tag

### 12. Update data directory and run full test suite
- **Requirements**: R11
- **Files**: `stata_registry/data/*.yaml`
- **Details**: Copy updated YAML from `commands/` to `stata_registry/data/`.
  Run the full test suite. Remove xfail markers from tests whose underlying
  defects are now fixed. Verify that the xpass tests are intentional.
- **Test Scenarios**: `pytest tests/ -v` shows 0 xfail for fixed findings.
  No new failures. Count of passing tests increases by the number of fixed
  findings.
- **Tests**: Full suite.
- **Acceptance criteria**: `pytest tests/ -v` passes with 0 unexpected
  failures.

### 13. Bump version to 0.2.0 and tag
- **Requirements**: R4
- **Files**: `pyproject.toml`
- **Details**: Change `version = "0.1.0"` to `version = "0.2.0"`. Commit.
  Tag as `v0.2.0`.
- **Test Scenarios**: `python -c "import importlib.metadata;
  print(importlib.metadata.version('stata-registry'))"` returns `0.2.0`.
- **Tests**: Add a version check test.
- **Acceptance criteria**: `v0.2.0` tag exists and pyproject.toml says
  `0.2.0`.

## Testing Strategy

- Existing test suite (7 files, 123 tests) is the primary verification.
- xfail markers are removed as defects are fixed; `strict=True` tests
  will fail if the fix is incomplete.
- New tests added for `variable_effect` accessor (KeyError, ValueError
  paths) and for removed entries (`in`, `of`, `us`).
- Full suite run after each phase to catch regressions.

## Documentation Checklist

- [ ] README field reference updated for abbreviation contract
- [ ] Schema description updated for abbreviation contract
- [ ] README API section updated with `variable_effect()` example
- [ ] `variable_effect` values documented (enum values + ambiguous cases)

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Abbreviation contract decision stalls | Medium | Blocks Phase 2 | Phase 1 is independent. Tag v0.1.0 and add variable_effect while waiting. |
| variable_effect values for ambiguous commands are wrong | Low | Data bug | Ambiguous cases are explicitly flagged. Values can be corrected in a patch release. |
| Removing `in`/`of` breaks stataGlow | Low | External consumer | stataGlow hasn't migrated yet. It uses its own YAML copies. |
| 640 commands need `abbreviations: []` | Medium | Large manual effort | Only add `[]` to verified non-abbreviable commands in this plan. Rest deferred. |
| Copy commands/ → data/ forgets a file | Low | Stale data | Existing `test_file_is_identical` catches this. |

## Out of Scope

- H-1: Build step to automate `commands/` → `data/` copy.
- H-2: Remove `stata_registry.egg-info/` from git.
- H-3: Remove stale xfail on `test_fresh_pip_install`.
- S-1: Explicit `is_prefix`/`is_control_flow` boolean fields.
- B-8: stataGlow migration (external repository).
- Full audit of all 640 commands for `abbreviations: []`.

## Completion Contract

### Outcome

`stata-registry` v0.2.0 is tagged and published with `variable_effect` on
every command, corrected abbreviations, and a clean test suite. do2screen-py
can pin `stata-registry>=0.2,<0.3` and use `variable_effect()` to classify
command effects.

### Verification Surface

| ID | Evidence Required | Command/Artifact | Required |
|----|-------------------|------------------|----------|
| V1 | v0.1.0 tag exists | `git tag -l v0.1.0` | yes |
| V2 | v0.2.0 tag exists | `git tag -l v0.2.0` | yes |
| V3 | variable_effect in schema | `check-jsonschema --schemafile commands/schema.json commands/official_stata_commands.yaml` | yes |
| V4 | variable_effect accessor works | `python -c "import stata_registry as sr; print(sr.variable_effect('generate'))"` → `creates` | yes |
| V5 | Full test suite passes | `pytest tests/ -v` — 0 unexpected failures | yes |
| V6 | generate→g resolves | `python -c "import stata_registry as sr; print(sr.canonical_command('g'))"` → `generate` | yes |
| V7 | in/of removed | `python -c "import stata_registry as sr; print(sr.is_command('in'))"` → `False` | yes |
| V8 | use→us removed | `python -c "import stata_registry as sr; print(sr.is_command('us'))"` → `False` | yes |
| V9 | data/ in sync | `test_file_is_identical` passes | yes |
| V10 | Version is 0.2.0 | `pyproject.toml` shows `version = "0.2.0"` | yes |

### Constraints

| ID | Constraint | Check |
|----|------------|-------|
| C1 | No parsing logic, no regex, no deps beyond PyYAML | `test_only_yaml_dependency` passes |
| C2 | Schema changes are backward-compatible (optional fields) | Existing YAML without `variable_effect` still validates |
| C3 | Reader API is backward-compatible (no existing function changes) | All existing tests pass |
| C4 | `commands/` and `stata_registry/data/` are byte-identical | `test_file_is_identical` passes |

### Boundaries

- **Allowed**: Schema additions (optional fields), YAML data edits, reader
  API additions, test additions/modifications, README/schema description
  updates, version bump, git tags.
- **Out of scope**: Hygiene items (H-1, H-2, H-3, S-1), stataGlow migration,
  full abbreviation audit of 640 commands.

### Iteration Policy

1. Apply Phase 1 steps in order. Each step is independently committable.
2. Gate A and Gate B decisions must be resolved before Phase 2 steps that
   depend on them.
3. Phase 2 steps can be applied in any order once their gates are cleared.
4. Phase 3 runs after all Phase 2 steps are complete.
5. If a step fails its acceptance criteria, fix before proceeding.

### Blocked-Stop Conditions

- Gate A (abbreviation contract) is unresolved → Phase 2 steps 6-8 cannot
  proceed. Phase 1 is unaffected.
- Gate B (variable_effect ambiguous values) is unresolved → Step 4 cannot
  complete. Steps 1-3 are unaffected.
- `check-jsonschema` fails after schema change → stop and fix schema before
  touching YAML.
- Existing tests break after a change → stop and fix before proceeding.
