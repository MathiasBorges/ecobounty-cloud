"""Estrutura de Dados: Vetor Dinâmico (CustomVector / VetorDinamico).

Implementa array redimensionável com fator de crescimento geométrico (2x),
acesso indexado O(1), inserção, remoção e busca.
Utilizado no EcoBounty para o catálogo contíguo de bounties e coleções
de alta performance com cache locality.
"""
from typing import Any, Generic, Iterator, List, Optional, TypeVar

T = TypeVar("T")


class CustomVector(Generic[T]):
    """Vetor dinâmico com realocação geométrica e acesso O(1)."""

    def __init__(self, initial_capacity: int = 4):
        if initial_capacity < 1:
            initial_capacity = 4
        self._capacity: int = initial_capacity
        self._size: int = 0
        self._data: List[Optional[T]] = [None] * self._capacity

    @property
    def capacity(self) -> int:
        return self._capacity

    def __len__(self) -> int:
        return self._size

    def is_empty(self) -> bool:
        return self._size == 0

    def _resize(self, new_capacity: int) -> None:
        new_data: List[Optional[T]] = [None] * new_capacity
        for i in range(self._size):
            new_data[i] = self._data[i]
        self._data = new_data
        self._capacity = new_capacity

    def append(self, item: T) -> None:
        """Adiciona um elemento ao final do vetor. O(1) amortizado."""
        if self._size == self._capacity:
            self._resize(self._capacity * 2)
        self._data[self._size] = item
        self._size += 1

    def _normalize_index(self, index: int) -> int:
        norm = index + self._size if index < 0 else index
        if norm < 0 or norm >= self._size:
            raise IndexError(f"Índice fora dos limites: {index} (tamanho {self._size})")
        return norm

    def get(self, index: int) -> T:
        """Obtém elemento pelo índice. O(1). Suporta índices negativos."""
        norm_idx = self._normalize_index(index)
        return self._data[norm_idx]  # type: ignore

    def set(self, index: int, value: T) -> None:
        """Atualiza elemento no índice especificado. O(1). Suporta índices negativos."""
        norm_idx = self._normalize_index(index)
        self._data[norm_idx] = value

    def insert(self, index: int, item: T) -> None:
        """Insere um elemento no índice especificado deslocando os posteriores. O(N)."""
        if index < 0:
            index += self._size
        if index < 0 or index > self._size:
            raise IndexError(f"Índice de inserção inválido: {index} (tamanho {self._size})")
        if self._size == self._capacity:
            self._resize(self._capacity * 2)
        for i in range(self._size, index, -1):
            self._data[i] = self._data[i - 1]
        self._data[index] = item
        self._size += 1

    def remove_at(self, index: int) -> T:
        """Remove o elemento no índice especificado e desloca os elementos. O(N). Suporta índices negativos."""
        norm_idx = self._normalize_index(index)
        removed = self._data[norm_idx]
        for i in range(norm_idx, self._size - 1):
            self._data[i] = self._data[i + 1]
        self._data[self._size - 1] = None
        self._size -= 1
        # Reduz capacidade se a ocupação cair para 1/4 da capacidade (mantendo min 4)
        if 0 < self._size <= self._capacity // 4 and self._capacity > 4:
            self._resize(max(4, self._capacity // 2))
        return removed  # type: ignore

    def pop(self) -> T:
        """Remove e retorna o último elemento. O(1) amortizado."""
        if self.is_empty():
            raise IndexError("pop de vetor vazio")
        return self.remove_at(self._size - 1)

    def find_first(self, predicate) -> Optional[T]:
        """Retorna o primeiro elemento que satisfaz a função predicado."""
        for i in range(self._size):
            item = self._data[i]
            if predicate(item):
                return item
        return None

    def clear(self) -> None:
        """Limpa o vetor mantendo a capacidade inicial padrão."""
        self._capacity = 4
        self._size = 0
        self._data = [None] * self._capacity

    def to_list(self) -> List[T]:
        """Converte para lista padrão Python."""
        return [self._data[i] for i in range(self._size)]  # type: ignore

    def __getitem__(self, index: int) -> T:
        return self.get(index)

    def __setitem__(self, index: int, value: T) -> None:
        self.set(index, value)

    def __iter__(self) -> Iterator[T]:
        for i in range(self._size):
            yield self._data[i]  # type: ignore

    def __repr__(self) -> str:
        return f"CustomVector({self.to_list()})"
