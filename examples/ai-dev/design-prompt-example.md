# Пример: улучшение расплывчатого промпта для ревью кода

Используй как входные данные для `ai-dev.design-prompt`.

## Входные данные

```yaml
skill_id: ai-dev.design-prompt
inputs:
  mode: improve
  goal: "Ревью pull request в Python-проекте: найти баги и риски, не придираться к стилю"
  target_model: universal
  output_format: markdown
  tone: concise and precise
  constraints: "Не комментировать форматирование, если оно проходит ruff"
  current_prompt: |
    You are a helpful assistant. Review the code and be helpful.
    Give good feedback and be nice.
  failure_examples: |
    - Ответ на diff в 400 строк: общие слова "код выглядит хорошо", ни одного конкретного замечания.
    - На пустой diff модель выдумала файл и написала ревью к нему.
```

## Что должен сделать скилл

- Diagnosis: расплывчатая роль ("helpful assistant"), нет формата вывода, нет ограничений, нет поведения при пустом или неполном diff.
- Каждой проблеме из diagnosis соответствует исправление в новом промпте.
- Role sentence: одна строка до 20 слов, например про senior Python reviewer для backend-разработчиков.
- Uncertainty handling: при пустом diff или отсутствии контекста спросить, а не выдумывать.
- Явный формат: список замечаний с уровнем серьёзности и ссылкой на строку.

## Критерии проверки

- Role sentence не содержит "helpful" и укладывается в 20 слов.
- Есть блок про пустой или противоречивый ввод.
- known_weaknesses упоминает огромные diff и отсутствие контекста репозитория.
