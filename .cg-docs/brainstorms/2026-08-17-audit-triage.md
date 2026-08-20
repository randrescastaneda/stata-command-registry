---
date: 2026-08-17
title: "Audit triage — severity reclassification and decision extraction"
status: in-progress
scope: "Deep"
artifact-schema-version: 1
chosen-approach: ""
tags: [audit, triage, do2screen-py, variable-effect, abbreviations]
---

# Audit Triage — Severity Reclassification and Decision Extraction

## STEP 1: Test-Evidence Validation

**pytest results:** 103 passed, 17 xfailed, 2 skipped, 1 xpassed.

### Findings with xfail test coverage

| Finding | xfail tests | Count |
|---------|-------------|-------|
| B-1 variable_effect absent | `test_variable_effect_in_official_yaml`, `test_variable_effect_accessor_exists`, `test_variable_effect_full_stack` | 3 |
| B-2 Abbreviation contract undefined | `test_implied_intermediate_resolves`, `test_readme_field_reference_matches_code` | 2 |
| B-3 generate missing `g` | `test_generate_abbreviates_to_g`, `test_generate_shortest_abbreviation_in_yaml` | 2 |
| B-4 describe missing `d` | `test_describe_abbreviation_d_in_yaml` | 1 |
| B-5 list missing `l` | `test_list_abbreviation_l_in_yaml` | 1 |
| B-7 v0.1.0 tag missing | `test_v010_tag_exists` | 1 |
| B-8 stataGlow not migrated | `test_stataglow_grammar_unchanged_after_migration` (+ 1 skip) | 1 |
| C-1 No "none allowed" signal | `test_replace_abbreviations_field_present`, `test_egen_abbreviations_field_present`, `test_destring_abbreviations_field_present` | 3 |
| C-3 Zero aliases | `test_alias_resolves` (skipped — no data) | 0 (+ 1 skip) |
| H-1 Duplicate data dirs | `test_no_manual_duplicate` | 1 |
| H-2 egg-info committed | `test_egg_info_not_tracked` | 1 |
| S-1 Category-derived coupling | `test_is_prefix_not_category_derived` | 1 |
| **Total xfail accounted for** | | **17** |

All 17 xfail tests map to named findings. Every xfail has a `reason` string.

### Findings with NO test (assertions only)

| Finding | Status | Verified mechanically |
|---------|--------|----------------------|
| **B-6 / C-2** `in` and `of` registered as commands | **No xfail test** | Yes — `is_command("in")` returns True, `canonical_command("in")` returns `"in"` |
| **C-4** `use` has abbreviation `us` | **No xfail test** | Yes — `is_command("us")` returns True, maps to `"use"` |

These two findings are real but are assertions in prose, not encoded as
failing tests. They carry less evidentiary weight until a test is committed.

### Stale marker

| Test | Issue |
|------|-------|
| `test_fresh_pip_install` | Marked `xfail` but passes (XPASS). The xfail marker is stale — remove it. H-3 (clean pip install) is confirmed working. |

---

## STEP 2: Reclassified Severity

**Test applied to each finding:** Does this prevent do2screen-py from starting
work today?

### Blocking (genuinely prevents do2screen-py from starting)

| # | Finding | Why it blocks |
|---|---------|---------------|
| **B-1** | `variable_effect` field absent everywhere | do2screen-py cannot classify a line's effect on variables. It is contractually forbidden from hardcoding command names. Without this field, it cannot start. |
| **B-7** | v0.1.0 tag does not exist | The dependency cannot be pinned. A dependency that cannot be pinned is not a dependency — do2screen-py cannot add `stata-registry` to its requirements in any reproducible way. |

### Correctness (wrong, should fix before production, but does not block starting)

| # | Finding | Original | Why demoted | Reasoning |
|---|---------|----------|-------------|-----------|
| **B-2** | Abbreviation contract undefined | Blocking | Correctness | The reader implements enumeration. The code IS the contract. The README is wrong, not the code. do2screen-py can build against the reader's actual behavior today. Documentation mismatch does not block development. |
| **B-3** | `generate` missing `g` | Blocking | Correctness | `g` not resolving is a data bug. do2screen-py can start and will surface this during testing. It does not prevent the parser from being built. |
| **B-4** | `describe` missing `d` | Blocking | Correctness | Same reasoning as B-3. |
| **B-5** | `list` missing `l` | Blocking | Correctness | Same reasoning as B-3. |
| **B-6** | `in` and `of` registered as commands | Blocking | Correctness | If do2screen-py treats `in` as a command, it will misparse `foreach x in 1 2 3`. But this is a data fix, not an architectural blocker. The parser can be built and this discovered during integration testing. |
| **B-8** | stataGlow not migrated | Blocking | N/A | Does not affect do2screen-py at all. do2screen-py depends on this package, not on stataGlow. This is a project goal, not a do2screen-py blocker. |
| **C-1** | No "none allowed" signal | Correctness | (unchanged) | Data quality issue. |
| **C-2** | `in` and `of` are syntax fragments | Correctness | (unchanged) | Same issue as B-6, restated. |
| **C-3** | Zero aliases | Correctness | (unchanged) | Alias code path is untested in production but implemented. |
| **C-4** | `use` has `us` abbreviation | Correctness | (unchanged) | Data bug — `us` is not a valid Stata abbreviation for `use`. |

### Hygiene (does not affect consumers)

| # | Finding | Original | Notes |
|---|---------|----------|-------|
| **H-1** | Duplicate data directories | Hygiene | (unchanged) |
| **H-2** | egg-info committed | Hygiene | (unchanged) |
| **H-3** | Clean pip install | Hygiene | Confirmed working (XPASS). Remove stale xfail marker. |
| **S-1** | Category-derived coupling | Semantic coupling | Design concern, not a bug. Can be addressed later. |
| **S-2** | Reader does not import re | — | Positive finding. No action. |

### Summary: 2 blocking, 8 correctness, 5 hygiene

---

## STEP 3: Decision Extraction

### Load-bearing decisions (presented with options and consequences only)

#### Decision 1: Abbreviation contract + "no abbreviation" representation

This is two decisions that must be resolved together because they interact.

**D-1a: Enumeration vs implied intermediates**

| Option | Description | Consequences |
|--------|-------------|--------------|
| **A: Enumeration** | `abbreviations` lists every valid abbreviation explicitly. Reader does not generate forms. | Verbose YAML entries. Reader stays trivial. Cannot overgenerate. Every abbreviation must be manually verified and listed. Current reader already implements this. |
| **B: Implied intermediates** | `abbreviations` lists only the shortest form. Reader generates all intermediate forms between shortest and canonical name. | Compact entries. Reader must contain generation logic. Will overgenerate for commands where Stata does NOT accept all intermediates (e.g., `display` → `di` but not `d`; `describe` → `d` but not intermediate forms). Requires per-command exceptions or a new field to opt out of generation. |

**D-1b: How to express "no abbreviations allowed"**

| Option | Description | Consequences |
|--------|-------------|--------------|
| **A: Explicit `abbreviations: []`** | Empty list means "deliberately no abbreviations". Absent field means "not yet classified". | Distinguishes "we checked and Stata forbids this" from "we haven't checked yet". Requires updating every non-abbreviable command to have explicit `[]`. Schema already allows this. |
| **B: Separate `abbreviatable: false` field** | Boolean field, independent of `abbreviations`. | More explicit but adds schema complexity. The `abbreviations` field still needs to handle the empty-vs-absent ambiguity unless both are present. Two fields to keep in sync. |
| **C: Convention that absent = none** | If `abbreviations` is missing, the command cannot be abbreviated. | Simplest. But makes it impossible to distinguish "not yet classified" from "deliberately none". Every new command added without the field would silently claim to be non-abbreviable. |

#### Decision 2: `variable_effect` values for ambiguous commands

The proposed enum is: `creates`, `modifies`, `renames`, `removes`, `labels`, `restructures`, `none`.

These commands cannot be cleanly assigned a single value:

| Command | Tension | Options |
|---------|---------|---------|
| **`egen`** | Behavior depends on the function called. All standard `egen` functions create new variables, but the command's effect is not deterministic from the name alone. | **A:** `creates` (safe default — most egen functions create). **B:** Omit the field on egen, force consumers to handle unknown. **C:** Add a new value `conditional` with a description explaining the dependency. |
| **`recode`** | Without `generate()`, modifies in place. With `generate(newvar)`, creates. | **A:** `modifies` (common case is in-place). **B:** `creates` (safer for a parser that must account for all possibilities). **C:** `conditional` as above. |
| **`merge`** | Primarily restructures (joins datasets), but also creates `_merge`. | **A:** `restructures` (primary purpose). **B:** `creates` (conservative — a new variable appears). **C:** Add both values as a list, e.g., `variable_effect: [restructures, creates]`. |
| **`append`** | Primarily restructures. May create variables if the using dataset has columns the master doesn't. | **A:** `restructures`. **B:** `creates` (conservative). **C:** List as above. |
| **`sort`** | Changes row order only. No variables added, removed, or modified. | **A:** `restructures` (row order is structural). **B:** `none` (no variables are affected). This is a definitional choice about whether "restructures" includes row ordering. |
| **`keep`** | Removes variables (keeps specified, drops others). | **A:** `removes`. This is not really ambiguous — just listed for completeness. |

#### Decision 3: `is_prefix` / `is_control_flow` coupling

| Option | Description | Consequences |
|--------|-------------|--------------|
| **A: Add explicit boolean fields** | `is_prefix: true/false` and `is_control_flow: true/false` on each entry in YAML. Category keys remain for TextMate scoping only. | Decouples parser identity from presentation layer. Schema addition (optional, backward-compatible). Requires touching every prefix and control-flow entry in the YAML. More work upfront, but eliminates the coupling risk permanently. |
| **B: Keep as-is (category-derived)** | `is_prefix()` and `is_control_flow()` continue to check category key names. | Zero work now. But any cosmetic rename of a category key (e.g., `prefix_commands` → `data_prefixes` for cleaner TextMate scopes) silently breaks do2screen-py. The coupling is undocumented and invisible. |

### Default proposals for remaining decisions

| # | Decision | Proposed default | Reasoning |
|---|----------|-----------------|-----------|
| D-3 | Should `in` and `of` remain as entries? | **Remove from YAML.** | They are `foreach` syntax fragments, not standalone commands. do2screen-py will misparse `foreach x in 1 2 3` if `in` registers as a command. |
| D-7 | Data directory duplication resolution? | **Build step copies `commands/` → `data/` at package time, `data/` is gitignored.** | `commands/` is the human-editable source. `data/` is a build artifact. Symlinks break on Windows and in sdist. |
| D-8 | `use` abbreviation `us`: valid? | **Remove `us`.** Stata does not abbreviate `use` because it conflicts with other command prefixes. | The audit instruction already flagged this. Verify against Stata 19 docs if available; otherwise remove and let a user re-add if wrong. |
| D-9 | Version after all fixes? | **Tag v0.1.0 on current commit immediately (before any fixes). Then bump to v0.2.0 after variable_effect lands.** | do2screen-py needs a pinnable version NOW. v0.1.0 captures the current state (known warts and all). v0.2.0 adds variable_effect and abbreviation corrections. This matches the user's instruction to "cut v0.1.0 as soon as variable_effect lands" — interpreted as: tag current state as v0.1.0, then cut v0.2.0 with the fixes. |

---

## Implementation Scope (pending decisions)

Scoped to **blocking + correctness only**. Hygiene items (H-1, H-2, H-3, S-1)
are deferred.

**Blocking (must complete before v0.2.0):**
1. Add `variable_effect` field to schema.json (optional), YAML entries, and reader API.
2. Tag v0.1.0 on current commit.

**Correctness (must complete before v0.2.0):**
3. Resolve abbreviation contract (D-1a) and update README + schema description.
4. Resolve "no abbreviation" representation (D-1b) and update non-abbreviable entries.
5. Fix missing abbreviations: `generate` → add `g`, `describe` → add `d`, `list` → add `l`.
6. Remove `in` and `of` from YAML (D-3, pending approval).
7. Fix `use` abbreviation `us` (D-8, pending approval).
8. Commit xfail tests for B-6/C-2 and C-4 (assertions need test evidence).

**Deferred:**
- H-1: Duplicate data directories.
- H-2: egg-info removal.
- H-3: Stale xfail marker on `test_fresh_pip_install`.
- S-1: Explicit `is_prefix`/`is_control_flow` fields.
- B-8: stataGlow migration (external dependency).
