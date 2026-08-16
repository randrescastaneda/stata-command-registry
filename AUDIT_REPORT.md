# stata-command-registry — Audit Report

**Date:** 2026-08-16  
**Auditor:** Kilo (automated + manual analysis)  
**Scope:** Data integrity, abbreviation semantics, variable_effect gap, API correctness, packaging, stataGlow migration  
**Tests committed:** 123 (103 pass, 17 xfail documenting known defects, 2 skip, 1 xpass)

---

## Summary Verdict

**NOT FIT FOR do2py TO DEPEND ON TODAY.**

Three blocking issues must be resolved before do2py can consume this package:

1. **`variable_effect` field is completely absent** — schema, YAML, reader, and API. do2py cannot determine what effect a command has on variables without hardcoding command names, which violates its contract.

2. **Abbreviation contract is undefined and self-contradictory.** The README, schema, data, and code all disagree on what the `abbreviations` field means. At least three commands (`generate`, `describe`, `list`) have incorrect abbreviations relative to real Stata.

3. **stataGlow has not been migrated.** It still carries its own byte-identical copies of `commands/*.yaml`. The "single source of truth" does not yet exist in practice.

The underlying data quality (669 commands, schema conformance, no collisions) is strong. The reader implementation is clean, correct, and minimal. The blocking issues are design and completeness problems, not engineering debt.

---

## Findings by Severity

### BLOCKING (must fix before do2py can depend on the package)

| # | Finding | Evidence | Impact | Recommended Fix |
|---|---------|----------|--------|-----------------|
| B-1 | **`variable_effect` field absent everywhere** | Not in `schema.json`, not in any YAML file, no accessor in reader. Confirmed by grep + inspect. | do2py is contractually forbidden from hardcoding command names. Without variable_effect, it cannot know whether `generate` creates or `replace` modifies. | See Part 3 implementation plan below. |
| B-2 | **Abbreviation contract undefined** | README field reference: "Shortest accepted forms (intermediates implied)". Schema description: "['reg', 'regr'] for 'regress'" (enumeration). Reader: exact YAML values only (enumeration, no generation). All three disagree. | Any consumer must guess which interpretation is correct. do2py using implied-intermediates would overgenerate; stataGlow using enumeration would miss forms. | Adopt **enumeration** contract (current reader behavior). Update README and schema descriptions to match. |
| B-3 | **`generate` missing `g` abbreviation** | YAML lists `[ge, gen, gene, gener, genera, generat]`. Stata accepts `g` as the shortest abbreviation for generate. `is_command("g")` returns False. | Any Stata code containing `g y = x+1` will fail to recognize `g` as generate. Blocking for both do2py and stataGlow. | Add `g` to generate's abbreviations list and verify against Stata 19 docs. |
| B-4 | **`describe` missing `d` abbreviation** | YAML lists `[de, des, desc, descr, descri, describ]`. Stata's shortest abbreviation for describe is `d`. | Same as B-3. `d varname` in Stata triggers describe; the registry won't recognize it. | Add `d` to describe's abbreviations list. |
| B-5 | **`list` missing `l` abbreviation** | YAML lists `[li]`. In Stata 14+, list abbreviates to `l`. | Same as B-3. | Add `l` to list's abbreviations list. Verify against Stata 19 docs. Note: `l` is a very low-ambiguity prefix in Stata, so confirm it doesn't collide with another command. |
| B-6 | **`in` and `of` registered as commands** | Listed under `control_flow` category. `is_command("in")` and `is_command("of")` return True. | `in` and `of` are syntax fragments of `foreach`, not standalone commands. do2py treating `in` as a command will produce incorrect parse trees. | Remove `in` and `of` from the `control_flow` category, or introduce a `syntax_fragment` category that is not included in the public `is_command()` API. |
| B-7 | **v0.1.0 tag does not exist** | `git tag -l` returns nothing. README instructs consumers to install at `@v0.1.0`. | Consumers following the README get a git error on install. | Create the tag: `git tag v0.1.0`. |
| B-8 | **stataGlow not migrated** | stataGlow `commands/` contains byte-identical copies of all three YAML files + `schema.json`. No reference to `stata-registry` as a dependency. | The "single source of truth" does not exist. Changes to this repo are not picked up by stataGlow. Any divergence creates parallel realities. | Migrate stataGlow to depend on `stata-registry`. Remove its `commands/` directory. Generate `grammars/stata.json` from the package data. Verify byte-identical output. |

### CORRECTNESS (affects data quality, should fix soon)

| # | Finding | Evidence | Impact | Recommended Fix |
|---|---------|----------|--------|-----------------|
| C-1 | **No way to distinguish "no abbreviations allowed" from "not yet specified"** | `replace`, `egen`, `destring` have no `abbreviations` field. The reader treats absent field the same as empty list. | A newly added command with a typo'd name will silently have no abbreviations and it's impossible to tell if that's intentional. | Adopt the convention: `abbreviations: []` means explicitly "none allowed". Absent field means "not yet classified". Add schema `"minItems": 0` for the array. Update all commands that cannot be abbreviated to have explicit `abbreviations: []`. |
| C-2 | **`in` and `of` are syntax fragments, not commands** | No Stata documentation classifies `in` or `of` as commands. They are keywords used in `foreach ... in ...` and `foreach ... of ...` syntax. | Pollutes the command namespace. | Remove from YAML. |
| C-3 | **0 aliases exist across the entire registry** | No command has a `aliases` field populated. The code supports aliases perfectly. | Alias code path is untested in production. | Audit whether any Stata commands actually need aliases (e.g., `anova` has `manova` — but those are separate commands). If none exist, document the decision. |
| C-4 | **`use` has abbreviation `us` but Stata does not abbreviate `use`** | YAML lists `use: [us]`. In Stata, `use` cannot be abbreviated because it conflicts with other command prefixes. | `is_command("us")` returns True and resolves to `use`, but Stata does not accept `us` as an abbreviation. | Verify against Stata 19. If Stata does not abbreviate `use`, remove `us`. |

### HYGIENE (should fix, does not block consumers)

| # | Finding | Evidence | Impact | Recommended Fix |
|---|---------|----------|--------|-----------------|
| H-1 | **Duplicate data directories** | `commands/` and `stata_registry/data/` contain byte-identical regular files. | The exact duplication this repo exists to eliminate is reintroduced within the repo itself. Must be kept in sync manually. | Pick one canonical location. Either: (a) `stata_registry/data/` is the source, and `commands/` is a symlink, or (b) a build step copies `commands/` -> `stata_registry/data/` at build time, and `data/` is gitignored. |
| H-2 | **`stata_registry.egg-info/` committed to git** | `git ls-files` confirms it. `.gitignore` has `*.egg-info/` but the directory was committed before the rule existed. | Clutters the repo; stale metadata. | `git rm -r --cached stata_registry.egg-info/` |
| H-3 | **Clean pip install works** | Verified: `pip install .` in a fresh venv, then `import stata_registry as sr; sr.is_command('regress')` returns True. YAML data files are correctly packaged via `package-data` in `pyproject.toml`. | N/A (positive finding). | No action needed. |

### SEMANTIC COUPLING (design concern, affects do2py architecture)

| # | Finding | Evidence | Impact | Recommended Fix |
|---|---------|----------|--------|-----------------|
| S-1 | **`is_prefix()` and `is_control_flow()` derived from category keys** | `_PREFIX_CATEGORIES = {"prefix_commands", "prefix_control"}`, `_CONTROL_FLOW_CATEGORIES = {"control_flow"}`. A cosmetic rename of a TextMate scope key (e.g., `prefix_commands` → `data_prefixes` for cleaner stataGlow scopes) would silently break do2py's parser. | The category key is a presentation-layer concept inherited from syntax highlighting. Coupling parser logic to it is fragile. | Add explicit `is_prefix: true/false` and `is_control_flow: true/false` fields to each entry in the YAML. Keep the category keys for TextMate scoping, but make parser identity explicit. This is a schema addition (optional field, backward-compatible). |
| S-2 | **Reader does not import or parse Stata source** | Confirmed: no `re` module, no parsing functions, only `yaml` as external dependency. Data and lookup only. | N/A (positive finding). | No action needed. |

---

## Part 3 — variable_effect Implementation Plan

### 3.1 Current state

Confirmed absent from:
- `commands/schema.json` — no `variable_effect` property defined
- All three YAML files — zero entries contain the field
- `stata_registry/__init__.py` — no `variable_effect()` function

### 3.2 Schema.json addition

Add `variable_effect` as an **optional** field on the command item schema:

```json
"variable_effect": {
  "type": "string",
  "enum": ["creates", "modifies", "renames", "removes", "labels",
           "restructures", "none"],
  "description": "How this command affects variables in the dataset"
}
```

Since the field is optional, all existing entries remain valid. stataGlow is unaffected (it ignores unknown fields).

### 3.3 Allowed values

| Value | Meaning | Example commands |
|-------|---------|-----------------|
| `creates` | Creates new variable(s) | `generate`, `egen`, `predict`, `recode` (with generate option) |
| `modifies` | Modifies existing variable(s) in place | `replace`, `compress`, `format`, `mvencode` |
| `renames` | Renames variable(s) | `rename` |
| `removes` | Removes variable(s) from dataset | `drop`, `keep` (keeps and drops others) |
| `labels` | Attaches or modifies variable/value labels | `label` |
| `restructures` | Changes the shape or ordering of the dataset | `reshape`, `merge`, `append`, `sort`, `collapse`, `xpose`, `stack` |
| `none` | Does not affect variables (or purely observational) | `describe`, `summarize`, `list`, `tabulate`, `count`, `display` |

### 3.4 Commands requiring a non-`none` value (proposed for human review)

| Command | Proposed value | Notes |
|---------|---------------|-------|
| `generate` | `creates` | |
| `egen` | `creates` | Ambiguous: behaviour depends on function called. See 3.5. |
| `replace` | `modifies` | |
| `rename` | `renames` | |
| `drop` | `removes` | |
| `keep` | `removes` | Keeps specified, drops all others |
| `encode` | `creates` | Creates a new numeric variable from string |
| `decode` | `creates` | Creates a new string variable from numeric |
| `recode` | `modifies` | Ambiguous: can create with `generate()`. See 3.5. |
| `compress` | `modifies` | Changes storage type, no new variables |
| `expand` | `modifies` | Multiplies rows (restructures) |
| `fillin` | `creates` | Creates missing observations to fill grid |
| `generate` | `creates` | |
| `rename` | `renames` | |
| `sort` | `restructures` | Changes row order, no variables added/removed |
| `gsort` | `restructures` | |
| `order` | `restructures` | Reorders columns |
| `merge` | `restructures` | Ambiguous: creates `_merge` variable. See 3.5. |
| `append` | `restructures` | |
| `collapse` | `restructures` | |
| `reshape` | `restructures` | |
| `xpose` | `restructures` | |
| `stack` | `restructures` | |
| `cross` | `restructures` | |
| `joinby` | `restructures` | |
| `contract` | `restructures` | |
| `separate` | `creates` | Creates one indicator per group |
| `split` | `creates` | Creates new variables from string parts |
| `mvencode` | `modifies` | |
| `mvdecode` | `modifies` | |
| `tostring` | `creates` | Creates new string variable |
| `destring` | `creates` | Creates new numeric variable |
| `ipolate` | `creates` | |
| `predict` | `creates` | |
| `margins` | `creates` | Creates new estimation results |
| `label` | `labels` | |
| `format` | `modifies` | Changes display format (not values) |
| `snapshot` | `none` | Saves/restores snapshot; doesn't modify variables |
| `preserve` | `none` | Saves current state |
| `restore` | `none` | Restores preserved state |
| `save` | `none` | Writes to disk; doesn't modify in-memory variables |
| `use` | `none` | Loads data; "creates" is technically correct but misleading |
| `import` | `creates` | Loads data from external format |
| `export` | `none` | Writes to disk |
| `clear` | `removes` | Drops entire dataset |
| `tabulate` | `none` | Observational |
| `summarize` | `none` | Observational |
| `list` | `none` | Observational |
| `describe` | `none` | Observational |
| `count` | `none` | Observational |
| `display` | `none` | Observational |
| `regress` | `none` | Produces estimation results, not variables |
| `logit` | `none` | Same as regress |
| `anova` | `none` | Same |

*(Only the ~50 commands in data_management + a few in statistics are listed here. The full table would include all 669 commands. Most estimation commands have `none`.)*

### 3.5 Ambiguous cases requiring human decision

These commands cannot be cleanly assigned a single value:

| Command | Issue | Recommendation |
|---------|-------|---------------|
| **`egen`** | Behavior depends entirely on the function called. `egen mean = price)` creates; `egen tag = tag(make)` creates; but `egen count = count(price)` also creates. However, some `egen` variants (like `rownonmiss`) modify existing. | Assign `creates` as the safe default. Most `egen` functions create new variables. |
| **`recode`** | Without `generate()`, it modifies in place. With `generate(newvar)`, it creates a new variable. | Assign `modifies` as the default, since the common use case without `generate()` is modification. Document the ambiguity in the `description` field. |
| **`merge`** | Primarily restructures (joins datasets), but also creates the `_merge` indicator variable. | Assign `restructures`. The `_merge` variable is an artifact of the merge process, not its primary purpose. Document in description. |
| **`sort`** | Changes row order only. No variables added, removed, or modified. | Assign `restructures`. Row order is a structural property of the dataset. |
| **`keep`** | Removes variables, but which ones remain is determined by the command. | Assign `removes`. |
| **`append`** | Primarily restructures (extends dataset vertically). May create variables if the using dataset has columns the master doesn't. | Assign `restructures`. |

### 3.6 Reader API addition

Add to `stata_registry/__init__.py`:

```python
def variable_effect(command: str) -> str:
    """Return the variable_effect value for *command* (e.g. 'creates', 'none').

    Raises ``KeyError`` if *command* is not recognised.
    Raises ``ValueError`` if the entry has no variable_effect field.
    """
```

### 3.7 Version change

This is a **MINOR** version bump: `0.1.0` → `0.2.0`.

Rationale:
- Adding an optional field to the schema is backward-compatible (existing YAML validates).
- Adding a new API function is backward-compatible.
- No existing function's behavior changes.
- MINOR is correct per semver: new functionality in a backwards-compatible manner.

---

## Part 2 — Abbreviation Contract Decision

### Discrepancy

| Source | Says |
|--------|------|
| README field reference | "Shortest accepted forms (all intermediate forms between the shortest and name are implied)" |
| Schema `description` | Example: `['reg', 'regr'] for 'regress'` — implies enumeration of listed forms |
| Actual YAML data | Enumerates ALL intermediate forms: `[reg, regr, regre, regres]` |
| Reader code | `for abbrev in cmd.get("abbreviations") or []:` — enumeration, no generation |

All four disagree. The README says "shortest only", but the data and code both enumerate everything.

### Recommended contract: **Enumeration**

Adopt the convention that `abbreviations` lists every valid abbreviation explicitly. The reader does not generate intermediate forms.

**Tradeoff:**

| Approach | Pros | Cons |
|----------|------|------|
| Enumeration (recommended) | Explicit, no overgeneration, reader is trivial, testable | Verbose entries, must maintain completeness |
| Implied intermediates | Compact entries | Reader must generate forms, can overgenerate for commands where Stata does NOT accept all intermediates (e.g., `display` abbreviates to `di`, not `d`) |

The enumeration contract is the only safe choice because Stata's abbreviation rules are **not uniform**: some commands abbreviate to all intermediates, some don't. For example:
- `generate`: abbreviates to `g` but not intermediate forms shorter than `ge` in some contexts
- `display`: abbreviates to `di` but not `d`
- `describe`: abbreviates to `d` but not intermediate forms between `d` and `de`

Implied intermediates would overgenerate for these commands.

### Action items

1. Update README field reference to: "All accepted abbreviation forms, listed explicitly."
2. Update schema description to match.
3. Review and correct all abbreviation lists (fix B-3, B-4, B-5).

---

## Decisions Table

These questions require a human answer before implementation can proceed.

| # | Question | Options | Recommendation |
|---|----------|---------|---------------|
| D-1 | **Abbreviation contract:** enumeration vs implied intermediates? | A: Enumeration (explicit, new README recommendation)  B: Implied intermediates (current README field reference, not current reader) | **A: Enumeration.** Only safe option given Stata's non-uniform abbreviation rules. |
| D-2 | **How to represent "no abbreviations allowed"?** | A: Explicit `abbreviations: []`  B: Separate field `abbreviatable: false`  C: Convention that absent = none | **A: Explicit `abbreviations: []`.** Absent field should mean "not yet classified" to distinguish deliberate prevention from incomplete data. |
| D-3 | **Should `in` and `of` remain as entries?** | A: Remove entirely  B: Move to `syntax_fragment` category excluded from `is_command()`  C: Keep as-is | **A or B.** `in` and `of` are not commands. do2py will misparse if they register as commands. |
| D-4 | **`is_prefix` / `is_control_flow` coupling: explicit fields or keep category-derived?** | A: Add `is_prefix: true` / `is_control_flow: true` boolean fields  B: Keep as-is (category-derived) | **A.** The category key is cosmetic (TextMate scope). Parser identity must not depend on it. |
| D-5 | **`variable_effect` values for ambiguous commands** (see Part 3.5 table)? | Review the proposed values and resolve the ambiguous cases | Needs maintainer input on egen, recode, merge, sort, keep. |
| D-6 | **`sort` variable_effect: `restructures` or `none`?** | Sort changes row order only. No variables added/removed/modified. | `restructures` — row order is structural to the dataset. |
| D-7 | **Data directory duplication resolution?** | A: Symlink data/ -> commands/  B: Build step copies commands/ -> data/  C: Keep as-is with CI sync check | **B.** Build step at package time. |
| D-8 | **`use` abbreviation `us`: valid in Stata or not?** | Verify against Stata 19 documentation | If Stata does not abbreviate `use`, remove `us`. |
| D-9 | **Version after all fixes: v0.2.0 (MINOR)?** | Adding variable_effect + abbreviation fixes | Yes: v0.2.0 for new field + corrected data. Create missing v0.1.0 tag on current commit first. |

---

## Test Suite

Committed under `tests/` as five new files plus the original `test_registry.py`:

| File | What it tests | Pass | xfail | skip |
|------|---------------|------|-------|------|
| `test_registry.py` | Original API tests (is_command, canonical_command, etc.) | 28 | 0 | 0 |
| `test_data_integrity.py` | Schema conformance, uniqueness, required fields, reserved words, coverage | 37 | 0 | 0 |
| `test_abbreviations.py` | Abbreviation semantics, non-abbreviable commands, real Stata verification | 8 | 8 | 0 |
| `test_api.py` | Documented examples, semantic coupling, aliases, edge inputs, constraints | 24 | 1 | 1 |
| `test_variable_effect.py` | Variable_effect field and accessor existence | 1 | 3 | 0 |
| `test_packaging.py` | Duplicate data, egg-info, pip install, tag, test completeness | 5 | 4 | 0 |
| `test_stataglow_migration.py` | stataGlow migration status | 0 | 1 | 1 |
| **Total** | | **103** | **17** | **2** |

All xfail tests document known defects. They will **pass** when the defect is fixed (due to `strict=True` on critical ones), serving as a natural migration checklist.

---

## Appendix: Full list of xfail tests and what they encode

| Test | xfail reason |
|------|-------------|
| `test_implied_intermediate_resolves` | Documents that `genr` is NOT in YAML; reader doesn't generate intermediates |
| `test_replace_abbreviations_field_present` | replace has no abbreviations field (can't distinguish "none allowed" from "not done") |
| `test_egen_abbreviations_field_present` | Same for egen |
| `test_destring_abbreviations_field_present` | Same for destring |
| `test_generate_abbreviates_to_g` | `g` missing from generate abbreviations |
| `test_generate_shortest_abbreviation_in_yaml` | Same defect, YAML-level check |
| `test_describe_abbreviation_d_in_yaml` | `d` missing from describe abbreviations |
| `test_list_abbreviation_l_in_yaml` | `l` missing from list abbreviations |
| `test_readme_field_reference_matches_code` | README says "shortest", code does enumeration |
| `test_is_prefix_not_category_derived` | is_prefix derived from category key name |
| `test_alias_resolves` | No aliases exist to test (code support is untested) |
| `test_no_manual_duplicate` | data/ is a manual copy, not symlink/generated |
| `test_egg_info_not_tracked` | .egg-info committed to git |
| `test_v010_tag_exists` | v0.1.0 tag missing |
| `test_variable_effect_in_official_yaml` | variable_effect absent from YAML |
| `test_variable_effect_accessor_exists` | No variable_effect() function |
| `test_variable_effect_full_stack` | Full stack absent |
| `test_stataglow_grammar_unchanged_after_migration` | Migration not done |