# Пример: медленный запрос транзакций

Используй как входные данные для `db-sql.query-optimize`.

## Входные данные

```yaml
skill_id: db-sql.query-optimize
inputs:
  engine: mariadb
  goal: "ускорить запрос фильтрации транзакций на дашборде"
  table_sizes: "transactions: 5M строк, accounts: 200k строк"
  query: |
    SELECT
      t.id,
      t.amount,
      t.status,
      t.created_at,
      a.name AS account_name
    FROM transactions t
    JOIN accounts a ON a.id = t.account_id
    WHERE t.status IN ('pending', 'processing')
      AND t.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    ORDER BY t.created_at DESC
    LIMIT 50
  explain_output: |
    id  type    table  type  possible_keys  key     rows     Extra
    1   SIMPLE  t      ALL   NULL           NULL    4980000  Using where; Using filesort
    1   SIMPLE  a      eq_ref PRIMARY       PRIMARY 1
  schema: |
    CREATE TABLE transactions (
      id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      account_id INT UNSIGNED    NOT NULL,
      amount     DECIMAL(12,2)   NOT NULL,
      status     ENUM('pending','processing','completed','failed') NOT NULL,
      created_at DATETIME        NOT NULL
    ) ENGINE=InnoDB;

    CREATE TABLE accounts (
      id   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(255) NOT NULL
    ) ENGINE=InnoDB;
```

## Ожидаемый результат

- Диагноз: full scan из-за отсутствия composite index на `(status, created_at)`
- Рекомендация: `CREATE INDEX idx_status_created ON transactions (status, created_at DESC)`
- Переписанный запрос или объяснение почему переписывать не нужно
- Риски нового индекса на write-нагрузку
