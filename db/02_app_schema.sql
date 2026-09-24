ALTER TABLE case_seed.quote_items
  ADD COLUMN replaced_by_item_id TEXT
    REFERENCES case_seed.quote_items(quote_item_id),
  ADD COLUMN is_backorder BOOLEAN NOT NULL DEFAULT false;

  ALTER TABLE case_seed.quote_items
  ADD CONSTRAINT chk_quote_items_status
    CHECK (status IN ('active', 'replaced', 'removed')),
  ADD CONSTRAINT chk_quote_items_quantity
    CHECK (quantity >= 0);

    CREATE UNIQUE INDEX uq_quote_items_active_product
  ON case_seed.quote_items (quote_id, product_id)
  WHERE status = 'active';

  CREATE TABLE case_seed.idempotency_keys (
  idempotency_key TEXT PRIMARY KEY,
  tool_name       TEXT NOT NULL,
  quote_id        TEXT NOT NULL REFERENCES case_seed.quotes(quote_id),
  response        JSONB NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE case_seed.chat_sessions (
  session_id  TEXT PRIMARY KEY,
  quote_id    TEXT NOT NULL REFERENCES case_seed.quotes(quote_id),
  channel     TEXT NOT NULL CHECK (channel IN ('mobile', 'web', 'test')),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE case_seed.chat_messages (
  message_id  TEXT PRIMARY KEY,
  session_id  TEXT NOT NULL REFERENCES case_seed.chat_sessions(session_id),
  role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content     TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE case_seed.tool_call_logs (
  id          BIGSERIAL PRIMARY KEY,
  session_id  TEXT REFERENCES case_seed.chat_sessions(session_id),
  message_id  TEXT REFERENCES case_seed.chat_messages(message_id),
  seq         INTEGER NOT NULL,
  tool_name   TEXT NOT NULL,
  input       JSONB NOT NULL,
  status      TEXT NOT NULL CHECK (status IN ('success', 'error')),
  output      JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tool_call_logs_message
  ON case_seed.tool_call_logs (message_id, seq);