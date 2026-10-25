# Contributing to ai-skills

Как добавлять скиллы, обновлять реестр и писать eval-кейсы.

## Структура репозитория

```
ai-skills/
├─ registry.yaml              ← каталог всех скиллов (обновлять обязательно)
├─ common/                    ← общие правила: стиль, безопасность, форматы
├─ skills/{domain}/           ← YAML-файлы скиллов
├─ evals/{domain}/            ← тест-кейсы .cases.yaml
├─ examples/{domain}/         ← примеры входных данных .md
├─ changelog/{domain}.md      ← журнал изменений
├─ render.py                  ← CLI для рендеринга промптов
└─ scripts/validate.py        ← валидация консистентности
```

---

## Добавление нового скилла

### 1. Создай YAML-файл

Путь: `skills/{domain}/{skill-name}.yaml`

Обязательные поля:

```yaml
id: {domain}.{skill-name}        # уникальный ID
version: "1.0.0"
owner: victor
status: stable                   # stable | draft | deprecated
tags: []

intent: >                        # одно предложение — что делает скилл

use_when: []                     # когда применять
avoid_when: []                   # когда НЕ применять

inputs:
  required:
    - name: ...
      description: ...
  optional: []

output_contract:
  format: markdown
  must_include: []               # обязательные секции в ответе
  prefer: []                     # пожелания

prompt_template: |
  {common_style}
  {common_safety}
  ...

quality_checks: {}               # булевы флаги для eval
known_failures: []               # задокументированные проблемы
```

### 2. Добавь в registry.yaml

```yaml
domains:
  {domain}:
    skills:
      - id: {domain}.{skill-name}
        file: skills/{domain}/{skill-name}.yaml
        status: stable
        intent: "Краткое описание"
        inputs_required: [field1, field2]
        output: "что на выходе"
```

### 3. Добавь eval-кейсы

Путь: `evals/{domain}/{skill-name}.cases.yaml`

Минимум 2 кейса. Структура:

```yaml
skill_id: {domain}.{skill-name}
cases:
  - id: descriptive_name
    description: "Что проверяем"
    input:
      field1: value
    expected:
      must_contain: ["слово1", "слово2"]
      should_not_contain: ["антипаттерн"]
      should_not_match: ['^\s*<<<<<<< ']   # regex по всему ответу (re.MULTILINE)
      quality:
        has_X: true
```

### 4. Добавь пример

Путь: `examples/{domain}/{skill-name}-example.md`

Пример — это готовые входные данные которые можно скопировать и использовать сразу.

### 5. Обнови changelog

Файл: `changelog/{domain}.md`

```markdown
## YYYY-MM-DD
### {skill-name} v1.0.0
- Добавлен скилл: краткое описание.
```

### 6. Запусти валидацию

```bash
uv sync
python scripts/validate.py
```

Валидатор также проверяет `prompt_template`: каждый `{плейсхолдер}` должен быть
объявлен в `inputs` или быть модулем `common/`, а литеральные фигурные скобки
(JSON, код) нужно удваивать: `{{` и `}}`. Те же проверки запускает CI
(`.github/workflows/ci.yml`) вместе с dry-run всех eval-кейсов.

Юнит-тесты скриптов (`render.py`, `scripts/`) лежат в `tests/`: `uv run pytest`.
Новую логику в скриптах сопровождай тестами.

---

## Обновление существующего скилла

1. Измени `version` по semver: patch для фикса промпта, minor для новых inputs, major для breaking.
2. Обнови `known_failures` если исправил задокументированную проблему.
3. Прогони существующие eval-кейсы вручную.
4. Запиши в changelog что изменилось и почему.

---

## Правила для known_failures

Каждый `known_failures` должен содержать:
- Что модель делает неправильно
- Стрелку `→` и способ обойти

Пример:
```yaml
known_failures:
  - "Модель не включает команды тестирования → передавать testing_context явно"
```

---

## Правила для quality_checks

Флаги `quality` в eval-кейсах оценивает судья (`run_evals.py --judge`), поэтому называй их
так, чтобы по одному имени было ясно, что проверять: `asks_for_missing_input`, а не `ok`.
Значение `true` — свойство должно выполняться; другое значение (например, `max_code_blocks: 0`)
передаётся судье как ожидаемое.

Только булевы флаги. Называй их `has_{секция}` или `{свойство}_valid`.

```yaml
quality_checks:
  has_diagnosis: true
  has_index_suggestions: true
  subject_under_72_chars: true
```

---

## Запуск render.py

```bash
# Список всех скиллов
python render.py list

# Детали скилла
python render.py info db-sql.query-optimize

# Рендер промпта
python render.py render git.write-commit-message \
  --var style=conventional \
  --var scope=cli \
  --file diff_or_description=./my.diff
```

## Где хранить примеры

- Основной пример входных данных лежит в `examples/{domain}/{skill-name}-example.md`.
- Блок `examples:` внутри YAML скилла необязателен: это краткая выжимка (имя, входы, ключевые ожидания) для быстрого просмотра через `render.py show`.
- При расхождении источником истины считается файл в `examples/`.
