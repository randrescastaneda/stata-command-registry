# Changelog

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** — incompatible changes to the YAML schema or the Python API.
- **MINOR** — new commands or categories added in a backwards-compatible way.
- **PATCH** — corrections to existing entries.

Consumers should pin to a minor version, e.g. `stata-registry>=0.4,<0.5`.

<!-- cg:auto:version-history -->
## Version history

### 0.4.0 — 2026-08-21

- Added the explicit `include_driver` boolean field to every shipped command
  entry and defined it in the JSON schema.
- Classified `do`, `run`, and `include` as source drivers using official
  StataNow 19 help documentation.
- Added `is_include(token)`, which resolves canonical names, abbreviations, and
  aliases and returns `False` for unknown or non-driver tokens.
- Added a reproducible source-to-bundled-data generation/check pipeline and
  documented that source-driver metadata is independent of `variable_effect`.
- Bumped the package version to `0.4.0`.

### 0.3.0 — 2026-08-20

- Removed tracked generated package metadata and interpreter bytecode.
- Added strict packaging tests that keep generated artifacts out of git.
- Updated release guidance and package metadata for the `v0.3.0` tag.

### 0.2.0 — 2026-08-20

- Added the `variable_effect` schema field and `variable_effect()` lookup API.
- Documented the primary-effect semantics and resolved ambiguous-command defaults.
- Corrected the explicit abbreviation contract and key Stata abbreviations.
- Removed `in` and `of` as standalone registry commands and removed `us` from
  `use`.
- Added release and packaged-data verification coverage, including schema
  validation, wheel builds, and an install from outside the repository root.

### 0.1.0 — 2026-08-15

Initial public release.

- YAML command registries under `commands/`:
  - `official_stata_commands.yaml`
  - `ssc_contributed_commands.yaml`
  - `github_contributed_commands.yaml`
- JSON Schema (`commands/schema.json`) defining the YAML entry format.
- `stata_registry` Python reader package with the lookup API:
  `is_command`, `canonical_command`, `category`, `variable_effect`, `is_prefix`,
  `is_control_flow`.
- Bundled data YAML under `stata_registry/data/`.
- `pytest` test suite under `tests/`.
- MIT license.

> Note: This entry was synthesised from the repository state at wiki
> initialization. Replace or extend it with authoritative release notes as
> tags are cut.
<!-- cg:auto:end -->

← [Home](README.md)
