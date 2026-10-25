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
| gpt-6-luna | 16000 (по умолчанию) | 25.10.2026 | текущая | 66 из 66; quality (судья haiku): 152 pass, 0 fail, 2 unknown из 154 |
| gpt-6-luna | 16000 (по умолчанию) | 12.10.2026 | тег `evals-66of66-v2` | 66 из 66 |
| claude-haiku-5.5 | 64000 | 25.10.2026 | тег `evals-66of66-v2` | 66 из 66 |

После тега `evals-66of66-v2` промпты 8 скиллов доработаны по вердиктам судьи (см. changelog за 25.10.2026); haiku на этой версии не перепрогонялся.
Полный прогон с `--jobs 8` занимает 3,5–4 минуты (последовательно — около 30).
Результаты одного прогона шумят: в повторных прогонах отдельные кейсы и вердикты меняются без правок промптов.

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

`--repeat N` прогоняет каждый кейс N раз и в конце печатает стабильность: сколько кейсов прошли во всех прогонах, а для остальных — доля PASS, какие проверки падали и разброс вердиктов судьи. Сводка пишется в `results.json` (`stability`). Один прогон шумит, поэтому правки промптов лучше проверять с `--repeat 3` или больше.

`--jobs N` гоняет N кейсов параллельно (по умолчанию 1). Сетевые сбои, таймауты и ответы 429/5xx повторяются до 4 раз с паузой 2, 4, 8 с.

Заметки:

- На haiku с лимитом 16000 токенов набор давал 59–60 из 66: часть ответов обрезалась, поэтому нужен `--max-tokens 64000`.
- Результаты отдельных прогонов лежат в `evals/results/<дата-время>/`.
- PASS считается по `must_contain`, `should_not_contain` и `should_not_match`. Флаги `quality` без `--judge` только выводятся списком для ручной проверки.

### Оценка флагов quality судьёй

```bash
uv run python scripts/run_evals.py --provider openai --model gpt-6-luna --jobs 8 --judge --judge-model claude-haiku-5.5
```

- `--judge` — после ответа модели отдельный вызов судьи оценивает каждый флаг `quality`: `pass`, `fail` или `unknown` с причиной. Вердикты пишутся в `results.json` (`quality_verdicts`), ответ судьи — в `<кейс>.judge.md`.
- `--judge-model` — модель-судья того же провайдера; по умолчанию `--model`. Лучше брать другую модель, чем оцениваемая.
- По умолчанию вердикты судьи на PASS/FAIL не влияют, выводится только сводка. `--judge-strict` превращает `fail` судьи в FAIL кейса; `unknown` кейс не роняет.

## Жизненный цикл скилла

1. **Создать** новый YAML в `skills/<domain>/`.
2. **Написать** тест-кейсы в `evals/<domain>/*.cases.yaml`.
3. **Прогнать** кейсы вручную в Perplexity — проверить quality_checks.
4. **Зафиксировать** результат в `changelog/<domain>.md`.
5. **Версионировать** через git commit.

## Добавление нового домена

Скопируй структуру `skills/python-cli/` в `skills/<new-domain>/`, обнови `registry.yaml`.
