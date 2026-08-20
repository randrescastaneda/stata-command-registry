# stata-command-registry

<!-- cg:auto:overview -->
**stata-command-registry** is the single source of truth for the Stata command
vocabulary. Command definitions are held as versioned YAML data and consumed by
downstream tooling — notably [stataGlow](https://github.com/randrescastaneda/stataGlow)
(VS Code / Positron syntax highlighting) and `do2screen-py` (do-file tracing) —
so that command lists are never duplicated across projects.

The repository ships two artifacts:

- **`commands/`** — human-editable YAML registries (official Stata commands,
  SSC-contributed packages, GitHub-contributed packages) plus a JSON Schema
  (`commands/schema.json`) that validates the YAML format.
- **`stata_registry/`** — a thin, installable Python reader package that
  bundles the YAML data and exposes a lookup API
   (`is_command`, `canonical_command`, `category`, `variable_effect`,
   `is_prefix`, `is_control_flow`).

**Constraints.** This project is data and lookup only: no parsing logic, no
regular expressions, and no runtime dependencies beyond PyYAML. Abbreviations
are recorded as data (not derived), every entry is verifiable against the
official Stata docs, the registry is descriptive (not normative), and releases
follow [Semantic Versioning](https://semver.org/). Supported Python: **>=3.9**.
Licensed under MIT.
<!-- cg:auto:end -->

## Contents

- [API Reference](api-reference.md)
- [Vignettes](vignettes.md)
- [Changelog](changelog.md)

<!-- cg:auto:installation -->
### Install from PyPI

```bash
pip install stata-registry
```

### Install from source (this repo)

```bash
pip install git+https://github.com/randrescastaneda/stata-command-registry.git@v0.2.0
```

**Requirements:** Python >= 3.9. The only runtime dependency is
`pyyaml>=5.1`, which is declared in `pyproject.toml` and installed automatically.

### Verify a source release

From a checkout, run the test suite, validate every YAML registry, and build the
release wheel:

```bash
python -m pytest
check-jsonschema --schemafile commands/schema.json commands/*.yaml
python -m build
```

Install the generated `0.2.0` wheel from outside the repository root and verify
its package metadata, bundled YAML data, and public lookup API before publishing.
<!-- cg:auto:end -->

<!-- cg:auto:quick-start -->
```python
import stata_registry as sr

sr.is_command("regress")          # True
sr.is_command("reg")              # True  (abbreviation)
sr.is_command("notacommand")      # False
sr.is_command("in")               # False (syntax fragment, not a command)
sr.is_command("of")               # False (syntax fragment, not a command)
sr.is_command("us")               # False (not a `use` abbreviation)

sr.canonical_command("reg")       # "regress"
sr.canonical_command("gen")       # "generate"
sr.canonical_command("bys")       # "bysort"

sr.category("regress")            # "statistics"
sr.category("foreach")            # "control_flow"
sr.category("quietly")            # "prefix_control"

sr.is_prefix("bysort")            # True
sr.is_prefix("quietly")           # True
sr.is_prefix("regress")           # False

sr.is_control_flow("foreach")     # True
sr.is_control_flow("if")          # True
sr.is_control_flow("regress")     # False
sr.variable_effect("generate")   # "creates"
```

Registry abbreviations are explicit data: unlisted intermediate forms are not
inferred. `variable_effect()` reports the documented primary effect; option-
dependent or secondary effects require separate analysis.

The lookup tables are built lazily on first call and are thread-safe. See
[API Reference](api-reference.md) for the full function signatures and
[Vignettes](vignettes.md) for consumer integration patterns.
<!-- cg:auto:end -->
