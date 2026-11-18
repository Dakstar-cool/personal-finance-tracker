PRAGMA foreign_keys = ON;

CREATE TABLE account (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    opened_on TEXT NOT NULL,
    opening_minor INTEGER NOT NULL CHECK (typeof(opening_minor) = 'integer')
);
CREATE TABLE category (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL CHECK (kind IN ('income', 'expense'))
);
CREATE TABLE entry (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES account(id) ON DELETE RESTRICT,
    category_id INTEGER NOT NULL REFERENCES category(id) ON DELETE RESTRICT,
    booked_on TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (
        typeof(amount_minor) = 'integer' AND amount_minor BETWEEN 1 AND 1000000000000
    ),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'posted', 'void')),
    bank_ref TEXT CHECK (bank_ref IS NULL OR length(trim(bank_ref)) > 0),
    note TEXT NOT NULL DEFAULT '',
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
    UNIQUE (account_id, bank_ref)
);
CREATE INDEX entry_period ON entry(account_id, status, booked_on);
CREATE TRIGGER check_entry_date BEFORE INSERT ON entry
WHEN NEW.booked_on < (SELECT opened_on FROM account WHERE id = NEW.account_id)
BEGIN SELECT RAISE(ABORT, 'before opening'); END;
CREATE TRIGGER check_changed_date BEFORE UPDATE OF booked_on, account_id ON entry
WHEN NEW.booked_on < (SELECT opened_on FROM account WHERE id = NEW.account_id)
BEGIN SELECT RAISE(ABORT, 'before opening'); END;
CREATE TRIGGER check_state BEFORE UPDATE OF status ON entry
WHEN NOT (
    (OLD.status='draft' AND NEW.status IN ('draft','posted','void')) OR
    (OLD.status='posted' AND NEW.status IN ('posted','void'))
)
BEGIN SELECT RAISE(ABORT, 'invalid transition'); END;
CREATE TRIGGER freeze_void BEFORE UPDATE ON entry WHEN OLD.status='void'
BEGIN SELECT RAISE(ABORT, 'void is final'); END;
CREATE TRIGGER keep_history BEFORE DELETE ON entry
BEGIN SELECT RAISE(ABORT, 'use void'); END;
CREATE TRIGGER fixed_kind BEFORE UPDATE OF kind ON category WHEN NEW.kind <> OLD.kind
BEGIN SELECT RAISE(ABORT, 'fixed category kind'); END;
