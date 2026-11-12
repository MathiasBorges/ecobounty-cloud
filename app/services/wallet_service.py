"""Serviço de Carteira Digital e Integridade Financeira (Google Cloud Firestore).

Garante a Regra 50/50, atualização dinâmica de saldos e proteção contra créditos
duplicados através de chaves de idempotência (RNF08, RF11), com sincronização
em nuvem no Cloud Firestore.
"""
from datetime import datetime
from typing import List, Optional, Tuple

from app.database.connection import get_connection
from app.models.transaction import HistoryItem, Transaction


class WalletService:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def get_balance(self, user_id: int) -> float:
        """Obtém o saldo atualizado do usuário diretamente do banco local ou Cloud Firestore."""
        conn = get_connection(self.db_path)
        try:
            row = conn.execute("SELECT balance FROM users WHERE id = ?", (user_id,)).fetchone()
            if row:
                return float(row["balance"])

            # Fallback para o Cloud Firestore
            try:
                from app.services.firestore_service import get_firestore_service
                user = get_firestore_service().get_user(user_id)
                if user:
                    return float(user.balance)
            except Exception:
                pass

            return 0.0
        finally:
            conn.close()

    def credit_advance(self, user_id: int, bounty_id: int, total_val: float) -> Tuple[bool, float, str]:
        """Credita 50% de adiantamento (Fase 1) com idempotência garantida e sincronização Firestore."""
        half_val = round(total_val / 2.0, 2)
        idempotency_key = f"advance_{user_id}_{bounty_id}"
        now = datetime.now().isoformat()

        conn = get_connection(self.db_path)
        try:
            with conn:
                # Verifica duplicidade
                existing = conn.execute(
                    "SELECT id FROM transactions WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()

                if existing:
                    curr_bal = conn.execute("SELECT balance FROM users WHERE id = ?", (user_id,)).fetchone()["balance"]
                    return False, float(curr_bal), "Adiantamento já creditado anteriormente para esta missão."

                # Registra transação
                cursor = conn.execute(
                    """
                    INSERT INTO transactions (user_id, bounty_id, type, amount, idempotency_key, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, bounty_id, "ADIANTAMENTO_50", half_val, idempotency_key, now),
                )
                tx_id = cursor.lastrowid

                # Atualiza saldo e ganhos totais do usuário
                conn.execute(
                    """
                    UPDATE users
                    SET balance = balance + ?,
                        total_earnings = total_earnings + ?
                    WHERE id = ?
                    """,
                    (half_val, half_val, user_id),
                )

                user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                new_bal = user_row["balance"]

                # Sincroniza transação e usuário no Cloud Firestore
                try:
                    from app.services.firestore_service import get_firestore_service
                    svc = get_firestore_service()
                    tx = Transaction(
                        id=tx_id,
                        user_id=user_id,
                        bounty_id=bounty_id,
                        type="ADIANTAMENTO_50",
                        amount=half_val,
                        idempotency_key=idempotency_key,
                        created_at=now,
                    )
                    svc.save_transaction_async(tx)
                    svc.update_user_balance(
                        user_id=user_id,
                        balance=float(user_row["balance"]),
                        total_earnings=float(user_row["total_earnings"]),
                        waste_saved_kg=float(user_row["waste_saved_kg"]),
                    )
                except Exception:
                    pass
                except Exception:
                    pass

                return True, float(new_bal), "Adiantamento de 50% creditado com sucesso."
        finally:
            conn.close()

    def credit_completion(
        self, user_id: int, bounty_id: int, total_val: float, bounty_title: str = "Missão Concluída"
    ) -> Tuple[bool, float, str]:
        """Credita os 50% restantes (Fase 2) com idempotência, histórico e sincronização Firestore."""
        advance_val = round(total_val / 2.0, 2)
        remaining_val = round(total_val - advance_val, 2)
        idempotency_key = f"completion_{user_id}_{bounty_id}"
        now = datetime.now().isoformat()

        conn = get_connection(self.db_path)
        try:
            with conn:
                existing = conn.execute(
                    "SELECT id FROM transactions WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()

                if existing:
                    curr_bal = conn.execute("SELECT balance FROM users WHERE id = ?", (user_id,)).fetchone()["balance"]
                    return False, float(curr_bal), "Quitação final já realizada para esta missão."

                # Registra transação
                cursor_tx = conn.execute(
                    """
                    INSERT INTO transactions (user_id, bounty_id, type, amount, idempotency_key, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, bounty_id, "QUITACAO_50", remaining_val, idempotency_key, now),
                )
                tx_id = cursor_tx.lastrowid

                # Atualiza usuário (saldo, ganhos e kg salvos)
                conn.execute(
                    """
                    UPDATE users
                    SET balance = balance + ?,
                        total_earnings = total_earnings + ?,
                        waste_saved_kg = waste_saved_kg + 15.0
                    WHERE id = ?
                    """,
                    (remaining_val, remaining_val, user_id),
                )

                # Adiciona ao histórico recente
                cursor_hist = conn.execute(
                    """
                    INSERT INTO history (user_id, title, status, amount, date_label, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, bounty_title, "Concluído", total_val, "Hoje • Concluído", now),
                )
                hist_id = cursor_hist.lastrowid

                user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                new_bal = user_row["balance"]

                # Sincroniza no Cloud Firestore
                try:
                    from app.services.firestore_service import get_firestore_service
                    svc = get_firestore_service()
                    tx = Transaction(
                        id=tx_id,
                        user_id=user_id,
                        bounty_id=bounty_id,
                        type="QUITACAO_50",
                        amount=remaining_val,
                        idempotency_key=idempotency_key,
                        created_at=now,
                    )
                    svc.save_transaction_async(tx)

                    h_item = HistoryItem(
                        id=hist_id,
                        user_id=user_id,
                        title=bounty_title,
                        status="Concluído",
                        amount=total_val,
                        date_label="Hoje • Concluído",
                        created_at=now,
                    )
                    svc.save_history_async(h_item)

                    svc.update_user_balance(
                        user_id=user_id,
                        balance=float(user_row["balance"]),
                        total_earnings=float(user_row["total_earnings"]),
                        waste_saved_kg=float(user_row["waste_saved_kg"]),
                    )
                except Exception:
                    pass

                return True, float(new_bal), "Ciclo fechado! 100% da recompensa quitada."
        finally:
            conn.close()

    def get_history(self, user_id: int) -> List[HistoryItem]:
        """Recupera histórico recente de missões concluídas (SQLite com fallback Firestore)."""
        conn = get_connection(self.db_path)
        try:
            rows = conn.execute(
                """
                SELECT id, user_id, title, status, amount, date_label, created_at
                FROM history
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()
            if rows:
                return [
                    HistoryItem(
                        id=r["id"],
                        user_id=r["user_id"],
                        title=r["title"],
                        status=r["status"],
                        amount=float(r["amount"]),
                        date_label=r["date_label"],
                        created_at=r["created_at"],
                    )
                    for r in rows
                ]

            # Fallback para o Cloud Firestore
            try:
                from app.services.firestore_service import get_firestore_service
                return get_firestore_service().get_history_for_user(user_id)
            except Exception:
                return []
        finally:
            conn.close()

    def withdraw_pix(
        self,
        user_id: int,
        amount: float,
        pix_key: str,
        pix_key_type: str = "CPF/E-mail",
    ) -> Tuple[bool, float, str, dict]:
        """Executa transferência/saque Pix via Mercado Pago (Sandbox) e debita o saldo do coletor."""
        import uuid
        from app.services.mercadopago_service import get_mercadopago_service

        clean_key = (pix_key or "").strip()
        if not clean_key:
            return False, self.get_balance(user_id), "Informe uma chave Pix válida.", {}

        if amount <= 0:
            return False, self.get_balance(user_id), "O valor do saque deve ser maior que zero.", {}

        conn = get_connection(self.db_path)
        try:
            with conn:
                user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                if not user_row:
                    return False, 0.0, "Usuário não encontrado.", {}

                curr_bal = float(user_row["balance"])
                req_amount = round(float(amount), 2)
                if req_amount > curr_bal:
                    return False, curr_bal, f"Saldo insuficiente (disponível: R$ {curr_bal:.2f}).", {}

                idem_key = f"mp_pix_{user_id}_{uuid.uuid4().hex[:10]}"
                mp_res = get_mercadopago_service().create_pix_transfer(
                    user_id=user_id,
                    user_name=user_row["name"],
                    user_email=user_row["email"],
                    pix_key=clean_key,
                    pix_key_type=pix_key_type,
                    amount=req_amount,
                    idempotency_key=idem_key,
                )
                if not mp_res.get("success"):
                    return False, curr_bal, mp_res.get("message", "Falha ao processar Pix no Mercado Pago."), mp_res

                now = datetime.now().isoformat()
                mp_id = mp_res.get("mp_payment_id", idem_key)

                bounty_row = conn.execute("SELECT id FROM bounties ORDER BY id ASC LIMIT 1").fetchone()
                ref_bounty_id = int(bounty_row["id"]) if bounty_row else None
                tx_id = 0
                if ref_bounty_id is not None:
                    cursor_tx = conn.execute(
                        """
                        INSERT INTO transactions (user_id, bounty_id, type, amount, idempotency_key, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (user_id, ref_bounty_id, "SAQUE_PIX_MP", -req_amount, f"{idem_key}_{mp_id}", now),
                    )
                    tx_id = cursor_tx.lastrowid or 0

                conn.execute(
                    "UPDATE users SET balance = ROUND(balance - ?, 2) WHERE id = ?",
                    (req_amount, user_id),
                )

                cursor_hist = conn.execute(
                    """
                    INSERT INTO history (user_id, title, status, amount, date_label, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        f"Saque Pix MP ({pix_key_type}: {clean_key})",
                        "Mercado Pago Sandbox",
                        req_amount,
                        f"Pix #{mp_id} • Aprovado",
                        now,
                    ),
                )
                hist_id = cursor_hist.lastrowid

                updated_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                new_bal = float(updated_row["balance"])

                try:
                    from app.services.firestore_service import get_firestore_service
                    svc = get_firestore_service()
                    tx = Transaction(
                        id=tx_id,
                        user_id=user_id,
                        bounty_id=0,
                        type="SAQUE_PIX_MP",
                        amount=-req_amount,
                        idempotency_key=f"{idem_key}_{mp_id}",
                        created_at=now,
                    )
                    svc.save_transaction_async(tx)
                    h_item = HistoryItem(
                        id=hist_id,
                        user_id=user_id,
                        title=f"Saque Pix MP ({pix_key_type}: {clean_key})",
                        status="Mercado Pago Sandbox",
                        amount=req_amount,
                        date_label=f"Pix #{mp_id} • Aprovado",
                        created_at=now,
                    )
                    svc.save_history_async(h_item)
                    svc.update_user_balance(
                        user_id=user_id,
                        balance=new_bal,
                        total_earnings=float(updated_row["total_earnings"]),
                        waste_saved_kg=float(updated_row["waste_saved_kg"]),
                    )
                except Exception:
                    pass

                return True, new_bal, mp_res.get("message", "Transferência Pix concluída!"), mp_res
        finally:
            conn.close()

    def deposit_funds_pix(
        self,
        user_id: int,
        amount: float,
        description: str = "Aporte de Fundo ESG",
    ) -> Tuple[bool, float, str, dict]:
        """Adiciona saldo (Fundo ESG para Patrocinador/Ecoponto) via Pix no Mercado Pago Sandbox."""
        import uuid
        from app.services.mercadopago_service import get_mercadopago_service

        if amount <= 0:
            return False, self.get_balance(user_id), "Informe um valor maior que zero para o depósito.", {}

        conn = get_connection(self.db_path)
        try:
            with conn:
                user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                if not user_row:
                    return False, 0.0, "Usuário não encontrado.", {}

                req_amount = round(float(amount), 2)
                idem_key = f"mp_dep_{user_id}_{uuid.uuid4().hex[:10]}"
                mp_res = get_mercadopago_service().create_pix_transfer(
                    user_id=user_id,
                    user_name=user_row["name"],
                    user_email=user_row["email"],
                    pix_key=user_row["email"] or "fundo.esg@ecobounty.com",
                    pix_key_type="Fundo ESG",
                    amount=req_amount,
                    idempotency_key=idem_key,
                )
                if not mp_res.get("success"):
                    return False, float(user_row["balance"]), mp_res.get("message", "Erro no Mercado Pago."), mp_res

                now = datetime.now().isoformat()
                mp_id = mp_res.get("mp_payment_id", idem_key)

                bounty_row = conn.execute("SELECT id FROM bounties ORDER BY id ASC LIMIT 1").fetchone()
                ref_bounty_id = int(bounty_row["id"]) if bounty_row else None
                tx_id = 0
                if ref_bounty_id is not None:
                    cursor_tx = conn.execute(
                        """
                        INSERT INTO transactions (user_id, bounty_id, type, amount, idempotency_key, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (user_id, ref_bounty_id, "APORTE_ESG_MP", req_amount, f"{idem_key}_{mp_id}", now),
                    )
                    tx_id = cursor_tx.lastrowid or 0

                conn.execute(
                    "UPDATE users SET balance = ROUND(balance + ?, 2) WHERE id = ?",
                    (req_amount, user_id),
                )

                cursor_hist = conn.execute(
                    """
                    INSERT INTO history (user_id, title, status, amount, date_label, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        f"{description} (Mercado Pago)",
                        "Crédito ESG Aprovado",
                        req_amount,
                        f"Pix #{mp_id} • Sandbox",
                        now,
                    ),
                )
                hist_id = cursor_hist.lastrowid

                updated_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                new_bal = float(updated_row["balance"])

                try:
                    from app.services.firestore_service import get_firestore_service
                    svc = get_firestore_service()
                    tx = Transaction(
                        id=tx_id,
                        user_id=user_id,
                        bounty_id=ref_bounty_id or 0,
                        type="APORTE_ESG_MP",
                        amount=req_amount,
                        idempotency_key=f"{idem_key}_{mp_id}",
                        created_at=now,
                    )
                    svc.save_transaction_async(tx)
                    h_item = HistoryItem(
                        id=hist_id,
                        user_id=user_id,
                        title=f"{description} (Mercado Pago)",
                        status="Crédito ESG Aprovado",
                        amount=req_amount,
                        date_label=f"Pix #{mp_id} • Sandbox",
                        created_at=now,
                    )
                    svc.save_history_async(h_item)
                    svc.update_user_balance(
                        user_id=user_id,
                        balance=new_bal,
                        total_earnings=float(updated_row["total_earnings"]),
                        waste_saved_kg=float(updated_row["waste_saved_kg"]),
                    )
                except Exception:
                    pass

                return True, new_bal, f"Fundo ESG de R$ {req_amount:.2f} adicionado via Mercado Pago Sandbox ({mp_id})!", mp_res
        finally:
            conn.close()
