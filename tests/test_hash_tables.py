"""Testes unitários rigorosos para o Diferencial 1 (Tabelas Hash e Métodos de Dispersão).

Cobre:
- Tabela Hash com Encadeamento Separado (SeparateChainingHashTable)
- Tabela Hash com Endereçamento Aberto (OpenAddressingHashTable com Sondagem Linear e Hash Duplo)
- Métodos da Divisão e Multiplicação (Knuth)
- Rehash dinâmico e tratamento de Tombstones
- Justificativa de software aplicada ao EcoBounty
"""
import pytest
from typing import Any, Optional

from app.data_structures.linked_list import LinkedList
from app.data_structures.hash_table import (
    SeparateChainingHashTable,
    OpenAddressingHashTable,
    HashMethod,
    OpenAddressingStrategy,
    is_prime,
)


# ============================================================================
# 1. Testes de Encadeamento Separado (Separate Chaining)
# ============================================================================

def test_separate_chaining_put_get_update():
    ht = SeparateChainingHashTable[str, str](initial_capacity=7, method=HashMethod.DIVISION)
    assert len(ht) == 0
    assert ht.is_empty if hasattr(ht, "is_empty") else len(ht) == 0

    ht.put("plastico", "Reciclável R$ 25,00")
    ht.put("vidro", "Reciclável R$ 15,00")
    ht.put("metal", "Reciclável R$ 40,00")

    assert ht.get("plastico") == "Reciclável R$ 25,00"
    assert ht.get("vidro") == "Reciclável R$ 15,00"
    assert ht.get("metal") == "Reciclável R$ 40,00"
    assert ht.get("inexistente") is None
    assert len(ht) == 3

    # Atualização de chave já existente
    ht.put("plastico", "Reciclável R$ 30,00 (Preço Atualizado)")
    assert ht.get("plastico") == "Reciclável R$ 30,00 (Preço Atualizado)"
    assert len(ht) == 3


def test_separate_chaining_collisions_and_removal():
    # Capacidade baixa para forçar colisões controladas
    ht = SeparateChainingHashTable[int, str](initial_capacity=7, method=HashMethod.DIVISION)

    # 1 % 7 == 1, 8 % 7 == 1, 15 % 7 == 1 (todas colidem no bucket 1)
    ht.put(1, "Item_1")
    ht.put(8, "Item_8")
    ht.put(15, "Item_15")

    assert ht.get(1) == "Item_1"
    assert ht.get(8) == "Item_8"
    assert ht.get(15) == "Item_15"
    assert len(ht) == 3

    stats = ht.get_distribution_stats()
    assert stats["collisions_count"] >= 2
    assert stats["max_chain_length"] >= 3

    # Remoção de elemento da cadeia
    assert ht.remove(8) is True
    assert ht.get(8) is None
    assert ht.get(1) == "Item_1"
    assert ht.get(15) == "Item_15"
    assert len(ht) == 2

    assert ht.remove(999) is False


def test_separate_chaining_multiplication_method_and_rehash():
    ht = SeparateChainingHashTable[int, str](initial_capacity=7, method=HashMethod.MULTIPLICATION)
    initial_cap = ht.capacity

    # Inserção em massa para disparar rehash dinâmico (alfa > 1.5)
    for i in range(25):
        ht.put(i, f"Val_{i}")

    assert ht.capacity > initial_cap
    assert len(ht) == 25
    for i in range(25):
        assert ht.get(i) == f"Val_{i}"


# ============================================================================
# 2. Testes de Endereçamento Aberto (Open Addressing: Linear & Hash Duplo)
# ============================================================================

def test_open_addressing_linear_probing():
    ht = OpenAddressingHashTable[str, str](
        initial_capacity=11,
        strategy=OpenAddressingStrategy.LINEAR_PROBING,
    )

    ht.put("ECOPONTO-1", "Jatiúca")
    ht.put("ECOPONTO-2", "Ponta Verde")
    ht.put("ECOPONTO-3", "Pajuçara")

    assert ht.get("ECOPONTO-1") == "Jatiúca"
    assert ht.get("ECOPONTO-2") == "Ponta Verde"
    assert ht.get("ECOPONTO-3") == "Pajuçara"
    assert ht.get("ECOPONTO-999") is None
    assert len(ht) == 3


def test_open_addressing_double_hashing_and_tombstone():
    ht = OpenAddressingHashTable[str, str](
        initial_capacity=11,
        strategy=OpenAddressingStrategy.DOUBLE_HASHING,
    )

    ht.put("TOKEN_USER_A", "Session_Mathias")
    ht.put("TOKEN_USER_B", "Session_Allan")
    ht.put("TOKEN_USER_C", "Session_Kaue")

    assert len(ht) == 3
    assert "TOKEN_USER_B" in ht

    # Remove um elemento do meio criando marcador TOMBSTONE
    assert ht.remove("TOKEN_USER_B") is True
    assert ht.get("TOKEN_USER_B") is None
    assert len(ht) == 2

    # As outras chaves devem continuar encontráveis após pular o tombstone
    assert ht.get("TOKEN_USER_A") == "Session_Mathias"
    assert ht.get("TOKEN_USER_C") == "Session_Kaue"

    # Inserção subsequente deve reutilizar o slot livre ou expandir normalmente
    ht.put("TOKEN_USER_D", "Session_Novo")
    assert ht.get("TOKEN_USER_D") == "Session_Novo"
    assert len(ht) == 3


def test_open_addressing_automatic_rehash_at_threshold():
    ht = OpenAddressingHashTable[int, str](
        initial_capacity=11,
        strategy=OpenAddressingStrategy.DOUBLE_HASHING,
    )
    initial_cap = ht.capacity

    # Inserção até superar fator de carga 0.70 (11 * 0.70 = 7.7)
    for i in range(9):
        ht.put(i, f"Dado_{i}")

    # Deve ter expandido a capacidade
    assert ht.capacity > initial_cap
    assert len(ht) == 9
    for i in range(9):
        assert ht.get(i) == f"Dado_{i}"


def test_hash_table_none_value_support():
    # Encadeamento Separado com valor None
    ch = SeparateChainingHashTable[str, Optional[int]]()
    ch.put("chave_nula", None)
    assert "chave_nula" in ch
    assert ch.contains("chave_nula") is True
    assert ch.get("chave_nula") is None
    assert ch["chave_nula"] is None
    assert len(ch) == 1

    # Endereçamento Aberto com valor None
    op = OpenAddressingHashTable[str, Optional[str]]()
    op.put("sessao_vazia", None)
    assert "sessao_vazia" in op
    assert op.contains("sessao_vazia") is True
    assert op.get("sessao_vazia") is None
    assert op["sessao_vazia"] is None
    assert len(op) == 1


def test_open_addressing_none_key_raises_error():
    op = OpenAddressingHashTable[Any, str]()
    with pytest.raises(ValueError, match="A chave não pode ser None"):
        op.put(None, "valor")


def test_separate_chaining_uses_linked_list_buckets():
    ch = SeparateChainingHashTable[str, str](initial_capacity=7)
    for b in ch._buckets:
        assert isinstance(b, LinkedList)


def test_open_addressing_capacity_always_prime():
    op = OpenAddressingHashTable[int, int](initial_capacity=10)
    assert is_prime(op.capacity)

    for i in range(50):
        op.put(i, i * 2)
        assert is_prime(op.capacity)

