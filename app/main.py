"""Ponto de Entrada Principal do Aplicativo EcoBounty (Web + APK).

Inicia o servidor Flet local ou nativo Android com navegação entre views,
Material 3 Design e persistência local-first (SQLite).
"""
import os
import sys
import warnings
from pathlib import Path
from typing import Optional

# Suprime aviso informativo de fim de suporte futuro de versão do Python pela biblioteca Google
warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")

import flet as ft

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import ASSETS_DIR, PROJECT_DIR, SERVER_HOST, SERVER_PORT, UPLOADS_DIR

def _ensure_flet_web_runtime(target_web_dir: Path) -> None:
    """Sincroniza os binários do runtime Flutter Web (flutter.js, main.dart.js, manifest.json, assets, icons)
    da instalação do pacote Flet para `web/`, preservando o `web/index.html` customizado do EcoBounty."""
    try:
        import json
        import shutil
        flet_pkg_web = Path(ft.__file__).resolve().parent / "web"
        if not flet_pkg_web.exists() or not target_web_dir.exists():
            return
        for item in flet_pkg_web.iterdir():
            if item.name in ("index.html", "manifest.json"):
                continue
            dest = target_web_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            elif not dest.exists():
                shutil.copy2(item, dest)

        # Gera manifest.json oficial do EcoBounty (100% compatível com PWABuilder TWA / Android APK)
        eco_manifest = {
            "id": "/",
            "name": "EcoBounty - Economia Circular Gamificada",
            "short_name": "EcoBounty",
            "description": "Plataforma de Economia Circular Gamificada de Maceió - AL com Auditoria por IA e Recompensas Pix.",
            "lang": "pt-BR",
            "dir": "ltr",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "orientation": "portrait",
            "background_color": "#059669",
            "theme_color": "#059669",
            "categories": ["environment", "finance", "utilities"],
            "prefer_related_applications": False,
            "icons": [
                {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                {"src": "icons/icon-maskable-192.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable"},
                {"src": "icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
            ],
        }
        (target_web_dir / "manifest.json").write_text(
            json.dumps(eco_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


# Configura o diretório web nativo com scripts de câmera in-page e GPS
web_dir = PROJECT_DIR / "web"
if web_dir.exists():
    _ensure_flet_web_runtime(web_dir)
    os.environ["FLET_WEB_PATH"] = str(web_dir)

from app.database.connection import init_db
from app.models.bounty import Bounty
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.bounty_service import BountyService
from app.services.geo_service import get_geo_service
from app.services.storage_service import get_client_id, register_location_listener, start_upload_server
from app.services.wallet_service import WalletService
from app.views.camera_view import CameraView
from app.views.home_view import HomeView
from app.views.login_view import LoginView
from app.views.mission_view import MissionView
from app.views.profile_view import ProfileView
from app.views.reward_view import RewardView
from app.views.route_view import RouteView
from app.views.splash_view import SplashView


def main(page: ft.Page):
    # Inicializa banco de dados SQLite local com seeds
    init_db()

    # Inicia o servidor local de recebimento de fotos em tempo real da câmera
    start_upload_server()

    # Sincroniza em background com o Cloud Firestore no startup (sem bloquear o carregamento)
    try:
        import threading
        from app.services.firestore_service import get_firestore_service
        threading.Thread(target=get_firestore_service().sync_all_from_sqlite, daemon=True).start()
    except Exception:
        pass

    # Detecta a localização geográfica física real do usuário
    geo_service = get_geo_service()

    # Identificador deste dispositivo (?cid=...): isola GPS, câmera, login Google e seleção de
    # missão para que eventos de um aparelho não afetem os demais conectados ao mesmo servidor.
    cid = get_client_id(page)

    # Tenta ler parâmetros de GPS passados via URL querystring (ex: ?lat=...&lng=...)
    try:
        q_lat = page.query.get("lat")
        q_lng = page.query.get("lng")
        if q_lat and q_lng and not cid:
            geo_service.update_from_gps(float(q_lat), float(q_lng))
    except Exception:
        pass

    # Instancia camada de serviços desacoplada
    auth_service = AuthService()
    wallet_service = WalletService()
    bounty_service = BountyService(wallet_service=wallet_service)

    # Configurações gerais da página
    page.title = "EcoBounty - Economia Circular Gamificada"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.bgcolor = "#e2e8f0"

    # Captura parâmetros de retorno da câmera ou navegação externa se houver
    captured_from_url = None
    captured_mode_from_url = None
    initial_tab_from_url = "list"
    initial_bounty_from_url = None
    try:
        cap_q = page.query.get("captured")
        if cap_q:
            captured_from_url = f"/uploads/{cap_q}"
            captured_mode_from_url = page.query.get("mode") or "denuncia"
        q_tab = page.query.get("tab")
        if q_tab in ("list", "map"):
            initial_tab_from_url = q_tab
        q_b_id = page.query.get("bounty_id")
        if q_b_id:
            initial_bounty_from_url = bounty_service.get_bounty_by_id(int(q_b_id))
    except Exception:
        pass

    # Estado da Aplicação com Geolocalização Real
    app_state = {
        "user": None,
        "active_bounty": initial_bounty_from_url,
        "selected_bounty_on_map": initial_bounty_from_url,
        "current_phase": 1,
        "user_lat": geo_service.user_lat,
        "user_lng": geo_service.user_lng,
        "user_city": geo_service.city_label,
        "is_real_location": geo_service.is_real_location,
        "captured_photo": captured_from_url,
        "pending_camera_mode": captured_mode_from_url,
        "initial_tab": initial_tab_from_url,
    }

    # Container de conteúdo móvel
    content_area = ft.Container(expand=True)

    def on_live_location_received(lat: float, lng: float):
        app_state["user_lat"] = lat
        app_state["user_lng"] = lng
        app_state["is_real_location"] = True
        try:
            from app.services.google_maps_service import get_google_maps_service
            info = get_google_maps_service().reverse_geocode(lat, lng)
            if info and info.get("full_label"):
                app_state["user_city"] = info["full_label"]
        except Exception:
            pass
        current_view = getattr(content_area, "content", None)
        if isinstance(current_view, HomeView):
            current_view.user_lat = lat
            current_view.user_lng = lng
            current_view.is_real_location = True
            current_view.city_label = app_state["user_city"]
            if hasattr(current_view, "map_widget") and current_view.map_widget:
                current_view.map_widget.update_user_position(lat, lng)
            try:
                current_view.update()
            except Exception:
                pass
        elif isinstance(current_view, CameraView):
            current_view.user_lat = lat
            current_view.user_lng = lng
        try:
            page.update()
        except Exception:
            pass

    register_location_listener(on_live_location_received, cid=cid)

    def on_live_bounty_selected(bounty_id: int):
        b = bounty_service.get_bounty_by_id(bounty_id)
        if b:
            app_state["active_bounty"] = b
            app_state["selected_bounty_on_map"] = b
            navigate_to("mission_details")
            try:
                page.update()
            except Exception:
                pass

    from app.services.storage_service import register_bounty_listener, unregister_bounty_listener
    from app.services.storage_service import unregister_location_listener
    register_bounty_listener(on_live_bounty_selected, cid=cid)

    def on_session_disconnect(e=None):
        """Libera os ouvintes desta sessão ao fechar a aba (evita vazamento e eventos cruzados)."""
        unregister_location_listener(on_live_location_received)
        unregister_bounty_listener(on_live_bounty_selected)

    page.on_disconnect = on_session_disconnect

    def navigate_to(view_name: str, **kwargs):
        """Gerenciador central de navegação entre telas."""
        if view_name == "splash":
            view_control = SplashView(on_finish=lambda: navigate_to("login"))

        elif view_name == "login":
            def on_login(user: User):
                app_state["user"] = user
                if app_state.get("pending_camera_mode"):
                    c_mode = app_state.pop("pending_camera_mode")
                    c_img = app_state.pop("captured_photo", None)
                    navigate_to("camera", mode=c_mode, captured_image_path=c_img)
                else:
                    navigate_to("home")

            view_control = LoginView(
                auth_service=auth_service,
                on_login_success=on_login,
            )

        elif view_name == "home":
            user = app_state["user"]
            if not user:
                navigate_to("login")
                return

            refreshed_user = auth_service.get_user_profile(user.id)
            if refreshed_user:
                app_state["user"] = refreshed_user
                user = refreshed_user

            initial_tab = kwargs.get("initial_tab", app_state.get("initial_tab", "list"))
            selected_bounty = kwargs.get("selected_bounty") or app_state.get("selected_bounty_on_map")

            def on_open_mission(bounty: Bounty):
                app_state["active_bounty"] = bounty
                navigate_to("mission_details")

            def on_open_denuncia():
                navigate_to("camera", mode="denuncia", auto_open=False)

            def on_location_change(lat: float, lng: float, label: str):
                app_state["user_lat"] = lat
                app_state["user_lng"] = lng
                app_state["user_city"] = label
                app_state["is_real_location"] = True
                geo_service.update_from_gps(lat, lng, label=label)

            view_control = HomeView(
                user=user,
                bounty_service=bounty_service,
                wallet_service=wallet_service,
                on_open_mission=on_open_mission,
                on_open_profile=lambda: navigate_to("profile"),
                on_open_camera_denuncia=on_open_denuncia,
                user_lat=app_state["user_lat"],
                user_lng=app_state["user_lng"],
                city_label=app_state["user_city"],
                is_real_location=app_state["is_real_location"],
                on_location_change=on_location_change,
                initial_tab=initial_tab,
                selected_bounty=selected_bounty,
            )

        elif view_name == "mission_details":
            bounty = app_state["active_bounty"]
            user = app_state["user"]

            def on_start(b: Bounty):
                app_state["active_bounty"] = b
                app_state["current_phase"] = 1
                navigate_to("route", phase=1)

            view_control = MissionView(
                bounty=bounty,
                user=user,
                bounty_service=bounty_service,
                on_back=lambda: navigate_to("home"),
                on_start_mission=on_start,
            )

        elif view_name == "route":
            phase = kwargs.get("phase", 1)
            bounty = app_state["active_bounty"]
            user = app_state["user"]

            def on_trigger_camera(p: int):
                navigate_to("camera", mode=f"phase{p}", auto_open=False)

            view_control = RouteView(
                bounty=bounty,
                user=user,
                phase=phase,
                bounty_service=bounty_service,
                on_back=lambda: navigate_to("mission_details" if phase == 1 else "home"),
                on_trigger_camera=on_trigger_camera,
                initial_user_lat=app_state["user_lat"],
                initial_user_lng=app_state["user_lng"],
                is_real_location=app_state["is_real_location"],
            )

        elif view_name == "camera":
            mode = kwargs.get("mode", "phase1")
            bounty = app_state["active_bounty"]
            user = app_state["user"]
            auto_open = kwargs.get("auto_open", False)
            captured_image_path = kwargs.get("captured_image_path") or app_state.get("captured_photo")

            def on_success_denuncia(new_b: Optional[Bounty]):
                if new_b:
                    app_state["active_bounty"] = new_b
                    app_state["selected_bounty_on_map"] = new_b
                ai_info = None
                if new_b:
                    ai_info = {
                        "waste_type": new_b.type,
                        "title": new_b.title,
                        "dest": new_b.dest,
                        "estimated_value": new_b.val,
                        "message": f"Resíduo de {new_b.type} identificado e classificado com sucesso via IA.",
                        "provider": "IA EcoBounty (Visão)",
                    }
                navigate_to(
                    "reward",
                    title="Nova Quest Criada!",
                    subtitle=f"Missão '{new_b.title if new_b else 'Descarte Irregular'}' já está no mapa!",
                    amount=None,
                    percentage_label="Publicado no EcoBounty",
                    image_url=(new_b.img if (new_b and new_b.img) else captured_image_path),
                    ai_audit_info=ai_info,
                    button_label="Ver Quest no Mapa",
                    next_view="home_map",
                )

            def on_success_phase1(half_val: float, clean_img: Optional[str] = None):
                ai_info = {
                    "waste_type": bounty.type if bounty else "Plástico",
                    "dest": bounty.dest if bounty else "COOPLUM",
                    "estimated_value": half_val,
                    "message": "Área auditada por IA: Limpeza comprovada! Nenhum resíduo remanescente detectado.",
                    "provider": "Auditoria de Limpeza por IA",
                }
                navigate_to(
                    "reward",
                    title="Área Limpa!",
                    subtitle="Siga para a destinação homologada.",
                    amount=half_val,
                    percentage_label="50% do total (Adiantamento)",
                    image_url=clean_img or (bounty.img if bounty else None),
                    ai_audit_info=ai_info,
                    button_label="Ir para Destino",
                    next_view="route_phase2",
                )

            def on_success_phase2(rem_val: float):
                navigate_to(
                    "reward",
                    title="Ciclo Fechado!",
                    subtitle="Descarte realizado com sucesso.",
                    amount=rem_val,
                    percentage_label="100% da missão concluída",
                    button_label="Voltar ao Início",
                    next_view="home",
                )

            view_control = CameraView(
                mode=mode,
                user=user,
                bounty_service=bounty_service,
                bounty=bounty,
                auto_open=auto_open,
                user_lat=app_state["user_lat"],
                user_lng=app_state["user_lng"],
                captured_image_path=captured_image_path,
                on_cancel=lambda: navigate_to("home"),
                on_success_phase1=on_success_phase1,
                on_success_phase2=on_success_phase2,
                on_success_denuncia=on_success_denuncia,
            )

        elif view_name == "reward":
            next_target = kwargs.get("next_view", "home")

            def handle_reward_next():
                if next_target == "route_phase2":
                    navigate_to("route", phase=2)
                elif next_target == "home_map":
                    navigate_to("home", initial_tab="map", selected_bounty=app_state.get("selected_bounty_on_map"))
                else:
                    navigate_to("home")

            view_control = RewardView(
                title=kwargs.get("title", "Sucesso!"),
                subtitle=kwargs.get("subtitle", "Ação confirmada."),
                amount=kwargs.get("amount"),
                percentage_label=kwargs.get("percentage_label"),
                button_label=kwargs.get("button_label", "Continuar"),
                image_url=kwargs.get("image_url"),
                ai_audit_info=kwargs.get("ai_audit_info"),
                on_action=handle_reward_next,
            )

        elif view_name == "profile":
            user = app_state["user"]

            def handle_logout():
                app_state["user"] = None
                app_state["active_bounty"] = None
                navigate_to("login")

            view_control = ProfileView(
                user=user,
                auth_service=auth_service,
                wallet_service=wallet_service,
                on_back=lambda: navigate_to("home"),
                on_logout=handle_logout,
            )
        else:
            view_control = ft.Text(f"View {view_name} não encontrada.")

        content_area.content = view_control
        page.update()

    # Container interno do app
    inner_frame = ft.Container(
        expand=True,
        bgcolor="#ffffff",
        border_radius=30,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=content_area,
    )

    # Moldura celular (Mockup responsivo com sombra no Desktop e 100% de tela no mobile/APK)
    device_frame = ft.Container(
        width=400,
        height=830,
        bgcolor="#0f172a",
        border_radius=36,
        padding=6,
        shadow=ft.BoxShadow(spread_radius=2, blur_radius=25, color="#64748b"),
        alignment=ft.alignment.center,
        content=inner_frame,
    )

    wrapper_container = ft.Container(
        expand=True,
        alignment=ft.alignment.center,
        content=device_frame,
    )

    def apply_adaptive_layout(e=None):
        """Ajusta o layout dinamicamente: 100% sem bordas no celular/APK, moldura no desktop."""
        w = page.width or 0
        platform_str = str(getattr(page, "platform", "") or "").lower()
        ua = str(getattr(page, "client_user_agent", "") or "").lower()
        is_mobile = (
            (w > 0 and w < 500)
            or platform_str in ["android", "ios"]
            or any(m in ua for m in ["android", "iphone", "ipad", "mobile"])
        )
        if is_mobile:
            page.bgcolor = "#ffffff"
            wrapper_container.padding = 0
            device_frame.width = None
            device_frame.height = None
            device_frame.expand = True
            device_frame.padding = 0
            device_frame.border_radius = 0
            device_frame.bgcolor = "#ffffff"
            device_frame.shadow = None
            inner_frame.border_radius = 0
        else:
            page.bgcolor = "#e2e8f0"
            wrapper_container.padding = 0
            device_frame.width = 400
            device_frame.height = 830
            device_frame.expand = False
            device_frame.padding = 6
            device_frame.border_radius = 36
            device_frame.bgcolor = "#0f172a"
            device_frame.shadow = ft.BoxShadow(spread_radius=2, blur_radius=25, color="#64748b")
            inner_frame.border_radius = 30
        page.update()

    page.on_resized = apply_adaptive_layout
    page.add(wrapper_container)
    apply_adaptive_layout()

    # Inicia com Splash View
    navigate_to("splash")


def get_local_network_ip() -> str:
    """Detecta o endereço IP local na rede Wi-Fi / Ethernet para acesso mobile."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    # Inicia o servidor HTTP de ações e uploads em tempo real antes de abrir o browser
    start_upload_server()

    local_ip = get_local_network_ip()
    mobile_url = f"http://{local_ip}:{SERVER_PORT}"
    local_url = f"http://localhost:{SERVER_PORT}"

    print("=================================================================")
    print("🌱 ECOBOUNTY - Economia Circular Gamificada (Maceió - AL)")
    print("=================================================================")
    print("🌐 Servidor Web Flet iniciado!")
    print(f"💻 No PC (Localhost): {local_url}")
    print(f"📱 No Celular (Wi-Fi): {mobile_url}")
    print("📸 Servidor de Câmera/Upload ativo na porta 8552")
    
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=1, border=1)
        qr.add_data(mobile_url)
        print("\n📲 Aponte a câmera do seu celular para abrir o app:")
        qr.print_ascii(invert=True)
    except Exception:
        pass

    print("=================================================================")
    print("Pressione Ctrl+C para encerrar o servidor.\n")

    # No Windows, passar "0.0.0.0" diretamente faz o websocket client interno do Flet
    # tentar se conectar a ws://0.0.0.0, gerando WinError 10049 e timeout de 30 segundos.
    # O valor "*" instrui o Flet a vincular o servidor a todas as interfaces (:port),
    # enquanto mantém a conexão do cliente interno via loopback (127.0.0.1).
    flet_host = "*" if SERVER_HOST in ("0.0.0.0", "*", "") else SERVER_HOST

    # Permite execução via "python -m app.main" ou direto "flet run --web app/main.py"
    ft.app(
        target=main,
        port=SERVER_PORT,
        host=flet_host,
        view=ft.AppView.WEB_BROWSER,
        assets_dir=str(ASSETS_DIR),
        upload_dir=str(UPLOADS_DIR),
    )
