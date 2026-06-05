# Пример: commit message по diff

Используй как входные данные для `git.write-commit-message`.

## Входные данные

```yaml
skill_id: git.write-commit-message
inputs:
  style: conventional
  scope: cli
  breaking: "no"
  diff_or_description: |
    diff --git a/src/mytool/commands/sync.py b/src/mytool/commands/sync.py
    --- a/src/mytool/commands/sync.py
    +++ b/src/mytool/commands/sync.py
    @@ -12,8 +12,15 @@
     def sync(dry_run: bool = False, verbose: bool = False):
    -    items = load_all_items()
    -    for item in items:
    -        process(item)
    +    items = load_all_items()
    +    if not items:
    +        typer.echo("Nothing to sync.", err=True)
    +        raise typer.Exit(code=0)
    +    with Progress() as progress:
    +        task = progress.add_task("Syncing...", total=len(items))
    +        for item in items:
    +            process(item)
    +            progress.advance(task)
    +    typer.echo(f"Synced {len(items)} items.")
```

## Ожидаемый результат

- Subject: `feat(cli): add progress bar and empty-state handling to sync command`
- Или альтернативы с объяснением разницы
- Body: почему добавлен progress bar (UX для больших наборов данных)
