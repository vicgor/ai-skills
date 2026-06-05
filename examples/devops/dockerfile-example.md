# Пример: Dockerfile для Python CLI-инструмента

Используй как входные данные для `devops.write-dockerfile`.

## Входные данные

```yaml
skill_id: devops.write-dockerfile
inputs:
  python_version: "3.12"
  base_image: "python:3.12-slim"
  package_manager: "uv"
  requirements: "non-root user, минимальный образ, без dev-зависимостей"
  app_description: |
    Python CLI-инструмент на Typer.
    Точка входа: `python -m mytool` или команда `mytool`.
    Зависимости: typer, httpx, pydantic-settings.
    Читает конфиг из переменных окружения.
    Не нужен web-порт — запускается как одноразовый job.
```

## Ожидаемый результат

- Multi-stage build: builder (uv install) + runtime (только .venv)
- Non-root user `appuser`
- COPY pyproject.toml / uv.lock перед COPY src для кэширования слоёв
- .dockerignore с исключением .git, __pycache__, tests
- Команды: `docker build` + `docker run --rm`
