-- 009_dunning.sql -- Mahnwesen-Stufen pro Kredit (Swiss banking workflow).

CREATE TABLE dunning_step (
  dunning_id              INTEGER PRIMARY KEY,
  loan_id                 INTEGER NOT NULL REFERENCES loan(loan_id),
  step                    INTEGER NOT NULL CHECK (step BETWEEN 1 AND 4),
  -- 1 = 1. Mahnung, 2 = 2. Mahnung, 3 = Bonitätsentscheid, 4 = Verwertungsbegehren
  step_label              TEXT NOT NULL,
  issued_date             TEXT NOT NULL,
  due_date                TEXT NOT NULL,
  amount_overdue_chf      REAL NOT NULL,
  fee_chf                 REAL NOT NULL DEFAULT 0,
  status                  TEXT NOT NULL DEFAULT 'open'
                              CHECK (status IN ('open','paid','escalated','closed')),
  resolved_date           TEXT,
  assigned_officer        TEXT,
  reference               TEXT
);
CREATE INDEX ix_dunning_loan ON dunning_step(loan_id, step);
CREATE INDEX ix_dunning_status ON dunning_step(status);
