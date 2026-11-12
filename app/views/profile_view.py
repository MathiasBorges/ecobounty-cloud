"""Tela de Perfil do Coletor, Histórico e Gamificação (UC11)."""
from typing import Callable
import flet as ft

from app.models.user import User
from app.services.auth_service import AuthService
from app.services.wallet_service import WalletService


class ProfileView(ft.UserControl):
    def __init__(
        self,
        user: User,
        auth_service: AuthService,
        wallet_service: WalletService,
        on_back: Callable[[], None],
        on_logout: Callable[[], None],
    ):
        super().__init__()
        self.user = user
        self.auth_service = auth_service
        self.wallet_service = wallet_service
        self.on_back = on_back
        self.on_logout = on_logout

    def safe_update(self):
        if self.page:
            self.update()

    def build_history_item(self, item) -> ft.Control:
        return ft.Container(
            bgcolor="#ffffff",
            border_radius=14,
            padding=14,
            border=ft.border.all(1, "#f1f5f9"),
            shadow=ft.BoxShadow(blur_radius=4, color="#f8fafc"),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=12,
                        controls=[
                            ft.Container(
                                width=38,
                                height=38,
                                border_radius=19,
                                bgcolor="#d1fae5",
                                alignment=ft.alignment.center,
                                content=ft.Icon(ft.icons.CHECK, color="#059669", size=20),
                            ),
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Text(item.title, size=13, weight=ft.FontWeight.BOLD, color="#1e293b"),
                                    ft.Text(item.date_label, size=11, color="#64748b"),
                                ],
                            ),
                        ],
                    ),
                    ft.Text(
                        item.formatted_amount(),
                        color="#059669",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
            ),
        )

    def open_pix_transfer_dialog(self, e=None):
        """Abre modal de transferência/saque Pix via Mercado Pago Sandbox."""
        if not self.page:
            return

        curr_balance = self.wallet_service.get_balance(self.user.id)
        formatted_bal = f"R$ {curr_balance:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        pix_type_dd = ft.Dropdown(
            label="Tipo de Chave Pix",
            value="E-mail",
            options=[
                ft.dropdown.Option("CPF"),
                ft.dropdown.Option("E-mail"),
                ft.dropdown.Option("Telefone"),
                ft.dropdown.Option("Chave Aleatória"),
            ],
            border_radius=10,
            text_size=13,
        )
        pix_key_field = ft.TextField(
            label="Chave Pix de Destino",
            value=self.user.email or "",
            hint_text="Ex.: CPF, e-mail ou telefone",
            border_radius=10,
            text_size=13,
        )
        amount_field = ft.TextField(
            label="Valor a Transferir (R$)",
            value=f"{curr_balance:.2f}" if curr_balance > 0 else "0.00",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=10,
            text_size=13,
        )
        feedback_text = ft.Text("", size=12, color="#dc2626", visible=False)

        def confirm_transfer(ev):
            try:
                val = float((amount_field.value or "0").replace(",", ".").strip())
            except ValueError:
                feedback_text.value = "Informe um valor numérico válido."
                feedback_text.visible = True
                self.page.update()
                return

            ok, new_bal, msg, mp_info = self.wallet_service.withdraw_pix(
                user_id=self.user.id,
                amount=val,
                pix_key=pix_key_field.value or "",
                pix_key_type=pix_type_dd.value or "E-mail",
            )
            if not ok:
                feedback_text.value = msg
                feedback_text.visible = True
                self.page.update()
                return

            self.user.balance = new_bal
            self.page.dialog.open = False
            self.page.snack_bar = ft.SnackBar(
                content=ft.Row(
                    spacing=8,
                    controls=[
                        ft.Icon(ft.icons.CHECK_CIRCLE, color="white", size=18),
                        ft.Text(msg, size=12),
                    ],
                ),
                bgcolor="#009ee3",
                duration=4000,
            )
            self.page.snack_bar.open = True
            if hasattr(self, "root_container"):
                self._render_into_root()
            self.safe_update()
            self.page.update()

        def close_dlg(ev):
            self.page.dialog.open = False
            self.page.update()

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.icons.PIX, color="#009ee3", size=22),
                    ft.Text("Transferir via Pix (Mercado Pago)", size=16, weight=ft.FontWeight.BOLD),
                ],
            ),
            content=ft.Container(
                width=330,
                content=ft.Column(
                    tight=True,
                    spacing=12,
                    controls=[
                        ft.Container(
                            bgcolor="#e0f2fe",
                            border_radius=10,
                            padding=10,
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text("Saldo Disponível:", size=12, color="#0369a1", weight=ft.FontWeight.W_600),
                                    ft.Text(formatted_bal, size=14, color="#0369a1", weight=ft.FontWeight.BOLD),
                                ],
                            ),
                        ),
                        pix_type_dd,
                        pix_key_field,
                        amount_field,
                        feedback_text,
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dlg),
                ft.ElevatedButton(
                    "Confirmar Pix Sandbox",
                    bgcolor="#009ee3",
                    color="white",
                    on_click=confirm_transfer,
                ),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    def open_deposit_esg_dialog(self, e=None):
        """Abre modal para Patrocinador/Ecoponto adicionar Fundo ESG via Pix no Mercado Pago Sandbox."""
        if not self.page:
            return

        amount_field = ft.TextField(
            label="Valor do Aporte ESG (R$)",
            value="100.00",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=10,
            text_size=13,
        )
        feedback_text = ft.Text("", size=12, color="#dc2626", visible=False)

        def confirm_deposit(ev):
            try:
                val = float((amount_field.value or "0").replace(",", ".").strip())
            except ValueError:
                feedback_text.value = "Informe um valor numérico válido."
                feedback_text.visible = True
                self.page.update()
                return

            ok, new_bal, msg, _ = self.wallet_service.deposit_funds_pix(
                user_id=self.user.id,
                amount=val,
                description=f"Aporte ESG ({self.user.name})",
            )
            if not ok:
                feedback_text.value = msg
                feedback_text.visible = True
                self.page.update()
                return

            self.user.balance = new_bal
            self.page.dialog.open = False
            self.page.snack_bar = ft.SnackBar(
                content=ft.Row(
                    spacing=8,
                    controls=[
                        ft.Icon(ft.icons.CHECK_CIRCLE, color="white", size=18),
                        ft.Text(msg, size=12),
                    ],
                ),
                bgcolor="#059669",
                duration=4000,
            )
            self.page.snack_bar.open = True
            self._render_into_root()
            self.safe_update()
            self.page.update()

        def close_dlg(ev):
            self.page.dialog.open = False
            self.page.update()

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.icons.ADD_CARD, color="#059669", size=22),
                    ft.Text("Adicionar Fundo ESG (Mercado Pago)", size=15, weight=ft.FontWeight.BOLD),
                ],
            ),
            content=ft.Container(
                width=330,
                content=ft.Column(
                    tight=True,
                    spacing=12,
                    controls=[
                        ft.Text(
                            "Adicione saldo via Pix no Mercado Pago Sandbox para patrocinar novas missões de coleta.",
                            size=12,
                            color="#475569",
                        ),
                        amount_field,
                        feedback_text,
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dlg),
                ft.ElevatedButton(
                    "Depositar via Pix",
                    bgcolor="#059669",
                    color="white",
                    on_click=confirm_deposit,
                ),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    def open_create_sponsored_bounty_dialog(self, e=None):
        """Abre modal para Patrocinador, Ecoponto ou Admin criar um Bounty com valor próprio via Mercado Pago."""
        if not self.page:
            return

        title_field = ft.TextField(
            label="Título da Missão Patrocinada",
            value=f"Mutirão de Limpeza • {self.user.name}",
            border_radius=10,
            text_size=13,
        )
        type_dd = ft.Dropdown(
            label="Tipo de Resíduo",
            value="Plástico",
            options=[
                ft.dropdown.Option("Plástico"),
                ft.dropdown.Option("Inerte"),
                ft.dropdown.Option("Eletrônicos"),
                ft.dropdown.Option("Papelão"),
                ft.dropdown.Option("Metal"),
            ],
            border_radius=10,
            text_size=13,
        )
        dest_dd = ft.Dropdown(
            label="Ecoponto / Cooperativa de Destino",
            value="COOPLUM" if self.user.role.upper() != "ECOPONTO" else self.user.name,
            options=[
                ft.dropdown.Option("COOPLUM"),
                ft.dropdown.Option("Ecoponto ALURB"),
                ft.dropdown.Option("COOPREL"),
                *(
                    [ft.dropdown.Option(self.user.name)]
                    if self.user.role.upper() == "ECOPONTO" and self.user.name not in ("COOPLUM", "Ecoponto ALURB", "COOPREL")
                    else []
                ),
            ],
            border_radius=10,
            text_size=13,
        )
        val_field = ft.TextField(
            label="Valor da Recompensa (R$)",
            value="50.00",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=10,
            text_size=13,
        )
        feedback_text = ft.Text("", size=12, color="#dc2626", visible=False)

        def confirm_bounty(ev):
            try:
                val = float((val_field.value or "0").replace(",", ".").strip())
            except ValueError:
                feedback_text.value = "Informe um valor numérico válido."
                feedback_text.visible = True
                self.page.update()
                return

            from app.services.bounty_service import BountyService
            from app.services.geo_service import get_geo_service

            u_lat, u_lng = get_geo_service().get_current_location()
            b_svc = BountyService(db_path=self.wallet_service.db_path)
            ok, _, msg, _ = b_svc.create_sponsored_bounty(
                user_id=self.user.id,
                sponsor_name=self.user.name,
                title=title_field.value or "",
                waste_type=type_dd.value or "Plástico",
                dest=dest_dd.value or "COOPLUM",
                val=val,
                lat=u_lat,
                lng=u_lng,
            )
            if not ok:
                feedback_text.value = msg
                feedback_text.visible = True
                self.page.update()
                return

            self.user.balance = self.wallet_service.get_balance(self.user.id)
            self.page.dialog.open = False
            self.page.snack_bar = ft.SnackBar(
                content=ft.Row(
                    spacing=8,
                    controls=[
                        ft.Icon(ft.icons.VERIFIED, color="white", size=18),
                        ft.Text(msg, size=12),
                    ],
                ),
                bgcolor="#7e22ce",
                duration=4000,
            )
            self.page.snack_bar.open = True
            self._render_into_root()
            self.safe_update()
            self.page.update()

        def close_dlg(ev):
            self.page.dialog.open = False
            self.page.update()

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.icons.VOLUNTEER_ACTIVISM, color="#7e22ce", size=22),
                    ft.Text("Criar Bounty Patrocinado", size=16, weight=ft.FontWeight.BOLD),
                ],
            ),
            content=ft.Container(
                width=330,
                content=ft.Column(
                    tight=True,
                    spacing=10,
                    controls=[
                        ft.Text(
                            "Defina a recompensa da missão. O valor será custeado via Mercado Pago Sandbox (50% limpeza + 50% entrega).",
                            size=11,
                            color="#475569",
                        ),
                        title_field,
                        type_dd,
                        dest_dd,
                        val_field,
                        feedback_text,
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dlg),
                ft.ElevatedButton(
                    "Publicar & Pagar Pix",
                    bgcolor="#7e22ce",
                    color="white",
                    on_click=confirm_bounty,
                ),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    def build(self):
        self.root_container = ft.Container(expand=True, bgcolor="#f8fafc")
        self._render_into_root()
        return self.root_container

    def _render_into_root(self):
        # Atualiza dados dinâmicos do perfil
        refreshed_user = self.auth_service.get_user_profile(self.user.id) or self.user
        curr_balance = self.wallet_service.get_balance(self.user.id)
        refreshed_user.balance = curr_balance
        history_items = self.wallet_service.get_history(self.user.id)

        formatted_balance = f"R$ {curr_balance:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        formatted_total = f"R$ {refreshed_user.total_earnings:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        formatted_kg = f"{int(refreshed_user.waste_saved_kg)} kg"

        # Paleta visual por Papel / Perfil
        role_palette = {
            "ADMIN": ("#fee2e2", "#b91c1c", ft.icons.ADMIN_PANEL_SETTINGS),
            "COLETOR": ("#dcfce7", "#15803d", ft.icons.RECYCLING),
            "CIDADAO": ("#e0f2fe", "#0369a1", ft.icons.PERSON_PIN_CIRCLE),
            "ECOPONTO": ("#fef3c7", "#b45309", ft.icons.WAREHOUSE),
            "PATROCINADOR": ("#f3e8ff", "#7e22ce", ft.icons.CORPORATE_FARE),
        }
        bg_role, text_role, icon_role = role_palette.get(
            refreshed_user.role.upper(), ("#f1f5f9", "#334155", ft.icons.PERSON)
        )

        # Banner Superior do Perfil
        top_banner = ft.Container(
            bgcolor="#059669" if not refreshed_user.is_admin() else "#1e293b",
            padding=ft.padding.only(left=20, right=20, top=24, bottom=32),
            border_radius=ft.border_radius.only(bottom_left=32, bottom_right=32),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
                controls=[
                    ft.Row(
                        controls=[
                            ft.IconButton(
                                icon=ft.icons.ARROW_BACK,
                                icon_color="white",
                                on_click=lambda e: self.on_back(),
                            ),
                        ],
                    ),
                    ft.CircleAvatar(
                        content=ft.Text(
                            refreshed_user.name[0].upper(),
                            size=34,
                            weight=ft.FontWeight.BOLD,
                            color="#059669" if not refreshed_user.is_admin() else "#1e293b",
                        ),
                        bgcolor="white",
                        radius=42,
                    ),
                    ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                        controls=[
                            ft.Text(refreshed_user.name, size=20, weight=ft.FontWeight.BOLD, color="white"),
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=12, vertical=4),
                                border_radius=12,
                                bgcolor=bg_role,
                                content=ft.Row(
                                    spacing=4,
                                    tight=True,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    controls=[
                                        ft.Icon(icon_role, size=14, color=text_role),
                                        ft.Text(
                                            refreshed_user.role_display_name().upper(),
                                            size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color=text_role,
                                        ),
                                    ],
                                ),
                            ),
                            ft.Text(refreshed_user.level_title, size=13, color="#d1fae5" if not refreshed_user.is_admin() else "#94a3b8", weight=ft.FontWeight.W_500),
                        ],
                    ),
                ],
            ),
        )

        # Indicadores de Gamificação (Ganhos Totais + Resíduos Salvos)
        stats_row = ft.Row(
            spacing=12,
            controls=[
                ft.Container(
                    expand=True,
                    bgcolor="#ffffff",
                    padding=16,
                    border_radius=16,
                    border=ft.border.all(1, "#f1f5f9"),
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                        controls=[
                            ft.Icon(ft.icons.ACCOUNT_BALANCE_WALLET, color="#059669", size=26),
                            ft.Text("Ganhos Totais", size=11, color="#64748b", weight=ft.FontWeight.W_500),
                            ft.Text(formatted_total, size=16, weight=ft.FontWeight.BOLD, color="#1e293b"),
                        ],
                    ),
                ),
                ft.Container(
                    expand=True,
                    bgcolor="#ffffff",
                    padding=16,
                    border_radius=16,
                    border=ft.border.all(1, "#f1f5f9"),
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                        controls=[
                            ft.Icon(ft.icons.SCALE, color="#2563eb", size=26),
                            ft.Text("Resíduos Salvos", size=11, color="#64748b", weight=ft.FontWeight.W_500),
                            ft.Text(formatted_kg, size=16, weight=ft.FontWeight.BOLD, color="#1e293b"),
                        ],
                    ),
                ),
            ],
        )

        # Seção de Histórico
        history_section = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.START,
            spacing=10,
            controls=[
                ft.Text("Histórico Recente", size=15, weight=ft.FontWeight.BOLD, color="#1e293b"),
                *[self.build_history_item(h) for h in history_items],
            ],
        )

        # Botão Sair da Conta
        btn_logout = ft.OutlinedButton(
            "Sair da Conta",
            width=360,
            style=ft.ButtonStyle(
                color="#dc2626",
                side=ft.BorderSide(1, "#fca5a5"),
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.padding.symmetric(vertical=15),
            ),
            on_click=lambda e: self.on_logout(),
        )

        is_sponsor_or_ecoponto = refreshed_user.role.upper() in ("PATROCINADOR", "ECOPONTO", "ADMIN")
        sponsor_controls = (
            [
                ft.ElevatedButton(
                    "Criar Bounty Patrocinado (Definir Valor)",
                    icon=ft.icons.ADD_LOCATION_ALT,
                    width=360,
                    bgcolor="#7e22ce" if refreshed_user.role.upper() == "PATROCINADOR" else "#b45309",
                    color="white",
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.padding.symmetric(vertical=13),
                    ),
                    on_click=self.open_create_sponsored_bounty_dialog,
                ),
                ft.OutlinedButton(
                    "Adicionar Fundo ESG via Pix (Mercado Pago)",
                    icon=ft.icons.ADD_CARD,
                    width=360,
                    style=ft.ButtonStyle(
                        color="#059669",
                        side=ft.BorderSide(1, "#059669"),
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.padding.symmetric(vertical=12),
                    ),
                    on_click=self.open_deposit_esg_dialog,
                ),
            ]
            if is_sponsor_or_ecoponto
            else []
        )

        # Card de Saldo Disponível + Transferência Pix Mercado Pago Sandbox
        mp_wallet_card = ft.Container(
            bgcolor="#ffffff",
            padding=16,
            border_radius=16,
            border=ft.border.all(1, "#bae6fd"),
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Row(
                                        spacing=6,
                                        controls=[
                                            ft.Icon(ft.icons.PIX, color="#009ee3", size=18),
                                            ft.Text(
                                                "Fundo ESG / Saldo Disponível" if is_sponsor_or_ecoponto else "Saldo Disponível para Saque",
                                                size=12,
                                                color="#0369a1",
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                        ],
                                    ),
                                    ft.Text(formatted_balance, size=22, weight=ft.FontWeight.W_900, color="#0f172a"),
                                ],
                            ),
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                border_radius=8,
                                bgcolor="#e0f2fe",
                                content=ft.Text("Mercado Pago Sandbox", size=10, color="#0284c7", weight=ft.FontWeight.BOLD),
                            ),
                        ],
                    ),
                    *sponsor_controls,
                    ft.ElevatedButton(
                        "Transferir Saldo via Pix (Mercado Pago)",
                        icon=ft.icons.SEND_TO_MOBILE,
                        width=360,
                        bgcolor="#009ee3",
                        color="white",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            padding=ft.padding.symmetric(vertical=13),
                        ),
                        on_click=self.open_pix_transfer_dialog,
                    ),
                ],
            ),
        )

        # Corpo com Scroll
        body = ft.Container(
            expand=True,
            padding=ft.padding.symmetric(horizontal=20, vertical=16),
            content=ft.ListView(
                spacing=16,
                controls=[
                    mp_wallet_card,
                    stats_row,
                    history_section,
                    ft.Container(height=8),
                    btn_logout,
                ],
            ),
        )

        self.root_container.content = ft.Column(
            spacing=0,
            controls=[
                top_banner,
                body,
            ],
        )
        return self.root_container
