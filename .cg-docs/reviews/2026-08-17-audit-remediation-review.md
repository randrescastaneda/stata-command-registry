---
date: 2026-08-17
depth: full
type: standard
plan: .cg-docs/plans/2026-08-17-audit-remediation.md
findings:
  P0.1: skipped
  P1.1: fixed
  P1.2: fixed
  P1.3: fixed
  P1.4: fixed
  P1.5: fixed
  P1.6: fixed
  P2.1: fixed
  P2.2: fixed
  P2.3: skipped
  P2.4: fixed
  P2.5: fixed
  P2.6: skipped
  P2.7: fixed
---

# Review Report — Audit Remediation

**Review mode**: full (requested `mode:verify`; no prior review with fixed findings existed, so normal routing applied; schema and release changes required full-risk coverage)

**Files reviewed**: 14 tracked implementation files plus the active plan, audit artifacts, wiki files, and package metadata

**Findings**: 14 (P0: 1 deferred, P1: 6 fixed, P2: 5 fixed and 2 deferred, P3: 0)

## P0 — BLOCKING

### [P0.1] False precision in `variable_effect` metadata

**Agents**: `@cg-data-quality`, `@cg-adversarial`, `@cg-architecture`

**Files**: `commands/ssc_contributed_commands.yaml:14-212`, `commands/official_stata_commands.yaml:296-298,398-399,828-830,846-847,873-874,1009,1141`

**Issue**: Many commands are labeled `variable_effect: none` even though valid options or documented behavior can create, modify, remove, or restructure data. Examples include SSC commands `winsor2`, `ereplace`, `carryforward`, `sxpose`, and `sencode`, and official commands such as `tabulate`, `stset`, `tsappend`, `tsfill`, `stgen`, `stsplit`, `frlink`, and `splitsample`.

**Why**: A downstream data-flow consumer can silently miss variable or dataset changes. The scalar enum does not distinguish primary effects from possible or option-dependent effects.

**Fix**: Define an explicit primary-versus-possible-effects policy, then audit affected official and contributed commands. If a single scalar is insufficient, introduce a documented conditional or multi-effect representation. This requires a decision beyond the current plan's resolved Gate B values.

## P1 — CRITICAL

### [P1.1] Release metadata still identifies the pre-remediation release

**Agents**: `@cg-version-control`, `@cg-reproducibility`, `@cg-documentation`, `@cg-adversarial`

**Files**: `pyproject.toml:7`, `README.md:97-99`, `stata_registry.egg-info/PKG-INFO:3`

**Issue**: The working tree adds `variable_effect` and changes registry behavior, but the package remains version `0.1.0` and the README installs `v0.1.0`, which is the immutable pre-fix tag.

**Fix**: Bump `pyproject.toml` to `0.2.0`, update the install example and minor-version pin, add a version/tag consistency test, regenerate package metadata during release, and create `v0.2.0` after committing.

### [P1.2] `variable_effect` coverage test is existential, not complete

**Agents**: `@cg-testing`, `@cg-data-quality`, `@cg-reproducibility`

**Files**: `tests/test_variable_effect.py:74-85`

**Issue**: The test checks only that one official command has the field. Missing or invalid values in other official, SSC, GitHub, or bundled entries would pass.

**Fix**: Iterate over every command in every source and packaged YAML file and assert field presence plus exact enum membership. Keep the schema optional for legacy compatibility if that remains the plan decision, but enforce complete coverage for shipped data.

### [P1.3] Conflicting tokens silently overwrite earlier owners

**Agents**: `@cg-data-quality`, `@cg-adversarial`, `@cg-testing`

**Files**: `stata_registry/__init__.py:67-80`, `tests/test_data_integrity.py:118-167`

**Issue**: `_build_index()` uses last-write-wins for duplicate names, abbreviations, or aliases. Existing tests also build dictionaries that erase duplicate owners before asserting uniqueness.

**Fix**: Track all owners per token and reject conflicts during index construction. Add tests for abbreviation-abbreviation, alias-alias, name-abbreviation, and cross-file collisions.

### [P1.4] Lazy initialization publishes a partial index to concurrent readers

**Agent**: `@cg-performance`

**Files**: `stata_registry/__init__.py:108-122`

**Issue**: Multiple global indexes are assigned sequentially during tuple unpacking. A second thread can observe `_token_to_canonical` as non-`None` while category, effect, prefix, or control-flow indexes are still unset.

**Fix**: Publish a single immutable index object or tuple atomically, and have all lookup functions read from that object.

### [P1.5] Clean-install test is non-strict and can import the source tree

**Agents**: `@cg-testing`, `@cg-reproducibility`, `@cg-adversarial`

**Files**: `tests/test_packaging.py:100-132`

**Issue**: The test is marked `xfail(strict=False)` and the child process inherits the repository working directory, allowing `import stata_registry` to resolve the checkout rather than the installed package. The current suite reports an XPASS.

**Fix**: Remove the stale xfail, run the child from a temporary directory using the venv interpreter, assert the imported module path is under site-packages, and verify the bundled data plus `variable_effect()`.

### [P1.6] Public documentation omits the new data-field contract

**Agents**: `@cg-documentation`, `@cg-learnings-researcher`

**Files**: `README.md:31-67`, `commands/schema.json:80-92`, `wiki/api-reference.md:3-75`

**Issue**: The root README YAML example and field table omit `variable_effect`; the wiki still documents five API functions. Contributors are not told the enum meanings, optional legacy behavior, or the resolved ambiguous-command defaults.

**Fix**: Document the field in the YAML example and field table, list all enum values and primary-effect semantics, and update the wiki API reference through the normal compound/wiki workflow.

## P2 — IMPORTANT

### [P2.1] README contract test is weak and its docstring is stale

**Agents**: `@cg-testing`, `@cg-documentation`

**Files**: `tests/test_abbreviations.py:202-209`

**Issue**: The `or` assertion can pass without checking the exact field-reference wording, and the docstring still describes the old shortest/implied contract.

**Fix**: Assert the exact enumeration wording and update the test description.

### [P2.2] Generated package/cache artifacts are mixed into the implementation diff

**Agents**: `@cg-version-control`, `@cg-reproducibility`, `@cg-code-quality`

**Files**: `stata_registry.egg-info/PKG-INFO`, `stata_registry/__pycache__/*.pyc`, `tests/__pycache__/*.pyc`

**Issue**: These are generated outputs and interpreter-specific bytecode, not source changes. They create noisy, stale, non-portable release diffs.

**Fix**: Remove tracked generated artifacts and enforce their absence with packaging tests while retaining the existing ignore rules.

### [P2.3] Source/package YAML duplication remains manually synchronized

**Agents**: `@cg-version-control`, `@cg-reproducibility`, `@cg-architecture`, `@cg-adversarial`

**Files**: `commands/*.yaml`, `stata_registry/data/*.yaml`, `tests/test_packaging.py:50-68`

**Issue**: The package reads `stata_registry/data/`, while maintainers edit `commands/`; synchronization is manual and the corresponding test remains an expected failure.

**Fix**: Add build-time generation or a mandatory release/CI synchronization step. This is explicitly deferred as H-1 in the active plan.

### [P2.4] Managed audit and wiki artifacts contain historical/stale status text

**Agents**: `@cg-documentation`, `@cg-version-control`, `@cg-reproducibility`

**Files**: `AUDIT_REPORT.md`, `wiki/api-reference.md`, `.cg-docs/work-reports/2026-08-17-audit-remediation.md`, `.cg-docs/plans/2026-08-17-audit-remediation.md`

**Issue**: Historical audit text still describes the pre-remediation state, while the work report and plan metadata have not yet recorded the completed Phase 2 evidence or post-removal count of 667 entries.

**Fix**: Preserve historical reports but mark their status where appropriate, update the workflow report through `/cg-work`, and update wiki/API documentation through `/cg-compound`/wiki ownership rules.

### [P2.5] Missing-field behavior test mutates private module state

**Agents**: `@cg-testing`, `@cg-architecture`

**Files**: `tests/test_variable_effect.py:108-122`

**Issue**: The `ValueError` path is simulated by deleting a private dictionary entry, so harmless internal refactoring can break the test without changing the public behavior.

**Fix**: Exercise the missing-field boundary with an isolated synthetic index/document fixture or a controlled loader fixture.

### [P2.6] Test dependencies are undeclared

**Agents**: `@cg-reproducibility`

**Files**: `pyproject.toml:1-12`, `tests/test_variable_effect.py:44,61`

**Issue**: Verification requires `pytest` and `jsonschema`, but only runtime PyYAML is declared and no lock/constraints artifact exists.

**Fix**: Declare development/test dependencies and add a reproducible environment lock or constraints file. This is outside the current remediation plan.

### [P2.7] Boolean predicates raise `TypeError` for unhashable malformed input

**Agent**: `@cg-adversarial`

**Files**: `stata_registry/__init__.py:130-134`

**Issue**: `is_command([])` and equivalent malformed parser input raise `TypeError` rather than returning `False`.

**Fix**: Guard predicate inputs with a string type check if malformed-token handling is part of the public contract. This is outside the current plan.

## Passed

- `@cg-code-quality`: no additional P0/P1 issue beyond the findings above.
- Current source and bundled YAML files are byte-identical.
- Current registry counts are 567 official, 100 SSC, and 0 GitHub entries.
- All 667 current entries contain an enum value according to review-time inspection.
- No current abbreviation/name/alias collisions were found.
- `git diff --check` passed.
- Full test suite: `124 passed, 2 skipped, 5 xfailed, 1 xpassed`.
- Plan artifact validation passed with `cg-render-artifact --validate-only`.

## Triage Notes

The user instructed the work to be finished. Under the active plan's resolved
scalar primary-effect policy, P0.1 is deferred rather than reclassified by
guesswork; a future plan should audit option-dependent and contributed-command
effects. H-1 and undeclared test-environment dependencies remain deferred
scope. The independent correctness, packaging, documentation, collision,
concurrency, malformed-input, and completeness fixes are implemented and
verified below.

## Fix Evidence

- P1.1: `pyproject.toml` is `0.2.0`; README and wiki install guidance use
  `v0.2.0`; the wheel builds with version `0.2.0`.
- P1.2: source and bundled YAML completeness is asserted for every entry.
- P1.3: `_build_index()` rejects conflicting names, abbreviations, and aliases;
  synthetic collision tests pass.
- P1.4: lazy indexes are published as one atomic tuple.
- P1.5: clean-install coverage is strict and verifies site-packages, version,
  packaged data, and `variable_effect()`.
- P1.6: README and wiki document `variable_effect` and its enum contract.
- P2.1: README contract test asserts the exact enumeration wording.
- P2.4: wiki API/changelog and execution report were reconciled; historical
  `AUDIT_REPORT.md` remains a historical snapshot.
- P2.5: missing-field behavior uses an isolated synthetic index fixture.
- P2.7: boolean predicates return `False` for non-string input.
- P2.2: tracked egg-info and bytecode were removed; packaging tests enforce
  generated-artifact exclusion.

### Deferred

- P0.1: broader semantic audit of conditional and contributed commands.
- P2.3: build-time source/package synchronization, deferred hygiene item H-1.
- P2.6: test dependency declaration and lockfile, outside the active plan.
