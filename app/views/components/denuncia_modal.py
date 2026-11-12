"""Modal de Denúncia Cidadã de Lixo Irregular (UC10)."""
from typing import Callable, Optional
import flet as ft


class DenunciaModal:
    @staticmethod
    def show(
        page: ft.Page,
        on_open_camera: Callable[[], None],
        on_cancel: Optional[Callable[[], None]] = None,
    ):
        bottom_sheet = None

        def handle_cancel(e):
            bottom_sheet.open = False
            if bottom_sheet in page.overlay:
                page.overlay.remove(bottom_sheet)
            page.update()
            if on_cancel:
                on_cancel()

        def handle_camera(e):
            bottom_sheet.open = False
            if bottom_sheet in page.overlay:
                page.overlay.remove(bottom_sheet)
            page.update()
            on_open_camera()

        content = ft.Container(
            padding=24,
            bgcolor="white",
            border_radius=ft.border_radius.only(top_left=24, top_right=24),
            content=ft.Column(
                tight=True,
                spacing=16,
                controls=[
                    # Puxador decorativo
                    ft.Container(
                        width=48,
                        height=5,
                        bgcolor="#cbd5e1",
                        border_radius=3,
                        alignment=ft.alignment.center,
                    ),
                    # Cabeçalho com ícone de pin
                    ft.Row(
                        spacing=12,
                        controls=[
                            ft.Container(
                                width=48,
                                height=48,
                                border_radius=24,
                                bgcolor="#d1fae5",
                                alignment=ft.alignment.center,
                                content=ft.Icon(ft.icons.LOCATION_ON, color="#059669", size=26),
                            ),
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Text("Nova Denúncia", size=18, weight=ft.FontWeight.BOLD, color="#1e293b"),
                                    ft.Text("Mapeie um descarte irregular", size=13, color="#64748b"),
                                ],
                            ),
                        ],
                    ),
                    # Texto explicativo
                    ft.Container(
                        bgcolor="#f8fafc",
                        border=ft.border.all(1, "#f1f5f9"),
                        border_radius=12,
                        padding=12,
                        content=ft.Text(
                            "Ao fotografar um lixo na rua, a nossa IA analisa a gravidade e cria "
                            "uma nova missão (Bounty) para que outra pessoa limpe.",
                            size=13,
                            color="#475569",
                        ),
                    ),
                    # Ações
                    ft.Column(
                        spacing=8,
                        controls=[
                            ft.ElevatedButton(
                                content=ft.Row(
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=8,
                                    controls=[
                                        ft.Icon(ft.icons.CAMERA_ALT, color="white", size=18),
                                        ft.Text("Abrir Câmera", color="white", weight=ft.FontWeight.BOLD),
                                    ],
                                ),
                                bgcolor="#059669",
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=ft.padding.symmetric(vertical=14),
                                ),
                                on_click=handle_camera,
                            ),
                            ft.TextButton(
                                "Cancelar",
                                style=ft.ButtonStyle(
                                    color="#64748b",
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=ft.padding.symmetric(vertical=12),
                                ),
                                on_click=handle_cancel,
                            ),
                        ],
                    ),
                ],
            ),
        )

        bottom_sheet = ft.BottomSheet(content=content, open=True)
        page.overlay.append(bottom_sheet)
        page.update()
