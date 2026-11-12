"""Componente de Mapa Interativo em Flet (EcoMapWidget) Multi-Escala.

Suporta 3 níveis de abrangência cartográfica com OpenStreetMap real:
1. "alagoas": Todo o Estado de Alagoas (Arapiraca, Maceió, Penedo, Maragogi, etc.)
2. "metropolitana": Grande Maceió e Lagoas (Mundaú/Manguaba, Marechal, Rio Largo)
3. "urbano": Ruas e Bairros detalhados de Maceió (Centro, Farol, Ponta Verde, etc.)
"""
from typing import Callable, Dict, List, Optional
import base64
import math
from pathlib import Path
import flet as ft
import flet.canvas as cv

from app.config import (
    DEFAULT_USER_LAT,
    DEFAULT_USER_LNG,
    MACEIO_CENTER_LAT,
    MACEIO_CENTER_LNG,
)
from app.models.bounty import Bounty

MAP_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"
_BASE64_CACHE: Dict[str, Optional[str]] = {}


def get_map_base64(filename: str) -> Optional[str]:
    """Recupera o base64 da imagem cartográfica para renderização instantânea no CanvasKit/Web."""
    if filename not in _BASE64_CACHE:
        file_path = MAP_ASSETS_DIR / filename
        if file_path.exists():
            try:
                with open(file_path, "rb") as f:
                    _BASE64_CACHE[filename] = base64.b64encode(f.read()).decode("ascii")
            except Exception:
                _BASE64_CACHE[filename] = None
        else:
            _BASE64_CACHE[filename] = None
    return _BASE64_CACHE.get(filename)


MAP_LEVELS = {
    "alagoas": {
        "label": "Alagoas",
        "file": "alagoas_map.png",
        "nw_lat": -8.40717,
        "nw_lng": -39.37500,
        "se_lat": -11.17840,
        "se_lng": -33.75000,
        "width": 1024.0,
        "height": 512.0,
        "center_lat": -9.60,
        "center_lng": -36.50,
    },
    "metropolitana": {
        "label": "Grande Maceió",
        "file": "grande_maceio_map.png",
        "nw_lat": -9.27562,
        "nw_lng": -36.03516,
        "se_lat": -9.96885,
        "se_lng": -35.50781,
        "width": 768.0,
        "height": 1024.0,
        "center_lat": -9.62,
        "center_lng": -35.77,
    },
    "urbano": {
        "label": "Ruas",
        "file": "maceio_map.png",
        "nw_lat": -9.62241,
        "nw_lng": -35.77148,
        "se_lat": -9.68740,
        "se_lng": -35.70557,
        "width": 768.0,
        "height": 768.0,
        "center_lat": -9.665,
        "center_lng": -35.735,
    },
}


class EcoMapWidget(ft.UserControl):
    def __init__(
        self,
        bounties: Optional[List[Bounty]] = None,
        selected_bounty: Optional[Bounty] = None,
        user_lat: float = DEFAULT_USER_LAT,
        user_lng: float = DEFAULT_USER_LNG,
        route_mode: str = "none",  # "none", "phase1", "phase2"
        on_select_bounty: Optional[Callable[[Bounty], None]] = None,
        on_open_details: Optional[Callable[[Bounty], None]] = None,
        width: int = 400,
        height: Optional[int] = None,
        expand: bool = True,
        simulated_offline: bool = False,
        initial_level: str = "urbano",
    ):
        super().__init__()
        self.expand = expand
        self.bounties = bounties or []
        self.selected_bounty = selected_bounty or (self.bounties[0] if self.bounties else None)
        self.user_lat = user_lat
        self.user_lng = user_lng
        self.route_mode = route_mode
        self.on_select_bounty = on_select_bounty
        self.on_open_details = on_open_details
        self.map_width = width or 400
        self.map_height = height or 650
        self.simulated_offline = simulated_offline
        nw = MAP_LEVELS["urbano"]
        is_inside_urbano = (
            nw["se_lat"] <= self.user_lat <= nw["nw_lat"]
            and nw["nw_lng"] <= self.user_lng <= nw["se_lng"]
        )
        if initial_level in MAP_LEVELS:
            self.active_level = initial_level
        else:
            self.active_level = "urbano" if is_inside_urbano else "metropolitana"
        
        # Define zoom inicial adequado para o escopo
        if self.active_level == "urbano":
            self.zoom = 2.0 if is_inside_urbano else 3.8
        elif self.active_level == "metropolitana":
            self.zoom = 1.6
        else:
            self.zoom = 0.85

        self.pan_x = 0.0
        self.pan_y = 0.0

        self.provider = "google"
        self.gmaps_view_state = None  # (center_lat, center_lng, g_zoom)
        self.drag_gesture = ft.GestureDetector(
            content=ft.Container(
                width=self.map_width,
                height=self.map_height,
                bgcolor=ft.colors.TRANSPARENT,
            ),
            drag_interval=35,
            on_pan_update=self.handle_pan_update,
            mouse_cursor=ft.MouseCursor.GRAB,
        )
        self.root_container = ft.Container(
            expand=self.expand,
            width=None if self.expand else self.map_width,
            height=None if self.expand else self.map_height,
            border_radius=16,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            bgcolor="#e2e8f0",
        )

    def did_mount(self):
        """Solicita GPS sob demanda no momento em que o mapa é aberto na tela."""
        try:
            from app.services.storage_service import get_client_id, register_location_listener, set_pending_action
            cid = get_client_id(self.page)
            set_pending_action("request_gps", cid=cid)
            register_location_listener(self.update_user_position, cid=cid)
        except Exception:
            pass

    def will_unmount(self):
        try:
            from app.services.storage_service import unregister_location_listener
            unregister_location_listener(self.update_user_position)
        except Exception:
            pass

    def update_user_position(self, lat: float, lng: float):
        """Atualiza a posição física real do usuário e re-centraliza o mapa."""
        self.user_lat = float(lat)
        self.user_lng = float(lng)
        self.gmaps_view_state = (self.user_lat, self.user_lng, 15)
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._render()
        self.safe_update()

    def open_leaflet_interactive(self, e=None):
        """Abre o mapa interativo Leaflet.js real com suporte a zoom, satélite e camadas livres."""
        import json
        import urllib.parse

        bounties_data = [
            {
                "id": b.id,
                "title": b.title,
                "value": b.val,
                "lat": b.lat,
                "lng": b.lng,
                "type": b.type,
                "dist_text": b.formatted_distance(),
            }
            for b in self.bounties[:25]
        ]
        bounties_json = urllib.parse.quote(json.dumps(bounties_data))

        dest_lat = 0.0
        dest_lng = 0.0
        if self.selected_bounty and self.route_mode in ["phase1", "phase2"]:
            if self.route_mode == "phase1":
                dest_lat = self.selected_bounty.lat
                dest_lng = self.selected_bounty.lng
            else:
                from app.services.ecoponto_service import get_ecoponto_service
                eco = get_ecoponto_service().get_ecoponto(self.selected_bounty.dest)
                dest_lat = eco.lat
                dest_lng = eco.lng

        # 1. Notifica o navegador hospedeiro para abrir o modal Leaflet in-page
        try:
            from app.services.storage_service import get_client_id, set_pending_action
            set_pending_action(
                "open_leaflet_map",
                {
                    "lat": round(self.user_lat, 6),
                    "lng": round(self.user_lng, 6),
                    "zoom": 15,
                    "route_mode": self.route_mode,
                    "dest_lat": round(dest_lat, 6),
                    "dest_lng": round(dest_lng, 6),
                    "bounties": bounties_data,
                },
                cid=get_client_id(self.page),
            )
        except Exception:
            pass

        # 2. Se executando em cliente nativo ou sem escuta de ação web, lança URL de fallback
        interactive_url = (
            f"/interactive_map.html?"
            f"lat={self.user_lat:.6f}&lng={self.user_lng:.6f}"
            f"&zoom=15&route_mode={self.route_mode}"
            f"&dest_lat={dest_lat:.6f}&dest_lng={dest_lng:.6f}"
            f"&bounties={bounties_json}"
        )
        is_web = getattr(self.page, "web", True) if self.page else False
        if not is_web and self.page:
            try:
                self.page.launch_url(interactive_url)
            except Exception:
                pass

    def set_provider(self, prov: str, e=None):
        """Alterna entre o mapa interativo Leaflet (Livre) e o Google Maps oficial."""
        self.provider = prov
        self._render()
        self.safe_update()

    def is_google_maps_active(self) -> bool:
        """Verifica se há chave de produção oficial da Google Maps Platform ativa e não negada."""
        try:
            from app.services.google_maps_service import get_google_maps_service, is_google_api_denied
            if is_google_api_denied():
                return False
            gmaps = get_google_maps_service()
            return gmaps.is_available()
        except Exception:
            return False

    def safe_update(self):
        if self.page:
            self.update()

    def set_level(self, level: str, e=None):
        """Muda o nível de abrangência do mapa (Alagoas, Grande Maceió ou Ruas)."""
        if level in MAP_LEVELS:
            self.active_level = level
            nw = MAP_LEVELS["urbano"]
            is_inside_urbano = (
                nw["se_lat"] <= self.user_lat <= nw["nw_lat"]
                and nw["nw_lng"] <= self.user_lng <= nw["se_lng"]
            )
            # Ao selecionar "Ruas", entra em modo de proximidade adequado
            if level == "urbano":
                self.zoom = 2.0 if is_inside_urbano else 2.2
            elif level == "metropolitana":
                self.zoom = 1.6
            elif level == "alagoas":
                self.zoom = 0.85

        self.pan_x = 0.0
        self.pan_y = 0.0
        self._render()
        self.safe_update()

    def lat_lng_to_base_xy(self, lat: float, lng: float) -> tuple[float, float]:
        """Projeção Web Mercator exata para a malha do nível ativo."""
        nw = MAP_LEVELS["urbano"]
        is_inside_urbano = (
            nw["se_lat"] <= self.user_lat <= nw["nw_lat"]
            and nw["nw_lng"] <= self.user_lng <= nw["se_lng"]
        )
        lvl_key = self.active_level
        if lvl_key == "urbano" and not is_inside_urbano and not self.is_google_maps_active():
            lvl_key = "metropolitana"
        cfg = MAP_LEVELS[lvl_key]

        def lat_to_y(lat_deg: float) -> float:
            lat_rad = math.radians(lat_deg)
            return (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0

        def lng_to_x(lng_deg: float) -> float:
            return (lng_deg + 180.0) / 360.0

        x_norm = (lng_to_x(lng) - lng_to_x(cfg["nw_lng"])) / (
            lng_to_x(cfg["se_lng"]) - lng_to_x(cfg["nw_lng"])
        )
        y_norm = (lat_to_y(lat) - lat_to_y(cfg["nw_lat"])) / (
            lat_to_y(cfg["se_lat"]) - lat_to_y(cfg["nw_lat"])
        )
        return x_norm * cfg["width"], y_norm * cfg["height"]

    def get_focus_lat_lng(self) -> tuple[float, float]:
        """Determina o ponto de foco central do mapa para manter o enquadramento ideal."""
        if self.active_level == "alagoas":
            return MAP_LEVELS["alagoas"]["center_lat"], MAP_LEVELS["alagoas"]["center_lng"]
        elif self.active_level == "metropolitana":
            # Se o usuário estiver na Grande Maceió (Satuba, Rio Largo, Maceió), foca nele!
            cfg = MAP_LEVELS["metropolitana"]
            if cfg["se_lat"] <= self.user_lat <= cfg["nw_lat"] and cfg["nw_lng"] <= self.user_lng <= cfg["se_lng"]:
                return self.user_lat, self.user_lng
            return cfg["center_lat"], cfg["center_lng"]
        else:
            nw = MAP_LEVELS["urbano"]
            is_inside_urbano = (
                nw["se_lat"] <= self.user_lat <= nw["nw_lat"]
                and nw["nw_lng"] <= self.user_lng <= nw["se_lng"]
            )
            # Se fora do quadrante sul (Farol), mantém foco fixo e preciso na posição real do usuário
            if not is_inside_urbano and not self.is_google_maps_active():
                return self.user_lat, self.user_lng
            if self.route_mode in ["phase1", "phase2"] and self.selected_bounty:
                if self.route_mode == "phase1":
                    dest_lat = self.selected_bounty.lat
                    dest_lng = self.selected_bounty.lng
                else:
                    from app.services.ecoponto_service import get_ecoponto_service
                    eco = get_ecoponto_service().get_ecoponto(self.selected_bounty.dest)
                    dest_lat = eco.lat
                    dest_lng = eco.lng
                return (self.user_lat + dest_lat) / 2.0, (self.user_lng + dest_lng) / 2.0
            return self.user_lat, self.user_lng

    def center_on_user(self, e=None):
        """Centraliza o enquadramento na posição real do usuário com visão aproximada de rua."""
        try:
            from app.services.storage_service import get_client_id, set_pending_action
            set_pending_action("request_gps", cid=get_client_id(self.page))
        except Exception:
            pass
        self.gmaps_view_state = (self.user_lat, self.user_lng, 16)
        nw = MAP_LEVELS["urbano"]
        is_inside_urbano = (
            nw["se_lat"] <= self.user_lat <= nw["nw_lat"]
            and nw["nw_lng"] <= self.user_lng <= nw["se_lng"]
        )
        self.active_level = "urbano" if is_inside_urbano else "metropolitana"
        self.zoom = 2.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._render()
        self.safe_update()

    def drag(self, dx: float, dy: float):
        """Desloca a visualização do mapa conforme o arrasto (dx, dy)."""
        self.pan(dx, dy)

    def handle_pan_update(self, e: ft.DragUpdateEvent):
        """Manipulador do evento de arrasto (drag to pan) do mouse ou toque."""
        dx = getattr(e, "delta_x", 0.0) or 0.0
        dy = getattr(e, "delta_y", 0.0) or 0.0
        if dx != 0.0 or dy != 0.0:
            self.drag(dx, dy)

    def pan(self, dx: float, dy: float, e=None):
        """Desloca a câmera horizontal e verticalmente."""
        self.pan_x += dx
        self.pan_y += dy
        self._render()
        self.safe_update()

    def lat_lng_to_xy(self, lat: float, lng: float) -> tuple[float, float]:
        """Converte coordenadas geográficas em pixels dentro da janela de visualização."""
        if self.provider == "google" and self.gmaps_view_state:
            center_lat, center_lng, g_zoom = self.gmaps_view_state
            scale = 256.0 * (2.0 ** g_zoom)

            def mercator_x(lon: float) -> float:
                return (lon + 180.0) / 360.0 * scale

            def mercator_y(lt: float) -> float:
                lat_rad = math.radians(lt)
                return (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * scale

            cx = mercator_x(center_lng)
            cy = mercator_y(center_lat)
            px = mercator_x(lng)
            py = mercator_y(lat)

            screen_x = (self.map_width / 2.0) + (px - cx)
            screen_y = (self.map_height / 2.0) + (py - cy)
            return screen_x, screen_y

        focus_lat, focus_lng = self.get_focus_lat_lng()
        fx, fy = self.lat_lng_to_base_xy(focus_lat, focus_lng)
        bx, by = self.lat_lng_to_base_xy(lat, lng)

        map_left = (self.map_width / 2.0) - (fx * self.zoom) + self.pan_x
        map_top = (self.map_height / 2.0) - (fy * self.zoom) + self.pan_y

        screen_x = map_left + (bx * self.zoom)
        screen_y = map_top + (by * self.zoom)
        return screen_x, screen_y

    def change_zoom(self, delta: float, e=None):
        """Aumenta ou diminui o zoom progressivamente de 0.6x até 6.0x sem travas."""
        new_zoom = round(self.zoom + delta, 2)
        # Limites amplos: de 0.6x (visão panorâmica) até 6.0x (detalhe máximo de rua)
        self.zoom = max(0.6, min(6.0, new_zoom))

        # Atualiza a indicação visual da aba ativa conforme o nível de ampliação
        if self.zoom >= 2.5:
            self.active_level = "urbano"
        elif self.zoom >= 1.2:
            self.active_level = "metropolitana"
        else:
            self.active_level = "alagoas"

        self._render()
        self.safe_update()

    def select_bounty(self, b: Bounty, e=None):
        self.selected_bounty = b
        if self.on_select_bounty:
            self.on_select_bounty(b)
        self._render()
        self.safe_update()

    def set_offline(self, offline: bool):
        self.simulated_offline = offline
        self._render()
        self.safe_update()

    def open_external_maps(self, e=None):
        """Abre a visualização completa ou rota oficial a pé no Google Maps."""
        from app.services.google_maps_service import get_google_maps_service
        gmaps = get_google_maps_service()
        if self.selected_bounty:
            if self.route_mode != "phase2":
                dest_lat = self.selected_bounty.lat
                dest_lng = self.selected_bounty.lng
            else:
                from app.services.ecoponto_service import get_ecoponto_service
                eco = get_ecoponto_service().get_ecoponto(self.selected_bounty.dest)
                dest_lat = eco.lat
                dest_lng = eco.lng
            url = gmaps.get_navigation_url(dest_lat, dest_lng, self.user_lat, self.user_lng)
        else:
            url = f"https://www.google.com/maps/@{self.user_lat:.6f},{self.user_lng:.6f},15z"
        if self.page:
            self.page.launch_url(url)

    def build(self):
        self._render()
        return self.root_container

    def _render(self):
        if self.simulated_offline:
            self.root_container.content = ft.Container(
                width=self.map_width,
                height=self.map_height,
                bgcolor="#e2e8f0",
                border_radius=16,
                alignment=ft.alignment.center,
                content=ft.Column(
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.icons.WIFI_OFF, color="#64748b", size=40),
                        ft.Text(
                            "Não foi possível carregar o mapa. Verifique sua conexão.",
                            color="#475569",
                            weight=ft.FontWeight.W_500,
                            size=13,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
            )
            return

        # -------------------------------------------------------------
        # PROVEDOR CARTOGRÁFICO UNIFICADO (Google Maps + OSM + Leaflet)
        # -------------------------------------------------------------
        if self.expand and self.page:
            if getattr(self.page, "height", None):
                self.map_height = max(520, int(self.page.height - 170))
            if getattr(self.page, "width", None):
                self.map_width = max(360, min(440, int(self.page.width)))

        nw = MAP_LEVELS["urbano"]
        is_inside_urbano = (
            nw["se_lat"] <= self.user_lat <= nw["nw_lat"]
            and nw["nw_lng"] <= self.user_lng <= nw["se_lng"]
        )
        lvl_key = self.active_level
        if lvl_key == "urbano" and not is_inside_urbano and not self.is_google_maps_active():
            lvl_key = "metropolitana"
        cfg = MAP_LEVELS[lvl_key]
        focus_lat, focus_lng = self.get_focus_lat_lng()
        fx, fy = self.lat_lng_to_base_xy(focus_lat, focus_lng)
        map_left = (self.map_width / 2.0) - (fx * self.zoom) + self.pan_x
        map_top = (self.map_height / 2.0) - (fy * self.zoom) + self.pan_y

        map_stack_controls = []

        # 1. Camada Base Cartográfica do Nível Ativo
        is_gmaps = self.is_google_maps_active() and (self.provider == "google")
        b64_gmap = None
        if is_gmaps:
            from app.services.google_maps_service import get_google_maps_service
            gmaps = get_google_maps_service()
            g_zoom = 12 if self.active_level == "alagoas" else (14 if self.active_level == "metropolitana" else 16)
            g_zoom = int(max(9, min(20, round(g_zoom + (self.zoom - 1.0) * 3))))

            g_center_lat = focus_lat
            g_center_lng = focus_lng
            self.gmaps_view_state = (g_center_lat, g_center_lng, g_zoom)

            b64_gmap = gmaps.fetch_static_map_base64(
                center_lat=g_center_lat,
                center_lng=g_center_lng,
                zoom=g_zoom,
                width=int(self.map_width),
                height=int(self.map_height),
            )
        else:
            self.gmaps_view_state = None

        if b64_gmap:
            map_stack_controls.append(
                ft.Container(
                    left=self.pan_x,
                    top=self.pan_y,
                    width=self.map_width,
                    height=self.map_height,
                    content=ft.Image(
                        src_base64=b64_gmap,
                        width=self.map_width,
                        height=self.map_height,
                        fit=ft.ImageFit.COVER,
                        gapless_playback=True,
                    ),
                )
            )
        else:
            b64_map = get_map_base64(cfg["file"])
            img_w = cfg["width"] * self.zoom
            img_h = cfg["height"] * self.zoom

            map_stack_controls.append(
                ft.Container(
                    left=map_left,
                    top=map_top,
                    width=img_w,
                    height=img_h,
                    content=ft.Image(
                        src_base64=b64_map if b64_map else None,
                        src=cfg["file"] if not b64_map else None,
                        width=img_w,
                        height=img_h,
                        fit=ft.ImageFit.FILL,
                        gapless_playback=True,
                    ),
                )
            )

        # 2. Camada Vetorial de Rotas (Canvas com suporte a Curvas de Ruas)
        ux, uy = self.lat_lng_to_xy(self.user_lat, self.user_lng)
        canvas_shapes = []

        if self.selected_bounty:
            from app.services.google_maps_service import get_google_maps_service
            gmaps = get_google_maps_service()

            if self.route_mode == "phase2":
                from app.services.ecoponto_service import get_ecoponto_service
                eco = get_ecoponto_service().get_ecoponto(self.selected_bounty.dest)
                route_res = gmaps.compute_walking_route(
                    self.selected_bounty.lat, self.selected_bounty.lng, eco.lat, eco.lng
                )
                pts = (
                    route_res.get("polyline_points")
                    if route_res
                    else [(self.selected_bounty.lat, self.selected_bounty.lng), (eco.lat, eco.lng)]
                )
                glow_col = "#93c5fd"
                core_col = "#2563eb"
            else:
                route_res = gmaps.compute_walking_route(
                    self.user_lat, self.user_lng, self.selected_bounty.lat, self.selected_bounty.lng
                )
                pts = (
                    route_res.get("polyline_points")
                    if route_res
                    else [(self.user_lat, self.user_lng), (self.selected_bounty.lat, self.selected_bounty.lng)]
                )
                glow_col = "#60a5fa"
                core_col = "#2563eb" if self.route_mode == "phase1" else "#059669"

            # Desenha os segmentos curvos de rua
            for i in range(len(pts) - 1):
                p1_x, p1_y = self.lat_lng_to_xy(pts[i][0], pts[i][1])
                p2_x, p2_y = self.lat_lng_to_xy(pts[i + 1][0], pts[i + 1][1])
                if math.dist((p1_x, p1_y), (p2_x, p2_y)) > 1:
                    # Linha de brilho
                    canvas_shapes.append(
                        cv.Line(
                            p1_x,
                            p1_y,
                            p2_x,
                            p2_y,
                            paint=ft.Paint(
                                color=glow_col,
                                stroke_width=6,
                                style=ft.PaintingStyle.STROKE,
                                stroke_cap=ft.StrokeCap.ROUND,
                            ),
                        )
                    )
                    # Linha sólida central
                    canvas_shapes.append(
                        cv.Line(
                            p1_x,
                            p1_y,
                            p2_x,
                            p2_y,
                            paint=ft.Paint(
                                color=core_col,
                                stroke_width=3,
                                style=ft.PaintingStyle.STROKE,
                                stroke_cap=ft.StrokeCap.ROUND,
                            ),
                        )
                    )

        map_stack_controls.append(
            cv.Canvas(
                shapes=canvas_shapes,
                width=self.map_width,
                height=self.map_height,
            )
        )

        # 3. Camada Interativa de Arrasto (Drag-to-Pan com suporte a Mouse e Touch)
        self.drag_gesture.content.width = self.map_width
        self.drag_gesture.content.height = self.map_height
        map_stack_controls.append(self.drag_gesture)

        # 4. Marcador do Usuário (Coletor)
        is_at_location = False
        if self.selected_bounty and self.route_mode in ["phase1", "phase2"]:
            target_bx, target_by = self.lat_lng_to_xy(
                self.selected_bounty.lat, self.selected_bounty.lng
            )
            if math.dist((ux, uy), (target_bx, target_by)) < 12:
                is_at_location = True

        pin_size = 28 if self.active_level == "urbano" else 22
        pin_half = pin_size / 2.0

        if is_at_location:
            map_stack_controls.append(
                ft.Container(
                    left=ux - 24,
                    top=uy - 24,
                    width=48,
                    height=48,
                    border=ft.border.all(3, "#3b82f6"),
                    border_radius=24,
                    bgcolor=ft.colors.with_opacity(0.2, "#3b82f6"),
                    tooltip="Você está no local exato da missão!",
                )
            )
        else:
            map_stack_controls.append(
                ft.Container(
                    left=max(0, min(self.map_width - pin_size, ux - pin_half)),
                    top=max(0, min(self.map_height - pin_size, uy - pin_half)),
                    width=pin_size,
                    height=pin_size,
                    bgcolor="#2563eb",
                    border=ft.border.all(2, "#ffffff"),
                    border_radius=pin_half,
                    shadow=ft.BoxShadow(spread_radius=2, blur_radius=8, color="#3b82f6"),
                    alignment=ft.alignment.center,
                    tooltip=f"Você está aqui ({self.user_lat:.4f}, {self.user_lng:.4f})",
                    content=ft.Icon(
                        ft.icons.PERSON_PIN_CIRCLE,
                        size=16 if self.active_level == "urbano" else 13,
                        color="white",
                    ),
                )
            )

        # 4. Marcadores de Bounties (Foco de resíduos com ícone de moeda $)
        if self.route_mode != "phase2":
            b_size = 36 if self.active_level == "urbano" else 26
            b_half = b_size / 2.0
            for b in self.bounties:
                bx, by = self.lat_lng_to_xy(b.lat, b.lng)
                if not (-50 <= bx <= self.map_width + 50 and -50 <= by <= self.map_height + 50):
                    continue
                is_selected = self.selected_bounty and self.selected_bounty.id == b.id
                bg_color = "#059669" if is_selected else "#0f172a"

                map_stack_controls.append(
                    ft.Container(
                        left=bx - b_half,
                        top=by - b_half,
                        width=b_size,
                        height=b_size,
                        bgcolor=bg_color,
                        border=ft.border.all(2, "#ffffff"),
                        border_radius=b_half,
                        shadow=ft.BoxShadow(spread_radius=1, blur_radius=6, color="#334155"),
                        alignment=ft.alignment.center,
                        on_click=lambda e, bounty=b: self.select_bounty(bounty, e),
                        content=ft.Text(
                            "$",
                            color="white",
                            weight=ft.FontWeight.BOLD,
                            size=14 if self.active_level == "urbano" else 11,
                        ),
                    )
                )

        # 5. Marcador da Fase 2 (Ecoponto / Cooperativa com bandeira azul e local exato)
        if self.route_mode == "phase2" and self.selected_bounty:
            from app.services.ecoponto_service import get_ecoponto_service
            eco = get_ecoponto_service().get_ecoponto(self.selected_bounty.dest)
            ex, ey = self.lat_lng_to_xy(eco.lat, eco.lng)
            map_stack_controls.append(
                ft.Container(
                    left=max(0, min(self.map_width - 36, ex - 18)),
                    top=max(0, min(self.map_height - 36, ey - 18)),
                    width=36,
                    height=36,
                    bgcolor="#2563eb",
                    border=ft.border.all(2, "#ffffff"),
                    border_radius=18,
                    alignment=ft.alignment.center,
                    tooltip=f"Destino Homologado: {eco.name} ({eco.neighborhood})",
                    content=ft.Icon(ft.icons.FLAG, color="white", size=18),
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=6, color="#1d4ed8"),
                )
            )

        # 6. Barra Superior de Seleção de Escala (Alagoas | Grande Maceió | Ruas)
        scale_tabs = []
        for key, name in [
            ("alagoas", "🗺️ Alagoas"),
            ("metropolitana", "📍 Metrópole"),
            ("urbano", "🔍 Ruas"),
        ]:
            is_active = self.active_level == key
            scale_tabs.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=6,
                    bgcolor="#059669" if is_active else "#ffffff",
                    shadow=ft.BoxShadow(blur_radius=3, color="#94a3b8") if is_active else None,
                    on_click=lambda e, lvl=key: self.set_level(lvl, e),
                    content=ft.Text(
                        name,
                        size=10,
                        weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.W_500,
                        color="white" if is_active else "#1e293b",
                    ),
                )
            )

        is_real_gmaps = self.is_google_maps_active() and (self.provider == "google")
        gmaps_badge = ft.Container(
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=6,
            bgcolor="#2563eb" if is_real_gmaps else "#059669",
            tooltip="Abrir Mapa Interativo Completo",
            on_click=self.open_leaflet_interactive,
            content=ft.Row(
                spacing=4,
                controls=[
                    ft.Icon(ft.icons.MAP if is_real_gmaps else ft.icons.TRAVEL_EXPLORE, size=12, color="white"),
                    ft.Text(
                        "Google Maps" if is_real_gmaps else "OpenStreetMap",
                        size=10,
                        weight=ft.FontWeight.BOLD,
                        color="white",
                    ),
                ],
            ),
        )

        map_stack_controls.append(
            ft.Container(
                top=10,
                left=10,
                bgcolor=ft.colors.with_opacity(0.85, "#ffffff"),
                border_radius=8,
                padding=3,
                shadow=ft.BoxShadow(blur_radius=4, color="#94a3b8"),
                content=ft.Row(spacing=4, controls=[gmaps_badge, *scale_tabs]),
            )
        )

        # Banner Flutuante de Atalho para o Modo Interativo HD (Leaflet + Ruas)
        map_stack_controls.append(
            ft.Container(
                top=46,
                left=10,
                bgcolor=ft.colors.with_opacity(0.92, "#0f172a"),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=5),
                shadow=ft.BoxShadow(blur_radius=6, color="#334155"),
                on_click=self.open_leaflet_interactive,
                tooltip="Navegar no Mapa Interativo HD com OpenStreetMap e Satélite",
                content=ft.Row(
                    tight=True,
                    spacing=6,
                    controls=[
                        ft.Icon(ft.icons.EXPLORE, color="#34d399", size=14),
                        ft.Text(
                            "Modo Interativo HD (Ruas)",
                            color="white",
                            weight=ft.FontWeight.BOLD,
                            size=10,
                        ),
                    ],
                ),
            )
        )

        # 7. Controles de Zoom e Navegação Direita (+ / - / 🎯 / 🗺️ / 🌐)
        map_stack_controls.append(
            ft.Container(
                top=50,
                right=10,
                bgcolor="#ffffff",
                border_radius=8,
                shadow=ft.BoxShadow(blur_radius=4, color="#94a3b8"),
                content=ft.Column(
                    spacing=0,
                    controls=[
                        ft.IconButton(
                            icon=ft.icons.ADD,
                            icon_size=18,
                            tooltip="Aumentar Zoom (+0.35x)",
                            on_click=lambda e: self.change_zoom(0.35, e),
                        ),
                        ft.IconButton(
                            icon=ft.icons.REMOVE,
                            icon_size=18,
                            tooltip="Diminuir Zoom (-0.35x)",
                            on_click=lambda e: self.change_zoom(-0.35, e),
                        ),
                        ft.Container(height=1, bgcolor="#e2e8f0"),
                        ft.IconButton(
                            icon=ft.icons.MY_LOCATION,
                            icon_size=18,
                            icon_color="#059669",
                            tooltip="Centralizar na Minha Posição (Ruas)",
                            on_click=self.center_on_user,
                        ),
                        ft.IconButton(
                            icon=ft.icons.MAP_OUTLINED,
                            icon_size=18,
                            icon_color="#059669",
                            tooltip="Abrir Mapa Interativo de Ruas (OpenStreetMap / Satélite)",
                            on_click=self.open_leaflet_interactive,
                        ),
                        ft.IconButton(
                            icon=ft.icons.OPEN_IN_NEW,
                            icon_size=18,
                            icon_color="#2563eb",
                            tooltip="Abrir no Google Maps Oficial",
                            on_click=self.open_external_maps,
                        ),
                    ],
                ),
            )
        )

        # 8. Card Flutuante de Detalhes do Bounty Selecionado (somente na Home / route_mode=="none")
        if self.selected_bounty and self.route_mode == "none":
            b = self.selected_bounty
            map_stack_controls.append(
                ft.Container(
                    bottom=16,
                    left=20,
                    right=20,
                    bgcolor="#ffffff",
                    border_radius=16,
                    padding=12,
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color="#64748b"),
                    border=ft.border.all(1, "#e2e8f0"),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Text(b.title, weight=ft.FontWeight.BOLD, size=13, color="#1e293b"),
                                    ft.Text(
                                        f"{b.formatted_value()} • {b.formatted_distance()}",
                                        color="#059669",
                                        weight=ft.FontWeight.BOLD,
                                        size=12,
                                    ),
                                ],
                            ),
                            ft.ElevatedButton(
                                "Ver Missão",
                                bgcolor="#059669",
                                color="white",
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                                ),
                                on_click=lambda e: self.on_open_details(b) if self.on_open_details else None,
                            ),
                        ],
                    ),
                )
            )

        # 9. Atribuição Cartográfica
        attr_text = "© Google Maps" if is_real_gmaps else "© OpenStreetMap contributors"
        map_stack_controls.append(
            ft.Container(
                bottom=4,
                right=8,
                bgcolor=ft.colors.with_opacity(0.75, "#ffffff"),
                padding=ft.padding.symmetric(horizontal=4, vertical=1),
                border_radius=4,
                content=ft.Text(
                    attr_text,
                    size=9,
                    color="#475569",
                    weight=ft.FontWeight.W_500,
                ),
            )
        )

        self.root_container.content = ft.Stack(controls=map_stack_controls)
