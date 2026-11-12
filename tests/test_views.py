"""Testes unitários e de integração das Views e Componentes Flet."""
import os
import tempfile
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
from app.views.mission_view import MissionView
from app.views.profile_view import ProfileView
from app.views.reward_view import RewardView
from app.views.route_view import RouteView
from app.views.splash_view import SplashView


@pytest.fixture
def test_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path, force_reset=True)
    yield path
    if os.path.exists(path):
        try:
            os.unlink(path)
        except (PermissionError, OSError):
            pass


def test_splash_view_instantiation():
    called = []
    view = SplashView(on_finish=lambda: called.append(True))
    control = view.build()
    assert control is not None


def test_login_view_interactions(test_db):
    auth = AuthService(test_db)
    success_user = []
    login_view = LoginView(auth, on_login_success=lambda u: success_user.append(u))
    login_root = login_view.build()

    # Modo inicial é login
    assert login_view.mode == "login"

    # Teste de login com sucesso
    login_view.email_input.value = "coletor@ecobounty.com"
    login_view.password_input.value = "123456"
    login_view.do_login(None)
    assert len(success_user) == 1
    assert success_user[0].email == "coletor@ecobounty.com"

    # Teste de login com erro (senha errada limpa campo senha)
    login_view.password_input.value = "000000"
    login_view.do_login(None)
    assert login_view.error_text.visible is True
    assert "E-mail ou senha inválidos" in login_view.error_text.value
    assert login_view.password_input.value == ""

    # Teste de alternância reativa para Cadastro
    login_view.switch_mode("register")
    assert login_view.mode == "register"
    # Verifica que os controles renderizados no root mudaram para o formulário de cadastro
    register_controls = login_root.content.content.controls
    labels = [getattr(c, "label", None) for c in register_controls]
    assert "Nome Completo" in labels
    assert "CPF" in labels
    assert "Telefone" in labels

    # Retorna para login
    login_view.switch_mode("login")
    assert login_view.mode == "login"


def test_home_view_and_filters(test_db):
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

    home_root = home.build()
    assert home_root is not None

    # Inicialmente está na aba Lista e filtro Todos (3 cards)
    col = home_root.content
    main_area = col.controls[3]
    assert isinstance(main_area.content, ft.ListView)
    assert len(main_area.content.controls) == 3

    # Alterna reativamente para Mapa
    home.set_tab("map")
    assert home.current_tab == "map"
    col = home_root.content
    main_area = col.controls[3]
    assert isinstance(main_area.content, EcoMapWidget)

    # Alterna de volta para Lista
    home.set_tab("list")
    assert home.current_tab == "list"
    main_area = home_root.content.controls[3]
    assert isinstance(main_area.content, ft.ListView)

    # Filtro "plastico" (deve filtrar para 1 card de Plástico)
    home.set_filter("plastico")
    assert home.current_filter == "plastico"
    main_area = home_root.content.controls[3]
    assert len(main_area.content.controls) == 1

    # Filtro "valiosos" (ordem decrescente de valor: R$ 60,00 primeiro)
    home.set_filter("valiosos")
    assert home.current_filter == "valiosos"
    main_area = home_root.content.controls[3]
    assert len(main_area.content.controls) == 3


def test_mission_view_rendering_and_lock(test_db):
    auth = AuthService(test_db)
    bounty_service = BountyService(test_db)
    _, user1, _ = auth.login("coletor@ecobounty.com", "123456")

    # Cadastra segundo coletor
    auth.register("Outro Coletor", "outro@ecobounty.com", "999.888.777-66", "(82) 98888-9999", "Eco@2026", "Eco@2026", True)
    _, user2, _ = auth.login("outro@ecobounty.com", "Eco@2026")

    bounty = bounty_service.get_bounties("todos")[0]

    # Aceite com sucesso pelo user1
    started = []
    view1 = MissionView(
        bounty=bounty,
        user=user1,
        bounty_service=bounty_service,
        on_back=lambda: None,
        on_start_mission=lambda b: started.append(b),
    )
    view1.build()
    view1.handle_accept(None)
    assert len(started) == 1
    assert started[0].id == bounty.id

    # user2 tenta aceitar a mesma missão já em andamento por outro coletor
    locked_bounty = bounty_service.get_bounty_by_id(bounty.id)
    view2 = MissionView(
        bounty=locked_bounty,
        user=user2,
        bounty_service=bounty_service,
        on_back=lambda: None,
        on_start_mission=lambda b: None,
    )
    root2 = view2.build()
    view2.handle_accept(None)
    assert view2.error_message == "Missão indisponível – já aceita por outro coletor"
    # Verifica que o erro foi renderizado reativamente
    body_col = root2.content.controls[1].content
    rendered_texts = [c.value for c in body_col.controls if isinstance(c, ft.Text)]
    assert any("Missão indisponível" in t for t in rendered_texts)


def test_route_view_proximity_check(test_db):
    auth = AuthService(test_db)
    bounty_service = BountyService(test_db)
    _, user, _ = auth.login("coletor@ecobounty.com", "123456")
    bounty = bounty_service.get_bounties("todos")[0]

    triggered = []
    view = RouteView(
        bounty=bounty,
        user=user,
        phase=1,
        bounty_service=bounty_service,
        on_back=lambda: None,
        on_trigger_camera=lambda p: triggered.append(p),
    )
    root = view.build()

    # 1. Simula usuário distante (~330m em -9.665, -35.730 conforme UC07 FE2)
    view.set_gps_mode("distante")
    view.handle_arrive_button(None)
    assert triggered == []  # Não deve abrir a câmera!
    assert view.error_text.visible is True
    assert "Você ainda não está no local da missão" in view.error_text.value

    # 2. Simula usuário no local (0m)
    view.set_gps_mode("local")
    view.handle_arrive_button(None)
    assert triggered == [1]  # Agora sim abre a câmera da Fase 1!


def test_camera_view_shutter_debounce_and_modes(test_db):
    auth = AuthService(test_db)
    bounty_service = BountyService(test_db)
    _, user, _ = auth.login("coletor@ecobounty.com", "123456")
    bounty = bounty_service.get_bounties("todos")[0]

    cam = CameraView(
        mode="phase1",
        user=user,
        bounty_service=bounty_service,
        bounty=bounty,
        on_cancel=lambda: None,
    )
    root = cam.build()
    assert cam.is_processing is False

    # Dispara obturador
    cam.handle_shutter_click(None)
    assert cam.is_processing is True

    # Verifica debounce: segundo clique imediato não lança outro processamento
    cam.handle_shutter_click(None)
    assert cam.is_processing is True

    # Aguarda término da thread para limpeza graciosa do banco temporário
    if hasattr(cam, "current_thread"):
        cam.current_thread.join(timeout=1.5)


def test_reward_view_rendering():
    reward = RewardView(
        title="Área Limpa!",
        subtitle="Siga para a destinação homologada.",
        amount=10.00,
        percentage_label="50% do total (Adiantamento)",
        button_label="Ir para Destino",
    )
    control = reward.build()
    assert control is not None


def test_profile_view_rendering(test_db):
    auth = AuthService(test_db)
    wallet_service = WalletService(test_db)
    _, user, _ = auth.login("coletor@ecobounty.com", "123456")

    profile = ProfileView(
        user=user,
        auth_service=auth,
        wallet_service=wallet_service,
        on_back=lambda: None,
        on_logout=lambda: None,
    )
    control = profile.build()
    assert control is not None


def test_map_widget_reactive_zoom_and_selection(test_db):
    bounty_service = BountyService(test_db)
    bounties = bounty_service.get_bounties("todos")

    selected = []
    map_widget = EcoMapWidget(
        bounties=bounties,
        selected_bounty=bounties[0],
        on_select_bounty=lambda b: selected.append(b),
        width=380,
        height=420,
    )
    root = map_widget.build()

    # Zoom
    initial_zoom = map_widget.zoom
    map_widget.change_zoom(0.2)
    assert map_widget.zoom == initial_zoom + 0.2

    # Seleção de outro marcador
    map_widget.select_bounty(bounties[1])
    assert map_widget.selected_bounty.id == bounties[1].id
    assert len(selected) == 1

    # Floating popup card reflete o bounty 2
    stack = root.content
    popup_card = stack.controls[-2]
    title_text = popup_card.content.controls[0].controls[0].value
    assert title_text == bounties[1].title

    # Teste do novo método drag e manipulador de arrasto (drag to pan)
    initial_pan_x = map_widget.pan_x
    initial_pan_y = map_widget.pan_y
    map_widget.drag(15.0, -10.0)
    assert map_widget.pan_x == initial_pan_x + 15.0
    assert map_widget.pan_y == initial_pan_y - 10.0

    # Teste via evento ft.DragUpdateEvent no GestureDetector
    class MockDragEvent:
        delta_x = 5.0
        delta_y = 8.0

    map_widget.handle_pan_update(MockDragEvent())
    assert map_widget.pan_x == initial_pan_x + 20.0
    assert map_widget.pan_y == initial_pan_y - 2.0
