#!/usr/bin/env python3
"""CLI-утилита для рендера AI prompt скиллов из YAML-шаблонов.

Использование:
    python render.py list
    python render.py render python-cli.refactor-command --var framework=typer
    python render.py render python-cli.fix-bug-from-trace --file traceback=error.log
"""
import sys
from pathlib import Path

import click
import yaml

SKILLS_DIR = Path(__file__).parent / "skills"
COMMON_DIR = Path(__file__).parent / "common"
REGISTRY_FILE = Path(__file__).parent / "registry.yaml"


def load_registry() -> dict:
    with REGISTRY_FILE.open() as f:
        return yaml.safe_load(f)


def find_skill_file(skill_id: str) -> Path:
    """Ищет YAML файл скилла по ID (domain.name)."""
    registry = load_registry()
    for domain_data in registry.get("domains", {}).values():
        for skill in domain_data.get("skills", []):
            if skill["id"] == skill_id:
                return Path(__file__).parent / skill["file"]
    raise click.ClickException(f"Скилл '{skill_id}' не найден в registry.yaml")


def load_skill(skill_id: str) -> dict:
    skill_file = find_skill_file(skill_id)
    if not skill_file.exists():
        raise click.ClickException(f"Файл скилла не найден: {skill_file}")
    with skill_file.open() as f:
        return yaml.safe_load(f)


def load_common() -> dict:
    """Загружает общие модули из common/."""
    common = {}
    for md_file in COMMON_DIR.glob("*.md"):
        key = f"common_{md_file.stem.replace('-', '_')}"
        common[key] = md_file.read_text()
    return common


def render_prompt(skill: dict, variables: dict) -> str:
    template = skill.get("prompt_template", "")
    if not template:
        raise click.ClickException("Скилл не содержит prompt_template")

    # Подставляем common модули
    context = load_common()

    # Подставляем defaults из inputs.optional
    for inp in skill.get("inputs", {}).get("optional", []):
        key = inp["name"]
        if key not in variables and "default" in inp:
            variables[key] = inp["default"]

    # Подставляем пустую строку для optional, которых нет
    for inp in skill.get("inputs", {}).get("optional", []):
        variables.setdefault(inp["name"], "")

    # Проверяем обязательные inputs
    missing = []
    for inp in skill.get("inputs", {}).get("required", []):
        if inp["name"] not in variables or not variables[inp["name"]]:
            missing.append(inp["name"])
    if missing:
        click.echo(
            f"⚠️  Не переданы обязательные параметры: {', '.join(missing)}",
            err=True,
        )
        click.echo(
            "Добавь их через --var name=value или --file name=path",
            err=True,
        )

    context.update(variables)

    try:
        rendered = template.format_map(context)
    except KeyError as e:
        raise click.ClickException(f"Неизвестная переменная в шаблоне: {e}")

    return rendered


@click.group()
def cli():
    """AI Skills renderer — рендер промптов из YAML-шаблонов."""


@cli.command(name="list")
def list_skills():
    """Показать все доступные скиллы из registry.yaml."""
    registry = load_registry()
    click.echo(f"AI Skills Registry (v{registry.get('version', '?')})\n")
    for domain, domain_data in registry.get("domains", {}).items():
        click.echo(f"📁 {domain}: {domain_data.get('description', '')}")
        for skill in domain_data.get("skills", []):
            status = skill.get("status", "?")
            status_icon = {"stable": "✅", "draft": "🔧", "deprecated": "❌"}.get(
                status, "❓"
            )
            click.echo(f"  {status_icon} {skill['id']}")
            click.echo(f"     {skill.get('intent', '')}")
            required = skill.get("inputs_required", [])
            if required:
                click.echo(f"     Входы: {', '.join(required)}")
        click.echo()


@cli.command()
@click.argument("skill_id")
@click.option(
    "--var",
    "variables",
    multiple=True,
    metavar="KEY=VALUE",
    help="Переменная для подстановки (можно несколько: --var a=1 --var b=2)",
)
@click.option(
    "--file",
    "files",
    multiple=True,
    metavar="KEY=PATH",
    help="Прочитать значение из файла (--file current_code=./cmd.py)",
)
@click.option(
    "--show-meta",
    is_flag=True,
    default=False,
    help="Показать метаданные скилла перед промптом",
)
def render(skill_id: str, variables: tuple, files: tuple, show_meta: bool):
    """Отрендерить промпт для скилла SKILL_ID.

    Результат выводится в stdout, удобно использовать с pbcopy / xclip:

        python render.py render python-cli.refactor-command \\
          --var framework=typer \\
          --var goal="вынести service слой" | xclip -selection clipboard
    """
    skill = load_skill(skill_id)

    vars_dict: dict[str, str] = {}

    # Разбираем --var KEY=VALUE
    for var in variables:
        if "=" not in var:
            raise click.ClickException(f"Неверный формат --var: '{var}' (ожидается KEY=VALUE)")
        key, _, value = var.partition("=")
        vars_dict[key.strip()] = value.strip()

    # Разбираем --file KEY=PATH
    for file_arg in files:
        if "=" not in file_arg:
            raise click.ClickException(
                f"Неверный формат --file: '{file_arg}' (ожидается KEY=PATH)"
            )
        key, _, path_str = file_arg.partition("=")
        path = Path(path_str.strip())
        if not path.exists():
            raise click.ClickException(f"Файл не найден: {path}")
        vars_dict[key.strip()] = path.read_text()

    if show_meta:
        click.echo(f"# Скилл: {skill.get('id')}")
        click.echo(f"# Версия: {skill.get('version')}")
        click.echo(f"# Статус: {skill.get('status')}")
        click.echo(f"# Цель: {skill.get('intent', '').strip()}")
        click.echo("---")

    result = render_prompt(skill, vars_dict)
    click.echo(result)


@cli.command()
@click.argument("skill_id")
def info(skill_id: str):
    """Показать детальную информацию о скилле."""
    skill = load_skill(skill_id)
    click.echo(f"ID: {skill.get('id')}")
    click.echo(f"Версия: {skill.get('version')}")
    click.echo(f"Статус: {skill.get('status')}")
    click.echo(f"Теги: {', '.join(skill.get('tags', []))}")
    click.echo(f"\nЦель:\n  {skill.get('intent', '').strip()}")

    click.echo("\nПрименять когда:")
    for item in skill.get("use_when", []):
        click.echo(f"  + {item}")

    click.echo("\nНе применять когда:")
    for item in skill.get("avoid_when", []):
        click.echo(f"  - {item}")

    click.echo("\nОбязательные входы:")
    for inp in skill.get("inputs", {}).get("required", []):
        click.echo(f"  * {inp['name']}: {inp.get('description', '')}")

    click.echo("\nОпциональные входы:")
    for inp in skill.get("inputs", {}).get("optional", []):
        default = inp.get("default", "")
        click.echo(f"  - {inp['name']} [{default}]: {inp.get('description', '')}")

    known_failures = skill.get("known_failures", [])
    if known_failures:
        click.echo("\nИзвестные проблемы:")
        for f in known_failures:
            click.echo(f"  ⚠️  {f}")


if __name__ == "__main__":
    cli()
