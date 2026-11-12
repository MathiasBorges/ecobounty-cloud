"""Tela de Detalhes da Missão e Regra 50/50 (UC06, UC07)."""
from typing import Callable, Optional
import flet as ft

from app.models.bounty import Bounty
from app.models.user import User
from app.services.bounty_service import BountyService


class MissionView(ft.UserControl):
    def __init__(
        self,
        bounty: Bounty,
        user: User,
        bounty_service: BountyService,
        on_back: Callable[[], None],
        on_start_mission: Callable[[Bounty], None],
    ):
        super().__init__()
        self.bounty = bounty
        self.user = user
        self.bounty_service = bounty_service
        self.on_back = on_back
        self.on_start_mission = on_start_mission
        self.error_message: Optional[str] = None
        self.root_container = ft.Container(expand=True, bgcolor="#ffffff")

    def safe_update(self):
        try:
            if self.page:
                self.update()
        except Exception:
            pass

    def handle_accept(self, e):
        ok, msg = self.bounty_service.accept_bounty(self.bounty.id, self.user.id)
        if ok:
            self.on_start_mission(self.bounty)
        else:
            self.error_message = msg
            self._render()
            self.safe_update()

    def build(self):
        self._render()
        return self.root_container

    def _render(self):
        # Verifica se está reservada por outro coletor
        is_locked_by_other = (
            self.bounty.status == "EM_ANDAMENTO" and self.bounty.assigned_user_id != self.user.id
        )

        # Imagem de Cabeçalho com Overlay
        from app.services.storage_service import get_image_base64
        b64_bounty_img = get_image_base64(self.bounty.img)
        header_image = ft.Container(
            height=240,
            bgcolor="#1e293b",
            content=ft.Stack(
                controls=[
                    # Imagem do resíduo (com fallback automático de imagem)
                    ft.Image(
                        src=self.bounty.img if not b64_bounty_img else None,
                        src_base64=b64_bounty_img,
                        width=420,
                        height=240,
                        fit=ft.ImageFit.COVER,
                        opacity=0.85,
                        error_content=ft.Container(
                            alignment=ft.alignment.center,
                            bgcolor="#334155",
                            content=ft.Column(
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Icon(ft.icons.IMAGE_NOT_SUPPORTED, color="#94a3b8", size=48),
                                    ft.Text("Lixo", color="#cbd5e1", size=14, weight=ft.FontWeight.BOLD),
                                ],
                            ),
                        ),
                    ),
                    # Botão Voltar (Canto superior esquerdo)
                    ft.Container(
                        top=16,
                        left=16,
                        content=ft.IconButton(
                            icon=ft.icons.ARROW_BACK,
                            icon_color="white",
                            bgcolor="#475569",
                            icon_size=20,
                            on_click=lambda e: self.on_back(),
                        ),
                    ),
                    # Barra Inferior da Imagem (Selo IA + Valor)
                    ft.Container(
                        bottom=16,
                        left=16,
                        right=16,
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.END,
                            controls=[
                                # Selo IA
                                ft.Container(
                                    bgcolor="#059669",
                                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                                    border_radius=20,
                                    content=ft.Row(
                                        spacing=4,
                                        controls=[
                                            ft.Icon(ft.icons.CHECK_CIRCLE, color="white", size=14),
                                            ft.Text("Validado por IA", color="white", size=11, weight=ft.FontWeight.BOLD),
                                        ],
                                    ),
                                ),
                                # Valor R$
                                ft.Text(
                                    self.bounty.formatted_value(),
                                    color="white",
                                    size=26,
                                    weight=ft.FontWeight.W_900,
                                ),
                            ],
                        ),
                    ),
                ]
            ),
        )

        # Informações e Regra 50/50
        body_content = ft.Container(
            expand=True,
            padding=20,
            bgcolor="#f8fafc",
            content=ft.Column(
                scroll=ft.ScrollMode.AUTO,
                spacing=16,
                controls=[
                    # Título e Distância
                    ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text(self.bounty.title, size=20, weight=ft.FontWeight.BOLD, color="#1e293b"),
                            ft.Row(
                                spacing=4,
                                controls=[
                                    ft.Icon(ft.icons.LOCATION_ON, color="#059669", size=16),
                                    ft.Text(
                                        f"{self.bounty.formatted_distance()} de distância",
                                        size=13,
                                        color="#64748b",
                                        weight=ft.FontWeight.W_500,
                                    ),
                                ],
                            ),
                        ],
                    ),
                    # Grid: Destino Exigido + Patrocinador ESG
                    ft.Row(
                        spacing=12,
                        controls=[
                            ft.Container(
                                expand=True,
                                bgcolor="#ffffff",
                                padding=14,
                                border_radius=14,
                                border=ft.border.all(1, "#f1f5f9"),
                                content=ft.Column(
                                    spacing=4,
                                    controls=[
                                        ft.Text("Destino Exigido", size=11, color="#64748b", weight=ft.FontWeight.W_500),
                                        ft.Text(self.bounty.dest, size=14, weight=ft.FontWeight.BOLD, color="#1e293b"),
                                    ],
                                ),
                            ),
                            ft.Container(
                                expand=True,
                                bgcolor="#ffffff",
                                padding=14,
                                border_radius=14,
                                border=ft.border.all(1, "#f1f5f9"),
                                content=ft.Column(
                                    spacing=4,
                                    controls=[
                                        ft.Text("Patrocinador ESG", size=11, color="#64748b", weight=ft.FontWeight.W_500),
                                        ft.Text(self.bounty.sponsor, size=14, weight=ft.FontWeight.BOLD, color="#1e293b"),
                                    ],
                                ),
                            ),
                        ],
                    ),
                    # Banner de Informação da Regra de Pagamento 50/50
                    ft.Container(
                        bgcolor="#eff6ff",
                        border=ft.border.all(1, "#bfdbfe"),
                        border_radius=14,
                        padding=14,
                        content=ft.Row(
                            spacing=12,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.Icon(ft.icons.INFO_OUTLINE, color="#2563eb", size=22),
                                ft.Column(
                                    expand=True,
                                    spacing=4,
                                    controls=[
                                        ft.Text("Regra de Pagamento 50/50", size=13, weight=ft.FontWeight.BOLD, color="#1e3a8a"),
                                        ft.Text(
                                            "Você recebe 50% ao limpar o local e tirar a foto, "
                                            "e os outros 50% ao entregar no destino indicado.",
                                            size=12,
                                            color="#1d4ed8",
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ),
                    # Mensagem de Erro (se houver)
                    *(
                        [ft.Text(self.error_message, color="#dc2626", size=13, weight=ft.FontWeight.BOLD)]
                        if self.error_message
                        else []
                    ),
                ],
            ),
        )

        # Botão de Ação Inferior
        btn_accept = ft.ElevatedButton(
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
                controls=[
                    ft.Text(
                        "Missão indisponível – já aceita por outro coletor"
                        if is_locked_by_other
                        else "Aceitar Missão",
                        color="white",
                        weight=ft.FontWeight.BOLD,
                        size=15,
                    ),
                    *(
                        [ft.Icon(ft.icons.ARROW_FORWARD, color="white", size=18)]
                        if not is_locked_by_other
                        else []
                    ),
                ],
            ),
            bgcolor="#64748b" if is_locked_by_other else "#0f172a",
            disabled=is_locked_by_other,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=14),
                padding=ft.padding.symmetric(vertical=16),
            ),
            on_click=self.handle_accept,
        )

        bottom_action = ft.Container(
            bgcolor="#ffffff",
            padding=16,
            border=ft.border.only(top=ft.BorderSide(1, "#f1f5f9")),
            content=btn_accept,
        )

        self.root_container.content = ft.Column(
            spacing=0,
            controls=[
                header_image,
                body_content,
                bottom_action,
            ],
        )
