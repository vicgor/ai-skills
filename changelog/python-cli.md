# Changelog: python-cli skills

## 2026-10-25

Правки по замеру стабильности (`--repeat 5 --judge`, прогон 20261025-121537: 325/330 PASS, 61/66 кейсов стабильны). После правок затронутые скиллы — 70/70 PASS, 165/165 флагов pass.

### python-cli.generate-help-text — v1.0.3
- Примеры вызывают команду по имени из описания (`mycli export 2025-01`), а не `python cli.py 2025-01`.

### python-cli.handle-config-file (только eval-кейсы)
- secret_field_not_printed: `config show` засчитывается и как `command("show")`.

Правки по вердиктам судьи (`run_evals.py --judge`): прогон до правок 20261025-102711 (65/66, quality 145 pass / 7 fail / 2 unknown), после — 20261025-105406 (66/66, quality 152 pass / 0 fail / 2 unknown).

### python-cli.generate-help-text — v1.0.2
- У каждого аргумента и опции своя справка в сигнатуре (`typer.Option(help=...)` и аналоги); сигнатура целиком, без `def cmd(...)`. Модель переносила справку опций в общий help команды.
- Фрагмент должен запускаться как есть: импорты, `app = typer.Typer()`, тело — заглушка `# TODO`.

### python-cli.review-cli-ux — v1.0.2
- Правило фокуса: без разделов «Остальные пункты»; вне фокуса — максимум одна строка.
- Обработка ошибок: проверять, что сообщения идут в stderr и exit code ненулевой.
- Не выдумывать проблемы: то, что не видно во входных данных, — «Проверить», не в приоритетном списке.
- Eval-кейс focus_error_messages: `stderr` или `err=True`.

### python-cli.design-command — v1.0.2
- Расплывчатая цель (непонятно, ЧТО делает команда): не вводить форматы, enum, пути и примеры, которых нет во входных данных; только каркас и 3–5 вопросов. При ясных действии и объекте — полный дизайн с явно помеченными допущениями (первая версия правила срабатывала и на ясных целях).
- Примеры вызова: не больше 5.

### python-cli.setup-project — v1.0.2
- При публикации на PyPI и github-actions — job публикации по тегу `v*` (`uv build` + `uv publish`).

### python-cli.handle-config-file — v1.0.1
- Новый раздел «Секретные поля»: `SecretStr`, маска в `config show`, предупреждение об открытом тексте, права `600`, альтернатива — env или keyring.

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
