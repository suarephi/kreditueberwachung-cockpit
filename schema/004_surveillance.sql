-- 004_surveillance.sql -- Event-based monitoring, cases, documents, audit.

CREATE TABLE event (
  event_id                 INTEGER PRIMARY KEY,
  loan_id                  INTEGER REFERENCES loan(loan_id),
  client_id                INTEGER REFERENCES client(client_id),
  property_id              INTEGER REFERENCES property(property_id),
  event_type               TEXT NOT NULL,
  event_subtype            TEXT,
  severity                 TEXT NOT NULL CHECK (severity IN ('info','low','medium','high','critical')),
  source                   TEXT NOT NULL,
  detected_at              TEXT NOT NULL,
  occurred_at              TEXT,
  title                    TEXT,
  description              TEXT,
  status                   TEXT NOT NULL DEFAULT 'open'
                              CHECK (status IN ('open','in_progress','waived','closed_resolved','escalated')),
  assigned_to              TEXT,
  resolved_at              TEXT,
  sla_due_date             TEXT,
  linked_case_id           INTEGER
);
CREATE INDEX ix_event_loan       ON event(loan_id);
CREATE INDEX ix_event_status_sev ON event(status, severity);
CREATE INDEX ix_event_type       ON event(event_type);

CREATE TABLE loan_case (
  case_id                  INTEGER PRIMARY KEY,
  case_type                TEXT NOT NULL,
  loan_id                  INTEGER REFERENCES loan(loan_id),
  client_id                INTEGER REFERENCES client(client_id),
  opened_at                TEXT NOT NULL,
  due_date                 TEXT,
  closed_at                TEXT,
  status                   TEXT NOT NULL DEFAULT 'open',
  priority                 TEXT NOT NULL DEFAULT 'normal',
  assigned_team            TEXT,
  assigned_officer         TEXT,
  decision                 TEXT,
  decision_at              TEXT,
  decided_by               TEXT,
  notes                    TEXT
);
CREATE INDEX ix_case_loan ON loan_case(loan_id);

CREATE TABLE document (
  document_id              INTEGER PRIMARY KEY,
  parent_type              TEXT NOT NULL CHECK (parent_type IN ('client','loan','property','case','event')),
  parent_id                INTEGER NOT NULL,
  doc_type                 TEXT NOT NULL,
  filename                 TEXT,
  upload_date              TEXT,
  expiry_date              TEXT,
  status                   TEXT NOT NULL CHECK (status IN ('valid','expired','missing','superseded')),
  hash                     TEXT
);
CREATE INDEX ix_doc_parent ON document(parent_type, parent_id);

CREATE TABLE audit_log (
  audit_id                 INTEGER PRIMARY KEY,
  entity_type              TEXT NOT NULL,
  entity_id                INTEGER NOT NULL,
  field_name               TEXT NOT NULL,
  old_value                TEXT,
  new_value                TEXT,
  changed_by               TEXT,
  changed_at               TEXT NOT NULL,
  source_system            TEXT
);
CREATE INDEX ix_audit_entity ON audit_log(entity_type, entity_id);
