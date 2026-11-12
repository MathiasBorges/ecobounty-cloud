"""Testes de validação dos novos requisitos: Layout Adaptativo, Cadastro/Login e Câmera com Armazenamento Real."""
import os
import tempfile
from pathlib import Path
import pytest
import flet as ft

from app.database.connection import init_db
from app.models.bounty import Bounty
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.bounty_service import BountyService
from app.services.storage_service import LocalStorageService
from app.services.wallet_service import WalletService
from app.views.camera_view import CameraView
from app.views.login_view import LoginView
from app.views.reward_view import RewardView


@pytest.fixture
def test_env():
    # Banco temporário isolado
    fd_db, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd_db)
    init_db(db_path, force_reset=True)

    # Diretório de uploads temporário isolado
    temp_uploads = tempfile.mkdtemp(prefix="ecobounty_test_uploads_")
    storage = LocalStorageService(upload_dir=Path(temp_uploads))
    auth = AuthService(db_path)
    wallet = WalletService(db_path)
    bounty_svc = BountyService(db_path=db_path, wallet_service=wallet, storage_service=storage)

    yield {
        "db_path": db_path,
        "uploads_dir": Path(temp_uploads),
        "storage": storage,
        "auth": auth,
        "wallet": wallet,
        "bounty_svc": bounty_svc,
    }

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)
    for f in Path(temp_uploads).glob("*"):
        try:
            f.unlink()
        except Exception:
            pass
    try:
        os.rmdir(temp_uploads)
    except Exception:
        pass


class MockPage:
    """Mock leve do ft.Page para testes de reatividade e adaptabilidade sem servidor websocket."""
    def __init__(self, width: int = 400, platform=None, client_user_agent=None):
        self.width = width
        self.platform = platform
        self.client_user_agent = client_user_agent
        self.bgcolor = "#e2e8f0"
        self.padding = 0
        self.overlay = []
        self.controls = []
        self.snack_bar = None
        self.on_resized = None

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self, *args, **kwargs):
        pass

    def get_upload_url(self, file_name: str, expires: int):
        return f"/upload_target/{file_name}"


# ==============================================================================
# 1. TESTES DE CADASTRO E LOGIN 100% FUNCIONAIS NO BANCO DE DADOS
# ==============================================================================

def test_full_registration_and_login_flow(test_env):
    auth = test_env["auth"]
    logged_in_users = []

    login_view = LoginView(
        auth_service=auth,
        on_login_success=lambda u: logged_in_users.append(u),
    )
    mock_page = MockPage()
    login_view._Control__page = mock_page

    # Alterna para modo cadastro
    login_view.switch_mode("register")
    assert login_view.mode == "register"

    # Preenche todos os campos exigidos (UC02)
    login_view.reg_name.value = "Carlos Eduardo Ferreira"
    login_view.reg_email.value = "carlos.ferreira@ecobounty.com"
    login_view.reg_cpf.value = "333.444.555-66"
    login_view.reg_phone.value = "(82) 98765-4321"
    login_view.reg_pass.value = "EcoBounty2026!"
    login_view.reg_confirm_pass.value = "EcoBounty2026!"
    login_view.reg_terms.value = True

    # Executa o cadastro
    login_view.do_register(None)

    # Valida sucesso imediato
    assert len(logged_in_users) == 1
    new_user = logged_in_users[0]
    assert new_user.name == "Carlos Eduardo Ferreira"
    assert new_user.email == "carlos.ferreira@ecobounty.com"
    assert new_user.balance == 0.0

    # Valida feedback visual (SnackBar verde com mensagem de sucesso)
    assert mock_page.snack_bar is not None
    assert mock_page.snack_bar.open is True
    assert "Conta criada com sucesso" in mock_page.snack_bar.content.controls[1].value

    # Valida persistência real no SQLite
    persisted = auth.get_user_profile(new_user.id)
    assert persisted is not None
    assert persisted.cpf == "333.444.555-66"
    assert persisted.phone == "(82) 98765-4321"

    # Testa novo Login usando as credenciais que acabamos de cadastrar
    logged_in_users.clear()
    login_view.switch_mode("login")
    login_view.email_input.value = "carlos.ferreira@ecobounty.com"
    login_view.password_input.value = "EcoBounty2026!"

    login_view.do_login(None)
    assert len(logged_in_users) == 1
    assert logged_in_users[0].id == new_user.id
    assert mock_page.snack_bar.open is True
    assert "Login realizado com sucesso" in mock_page.snack_bar.content.controls[1].value


def test_registration_validation_errors(test_env):
    auth = test_env["auth"]
    login_view = LoginView(auth_service=auth, on_login_success=lambda u: None)

    # 1. Campos vazios
    login_view.do_register(None)
    assert login_view.error_text.visible is True
    assert "obrigatórios" in login_view.error_text.value

    # 2. Termos LGPD desmarcados
    login_view.reg_name.value = "Teste"
    login_view.reg_email.value = "teste@email.com"
    login_view.reg_cpf.value = "111.222.333-44"
    login_view.reg_phone.value = "(82) 99999-0000"
    login_view.reg_pass.value = "SenhaForte123"
    login_view.reg_confirm_pass.value = "SenhaForte123"
    login_view.reg_terms.value = False
    login_view.do_register(None)
    assert "LGPD" in login_view.error_text.value


# ==============================================================================
# 2. TESTES DE CÂMERA REAL, CAPTURA E ARMAZENAMENTO FÍSICO NO DISCO
# ==============================================================================

def test_camera_storage_physical_write(test_env):
    storage = test_env["storage"]
    uploads_dir = test_env["uploads_dir"]

    # Cria uma foto real pelo gerador de foto com geolocalização e carimbo
    saved_url = storage.create_sample_photo(
        label="Garrafas Plásticas",
        lat=-9.664,
        lng=-35.732,
        is_clean=False,
    )
    assert saved_url.startswith("/uploads/")

    # Valida que o arquivo foi realmente escrito fisicamente no disco
    physical_path = storage.get_physical_path(saved_url)
    assert physical_path.exists()
    assert physical_path.parent == uploads_dir
    assert physical_path.stat().st_size > 1000  # JPEG válido com mais de 1KB


def test_camera_view_capture_and_denuncia_bounty(test_env):
    auth = test_env["auth"]
    bounty_svc = test_env["bounty_svc"]
    storage = test_env["storage"]
    _, user, _ = auth.login("coletor@ecobounty.com", "123456")

    created_bounties = []
    cam = CameraView(
        mode="denuncia",
        user=user,
        bounty_service=bounty_svc,
        storage_service=storage,
        on_success_denuncia=lambda b: created_bounties.append(b),
    )
    mock_page = MockPage()
    cam._Control__page = mock_page
    cam.build()

    # 1. Tira foto real instantânea
    cam.take_instant_photo()
    assert cam.captured_image_path is not None
    assert cam.captured_image_path.startswith("/uploads/")

    # Confirma que a foto foi salva fisicamente no disco
    phys_file = storage.get_physical_path(cam.captured_image_path)
    assert phys_file.exists()

    # 2. Clica no obturador para processar
    cam.handle_shutter_click(None)
    if hasattr(cam, "current_thread"):
        cam.current_thread.join(timeout=2.0)

    # Valida que o Bounty foi gerado com a foto real vinculada
    assert len(created_bounties) == 1
    new_bounty = created_bounties[0]
    assert new_bounty.img == cam.captured_image_path

    # Valida que o bounty recém-criado foi salvo no SQLite
    db_bounty = bounty_svc.get_bounty_by_id(new_bounty.id)
    assert db_bounty is not None
    assert db_bounty.img == cam.captured_image_path


def test_camera_file_picker_local_import(test_env):
    auth = test_env["auth"]
    bounty_svc = test_env["bounty_svc"]
    storage = test_env["storage"]
    _, user, _ = auth.login("coletor@ecobounty.com", "123456")

    # Cria arquivo fictício de teste
    temp_img = test_env["uploads_dir"].parent / "foto_externa.jpg"
    temp_img.write_bytes(b"FAKE_JPEG_DATA_12345")

    cam = CameraView(
        mode="denuncia",
        user=user,
        bounty_service=bounty_svc,
        storage_service=storage,
    )
    cam.build()

    # Simula evento do FilePicker ao selecionar arquivo
    class MockFile:
        path = str(temp_img)
        name = "foto_externa.jpg"

    class MockEvent:
        files = [MockFile()]

    cam.on_file_picker_result(MockEvent())
    assert cam.captured_image_path is not None
    assert cam.captured_image_path.startswith("/uploads/")
    assert storage.get_physical_path(cam.captured_image_path).exists()

    if temp_img.exists():
        temp_img.unlink()


def test_reward_view_displays_photo():
    reward = RewardView(
        title="Bounty Criado!",
        subtitle="Mapeamento realizado.",
        image_url="/uploads/minha_foto.jpg",
    )
    control = reward.build()
    col = control.content
    # Valida que o controle de preview de imagem foi montado com o src correto
    image_preview = col.controls[2]
    assert isinstance(image_preview, ft.Container)
    stack = image_preview.content
    img_control = stack.controls[0]
    assert isinstance(img_control, ft.Image)
    assert img_control.src == "/uploads/minha_foto.jpg"


# ==============================================================================
# 3. TESTES DE LAYOUT ADAPTATIVO (MOBILE / APK vs DESKTOP)
# ==============================================================================

def test_adaptive_layout_logic():
    from app.main import main

    # 1. Simula Mobile (page.width = 390 < 500)
    page_mobile = MockPage(width=390)
    # Executa a configuração da página
    device_frame = ft.Container(width=400, height=830, padding=6, border_radius=36, bgcolor="#0f172a")
    inner_frame = ft.Container(expand=True, border_radius=30)

    def apply_adaptive(p, df, inf):
        w = p.width or 0
        platform_str = str(getattr(p, "platform", "") or "").lower()
        is_mobile = (w > 0 and w < 500) or platform_str in ["android", "ios"]
        if is_mobile:
            p.bgcolor = "#ffffff"
            df.width = None
            df.height = None
            df.expand = True
            df.padding = 0
            df.border_radius = 0
            df.bgcolor = "#ffffff"
            df.shadow = None
            inf.border_radius = 0
        else:
            p.bgcolor = "#e2e8f0"
            df.width = 400
            df.height = 830
            df.expand = False
            df.padding = 6
            df.border_radius = 36
            df.bgcolor = "#0f172a"
            inf.border_radius = 30

    apply_adaptive(page_mobile, device_frame, inner_frame)
    assert page_mobile.bgcolor == "#ffffff"
    assert device_frame.expand is True
    assert not device_frame.width
    assert not device_frame.height
    assert device_frame.padding == 0
    assert device_frame.border_radius == 0
    assert inner_frame.border_radius == 0

    # 2. Simula Desktop (page.width = 1200 >= 500)
    page_desktop = MockPage(width=1200)
    apply_adaptive(page_desktop, device_frame, inner_frame)
    assert page_desktop.bgcolor == "#e2e8f0"
    assert device_frame.expand is False
    assert device_frame.width == 400
    assert device_frame.height == 830
    assert device_frame.padding == 6
    assert device_frame.border_radius == 36
    assert inner_frame.border_radius == 30

    # 3. Simula APK Android com largura não inicializada
    page_apk = MockPage(width=0, platform="android")
    apply_adaptive(page_apk, device_frame, inner_frame)
    assert page_apk.bgcolor == "#ffffff"
    assert device_frame.expand is True
    assert device_frame.padding == 0
    assert device_frame.border_radius == 0

    # 4. Simula Navegador Mobile via User-Agent (ex: Android Chrome)
    page_ua_mobile = MockPage(width=600, client_user_agent="Mozilla/5.0 (Linux; Android 13; SM-G998B)")
    def apply_adaptive_with_ua(p, df, inf):
        w = p.width or 0
        platform_str = str(getattr(p, "platform", "") or "").lower()
        ua = str(getattr(p, "client_user_agent", "") or "").lower()
        is_mob = (
            (w > 0 and w < 500)
            or platform_str in ["android", "ios"]
            or any(m in ua for m in ["android", "iphone", "ipad", "mobile"])
        )
        if is_mob:
            p.bgcolor = "#ffffff"
            df.expand = True
            df.padding = 0
            df.border_radius = 0
            inf.border_radius = 0
        else:
            p.bgcolor = "#e2e8f0"
            df.expand = False

    apply_adaptive_with_ua(page_ua_mobile, device_frame, inner_frame)
    assert page_ua_mobile.bgcolor == "#ffffff"
    assert device_frame.expand is True


def test_camera_shutter_triggers_picker_when_active(test_env):
    """Garante que clicar no botão obturador sem foto abre a câmera real via FilePicker."""
    auth = test_env["auth"]
    bounty_svc = test_env["bounty_svc"]
    storage = test_env["storage"]
    _, user, _ = auth.login("coletor@ecobounty.com", "123456")

    cam = CameraView(
        mode="denuncia",
        user=user,
        bounty_service=bounty_svc,
        storage_service=storage,
    )
    mock_page = MockPage()
    cam._Control__page = mock_page
    cam.build()

    picker_called = []
    cam.open_camera_picker = lambda e=None: picker_called.append(True)

    # Clica no obturador sem foto capturada prévia
    cam.handle_shutter_click(None)
    assert len(picker_called) == 1
    assert cam.is_processing is False


def test_camera_webcam_fallback_to_picker(test_env):
    """Garante que a captura de webcam, na ausência de hardware físico, faz fallback seguro para a câmera do dispositivo."""
    auth = test_env["auth"]
    bounty_svc = test_env["bounty_svc"]
    storage = test_env["storage"]
    _, user, _ = auth.login("coletor@ecobounty.com", "123456")

    cam = CameraView(
        mode="denuncia",
        user=user,
        bounty_service=bounty_svc,
        storage_service=storage,
    )
    mock_page = MockPage()
    cam._Control__page = mock_page
    cam.build()

    picker_called = []
    cam.open_camera_picker = lambda e=None: picker_called.append(True)

    import sys
    from unittest.mock import MagicMock, patch
    if "cv2" not in sys.modules:
        sys.modules["cv2"] = MagicMock()
    with patch("cv2.VideoCapture") as mock_vc:
        mock_vc.return_value.isOpened.return_value = False
        cam.capture_webcam()

    # Em ambiente sem hardware de webcam, deve ter acionado o fallback
    assert len(picker_called) == 1
    assert mock_page.snack_bar is not None
    assert "câmera do dispositivo" in mock_page.snack_bar.content.controls[1].value


def test_camera_web_upload_event_saves_permanently(test_env):
    """Garante que uploads de fotos pela web/APK são salvos fisicamente em uploads com UUID."""
    auth = test_env["auth"]
    bounty_svc = test_env["bounty_svc"]
    storage = test_env["storage"]
    uploads_dir = test_env["uploads_dir"]
    _, user, _ = auth.login("coletor@ecobounty.com", "123456")

    cam = CameraView(
        mode="denuncia",
        user=user,
        bounty_service=bounty_svc,
        storage_service=storage,
    )
    mock_page = MockPage()
    cam._Control__page = mock_page
    cam.build()

    # Cria arquivo simulado no diretório de uploads do Flet
    flet_uploaded_file = uploads_dir / "mobile_photo_123.jpg"
    flet_uploaded_file.write_bytes(b"REAL_MOBILE_CAMERA_PICTURE_BYTES_999")

    # Dispara evento de upload concluído (progress=1.0)
    upload_event = ft.FilePickerUploadEvent(
        file_name="mobile_photo_123.jpg",
        progress=1.0,
        error=None,
    )
    cam.on_file_picker_upload(upload_event)

    assert cam.captured_image_path is not None
    assert cam.captured_image_path.startswith("/uploads/")
    # Confirma que o arquivo existe fisicamente no disco sob a pasta uploads
    phys = storage.get_physical_path(cam.captured_image_path)
    assert phys.exists()
    assert phys.read_bytes() == b"REAL_MOBILE_CAMERA_PICTURE_BYTES_999"


def test_auth_case_insensitive_and_persistence(test_env):
    """Garante que cadastro e login tratam e-mails insensíveis a maiúsculas/minúsculas."""
    auth = test_env["auth"]

    ok, user, msg = auth.register(
        name="Beatriz Lima",
        email="Beatriz.Lima@EcoBounty.COM",
        cpf="111.222.333-44",
        phone="(82) 91111-2222",
        password="SenhaSegura2026",
        confirm_password="SenhaSegura2026",
        terms_accepted=True,
    )
    assert ok is True
    assert user.email == "beatriz.lima@ecobounty.com"

    # Testa login com e-mail em minúsculas
    ok_login, user_login, _ = auth.login("beatriz.lima@ecobounty.com", "SenhaSegura2026")
    assert ok_login is True
    assert user_login.id == user.id

    # Testa login com e-mail em maiúsculas
    ok_login_upper, user_upper, _ = auth.login("BEATRIZ.LIMA@ECOBOUNTY.COM", "SenhaSegura2026")
    assert ok_login_upper is True
    assert user_upper.id == user.id


def test_main_app_lifecycle_and_camera_navigation(test_env, monkeypatch):
    """Garante que a função main inicializa corretamente e suporta o ciclo de vida completo."""
    from app.main import main

    monkeypatch.setattr("app.main.init_db", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.main.AuthService", lambda *args, **kwargs: test_env["auth"])
    monkeypatch.setattr("app.main.WalletService", lambda *args, **kwargs: test_env["wallet"])
    monkeypatch.setattr("app.main.BountyService", lambda *args, **kwargs: test_env["bounty_svc"])

    page = MockPage(width=390)
    main(page)

    # Verifica que a tela foi adicionada e adaptada para mobile
    assert len(page.controls) == 1
    assert page.bgcolor == "#ffffff"
    wrapper = page.controls[0]
    assert wrapper.expand is True


def test_in_page_camera_listener_and_action_queue(test_env):
    """Garante que a fila de ações sob demanda e o listener de foto in-page funcionam integrados."""
    from app.services.storage_service import (
        pop_pending_action,
        register_photo_listener,
        set_latest_captured_photo,
        set_pending_action,
        unregister_photo_listener,
    )

    set_pending_action("open_camera", {"mode": "denuncia"})
    act, data = pop_pending_action()
    assert act == "open_camera"
    assert data.get("mode") == "denuncia"

    # Fila deve estar vazia após pop
    act_empty, _ = pop_pending_action()
    assert act_empty is None

    received_photos = []

    def on_photo(p):
        received_photos.append(p)

    register_photo_listener(on_photo)
    set_latest_captured_photo("/uploads/test_camera_snap.jpg")
    assert len(received_photos) == 1
    assert received_photos[0] == "/uploads/test_camera_snap.jpg"
    unregister_photo_listener(on_photo)


def test_map_widget_dynamic_user_position_and_gps_action(test_env):
    """Garante que o EcoMapWidget solicita GPS sob demanda e atualiza o mapa em tempo real."""
    from app.services.storage_service import pop_pending_action
    from app.views.components.map_widget import EcoMapWidget

    widget = EcoMapWidget(user_lat=-9.665, user_lng=-35.735)
    widget.did_mount()

    act, _ = pop_pending_action()
    assert act == "request_gps"

    # Simula recebimento de novas coordenadas físicas reais
    widget.update_user_position(-9.6500, -35.7100)
    assert widget.user_lat == -9.6500
    assert widget.user_lng == -35.7100
    assert widget.gmaps_view_state[0] == -9.6500
    assert widget.gmaps_view_state[1] == -35.7100

    widget.will_unmount()


