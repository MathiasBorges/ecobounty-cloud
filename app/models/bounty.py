"""Modelo de Bounty (Missão de Limpeza)."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Bounty:
    id: int
    title: str
    val: float
    dist: int
    type: str
    dest: str
    img: str
    lat: float
    lng: float
    icon: str = "trash"
    color: str = "blue"
    sponsor: str = "Parceiro ESG Maceió"
    status: str = "DISPONIVEL"  # 'DISPONIVEL', 'EM_ANDAMENTO', 'CONCLUIDO'
    assigned_user_id: Optional[int] = None
    current_phase: int = 0  # 0: Aberto, 1: Fase 1 (Coleta), 2: Fase 2 (Ecoponto), 3: Concluído
    created_at: Optional[str] = None
    dijkstra_km: Optional[float] = None
    dijkstra_score: Optional[float] = None

    @classmethod
    def from_row(cls, row) -> "Bounty":
        return cls(
            id=row["id"],
            title=row["title"],
            val=float(row["val"]),
            dist=int(row["dist"]),
            type=row["type"],
            dest=row["dest"],
            img=row["img"],
            lat=float(row["lat"]),
            lng=float(row["lng"]),
            icon=row["icon"],
            color=row["color"],
            sponsor=row["sponsor"] if "sponsor" in row.keys() else "Parceiro ESG Maceió",
            status=row["status"],
            assigned_user_id=row["assigned_user_id"],
            current_phase=int(row["current_phase"]),
            created_at=row["created_at"] if "created_at" in row.keys() else None,
        )

    def formatted_distance(self) -> str:
        """Retorna formato em m ou km conforme UC03 FP2."""
        if self.dist >= 1000:
            return f"{self.dist / 1000.0:.1f}km"
        return f"{self.dist}m"

    def formatted_value(self) -> str:
        """Formata valor monetário no padrão brasileiro R$ 00,00."""
        return f"R$ {self.val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def half_value(self) -> float:
        """Retorna 50% do valor com arredondamento preciso em centavos."""
        return round(self.val / 2.0, 2)

    def formatted_half_value(self) -> str:
        half = self.half_value()
        return f"R$ {half:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
