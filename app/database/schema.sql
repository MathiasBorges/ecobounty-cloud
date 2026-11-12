-- ===================================================================
-- Esquema de Banco de Dados Local - EcoBounty (SQLite embutido)
-- ===================================================================

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    cpf TEXT NOT NULL,
    phone TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    balance REAL NOT NULL DEFAULT 0.0,
    total_earnings REAL NOT NULL DEFAULT 0.0,
    waste_saved_kg REAL NOT NULL DEFAULT 0.0,
    level_title TEXT NOT NULL DEFAULT 'Nível 1 • Recruta Verde',
    role TEXT NOT NULL DEFAULT 'COLETOR',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bounties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    val REAL NOT NULL,
    dist INTEGER NOT NULL,
    type TEXT NOT NULL,
    dest TEXT NOT NULL,
    img TEXT NOT NULL,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    icon TEXT NOT NULL,
    color TEXT NOT NULL,
    sponsor TEXT NOT NULL DEFAULT 'Parceiro ESG Maceió',
    status TEXT NOT NULL DEFAULT 'DISPONIVEL',
    assigned_user_id INTEGER,
    current_phase INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(assigned_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    bounty_id INTEGER NOT NULL,
    type TEXT NOT NULL, -- 'ADIANTAMENTO_50', 'QUITACAO_50'
    amount REAL NOT NULL,
    idempotency_key TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(bounty_id) REFERENCES bounties(id)
);

CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    amount REAL NOT NULL,
    date_label TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
