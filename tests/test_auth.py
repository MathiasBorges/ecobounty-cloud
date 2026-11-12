"""Testes unitários de autenticação e cadastro de coletor (UC01, UC02)."""
import os
import tempfile
import pytest

from app.database.connection import init_db
from app.services.auth_service import AuthService


@pytest.fixture
def test_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path, force_reset=True)
    yield path
    if os.path.exists(path):
        os.unlink(path)


def test_login_success(test_db):
    auth = AuthService(test_db)
    success, user, msg = auth.login("coletor@ecobounty.com", "123456")
    assert success is True
    assert user is not None
    assert user.name == "Coletor Ativo"
    assert user.balance == 45.00


def test_login_wrong_password(test_db):
    auth = AuthService(test_db)
    success, user, msg = auth.login("coletor@ecobounty.com", "000000")
    assert success is False
    assert user is None
    assert msg == "E-mail ou senha inválidos"


def test_login_invalid_email_format(test_db):
    auth = AuthService(test_db)
    success, user, msg = auth.login("coletor.ecobounty.com", "123456")
    assert success is False
    assert user is None
    assert msg == "Informe um e-mail válido"


def test_login_empty_fields(test_db):
    auth = AuthService(test_db)
    success, user, msg = auth.login("", "")
    assert success is False
    assert msg == "Preencha e-mail e senha"


def test_register_success(test_db):
    auth = AuthService(test_db)
    success, user, msg = auth.register(
        name="Maria Silva",
        email="maria.silva@email.com",
        cpf="529.982.247-25",
        phone="(82) 98888-7777",
        password="Eco@2026Password",
        confirm_password="Eco@2026Password",
        terms_accepted=True,
    )
    assert success is True
    assert user is not None
    assert user.balance == 0.0
    assert user.email == "maria.silva@email.com"


def test_register_duplicate_email(test_db):
    auth = AuthService(test_db)
    success, user, msg = auth.register(
        name="Coletor Teste",
        email="coletor@ecobounty.com",
        cpf="111.444.777-35",
        phone="(82) 99999-0000",
        password="Eco@2026Password",
        confirm_password="Eco@2026Password",
        terms_accepted=True,
    )
    assert success is False
    assert user is None
    assert msg == "E-mail já cadastrado"


def test_register_passwords_mismatch(test_db):
    auth = AuthService(test_db)
    success, user, msg = auth.register(
        name="João Lima",
        email="joao.lima@email.com",
        cpf="390.533.447-05",
        phone="(82) 98111-2222",
        password="Eco@2026Password",
        confirm_password="Eco@2025Wrong",
        terms_accepted=True,
    )
    assert success is False
    assert msg == "As senhas não conferem"


def test_register_weak_password(test_db):
    auth = AuthService(test_db)
    success, user, msg = auth.register(
        name="Ana Souza",
        email="ana.souza@email.com",
        cpf="248.438.034-80",
        phone="(82) 98333-4444",
        password="123",
        confirm_password="123",
        terms_accepted=True,
    )
    assert success is False
    assert "A senha deve ter no mínimo 8 caracteres" in msg


def test_register_terms_rejected(test_db):
    auth = AuthService(test_db)
    success, user, msg = auth.register(
        name="Carlos",
        email="carlos@email.com",
        cpf="123.456.789-00",
        phone="(82) 90000-0000",
        password="Eco@2026Password",
        confirm_password="Eco@2026Password",
        terms_accepted=False,
    )
    assert success is False
    assert "LGPD" in msg


def test_unique_admin_users_and_all_profiles(test_db):
    auth = AuthService(test_db)

    # 1. Valida os 3 únicos Administradores Oficiais
    admin_emails = [
        "mathiasbm377@gmail.com",
        "gabrielholallan09@gmail.com",
        "kauelucasbarbosa979@gmail.com",
    ]
    for email in admin_emails:
        ok, user, msg = auth.login(email, "123456")
        assert ok is True, f"Falha ao logar com {email}"
        assert user.is_admin() is True
        assert user.role == "ADMIN"
        assert "Administrador" in user.level_title

    # 2. Valida cada um dos demais perfis do ecossistema
    profile_cases = [
        ("coletor@ecobounty.com", "COLETOR", "Coletor Ativo", False),
        ("cidadao@ecobounty.com", "CIDADAO", "Maria Silva (Cidadã)", False),
        ("ecoponto@ecobounty.com", "ECOPONTO", "Ecoponto ALURB / Cooplum", False),
        ("patrocinador@ecobounty.com", "PATROCINADOR", "Maceió Sustentável ESG", False),
    ]
    for email, role, expected_name, is_admin in profile_cases:
        ok, user, msg = auth.login(email, "123456")
        assert ok is True, f"Falha ao logar com {email}"
        assert user.role == role
        assert user.name == expected_name
        assert user.is_admin() is is_admin
        assert user.password_hash == "123456"

