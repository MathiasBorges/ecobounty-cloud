"""Estrutura de Dados: Deque (Double-Ended Queue - Fila com duas extremidades).

Permite inserções e remoções tanto no início (left) quanto no fim (right) em O(1) estrito
utilizando a Lista Duplamente Encadeada (DoublyLinkedList).
Utilizada no EcoBounty para:
- Cache deslizante bidirecional de notificações recentes e alertas
- Fila de prioridade adaptativa: denúncias urgentes / risco ambiental furam a fila à esquerda (append_left)
"""
from typing import Any, Generic, Iterator, List, Optional, TypeVar

from app.data_structures.linked_list import DoublyLinkedList

T = TypeVar("T")


class DequeUnderflowError(Exception):
    """Lançado ao tentar remover de deque vazio."""
    pass


class Deque(Generic[T]):
    """Deque genérico de alta performance baseado em Lista Duplamente Encadeada para O(1) estrito."""

    def __init__(self, max_size: Optional[int] = None):
        self._list: DoublyLinkedList[T] = DoublyLinkedList[T]()
        self._max_size: Optional[int] = max_size

    def __len__(self) -> int:
        return len(self._list)

    def is_empty(self) -> bool:
        return self._list.is_empty()

    def is_full(self) -> bool:
        if self._max_size is None:
            return False
        return len(self._list) >= self._max_size

    def append_right(self, item: T) -> None:
        """Insere no final (direita) do deque. O(1) estrito."""
        if self.is_full():
            # Remove o mais antigo do lado oposto se atingir capacidade máxima
            self._list.pop_head()
        self._list.append(item)

    def append_left(self, item: T) -> None:
        """Insere no início (esquerda) do deque (alta prioridade / fura-fila). O(1) estrito."""
        if self.is_full():
            self._list.pop_tail()
        self._list.prepend(item)

    def pop_right(self) -> T:
        """Remove e retorna o elemento da extremidade direita (final). O(1) estrito."""
        if self.is_empty():
            raise DequeUnderflowError("Deque vazio")
        return self._list.pop_tail()

    def pop_left(self) -> T:
        """Remove e retorna o elemento da extremidade esquerda (início). O(1) estrito."""
        if self.is_empty():
            raise DequeUnderflowError("Deque vazio")
        return self._list.pop_head()

    def peek_left(self) -> T:
        if self.is_empty():
            raise DequeUnderflowError("Deque vazio")
        return self._list.head.data  # type: ignore

    def peek_right(self) -> T:
        if self.is_empty():
            raise DequeUnderflowError("Deque vazio")
        return self._list.tail.data  # type: ignore

    def clear(self) -> None:
        self._list.clear()

    def to_list(self) -> List[T]:
        return self._list.to_list()

    def __iter__(self) -> Iterator[T]:
        return iter(self._list)

    def __repr__(self) -> str:
        return f"Deque({self.to_list()})"
