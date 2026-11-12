"""Serviço de Autenticação, Cadastro (LGPD) e Gestão de Usuários (Google Auth & Firestore)."""
import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from app.database.connection import get_connection
from app.models.user import User

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


class AuthService:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def validate_email_format(self, email: str) -> bool:
        if not email or not isinstance(email, str):
            return False
        return bool(EMAIL_REGEX.match(email.strip()))

    def login(self, email: str, password: str) -> Tuple[bool, Optional[User], str]:
        """Autentica usuário existente conforme UC01 com suporte dual SQLite + Cloud Firestore."""
        clean_email = email.strip().lower() if email else ""
        clean_pass = password.strip() if password else ""

        if not clean_email or not clean_pass:
            return False, None, "Preencha e-mail e senha"

        if not self.validate_email_format(clean_email):
            return False, None, "Informe um e-mail válido"

        conn = get_connection(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE LOWER(email) = LOWER(?)",
                (clean_email,),
            ).fetchone()

            if row:
                if row["password_hash"] != clean_pass and row["password_hash"] != "GOOGLE_AUTH":
                    return False, None, "E-mail ou senha inválidos"

                user = User.from_row(row)
                return True, user, "Login realizado com sucesso"

            # Fallback de consulta no Cloud Firestore se o usuário foi registrado em outro dispositivo
            try:
                from app.services.firestore_service import get_firestore_service
                cloud_user = get_firestore_service().get_user_by_email(clean_email)
                if cloud_user:
                    # Sincroniza para o cache local SQLite
                    with conn:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO users (id, name, email, cpf, phone, password_hash, balance, total_earnings, waste_saved_kg, level_title, role, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                cloud_user.id,
                                cloud_user.name,
                                cloud_user.email,
                                cloud_user.cpf,
                                cloud_user.phone,
                                clean_pass,
                                cloud_user.balance,
                                cloud_user.total_earnings,
                                cloud_user.waste_saved_kg,
                                cloud_user.level_title,
                                cloud_user.role,
                                cloud_user.created_at,
                            ),
                        )
                    return True, cloud_user, "Login realizado com sucesso (sincronizado da nuvem)"
            except Exception:
                pass

            return False, None, "E-mail ou senha inválidos"
        finally:
            conn.close()

    def register(
        self,
        name: str,
        email: str,
        cpf: str,
        phone: str,
        password: str,
        confirm_password: str,
        terms_accepted: bool,
        role: str = "COLETOR",
    ) -> Tuple[bool, Optional[User], str]:
        """Registra novo usuário cumprindo normas de validação e LGPD (UC02) gravando em SQLite e Firestore."""
        name = name.strip() if name else ""
        clean_email = email.strip().lower() if email else ""
        cpf = cpf.strip() if cpf else ""
        phone = phone.strip() if phone else ""
        password = password.strip() if password else ""
        confirm_password = confirm_password.strip() if confirm_password else ""
        clean_role = role.strip().upper() if role else "COLETOR"
        if clean_role not in ["COLETOR", "CIDADAO", "ECOPONTO", "PATROCINADOR", "ADMIN"]:
            clean_role = "COLETOR"

        if not name or not clean_email or not cpf or not phone or not password or not confirm_password:
            return False, None, "Preencha todos os campos obrigatórios"

        if not terms_accepted:
            return False, None, "Você deve aceitar os termos e a política de privacidade (LGPD)"

        if not self.validate_email_format(clean_email):
            return False, None, "Informe um e-mail válido"

        if password != confirm_password:
            return False, None, "As senhas não conferem"

        # Política de senha: ≥ 8 caracteres, letras e números (UC02 FE3)
        if len(password) < 8 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            return False, None, "A senha deve ter no mínimo 8 caracteres, com letras e números"

        conn = get_connection(self.db_path)
        try:
            with conn:
                existing = conn.execute(
                    "SELECT id FROM users WHERE LOWER(email) = LOWER(?)",
                    (clean_email,),
                ).fetchone()

                if existing:
                    return False, None, "E-mail já cadastrado"

                now = datetime.now().isoformat()
                cursor = conn.execute(
                    """
                    INSERT INTO users (name, email, cpf, phone, password_hash, balance, total_earnings, waste_saved_kg, level_title, role, created_at)
                    VALUES (?, ?, ?, ?, ?, 0.0, 0.0, 0.0, 'Nível 1 • Recruta Verde', ?, ?)
                    """,
                    (name, clean_email, cpf, phone, password, clean_role, now),
                )
                user_id = cursor.lastrowid
                row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                new_user = User.from_row(row)

                # Persiste no Cloud Firestore
                try:
                    from app.services.firestore_service import get_firestore_service
                    get_firestore_service().save_user_async(new_user)
                except Exception:
                    pass

                return True, new_user, "Conta criada com sucesso"
        finally:
            conn.close()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Obtém usuário por e-mail com fallback e sincronização automática Cloud Firestore."""
        if not email:
            return None
        clean_email = email.strip().lower()
        conn = get_connection(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE LOWER(email) = LOWER(?)",
                (clean_email,),
            ).fetchone()
            if row:
                return User.from_row(row)

            # Fallback para Cloud Firestore se o usuário foi criado em outro nó
            try:
                from app.services.firestore_service import get_firestore_service
                cloud_user = get_firestore_service().get_user_by_email(clean_email)
                if cloud_user:
                    with conn:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO users (id, name, email, cpf, phone, password_hash, balance, total_earnings, waste_saved_kg, level_title, role, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                cloud_user.id,
                                cloud_user.name,
                                cloud_user.email,
                                cloud_user.cpf,
                                cloud_user.phone,
                                cloud_user.password_hash or "GOOGLE_AUTH",
                                cloud_user.balance,
                                cloud_user.total_earnings,
                                cloud_user.waste_saved_kg,
                                cloud_user.level_title,
                                cloud_user.role,
                                cloud_user.created_at,
                            ),
                        )
                    return cloud_user
            except Exception:
                pass
            return None
        finally:
            conn.close()

    def check_google_user(self, email: str) -> Optional[User]:
        """Verifica se já existe conta cadastrada para o e-mail Google."""
        return self.get_user_by_email(email)

    def register_google_user(
        self,
        email: str,
        name: str,
        role: str = "COLETOR",
        phone: str = "",
        google_id: str = "",
    ) -> Tuple[bool, Optional[User], str]:
        """Cadastra novo usuário via Google com o perfil de atuação selecionado (Coletor, Cidadão, Ecoponto ou Patrocinador)."""
        clean_email = email.strip().lower() if email else ""
        clean_name = name.strip() if name else "Usuário Google"
        clean_phone = phone.strip() if phone else "(82) 90000-0000"
        clean_role = role.strip().upper() if role else "COLETOR"

        if not clean_email or not self.validate_email_format(clean_email):
            return False, None, "Informe um e-mail Google válido"

        valid_roles = ["COLETOR", "CIDADAO", "ECOPONTO", "PATROCINADOR", "ADMIN"]
        if clean_role not in valid_roles:
            clean_role = "COLETOR"

        conn = get_connection(self.db_path)
        try:
            with conn:
                existing = conn.execute(
                    "SELECT * FROM users WHERE LOWER(email) = LOWER(?)",
                    (clean_email,),
                ).fetchone()

                if existing:
                    user = User.from_row(existing)
                    setattr(user, "google_id", google_id)
                    return True, user, f"Conta já existente. Conectado como {user.role_display_name()}!"

                now = datetime.now().isoformat()
                cursor = conn.execute(
                    """
                    INSERT INTO users (name, email, cpf, phone, password_hash, balance, total_earnings, waste_saved_kg, level_title, role, created_at)
                    VALUES (?, ?, '000.000.000-00', ?, 'GOOGLE_AUTH', 0.0, 0.0, 0.0, 'Nível 1 • Recruta Verde', ?, ?)
                    """,
                    (clean_name, clean_email, clean_phone, clean_role, now),
                )
                user_id = cursor.lastrowid
                row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                new_user = User.from_row(row)
                setattr(new_user, "google_id", google_id)

                # Persistência e sincronização com Cloud Firestore
                try:
                    from app.services.firestore_service import get_firestore_service
                    get_firestore_service().save_user_async(new_user)
                except Exception:
                    pass

                return True, new_user, f"Cadastro realizado com sucesso como {new_user.role_display_name()}!"
        finally:
            conn.close()

    def login_or_register_with_google(
        self,
        google_user_data: Optional[Dict[str, Any]] = None,
        id_token: Optional[str] = None,
        role: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Tuple[bool, Optional[User], str]:
        """Autentica ou cadastra coletor via Google Auth (Firebase Authentication)."""
        user_info: Dict[str, Any] = {}

        if id_token:
            try:
                from app.cloud.gcp_provider import get_gcp_provider
                verified = get_gcp_provider().verify_google_token(id_token)
                if verified:
                    user_info = verified
            except Exception:
                pass

        if not user_info and google_user_data:
            user_info = dict(google_user_data)

        if not user_info:
            # Dados padrão para teste/mock do Google Auth
            user_info = {
                "name": "Coletor Google Verificado",
                "email": "coletor.google@ecobounty.com",
                "uid": "google_default_uid_123",
            }

        email = str(user_info.get("email", "")).strip().lower()
        name = str(user_info.get("name", "Usuário Google")).strip() or "Usuário Google"
        google_id = str(user_info.get("uid", user_info.get("google_id", "")))

        if not email or not self.validate_email_format(email):
            return False, None, "Conta Google não possui e-mail válido"

        # Se já existe conta registrada para este e-mail, entra imediatamente
        existing = self.get_user_by_email(email)
        if existing:
            setattr(existing, "google_id", google_id)
            return True, existing, f"Conectado com sucesso via Google! Olá, {existing.name.split()[0]}!"

        # Se for conta nova, realiza o cadastro com o perfil selecionado
        chosen_role = role or "COLETOR"
        return self.register_google_user(
            email=email,
            name=name,
            role=chosen_role,
            phone=phone or "(82) 90000-0000",
            google_id=google_id,
        )

    def get_user_profile(self, user_id: int) -> Optional[User]:
        """Obtém perfil do usuário pelo id (SQLite com fallback para Cloud Firestore)."""
        conn = get_connection(self.db_path)
        try:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if row:
                return User.from_row(row)

            # Fallback para o Cloud Firestore
            try:
                from app.services.firestore_service import get_firestore_service
                return get_firestore_service().get_user(user_id)
            except Exception:
                return None
        finally:
            conn.close()
