import pytest

import run_evals
from run_evals import check_expected, resolve_placeholder, safe_name


class TestCheckExpected:
    def test_empty_expected_passes(self):
        assert check_expected("anything", {}) == []

    def test_must_contain_is_case_insensitive(self):
        assert check_expected("Use SHOW PROCESSLIST here", {"must_contain": ["show processlist"]}) == []

    def test_must_contain_missing_substring_fails(self):
        failures = check_expected("nothing relevant", {"must_contain": ["KILL"]})
        assert failures == ["нет обязательной подстроки: 'KILL'"]

    def test_must_contain_any_of_passes_on_one_option(self):
        assert check_expected("Если только нужно", {"must_contain": [["Unless", "если только"]]}) == []

    def test_must_contain_any_of_fails_when_no_option_found(self):
        failures = check_expected("ничего", {"must_contain": [["Unless", "если только"]]})
        assert len(failures) == 1
        assert "Unless" in failures[0]

    def test_should_not_contain_found_fails(self):
        failures = check_expected("сначала web_search, затем fetch", {"should_not_contain": ["Сначала web_search"]})
        assert failures == ["найдена запрещённая подстрока: 'Сначала web_search'"]

    def test_failures_from_all_checks_are_collected(self):
        expected = {"must_contain": ["a", "b"], "should_not_contain": ["c"]}
        assert len(check_expected("c", expected)) == 3


CONFLICT_MARKER = r"^\s*(<<<<<<<|>>>>>>>)( |$)"


class TestShouldNotMatch:
    @pytest.mark.parametrize(
        "output",
        [
            "<<<<<<< HEAD\nimport yaml",
            "code\n<<<<<<< feature/json-output\n",
            "  >>>>>>> feature/x",
            "x = 1\n>>>>>>>\n",
        ],
    )
    def test_unresolved_marker_at_line_start_fails(self, output):
        assert check_expected(output, {"should_not_match": [CONFLICT_MARKER]}) != []

    @pytest.mark.parametrize(
        "output",
        [
            "Проверь, что не осталось `<<<<<<<` и `>>>>>>>`.",
            "git grep -n -E '^(<<<<<<<|=======|>>>>>>>)' -- file.py",
            "<<<<<<<< not a marker",
            "import yaml\nimport json\n",
        ],
    )
    def test_quoted_or_absent_markers_pass(self, output):
        assert check_expected(output, {"should_not_match": [CONFLICT_MARKER]}) == []

    def test_pattern_is_case_sensitive(self):
        assert check_expected("kill 42", {"should_not_match": [r"^KILL"]}) == []


class TestResolvePlaceholder:
    def test_plain_value_unchanged(self):
        assert resolve_placeholder("def main(): ...") == "def main(): ..."

    def test_missing_file_keeps_placeholder(self, tmp_path, monkeypatch):
        monkeypatch.setattr(run_evals, "ROOT", tmp_path)
        assert resolve_placeholder("<см. examples/nope.md>") == "<см. examples/nope.md>"

    def test_returns_first_code_block(self, tmp_path, monkeypatch):
        monkeypatch.setattr(run_evals, "ROOT", tmp_path)
        (tmp_path / "ex.md").write_text("# Пример\n\n```python\nprint(1)\n```\n\n```bash\nls\n```\n")
        assert resolve_placeholder("  <см. ex.md>  ") == "print(1)"

    def test_returns_whole_file_without_code_blocks(self, tmp_path, monkeypatch):
        monkeypatch.setattr(run_evals, "ROOT", tmp_path)
        (tmp_path / "ex.md").write_text("просто текст")
        assert resolve_placeholder("<см. ex.md>") == "просто текст"


def test_safe_name_replaces_unsafe_chars():
    assert safe_name("db-sql.write-migration__drop col/1") == "db-sql.write-migration__drop_col_1"
