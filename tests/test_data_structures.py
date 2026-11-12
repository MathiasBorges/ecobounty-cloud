"""Testes unitários rigorosos para as Estruturas de Dados (1ª Unidade).

Cobre:
- CustomVector (Vetor Dinâmico com realocação geométrica)
- LinkedList & DoublyLinkedList (Listas Encadeadas simples e duplas)
- RestrictedLinearList (Lista Linear Restrita com limites rígidos)
- Stack & UndoRedoManager (Pilhas LIFO e controle de desfazer/refazer)
- Queue (Fila FIFO de auditoria)
- Deque (Fila com duas extremidades e priorização)
"""
import pytest

from app.data_structures.vector import CustomVector
from app.data_structures.linked_list import LinkedList, DoublyLinkedList, Node, DoublyNode
from app.data_structures.restricted_list import (
    RestrictedLinearList,
    RestrictedLinearListOverflowError,
    RestrictedLinearListUnderflowError,
)
from app.data_structures.stack import Stack, StackUnderflowError, UndoRedoManager
from app.data_structures.queue import Queue, QueueUnderflowError
from app.data_structures.deque import Deque, DequeUnderflowError


# ============================================================================
# 1. Testes de Vetor Dinâmico (CustomVector)
# ============================================================================

def test_custom_vector_append_and_geometric_resize():
    vec = CustomVector[int](initial_capacity=2)
    assert vec.capacity == 2
    assert len(vec) == 0
    assert vec.is_empty()

    vec.append(10)
    vec.append(20)
    assert len(vec) == 2
    assert vec.capacity == 2

    # Próximo append deve dobrar a capacidade (2 -> 4)
    vec.append(30)
    assert len(vec) == 3
    assert vec.capacity == 4
    assert vec.get(0) == 10
    assert vec.get(1) == 20
    assert vec.get(2) == 30


def test_custom_vector_insert_remove_and_pop():
    vec = CustomVector[str](initial_capacity=4)
    vec.append("A")
    vec.append("C")
    vec.insert(1, "B")  # Result: ["A", "B", "C"]
    assert vec.to_list() == ["A", "B", "C"]

    # Teste de set e get por indexador []
    vec[1] = "B_MODIFIED"
    assert vec[1] == "B_MODIFIED"

    # Remove no meio
    removed = vec.remove_at(1)
    assert removed == "B_MODIFIED"
    assert vec.to_list() == ["A", "C"]

    # Pop final
    popped = vec.pop()
    assert popped == "C"
    assert len(vec) == 1


def test_custom_vector_bounds_and_edge_cases():
    vec = CustomVector[int](initial_capacity=2)
    with pytest.raises(IndexError):
        _ = vec[0]

    with pytest.raises(IndexError):
        vec.pop()

    with pytest.raises(IndexError):
        vec.insert(5, 99)

    vec.append(42)
    assert vec.find_first(lambda x: x == 42) == 42
    assert vec.find_first(lambda x: x == 999) is None

    vec.clear()
    assert len(vec) == 0
    assert vec.is_empty()


# ============================================================================
# 2. Testes de Listas Encadeadas (LinkedList & DoublyLinkedList)
# ============================================================================

def test_singly_linked_list_operations():
    ll = LinkedList[int]()
    assert ll.is_empty()
    assert len(ll) == 0

    ll.append(100)
    ll.append(200)
    ll.prepend(50)  # [50, 100, 200]
    assert ll.to_list() == [50, 100, 200]
    assert len(ll) == 3

    # Inserção no meio
    ll.insert_at(1, 75)  # [50, 75, 100, 200]
    assert ll.to_list() == [50, 75, 100, 200]

    # Remoção por valor
    assert ll.remove(75) is True
    assert ll.remove(999) is False
    assert ll.to_list() == [50, 100, 200]

    # Remoção por índice
    removed = ll.remove_at(0)
    assert removed == 50
    assert ll.to_list() == [100, 200]

    # Busca
    assert ll.find(lambda x: x > 150) == 200
    assert ll.find(lambda x: x < 0) is None


def test_doubly_linked_list_bidirectional():
    dll = DoublyLinkedList[str]()
    dll.append("MEIO")
    dll.prepend("INICIO")
    dll.append("FIM")
    assert dll.to_list() == ["INICIO", "MEIO", "FIM"]
    assert len(dll) == 3

    # Remove o nó do meio
    curr = dll.head.next
    assert curr.data == "MEIO"
    removed = dll.remove_node(curr)
    assert removed == "MEIO"
    assert dll.to_list() == ["INICIO", "FIM"]
    assert len(dll) == 2


# ============================================================================
# 3. Testes de Lista Linear Restrita (RestrictedLinearList)
# ============================================================================

def test_restricted_linear_list_capacity_and_overflow():
    # Coletor com no máximo 3 missões simultâneas
    rlist = RestrictedLinearList[str](max_capacity=3)
    assert rlist.max_capacity == 3
    assert rlist.is_empty()
    assert not rlist.is_full()

    rlist.insert("Missao_1")
    rlist.insert("Missao_2")
    rlist.insert("Missao_3")
    assert rlist.is_full()
    assert len(rlist) == 3

    # Tentativa de exceder o limite regulamentar deve disparar OverflowError
    with pytest.raises(RestrictedLinearListOverflowError):
        rlist.insert("Missao_Excedente")


def test_restricted_linear_list_removal_and_underflow():
    rlist = RestrictedLinearList[int](max_capacity=2)
    with pytest.raises(RestrictedLinearListUnderflowError):
        rlist.remove_at(0)

    rlist.insert(10)
    rlist.insert(20)
    assert rlist.search(20) == 1
    assert rlist.search(999) == -1

    assert rlist.remove_item(10) is True
    assert rlist.remove_item(999) is False
    assert len(rlist) == 1
    assert rlist.get(0) == 20

    rlist.clear()
    assert rlist.is_empty()


# ============================================================================
# 4. Testes de Pilha (Stack) e UndoRedoManager
# ============================================================================

def test_stack_lifo_behavior():
    stack = Stack[int](max_size=3)
    assert stack.is_empty()

    with pytest.raises(StackUnderflowError):
        stack.pop()

    stack.push(1)
    stack.push(2)
    stack.push(3)
    assert stack.peek() == 3
    assert len(stack) == 3

    # Política de substituição de mais antigo se ultrapassar capacidade máxima
    stack.push(4)
    assert len(stack) == 3
    assert stack.to_list() == [2, 3, 4]

    assert stack.pop() == 4
    assert stack.pop() == 3
    assert stack.pop() == 2
    assert stack.is_empty()


def test_undo_redo_manager():
    mgr = UndoRedoManager[str]()
    assert not mgr.can_undo()
    assert not mgr.can_redo()

    mgr.record_action("ACEITAR_MISSAO_1")
    mgr.record_action("INICIAR_COLETA_1")
    assert mgr.can_undo()
    assert not mgr.can_redo()

    undone = mgr.undo()
    assert undone == "INICIAR_COLETA_1"
    assert mgr.can_redo()

    redone = mgr.redo()
    assert redone == "INICIAR_COLETA_1"

    # Nova ação invalida redo
    mgr.undo()
    mgr.record_action("OUTRA_ACAO")
    assert not mgr.can_redo()


# ============================================================================
# 5. Testes de Fila (Queue FIFO)
# ============================================================================

def test_queue_fifo_behavior():
    q = Queue[str](max_size=3)
    assert q.is_empty()

    with pytest.raises(QueueUnderflowError):
        q.dequeue()

    q.enqueue("FOTO_1")
    q.enqueue("FOTO_2")
    assert q.peek() == "FOTO_1"
    assert len(q) == 2

    assert q.dequeue() == "FOTO_1"
    assert q.dequeue() == "FOTO_2"
    assert q.is_empty()

    q.enqueue("FOTO_A")
    q.enqueue("FOTO_B")
    q.enqueue("FOTO_C")
    with pytest.raises(OverflowError):
        q.enqueue("FOTO_D")


# ============================================================================
# 6. Testes de Deque (Double-Ended Queue)
# ============================================================================

def test_deque_bidirectional_operations():
    deq = Deque[str](max_size=4)
    assert deq.is_empty()

    with pytest.raises(DequeUnderflowError):
        deq.pop_left()

    # Inserção normal à direita
    deq.append_right("NOTIF_NORMAL_1")
    deq.append_right("NOTIF_NORMAL_2")

    # Inserção urgente à esquerda (fura-fila)
    deq.append_left("ALERTA_URGENTE")

    assert deq.peek_left() == "ALERTA_URGENTE"
    assert deq.peek_right() == "NOTIF_NORMAL_2"
    assert len(deq) == 3

    assert deq.pop_left() == "ALERTA_URGENTE"
    assert deq.pop_right() == "NOTIF_NORMAL_2"
    assert deq.pop_left() == "NOTIF_NORMAL_1"
    assert deq.is_empty()


def test_custom_vector_negative_indexing():
    vec = CustomVector[int](initial_capacity=4)
    vec.append(10)
    vec.append(20)
    vec.append(30)
    assert vec[-1] == 30
    assert vec[-2] == 20
    assert vec[-3] == 10

    vec[-1] = 99
    assert vec[-1] == 99

    removed = vec.remove_at(-1)
    assert removed == 99
    assert len(vec) == 2
    assert vec[-1] == 20

    with pytest.raises(IndexError):
        _ = vec[-3]


def test_doubly_linked_list_pop_and_peek():
    dll = DoublyLinkedList[str]()
    dll.append("A")
    dll.append("B")
    assert dll.peek_head() == "A"
    assert dll.peek_tail() == "B"

    assert dll.pop_head() == "A"
    assert dll.pop_tail() == "B"
    assert dll.is_empty()

    with pytest.raises(IndexError):
        dll.pop_head()

    with pytest.raises(IndexError):
        dll.pop_tail()

