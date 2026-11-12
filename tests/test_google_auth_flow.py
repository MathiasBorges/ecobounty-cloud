"""Testes unitários do fluxo de autenticação e onboarding Google com seleção de papéis."""
import os
import tempfile
import pytest

from app.database.connection import init_db
from app.models.user import (
    ROLE_CIDADAO,
    ROLE_COLETOR,
    ROLE_ECOPONTO,
    ROLE_PATROCINADOR,
)
from app.services.auth_service import AuthService


@pytest.fixture
def auth_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path, force_reset=True)
    yield path
    if os.path.exists(path):
        os.unlink(path)


def test_google_login_existing_user_instant_access(auth_db):
    auth = AuthService(auth_db)
    # 1. Usuário coletor existente do seed
    existing_email = "coletor@ecobounty.com"

    # Simula autenticação Google com e-mail já existente
    success, user, msg = auth.login_or_register_with_google(
        google_user_data={"email": existing_email, "name": "Coletor Ativo", "uid": "google_123"}
    )
    assert success is True
    assert user is not None
    assert user.email == existing_email
    assert user.role == ROLE_COLETOR
    assert "Conectado com sucesso via Google" in msg


def test_google_registration_with_selected_role_cidadao(auth_db):
    auth = AuthService(auth_db)
    new_google_email = "cidadao.novo@gmail.com"

    # Garante que não existe inicialmente
    assert auth.check_google_user(new_google_email) is None

    # Cadastra via Google selecionando o papel Cidadão
    success, user, msg = auth.register_google_user(
        email=new_google_email,
        name="Lucas Cidadão",
        role=ROLE_CIDADAO,
        phone="(82) 99111-2222",
        google_id="google_cidadao_uid_999",
    )
    assert success is True
    assert user is not None
    assert user.email == new_google_email
    assert user.name == "Lucas Cidadão"
    assert user.role == ROLE_CIDADAO
    assert user.is_cidadao() is True
    assert user.role_display_name() == "Cidadão"


def test_google_registration_with_selected_role_ecoponto(auth_db):
    auth = AuthService(auth_db)
    new_google_email = "cooperativa.al@gmail.com"

    success, user, msg = auth.register_google_user(
        email=new_google_email,
        name="Cooperativa Recicla Maceió",
        role=ROLE_ECOPONTO,
        phone="(82) 99333-4444",
        google_id="google_ecoponto_uid_888",
    )
    assert success is True
    assert user is not None
    assert user.role == ROLE_ECOPONTO
    assert user.is_ecoponto() is True
    assert user.role_display_name() == "Ecoponto / Cooperativa"


def test_google_registration_with_selected_role_patrocinador(auth_db):
    auth = AuthService(auth_db)
    new_google_email = "empresa.esg@gmail.com"

    success, user, msg = auth.register_google_user(
        email=new_google_email,
        name="Diretor ESG Brasil",
        role=ROLE_PATROCINADOR,
        phone="(82) 99444-5555",
        google_id="google_patrocinador_uid_777",
    )
    assert success is True
    assert user is not None
    assert user.role == ROLE_PATROCINADOR
    assert user.is_patrocinador() is True
    assert user.role_display_name() == "Patrocinador ESG"


def test_register_standard_user_with_role(auth_db):
    auth = AuthService(auth_db)
    success, user, msg = auth.register(
        name="Carlos Cidadão",
        email="carlos.cidadao@email.com",
        cpf="123.456.789-01",
        phone="(82) 99777-6666",
        password="Eco@2026Password",
        confirm_password="Eco@2026Password",
        terms_accepted=True,
        role=ROLE_CIDADAO,
    )
    assert success is True
    assert user is not None
    assert user.role == ROLE_CIDADAO


def test_storage_service_google_auth_queue():
    from app.services.storage_service import pop_google_auth_result, set_google_auth_result
    set_google_auth_result({"status": "success", "email": "real.google.user@gmail.com", "name": "Real User"})
    res = pop_google_auth_result()
    assert res is not None
    assert res["status"] == "success"
    assert res["email"] == "real.google.user@gmail.com"
    # Fila esvaziada após consumo
    assert pop_google_auth_result() is None


def test_login_view_google_existing_instant_and_new_onboarding(auth_db):
    from app.views.login_view import LoginView
    auth = AuthService(auth_db)
    logged_in = []

    view = LoginView(auth, on_login_success=lambda u: logged_in.append(u))
    view.build()

    # 1. Campos iniciam vazios (sem mocks ou aprovações automáticas falsas)
    assert view.google_email_field.value == ""
    assert view.google_name_field.value == ""

    # 2. Usuário existente (coletor@ecobounty.com) faz login imediato ao autenticar no Google
    view._process_verified_google_user("coletor@ecobounty.com", "Coletor Maceio")
    assert len(logged_in) == 1
    assert logged_in[0].email == "coletor@ecobounty.com"

    # 3. Usuário novo: transiciona para onboarding de seleção de papel
    view._process_verified_google_user("novo.cidadao@gmail.com", "Novo Cidadão")
    assert view.mode == "google_onboarding"
    assert view.google_email_field.value == "novo.cidadao@gmail.com"

    # Seleciona papel Patrocinador e conclui
    view.select_role(ROLE_PATROCINADOR)
    view.complete_google_onboarding()

    assert len(logged_in) == 2
    assert logged_in[1].email == "novo.cidadao@gmail.com"
    assert logged_in[1].role == ROLE_PATROCINADOR

