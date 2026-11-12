"""Estruturas de Dados: Listas Encadeadas (Singly & Doubly Linked Lists).

Implementa nós independentes com ponteiros de encadeamento.
Utilizado no EcoBounty para:
- Trilha encadeada de auditoria de missões (auditoria imutável / timeline de checkpoints)
- Buckets de colisão nas Tabelas Hash por Encadeamento Separado.
"""
from typing import Any, Generic, Iterator, List, Optional, TypeVar

T = TypeVar("T")


class Node(Generic[T]):
    """Nó para Lista Simplesmente Encadeada."""

    def __init__(self, data: T, next_node: Optional["Node[T]"] = None):
        self.data: T = data
        self.next: Optional["Node[T]"] = next_node

    def __repr__(self) -> str:
        return f"Node({self.data})"


class LinkedList(Generic[T]):
    """Lista Simplesmente Encadeada (Singly Linked List)."""

    def __init__(self):
        self.head: Optional[Node[T]] = None
        self._size: int = 0

    def __len__(self) -> int:
        return self._size

    def is_empty(self) -> bool:
        return self.head is None

    def prepend(self, data: T) -> None:
        """Insere no início da lista. O(1)."""
        new_node = Node(data, next_node=self.head)
        self.head = new_node
        self._size += 1

    def append(self, data: T) -> None:
        """Insere no final da lista. O(N) sem tail pointer ou O(1) se mantido."""
        new_node = Node(data)
        if self.head is None:
            self.head = new_node
        else:
            curr = self.head
            while curr.next is not None:
                curr = curr.next
            curr.next = new_node
        self._size += 1

    def insert_at(self, index: int, data: T) -> None:
        """Insere em uma posição específica da lista encadeada."""
        if index < 0 or index > self._size:
            raise IndexError(f"Índice de inserção inválido: {index}")
        if index == 0:
            self.prepend(data)
            return

        curr = self.head
        for _ in range(index - 1):
            if curr is None:
                break
            curr = curr.next

        if curr is None:
            raise IndexError("Falha ao navegar no nó")
        new_node = Node(data, next_node=curr.next)
        curr.next = new_node
        self._size += 1

    def remove(self, data: T) -> bool:
        """Remove a primeira ocorrência do valor. Retorna True se encontrado e removido."""
        if self.head is None:
            return False

        if self.head.data == data:
            self.head = self.head.next
            self._size -= 1
            return True

        curr = self.head
        while curr.next is not None and curr.next.data != data:
            curr = curr.next

        if curr.next is not None:
            curr.next = curr.next.next
            self._size -= 1
            return True
        return False

    def remove_at(self, index: int) -> T:
        """Remove o elemento no índice especificado e retorna seu valor."""
        if index < 0 or index >= self._size or self.head is None:
            raise IndexError(f"Índice inválido: {index}")

        if index == 0:
            val = self.head.data
            self.head = self.head.next
            self._size -= 1
            return val

        curr = self.head
        for _ in range(index - 1):
            if curr is None or curr.next is None:
                raise IndexError(f"Índice inacessível: {index}")
            curr = curr.next

        if curr.next is None:
            raise IndexError(f"Índice inacessível: {index}")

        val = curr.next.data
        curr.next = curr.next.next
        self._size -= 1
        return val

    def find(self, predicate) -> Optional[T]:
        """Busca o primeiro elemento que satisfaz a condição."""
        curr = self.head
        while curr is not None:
            if predicate(curr.data):
                return curr.data
            curr = curr.next
        return None

    def to_list(self) -> List[T]:
        """Converte todos os nós para lista Python nativa."""
        result: List[T] = []
        curr = self.head
        while curr is not None:
            result.append(curr.data)
            curr = curr.next
        return result

    def __iter__(self) -> Iterator[T]:
        curr = self.head
        while curr is not None:
            yield curr.data
            curr = curr.next

    def __repr__(self) -> str:
        return f"LinkedList({self.to_list()})"


class DoublyNode(Generic[T]):
    """Nó para Lista Duplamente Encadeada com ponteiros prev e next."""

    def __init__(
        self,
        data: T,
        prev_node: Optional["DoublyNode[T]"] = None,
        next_node: Optional["DoublyNode[T]"] = None,
    ):
        self.data: T = data
        self.prev: Optional["DoublyNode[T]"] = prev_node
        self.next: Optional["DoublyNode[T]"] = next_node


class DoublyLinkedList(Generic[T]):
    """Lista Duplamente Encadeada (Doubly Linked List). Permite navegação bidirecional."""

    def __init__(self):
        self.head: Optional[DoublyNode[T]] = None
        self.tail: Optional[DoublyNode[T]] = None
        self._size: int = 0

    def __len__(self) -> int:
        return self._size

    def is_empty(self) -> bool:
        return self.head is None

    def prepend(self, data: T) -> None:
        """Insere no início. O(1)."""
        new_node = DoublyNode(data, prev_node=None, next_node=self.head)
        if self.head is not None:
            self.head.prev = new_node
        else:
            self.tail = new_node
        self.head = new_node
        self._size += 1

    def append(self, data: T) -> None:
        """Insere no final. O(1)."""
        new_node = DoublyNode(data, prev_node=self.tail, next_node=None)
        if self.tail is not None:
            self.tail.next = new_node
        else:
            self.head = new_node
        self.tail = new_node
        self._size += 1

    def remove_node(self, node: DoublyNode[T]) -> T:
        """Remove um nó arbitrário da lista duplamente encadeada em O(1)."""
        if node.prev is not None:
            node.prev.next = node.next
        else:
            self.head = node.next

        if node.next is not None:
            node.next.prev = node.prev
        else:
            self.tail = node.prev

        self._size = max(0, self._size - 1)
        return node.data

    def pop_head(self) -> T:
        """Remove e retorna o elemento inicial (head). O(1)."""
        if self.head is None:
            raise IndexError("pop de lista duplamente encadeada vazia")
        return self.remove_node(self.head)

    def pop_tail(self) -> T:
        """Remove e retorna o elemento final (tail). O(1)."""
        if self.tail is None:
            raise IndexError("pop de lista duplamente encadeada vazia")
        return self.remove_node(self.tail)

    def peek_head(self) -> Optional[T]:
        return self.head.data if self.head is not None else None

    def peek_tail(self) -> Optional[T]:
        return self.tail.data if self.tail is not None else None

    def clear(self) -> None:
        self.head = None
        self.tail = None
        self._size = 0

    def to_list(self) -> List[T]:
        result: List[T] = []
        curr = self.head
        while curr is not None:
            result.append(curr.data)
            curr = curr.next
        return result

    def __iter__(self) -> Iterator[T]:
        curr = self.head
        while curr is not None:
            yield curr.data
            curr = curr.next

    def __repr__(self) -> str:
        return f"DoublyLinkedList({self.to_list()})"
