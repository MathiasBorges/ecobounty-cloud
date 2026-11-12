"""Diferencial 2 do Projeto (2ª Unidade - Obrigatório): Algoritmos de Grafos e Geolocalização.

Implementa a malha viária e de ecopontos da cidade de Maceió - AL,
com algoritmo de Dijkstra para cálculo de menor caminho (rotas ótimas de coleta),
busca em largura (BFS) e profundidade (DFS) para conectividade e alcance.
"""
import heapq
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from app.data_structures.queue import Queue
from app.data_structures.stack import Stack


@dataclass
class GeoNode:
    """Vértice do grafo representando um Ecoponto, Cooperativa ou Bairro de Maceió."""
    node_id: str
    name: str
    lat: float
    lng: float
    node_type: str  # "cooperativa", "ecoponto", "bairro", "ponto_descarte"


@dataclass
class GeoEdge:
    """Aresta ponderada representando o trecho viário entre dois pontos."""
    origin_id: str
    target_id: str
    distance_km: float
    road_type: str = "avenida"  # "avenida", "rua", "litoral"


class MaceioEcoGraph:
    """Grafo de geolocalização e roteamento para logística reversa em Maceió."""

    def __init__(self):
        self.nodes: Dict[str, GeoNode] = {}
        self.adj_list: Dict[str, List[Tuple[str, float]]] = {}

    def add_node(self, node: GeoNode) -> None:
        self.nodes[node.node_id] = node
        if node.node_id not in self.adj_list:
            self.adj_list[node.node_id] = []

    def add_edge(self, u: str, v: str, distance_km: float, bidirectional: bool = True) -> None:
        if u not in self.adj_list:
            self.adj_list[u] = []
        if v not in self.adj_list:
            self.adj_list[v] = []

        self.adj_list[u].append((v, round(distance_km, 2)))
        if bidirectional:
            self.adj_list[v].append((u, round(distance_km, 2)))

    def get_node(self, node_id: str) -> Optional[GeoNode]:
        return self.nodes.get(node_id)

    def dijkstra_shortest_path(self, start_id: str, end_id: str) -> Tuple[List[str], float]:
        """Calcula a rota de menor distância utilizando o Algoritmo de Dijkstra.

        Retorna (lista_de_ids_do_caminho, distancia_total_km).
        """
        if start_id not in self.nodes or end_id not in self.nodes:
            return [], float("inf")

        distances: Dict[str, float] = {node_id: float("inf") for node_id in self.nodes}
        previous: Dict[str, Optional[str]] = {node_id: None for node_id in self.nodes}
        distances[start_id] = 0.0

        # Fila de prioridade com tupla (distancia, node_id)
        pq: List[Tuple[float, str]] = [(0.0, start_id)]

        while pq:
            curr_dist, curr_node = heapq.heappop(pq)

            if curr_dist > distances[curr_node]:
                continue

            if curr_node == end_id:
                break

            for neighbor, weight in self.adj_list.get(curr_node, []):
                new_dist = curr_dist + weight
                if new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous[neighbor] = curr_node
                    heapq.heappush(pq, (new_dist, neighbor))

        if distances[end_id] == float("inf"):
            return [], float("inf")

        # Reconstrói o caminho ótimo do destino até a origem
        path: List[str] = []
        curr: Optional[str] = end_id
        while curr is not None:
            path.append(curr)
            curr = previous[curr]
        path.reverse()

        return path, round(distances[end_id], 2)

    def find_nearest_node(self, lat: float, lng: float, node_type: Optional[str] = None) -> Optional[GeoNode]:
        """Localiza o nó do grafo geograficamente mais próximo às coordenadas informadas."""
        best_node: Optional[GeoNode] = None
        min_dist = float("inf")

        for node in self.nodes.values():
            if node_type and node.node_type != node_type:
                continue
            # Distância euclidiana aproximada ponderada
            d = math.hypot(node.lat - lat, node.lng - lng)
            if d < min_dist:
                min_dist = d
                best_node = node

        return best_node

    def bfs_reachable(self, start_id: str) -> List[str]:
        """Busca em Largura (BFS) utilizando a Fila FIFO (1ª Unidade) para explorar nós alcançáveis."""
        if start_id not in self.nodes:
            return []
        visited: Set[str] = {start_id}
        queue: Queue[str] = Queue[str]()
        queue.enqueue(start_id)
        order: List[str] = []

        while not queue.is_empty():
            node = queue.dequeue()
            order.append(node)
            for neighbor, _ in self.adj_list.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.enqueue(neighbor)
        return order

    def dfs_explore(self, start_id: str) -> List[str]:
        """Busca em Profundidade (DFS) utilizando a Pilha LIFO (1ª Unidade) para explorar a malha."""
        if start_id not in self.nodes:
            return []
        visited: Set[str] = set()
        stack: Stack[str] = Stack[str]()
        stack.push(start_id)
        order: List[str] = []

        while not stack.is_empty():
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            order.append(node)
            # Empilha vizinhos para visita em profundidade
            for neighbor, _ in reversed(self.adj_list.get(node, [])):
                if neighbor not in visited:
                    stack.push(neighbor)
        return order


    def compute_bounty_routing(
        self,
        user_lat: float,
        user_lng: float,
        bounty_lat: float,
        bounty_lng: float,
        dest_lat: Optional[float] = None,
        dest_lng: Optional[float] = None,
        bounty_val: float = 25.0,
    ) -> dict:
        """Calcula o roteamento ótimo de ciclo completo utilizando o Algoritmo de Dijkstra.

        Fase 1: Usuário -> Ponto do Resíduo (Bounty)
        Fase 2: Resíduo -> Ecoponto/Cooperativa de Destino
        Score: Recompensa (R$) / Distância Total Viária (km)
        """
        user_node = self.find_nearest_node(user_lat, user_lng)
        bounty_node = self.find_nearest_node(bounty_lat, bounty_lng)
        if dest_lat is not None and dest_lng is not None:
            dest_node = (
                self.find_nearest_node(dest_lat, dest_lng, node_type="cooperativa")
                or self.find_nearest_node(dest_lat, dest_lng)
            )
        else:
            dest_node = self.get_node("COOPLUM") or bounty_node

        u_id = user_node.node_id if user_node else "ECO_CENTRO"
        b_id = bounty_node.node_id if bounty_node else "ECO_CENTRO"
        d_id = dest_node.node_id if dest_node else "COOPLUM"

        p1_path, p1_dist = self.dijkstra_shortest_path(u_id, b_id)
        p2_path, p2_dist = self.dijkstra_shortest_path(b_id, d_id)

        # Distância geodésica local dos extremos até os nós mais próximos da malha (1 grau ~= 111 km)
        u_offset_km = round(math.hypot(user_lat - user_node.lat, user_lng - user_node.lng) * 111.0, 2) if user_node else 0.0
        b_offset_km = round(math.hypot(bounty_lat - bounty_node.lat, bounty_lng - bounty_node.lng) * 111.0, 2) if bounty_node else 0.0

        p1_km = round(p1_dist + u_offset_km + b_offset_km, 2)
        p2_km = round(p2_dist + b_offset_km, 2)
        total_km = round(p1_km + p2_km, 2)
        efficiency = round(bounty_val / max(0.5, total_km), 2)

        return {
            "user_node": user_node,
            "bounty_node": bounty_node,
            "dest_node": dest_node,
            "phase1_path": p1_path,
            "phase1_km": p1_km,
            "phase2_path": p2_path,
            "phase2_km": p2_km,
            "total_dijkstra_km": total_km,
            "efficiency_score": efficiency,
        }


def build_maceio_recycling_graph() -> MaceioEcoGraph:
    """Constrói a malha canônica de ecopontos e cooperativas de Maceió - AL."""
    g = MaceioEcoGraph()

    # Principais Ecopontos e Cooperativas com coordenadas geográficas reais
    nodes = [
        GeoNode("COOPLUM", "Cooperativa COOPLUM (Jacarecica)", -9.6105, -35.6980, "cooperativa"),
        GeoNode("ECO_CRUZ_ALMAS", "Ecoponto Cruz das Almas", -9.6280, -35.7050, "ecoponto"),
        GeoNode("ECO_MANGABEIRAS", "Ecoponto Mangabeiras", -9.6380, -35.7150, "ecoponto"),
        GeoNode("ECO_JATIUCA", "Ecoponto Jatiúca", -9.6450, -35.7010, "ecoponto"),
        GeoNode("ECO_PONTA_VERDE", "Ecoponto Ponta Verde", -9.6610, -35.7020, "ecoponto"),
        GeoNode("ECO_PAJUCARA", "Ecoponto Pajuçara", -9.6675, -35.7180, "ecoponto"),
        GeoNode("ECO_JARAGUA", "Ecoponto Histórico de Jaraguá", -9.6730, -35.7270, "ecoponto"),
        GeoNode("ECO_CENTRO", "Ecoponto Centro - Praça Martírios", -9.6660, -35.7350, "ecoponto"),
        GeoNode("ECO_FAROL", "Ecoponto Farol / Fernandes Lima", -9.6520, -35.7380, "ecoponto"),
        GeoNode("ECO_TRAPICHE", "Ecoponto Trapiche da Barra", -9.6780, -35.7550, "ecoponto"),
        GeoNode("ECO_TABULEIRO", "Ecoponto Tabuleiro dos Martins", -9.5850, -35.7750, "ecoponto"),
        GeoNode("ECO_BENEDITO", "Ecoponto Benedito Bentes", -9.5420, -35.7480, "ecoponto"),
        GeoNode("ECO_SANTOS_DUMONT", "Ecoponto Santos Dumont / BR-104", -9.5600, -35.8100, "ecoponto"),
    ]

    for n in nodes:
        g.add_node(n)

    # Conexões viárias reais da capital alagoana com distâncias aproximadas em km
    connections = [
        # Orla / Litoral Norte -> COOPLUM
        ("COOPLUM", "ECO_CRUZ_ALMAS", 2.3),
        ("ECO_CRUZ_ALMAS", "ECO_MANGABEIRAS", 1.6),
        ("ECO_CRUZ_ALMAS", "ECO_JATIUCA", 2.1),
        ("ECO_MANGABEIRAS", "ECO_JATIUCA", 1.8),
        ("ECO_JATIUCA", "ECO_PONTA_VERDE", 1.9),
        ("ECO_PONTA_VERDE", "ECO_PAJUCARA", 1.8),
        ("ECO_PAJUCARA", "ECO_JARAGUA", 1.5),
        ("ECO_JARAGUA", "ECO_CENTRO", 1.2),
        ("ECO_CENTRO", "ECO_FAROL", 2.2),
        ("ECO_CENTRO", "ECO_TRAPICHE", 3.1),
        ("ECO_MANGABEIRAS", "ECO_FAROL", 3.0),
        ("ECO_FAROL", "ECO_TABULEIRO", 8.4),
        ("ECO_TABULEIRO", "ECO_BENEDITO", 6.2),
        ("ECO_TABULEIRO", "ECO_SANTOS_DUMONT", 4.2),
        ("ECO_BENEDITO", "ECO_SANTOS_DUMONT", 6.8),
        ("ECO_CRUZ_ALMAS", "ECO_FAROL", 4.5),
        ("ECO_MANGABEIRAS", "ECO_TABULEIRO", 7.8),
    ]

    for u, v, dist in connections:
        g.add_edge(u, v, dist, bidirectional=True)

    return g
