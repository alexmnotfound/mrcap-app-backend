-- Schema definition

-- Enumerated types
CREATE TYPE cash_movement_type AS ENUM ('deposit', 'withdrawal', 'fee');

CREATE TYPE fund_share_movement_type AS ENUM ('subscription', 'redemption');

CREATE TYPE app_user_status AS ENUM ('invited', 'active', 'suspended', 'disabled');

-- Tables
CREATE TABLE app_users (
    id BIGSERIAL PRIMARY KEY,
    firebase_uid TEXT NOT NULL,
    email TEXT NOT NULL,
    full_name TEXT NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    status app_user_status NOT NULL DEFAULT 'invited',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT app_users_email_unique UNIQUE (email),
    CONSTRAINT app_users_firebase_uid_unique UNIQUE (firebase_uid)
);

CREATE TABLE accounts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES app_users (id) ON DELETE CASCADE,
    account_number TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT accounts_account_number_unique UNIQUE (account_number)
);

CREATE TABLE funds (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    currency CHAR(3) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT funds_name_unique UNIQUE (name)
);

CREATE TABLE account_fund_positions (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts (id) ON DELETE CASCADE,
    fund_id BIGINT NOT NULL REFERENCES funds (id) ON DELETE CASCADE,
    share_balance NUMERIC(20, 6) NOT NULL DEFAULT 0,
    cost_basis NUMERIC(20, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT account_fund_positions_unique UNIQUE (account_id, fund_id)
);

CREATE TABLE fund_navs (
    id BIGSERIAL PRIMARY KEY,
    fund_id BIGINT NOT NULL REFERENCES funds (id) ON DELETE CASCADE,
    as_of_date DATE NOT NULL,
    fund_accumulated NUMERIC(20, 2) NOT NULL,
    shares_amount NUMERIC(20, 6) NOT NULL,
    share_value NUMERIC(18, 6) NOT NULL,
    delta_previous NUMERIC(8, 4),
    delta_since_origin NUMERIC(8, 4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fund_navs_fund_date_unique UNIQUE (fund_id, as_of_date)
);

CREATE TABLE cash_movements (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts (id) ON DELETE CASCADE,
    type cash_movement_type NOT NULL,
    amount NUMERIC(20, 2) NOT NULL,
    currency CHAR(3) NOT NULL,
    effective_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE fund_share_movements (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts (id) ON DELETE CASCADE,
    fund_id BIGINT NOT NULL REFERENCES funds (id) ON DELETE CASCADE,
    cash_movement_id BIGINT REFERENCES cash_movements (id) ON DELETE SET NULL,
    type fund_share_movement_type NOT NULL,
    shares_change NUMERIC(20, 6) NOT NULL,
    share_price NUMERIC(18, 6) NOT NULL,
    total_amount NUMERIC(20, 2) NOT NULL,
    effective_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    actor_user_id BIGINT REFERENCES app_users (id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity TEXT NOT NULL,
    entity_id BIGINT,
    before JSONB,
    after JSONB,
    at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX accounts_user_id_idx ON accounts (user_id);
CREATE INDEX fund_navs_fund_id_idx ON fund_navs (fund_id);
CREATE INDEX cash_movements_account_id_idx ON cash_movements (account_id);
CREATE INDEX account_fund_positions_account_fund_idx ON account_fund_positions (account_id, fund_id);
CREATE INDEX fund_share_movements_account_fund_idx ON fund_share_movements (account_id, fund_id);
CREATE INDEX fund_share_movements_effective_date_idx ON fund_share_movements (effective_date);
CREATE INDEX fund_share_movements_cash_movement_idx ON fund_share_movements (cash_movement_id);
CREATE INDEX audit_log_entity_idx ON audit_log (entity, entity_id);
CREATE INDEX audit_log_actor_idx ON audit_log (actor_user_id, at);

