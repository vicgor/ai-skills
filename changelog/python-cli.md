# Changelog: python-cli skills

## 2026-10-12

### python-cli.design-command — v1.0.1
- Для каждого аргумента и опции — текст справки (`typer.Option(help=...)` / `add_argument(help=...)`) и пример `--help`.

### python-cli.fix-bug-from-trace — v1.0.1
- Root cause называет тип исключения из трассы дословно и файл:строку.

### python-cli.generate-help-text — v1.0.1
- При недостаточном описании не выдумывать опции и примеры: короткое описание, «Заметки» с неясным и 2–4 уточняющих вопроса.

### python-cli.review-cli-ux — v1.0.1
- Каждая проблема — явная пара «Было» / «Стало».

### python-cli.setup-project — v1.0.1
- При ci_platform=none не генерировать CI-конфиг (90c41a8).
- Для публикации на PyPI: `uv build`, `uv publish`, `uvx twine check dist/*`, пример extras.

## 2026-06-05

### Все скиллы — v1.0.0 (initial release)
- Создан стартовый набор из 6 скиллов: refactor-command, design-command,
  fix-bug-from-trace, write-tests, review-cli-ux, generate-help-text.
- Добавлен common/ с style.md, safety.md, output_formats.md.
- Добавлены eval-кейсы для refactor-command и fix-bug-from-trace.
- Добавлен пример typer-small-app.md для тестирования.

## Шаблон записи изменений

```
## YYYY-MM-DD

### skill-id vX.Y.Z
- Что изменено и почему (какую проблему исправили)
- Какой known_failure устранён
- Добавленные/удалённые eval-кейсы
```
