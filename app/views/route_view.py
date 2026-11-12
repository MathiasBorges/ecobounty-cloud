"""Tela de Navegação por Rota (Fase 1 - Coleta e Fase 2 - Descarte) (UC07, UC09)."""
from typing import Callable, Optional
import flet as ft

from app.config import DEFAULT_USER_LAT, DEFAULT_USER_LNG
from app.models.bounty import Bounty
from app.models.user import User
from app.services.bounty_service import BountyService, haversine_distance
from app.views.components.map_widget import EcoMapWidget


class RouteView(ft.UserControl):
    def __init__(
        self,
        bounty: Bounty,
        user: User,
        phase: int,  # 1 ou 2
        bounty_service: BountyService,
        on_back: Callable[[], None],
        on_trigger_camera: Callable[[int], None],
        initial_user_lat: Optional[float] = None,
        initial_user_lng: Optional[float] = None,
        is_real_location: bool = False,
    ):
        super().__init__()
        self.bounty = bounty
        self.user = user
        self.phase = phase
        self.bounty_service = bounty_service
        self.on_back = on_back
        self.on_trigger_camera = on_trigger_camera
        self.is_real_location = is_real_location

        # Coordenadas reais de origem do usuário (ou fallback Maceió)
        self.real_user_lat = initial_user_lat if initial_user_lat is not None else DEFAULT_USER_LAT
        self.real_user_lng = initial_user_lng if initial_user_lng is not None else DEFAULT_USER_LNG

        # Inicia priorizando a posição física real do usuário
        self.user_lat = self.real_user_lat
        self.user_lng = self.real_user_lng
        if initial_user_lat is not None and (initial_user_lat == self.bounty.lat and initial_user_lng == self.bounty.lng):
            self.simulated_gps_mode = "local"
        elif is_real_location:
            self.simulated_gps_mode = "real"
        else:
            self.simulated_gps_mode = "em_rota"

        self.error_text = ft.Text("", color="#dc2626", size=13, weight=ft.FontWeight.BOLD, visible=False)
        self.root_container = ft.Container(expand=True, bgcolor="#ffffff")

    def safe_update(self):
        if self.page:
            self.update()

    def open_in_google_maps(self, e=None):
        """Abre a rota georreferenciada no aplicativo oficial do Google Maps com GPS em tempo real."""
        if self.phase == 1:
            dest_lat = self.bounty.lat
            dest_lng = self.bounty.lng
        else:
            from app.services.ecoponto_service import get_ecoponto_service
            eco = get_ecoponto_service().get_ecoponto(self.bounty.dest)
            dest_lat = eco.lat
            dest_lng = eco.lng
        url = f"https://www.google.com/maps/dir/?api=1&origin={self.user_lat},{self.user_lng}&destination={dest_lat},{dest_lng}&travelmode=walking"
        if self.page:
            self.page.launch_url(url)

    def use_real_gps(self, e=None):
        """Ativa a posição física real detectada do usuário."""
        try:
            from app.services.storage_service import get_client_id, set_pending_action
            set_pending_action("request_gps", cid=get_client_id(self.page))
        except Exception:
            pass
        if self.page:
            try:
                lat = self.page.client_storage.get("ecobounty_real_lat")
                lng = self.page.client_storage.get("ecobounty_real_lng")
                if lat and lng:
                    self.real_user_lat = float(lat)
                    self.real_user_lng = float(lng)
            except Exception:
                pass

        self.user_lat = self.real_user_lat
        self.user_lng = self.real_user_lng
        self.simulated_gps_mode = "real"
        self.error_text.visible = False
        self._render()
        self.safe_update()

    def set_gps_mode(self, mode: str, e=None):
        self.simulated_gps_mode = mode
        if mode == "distante":
            self.user_lat = -9.665
            self.user_lng = -35.730
        elif mode == "local":
            self.user_lat = self.bounty.lat
            self.user_lng = self.bounty.lng
        elif mode == "real":
            self.user_lat = self.real_user_lat
            self.user_lng = self.real_user_lng
        else:  # "em_rota"
            self.user_lat = DEFAULT_USER_LAT
            self.user_lng = DEFAULT_USER_LNG
        self.error_text.visible = False
        self._render()
        self.safe_update()

    def handle_arrive_button(self, e):
        # Validação de proximidade geográfica na Fase 1 (UC07 FE2)
        if self.phase == 1:
            from app.config import SIMULATION_MODE
            should_enforce = (self.simulated_gps_mode == "distante") or not SIMULATION_MODE
            ok, msg, dist = self.bounty_service.check_in_cleaning_location(
                bounty_id=self.bounty.id,
                user_lat=self.user_lat,
                user_lng=self.user_lng,
                enforce_radius=should_enforce,
            )
            if not ok:
                self.error_text.value = msg
                self.error_text.visible = True
                self._render()
                self.safe_update()
                return

            self.error_text.visible = False
            self.on_trigger_camera(1)
        else:
            self.error_text.visible = False
            self.on_trigger_camera(2)

    def build(self):
        self._render()
        return self.root_container

    def _render(self):
        is_phase_1 = self.phase == 1
        if is_phase_1:
            dest_lat = self.bounty.lat
            dest_lng = self.bounty.lng
            dest_display_name = self.bounty.title
        else:
            from app.services.ecoponto_service import get_ecoponto_service
            eco = get_ecoponto_service().get_ecoponto(self.bounty.dest)
            dest_lat = eco.lat
            dest_lng = eco.lng
            dest_display_name = f"{eco.name} ({eco.neighborhood})"

        # Enriquecimento de rota sem bloquear o event loop da interface
        from app.services.google_maps_service import _ROUTE_CACHE, get_google_maps_service
        cache_key = (
            round(self.user_lat, 4),
            round(self.user_lng, 4),
            round(dest_lat, 4),
            round(dest_lng, 4),
        )
        route_info = _ROUTE_CACHE.get(cache_key)
        if not route_info and not getattr(self, "_fetching_route", False):
            self._fetching_route = True
            def fetch_route_async(olat, olng, dlat, dlng):
                try:
                    gmaps = get_google_maps_service()
                    gmaps.compute_walking_route(olat, olng, dlat, dlng)
                    if self.page:
                        self._render()
                        self.safe_update()
                except Exception:
                    pass
                finally:
                    self._fetching_route = False

            import threading
            threading.Thread(
                target=fetch_route_async,
                args=(self.user_lat, self.user_lng, dest_lat, dest_lng),
                daemon=True,
            ).start()

        if route_info:
            dist_label = f"{route_info['distance_text']} ({route_info['duration_text']} a pé)"
        else:
            dist_meters = round(
                haversine_distance(self.user_lat, self.user_lng, dest_lat, dest_lng)
            )
            dist_label = f"{dist_meters}m" if dist_meters < 1000 else f"{dist_meters/1000:.1f}km"

        title_text = "Rota de Coleta (Fase 1)" if is_phase_1 else "Rota de Descarte (Fase 2)"
        subtitle_text = (
            f"Siga até o resíduo ({dist_label})"
            if is_phase_1
            else f"Leve até: {dest_display_name} ({dist_label})"
        )
        btn_label = "Cheguei no Local (Limpar)" if is_phase_1 else "Cheguei no Destino"
        btn_icon = ft.icons.CAMERA_ALT if is_phase_1 else ft.icons.PHOTO_CAMERA

        # Top Bar
        header = ft.Container(
            bgcolor="#ffffff",
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border=ft.border.only(bottom=ft.BorderSide(1, "#f1f5f9")),
            content=ft.Row(
                spacing=12,
                controls=[
                    ft.IconButton(
                        icon=ft.icons.ARROW_BACK,
                        icon_color="#1e293b",
                        on_click=lambda e: self.on_back(),
                    ),
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(title_text, size=14, weight=ft.FontWeight.BOLD, color="#1e293b"),
                            ft.Text(subtitle_text, size=12, color="#64748b", weight=ft.FontWeight.W_500),
                        ],
                    ),
                ],
            ),
        )

        # Seletor de Simulação GPS para a Fase 1 (facilita testar UC07 FE2 e usar GPS real)
        gps_selector = ft.Container(
            visible=is_phase_1,
            bgcolor="#f8fafc",
            padding=ft.padding.symmetric(horizontal=8, vertical=6),
            border=ft.border.only(bottom=ft.BorderSide(1, "#f1f5f9")),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=4,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.TextButton(
                        "📍 GPS Real",
                        style=ft.ButtonStyle(
                            color="#7c3aed" if self.simulated_gps_mode == "real" else "#64748b"
                        ),
                        on_click=self.use_real_gps,
                    ),
                    ft.TextButton(
                        "Em Rota",
                        style=ft.ButtonStyle(
                            color="#2563eb" if self.simulated_gps_mode == "em_rota" else "#94a3b8"
                        ),
                        on_click=lambda e: self.set_gps_mode("em_rota", e),
                    ),
                    ft.TextButton(
                        "No Local (0m)",
                        style=ft.ButtonStyle(
                            color="#059669" if self.simulated_gps_mode == "local" else "#94a3b8"
                        ),
                        on_click=lambda e: self.set_gps_mode("local", e),
                    ),
                    ft.TextButton(
                        "A 330m (Erro)",
                        style=ft.ButtonStyle(
                            color="#dc2626" if self.simulated_gps_mode == "distante" else "#94a3b8"
                        ),
                        on_click=lambda e: self.set_gps_mode("distante", e),
                    ),
                ],
            ),
        )

        # Mapa da Rota
        self.map_widget = EcoMapWidget(
            bounties=[self.bounty],
            selected_bounty=self.bounty,
            user_lat=self.user_lat,
            user_lng=self.user_lng,
            route_mode="phase1" if is_phase_1 else "phase2",
            width=400,
            height=None,
            expand=True,
        )
        map_content = ft.Container(
            expand=True,
            content=self.map_widget,
        )

        # Barra de Ação Inferior com botões de navegação e Check-in
        bottom_bar = ft.Container(
            bgcolor="#ffffff",
            padding=16,
            border=ft.border.only(top=ft.BorderSide(1, "#f1f5f9")),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    self.error_text,
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.OutlinedButton(
                                expand=True,
                                content=ft.Row(
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=6,
                                    controls=[
                                        ft.Icon(ft.icons.MAP, color="#059669", size=16),
                                        ft.Text(
                                            "Mapa Interativo HD",
                                            color="#059669",
                                            weight=ft.FontWeight.BOLD,
                                            size=12,
                                        ),
                                    ],
                                ),
                                style=ft.ButtonStyle(
                                    side=ft.BorderSide(1, "#a7f3d0"),
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=ft.padding.symmetric(vertical=12),
                                ),
                                on_click=lambda e: self.map_widget.open_leaflet_interactive(),
                            ),
                            ft.OutlinedButton(
                                expand=True,
                                content=ft.Row(
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=6,
                                    controls=[
                                        ft.Icon(ft.icons.DIRECTIONS_WALK, color="#2563eb", size=16),
                                        ft.Text(
                                            "Google Maps",
                                            color="#2563eb",
                                            weight=ft.FontWeight.BOLD,
                                            size=12,
                                        ),
                                    ],
                                ),
                                style=ft.ButtonStyle(
                                    side=ft.BorderSide(1, "#93c5fd"),
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=ft.padding.symmetric(vertical=12),
                                ),
                                on_click=self.open_in_google_maps,
                            ),
                        ],
                    ),
                    ft.ElevatedButton(
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=8,
                            controls=[
                                ft.Icon(btn_icon, color="white", size=20),
                                ft.Text(btn_label, color="white", weight=ft.FontWeight.BOLD, size=15),
                            ],
                        ),
                        bgcolor="#059669",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=14),
                            padding=ft.padding.symmetric(vertical=15),
                        ),
                        on_click=self.handle_arrive_button,
                    ),
                ],
            ),
        )

        self.root_container.content = ft.Column(
            spacing=0,
            controls=[
                header,
                gps_selector,
                map_content,
                bottom_bar,
            ],
        )
