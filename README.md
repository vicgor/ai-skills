# ai-skills

Personal AI prompt skills library. Промпты и скиллы для Perplexity, Claude и других LLM — организованные как инженерная система, а не случайные заметки.

## Структура

```
ai-skills/
├─ README.md
├─ registry.yaml              ← Каталог всех скиллов
├─ common/                    ← Переиспользуемые правила
│  ├─ style.md
│  ├─ safety.md
│  └─ output_formats.md
├─ skills/
│  └─ python-cli/             ← Скиллы по доменам
│     ├─ refactor-command.yaml
│     ├─ design-command.yaml
│     ├─ fix-bug-from-trace.yaml
│     ├─ write-tests.yaml
│     ├─ review-cli-ux.yaml
│     └─ generate-help-text.yaml
├─ examples/
│  └─ python-cli/             ← Примеры кода для тест-кейсов
│     └─ typer-small-app.md
├─ evals/
│  └─ python-cli/             ← Регрессионные тест-кейсы
│     ├─ refactor-command.cases.yaml
│     └─ fix-bug-from-trace.cases.yaml
├─ changelog/
│  └─ python-cli.md           ← История изменений
└─ render.py                  ← CLI-утилита для рендера промптов
```

## Быстрый старт

```bash
# Установить зависимости (только PyYAML + click)
uv pip install pyyaml click

# Список всех скиллов
python render.py list

# Рендер промпта в stdout
python render.py render python-cli.refactor-command \
  --var framework=typer \
  --var goal="вынести бизнес-логику в service слой" \
  --var constraints="не менять CLI аргументы, Python 3.12" \
  --var target_structure="cli.py + services/importer.py" \
  --file current_code=./my_command.py

# Скопировать в буфер
python render.py render python-cli.refactor-command --var framework=typer | pbcopy
# или под Linux:
python render.py render python-cli.refactor-command --var framework=typer | xclip -selection clipboard
```

## Жизненный цикл скилла

1. **Создать** новый YAML в `skills/<domain>/`.
2. **Написать** тест-кейсы в `evals/<domain>/*.cases.yaml`.
3. **Прогнать** кейсы вручную в Perplexity — проверить quality_checks.
4. **Зафиксировать** результат в `changelog/<domain>.md`.
5. **Версионировать** через git commit.

## Добавление нового домена

Скопируй структуру `skills/python-cli/` в `skills/<new-domain>/`, обнови `registry.yaml`.
