# stata-command-registry

A standalone repository of official and community-contributed Stata command
definitions, together with a tiny Python reader module.

Both [stataGlow](https://github.com/randrescastaneda/stataGlow) (VS Code / Positron
syntax highlighting) and third-party Stata parsers can consume this package as a
single source of truth, avoiding duplicated command lists.

---

## Repository layout

```
commands/                        # Human-editable YAML registries
  official_stata_commands.yaml
  ssc_contributed_commands.yaml
  github_contributed_commands.yaml
  schema.json                    # JSON Schema for the YAML format

stata_registry/                  # Installable Python package
  __init__.py
  data/                          # YAML files bundled with the package

tests/
  test_registry.py
```

---

## YAML entry format

Each YAML file must conform to `commands/schema.json`.  The top-level structure
is:

```yaml
metadata:
  version: "19.0"          # Stata version (required)
  last_updated: "2026-01-01"
  source: stata.com/help   # Origin of the data (required)

categories:
  <category_key>:
    description: "Human-readable label"
    scope: keyword.functions.data.stata   # TextMate grammar scope (optional)
    commands:
      - name: regress                     # canonical command name (required)
        abbreviations: [reg, regr, regre, regres]  # accepted short forms
        variable_effect: none              # primary effect on variables/data structure
        aliases: []                       # alternative full names
        since: "3.0"                      # Stata version introduced (optional)
        status: stable                    # stable | experimental | deprecated
        description: "OLS linear regression"
        url: "https://www.stata.com/help.cgi?regress"
```

### Field reference

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✓ | Primary, canonical command name |
| `abbreviations` | | All accepted abbreviation forms (listed explicitly) |
| `variable_effect` | | Primary effect: `creates`, `modifies`, `renames`, `removes`, `labels`, `restructures`, or `none`; optional for legacy documents, required for shipped entries |
| `aliases` | | Alternative full names treated identically to `name` |
| `scope` | | Per-command TextMate scope override (inherits from category if absent) |
| `since` | | Stata version that introduced the command |
| `status` | | `stable` (default), `experimental`, or `deprecated` |
| `description` | | One-line description |
| `url` | | Link to Stata help page |

`variable_effect` records the command's primary effect. The shipped defaults for
ambiguous commands are `egen: creates`, `recode: modifies`,
`merge`/`append`/`sort: restructures`, and `keep: removes`. Option-dependent or
secondary effects are outside this scalar field's primary-effect contract.

---

## Contributing a command

1. Identify the correct registry file:
   - **Official Stata commands** → `commands/official_stata_commands.yaml`
   - **SSC-hosted community packages** → `commands/ssc_contributed_commands.yaml`
   - **GitHub community packages** → `commands/github_contributed_commands.yaml`

2. Add an entry under the most appropriate `category` key.  Create a new
   category only when none of the existing ones fits.

3. Validate your changes against the schema:

   ```bash
   pip install check-jsonschema
   check-jsonschema --schemafile commands/schema.json commands/official_stata_commands.yaml
   ```

4. Open a pull request with a brief description of the command.

---

## Python package

### Installation

```bash
pip install stata-registry          # once published to PyPI
# or directly from this repo:
pip install git+https://github.com/randrescastaneda/stata-command-registry.git@v0.2.0
```

### API

```python
import stata_registry as sr

sr.is_command("regress")            # True
sr.is_command("reg")                # True  (abbreviation)
sr.is_command("notacommand")        # False

sr.canonical_command("reg")         # "regress"
sr.canonical_command("gen")         # "generate"
sr.canonical_command("bys")         # "bysort"

sr.category("regress")              # "statistics"
sr.category("foreach")              # "control_flow"
sr.category("quietly")              # "prefix_control"

sr.is_prefix("bysort")              # True
sr.is_prefix("quietly")             # True
sr.is_prefix("regress")             # False

sr.is_control_flow("foreach")       # True
sr.is_control_flow("if")            # True
sr.is_control_flow("regress")       # False

sr.variable_effect("generate")      # "creates"
sr.variable_effect("replace")       # "modifies"
sr.variable_effect("drop")          # "removes"
sr.variable_effect("sort")          # "restructures"
sr.variable_effect("label")         # "labels"
sr.variable_effect("regress")       # "none"
```

**Constraints:** data and lookup only — no parsing logic, no regular
expressions, no dependencies beyond PyYAML.

---

## Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible changes to the YAML schema or the Python API.
- **MINOR** version for new commands or categories added in a backwards-compatible way.
- **PATCH** version for corrections to existing entries.

Consumers should pin to a minor version, e.g. `stata-registry>=0.2,<0.3`.

---

## License

MIT — see [LICENSE](LICENSE).
