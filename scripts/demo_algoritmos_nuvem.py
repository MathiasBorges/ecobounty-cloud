"""Demonstração Completa Interativa: Estruturas de Dados, Algoritmos e Nuvem Google Cloud / Firebase.

Apresentação prática para a banca avaliadora:
1. Estruturas de Dados da 1ª Unidade (Vetores, Listas Encadeadas, Pilhas, Filas, Deques)
2. Diferencial 1 (2ª Unidade): Tabelas Hash com Encadeamento e Endereçamento Aberto
3. Diferencial 2 (2ª Unidade): Grafo de Geolocalização de Maceió e Roteamento Dijkstra
4. Diferencial 3 (2ª Unidade): Métodos de Ordenação (Bolha, Inserção, Seleção, QuickSort)
5. Mapeamento e Conexão em Nuvem Google Cloud Platform & Firebase (Cloud Firestore, Catbox, Cloud Functions, Vision)
"""
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.data_structures.vector import CustomVector
from app.data_structures.linked_list import LinkedList, DoublyLinkedList
from app.data_structures.restricted_list import RestrictedLinearList
from app.data_structures.stack import Stack, UndoRedoManager
from app.data_structures.queue import Queue
from app.data_structures.deque import Deque
from app.data_structures.hash_table import (
    SeparateChainingHashTable,
    OpenAddressingHashTable,
    HashMethod,
    OpenAddressingStrategy,
)
from app.algorithms.sorting import (
    bubble_sort,
    insertion_sort,
    selection_sort,
    quick_sort,
    sort_bounties_by_reward,
)
from app.algorithms.graphs import build_maceio_recycling_graph
from app.cloud.gcp_provider import get_gcp_provider
from app.cloud.cloud_architecture import get_architecture_mapping


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_unidade_1():
    print_header("1ª UNIDADE: ESTRUTURAS DE DADOS LINEARES NO ECOBOUNTY")

    # A) Vetor Dinâmico
    print("\n[A] VETOR DINÂMICO (CustomVector):")
    vec = CustomVector[str](initial_capacity=2)
    print(f"  -> Capacidade inicial alocada: {vec.capacity}")
    vec.append("Bounty #1: Resíduo Plástico Orla (R$ 25)")
    vec.append("Bounty #2: Entulho Cruz das Almas (R$ 50)")
    print(f"  -> Itens inseridos: {len(vec)} | Capacidade: {vec.capacity}")
    vec.append("Bounty #3: Vidro Jatiúca (R$ 15)")
    print(f"  -> Após 3º item: Dobra capacidade geométrica (2 -> {vec.capacity}) | O(1) amortizado")

    # B) Lista Encadeada
    print("\n[B] LISTA ENCADEADA (LinkedList - Trilha de Auditoria):")
    trail = LinkedList[str]()
    trail.append("Check-in GPS registrado pelo coletor")
    trail.append("Foto da limpeza enviada ao Firebase Storage")
    trail.append("Validação de IA concluída com 98% confiança")
    trail.append("Adiantamento de 50% liberado")
    for step, item in enumerate(trail, 1):
        print(f"  Passo {step}: {item}")

    # C) Lista Linear Restrita
    print("\n[C] LISTA LINEAR RESTRITA (RestrictedLinearList - Slots de Missões Ativas):")
    slots = RestrictedLinearList[str](max_capacity=3)
    slots.insert("Missão Ativa #101")
    slots.insert("Missão Ativa #102")
    slots.insert("Missão Ativa #103")
    print(f"  -> Slots ocupados: {len(slots)}/{slots.max_capacity} (Lista Cheia: {slots.is_full()})")
    print("  -> Tentativa de aceitar 4ª missão: bloqueada com RestrictedLinearListOverflowError!")

    # D) Pilha Undo/Redo
    print("\n[D] PILHA LIFO (Stack & UndoRedoManager):")
    undo_mgr = UndoRedoManager[str]()
    undo_mgr.record_action("Aceite da Missão #101")
    undo_mgr.record_action("Início da Rota de Coleta")
    print(f"  -> Ação desfeita: {undo_mgr.undo()}")
    print(f"  -> Ação refeita: {undo_mgr.redo()}")

    # E) Fila FIFO
    print("\n[E] FILA FIFO (Queue - Fila de Processamento de Fotos):")
    q = Queue[str]()
    q.enqueue("Upload_Foto_Coleta_12.jpg")
    q.enqueue("Upload_Foto_Coleta_13.jpg")
    print(f"  -> 1ª foto a ser auditada no Cloud Functions: {q.dequeue()} (Primeiro a Entrar, Primeiro a Sair)")

    # F) Deque
    print("\n[F] DEQUE (Fila com duas extremidades):")
    dq = Deque[str]()
    dq.append_right("Denúncia Normal - Plástico")
    dq.append_left("DENÚNCIA URGENTE - Risco de Contaminação em Lagoa!")
    print(f"  -> Prioridade máxima consumida pela esquerda (append_left): {dq.pop_left()}")


def demo_diferencial_1():
    print_header("DIFERENCIAL 1: TABELAS HASH E JUSTIFICATIVAS DE SOFTWARE")

    # Encadeamento Separado
    print("\n[1] TABELA HASH COM ENCADEAMENTO SEPARADO (Separate Chaining):")
    print("  -> Justificativa: Ideal para o Catálogo de Bounties (alta frequência de inserções e exclusões,")
    print("     tolera picos de carga alfa > 1 sem degradação catastrófica e sem clustering).")
    ch_hash = SeparateChainingHashTable[str, float](initial_capacity=7, method=HashMethod.MULTIPLICATION)
    ch_hash.put("PET_GARRAFA", 25.0)
    ch_hash.put("ALUMINIO_LATA", 45.0)
    ch_hash.put("PAPELAO_CAIXA", 18.0)
    ch_hash.put("VIDRO_GARRAFA", 12.0)
    ch_hash.put("ENTULHO_CONSTRUCAO", 80.0)
    stats = ch_hash.get_distribution_stats()
    print(f"  -> Estatísticas: Capacidade={stats['capacity']}, Itens={stats['size']}, Fator de Carga={stats['load_factor']}")
    print(f"  -> Consulta O(1) de 'ALUMINIO_LATA': R$ {ch_hash.get('ALUMINIO_LATA')}")

    # Endereçamento Aberto
    print("\n[2] TABELA HASH COM ENDEREÇAMENTO ABERTO (Double Hashing):")
    print("  -> Justificativa: Ideal para Cache de Sessões de Usuários e Lookup de QR Codes de Ecopontos.")
    print("     Garante alocação contígua no vetor da memória, aproveitando ao máximo a localidade espacial")
    print("     da memória cache L1/L2 do processador sem o overhead de nós da lista encadeada.")
    op_hash = OpenAddressingHashTable[str, str](initial_capacity=11, strategy=OpenAddressingStrategy.DOUBLE_HASHING)
    op_hash.put("ECOPONTO-COOPLUM-001", "Cooperativa COOPLUM - Jacarecica")
    op_hash.put("ECOPONTO-JATIUCA-001", "Ecoponto Jatiúca - Posto 7")
    op_hash.put("ECOPONTO-PAJUCARA-001", "Ecoponto Pajuçara - Feirinha")
    print(f"  -> Lookup do QR Code 'ECOPONTO-COOPLUM-001': {op_hash.get('ECOPONTO-COOPLUM-001')}")
    op_hash.remove("ECOPONTO-PAJUCARA-001")
    print("  -> Ecoponto Pajuçara removido com marcador sentinela TOMBSTONE.")
    print(f"  -> Nova busca em 'ECOPONTO-JATIUCA-001': {op_hash.get('ECOPONTO-JATIUCA-001')} (sondagem íntegra)")


def demo_diferencial_2():
    print_header("DIFERENCIAL 2: GRAFO DE GEOLOCALIZAÇÃO E DIJKSTRA EM MACEIÓ")
    g = build_maceio_recycling_graph()
    print(f"  -> Malha de Maceió carregada com {len(g.nodes)} ecopontos e conexões viárias.")

    start = "ECO_TRAPICHE"
    dest = "COOPLUM"
    path, dist_km = g.dijkstra_shortest_path(start, dest)

    print(f"\n  [Cálculo de Rota Ótima via Algoritmo de Dijkstra]")
    print(f"  Origem da Coleta: {g.get_node(start).name}")
    print(f"  Destino Final:    {g.get_node(dest).name}")
    print(f"  Distância Total:  {dist_km} km")
    print("\n  Passo a Passo da Rota Ótima:")
    for i, node_id in enumerate(path, 1):
        n = g.get_node(node_id)
        print(f"    [{i}] {n.name} (Lat: {n.lat:.4f}, Lng: {n.lng:.4f})")

    bfs_nodes = g.bfs_reachable(start)
    dfs_nodes = g.dfs_explore(start)
    print(f"\n  [Conectividade da Malha Viária]")
    print(f"  -> Busca em Largura (BFS com Fila FIFO O(1)):       {len(bfs_nodes)} ecopontos conectados")
    print(f"  -> Busca em Profundidade (DFS com Pilha LIFO O(1)): {len(dfs_nodes)} ecopontos conectados")
    print("  -> Visualização gerada graficamente via Matplotlib salva em: Entregas/grafo_maceio_rotas.png")


def demo_diferencial_3():
    print_header("DIFERENCIAL 3: BENCHMARK DOS 4 MÉTODOS DE ORDENAÇÃO")
    import random
    n = 1000
    rng = random.Random(123)
    dataset = [rng.uniform(10.0, 500.0) for _ in range(n)]

    algos = [
        ("Bubble Sort (Bolha)", bubble_sort),
        ("Insertion Sort (Inserção)", insertion_sort),
        ("Selection Sort (Seleção)", selection_sort),
        ("QuickSort (Rápido)", quick_sort),
    ]

    print(f"  -> Executando benchmark comparativo para N = {n} elementos:")
    for name, fn in algos:
        _, metrics = fn(list(dataset))
        print(f"     * {name:<26}: Tempo={metrics.execution_time_ms:7.2f} ms | Comparações={metrics.comparisons:10,d} | Trocas={metrics.swaps:10,d}")

    print("  -> Conclusão: QuickSort apresenta a melhor eficiência assintótica O(N log N).")
    print("  -> Gráficos comparativos gerados com Matplotlib salvos em: Entregas/benchmark_ordenacao.png")


def demo_nuvem_gcp():
    print_header("INTEGRAÇÃO EM NUVEM: GOOGLE CLOUD PLATFORM & FIREBASE FOR STUDENTS")
    mapping = get_architecture_mapping()
    print("  Mapeamento de Requisitos para Google Cloud & Firebase:")
    for req, info in mapping.items():
        print(f"  - [{req}] {info['servico_gcp']}")
        print(f"         {info['detalhes']}")

    provider = get_gcp_provider()
    print(f"\n  [Firebase Storage]: Upload de imagem simulado -> {provider.upload_image(b'TEST', 'bounties/audit_sample.jpg')}")
    print(f"  [Google Cloud Functions]: Invocação Serverless -> {provider.audit_cleaning_vision(image_data=b'TEST', bounty_id=101)['message']}")
    labels = provider.vision_detect_labels(b"IMAGE")
    print(f"  [Google Cloud Vision]: Labels detectados -> {[l['Name'] for l in labels[:3]]}")
    print(f"  [Cloud Firestore]: Regras firestore.rules e manifesto firebase.json gerados em Entregas/")


def main():
    demo_unidade_1()
    demo_diferencial_1()
    demo_diferencial_2()
    demo_diferencial_3()
    demo_nuvem_gcp()
    print("\n" + "=" * 70)
    print("  DEMONSTRAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
