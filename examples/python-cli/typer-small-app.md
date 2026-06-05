# Пример: Typer small app

Используй этот пример как `current_code` при прогоне eval-кейсов.

```python
# cli.py — пример CLI без разделения слоёв (для тестирования рефакторинга)
import typer
from pathlib import Path
import json

app = typer.Typer()

@app.command()
def sync_users(
    source: Path = typer.Argument(..., help="JSON файл с пользователями"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Не применять изменения"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Синхронизировать пользователей из JSON файла в БД."""
    if not source.exists():
        typer.echo(f"Файл не найден: {source}", err=True)
        raise typer.Exit(code=1)

    with open(source) as f:
        users = json.load(f)

    if verbose:
        typer.echo(f"Загружено пользователей: {len(users)}")

    # Бизнес-логика прямо в команде — проблема!
    created = 0
    updated = 0
    for user in users:
        # имитация работы с БД
        if user.get("id"):
            # обновление
            updated += 1
            if verbose:
                typer.echo(f"Обновление: {user['email']}")
        else:
            # создание
            created += 1
            if verbose:
                typer.echo(f"Создание: {user['email']}")

    if dry_run:
        typer.echo(f"[dry-run] Будет создано: {created}, обновлено: {updated}")
    else:
        typer.echo(f"Создано: {created}, обновлено: {updated}")

if __name__ == "__main__":
    app()
```

## Проблемы в этом коде (для скилла refactor-command)

1. Бизнес-логика (валидация, создание/обновление пользователей) прямо в CLI-команде.
2. Нет service/application слоя — не протестировать без вызова CLI.
3. Вывод через `typer.echo` перемешан с логикой.
4. Нет явной обработки ошибок парсинга JSON.
