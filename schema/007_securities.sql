-- 007_securities.sql -- Wertschriftendepots (Cross-Sell-Sicht für Hypothekarkunden).

CREATE TABLE portfolio (
  portfolio_id            INTEGER PRIMARY KEY,
  client_id               INTEGER NOT NULL REFERENCES client(client_id),
  strategy                TEXT NOT NULL CHECK (strategy IN
                              ('konservativ','vorsichtig','mittel','wachstum','aktien')),
  benchmark               TEXT,
  inception_date          TEXT NOT NULL,
  total_value_chf         REAL NOT NULL,
  cash_chf                REAL NOT NULL,
  ytd_return_pct          REAL,
  one_year_return_pct     REAL,
  custodian               TEXT,
  fee_model               TEXT,
  last_review_date        TEXT
);
CREATE INDEX ix_portfolio_client   ON portfolio(client_id);
CREATE INDEX ix_portfolio_strategy ON portfolio(strategy);

CREATE TABLE position (
  position_id             INTEGER PRIMARY KEY,
  portfolio_id            INTEGER NOT NULL REFERENCES portfolio(portfolio_id),
  isin                    TEXT NOT NULL,
  name                    TEXT NOT NULL,
  asset_class             TEXT NOT NULL CHECK (asset_class IN
                              ('bond','equity','etf_bond','etf_equity','cash','alternative')),
  currency                TEXT NOT NULL,
  quantity                REAL NOT NULL,
  avg_cost_chf            REAL,
  market_price_chf        REAL NOT NULL,
  market_value_chf        REAL NOT NULL,
  unrealized_pnl_chf      REAL,
  weight_pct              REAL,
  last_price_date         TEXT
);
CREATE INDEX ix_position_portfolio ON position(portfolio_id);
CREATE INDEX ix_position_isin      ON position(isin);
