"""Estrutura de Dados: Fila (Queue - FIFO).

Implementa a política First-In, First-Out com enfileiramento e desenfileiramento em O(1) estrito
utilizando a Lista Duplamente Encadeada (DoublyLinkedList).
Utilizada no EcoBounty para:
- Fila FIFO de upload e auditoria assíncrona de fotos de denúncias e coletas
- Fila de despacho de eventos para a nuvem Google Cloud (Storage / Cloud Functions / Firestore)
"""
from typing import Any, Generic, Iterator, List, Optional, TypeVar

from app.data_structures.linked_list import DoublyLinkedList

T = TypeVar("T")


class QueueUnderflowError(Exception):
    """Lançado ao tentar desenfileirar de uma fila vazia."""
    pass


class Queue(Generic[T]):
    """Fila genérica com política FIFO baseada em Lista Duplamente Encadeada para O(1) estrito."""

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

    def enqueue(self, item: T) -> None:
        """Enfileira um elemento no final da fila. O(1) estrito."""
        if self.is_full():
            raise OverflowError(f"Fila cheia: limite de {self._max_size} elementos atingido")
        self._list.append(item)

    def dequeue(self) -> T:
        """Desenfileira e retorna o elemento mais antigo (início). O(1) estrito.
        Lança QueueUnderflowError se a fila estiver vazia.
        """
        if self.is_empty():
            raise QueueUnderflowError("Fila vazia (Queue underflow)")
        return self._list.pop_head()

    def peek(self) -> T:
        """Consulta o primeiro elemento da fila sem remover. O(1)."""
        if self.is_empty():
            raise QueueUnderflowError("Fila vazia")
        return self._list.head.data  # type: ignore

    def clear(self) -> None:
        self._list.clear()

    def to_list(self) -> List[T]:
        return self._list.to_list()

    def __iter__(self) -> Iterator[T]:
        return iter(self._list)

    def __repr__(self) -> str:
        first = self.peek() if not self.is_empty() else None
        return f"Queue(head={first}, size={len(self)})"
