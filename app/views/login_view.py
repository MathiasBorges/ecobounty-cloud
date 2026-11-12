"""Tela de Autenticação e Cadastro com Google Auth, LGPD e Seleção de Papel (UC01, UC02)."""
import re
import threading
import time
import uuid
from typing import Callable, Optional
import flet as ft

from app.models.user import (
    ROLE_CIDADAO,
    ROLE_COLETOR,
    ROLE_ECOPONTO,
    ROLE_PATROCINADOR,
    User,
)
from app.services.auth_service import AuthService
from app.services.storage_service import get_client_id, pop_google_auth_result, set_pending_action


class LoginView(ft.UserControl):
    def __init__(
        self,
        auth_service: AuthService,
        on_login_success: Callable[[User], None],
    ):
        super().__init__()
        self.auth_service = auth_service
        self.on_login_success = on_login_success
        self.mode = "login"  # "login", "register", "google_onboarding"
        self.selected_role = ROLE_COLETOR
        self.root_container = ft.Container(expand=True, bgcolor="#ffffff")

        # Campos de Login (Iniciam limpos, sem valores mocados)
        self.email_input = ft.TextField(
            label="E-mail",
            value="",
            hint_text="seu.email@exemplo.com",
            border_radius=12,
            border_color="#cbd5e1",
            focused_border_color="#059669",
            text_size=14,
            prefix_icon=ft.icons.EMAIL_OUTLINED,
            on_submit=self.do_login,
        )
        self.password_input = ft.TextField(
            label="Senha",
            value="",
            password=True,
            can_reveal_password=True,
            border_radius=12,
            border_color="#cbd5e1",
            focused_border_color="#059669",
            text_size=14,
            prefix_icon=ft.icons.LOCK_OUTLINED,
            on_submit=self.do_login,
        )

        # Campos de Cadastro Padrão (UC02)
        self.reg_name = ft.TextField(
            label="Nome Completo",
            border_radius=12,
            border_color="#cbd5e1",
            focused_border_color="#059669",
            text_size=14,
            prefix_icon=ft.icons.PERSON_OUTLINED,
        )
        self.reg_email = ft.TextField(
            label="E-mail",
            border_radius=12,
            border_color="#cbd5e1",
            focused_border_color="#059669",
            text_size=14,
            prefix_icon=ft.icons.EMAIL_OUTLINED,
        )
        self.reg_cpf = ft.TextField(
            label="CPF",
            hint_text="000.000.000-00",
            border_radius=12,
            border_color="#cbd5e1",
            focused_border_color="#059669",
            text_size=14,
            prefix_icon=ft.icons.BADGE_OUTLINED,
        )
        self.reg_phone = ft.TextField(
            label="Telefone",
            hint_text="(82) 99999-9999",
            border_radius=12,
            border_color="#cbd5e1",
            focused_border_color="#059669",
            text_size=14,
            prefix_icon=ft.icons.PHONE_OUTLINED,
        )
        self.reg_pass = ft.TextField(
            label="Senha (mínimo 8 dígitos, letras e números)",
            password=True,
            can_reveal_password=True,
            border_radius=12,
            border_color="#cbd5e1",
            focused_border_color="#059669",
            text_size=14,
            prefix_icon=ft.icons.LOCK_OUTLINED,
        )
        self.reg_confirm_pass = ft.TextField(
            label="Confirmar Senha",
            password=True,
            can_reveal_password=True,
            border_radius=12,
            border_color="#cbd5e1",
            focused_border_color="#059669",
            text_size=14,
            prefix_icon=ft.icons.LOCK_RESET_OUTLINED,
            on_submit=self.do_register,
        )
        self.reg_terms = ft.Checkbox(
            label="Aceito os Termos de Uso e Política de Privacidade (LGPD)",
            value=True,
            active_color="#059669",
        )

        # Campos Google Auth e Onboarding de Papel (validação real, sem dados mocados)
        self.google_email_field = ft.TextField(
            label="E-mail da sua Conta Google",
            hint_text="exemplo@gmail.com",
            value="",
            border_radius=12,
            border_color="#cbd5e1",
            focused_border_color="#059669",
            text_size=14,
            prefix_icon=ft.icons.ACCOUNT_CIRCLE_OUTLINED,
        )
        self.google_name_field = ft.TextField(
            label="Seu Nome Completo",
            hint_text="Nome exibido no perfil",
            value="",
            border_radius=12,
            border_color="#cbd5e1",
            focused_border_color="#059669",
            text_size=14,
            prefix_icon=ft.icons.PERSON_OUTLINED,
        )
        self.google_phone_field = ft.TextField(
            label="Telefone / WhatsApp (opcional)",
            hint_text="(82) 99999-9999",
            value="",
            border_radius=12,
            border_color="#cbd5e1",
            focused_border_color="#059669",
            text_size=14,
            prefix_icon=ft.icons.PHONE_OUTLINED,
        )
        self.google_modal_dialog: Optional[ft.AlertDialog] = None
        self._google_poll_active = False

        # Mensagem de Erro
        self.error_text = ft.Text(
            "",
            color="#dc2626",
            size=13,
            weight=ft.FontWeight.W_500,
            visible=False,
        )

    def safe_update(self):
        try:
            if self.page:
                self.update()
        except Exception:
            pass

    def do_login(self, e):
        email = self.email_input.value or ""
        password = self.password_input.value or ""

        success, user, msg = self.auth_service.login(email, password)
        if success and user:
            self.error_text.visible = False
            if self.page:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.icons.CHECK_CIRCLE, color="white", size=18),
                            ft.Text(f"Login realizado com sucesso! Olá, {user.name.split()[0]}!", weight=ft.FontWeight.BOLD),
                        ],
                    ),
                    bgcolor="#059669",
                    duration=2500,
                )
                self.page.snack_bar.open = True
            self.on_login_success(user)
        else:
            self.error_text.value = msg
            self.error_text.visible = True
            if "senha" in msg.lower():
                self.password_input.value = ""
            self._render()
            self.safe_update()

    def do_register(self, e):
        success, user, msg = self.auth_service.register(
            name=self.reg_name.value or "",
            email=self.reg_email.value or "",
            cpf=self.reg_cpf.value or "",
            phone=self.reg_phone.value or "",
            password=self.reg_pass.value or "",
            confirm_password=self.reg_confirm_pass.value or "",
            terms_accepted=self.reg_terms.value or False,
            role=self.selected_role,
        )
        if success and user:
            self.error_text.visible = False
            self.email_input.value = (self.reg_email.value or "").strip().lower()
            if self.page:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.icons.CHECK_CIRCLE, color="white", size=18),
                            ft.Text(f"Conta criada com sucesso! Bem-vindo(a), {user.name} ({user.role_display_name()})!", weight=ft.FontWeight.BOLD),
                        ],
                    ),
                    bgcolor="#059669",
                    duration=3000,
                )
                self.page.snack_bar.open = True
            self.on_login_success(user)
        else:
            self.error_text.value = msg
            self.error_text.visible = True
            self._render()
            self.safe_update()

    def do_google_login(self, e=None):
        """Dispara autenticação direta do Google via popup do Firebase Auth sem diálogos redundantes."""
        self.error_text.visible = False
        self._google_poll_active = True

        # Dispara comando para abrir o popup oficial do Google no navegador (via web/index.html)
        cid = get_client_id(self.page)
        set_pending_action("trigger_google_auth", cid=cid)

        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Row(
                    spacing=8,
                    controls=[
                        ft.ProgressRing(width=16, height=16, stroke_width=2, color="white"),
                        ft.Text("Janela do Google aberta. Selecione sua conta para entrar...", size=13),
                    ],
                ),
                bgcolor="#059669",
                duration=4000,
            )
            self.page.snack_bar.open = True
            self.page.update()

        # Thread de escuta do resultado real vindo do popup do Google via web/index.html
        def poll_google_worker():
            for _ in range(120):  # até 60s
                if not self._google_poll_active:
                    break
                auth_res = pop_google_auth_result(cid)
                if auth_res:
                    status = auth_res.get("status")
                    if status == "success":
                        g_email = (auth_res.get("email") or "").strip().lower()
                        g_name = (auth_res.get("name") or "").strip() or g_email.split("@")[0].title()
                        g_photo = auth_res.get("photo_url") or ""
                        g_uid = auth_res.get("uid") or f"google_{uuid.uuid4().hex[:12]}"
                        self._google_poll_active = False

                        def on_success_ui():
                            self._process_verified_google_user(email=g_email, name=g_name, photo_url=g_photo, uid=g_uid)

                        if self.page:
                            try:
                                on_success_ui()
                            except Exception:
                                pass
                        else:
                            on_success_ui()
                        break
                    elif status == "error":
                        err_msg = auth_res.get("message") or "Autenticação cancelada na janela do Google"
                        self._google_poll_active = False
                        def on_error_ui():
                            if self.page:
                                self.page.snack_bar = ft.SnackBar(
                                    content=ft.Row(
                                        spacing=8,
                                        controls=[
                                            ft.Icon(ft.icons.INFO_OUTLINE, color="white", size=18),
                                            ft.Text(f"{err_msg}", size=12),
                                        ],
                                    ),
                                    bgcolor="#475569",
                                    duration=3000,
                                )
                                self.page.snack_bar.open = True
                                self.page.update()

                        if self.page:
                            try:
                                on_error_ui()
                            except Exception:
                                pass
                        else:
                            on_error_ui()
                        break
                time.sleep(0.5)

        t = threading.Thread(target=poll_google_worker, daemon=True)
        t.start()

    def _process_verified_google_user(self, email: str, name: str, photo_url: str = "", uid: str = ""):
        """Processa o usuário após confirmação real do e-mail Google."""
        self.google_email_field.value = email
        self.google_name_field.value = name

        # 1. Verifica se já existe conta registrada no banco com este e-mail
        existing = self.auth_service.get_user_by_email(email)
        if existing:
            # Conta existente: Login imediato!
            if self.page:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.icons.CHECK_CIRCLE, color="white", size=18),
                            ft.Text(f"Conectado com Google! Olá, {existing.name.split()[0]} ({existing.role_display_name()})!", weight=ft.FontWeight.BOLD),
                        ],
                    ),
                    bgcolor="#059669",
                    duration=2500,
                )
                self.page.snack_bar.open = True
            self.on_login_success(existing)
        else:
            # Conta nova: Abre o formulário de Onboarding de papel
            self.mode = "google_onboarding"
            self._render()
            self.safe_update()

    def complete_google_onboarding(self, e=None):
        """Conclui o cadastro Google com o perfil escolhido."""
        email = (self.google_email_field.value or "").strip().lower()
        name = (self.google_name_field.value or "").strip()
        phone = (self.google_phone_field.value or "").strip()
        role = self.selected_role or ROLE_COLETOR

        if not email or "@" not in email:
            self.error_text.value = "Informe um e-mail do Google válido para concluir seu cadastro."
            self.error_text.visible = True
            self.safe_update()
            return

        if not name:
            name = email.split("@")[0].title()

        success, user, msg = self.auth_service.register_google_user(
            email=email,
            name=name,
            role=role,
            phone=phone,
            google_id=f"google_{uuid.uuid4().hex[:12]}",
        )
        if success and user:
            self.error_text.visible = False
            if self.page:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.icons.CHECK_CIRCLE, color="white", size=18),
                            ft.Text(f"Bem-vindo(a) ao EcoBounty como {user.role_display_name()}!", weight=ft.FontWeight.BOLD),
                        ],
                    ),
                    bgcolor="#059669",
                    duration=3000,
                )
                self.page.snack_bar.open = True
            self.on_login_success(user)
        else:
            self.error_text.value = msg
            self.error_text.visible = True
            self._render()
            self.safe_update()

    def switch_mode(self, mode: str, e=None):
        self.mode = mode
        self.error_text.visible = False
        if mode == "login" and self.reg_email.value:
            self.email_input.value = self.reg_email.value
        self._render()
        self.safe_update()

    def select_role(self, role_code: str):
        self.selected_role = role_code
        self._render()
        self.safe_update()

    def _build_role_card(self, role_code: str, title: str, subtitle: str, icon_name: str, color_hex: str) -> ft.Container:
        """Cria um card interativo para seleção de papel no EcoBounty."""
        is_selected = self.selected_role == role_code
        return ft.Container(
            border=ft.border.all(2 if is_selected else 1, "#059669" if is_selected else "#e2e8f0"),
            border_radius=12,
            bgcolor="#f0fdf4" if is_selected else "#ffffff",
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            ink=True,
            on_click=lambda e, r=role_code: self.select_role(r),
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=40,
                        height=40,
                        border_radius=20,
                        bgcolor=f"{color_hex}15",
                        alignment=ft.alignment.center,
                        content=ft.Icon(icon_name, color=color_hex, size=22),
                    ),
                    ft.Column(
                        expand=True,
                        spacing=2,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(title, weight=ft.FontWeight.BOLD, size=14, color="#1e293b"),
                                    ft.Icon(
                                        ft.icons.CHECK_CIRCLE if is_selected else ft.icons.RADIO_BUTTON_UNCHECKED,
                                        color="#059669" if is_selected else "#94a3b8",
                                        size=18,
                                    ),
                                ],
                            ),
                            ft.Text(subtitle, size=11, color="#64748b"),
                        ],
                    ),
                ],
            ),
        )

    def build(self):
        self._render()
        return self.root_container

    def _render(self):
        if self.mode == "login":
            self.root_container.content = ft.Container(
                expand=True,
                bgcolor="#ffffff",
                padding=ft.padding.symmetric(horizontal=28, vertical=40),
                alignment=ft.alignment.center,
                content=ft.Column(
                    tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                    spacing=16,
                    controls=[
                        # Logotipo
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(ft.icons.ECO, color="#059669", size=28),
                                ft.Text(
                                    "EcoBounty",
                                    size=22,
                                    weight=ft.FontWeight.BOLD,
                                    color="#1e293b",
                                ),
                            ],
                        ),
                        ft.Container(height=4),
                        ft.Text(
                            "Bem-vindo(a)",
                            size=26,
                            weight=ft.FontWeight.BOLD,
                            color="#1e293b",
                        ),
                        ft.Text(
                            "Faça login para limpar a cidade e movimentar a economia circular.",
                            size=14,
                            color="#64748b",
                        ),
                        ft.Container(height=8),
                        self.email_input,
                        self.password_input,
                        self.error_text,
                        ft.Container(height=8),
                        # Botão Entrar
                        ft.ElevatedButton(
                            "Entrar",
                            width=360,
                            bgcolor="#059669",
                            color="white",
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=12),
                                padding=ft.padding.symmetric(vertical=15),
                            ),
                            on_click=self.do_login,
                        ),
                        # Divisor
                        ft.Row(
                            width=360,
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Container(expand=True, height=1, bgcolor="#e2e8f0"),
                                ft.Text("  ou  ", size=12, color="#94a3b8"),
                                ft.Container(expand=True, height=1, bgcolor="#e2e8f0"),
                            ],
                        ),
                        # Botão Entrar com Google
                        ft.OutlinedButton(
                            "Continuar com Google",
                            icon=ft.icons.ACCOUNT_CIRCLE_OUTLINED,
                            width=360,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=12),
                                padding=ft.padding.symmetric(vertical=14),
                                side=ft.BorderSide(1, "#cbd5e1"),
                            ),
                            on_click=self.do_google_login,
                        ),
                        # Botão Criar Conta
                        ft.TextButton(
                            "Criar Nova Conta",
                            width=360,
                            style=ft.ButtonStyle(
                                color="#059669",
                                shape=ft.RoundedRectangleBorder(radius=12),
                                padding=ft.padding.symmetric(vertical=14),
                            ),
                            on_click=lambda e: self.switch_mode("register", e),
                        ),
                    ],
                ),
            )
        elif self.mode == "google_onboarding":
            # Tela de Onboarding Simplificado Google (UC01, UC02)
            email_val = self.google_email_field.value or "seu-email@gmail.com"
            name_val = self.google_name_field.value or "Usuário Google"

            self.root_container.content = ft.Container(
                expand=True,
                bgcolor="#ffffff",
                padding=ft.padding.symmetric(horizontal=24, vertical=20),
                alignment=ft.alignment.center,
                content=ft.ListView(
                    spacing=14,
                    controls=[
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.IconButton(
                                    icon=ft.icons.ARROW_BACK,
                                    icon_color="#1e293b",
                                    on_click=lambda e: self.switch_mode("login", e),
                                ),
                                ft.Text(
                                    "Completar Cadastro Google",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color="#1e293b",
                                ),
                            ],
                        ),
                        # Badge de Conta Google Verificada
                        ft.Container(
                            border=ft.border.all(1, "#bbf7d0"),
                            bgcolor="#f0fdf4",
                            border_radius=12,
                            padding=ft.padding.all(12),
                            content=ft.Row(
                                spacing=12,
                                controls=[
                                    ft.Icon(ft.icons.CHECK_CIRCLE, color="#16a34a", size=24),
                                    ft.Column(
                                        spacing=2,
                                        expand=True,
                                        controls=[
                                            ft.Text(name_val, weight=ft.FontWeight.BOLD, size=14, color="#1e293b"),
                                            ft.Text(f"{email_val} • Conta Google Verificada", size=11, color="#15803d"),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                        ft.Text(
                            "O que você gostaria de fazer no EcoBounty?",
                            size=15,
                            weight=ft.FontWeight.BOLD,
                            color="#1e293b",
                        ),
                        ft.Text(
                            "Selecione seu perfil de atuação na plataforma:",
                            size=12,
                            color="#64748b",
                        ),
                        # Seleção dos 4 Papéis
                        self._build_role_card(
                            ROLE_COLETOR,
                            "Coletor(a)",
                            "Limpar pontos de lixo, transportar resíduos e receber recompensas em dinheiro",
                            ft.icons.CLEANING_SERVICES,
                            "#059669",
                        ),
                        self._build_role_card(
                            ROLE_CIDADAO,
                            "Cidadão(ã)",
                            "Mapear e denunciar focos de lixo irregular no seu bairro",
                            ft.icons.CAMPAIGN,
                            "#0284c7",
                        ),
                        self._build_role_card(
                            ROLE_ECOPONTO,
                            "Ecoponto / Cooperativa",
                            "Receber materiais recicláveis dos coletores e validar entregas",
                            ft.icons.RECYCLING,
                            "#16a34a",
                        ),
                        self._build_role_card(
                            ROLE_PATROCINADOR,
                            "Patrocinador ESG",
                            "Financiar missões ecológicas e acompanhar o impacto socioambiental",
                            ft.icons.BUSINESS,
                            "#7c3aed",
                        ),
                        ft.Container(height=4),
                        self.google_phone_field,
                        self.error_text,
                        ft.ElevatedButton(
                            "Concluir Cadastro e Começar",
                            bgcolor="#059669",
                            color="white",
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=12),
                                padding=ft.padding.symmetric(vertical=15),
                            ),
                            on_click=self.complete_google_onboarding,
                        ),
                        ft.TextButton(
                            "Voltar para o Login",
                            style=ft.ButtonStyle(color="#64748b"),
                            on_click=lambda e: self.switch_mode("login", e),
                        ),
                        ft.Container(height=20),
                    ],
                ),
            )
        else:
            # Formulário de Cadastro Padrão (UC02)
            self.root_container.content = ft.Container(
                expand=True,
                bgcolor="#ffffff",
                padding=ft.padding.symmetric(horizontal=24, vertical=20),
                alignment=ft.alignment.center,
                content=ft.ListView(
                    spacing=12,
                    controls=[
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.IconButton(
                                    icon=ft.icons.ARROW_BACK,
                                    icon_color="#1e293b",
                                    on_click=lambda e: self.switch_mode("login", e),
                                ),
                                ft.Text(
                                    "Criar Nova Conta",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color="#1e293b",
                                ),
                            ],
                        ),
                        ft.Text(
                            "Junte-se à rede de economia circular e receba recompensas reais.",
                            size=13,
                            color="#64748b",
                        ),
                        ft.Text(
                            "Perfil de Atuação:",
                            size=13,
                            weight=ft.FontWeight.BOLD,
                            color="#1e293b",
                        ),
                        self._build_role_card(
                            ROLE_COLETOR,
                            "Coletor",
                            "Limpar pontos e receber recompensas",
                            ft.icons.CLEANING_SERVICES,
                            "#059669",
                        ),
                        self._build_role_card(
                            ROLE_CIDADAO,
                            "Cidadão",
                            "Criar denúncias comunitárias",
                            ft.icons.CAMPAIGN,
                            "#0284c7",
                        ),
                        self._build_role_card(
                            ROLE_ECOPONTO,
                            "Ecoponto",
                            "Receber e pesar resíduos",
                            ft.icons.RECYCLING,
                            "#16a34a",
                        ),
                        self._build_role_card(
                            ROLE_PATROCINADOR,
                            "Patrocinador ESG",
                            "Financiar missões e impacto",
                            ft.icons.BUSINESS,
                            "#7c3aed",
                        ),
                        self.reg_name,
                        self.reg_email,
                        self.reg_cpf,
                        self.reg_phone,
                        self.reg_pass,
                        self.reg_confirm_pass,
                        self.reg_terms,
                        self.error_text,
                        ft.ElevatedButton(
                            "Cadastrar e Começar",
                            bgcolor="#059669",
                            color="white",
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=12),
                                padding=ft.padding.symmetric(vertical=15),
                            ),
                            on_click=self.do_register,
                        ),
                        ft.TextButton(
                            "Já possuo cadastro (Entrar)",
                            style=ft.ButtonStyle(color="#64748b"),
                            on_click=lambda e: self.switch_mode("login", e),
                        ),
                        ft.Container(height=30),
                    ],
                ),
            )
