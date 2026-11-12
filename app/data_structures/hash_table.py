"""Diferencial 1 do Projeto (2ª Unidade - Obrigatório): Tabelas Hash e Métodos Aplicados.

Implementação completa e formal de Tabelas Hash com:
1. Métodos de Dispersão (Hash Functions):
   - Método da Divisão: h(k) = k mod m
   - Método da Multiplicação (Knuth): h(k) = floor(m * ((k * A) mod 1)), onde A = (sqrt(5) - 1) / 2
   - Hashing Polinomial para strings (djb2)
2. Tratamento de Colisões:
   - Encadeamento Separado (Separate Chaining): lista encadeada pura (LinkedList) por bucket
   - Endereçamento Aberto (Open Addressing): Sondagem Linear (Linear Probing) e Hash Duplo (Double Hashing) com capacidade prima estrita

JUSTIFICATIVA DE SOFTWARE (Para Apresentação):
--------------------------------------------------------------------------------------------------
A) Encadeamento Separado (Separate Chaining):
   - Aplicação no EcoBounty: Catálogo Geral de Denúncias e Indexação de Bounties por Categoria/Bairro.
   - Justificativa Técnica: O volume de denúncias ambientais é imprevisível e altamente volátil,
     com frequentes inserções (novas denúncias) e remoções (missões concluídas). O encadeamento
     baseado em LinkedList não sofre com agrupamento primário ou secundário (clustering) e tolera picos onde o fator de carga
     alfa > 1 sem interrupção de serviço, garantindo flexibilidade e estabilidade.

B) Endereçamento Aberto (Open Addressing - Linear Probing & Double Hashing):
   - Aplicação no EcoBounty: Cache de Sessões de Usuários Conectados e Lookup de Ecopontos por QR Code.
   - Justificativa Técnica: O número de ecopontos e sessões ativas é delimitado e de alta frequência
     de consulta por segundo. Ao alocar chaves diretamente no vetor contíguo de memória sem nós
     adicionais, maximiza-se a localidade espacial da memória cache da CPU (L1/L2), eliminando o
     overhead de ponteiros da lista encadeada e atingindo latência de consulta O(1) estrita.
--------------------------------------------------------------------------------------------------
"""
import math
from typing import Any, Callable, Generic, Iterator, List, Optional, Tuple, TypeVar

from app.data_structures.linked_list import LinkedList

K = TypeVar("K")
V = TypeVar("V")

# Constante de Knuth para o método da multiplicação: (sqrt(5) - 1) / 2
KNUTH_A = (math.sqrt(5) - 1.0) / 2.0


def is_prime(n: int) -> bool:
    """Verifica se um número inteiro é primo."""
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def next_prime(n: int) -> int:
    """Retorna o menor número primo maior ou igual a n."""
    candidate = max(2, n)
    while not is_prime(candidate):
        candidate += 1
    return candidate


def hash_string_djb2(key_str: str) -> int:
    """Função de dispersão polinomial clássica djb2 para strings."""
    h = 5381
    for char in key_str:
        h = ((h << 5) + h) + ord(char)  # h * 33 + c
        h &= 0xFFFFFFFF  # Limita a 32 bits
    return h


def to_hash_code(key: Any) -> int:
    """Converte qualquer chave Python para um inteiro positivo determinístico."""
    if key is None:
        return 0
    if isinstance(key, int):
        return abs(key)
    if isinstance(key, str):
        return hash_string_djb2(key)
    return abs(hash(key))


class HashMethod:
    DIVISION = "division"
    MULTIPLICATION = "multiplication"


class OpenAddressingStrategy:
    LINEAR_PROBING = "linear_probing"
    DOUBLE_HASHING = "double_hashing"


class SeparateChainingHashTable(Generic[K, V]):
    """Tabela Hash com tratamento de colisões por Encadeamento Separado (Separate Chaining).

    Utiliza LinkedList pura (1ª Unidade) em cada bucket, interligando formalmente
    as estruturas de dados lineares ao catálogo de dispersão.
    """

    def __init__(self, initial_capacity: int = 11, method: str = HashMethod.DIVISION):
        self._capacity: int = next_prime(max(7, initial_capacity))
        self._size: int = 0
        self._method: str = method
        self._buckets: List[LinkedList[Tuple[K, V]]] = [
            LinkedList[Tuple[K, V]]() for _ in range(self._capacity)
        ]

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        return self._size

    @property
    def load_factor(self) -> float:
        """Fator de carga alfa = n / m."""
        return self._size / self._capacity

    def _hash(self, key: K) -> int:
        code = to_hash_code(key)
        if self._method == HashMethod.MULTIPLICATION:
            # Metodo da Multiplicacao de Knuth: floor(m * (k * A mod 1))
            val = (code * KNUTH_A) % 1.0
            return int(self._capacity * val) % self._capacity
        else:
            # Metodo da Divisao: k mod m
            return code % self._capacity

    def put(self, key: K, value: V) -> None:
        """Insere ou atualiza um par chave-valor. O(1) médio."""
        idx = self._hash(key)
        bucket = self._buckets[idx]

        # Busca chave já existente no bucket (LinkedList)
        curr = bucket.head
        while curr is not None:
            if curr.data[0] == key:
                curr.data = (key, value)
                return
            curr = curr.next

        # Se não existia, insere no início da lista encadeada em O(1)
        bucket.prepend((key, value))
        self._size += 1

        # Redimensiona se o fator de carga for excessivo (alfa > 1.5)
        if self.load_factor > 1.5:
            self._rehash(next_prime(self._capacity * 2 + 1))

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """Recupera o valor associado à chave ou default se não existir. O(1) médio."""
        idx = self._hash(key)
        bucket = self._buckets[idx]
        curr = bucket.head
        while curr is not None:
            if curr.data[0] == key:
                return curr.data[1]
            curr = curr.next
        return default

    def remove(self, key: K) -> bool:
        """Remove a chave da tabela. Retorna True se existia e foi removida."""
        idx = self._hash(key)
        bucket = self._buckets[idx]

        prev = None
        curr = bucket.head
        while curr is not None:
            if curr.data[0] == key:
                if prev is None:
                    bucket.head = curr.next
                else:
                    prev.next = curr.next
                bucket._size -= 1
                self._size -= 1
                return True
            prev = curr
            curr = curr.next
        return False

    def contains(self, key: K) -> bool:
        """Verifica presença da chave no bucket, independentemente do valor associado."""
        idx = self._hash(key)
        bucket = self._buckets[idx]
        curr = bucket.head
        while curr is not None:
            if curr.data[0] == key:
                return True
            curr = curr.next
        return False

    def _rehash(self, new_capacity: int) -> None:
        old_buckets = self._buckets
        self._capacity = next_prime(new_capacity)
        self._buckets = [LinkedList[Tuple[K, V]]() for _ in range(self._capacity)]
        self._size = 0
        for bucket in old_buckets:
            for k, v in bucket:
                self.put(k, v)

    def get_distribution_stats(self) -> dict:
        """Retorna estatísticas sobre dispersão de chaves e colisões nos buckets."""
        lengths = [len(b) for b in self._buckets]
        collisions = sum(max(0, l - 1) for l in lengths)
        return {
            "capacity": self._capacity,
            "size": self._size,
            "load_factor": round(self.load_factor, 3),
            "collisions_count": collisions,
            "empty_buckets": lengths.count(0),
            "max_chain_length": max(lengths) if lengths else 0,
        }

    def keys(self) -> List[K]:
        res: List[K] = []
        for bucket in self._buckets:
            for k, _ in bucket:
                res.append(k)
        return res

    def values(self) -> List[V]:
        res: List[V] = []
        for bucket in self._buckets:
            for _, v in bucket:
                res.append(v)
        return res

    def items(self) -> List[Tuple[K, V]]:
        res: List[Tuple[K, V]] = []
        for bucket in self._buckets:
            for pair in bucket:
                res.append(pair)
        return res

    def __getitem__(self, key: K) -> V:
        idx = self._hash(key)
        bucket = self._buckets[idx]
        curr = bucket.head
        while curr is not None:
            if curr.data[0] == key:
                return curr.data[1]
            curr = curr.next
        raise KeyError(f"Chave '{key}' não encontrada")

    def __setitem__(self, key: K, value: V) -> None:
        self.put(key, value)

    def __contains__(self, key: K) -> bool:
        return self.contains(key)

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[K]:
        for k in self.keys():
            yield k

    def __repr__(self) -> str:
        return f"SeparateChainingHashTable(size={self._size}, capacity={self._capacity}, load_factor={self.load_factor:.2f})"


class _Tombstone:
    """Marcador sentinela para slots removidos em Endereçamento Aberto."""
    def __repr__(self) -> str:
        return "<TOMBSTONE>"


class _EmptySlot:
    """Marcador sentinela para slots vazios em Endereçamento Aberto."""
    def __repr__(self) -> str:
        return "<EMPTY>"


TOMBSTONE = _Tombstone()
EMPTY_SLOT = _EmptySlot()


class OpenAddressingHashTable(Generic[K, V]):
    """Tabela Hash com Endereçamento Aberto (Open Addressing).

    Suporta Sondagem Linear (Linear Probing) e Hash Duplo (Double Hashing).
    Capacidade sempre prima para garantia matemática de coprimilidade e ciclo completo.
    Ideal para Cache de Sessões de Usuários e Lookup Rápido de Ecopontos (máxima localidade de CPU cache).
    """

    def __init__(
        self,
        initial_capacity: int = 17,
        strategy: str = OpenAddressingStrategy.DOUBLE_HASHING,
        hash_method: str = HashMethod.DIVISION,
    ):
        self._capacity: int = next_prime(max(11, initial_capacity))
        self._size: int = 0
        self._tombstones: int = 0
        self._strategy: str = strategy
        self._hash_method: str = hash_method
        self._keys: List[Any] = [EMPTY_SLOT] * self._capacity
        self._values: List[Any] = [None] * self._capacity

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        return self._size

    @property
    def load_factor(self) -> float:
        return self._size / self._capacity

    def _h1(self, code: int) -> int:
        """Primeira função hash (método da divisão ou multiplicação)."""
        if self._hash_method == HashMethod.MULTIPLICATION:
            val = (code * KNUTH_A) % 1.0
            return int(self._capacity * val) % self._capacity
        return code % self._capacity

    def _h2(self, code: int) -> int:
        """Segunda função hash para Double Hashing: passo coprimo com a capacidade prima."""
        # Como self._capacity é primo, qualquer passo entre 1 e self._capacity - 1 é coprimo
        step = 1 + (code % (self._capacity - 1))
        return step

    def _probe_index(self, code: int, step_i: int) -> int:
        """Calcula o índice de sondagem para a i-ésima tentativa."""
        base = self._h1(code)
        if self._strategy == OpenAddressingStrategy.LINEAR_PROBING:
            return (base + step_i) % self._capacity
        else:
            # Double Hashing: (h1 + i * h2) mod m
            h2 = self._h2(code)
            return (base + step_i * h2) % self._capacity

    def put(self, key: K, value: V) -> None:
        """Insere ou atualiza par chave-valor no vetor contíguo. O(1) amortizado."""
        if key is None:
            raise ValueError("A chave não pode ser None em OpenAddressingHashTable")

        # Se ocupação efetiva (chaves + tombstones) atingir 0.70, dispara rehash
        if (self._size + self._tombstones) / self._capacity >= 0.70:
            self._rehash(self._capacity * 2 + 1)

        code = to_hash_code(key)
        first_tombstone_idx: Optional[int] = None

        for i in range(self._capacity):
            idx = self._probe_index(code, i)
            current_key = self._keys[idx]

            if current_key is EMPTY_SLOT:
                # Encontrou slot vazio
                if first_tombstone_idx is not None:
                    target_idx = first_tombstone_idx
                    self._tombstones -= 1
                else:
                    target_idx = idx
                self._keys[target_idx] = key
                self._values[target_idx] = value
                self._size += 1
                return

            if current_key is TOMBSTONE:
                if first_tombstone_idx is None:
                    first_tombstone_idx = idx
                continue

            if current_key == key:
                # Atualização de chave já existente
                self._values[idx] = value
                return

        # Se percorreu toda a tabela e encontrou tombstone
        if first_tombstone_idx is not None:
            self._keys[first_tombstone_idx] = key
            self._values[first_tombstone_idx] = value
            self._tombstones -= 1
            self._size += 1
            return

        # Tabela cheia sem slots
        self._rehash(self._capacity * 2 + 1)
        self.put(key, value)

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """Busca o valor associado à chave usando a sequência de sondagem. O(1)."""
        if key is None:
            return default
        code = to_hash_code(key)
        for i in range(self._capacity):
            idx = self._probe_index(code, i)
            current_key = self._keys[idx]

            if current_key is EMPTY_SLOT:
                return default  # Não encontrado

            if current_key is not TOMBSTONE and current_key == key:
                return self._values[idx]

        return default

    def remove(self, key: K) -> bool:
        """Remove uma chave inserindo um marcador TOMBSTONE no slot."""
        if key is None:
            return False
        code = to_hash_code(key)
        for i in range(self._capacity):
            idx = self._probe_index(code, i)
            current_key = self._keys[idx]

            if current_key is EMPTY_SLOT:
                return False

            if current_key is not TOMBSTONE and current_key == key:
                self._keys[idx] = TOMBSTONE
                self._values[idx] = None
                self._size -= 1
                self._tombstones += 1
                return True

        return False

    def contains(self, key: K) -> bool:
        """Verifica se a chave está presente na tabela de forma independente do valor."""
        if key is None:
            return False
        code = to_hash_code(key)
        for i in range(self._capacity):
            idx = self._probe_index(code, i)
            current_key = self._keys[idx]

            if current_key is EMPTY_SLOT:
                return False

            if current_key is not TOMBSTONE and current_key == key:
                return True

        return False

    def _rehash(self, new_capacity: int) -> None:
        old_keys = self._keys
        old_values = self._values

        self._capacity = next_prime(new_capacity)
        self._keys = [EMPTY_SLOT] * self._capacity
        self._values = [None] * self._capacity
        self._size = 0
        self._tombstones = 0

        for k, v in zip(old_keys, old_values):
            if k is not EMPTY_SLOT and k is not TOMBSTONE:
                self.put(k, v)

    def keys(self) -> List[K]:
        return [k for k in self._keys if k is not EMPTY_SLOT and k is not TOMBSTONE]

    def values(self) -> List[V]:
        return [v for k, v in zip(self._keys, self._values) if k is not EMPTY_SLOT and k is not TOMBSTONE]

    def items(self) -> List[Tuple[K, V]]:
        return [
            (k, v)
            for k, v in zip(self._keys, self._values)
            if k is not EMPTY_SLOT and k is not TOMBSTONE
        ]

    def __getitem__(self, key: K) -> V:
        if not self.contains(key):
            raise KeyError(f"Chave '{key}' não encontrada")
        return self.get(key)

    def __setitem__(self, key: K, value: V) -> None:
        self.put(key, value)

    def __contains__(self, key: K) -> bool:
        return self.contains(key)

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[K]:
        for k in self.keys():
            yield k

    def __repr__(self) -> str:
        return f"OpenAddressingHashTable(strategy={self._strategy}, size={self._size}, capacity={self._capacity}, load_factor={self.load_factor:.2f})"
