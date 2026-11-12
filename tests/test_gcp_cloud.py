"""Testes unitários para a Camada em Nuvem Google Cloud Platform & Firebase.

Valida os requisitos R1 a R6 do PROJETO FINAL - CLOUD COMPUTING.pdf no ambiente Google for Students:
- Firebase Storage / Cloud Storage (Upload de fotos e URLs seguras)
- Cloud Firestore (Persistência NoSQL de missões e usuários)
- Google Cloud Functions (Processamento Serverless de auditoria)
- Google Cloud Vision API (Visão Computacional na Nuvem)
- Google Auth (Autenticação e Federação de Identidade)
- Regras de Segurança do Firestore (firestore.rules) e manifesto firebase.json
"""
from pathlib import Path
import pytest

from app.cloud.gcp_provider import GoogleCloudProvider, get_gcp_provider
from app.cloud.cloud_architecture import (
    get_architecture_mapping,
    generate_firestore_rules,
    generate_firebase_json,
    save_cloud_artifacts,
)
from app.services.storage_service import FirebaseStorageService
from app.services.vision_service import GoogleVisionService
from app.services.auth_service import AuthService


def test_gcp_provider_offline_mock_mode():
    provider = GoogleCloudProvider(
        project_id="ecobounty-test-project",
        storage_bucket="ecobounty-test.firebasestorage.app",
    )
    assert provider.project_id == "ecobounty-test-project"
    assert provider.storage_bucket == "ecobounty-test.firebasestorage.app"

    # Upload simulado no Firebase / Cloud Storage
    test_bytes = b"FAKE_PHOTO_BYTES_ECOBOUNTY_GCP"
    url = provider.upload_image(test_bytes, filename="bounties/test_bounty.jpg")
    assert "https://storage.googleapis.com" in url
    assert "test_bounty.jpg" in url

    # URL assinada
    signed = provider.generate_signed_url("bounties/test_bounty.jpg", expiration_minutes=15)
    assert "test_bounty.jpg" in signed
    assert "token=" in signed

    # Listagem de objetos
    objs = provider.list_storage_objects()
    assert "bounties/test_bounty.jpg" in objs


def test_gcp_firestore_put_and_get():
    provider = GoogleCloudProvider()
    bounty_data = {
        "id": "bounty-99",
        "title": "Descarte na Orla de Pajuçara",
        "val": 50.0,
        "lat": -9.6675,
        "lng": -35.7180,
    }

    assert provider.firestore_put_bounty(bounty_data) is True
    retrieved = provider.firestore_get_bounty("bounty-99")
    assert retrieved is not None
    assert retrieved["title"] == "Descarte na Orla de Pajuçara"
    assert retrieved["val"] == 50.0


def test_gcp_cloud_functions_serverless_handler():
    # Execução bem-sucedida
    event_ok = {"bounty_id": 42, "mode": "phase1", "simulate_failure": False}
    res_ok = GoogleCloudProvider.cloud_function_audit_handler(event_ok)
    assert res_ok["statusCode"] == 200
    assert res_ok["body"]["approved"] is True
    assert res_ok["body"]["advance_reward_released"] is True

    # Execução com reprovação por resíduo remanescente
    event_fail = {"bounty_id": 42, "mode": "phase1", "simulate_failure": True}
    res_fail = GoogleCloudProvider.cloud_function_audit_handler(event_fail)
    assert res_fail["statusCode"] == 422
    assert res_fail["body"]["approved"] is False


def test_gcp_vision_labels_and_audit():
    provider = GoogleCloudProvider()
    labels = provider.vision_detect_labels(b"PHOTO_BYTES_PLASTIC")
    assert len(labels) > 0
    names = [l["Name"] for l in labels]
    assert "Plastic" in names or "Waste" in names

    audit_ok = provider.audit_cleaning_vision(b"PHOTO_BYTES", bounty_id=1, simulate_failure=False)
    assert audit_ok["approved"] is True

    audit_fail = provider.audit_cleaning_vision(b"PHOTO_BYTES", bounty_id=1, simulate_failure=True)
    assert audit_fail["approved"] is False


def test_gcp_google_auth_flow(tmp_path):
    auth_service = AuthService(db_path=str(tmp_path / "test_auth.db"))
    from app.database.connection import init_db
    init_db(str(tmp_path / "test_auth.db"), force_reset=True)

    google_data = {
        "name": "Catador Silva Google",
        "email": "catador.silva@gmail.com",
        "uid": "google_uid_987654",
    }
    success, user, msg = auth_service.login_or_register_with_google(google_user_data=google_data)
    assert success is True
    assert user is not None
    assert user.email == "catador.silva@gmail.com"
    assert user.name == "Catador Silva Google"
    assert getattr(user, "google_id") == "google_uid_987654"

    # Segundo login com mesma conta Google
    success2, user2, msg2 = auth_service.login_or_register_with_google(google_user_data=google_data)
    assert success2 is True
    assert user2.id == user.id


def test_gcp_storage_and_vision_services():
    storage = FirebaseStorageService()
    saved_url = storage.save_image(b"TEST_BYTES", "jpg")
    assert "googleapis" in saved_url or "uploads" in saved_url

    vision = GoogleVisionService()
    audit_res = vision.audit_cleaning(b"BYTES", bounty_id=1, simulate_failure=False)
    assert audit_res["approved"] is True

    audit_fail = vision.audit_cleaning(b"BYTES", bounty_id=1, simulate_failure=True)
    assert audit_fail["approved"] is False


def test_cloud_architecture_mappings_and_iac_generation(tmp_path):
    mapping = get_architecture_mapping()
    assert "R1" in mapping
    assert "R2" in mapping
    assert "R3" in mapping
    assert "R4" in mapping
    assert "R5" in mapping
    assert "R6" in mapping

    # Regras do Firestore
    rules = generate_firestore_rules()
    assert "service cloud.firestore" in rules
    assert "match /bounties/{bountyId}" in rules
    assert "match /transactions/{txId}" in rules

    # Configuração do Firebase
    fb_json = generate_firebase_json()
    assert "firestore" in fb_json
    assert "hosting" in fb_json

    # Salva artefatos
    rules_p, json_p = save_cloud_artifacts(output_dir=tmp_path)
    assert rules_p.exists()
    assert json_p.exists()
