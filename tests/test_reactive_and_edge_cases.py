"""Testes de estresse de casos de borda e reatividade (UC01 a UC11)."""
import os
import tempfile
import time
import pytest
import flet as ft

from app.database.connection import init_db
from app.services.auth_service import AuthService
from app.services.bounty_service import BountyService
from app.services.wallet_service import WalletService
from app.views.camera_view import CameraView
from app.views.components.map_widget import EcoMapWidget
from app.views.home_view import HomeView
from app.views.login_view import LoginView
from app.views.route_view import RouteView


@pytest.fixture
def test_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path, force_reset=True)
    yield path
    if os.path.exists(path):
        os.unlink(path)


def test_camera_phase1_ai_rejection_edge_case(test_db):
    """UC08 FE2: IA reprova a limpeza quando resíduo ainda está presente."""
    auth = AuthService(test_db)
    bounty_service = BountyService(test_db)
    _, user, _ = auth.login("coletor@ecobounty.com", "123456")
    bounty = bounty_service.get_bounties("todos")[0]

    success_called = []
    cam = CameraView(
        mode="phase1",
        user=user,
        bounty_service=bounty_service,
        bounty=bounty,
        on_success_phase1=lambda val: success_called.append(val),
    )
    root = cam.build()

    # Simula resíduo visível / reprovação pela IA
    cam.set_phase1_simulation(True)
    assert cam.simulate_phase1_failure is True

    cam.handle_shutter_click(None)
    # Aguarda a thread de inferência
    time.sleep(1.8)

    assert len(success_called) == 0
    assert cam.is_processing is False
    assert cam.error_text.visible is True
    assert "Limpeza não validada" in cam.error_text.value


def test_camera_phase2_divergent_qrcode_edge_case(test_db):
    """UC09 FE1: QR Code não corresponde ao destino homologado."""
    auth = AuthService(test_db)
    bounty_service = BountyService(test_db)
    _, user, _ = auth.login("coletor@ecobounty.com", "123456")
    bounty = bounty_service.get_bounties("todos")[0]

    success_called = []
    cam = CameraView(
        mode="phase2",
        user=user,
        bounty_service=bounty_service,
        bounty=bounty,
        on_success_phase2=lambda val: success_called.append(val),
    )
    root = cam.build()

    # Define QR Code divergente
    cam.set_test_qr("ECOPONTO-DIVERGENTE-999")
    cam.handle_shutter_click(None)
    time.sleep(1.8)

    assert len(success_called) == 0
    assert cam.is_processing is False
    assert cam.error_text.visible is True
    assert "Destino incorreto" in cam.error_text.value


def test_camera_denuncia_empty_waste_edge_case(test_db):
    """UC10 FE1: IA não identifica resíduo na foto de denúncia."""
    auth = AuthService(test_db)
    bounty_service = BountyService(test_db)
    _, user, _ = auth.login("coletor@ecobounty.com", "123456")

    success_called = []
    cam = CameraView(
        mode="denuncia",
        user=user,
        bounty_service=bounty_service,
        on_success_denuncia=lambda b: success_called.append(b),
    )
    root = cam.build()

    # Simula sem resíduo
    cam.set_denuncia_simulation("empty")
    cam.handle_shutter_click(None)
    time.sleep(1.8)

    assert len(success_called) == 0
    assert cam.is_processing is False
    assert cam.error_text.visible is True
    assert "Nenhum resíduo identificado na imagem" in cam.error_text.value


def test_camera_denuncia_duplicate_edge_case(test_db):
    """UC10 FE2: Denúncia duplicada em raio inferior a 20m."""
    auth = AuthService(test_db)
    bounty_service = BountyService(test_db)
    _, user, _ = auth.login("coletor@ecobounty.com", "123456")

    success_called = []
    cam = CameraView(
        mode="denuncia",
        user=user,
        bounty_service=bounty_service,
        on_success_denuncia=lambda b: success_called.append(b),
    )
    root = cam.build()

    # Simula denúncia duplicada
    cam.set_denuncia_simulation("duplicate")
    cam.handle_shutter_click(None)
    time.sleep(1.8)

    assert len(success_called) == 0
    assert cam.is_processing is False
    assert cam.error_text.visible is True
    assert "Já existe uma missão aberta para este local" in cam.error_text.value


def test_route_view_gps_simulation_switching(test_db):
    """UC07 FE2: Alternância de simulação GPS e bloqueio fora do raio."""
    auth = AuthService(test_db)
    bounty_service = BountyService(test_db)
    _, user, _ = auth.login("coletor@ecobounty.com", "123456")
    bounty = bounty_service.get_bounties("todos")[0]

    triggered = []
    route = RouteView(
        bounty=bounty,
        user=user,
        phase=1,
        bounty_service=bounty_service,
        on_back=lambda: None,
        on_trigger_camera=lambda p: triggered.append(p),
    )
    root = route.build()

    # 1. Distante -> Bloqueia
    route.set_gps_mode("distante")
    route.handle_arrive_button(None)
    assert triggered == []
    assert route.error_text.visible is True
    assert "330" in route.error_text.value or "Você ainda não está no local" in route.error_text.value

    # 2. No Local -> Libera
    route.set_gps_mode("local")
    route.handle_arrive_button(None)
    assert triggered == [1]


def test_map_widget_offline_and_online_toggle(test_db):
    """UC05 FE1: Mapa offline exibe mensagem amigável sem travar."""
    bounty_service = BountyService(test_db)
    bounties = bounty_service.get_bounties("todos")

    widget = EcoMapWidget(bounties=bounties, width=380, height=420)
    root = widget.build()

    # Alterna para offline
    widget.set_offline(True)
    assert widget.simulated_offline is True
    col = root.content.content
    texts = [c.value for c in col.controls if hasattr(c, "value")]
    assert any("Não foi possível carregar o mapa" in t for t in texts)

    # Retorna para online
    widget.set_offline(False)
    assert widget.simulated_offline is False
    assert isinstance(root.content, ft.Stack)


def test_home_view_balance_reactive_refresh(test_db):
    """Garante que a atualização de saldo reflete no cabeçalho dinamicamente."""
    auth = AuthService(test_db)
    bounty_service = BountyService(test_db)
    wallet_service = WalletService(test_db)
    _, user, _ = auth.login("coletor@ecobounty.com", "123456")

    home = HomeView(
        user=user,
        bounty_service=bounty_service,
        wallet_service=wallet_service,
        on_open_mission=lambda b: None,
        on_open_profile=lambda: None,
        on_open_camera_denuncia=lambda: None,
    )
    root = home.build()

    # Saldo inicial é R$ 45,00
    header_container = root.content.controls[0]
    wallet_badge = header_container.content.controls[1]
    bal_text = wallet_badge.content.controls[1].value
    assert "45,00" in bal_text

    # Credita valor na carteira
    wallet_service.credit_advance(user.id, bounty_id=1, total_val=20.00)

    # Atualiza saldo no home
    home.refresh_user_balance()
    wallet_badge = root.content.controls[0].content.controls[1]
    updated_bal_text = wallet_badge.content.controls[1].value
    assert "55,00" in updated_bal_text
