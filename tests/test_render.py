import click
import pytest

from render import load_common, render_prompt


def make_skill(template, required=(), optional=()):
    return {
        "prompt_template": template,
        "inputs": {"required": list(required), "optional": list(optional)},
    }


def test_load_common_exposes_modules_with_prefix():
    common = load_common()
    assert {"common_style", "common_safety", "common_output_formats"} <= common.keys()


def test_required_and_optional_default_are_substituted():
    skill = make_skill(
        "{goal} on {engine}",
        required=[{"name": "goal"}],
        optional=[{"name": "engine", "default": "mariadb"}],
    )
    assert render_prompt(skill, {"goal": "speed up"}) == "speed up on mariadb"


def test_explicit_value_overrides_default():
    skill = make_skill("{engine}", optional=[{"name": "engine", "default": "mariadb"}])
    assert render_prompt(skill, {"engine": "postgresql"}) == "postgresql"


def test_optional_without_default_becomes_empty():
    skill = make_skill("[{context}]", optional=[{"name": "context"}])
    assert render_prompt(skill, {}) == "[]"


def test_missing_required_warns_then_raises(capsys):
    skill = make_skill("code: {current_code}", required=[{"name": "current_code"}])
    with pytest.raises(click.ClickException, match="current_code"):
        # обязательный вход не передан вовсе: предупреждение, затем KeyError в format_map
        render_prompt(skill, {})
    assert "current_code" in capsys.readouterr().err


def test_missing_required_with_empty_value_warns(capsys):
    skill = make_skill("code: {current_code}", required=[{"name": "current_code"}])
    assert render_prompt(skill, {"current_code": ""}) == "code: "
    assert "Не переданы обязательные параметры: current_code" in capsys.readouterr().err


def test_common_module_is_inlined():
    skill = make_skill("{common_style}")
    assert render_prompt(skill, {}) == load_common()["common_style"]


def test_doubled_braces_are_literal():
    skill = make_skill('{{"a": 1}} {x}', required=[{"name": "x"}])
    assert render_prompt(skill, {"x": "y"}) == '{"a": 1} y'


def test_unknown_placeholder_raises():
    with pytest.raises(click.ClickException, match="typo"):
        render_prompt(make_skill("{typo}"), {})


def test_empty_template_raises():
    with pytest.raises(click.ClickException, match="prompt_template"):
        render_prompt(make_skill(""), {})
