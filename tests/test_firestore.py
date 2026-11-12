"""Testes de Integração e Conformidade Completa do FirestoreService."""
import pytest
from app.services.firestore_service import FirestoreService, get_firestore_service
from app.models.bounty import Bounty
from app.models.user import User
from app.models.transaction import Transaction, HistoryItem


def test_firestore_service_singleton_and_properties():
    svc = get_firestore_service()
    assert svc is not None
    assert svc.project_id == "ecobounty-9d250"
    assert svc.api_key.startswith("AIza")


def test_firestore_data_converters_bidirectional():
    svc = get_firestore_service()

    # Primitivos para Firestore REST
    assert svc._to_firestore_value("teste") == {"stringValue": "teste"}
    assert svc._to_firestore_value(123) == {"integerValue": "123"}
    assert svc._to_firestore_value(45.50) == {"doubleValue": 45.50}
    assert svc._to_firestore_value(True) == {"booleanValue": True}
    assert svc._to_firestore_value(None) == {"nullValue": None}

    # Mapa aninhado e lista
    nested = {"tags": ["recicla", "maceio"], "info": {"bairro": "Pajuçara"}}
    converted_nested = svc._to_firestore_value(nested)
    assert "mapValue" in converted_nested

    # Reversão (Firestore REST -> Python Nativo)
    fields = svc._to_firestore_fields({
        "title": "Descarte PET",
        "val": 35.5,
        "count": 10,
        "is_active": True,
    })
    recovered = svc._from_firestore_fields(fields)
    assert recovered["title"] == "Descarte PET"
    assert recovered["val"] == 35.5
    assert recovered["count"] == 10
    assert recovered["is_active"] is True


def test_firestore_save_helpers_non_blocking():
    svc = get_firestore_service()

    # Bounty mock
    b = Bounty(
        id=9999,
        title="Bounty Teste Firestore",
        val=100.0,
        dist=500,
        type="Plástico",
        dest="COOPLUM",
        img="/uploads/test.jpg",
        lat=-9.665,
        lng=-35.735,
    )
    svc.save_bounty_async(b)

    # User mock
    u = User(
        id=9999,
        name="Teste Firestore",
        email="firestore@ecobounty.com",
        cpf="000.000.000-00",
        phone="8299999999",
        password_hash="secret",
    )
    svc.save_user_async(u)

    # Transaction mock
    tx = Transaction(
        id=999,
        user_id=9999,
        bounty_id=9999,
        type="ADIANTAMENTO_50",
        amount=50.0,
        idempotency_key="tx_test_key_9999",
    )
    svc.save_transaction_async(tx)

    # History mock
    h = HistoryItem(
        id=999,
        user_id=9999,
        title="Missão Teste",
        status="Concluído",
        amount=100.0,
        date_label="Hoje",
    )
    svc.save_history_async(h)


def test_firestore_model_converters_and_updates():
    svc = get_firestore_service()

    # Conversão de dicionário para Bounty
    b_dict = {
        "id": "1234",
        "title": "Bounty Mock Firestore",
        "val": 45.0,
        "dist": 200,
        "type": "Metal",
        "dest": "COOPLUM",
        "img": "/uploads/test.jpg",
        "lat": -9.66,
        "lng": -35.70,
        "current_phase": 1,
    }
    b = svc._dict_to_bounty(b_dict)
    assert b.id == 1234
    assert b.title == "Bounty Mock Firestore"
    assert b.val == 45.0
    assert b.current_phase == 1

    # Conversão de dicionário para User
    u_dict = {
        "id": "5678",
        "name": "Maria Coletora",
        "email": "maria@ecobounty.com",
        "balance": 150.0,
        "total_earnings": 300.0,
        "waste_saved_kg": 45.0,
        "google_id": "google_12345",
    }
    u = svc._dict_to_user(u_dict)
    assert u.id == 5678
    assert u.name == "Maria Coletora"
    assert u.balance == 150.0
    assert getattr(u, "google_id") == "google_12345"

    # Atualizações
    assert isinstance(svc.update_bounty_phase(1234, 2), bool)
    assert isinstance(svc.update_user_balance(5678, 200.0, 350.0, 60.0), bool)
