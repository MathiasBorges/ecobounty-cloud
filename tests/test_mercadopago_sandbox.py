"""Testes para o serviço de transferências Pix via Mercado Pago Sandbox."""
from app.database.connection import init_db
from app.services.mercadopago_service import MercadoPagoService
from app.services.wallet_service import WalletService


def test_mercadopago_sandbox_pix_transfer():
    mp = MercadoPagoService(access_token="", sandbox=True)
    res = mp.create_pix_transfer(
        user_id=1,
        user_name="João Silva",
        user_email="joao@ecobounty.com",
        pix_key="joao@ecobounty.com",
        pix_key_type="E-mail",
        amount=25.0,
    )
    assert res["success"] is True
    assert res["status"] == "approved"
    assert res["sandbox"] is True
    assert res["amount"] == 25.0
    assert res["mp_payment_id"].startswith("MPSB-")


def test_wallet_withdraw_pix_mercadopago(tmp_path):
    db_file = str(tmp_path / "mp_wallet.db")
    init_db(db_file)
    wallet = WalletService(db_path=db_file)

    # Saldo inicial de João Silva (user_id=1) é 45.00
    initial_bal = wallet.get_balance(1)
    assert initial_bal == 45.0

    ok, new_bal, msg, mp_info = wallet.withdraw_pix(
        user_id=1,
        amount=20.0,
        pix_key="123.456.789-00",
        pix_key_type="CPF",
    )
    assert ok is True
    assert new_bal == 25.0
    assert "Mercado Pago Sandbox" in msg
    assert mp_info.get("status") == "approved"

    # Tentativa de saque maior que o saldo disponível deve ser recusada
    ok2, bal2, msg2, _ = wallet.withdraw_pix(
        user_id=1,
        amount=100.0,
        pix_key="123.456.789-00",
        pix_key_type="CPF",
    )
    assert ok2 is False
    assert bal2 == 25.0
    assert "insuficiente" in msg2.lower()


def test_sponsor_and_ecoponto_create_bounty_mercadopago(tmp_path):
    from app.services.bounty_service import BountyService

    db_file = str(tmp_path / "mp_sponsor.db")
    init_db(db_file)
    wallet = WalletService(db_path=db_file)
    bounty_svc = BountyService(db_path=db_file)

    # 1. Patrocinador/Ecoponto deposita Fundo ESG via Pix Mercado Pago Sandbox
    ok_dep, new_bal, msg_dep, _ = wallet.deposit_funds_pix(user_id=2, amount=80.0, description="Aporte ESG")
    assert ok_dep is True
    assert new_bal == 580.0  # 500 inicial + 80

    # 2. Patrocinador/Ecoponto cria Bounty Patrocinado com valor customizado (R$ 75.00)
    ok_b, new_bounty, msg_b, mp_res = bounty_svc.create_sponsored_bounty(
        user_id=2,
        sponsor_name="Construtora Verde ESG",
        title="Mutirão Patrocinado da Orla",
        waste_type="Plástico",
        dest="COOPLUM",
        val=75.0,
        lat=-9.665,
        lng=-35.735,
    )
    assert ok_b is True
    assert new_bounty is not None
    assert new_bounty.val == 75.0
    assert new_bounty.sponsor == "Construtora Verde ESG"
    assert wallet.get_balance(2) == 505.0  # 580 - 75


