"""Testes unitários de carteira digital e idempotência financeira (RNF08, RF11)."""
import os
import tempfile
import pytest

from app.database.connection import init_db
from app.services.wallet_service import WalletService


@pytest.fixture
def test_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path, force_reset=True)
    yield path
    if os.path.exists(path):
        os.unlink(path)


def test_credit_advance_and_idempotency(test_db):
    wallet = WalletService(test_db)
    # Saldo inicial é 45.00
    assert wallet.get_balance(1) == 45.00

    # Adiantamento de 50% de R$ 20,00 = R$ 10,00
    ok, new_bal, msg = wallet.credit_advance(user_id=1, bounty_id=1, total_val=20.00)
    assert ok is True
    assert new_bal == 55.00

    # Segundo toque/tentativa duplicada deve ser bloqueada por idempotência
    ok_dup, dup_bal, dup_msg = wallet.credit_advance(user_id=1, bounty_id=1, total_val=20.00)
    assert ok_dup is False
    assert dup_bal == 55.00
    assert "já creditado" in dup_msg


def test_credit_completion_and_odd_value_calculation(test_db):
    wallet = WalletService(test_db)
    # Bounty de R$ 45,00 (valor ímpar com centavos)
    # Adiantamento: 22.50. Saldo: 45 + 22.50 = 67.50
    ok1, bal1, _ = wallet.credit_advance(user_id=1, bounty_id=2, total_val=45.00)
    assert ok1 is True
    assert bal1 == 67.50

    # Quitação dos 50% restantes (22.50): Saldo final = 67.50 + 22.50 = 90.00
    ok2, bal2, _ = wallet.credit_completion(
        user_id=1, bounty_id=2, total_val=45.00, bounty_title="Entulho na Calçada"
    )
    assert ok2 is True
    assert bal2 == 90.00

    # Quitação duplicada bloqueada
    ok2_dup, bal2_dup, msg2_dup = wallet.credit_completion(
        user_id=1, bounty_id=2, total_val=45.00, bounty_title="Entulho na Calçada"
    )
    assert ok2_dup is False
    assert bal2_dup == 90.00
    assert "já realizada" in msg2_dup

    # Histórico registrado
    history = wallet.get_history(1)
    assert any(h.title == "Entulho na Calçada" for h in history)
