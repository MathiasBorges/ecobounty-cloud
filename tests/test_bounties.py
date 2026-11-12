"""Testes unitários de descoberta, filtros, missões e denúncias (UC03 - UC10)."""
import os
import tempfile
import pytest

from app.database.connection import init_db
from app.services.bounty_service import BountyService, haversine_distance


@pytest.fixture
def test_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path, force_reset=True)
    yield path
    if os.path.exists(path):
        os.unlink(path)


def test_bounty_listing_and_formatting(test_db):
    service = BountyService(test_db)
    bounties = service.get_bounties("todos")
    assert len(bounties) == 3

    b1 = bounties[0]
    assert b1.formatted_distance() == "450m"
    assert b1.formatted_value() == "R$ 20,00"

    b2 = bounties[1]
    assert b2.formatted_distance() == "1.2km"
    assert b2.formatted_value() == "R$ 45,00"


def test_filter_proximos(test_db):
    service = BountyService(test_db)
    bounties = service.get_bounties("proximos")
    distances = [b.dist for b in bounties]
    assert distances == [450, 800, 1200]
    assert bounties[0].title == "Plástico na Encosta"
    assert bounties[1].title == "Lixo Eletrônico"
    assert bounties[2].title == "Entulho na Calçada"


def test_filter_valiosos(test_db):
    service = BountyService(test_db)
    bounties = service.get_bounties("valiosos")
    values = [b.val for b in bounties]
    assert values == [60.00, 45.00, 20.00]
    assert bounties[0].title == "Lixo Eletrônico"
    assert bounties[1].title == "Entulho na Calçada"
    assert bounties[2].title == "Plástico na Encosta"


def test_filter_plastico(test_db):
    service = BountyService(test_db)
    bounties = service.get_bounties("plastico")
    assert len(bounties) == 1
    assert bounties[0].title == "Plástico na Encosta"
    assert bounties[0].type == "Plástico"


def test_haversine_distance_calculation():
    # Coordenadas do teste UC07 FE2: ~333m
    dist = haversine_distance(-9.665, -35.730, -9.662, -35.730)
    assert 320 <= dist <= 340


def test_check_in_cleaning_radius(test_db):
    service = BountyService(test_db)
    # Usuário a 330m de distância
    ok, msg, dist = service.check_in_cleaning_location(
        bounty_id=1, user_lat=-9.665, user_lng=-35.730, enforce_radius=True
    )
    assert ok is False
    assert "Você ainda não está no local da missão" in msg

    # Usuário exatamente no local (distância 0m)
    ok_near, msg_near, dist_near = service.check_in_cleaning_location(
        bounty_id=1, user_lat=-9.662, user_lng=-35.730, enforce_radius=True
    )
    assert ok_near is True
    assert dist_near < 5.0


def test_mission_lock_another_user(test_db):
    service = BountyService(test_db)
    # Usuário 1 aceita a missão
    ok1, _ = service.accept_bounty(bounty_id=2, user_id=1)
    assert ok1 is True

    # Outro usuário (id 2) tenta aceitar a mesma missão
    ok2, msg2 = service.accept_bounty(bounty_id=2, user_id=2)
    assert ok2 is False
    assert msg2 == "Missão indisponível – já aceita por outro coletor"


def test_phase2_ecopoint_qrcode_divergent(test_db):
    service = BountyService(test_db)
    # Bounty id 1 exige COOPLUM
    # QR Code lido é de outro ecoponto (ALURB)
    ok, amount, msg = service.validate_phase2_ecopoint(
        bounty_id=1, user_id=1, qrcode_data="ECOPONTO-ALURB-002"
    )
    assert ok is False
    assert amount == 0.0
    assert "Destino incorreto. Leve o resíduo até COOPLUM." in msg


def test_denuncia_duplicate_prevention(test_db):
    service = BountyService(test_db)
    # Posição a ~15m do bounty id 1 (-9.662, -35.730)
    ok, bounty, msg = service.create_denuncia_bounty(
        user_id=1, lat=-9.6621, lng=-35.7301
    )
    assert ok is False
    assert bounty is None
    assert msg == "Já existe uma missão aberta para este local"


def test_denuncia_creation_success(test_db):
    service = BountyService(test_db)
    # Nova posição longe das existentes
    ok, bounty, msg = service.create_denuncia_bounty(
        user_id=1, lat=-9.6500, lng=-35.7100
    )
    assert ok is True
    assert bounty is not None
    assert bounty.status == "DISPONIVEL"
    assert "Bounty Criado!" in msg
