"""Teste de fluxo completo E2E dos Casos de Uso UC01 a UC11."""
import os
import tempfile
import pytest

from app.database.connection import init_db
from app.services.auth_service import AuthService
from app.services.bounty_service import BountyService
from app.services.wallet_service import WalletService


@pytest.fixture
def test_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path, force_reset=True)
    yield path
    if os.path.exists(path):
        os.unlink(path)


def test_full_mission_e2e_cycle(test_db):
    auth = AuthService(test_db)
    bounty_service = BountyService(test_db)
    wallet_service = WalletService(test_db)

    # 1. Login com credenciais válidas (UC01)
    ok_login, user, _ = auth.login("coletor@ecobounty.com", "123456")
    assert ok_login is True
    assert user.balance == 45.00

    # 2. Descoberta e Filtros (UC03, UC04)
    bounties = bounty_service.get_bounties("todos")
    assert len(bounties) == 3
    target_bounty = bounties[0]  # Plástico na Encosta (R$ 20,00, COOPLUM)
    assert target_bounty.id == 1
    assert target_bounty.val == 20.00
    assert target_bounty.dest == "COOPLUM"

    # 3. Aceite da Missão (UC06, UC07)
    ok_accept, msg_accept = bounty_service.accept_bounty(target_bounty.id, user.id)
    assert ok_accept is True

    # 4. Fase 1: Chegada no local e validação visual de limpeza por IA (UC08)
    ok_f1, half_val, msg_f1 = bounty_service.validate_phase1_cleaning(
        bounty_id=target_bounty.id, user_id=user.id
    )
    assert ok_f1 is True
    assert half_val == 10.00  # 50% de R$ 20,00
    assert wallet_service.get_balance(user.id) == 55.00  # 45 + 10

    # 5. Fase 2: Rota de descarte e validação via QR Code homologado (UC09)
    ok_f2, rem_val, msg_f2 = bounty_service.validate_phase2_ecopoint(
        bounty_id=target_bounty.id,
        user_id=user.id,
        qrcode_data="ECOPONTO-COOPLUM-001",
    )
    assert ok_f2 is True
    assert rem_val == 10.00

    # 6. Saldo final e integridade contábil (R$ 65,00)
    final_balance = wallet_service.get_balance(user.id)
    assert final_balance == 65.00

    # 7. Verificação do histórico no perfil do coletor (UC11)
    history = wallet_service.get_history(user.id)
    assert len(history) >= 2
    assert history[0].title == "Plástico na Encosta"
    assert history[0].amount == 20.00
