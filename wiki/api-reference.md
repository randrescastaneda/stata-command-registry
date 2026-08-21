# API Reference

The `stata_registry` package exposes seven pure-lookup functions. All of them
operate over the YAML registries bundled with the package (under
`stata_registry/data/`) and share a lazily-built, thread-safe in-memory index.
There is no parsing or regex involved — every lookup is a dictionary/set
membership check.

<!-- cg:auto:functions -->
## Functions

### `is_command(token)`

Return `True` if `token` is a known Stata command name, abbreviation, or alias;
otherwise `False`. Never raises.

### `canonical_command(token)`

Resolve `token` to its canonical (full) command name. Accepts the canonical
name itself, any recorded abbreviation, or any alias. Raises `KeyError` if
`token` is not a recognised command or abbreviation.

### `category(command)`

Return the registry category key for `command` (e.g. `"statistics"`,
`"control_flow"`, `"prefix_control"`). `command` may be a canonical name or a
known abbreviation. Raises `KeyError` if `command` is not recognised.

### `variable_effect(command)`

Return the primary `variable_effect` value for `command`: `creates`, `modifies`,
`renames`, `removes`, `labels`, `restructures`, or `none`. The shipped defaults
for ambiguous commands are `egen: creates`, `recode: modifies`,
`merge`/`append`/`sort: restructures`, and `keep: removes`. Option-dependent or
secondary effects are outside this scalar field's primary-effect contract. The
field is optional for legacy YAML documents, but every shipped registry entry
has a valid enum value.
Raises `KeyError` for an unknown command and `ValueError` for a legacy entry
without the field.

### `is_prefix(command)`

Return `True` if `command` is a Stata prefix command — i.e. a command that
appears before another command and modifies how it executes (e.g. `bysort`,
`quietly`, `capture`, `noisily`). Returns `False` for unknown tokens (never
raises). `command` may be an abbreviation.

### `is_control_flow(command)`

Return `True` if `command` is a control-flow keyword (e.g. `foreach`,
`forvalues`, `if`, `else`, `while`). Returns `False` for unknown tokens (never
raises). `command` may be an abbreviation.

### `is_include(token)`

Return `True` if `token` resolves to a command whose registry entry has
`include_driver: true`, meaning that it executes commands stored in another
Stata source file. Accepts canonical names, explicit abbreviations, and aliases
using the same resolution policy as `canonical_command`. Returns `False` for
unknown tokens and known non-source-driver commands. It does not infer from
`variable_effect`.
<!-- cg:auto:end -->

<!-- cg:auto:parameters -->
## Parameters

| Function | Parameter | Type | Required | Notes |
|----------|-----------|------|----------|-------|
| `is_command` | `token` | `str` | yes | Any string to test against the registry. |
| `canonical_command` | `token` | `str` | yes | A canonical name, abbreviation, or alias. |
| `category` | `command` | `str` | yes | Canonical name or abbreviation. |
| `variable_effect` | `command` | `str` | yes | Canonical name or abbreviation. |
| `is_prefix` | `command` | `str` | yes | Canonical name or abbreviation. |
| `is_control_flow` | `command` | `str` | yes | Canonical name or abbreviation. |
| `is_include` | `token` | `str` | yes | Canonical name, abbreviation, or alias. |

All parameters are required strings and may be passed positionally or by
keyword. No optional flags are accepted — the API is intentionally minimal.
<!-- cg:auto:end -->

<!-- cg:auto:return-values -->
## Return values

| Function | Return type | On success | On unknown token |
|----------|-------------|------------|------------------|
| `is_command` | `bool` | `True` | `False` |
| `canonical_command` | `str` | the canonical command name | raises `KeyError` |
| `category` | `str` | the category key (e.g. `"statistics"`) | raises `KeyError` |
| `variable_effect` | `str` | the primary effect enum value | raises `KeyError` or `ValueError` |
| `is_prefix` | `bool` | `True` / `False` | `False` |
| `is_control_flow` | `bool` | `True` / `False` | `False` |
| `is_include` | `bool` | `True` / `False` | `False` |

The `KeyError` raised by `canonical_command` and `category` carries a message
of the form `Unknown Stata command or abbreviation: '<token>'`.

The in-memory index is built once on first access (guarded by a module-level
`threading.Lock`) and reused for all subsequent calls; there is no per-call
YAML parse.
<!-- cg:auto:end -->

← [Home](README.md)
