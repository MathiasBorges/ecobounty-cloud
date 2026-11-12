"""Dashboard Principal (Home): Lista, Mapa, Filtros Dinâmicos e Ações (UC03, UC04, UC05, UC10)."""
from typing import Callable, List, Optional
import flet as ft

from app.config import DEFAULT_USER_LAT, DEFAULT_USER_LNG
from app.models.bounty import Bounty
from app.models.user import User
from app.services.bounty_service import BountyService
from app.services.wallet_service import WalletService
from app.views.components.denuncia_modal import DenunciaModal
from app.views.components.map_widget import EcoMapWidget


class HomeView(ft.UserControl):
    def __init__(
        self,
        user: User,
        bounty_service: BountyService,
        wallet_service: WalletService,
        on_open_mission: Callable[[Bounty], None],
        on_open_profile: Callable[[], None],
        on_open_camera_denuncia: Callable[[], None],
        user_lat: Optional[float] = None,
        user_lng: Optional[float] = None,
        city_label: Optional[str] = "Maceió, AL",
        is_real_location: bool = False,
        on_location_change: Optional[Callable[[float, float, str], None]] = None,
        initial_tab: str = "list",
        selected_bounty: Optional[Bounty] = None,
    ):
        super().__init__()
        self.user = user
        self.bounty_service = bounty_service
        self.wallet_service = wallet_service
        self.on_open_mission = on_open_mission
        self.on_open_profile = on_open_profile
        self.on_open_camera_denuncia = on_open_camera_denuncia
        self.on_location_change = on_location_change
        self.user_lat = user_lat if user_lat is not None else DEFAULT_USER_LAT
        self.user_lng = user_lng if user_lng is not None else DEFAULT_USER_LNG
        self.city_label = city_label or "Maceió, AL"
        self.is_real_location = is_real_location

        self.current_tab = initial_tab  # "list" ou "map"
        self.current_filter = "todos"  # "todos", "proximos", "valiosos", "plastico"
        self.selected_bounty_on_map: Optional[Bounty] = selected_bounty
        self.root_container = ft.Container(expand=True, bgcolor="#f8fafc")

        if self.current_tab == "map":
            try:
                from app.services.storage_service import set_pending_action
                set_pending_action("request_gps")
            except Exception:
                pass

    def safe_update(self):
        try:
            if self.page:
                self.update()
        except Exception:
            pass

    def refresh_user_balance(self):
        """Atualiza o saldo diretamente do banco contábil."""
        self.user.balance = self.wallet_service.get_balance(self.user.id)
        self._render()
        self.safe_update()

    def handle_change_location_dialog(self, e=None):
        """Abre diálogo para o usuário alternar o ponto geográfico ou selecionar outro bairro/cidade."""
        presets = [
            ("Ponta Verde / Pajuçara", -9.6610, -35.7020, "Maceió (Ponta Verde)"),
            ("Jatiúca / Mangabeiras", -9.6450, -35.7010, "Maceió (Jatiúca)"),
            ("Cruz das Almas / Jacarecica", -9.6280, -35.7050, "Maceió (Litoral Norte)"),
            ("Centro / Farol", -9.6635, -35.7350, "Maceió (Centro)"),
            ("Prado / Trapiche", -9.6680, -35.7480, "Maceió (Prado)"),
            ("Serraria / Antares", -9.5950, -35.7350, "Maceió (Serraria)"),
            ("Tabuleiro / Benedito Bentes", -9.5700, -35.7400, "Maceió (Parte Alta)"),
            ("Satuba (Conexão Atual / Provedor)", -9.5633, -35.8244, "Satuba, AL"),
            ("Arapiraca (Agreste Alagoano)", -9.7510, -36.6600, "Arapiraca, AL"),
            ("Marechal Deodoro / Francês", -9.7110, -35.8950, "Marechal Deodoro, AL"),
            ("Rio Largo (Aeroporto)", -9.4750, -35.8450, "Rio Largo, AL"),
        ]

        def select_preset(lat: float, lng: float, label: str):
            self.user_lat = lat
            self.user_lng = lng
            self.city_label = label
            self.is_real_location = True
            self.selected_bounty_on_map = None
            if self.on_location_change:
                self.on_location_change(lat, lng, label)
            self.bounty_service.ensure_nearby_bounties(lat, lng)
            if self.page and self.page.dialog:
                self.page.dialog.open = False
                self.page.update()
            self._render()
            self.safe_update()

        def detect_with_google(e=None):
            from app.services.google_maps_service import get_google_maps_service
            gmaps = get_google_maps_service()
            geo_info = gmaps.reverse_geocode(self.user_lat, self.user_lng)
            if geo_info and geo_info.get("full_label"):
                label = geo_info["full_label"]
                select_preset(self.user_lat, self.user_lng, label)
                if self.page:
                    self.page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"📍 Localização identificada: {label}"),
                        duration=3000,
                        bgcolor="#059669",
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
            else:
                select_preset(self.user_lat, self.user_lng, self.city_label or "Maceió (Jatiúca)")

        options_col = ft.Column(
            tight=True,
            scroll=ft.ScrollMode.AUTO,
            height=340,
            spacing=6,
            controls=[
                ft.ElevatedButton(
                    "🌐 Identificar Rua via Google Maps",
                    width=320,
                    style=ft.ButtonStyle(
                        bgcolor="#ecfdf5",
                        color="#059669",
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=detect_with_google,
                ),
                ft.Container(height=4),
                ft.Text("Ou toque no seu bairro para posicionar o pino e ver missões próximas:", size=12, color="#64748b"),
                *[
                    ft.ElevatedButton(
                        f"📍 {name}",
                        width=320,
                        style=ft.ButtonStyle(
                            bgcolor="#f8fafc",
                            color="#1e293b",
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                        on_click=lambda e, la=lat, ln=lng, lbl=lbl: select_preset(la, ln, lbl),
                    )
                    for name, lat, lng, lbl in presets
                ],
            ],
        )

        def close_dialog(e):
            dlg.open = False
            if self.page:
                self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Definir Localização", weight=ft.FontWeight.BOLD),
            content=options_col,
            actions=[
                ft.TextButton("Fechar", on_click=close_dialog),
            ],
        )
        if self.page:
            self.page.dialog = dlg
            dlg.open = True
            self.page.update()

    def set_tab(self, tab: str, e=None):
        self.current_tab = tab
        if tab == "map":
            try:
                from app.services.storage_service import get_client_id, set_pending_action
                set_pending_action("request_gps", cid=get_client_id(self.page))
            except Exception:
                pass
        self._render()
        self.safe_update()

    def set_filter(self, filter_name: str, e=None):
        self.current_filter = filter_name
        self._render()
        self.safe_update()

    def handle_open_denuncia_modal(self, e):
        DenunciaModal.show(
            page=self.page,
            on_open_camera=self.on_open_camera_denuncia,
        )

    def build_bounty_card(self, b: Bounty) -> ft.Control:
        color_map = {
            "blue": ("#dbeafe", "#2563eb", ft.icons.LOCAL_DRINK),
            "orange": ("#ffedd5", "#ea580c", ft.icons.CONSTRUCTION),
            "slate": ("#f1f5f9", "#475569", ft.icons.DEVICES),
        }
        bg_col, icon_col, icon_data = color_map.get(
            b.color, ("#d1fae5", "#059669", ft.icons.DELETE_OUTLINE)
        )

        return ft.Container(
            bgcolor="#ffffff",
            border_radius=16,
            padding=14,
            border=ft.border.all(1, "#f1f5f9"),
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=6, color="#f1f5f9"),
            on_click=lambda e, bounty=b: self.on_open_mission(bounty),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=46,
                                height=46,
                                border_radius=12,
                                bgcolor=bg_col,
                                alignment=ft.alignment.center,
                                content=ft.Icon(icon_data, color=icon_col, size=24),
                            ),
                            ft.Column(
                                spacing=3,
                                controls=[
                                    ft.Text(b.title, size=14, weight=ft.FontWeight.BOLD, color="#1e293b"),
                                    ft.Row(
                                        spacing=4,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        controls=[
                                            ft.Icon(ft.icons.LOCATION_ON, color="#059669", size=13),
                                            ft.Text(
                                                f"{b.formatted_distance()} • {b.type}",
                                                size=11,
                                                color="#64748b",
                                                weight=ft.FontWeight.W_500,
                                            ),
                                            *(
                                                [
                                                    ft.Container(
                                                        padding=ft.padding.symmetric(horizontal=5, vertical=1),
                                                        border_radius=4,
                                                        bgcolor="#ecfdf5",
                                                        border=ft.border.all(1, "#a7f3d0"),
                                                        content=ft.Text(
                                                            f"⚡ Dijkstra: {b.dijkstra_km:.1f}km",
                                                            size=9,
                                                            weight=ft.FontWeight.BOLD,
                                                            color="#047857",
                                                        ),
                                                    )
                                                ]
                                                if getattr(b, "dijkstra_km", None) is not None
                                                else []
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    ft.Text(
                        b.formatted_value(),
                        size=15,
                        weight=ft.FontWeight.W_800,
                        color="#059669",
                    ),
                ],
            ),
        )

    def build_filter_chip(self, label: str, filter_key: str) -> ft.Control:
        is_active = self.current_filter == filter_key
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=14, vertical=6),
            border_radius=20,
            bgcolor="#ecfdf5" if is_active else "#ffffff",
            border=ft.border.all(1, "#059669" if is_active else "#e2e8f0"),
            on_click=lambda e: self.set_filter(filter_key, e),
            content=ft.Text(
                label,
                size=12,
                weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.W_500,
                color="#059669" if is_active else "#475569",
            ),
        )

    def build(self):
        self._render()
        return self.root_container

    def _render(self):
        # Atualiza dados dinâmicos do banco respeitando as coordenadas do usuário
        bounties = self.bounty_service.get_bounties(
            filter_type=self.current_filter,
            user_lat=self.user_lat,
            user_lng=self.user_lng,
        )
        if bounties:
            # Se o filtro Dijkstra estiver ativo, prioriza o topo ordenado pela malha viária
            if self.current_filter in ("dijkstra", "rota_otima"):
                self.selected_bounty_on_map = bounties[0]
            # Seleciona automaticamente o bounty mais próximo para foco no mapa se o atual for nulo ou distante
            elif (
                not self.selected_bounty_on_map
                or self.selected_bounty_on_map.dist > 3000
                or self.selected_bounty_on_map.id not in [b.id for b in bounties]
            ):
                self.selected_bounty_on_map = min(bounties, key=lambda b: b.dist)
        display_city = self.city_label or ""
        if "(" in display_city:
            display_city = display_city.split("(")[0].strip().rstrip(",")
        if not display_city or display_city in ("Maceió, AL", "Satuba, AL"):
            try:
                from app.services.google_maps_service import get_google_maps_service
                info = get_google_maps_service().reverse_geocode(self.user_lat, self.user_lng)
                if info and info.get("short_label"):
                    display_city = info["short_label"]
            except Exception:
                pass
        if not display_city:
            display_city = "Satuba, AL" if (-9.63 <= self.user_lat <= -9.52 and -35.86 <= self.user_lng <= -35.78) else "Maceió, AL"

        current_bal_formatted = f"R$ {self.wallet_service.get_balance(self.user.id):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        # Banner Contextual de Papel
        role_banner_data = {
            "CIDADAO": (
                "#f0f9ff",
                "#0284c7",
                "#bae6fd",
                ft.icons.CAMPAIGN,
                "Modo Cidadão Ativo",
                "Mapeie descarte irregular! Toque no botão central (+) para criar uma denúncia comunitária.",
            ),
            "ECOPONTO": (
                "#fffbeb",
                "#d97706",
                "#fde68a",
                ft.icons.RECYCLING,
                "Modo Ecoponto / Cooperativa",
                "Ponto homologado para recebimento de recicláveis e fechamento de ciclo dos coletores.",
            ),
            "PATROCINADOR": (
                "#faf5ff",
                "#9333ea",
                "#e9d5ff",
                ft.icons.BUSINESS,
                "Painel do Patrocinador ESG",
                "Suas iniciativas financiam a limpeza urbana e o desenvolvimento socioambiental de Maceió.",
            ),
            "COLETOR": (
                "#f0fdf4",
                "#059669",
                "#bbf7d0",
                ft.icons.CLEANING_SERVICES,
                "Modo Coletor Ativo",
                "Selecione uma missão no mapa ou lista, limpe a área e receba seu adiantamento de 50%!",
            ),
        }
        bg_b, text_b, border_b, icon_b, title_b, desc_b = role_banner_data.get(
            self.user.role.upper(),
            role_banner_data["COLETOR"],
        )
        role_banner = ft.Container(
            bgcolor=bg_b,
            border=ft.border.all(1, border_b),
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            content=ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon_b, color=text_b, size=20),
                    ft.Column(
                        expand=True,
                        spacing=1,
                        controls=[
                            ft.Text(title_b, weight=ft.FontWeight.BOLD, size=12, color="#1e293b"),
                            ft.Text(desc_b, size=11, color="#475569"),
                        ],
                    ),
                ],
            ),
        )

        # Cabeçalho Superior Fixo
        header = ft.Container(
            bgcolor="#ffffff",
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border=ft.border.only(bottom=ft.BorderSide(1, "#f1f5f9")),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.CircleAvatar(
                                content=ft.Text(self.user.name[0].upper(), color="white", weight=ft.FontWeight.BOLD),
                                bgcolor="#059669",
                                radius=18,
                            ),
                            ft.Column(
                                spacing=1,
                                controls=[
                                    ft.Row(
                                        spacing=6,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        controls=[
                                            ft.Text(f"Olá, {self.user.name.split()[0]}", size=12, color="#64748b"),
                                            ft.Container(
                                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                                border_radius=6,
                                                bgcolor="#fee2e2" if self.user.is_admin() else "#ecfdf5",
                                                content=ft.Text(
                                                    self.user.role_display_name().upper(),
                                                    size=9,
                                                    weight=ft.FontWeight.BOLD,
                                                    color="#b91c1c" if self.user.is_admin() else "#059669",
                                                ),
                                            ),
                                        ],
                                    ),
                                    ft.Container(
                                        on_click=self.handle_change_location_dialog,
                                        tooltip="Toque para alterar a localização (Centro, Ponta Verde, Arapiraca...)",
                                        content=ft.Row(
                                            spacing=4,
                                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                            controls=[
                                                ft.Icon(
                                                    ft.icons.MY_LOCATION if self.is_real_location else ft.icons.LOCATION_ON,
                                                    color="#059669",
                                                    size=14,
                                                ),
                                                ft.Text(display_city, size=13, weight=ft.FontWeight.BOLD, color="#1e293b", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                                ft.Container(
                                                    padding=ft.padding.symmetric(horizontal=4, vertical=1),
                                                    border_radius=4,
                                                    bgcolor="#ecfdf5" if self.is_real_location else "#f1f5f9",
                                                    content=ft.Text(
                                                        "GPS Ativo" if self.is_real_location else "Maceió",
                                                        size=8,
                                                        weight=ft.FontWeight.BOLD,
                                                        color="#059669" if self.is_real_location else "#64748b",
                                                    ),
                                                ),
                                                ft.Icon(ft.icons.ARROW_DROP_DOWN, color="#64748b", size=16),
                                            ],
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),
                    # Saldo Dinâmico
                    ft.Container(
                        bgcolor="#0f172a",
                        padding=ft.padding.symmetric(horizontal=12, vertical=6),
                        border_radius=20,
                        content=ft.Row(
                            spacing=6,
                            controls=[
                                ft.Icon(ft.icons.ACCOUNT_BALANCE_WALLET, color="#34d399", size=16),
                                ft.Text(current_bal_formatted, color="white", weight=ft.FontWeight.BOLD, size=13),
                            ],
                        ),
                    ),
                ],
            ),
        )

        # Seletor Segmentado Lista / Mapa
        segmented_tab = ft.Container(
            bgcolor="#ffffff",
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        bgcolor="#f1f5f9",
                        border_radius=12,
                        padding=3,
                        width=240,
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=2,
                            controls=[
                                ft.Container(
                                    expand=True,
                                    alignment=ft.alignment.center,
                                    padding=ft.padding.symmetric(vertical=7),
                                    bgcolor="#ffffff" if self.current_tab == "list" else "transparent",
                                    border_radius=10,
                                    shadow=ft.BoxShadow(blur_radius=2, color="#cbd5e1") if self.current_tab == "list" else None,
                                    on_click=lambda e: self.set_tab("list", e),
                                    content=ft.Text(
                                        "Lista",
                                        size=13,
                                        weight=ft.FontWeight.BOLD if self.current_tab == "list" else ft.FontWeight.W_500,
                                        color="#1e293b" if self.current_tab == "list" else "#64748b",
                                    ),
                                ),
                                ft.Container(
                                    expand=True,
                                    alignment=ft.alignment.center,
                                    padding=ft.padding.symmetric(vertical=7),
                                    bgcolor="#ffffff" if self.current_tab == "map" else "transparent",
                                    border_radius=10,
                                    shadow=ft.BoxShadow(blur_radius=2, color="#cbd5e1") if self.current_tab == "map" else None,
                                    on_click=lambda e: self.set_tab("map", e),
                                    content=ft.Text(
                                        "Mapa",
                                        size=13,
                                        weight=ft.FontWeight.BOLD if self.current_tab == "map" else ft.FontWeight.W_500,
                                        color="#1e293b" if self.current_tab == "map" else "#64748b",
                                    ),
                                ),
                            ],
                        ),
                    )
                ],
            ),
        )

        # Chips de Filtro e Banner Contextual do Papel
        filter_chips_row = ft.Container(
            bgcolor="#ffffff",
            padding=ft.padding.only(left=16, right=16, bottom=10),
            visible=self.current_tab == "list",
            content=ft.Column(
                spacing=8,
                controls=[
                    role_banner,
                    ft.Row(
                        scroll=ft.ScrollMode.AUTO,
                        spacing=8,
                        controls=[
                            self.build_filter_chip("Todos", "todos"),
                            self.build_filter_chip("🎯 Rota Ótima (Dijkstra)", "dijkstra"),
                            self.build_filter_chip("Próximos", "proximos"),
                            self.build_filter_chip("+ Valiosos", "valiosos"),
                            self.build_filter_chip("Plástico", "plastico"),
                        ],
                    ),
                ],
            ),
        )

        # Área de Conteúdo (Lista ou Mapa)
        if self.current_tab == "list":
            if not bounties:
                main_area = ft.Container(
                    expand=True,
                    alignment=ft.alignment.center,
                    padding=20,
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                        controls=[
                            ft.Icon(ft.icons.SEARCH_OFF, color="#94a3b8", size=48),
                            ft.Text("Nenhum resultado encontrado.", size=14, color="#64748b", weight=ft.FontWeight.W_500),
                        ],
                    ),
                )
            else:
                main_area = ft.Container(
                    expand=True,
                    padding=ft.padding.symmetric(horizontal=16, vertical=8),
                    content=ft.ListView(
                        spacing=10,
                        controls=[self.build_bounty_card(b) for b in bounties],
                    ),
                )
        else:
            # Visualização do Mapa respeitando o filtro ativo e localização real do usuário
            self.map_widget = EcoMapWidget(
                bounties=bounties,
                selected_bounty=self.selected_bounty_on_map or (bounties[0] if bounties else None),
                user_lat=self.user_lat,
                user_lng=self.user_lng,
                on_select_bounty=lambda b: setattr(self, "selected_bounty_on_map", b),
                on_open_details=self.on_open_mission,
                width=400,
                height=None,
                expand=True,
            )
            main_area = ft.Container(
                expand=True,
                padding=0,
                content=self.map_widget,
            )

        # Barra de Navegação Inferior (Bottom Bar)
        bottom_nav = ft.Container(
            bgcolor="#ffffff",
            padding=ft.padding.symmetric(horizontal=24, vertical=6),
            border=ft.border.only(top=ft.BorderSide(1, "#f1f5f9")),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    # Aba Bounties
                    ft.IconButton(
                        icon=ft.icons.FORMAT_LIST_BULLETED,
                        icon_color="#059669" if self.current_tab == "list" else "#64748b",
                        icon_size=26,
                        tooltip="Bounties",
                        on_click=lambda e: self.set_tab("list", e),
                    ),
                    # Botão Central Flutuante (+) para Nova Denúncia
                    ft.Container(
                        width=54,
                        height=54,
                        border_radius=27,
                        bgcolor="#0f172a",
                        alignment=ft.alignment.center,
                        shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color="#0f172a"),
                        on_click=self.handle_open_denuncia_modal,
                        content=ft.Icon(ft.icons.ADD, color="white", size=30),
                    ),
                    # Aba Perfil
                    ft.IconButton(
                        icon=ft.icons.PERSON_OUTLINE,
                        icon_color="#64748b",
                        icon_size=26,
                        tooltip="Perfil do Coletor",
                        on_click=lambda e: self.on_open_profile(),
                    ),
                ],
            ),
        )

        self.root_container.content = ft.Column(
            spacing=0,
            controls=[
                header,
                segmented_tab,
                filter_chips_row,
                main_area,
                bottom_nav,
            ],
        )
