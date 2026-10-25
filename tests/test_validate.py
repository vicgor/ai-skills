import pytest
import yaml

import validate
from validate import check_eval_structure, check_templates


# --- check_templates -------------------------------------------------------


@pytest.fixture
def skill_repo(tmp_path, monkeypatch):
    """Пустой репозиторий с common/style.md; write(id, data) кладёт скилл и возвращает registry."""
    common = tmp_path / "common"
    common.mkdir()
    (common / "style.md").write_text("style")
    monkeypatch.setattr(validate, "ROOT", tmp_path)
    monkeypatch.setattr(validate, "COMMON_DIR", common)

    def write(data):
        path = tmp_path / "skill.yaml"
        path.write_text(yaml.safe_dump(data, allow_unicode=True))
        return {"domains": {"t": {"skills": [{"id": "t.s", "file": "skill.yaml"}]}}}

    return write


def skill(template, required=("goal",), optional=()):
    return {
        "prompt_template": template,
        "inputs": {
            "required": [{"name": n} for n in required],
            "optional": [{"name": n} for n in optional],
        },
    }


def test_templates_valid_skill_ok(skill_repo):
    registry = skill_repo(skill('{common_style} {goal} {ctx} {{"json": 1}}', optional=["ctx"]))
    assert check_templates(registry) == ([], [])


def test_templates_undeclared_placeholder_is_error(skill_repo):
    errors, _ = check_templates(skill_repo(skill("{goal} {typo}")))
    assert any("[TEMPLATE VAR]" in e and "{typo}" in e for e in errors)
    assert any("[TEMPLATE RENDER]" in e for e in errors)


def test_templates_literal_json_braces_are_error(skill_repo):
    errors, _ = check_templates(skill_repo(skill('{goal} {"json": 1}')))
    assert any("[TEMPLATE VAR]" in e for e in errors)


def test_templates_single_brace_is_syntax_error(skill_repo):
    errors, _ = check_templates(skill_repo(skill("{goal} {")))
    assert len(errors) == 1
    assert errors[0].startswith("[TEMPLATE SYNTAX]")


def test_templates_empty_placeholder_is_error(skill_repo):
    errors, _ = check_templates(skill_repo(skill("{goal} {}")))
    assert any("пустой плейсхолдер" in e for e in errors)


def test_templates_unused_input_is_warning(skill_repo):
    errors, warnings = check_templates(skill_repo(skill("{goal}", optional=["unused"])))
    assert errors == []
    assert warnings == ["[UNUSED INPUT] t.s — вход 'unused' не используется в prompt_template"]


def test_templates_attribute_access_uses_base_name(skill_repo):
    errors, _ = check_templates(skill_repo(skill("{goal.upper}")))
    assert not any("[TEMPLATE VAR]" in e for e in errors)


# --- check_eval_structure --------------------------------------------------


REGISTRY = {"domains": {"git": {"skills": [{"id": "git.resolve", "file": "skills/git/resolve.yaml"}]}}}


@pytest.fixture
def write_cases(tmp_path, monkeypatch):
    evals = tmp_path / "evals"
    (evals / "git").mkdir(parents=True)
    monkeypatch.setattr(validate, "ROOT", tmp_path)
    monkeypatch.setattr(validate, "EVALS_DIR", evals)

    def write(cases, skill_id="git.resolve"):
        (evals / "git" / "resolve.cases.yaml").write_text(
            yaml.safe_dump({"skill_id": skill_id, "cases": cases}, allow_unicode=True)
        )
        return check_eval_structure(REGISTRY)

    return write


def case(**overrides):
    base = {"id": "c1", "description": "d", "input": {"x": "y"}, "expected": {"must_contain": ["a"]}}
    base.update(overrides)
    return base


def test_eval_valid_case_ok(write_cases):
    expected = {
        "must_contain": ["a", ["b", "c"]],
        "should_not_contain": ["d"],
        "should_not_match": [r"^\s*<<<<<<< "],
        "quality": {"has_x": True},
    }
    assert write_cases([case(expected=expected)]) == ([], [])


def test_eval_wrong_skill_id(write_cases):
    errors, _ = write_cases([case()], skill_id="git.other")
    assert any("[EVAL SKILL_ID]" in e for e in errors)


def test_eval_expect_instead_of_expected(write_cases):
    c = case()
    c["expect"] = c.pop("expected")
    errors, _ = write_cases([c])
    assert any("используй 'expected'" in e for e in errors)
    assert any("нет ключа 'expected'" in e for e in errors)


def test_eval_duplicate_ids(write_cases):
    errors, _ = write_cases([case(), case()])
    assert any("[EVAL DUPLICATE]" in e for e in errors)


def test_eval_unknown_key_is_warning(write_cases):
    errors, warnings = write_cases([case(notes="x")])
    assert errors == []
    assert any("неизвестный ключ 'notes'" in w for w in warnings)


def test_eval_empty_expected(write_cases):
    errors, _ = write_cases([case(expected={})])
    assert any("пустой expected" in e for e in errors)


def test_eval_expected_only_should_not_match_is_not_empty(write_cases):
    assert write_cases([case(expected={"should_not_match": ["x"]})]) == ([], [])


@pytest.mark.parametrize("bad", ["a", [1], [[]], [["a", 2]]])
def test_eval_must_contain_must_be_list_of_strings(write_cases, bad):
    errors, _ = write_cases([case(expected={"must_contain": bad})])
    assert any("'must_contain' должен быть списком строк" in e for e in errors)


def test_eval_invalid_regex(write_cases):
    errors, _ = write_cases([case(expected={"should_not_match": ["(unclosed"]})])
    assert any("невалидный regex" in e for e in errors)


def test_eval_should_not_match_must_be_list(write_cases):
    errors, _ = write_cases([case(expected={"should_not_match": "x"})])
    assert any("'should_not_match' должен быть списком" in e for e in errors)


def test_eval_quality_must_be_dict(write_cases):
    errors, _ = write_cases([case(expected={"quality": ["has_x"]})])
    assert any("'quality' должен быть словарём" in e for e in errors)


# --- реальный репозиторий --------------------------------------------------


def test_repository_passes_validation():
    assert validate.main() == 0
