# Пример: ревью схемы таблицы заказов

Используй как входные данные для `db-sql.schema-review`.

## Входные данные

```yaml
skill_id: db-sql.schema-review
inputs:
  engine: mariadb
  context: "OLTP, интернет-магазин, ~10k заказов/день"
  focus: "всё"
  schema: |
    CREATE TABLE orders (
      id          INT NOT NULL AUTO_INCREMENT,
      user_id     INT,
      status      VARCHAR(50),
      total       FLOAT,
      address     TEXT,
      created     DATETIME,
      updated     DATETIME,
      notes       TEXT,
      extra_data  TEXT,
      PRIMARY KEY (id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
```

## Известные проблемы в схеме (для валидации ответа)

- `INT` вместо `INT UNSIGNED` для PK/FK
- `FLOAT` для денег → должен быть `DECIMAL(10,2)`
- `VARCHAR(50)` для status без ENUM → нет constraint
- `TEXT` для address → нет нормализации
- `utf8` вместо `utf8mb4`
- Нет индексов на `user_id`, `status`, `created`
- Нет `NOT NULL` на обязательных полях
- `created`/`updated` — неконсистентное именование (лучше `created_at`/`updated_at`)
