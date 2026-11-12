"""Módulo de Estruturas de Dados do EcoBounty.

Contempla todos os requisitos da 1ª Unidade (Vetores, Listas Encadeadas,
Listas Lineares Restritas, Pilhas, Filas, Deques) e Diferencial 1 da 2ª Unidade
(Tabelas Hash por Encadeamento e Endereçamento Aberto com justificativa de software).
"""
from app.data_structures.vector import CustomVector
from app.data_structures.linked_list import Node, LinkedList, DoublyNode, DoublyLinkedList
from app.data_structures.restricted_list import (
    RestrictedLinearList,
    RestrictedLinearListOverflowError,
    RestrictedLinearListUnderflowError,
)
from app.data_structures.stack import Stack, StackUnderflowError, UndoRedoManager
from app.data_structures.queue import Queue, QueueUnderflowError
from app.data_structures.deque import Deque, DequeUnderflowError
from app.data_structures.hash_table import (
    SeparateChainingHashTable,
    OpenAddressingHashTable,
    HashMethod,
    OpenAddressingStrategy,
)

__all__ = [
    "CustomVector",
    "Node",
    "LinkedList",
    "DoublyNode",
    "DoublyLinkedList",
    "RestrictedLinearList",
    "RestrictedLinearListOverflowError",
    "RestrictedLinearListUnderflowError",
    "Stack",
    "StackUnderflowError",
    "UndoRedoManager",
    "Queue",
    "QueueUnderflowError",
    "Deque",
    "DequeUnderflowError",
    "SeparateChainingHashTable",
    "OpenAddressingHashTable",
    "HashMethod",
    "OpenAddressingStrategy",
]
