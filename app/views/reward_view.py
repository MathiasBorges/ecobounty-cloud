"""Tela de Recompensa e Sucesso (UC08, UC09, UC10)."""
from typing import Callable, Optional
import flet as ft


class RewardView(ft.UserControl):
    def __init__(
        self,
        title: str,
        subtitle: str,
        amount: Optional[float] = None,
        percentage_label: Optional[str] = None,
        button_label: str = "Continuar",
        image_url: Optional[str] = None,
        ai_audit_info: Optional[dict] = None,
        on_action: Optional[Callable[[], None]] = None,
    ):
        super().__init__()
        self.title_text = title
        self.subtitle_text = subtitle
        self.amount = amount
        self.percentage_label = percentage_label
        self.button_label = button_label
        self.image_url = image_url
        self.ai_audit_info = ai_audit_info
        self.on_action = on_action

    def safe_update(self):
        if self.page:
            self.update()

    def build(self):
        formatted_amount = (
            f"+ R$ {self.amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if self.amount is not None
            else None
        )

        reward_card = (
            ft.Container(
                bgcolor="#047857",
                border=ft.border.all(1, "#10b981"),
                border_radius=18,
                padding=20,
                width=340,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=6,
                    controls=[
                        ft.Text(
                            "VALOR CREDITADO",
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color="#a7f3d0",
                        ),
                        ft.Text(
                            formatted_amount,
                            size=34,
                            weight=ft.FontWeight.W_900,
                            color="white",
                        ),
                        ft.Text(
                            self.percentage_label or "Recompensa EcoBounty",
                            size=12,
                            color="#d1fae5",
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                ),
            )
            if self.amount is not None
            else ft.Container(height=0)
        )

        img_src = None
        img_src_b64 = None

        if self.image_url:
            raw_url = str(self.image_url).strip()
            if raw_url.startswith("data:"):
                # Data URL com prefixo base64
                img_src_b64 = raw_url.split(",", 1)[-1].strip()
            elif raw_url.startswith("http://") or raw_url.startswith("https://"):
                img_src = raw_url
            else:
                # Caminho de arquivo local ou relativo
                from pathlib import Path
                from app.config import UPLOADS_DIR
                from app.services.storage_service import get_image_base64
                import base64

                b64_val = get_image_base64(raw_url)
                if b64_val:
                    img_src_b64 = b64_val.split(",", 1)[-1].strip()
                else:
                    # Tenta ler do caminho direto ou do diretório de uploads
                    p = Path(raw_url)
                    cand_paths = [p, UPLOADS_DIR / p.name, UPLOADS_DIR / raw_url]
                    for cand in cand_paths:
                        if cand.exists() and cand.is_file():
                            try:
                                with open(cand, "rb") as f:
                                    img_src_b64 = base64.b64encode(f.read()).decode("ascii")
                                break
                            except Exception:
                                pass
                if not img_src_b64:
                    img_src = raw_url

        # Se tiver base64, prioriza src_base64; caso contrário usa o src original
        img_control = ft.Image(
            src=img_src if not img_src_b64 else None,
            src_base64=img_src_b64,
            fit=ft.ImageFit.COVER,
            width=320,
            height=160,
            gapless_playback=True,
        )

        image_preview = (
            ft.Container(
                width=320,
                height=160,
                border_radius=14,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                border=ft.border.all(2, "#34d399"),
                bgcolor="#064e3b",
                content=ft.Stack(
                    controls=[
                        img_control,
                        ft.Container(
                            top=8,
                            left=8,
                            bgcolor="rgba(15, 23, 42, 0.75)",
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            border_radius=8,
                            content=ft.Row(
                                tight=True,
                                spacing=4,
                                controls=[
                                    ft.Icon(ft.icons.PHOTO_CAMERA, color="#34d399", size=13),
                                    ft.Text("Foto Registrada", color="white", size=10, weight=ft.FontWeight.BOLD),
                                ],
                            ),
                        ),
                    ]
                ),
            )
            if self.image_url
            else ft.Container(height=0)
        )

        # Cartão de Julgamento / Análise da IA
        ai_card = None
        if self.ai_audit_info:
            w_type = self.ai_audit_info.get("waste_type", "Plástico")
            w_dest = self.ai_audit_info.get("dest", "COOPLUM")
            w_val = self.ai_audit_info.get("estimated_value", 25.0)
            w_msg = self.ai_audit_info.get("message") or f"Resíduo de {w_type} identificado e homologado."
            prov = self.ai_audit_info.get("provider", "IA EcoBounty")

            ai_card = ft.Container(
                bgcolor="rgba(15, 23, 42, 0.35)",
                border=ft.border.all(1, "rgba(255, 255, 255, 0.25)"),
                border_radius=14,
                padding=12,
                width=340,
                content=ft.Column(
                    spacing=6,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Row(
                                    spacing=6,
                                    controls=[
                                        ft.Icon(ft.icons.SMART_TOY, color="#34d399", size=15),
                                        ft.Text("Julgamento da IA", size=11, weight=ft.FontWeight.BOLD, color="#a7f3d0"),
                                    ],
                                ),
                                ft.Container(
                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                    border_radius=6,
                                    bgcolor="rgba(52, 211, 153, 0.2)",
                                    content=ft.Text(prov, size=9, weight=ft.FontWeight.BOLD, color="#a7f3d0"),
                                ),
                            ],
                        ),
                        ft.Text(
                            w_msg,
                            size=12,
                            color="white",
                            weight=ft.FontWeight.W_500,
                        ),
                        ft.Row(
                            spacing=6,
                            controls=[
                                ft.Container(
                                    bgcolor="rgba(5, 150, 105, 0.6)",
                                    padding=ft.padding.symmetric(horizontal=7, vertical=3),
                                    border_radius=6,
                                    content=ft.Text(f"Material: {w_type}", size=10, color="white", weight=ft.FontWeight.BOLD),
                                ),
                                ft.Container(
                                    bgcolor="rgba(37, 99, 235, 0.6)",
                                    padding=ft.padding.symmetric(horizontal=7, vertical=3),
                                    border_radius=6,
                                    content=ft.Text(f"Destino: {w_dest}", size=10, color="white", weight=ft.FontWeight.BOLD),
                                ),
                                ft.Container(
                                    bgcolor="rgba(217, 119, 6, 0.6)",
                                    padding=ft.padding.symmetric(horizontal=7, vertical=3),
                                    border_radius=6,
                                    content=ft.Text(f"R$ {float(w_val):.2f}", size=10, color="white", weight=ft.FontWeight.BOLD),
                                ),
                            ],
                        ),
                    ],
                ),
            )

        return ft.Container(
            expand=True,
            bgcolor="#059669",
            padding=ft.padding.symmetric(horizontal=24, vertical=40),
            alignment=ft.alignment.center,
            content=ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
                controls=[
                    # Ícone de Sucesso com círculo branco
                    ft.Container(
                        width=80,
                        height=80,
                        border_radius=40,
                        bgcolor="white",
                        alignment=ft.alignment.center,
                        shadow=ft.BoxShadow(spread_radius=4, blur_radius=20, color="#065f46"),
                        content=ft.Icon(ft.icons.CHECK, color="#059669", size=44),
                    ),
                    ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                        controls=[
                            ft.Text(
                                self.title_text,
                                size=26,
                                weight=ft.FontWeight.BOLD,
                                color="white",
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                self.subtitle_text,
                                size=13,
                                color="#d1fae5",
                                weight=ft.FontWeight.W_500,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                    ),
                    image_preview,
                    *( [ai_card] if ai_card else [] ),
                    reward_card,
                    ft.Container(height=8),
                    ft.ElevatedButton(
                        self.button_label,
                        width=340,
                        bgcolor="white",
                        color="#065f46",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=14),
                            padding=ft.padding.symmetric(vertical=16),
                        ),
                        on_click=lambda e: self.on_action() if self.on_action else None,
                    ),
                ],
            ),
        )
