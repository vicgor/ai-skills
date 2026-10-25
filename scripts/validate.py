#!/usr/bin/env python3
"""Validates consistency between registry.yaml and actual skill files."""

import re
import string
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: uv sync")
    sys.exit(1)

ROOT = Path(__file__).parent.parent
REGISTRY = ROOT / "registry.yaml"
SKILLS_DIR = ROOT / "skills"
EVALS_DIR = ROOT / "evals"
COMMON_DIR = ROOT / "common"

Errors = list[str]
Warnings = list[str]


def load_registry() -> dict:
    with open(REGISTRY) as f:
        return yaml.safe_load(f)


def check_registry_files(registry: dict) -> tuple[Errors, Warnings]:
    """Every skill in registry must have a corresponding file."""
    errors, warnings = [], []
    for domain, domain_data in registry.get("domains", {}).items():
        for skill in domain_data.get("skills", []):
            skill_path = ROOT / skill["file"]
            if not skill_path.exists():
                errors.append(f"[MISSING FILE] {skill['id']} → {skill['file']}")
            else:
                # Verify skill file has required fields
                with open(skill_path) as f:
                    data = yaml.safe_load(f)
                for field in ["id", "version", "intent", "inputs", "output_contract", "prompt_template"]:
                    if field not in data:
                        errors.append(f"[MISSING FIELD] {skill['id']} → '{field}' not in {skill['file']}")
                if data.get("id") != skill["id"]:
                    errors.append(
                        f"[ID MISMATCH] registry has '{skill['id']}' but file has '{data.get('id')}'"
                    )
                if not data.get("known_failures"):
                    warnings.append(f"[NO KNOWN_FAILURES] {skill['id']} — добавь хотя бы одну запись")
    return errors, warnings


def check_files_in_registry(registry: dict) -> tuple[Errors, Warnings]:
    """Every skill file should be listed in registry."""
    errors, warnings = [], []
    registered_files = set()
    for domain_data in registry.get("domains", {}).values():
        for skill in domain_data.get("skills", []):
            registered_files.add(skill["file"])

    for skill_file in SKILLS_DIR.rglob("*.yaml"):
        rel = str(skill_file.relative_to(ROOT))
        if rel not in registered_files:
            warnings.append(f"[NOT IN REGISTRY] {rel} — не добавлен в registry.yaml")
    return errors, warnings


def check_evals_exist(registry: dict) -> tuple[Errors, Warnings]:
    """Every skill should have at least one eval case file."""
    errors, warnings = [], []
    for domain, domain_data in registry.get("domains", {}).items():
        for skill in domain_data.get("skills", []):
            skill_id = skill["id"]
            skill_name = skill_id.split(".", 1)[1]
            eval_file = EVALS_DIR / domain / f"{skill_name}.cases.yaml"
            if not eval_file.exists():
                warnings.append(f"[NO EVALS] {skill_id} → {eval_file.relative_to(ROOT)} не найден")
            else:
                with open(eval_file) as f:
                    data = yaml.safe_load(f)
                cases = data.get("cases", [])
                if len(cases) < 2:
                    warnings.append(f"[FEW EVALS] {skill_id} — только {len(cases)} кейс(а), рекомендуется ≥2")
    return errors, warnings


def check_output_contracts(registry: dict) -> tuple[Errors, Warnings]:
    """output_contract.must_include must not be empty."""
    errors, warnings = [], []
    for domain_data in registry.get("domains", {}).values():
        for skill in domain_data.get("skills", []):
            skill_path = ROOT / skill["file"]
            if not skill_path.exists():
                continue
            with open(skill_path) as f:
                data = yaml.safe_load(f)
            contract = data.get("output_contract", {})
            must_include = contract.get("must_include", [])
            if not must_include:
                errors.append(f"[EMPTY CONTRACT] {skill['id']} → output_contract.must_include пустой")
    return errors, warnings


def check_templates(registry: dict) -> tuple[Errors, Warnings]:
    """Every {placeholder} in prompt_template must be a declared input or common module,
    and the template must render with str.format_map (literal braces must be doubled)."""
    errors, warnings = [], []
    common = {f"common_{p.stem.replace('-', '_')}" for p in COMMON_DIR.glob("*.md")}
    for domain_data in registry.get("domains", {}).values():
        for skill in domain_data.get("skills", []):
            skill_path = ROOT / skill["file"]
            if not skill_path.exists():
                continue
            with open(skill_path) as f:
                data = yaml.safe_load(f)
            template = data.get("prompt_template") or ""
            inputs = data.get("inputs") or {}
            declared = {i["name"] for i in (inputs.get("required") or []) + (inputs.get("optional") or [])}
            try:
                fields = {
                    re.split(r"[.\[]", name, maxsplit=1)[0]
                    for _, name, _, _ in string.Formatter().parse(template)
                    if name is not None
                }
            except ValueError as exc:
                errors.append(f"[TEMPLATE SYNTAX] {skill['id']} — {exc} (литеральные скобки удваивай: {{{{ }}}})")
                continue
            for name in sorted(fields - declared - common):
                errors.append(f"[TEMPLATE VAR] {skill['id']} — {{{name}}} не объявлен в inputs и не модуль common/")
            for name in sorted(declared - fields):
                warnings.append(f"[UNUSED INPUT] {skill['id']} — вход '{name}' не используется в prompt_template")
            if "" in fields:
                errors.append(f"[TEMPLATE VAR] {skill['id']} — пустой плейсхолдер {{}}")
            dummy = {name: "x" for name in declared | common}
            try:
                template.format_map(dummy)
            except (KeyError, IndexError, ValueError, AttributeError) as exc:
                errors.append(f"[TEMPLATE RENDER] {skill['id']} — не рендерится: {exc!r}")
    return errors, warnings


CASE_REQUIRED = ["id", "description", "input", "expected"]
CASE_ALLOWED = set(CASE_REQUIRED)
EXPECTED_LIST_KEYS = ["must_contain", "should_not_contain"]


def check_eval_structure(registry: dict) -> tuple[Errors, Warnings]:
    """Every eval case must have id, description, input, expected (not 'expect')."""
    errors, warnings = [], []
    for domain, domain_data in registry.get("domains", {}).items():
        for skill in domain_data.get("skills", []):
            skill_id = skill["id"]
            skill_name = skill_id.split(".", 1)[1]
            eval_file = EVALS_DIR / domain / f"{skill_name}.cases.yaml"
            if not eval_file.exists():
                continue
            rel = eval_file.relative_to(ROOT)
            try:
                with open(eval_file) as f:
                    data = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                errors.append(f"[EVAL YAML] {rel} — {exc}")
                continue
            if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
                errors.append(f"[EVAL STRUCTURE] {rel} — нет списка 'cases'")
                continue
            if data.get("skill_id") != skill_id:
                errors.append(
                    f"[EVAL SKILL_ID] {rel} — skill_id '{data.get('skill_id')}', ожидается '{skill_id}'"
                )
            seen_ids = set()
            for i, case in enumerate(data["cases"], 1):
                if not isinstance(case, dict):
                    errors.append(f"[EVAL CASE] {rel} кейс #{i} — не словарь")
                    continue
                cid = case.get("id", f"#{i}")
                where = f"{rel} кейс '{cid}'"
                if "expect" in case:
                    errors.append(f"[EVAL KEY] {where} — используй 'expected' вместо 'expect'")
                for key in CASE_REQUIRED:
                    if key not in case:
                        errors.append(f"[EVAL KEY] {where} — нет ключа '{key}'")
                if "id" in case:
                    if case["id"] in seen_ids:
                        errors.append(f"[EVAL DUPLICATE] {rel} — повторяется id '{case['id']}'")
                    seen_ids.add(case["id"])
                for key in case:
                    if key not in CASE_ALLOWED and key != "expect":
                        warnings.append(f"[EVAL UNKNOWN KEY] {where} — неизвестный ключ '{key}'")
                expected = case.get("expected")
                if isinstance(expected, dict):
                    if not any(k in expected for k in EXPECTED_LIST_KEYS + ["should_not_match", "quality"]):
                        errors.append(f"[EVAL EXPECTED] {where} — пустой expected")
                    for k in EXPECTED_LIST_KEYS:
                        v = expected.get(k)
                        if v is not None and not (isinstance(v, list) and all(isinstance(s, str) or (isinstance(s, list) and s and all(isinstance(o, str) for o in s)) for s in v)):
                            errors.append(f"[EVAL EXPECTED] {where} — '{k}' должен быть списком строк")
                    patterns = expected.get("should_not_match")
                    if patterns is not None:
                        if not (isinstance(patterns, list) and all(isinstance(x, str) for x in patterns)):
                            errors.append(f"[EVAL EXPECTED] {where} — 'should_not_match' должен быть списком regex-строк")
                        else:
                            for x in patterns:
                                try:
                                    re.compile(x)
                                except re.error as exc:
                                    errors.append(f"[EVAL EXPECTED] {where} — невалидный regex {x!r}: {exc}")
                    q = expected.get("quality")
                    if q is not None and not isinstance(q, dict):
                        errors.append(f"[EVAL EXPECTED] {where} — 'quality' должен быть словарём")
                elif "expected" in case:
                    errors.append(f"[EVAL EXPECTED] {where} — 'expected' должен быть словарём")
    return errors, warnings


def main() -> int:
    print("=" * 60)
    print("ai-skills validator")
    print("=" * 60)

    registry = load_registry()
    all_errors: Errors = []
    all_warnings: Warnings = []

    checks = [
        ("Registry → Files", check_registry_files),
        ("Files → Registry", check_files_in_registry),
        ("Eval coverage", check_evals_exist),
        ("Eval structure", check_eval_structure),
        ("Output contracts", check_output_contracts),
        ("Prompt templates", check_templates),
    ]

    for check_name, check_fn in checks:
        errors, warnings = check_fn(registry)
        print(f"\n[{check_name}]")
        if not errors and not warnings:
            print("  ✓ OK")
        for e in errors:
            print(f"  ✗ {e}")
        for w in warnings:
            print(f"  ⚠ {w}")
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    print("\n" + "=" * 60)
    print(f"Итого: {len(all_errors)} ошибок, {len(all_warnings)} предупреждений")
    print("=" * 60)

    if all_errors:
        print("\nFAIL — исправь ошибки перед коммитом.")
        return 1
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
