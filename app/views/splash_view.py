"""Tela de Splash inicial (EcoBounty)."""
import threading
import time
from typing import Callable
import flet as ft


class SplashView(ft.UserControl):
    def __init__(self, on_finish: Callable[[], None]):
        super().__init__()
        self.on_finish = on_finish
        self._finished = False

    def trigger_finish(self):
        if not self._finished:
            self._finished = True
            self.on_finish()

    def did_mount(self):
        # Transição automática após 1.5s conforme especificação UC01 FP2
        def timer():
            time.sleep(1.5)
            self.trigger_finish()

        threading.Thread(target=timer, daemon=True).start()

    def build(self):
        return ft.Container(
            expand=True,
            bgcolor="#059669",
            alignment=ft.alignment.center,
            on_click=lambda e: self.trigger_finish(),
            content=ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
                controls=[
                    ft.Icon(ft.icons.ECO, color="white", size=72),
                    ft.Text(
                        "EcoBounty",
                        color="white",
                        size=38,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        "Economia Circular Gamificada",
                        color="#d1fae5",
                        size=15,
                        weight=ft.FontWeight.W_500,
                    ),
                ],
            ),
        )
