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
# Установить зависимости (click, PyYAML, httpx) в .venv по uv.lock
uv sync
source .venv/bin/activate

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

## Результаты evals

Тег `evals-66of66-v2` указывает на коммит, на котором сделан последний полный прогон. Предыдущий тег `evals-66of66` (`e2b57bc`) — версия до ужесточения проверок.

| Модель | Лимит токенов | Дата | Версия скиллов и кейсов | PASS |
|---|---|---|---|---|
| gpt-6-luna | 16000 (по умолчанию) | 12.10.2026 | текущая (тег `evals-66of66-v2`) | 66 из 66 |
| claude-haiku-5.5 | 64000 | 12.10.2026 | предыдущая (`e2b57bc`), до ужесточения проверок и правок write-eval / diagnose-performance | 66 из 66 |

Haiku на текущей версии ещё не перепрогонялся.

| Домен | Скиллов | Кейсов |
|---|---|---|
| python-cli | 9 | 27 |
| db-sql | 4 | 11 |
| devops | 4 | 11 |
| git | 3 | 8 |
| ai-dev | 2 | 9 |
| **Итого** | **22** | **66** |

Запуск:

```bash
uv run python scripts/run_evals.py --provider openai --model gpt-6-luna --jobs 8
uv run python scripts/run_evals.py --provider openai --model claude-haiku-5.5 --max-tokens 64000 --jobs 8
```

`--jobs N` гоняет N кейсов параллельно (по умолчанию 1). Сетевые сбои, таймауты и ответы 429/5xx повторяются до 4 раз с паузой 2, 4, 8 с.

Заметки:

- На haiku с лимитом 16000 токенов набор давал 59–60 из 66: часть ответов обрезалась, поэтому нужен `--max-tokens 64000`.
- Результаты отдельных прогонов лежат в `evals/results/<дата-время>/`.
- Ручные проверки качества (`quality`) выводятся списком, но автоматически не оцениваются: PASS считается только по `must_contain` и `should_not_contain`.

## Жизненный цикл скилла

1. **Создать** новый YAML в `skills/<domain>/`.
2. **Написать** тест-кейсы в `evals/<domain>/*.cases.yaml`.
3. **Прогнать** кейсы вручную в Perplexity — проверить quality_checks.
4. **Зафиксировать** результат в `changelog/<domain>.md`.
5. **Версионировать** через git commit.

## Добавление нового домена

Скопируй структуру `skills/python-cli/` в `skills/<new-domain>/`, обнови `registry.yaml`.
