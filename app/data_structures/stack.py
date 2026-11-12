"""Estrutura de Dados: Pilha (Stack - LIFO).

Implementa a política Last-In, First-Out com operações push, pop, peek em O(1).
Utilizada no EcoBounty para:
- Sistema de Desfazer/Refazer (Undo/Redo) de ações do coletor e auditor
- Pilha de navegação e histórico transacional de estados de missão
"""
from typing import Any, Generic, Iterator, List, Optional, TypeVar

T = TypeVar("T")


class StackUnderflowError(Exception):
    """Lançado ao tentar desempilhar de uma pilha vazia."""
    pass


class Stack(Generic[T]):
    """Pilha genérica com política LIFO."""

    def __init__(self, max_size: Optional[int] = None):
        self._items: List[T] = []
        self._max_size: Optional[int] = max_size

    def __len__(self) -> int:
        return len(self._items)

    def is_empty(self) -> bool:
        return len(self._items) == 0

    def is_full(self) -> bool:
        if self._max_size is None:
            return False
        return len(self._items) >= self._max_size

    def push(self, item: T) -> None:
        """Empilha um novo elemento no topo. O(1)."""
        if self.is_full():
            # Política de descarte do mais antigo para histórico limitado
            self._items.pop(0)
        self._items.append(item)

    def pop(self) -> T:
        """Desempilha e retorna o elemento do topo. O(1).
        Lança StackUnderflowError se a pilha estiver vazia.
        """
        if self.is_empty():
            raise StackUnderflowError("Pilha vazia (Stack underflow)")
        return self._items.pop()

    def peek(self) -> T:
        """Consulta o elemento do topo sem remover. O(1)."""
        if self.is_empty():
            raise StackUnderflowError("Pilha vazia")
        return self._items[-1]

    def clear(self) -> None:
        self._items.clear()

    def to_list(self) -> List[T]:
        """Retorna os elementos da base até o topo."""
        return list(self._items)

    def __iter__(self) -> Iterator[T]:
        # Itera do topo para a base
        return reversed(self._items)

    def __repr__(self) -> str:
        return f"Stack(top={self.peek() if not self.is_empty() else None}, size={len(self)})"


class UndoRedoManager(Generic[T]):
    """Gerenciador de Undo/Redo baseado em duas pilhas LIFO para o EcoBounty."""

    def __init__(self, max_history: int = 50):
        self.undo_stack: Stack[T] = Stack[T](max_size=max_history)
        self.redo_stack: Stack[T] = Stack[T](max_size=max_history)

    def record_action(self, action: T) -> None:
        """Registra uma nova ação e invalida a pilha de redo."""
        self.undo_stack.push(action)
        self.redo_stack.clear()

    def can_undo(self) -> bool:
        return not self.undo_stack.is_empty()

    def can_redo(self) -> bool:
        return not self.redo_stack.is_empty()

    def undo(self) -> T:
        """Desfaz a última ação empilhando-a no redo."""
        action = self.undo_stack.pop()
        self.redo_stack.push(action)
        return action

    def redo(self) -> T:
        """Refaz a ação anterior empilhando-a de volta no undo."""
        action = self.redo_stack.pop()
        self.undo_stack.push(action)
        return action
