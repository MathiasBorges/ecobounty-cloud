"""Modelos de Transações e Histórico."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Transaction:
    id: int
    user_id: int
    bounty_id: int
    type: str  # 'ADIANTAMENTO_50', 'QUITACAO_50'
    amount: float
    idempotency_key: str
    created_at: Optional[str] = None


@dataclass
class HistoryItem:
    id: int
    user_id: int
    title: str
    status: str
    amount: float
    date_label: str
    created_at: Optional[str] = None

    def formatted_amount(self) -> str:
        return f"+ R$ {self.amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
