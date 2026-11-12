"""Estrutura de Dados: Lista Linear Restrita (RestrictedLinearList / ListaLinearRestrita).

Estrutura linear de alocação sequencial com restrição rígida de capacidade (Bounded Array).
Garante controle estrito de overflow e underflow, integridade referencial contígua
e verificação de capacidade.

Utilizada no EcoBounty para:
- Slots de missões ativas concorrentes do coletor (limite regulamentar de no máx. K missões simultâneas)
- Buffer restrito de auditoria em campo
"""
from typing import Any, Generic, Iterator, List, Optional, TypeVar

T = TypeVar("T")


class RestrictedLinearListOverflowError(Exception):
    """Lançado ao tentar inserir em lista linear restrita cheia."""
    pass


class RestrictedLinearListUnderflowError(Exception):
    """Lançado ao tentar remover de lista linear restrita vazia."""
    pass


class RestrictedLinearList(Generic[T]):
    """Lista Linear Sequencial Restrita com capacidade fixa máxima."""

    def __init__(self, max_capacity: int = 5):
        if max_capacity <= 0:
            raise ValueError("A capacidade máxima deve ser maior que zero")
        self._max_capacity: int = max_capacity
        self._size: int = 0
        self._items: List[Optional[T]] = [None] * max_capacity

    @property
    def max_capacity(self) -> int:
        return self._max_capacity

    def __len__(self) -> int:
        return self._size

    def is_empty(self) -> bool:
        return self._size == 0

    def is_full(self) -> bool:
        return self._size == self._max_capacity

    def insert(self, item: T, position: Optional[int] = None) -> None:
        """Insere um elemento na posição especificada ou ao final (se position=None).
        Lança RestrictedLinearListOverflowError se atingir a capacidade máxima.
        """
        if self.is_full():
            raise RestrictedLinearListOverflowError(
                f"Capacidade máxima excedida: {self._size}/{self._max_capacity} slots ocupados"
            )

        if position is None:
            position = self._size

        if position < 0 or position > self._size:
            raise IndexError(f"Posição de inserção inválida: {position} (tamanho {self._size})")

        # Desloca elementos à direita
        for i in range(self._size, position, -1):
            self._items[i] = self._items[i - 1]

        self._items[position] = item
        self._size += 1

    def remove_at(self, position: int) -> T:
        """Remove o elemento na posição especificada.
        Lança RestrictedLinearListUnderflowError se a lista estiver vazia.
        """
        if self.is_empty():
            raise RestrictedLinearListUnderflowError("Lista vazia, impossível remover")

        if position < 0 or position >= self._size:
            raise IndexError(f"Posição de remoção inválida: {position}")

        removed = self._items[position]
        for i in range(position, self._size - 1):
            self._items[i] = self._items[i + 1]

        self._items[self._size - 1] = None
        self._size -= 1
        return removed  # type: ignore

    def remove_item(self, item: T) -> bool:
        """Remove a primeira ocorrência do item. Retorna True se encontrado."""
        for i in range(self._size):
            if self._items[i] == item:
                self.remove_at(i)
                return True
        return False

    def get(self, index: int) -> T:
        if index < 0 or index >= self._size:
            raise IndexError(f"Índice inválido: {index}")
        return self._items[index]  # type: ignore

    def search(self, item: T) -> int:
        """Busca sequencial pelo elemento. Retorna o índice ou -1 se não encontrado."""
        for i in range(self._size):
            if self._items[i] == item:
                return i
        return -1

    def clear(self) -> None:
        """Esvazia todos os slots."""
        self._items = [None] * self._max_capacity
        self._size = 0

    def to_list(self) -> List[T]:
        return [self._items[i] for i in range(self._size)]  # type: ignore

    def __iter__(self) -> Iterator[T]:
        for i in range(self._size):
            yield self._items[i]  # type: ignore

    def __repr__(self) -> str:
        return f"RestrictedLinearList({self.to_list()}, max={self._max_capacity})"
