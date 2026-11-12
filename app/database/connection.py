"""Gerenciador de conexão e inicialização do banco SQLite local."""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import DB_PATH

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Retorna uma conexão configurada com row_factory ativado."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[str] = None, force_reset: bool = False) -> None:
    """Cria tabelas e popula dados iniciais se necessário."""
    path = db_path or DB_PATH
    if force_reset and Path(path).exists():
        Path(path).unlink(missing_ok=True)

    conn = get_connection(path)
    with conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())

        # Garante migração da coluna role caso a tabela já existisse
        try:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'COLETOR'")
        except sqlite3.OperationalError:
            pass

        now = datetime.now().isoformat()

        # Seed de usuários oficiais por perfil com senha padrão 123456
        default_users = [
            # Perfil Coletor (Agente Ambiental) - ID 1 para manter compatibilidade com suíte de testes
            (
                "Coletor Ativo",
                "coletor@ecobounty.com",
                "111.444.777-35",
                "(82) 99999-0000",
                "123456",
                45.00,
                380.00,
                125.00,
                "Nível 4 • Guardião do Bairro",
                "COLETOR",
            ),
            # Admins Únicos Oficiais
            (
                "Mathias Borges",
                "mathiasbm377@gmail.com",
                "000.000.002-02",
                "(82) 99999-0002",
                "123456",
                500.00,
                1500.00,
                450.00,
                "Administrador do Sistema • Scrum Master",
                "ADMIN",
            ),
            (
                "Allan Gabriel",
                "gabrielholallan09@gmail.com",
                "000.000.001-01",
                "(82) 99999-0001",
                "123456",
                500.00,
                1500.00,
                450.00,
                "Administrador do Sistema • Front-end Lead",
                "ADMIN",
            ),
            (
                "Kauê Lucas",
                "kauelucasbarbosa979@gmail.com",
                "000.000.003-03",
                "(82) 99999-0003",
                "123456",
                500.00,
                1500.00,
                450.00,
                "Administrador do Sistema • Back-end & IA Lead",
                "ADMIN",
            ),
            # Perfil Cidadão (Denunciante / Mapeador)
            (
                "Maria Silva (Cidadã)",
                "cidadao@ecobounty.com",
                "529.982.247-25",
                "(82) 98888-7777",
                "123456",
                0.00,
                0.00,
                35.00,
                "Cidadão Consciente • Mapeador",
                "CIDADAO",
            ),
            # Perfil Ecoponto / Cooperativa (Ponto de Destinação Homologado)
            (
                "Ecoponto ALURB / Cooplum",
                "ecoponto@ecobounty.com",
                "222.333.444-55",
                "(82) 98765-4321",
                "123456",
                0.00,
                0.00,
                1850.00,
                "Operador de Destinação Homologado",
                "ECOPONTO",
            ),
            # Perfil Patrocinador ESG (Financiador de Recompensas)
            (
                "Maceió Sustentável ESG",
                "patrocinador@ecobounty.com",
                "333.444.555-66",
                "(82) 98123-4567",
                "123456",
                5000.00,
                5000.00,
                3200.00,
                "Patrocinador ESG Oficial",
                "PATROCINADOR",
            ),
        ]

        for u in default_users:
            existing = conn.execute(
                "SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (u[1],)
            ).fetchone()
            if not existing:
                conn.execute(
                    """
                    INSERT INTO users (name, email, cpf, phone, password_hash, balance, total_earnings, waste_saved_kg, level_title, role, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (*u, now),
                )
            else:
                # Atualiza role e senha se já existia
                conn.execute(
                    """
                    UPDATE users
                    SET name = ?, password_hash = ?, level_title = ?, role = ?
                    WHERE LOWER(email) = LOWER(?)
                    """,
                    (u[0], u[4], u[8], u[9], u[1]),
                )

        # Seed de bounties padrão
        bounty_count = conn.execute("SELECT COUNT(*) AS total FROM bounties").fetchone()["total"]
        if bounty_count == 0:
            now = datetime.now().isoformat()
            initial_bounties = [
                (
                    1,
                    "Plástico na Encosta",
                    20.00,
                    450,
                    "Plástico",
                    "COOPLUM",
                    "https://images.unsplash.com/photo-1611284446314-60a58ac0deb9?auto=format&fit=crop&w=800&q=80",
                    -9.662,
                    -35.730,
                    "cup-soda",
                    "blue",
                    "Supermercado X",
                    "DISPONIVEL",
                    None,
                    0,
                    now,
                ),
                (
                    2,
                    "Entulho na Calçada",
                    45.00,
                    1200,
                    "Inerte",
                    "Ecoponto ALURB",
                    "https://images.unsplash.com/photo-1530587191325-3db32d826c18?auto=format&fit=crop&w=800&q=80",
                    -9.658,
                    -35.725,
                    "hammer",
                    "orange",
                    "Construtora Maceió",
                    "DISPONIVEL",
                    None,
                    0,
                    now,
                ),
                (
                    3,
                    "Lixo Eletrônico",
                    60.00,
                    800,
                    "Eletrônicos",
                    "COOPREL",
                    "https://images.unsplash.com/photo-1550989460-0adf9ea622e2?auto=format&fit=crop&w=800&q=80",
                    -9.671,
                    -35.740,
                    "monitor",
                    "slate",
                    "TechGreen ESG",
                    "DISPONIVEL",
                    None,
                    0,
                    now,
                ),
            ]
            conn.executemany(
                """
                INSERT INTO bounties (id, title, val, dist, type, dest, img, lat, lng, icon, color, sponsor, status, assigned_user_id, current_phase, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                initial_bounties,
            )

        # Seed de histórico inicial
        hist_count = conn.execute("SELECT COUNT(*) AS total FROM history").fetchone()["total"]
        if hist_count == 0:
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT INTO history (user_id, title, status, amount, date_label, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (1, "Madeira em Terreno", "Concluído", 35.00, "Ontem • Concluído", now),
            )
    conn.close()
