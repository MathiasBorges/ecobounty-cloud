"""Modelo de Usuário / Coletor, Cidadão, Ecoponto e Patrocinador."""
from dataclasses import dataclass
from typing import Dict, Optional

# Constantes de Papéis (Perfis de Atuação no EcoBounty)
ROLE_COLETOR = "COLETOR"
ROLE_CIDADAO = "CIDADAO"
ROLE_ECOPONTO = "ECOPONTO"
ROLE_PATROCINADOR = "PATROCINADOR"
ROLE_ADMIN = "ADMIN"

ROLE_LABELS: Dict[str, str] = {
    ROLE_COLETOR: "Coletor",
    ROLE_CIDADAO: "Cidadão",
    ROLE_ECOPONTO: "Ecoponto / Cooperativa",
    ROLE_PATROCINADOR: "Patrocinador ESG",
    ROLE_ADMIN: "Administrador",
}

ROLE_ICONS: Dict[str, str] = {
    ROLE_COLETOR: "cleaning_services",
    ROLE_CIDADAO: "campaign",
    ROLE_ECOPONTO: "recycling",
    ROLE_PATROCINADOR: "business",
    ROLE_ADMIN: "admin_panel_settings",
}

ROLE_DESCRIPTIONS: Dict[str, str] = {
    ROLE_COLETOR: "Limpar pontos, coletar resíduos e ganhar recompensas",
    ROLE_CIDADAO: "Reportar focos de lixo e acompanhar a limpeza do bairro",
    ROLE_ECOPONTO: "Receber descartes e validar a entrega dos materiais",
    ROLE_PATROCINADOR: "Financiar missões ecológicas e acompanhar o impacto ESG",
    ROLE_ADMIN: "Gestão do ecossistema e moderação",
}


@dataclass
class User:
    id: int
    name: str
    email: str
    cpf: str
    phone: str
    password_hash: str
    balance: float = 0.0
    total_earnings: float = 0.0
    waste_saved_kg: float = 0.0
    level_title: str = "Nível 1 • Recruta Verde"
    role: str = ROLE_COLETOR
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "User":
        keys = row.keys() if hasattr(row, "keys") else []
        return cls(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            cpf=row["cpf"],
            phone=row["phone"],
            password_hash=row["password_hash"],
            balance=float(row["balance"]),
            total_earnings=float(row["total_earnings"]),
            waste_saved_kg=float(row["waste_saved_kg"]),
            level_title=row["level_title"],
            role=row["role"] if "role" in keys else ROLE_COLETOR,
            created_at=row["created_at"] if "created_at" in keys else None,
        )

    def is_admin(self) -> bool:
        return self.role.upper() == ROLE_ADMIN

    def is_coletor(self) -> bool:
        return self.role.upper() == ROLE_COLETOR

    def is_cidadao(self) -> bool:
        return self.role.upper() == ROLE_CIDADAO

    def is_ecoponto(self) -> bool:
        return self.role.upper() == ROLE_ECOPONTO

    def is_patrocinador(self) -> bool:
        return self.role.upper() == ROLE_PATROCINADOR

    def role_display_name(self) -> str:
        return ROLE_LABELS.get(self.role.upper(), self.role.capitalize())

    def role_icon(self) -> str:
        return ROLE_ICONS.get(self.role.upper(), "person")

    def role_description(self) -> str:
        return ROLE_DESCRIPTIONS.get(self.role.upper(), "")

    def formatted_balance(self) -> str:
        return f"R$ {self.balance:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
