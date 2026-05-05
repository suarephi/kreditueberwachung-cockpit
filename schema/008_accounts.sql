-- 008_accounts.sql -- Kundenkonten + 24-Monats-Transaktionshistorie für Bewegungsanalyse.

CREATE TABLE account (
  account_id          INTEGER PRIMARY KEY,
  client_id           INTEGER NOT NULL REFERENCES client(client_id),
  iban                TEXT NOT NULL,
  account_type        TEXT NOT NULL CHECK (account_type IN
                          ('salary','savings','mortgage_servicing','rental','joint')),
  currency            TEXT NOT NULL DEFAULT 'CHF',
  opened_date         TEXT NOT NULL,
  current_balance_chf REAL NOT NULL,
  avg_balance_12m_chf REAL,
  status              TEXT NOT NULL DEFAULT 'active'
);
CREATE INDEX ix_account_client ON account(client_id);

CREATE TABLE account_tx (
  tx_id               INTEGER PRIMARY KEY,
  account_id          INTEGER NOT NULL REFERENCES account(account_id),
  tx_date             TEXT NOT NULL,
  value_date          TEXT NOT NULL,
  amount_chf          REAL NOT NULL,
  category            TEXT NOT NULL,
  counterparty        TEXT,
  description         TEXT,
  reference           TEXT
);
CREATE INDEX ix_tx_account_date ON account_tx(account_id, tx_date);
CREATE INDEX ix_tx_category     ON account_tx(category);
