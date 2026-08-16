import pytest
import stata_registry as sr


class TestIsCommand:
    def test_canonical_name(self):
        assert sr.is_command("regress") is True

    def test_abbreviation(self):
        assert sr.is_command("reg") is True
        assert sr.is_command("gen") is True

    def test_unknown(self):
        assert sr.is_command("notacommand") is False

    def test_case_sensitive(self):
        # Stata commands are lowercase; uppercase should not match
        assert sr.is_command("Regress") is False


class TestCanonicalCommand:
    def test_abbreviation_resolves(self):
        assert sr.canonical_command("reg") == "regress"
        assert sr.canonical_command("gen") == "generate"
        assert sr.canonical_command("ge") == "generate"

    def test_full_name_returns_itself(self):
        assert sr.canonical_command("regress") == "regress"
        assert sr.canonical_command("generate") == "generate"

    def test_unknown_raises(self):
        with pytest.raises(KeyError):
            sr.canonical_command("notacommand")

    def test_bysort_abbreviations(self):
        for abbrev in ("by", "bys", "byso", "bysor"):
            assert sr.canonical_command(abbrev) == "bysort"


class TestCategory:
    def test_regress_statistics(self):
        assert sr.category("regress") == "statistics"

    def test_generate_data_management(self):
        assert sr.category("generate") == "data_management"

    def test_foreach_control_flow(self):
        assert sr.category("foreach") == "control_flow"

    def test_quietly_prefix_control(self):
        assert sr.category("quietly") == "prefix_control"

    def test_abbreviation_resolves_category(self):
        # "reg" -> "regress" -> "statistics"
        assert sr.category("reg") == "statistics"

    def test_unknown_raises(self):
        with pytest.raises(KeyError):
            sr.category("notacommand")


class TestIsPrefix:
    def test_bysort(self):
        assert sr.is_prefix("bysort") is True

    def test_bysort_abbrev(self):
        assert sr.is_prefix("bys") is True

    def test_quietly(self):
        assert sr.is_prefix("quietly") is True

    def test_capture(self):
        assert sr.is_prefix("capture") is True

    def test_noisily(self):
        assert sr.is_prefix("noisily") is True

    def test_non_prefix(self):
        assert sr.is_prefix("regress") is False

    def test_unknown(self):
        assert sr.is_prefix("notacommand") is False


class TestIsControlFlow:
    def test_foreach(self):
        assert sr.is_control_flow("foreach") is True

    def test_forvalues(self):
        assert sr.is_control_flow("forvalues") is True

    def test_if(self):
        assert sr.is_control_flow("if") is True

    def test_else(self):
        assert sr.is_control_flow("else") is True

    def test_while(self):
        assert sr.is_control_flow("while") is True

    def test_non_control_flow(self):
        assert sr.is_control_flow("regress") is False

    def test_unknown(self):
        assert sr.is_control_flow("notacommand") is False
